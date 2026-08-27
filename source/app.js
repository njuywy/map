(function () {
  'use strict';

  const pointFeatures = window.MAP_DATA.features.filter(function (feature) {
    return feature.geometry && feature.geometry.type === 'Point';
  });
  if (!pointFeatures.length) throw new Error('地图数据中缺少目标点位');
  const points = pointFeatures.map(function (feature) {
    const crs = feature.properties.crs || 'CGCS2000 / EPSG:4490';
    return {
      name: feature.properties.name,
      lat: feature.geometry.coordinates[1],
      lng: feature.geometry.coordinates[0],
      crs: crs.replace(' / ', '（') + (crs.includes(' / ') ? '）' : ''),
    };
  });
  const routeFeatures = window.MAP_DATA.features.filter(function (feature) {
    return feature.geometry && feature.geometry.type === 'LineString';
  });
  const squareBoundsArray = MapUtils.squareMercatorBounds(routeFeatures, 0.07);
  const squareBounds = L.latLngBounds(squareBoundsArray[0], squareBoundsArray[1]);

  const map = L.map('map', {
    zoomControl: false,
    minZoom: 11,
    maxZoom: 18,
    zoomSnap: 0.25,
    zoomDelta: 0.5,
    wheelPxPerZoomLevel: 90,
    maxBounds: squareBounds,
    maxBoundsViscosity: 1,
  });
  L.control.zoom({ position: 'bottomright', zoomInTitle: '放大', zoomOutTitle: '缩小' }).addTo(map);
  L.control.scale({ position: 'bottomleft', imperial: false, maxWidth: 160 }).addTo(map);

  const offlinePane = map.createPane('offlinePane');
  offlinePane.style.zIndex = '150';
  offlinePane.style.pointerEvents = 'none';
  const offlineLayer = L.imageOverlay('assets/tonghai-tianditu-satellite-square.jpg', squareBounds, {
    alt: '仅覆盖通海铁路专用线全线范围的正方形天地图卫星影像',
    opacity: 1,
    pane: 'offlinePane',
  }).addTo(map);

  const routeLayer = L.geoJSON({ type: 'FeatureCollection', features: routeFeatures }, {
    style: {
      color: '#79d7ee',
      weight: 7,
      opacity: 0.96,
      lineCap: 'round',
      lineJoin: 'round',
    },
  }).bindTooltip('通海港区铁路专用线（公开线位）', { sticky: true }).addTo(map);
  const pointLayer = L.featureGroup();
  points.forEach(function (point) {
    const marker = L.circleMarker([point.lat, point.lng], {
      radius: 5,
      color: '#ffffff',
      weight: 2,
      fillColor: '#dc293a',
      fillOpacity: 0.95,
    });
    marker.bindTooltip(point.name, { direction: 'top' });
    marker.bindPopup(MapUtils.buildPointPopup(point), { maxWidth: 330, minWidth: 270 });
    marker.addTo(pointLayer);
  });
  pointLayer.addTo(map);
  document.getElementById('point-count').textContent = `${points.length} 个 CGCS2000 点位`;

  const stations = L.featureGroup([
    L.circleMarker([31.9278785, 121.1783968], { radius: 7, color: '#fff', weight: 2, fillColor: '#79d7ee', fillOpacity: 1 }).bindTooltip('海门站', { permanent: true, direction: 'right' }),
    L.circleMarker([31.8143874, 121.0504339], { radius: 7, color: '#fff', weight: 2, fillColor: '#79d7ee', fillOpacity: 1 }).bindTooltip('通海港站', { permanent: true, direction: 'right' }),
  ]).addTo(map);

  function fitSquare(animate) {
    map.setMinZoom(0);
    map.fitBounds(squareBounds, { animate: Boolean(animate) });
    window.setTimeout(function () {
      map.setMinZoom(map.getBoundsZoom(squareBounds, false));
    }, animate ? 300 : 0);
  }

  document.getElementById('show-point').addEventListener('click', function () {
    map.fitBounds(pointLayer.getBounds().pad(0.08), { animate: true, maxZoom: 17 });
  });
  document.getElementById('fit-route').addEventListener('click', function () { fitSquare(true); });
  map.on('popupopen', function () {
    const copyButton = document.getElementById('copy-coordinate');
    if (!copyButton) return;
    copyButton.addEventListener('click', function () {
      const value = copyButton.dataset.coordinate;
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(value).then(function () { copyButton.textContent = '已复制'; });
      } else {
        window.prompt('复制经纬度：', value);
      }
    }, { once: true });
  });

  const settingsPanel = document.getElementById('settings-panel');
  const settingsToggle = document.getElementById('cache-settings-toggle');
  function setSettingsOpen(open) {
    settingsPanel.hidden = !open;
    settingsToggle.setAttribute('aria-expanded', String(open));
    if (open) refreshCacheStats();
  }
  settingsToggle.addEventListener('click', function () { setSettingsOpen(settingsPanel.hidden); });
  document.getElementById('close-settings').addEventListener('click', function () { setSettingsOpen(false); });

  function safeStorageGet(key, fallback) {
    try { return window.localStorage.getItem(key) || fallback; } catch (error) { return fallback; }
  }
  function safeStorageSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (error) { /* Storage may be disabled for file:// pages. */ }
  }

  const cacheEnabled = document.getElementById('cache-enabled');
  const cacheDays = document.getElementById('cache-days');
  const cacheLimit = document.getElementById('cache-limit');
  const cacheMessage = document.getElementById('cache-message');
  cacheLimit.max = CacheUtils.DEFAULT_SETTINGS.maxEntries;
  const savedCacheSettings = CacheUtils.sanitizeSettings({
    enabled: safeStorageGet('tileCacheEnabled', String(CacheUtils.DEFAULT_SETTINGS.enabled)) !== 'false',
    maxAgeDays: safeStorageGet('tileCacheDays', String(CacheUtils.DEFAULT_SETTINGS.maxAgeDays)),
    maxEntries: safeStorageGet('tileCacheLimit', String(CacheUtils.DEFAULT_SETTINGS.maxEntries)),
  });
  cacheEnabled.checked = savedCacheSettings.enabled;
  cacheDays.value = savedCacheSettings.maxAgeDays;
  cacheLimit.value = savedCacheSettings.maxEntries;

  let serviceWorkerRegistration = null;
  function sendWorkerMessage(message) {
    return new Promise(function (resolve, reject) {
      if (!serviceWorkerRegistration || !serviceWorkerRegistration.active) {
        reject(new Error('缓存服务尚未启动'));
        return;
      }
      const channel = new MessageChannel();
      const timeout = window.setTimeout(function () { reject(new Error('缓存服务响应超时')); }, 5000);
      channel.port1.onmessage = function (event) {
        window.clearTimeout(timeout);
        resolve(event.data);
      };
      serviceWorkerRegistration.active.postMessage(message, [channel.port2]);
    });
  }

  function currentCacheSettings() {
    return CacheUtils.sanitizeSettings({
      enabled: cacheEnabled.checked,
      maxAgeDays: cacheDays.value,
      maxEntries: cacheLimit.value,
    });
  }

  function saveCacheSettings() {
    const settings = currentCacheSettings();
    cacheDays.value = settings.maxAgeDays;
    cacheLimit.value = settings.maxEntries;
    safeStorageSet('tileCacheEnabled', String(settings.enabled));
    safeStorageSet('tileCacheDays', String(settings.maxAgeDays));
    safeStorageSet('tileCacheLimit', String(settings.maxEntries));
    sendWorkerMessage({ type: 'CACHE_CONFIG', settings }).then(function () {
      cacheMessage.textContent = settings.enabled ? '缓存设置已保存。' : '瓦片缓存已暂停。';
      refreshCacheStats();
    }).catch(function (error) { cacheMessage.textContent = error.message; });
  }
  [cacheEnabled, cacheDays, cacheLimit].forEach(function (control) {
    control.addEventListener('change', saveCacheSettings);
  });

  function refreshCacheStats() {
    const output = document.getElementById('cache-stats');
    sendWorkerMessage({ type: 'CACHE_STATS' }).then(function (response) {
      output.textContent = `已缓存 ${response.stats.count} 张瓦片`;
    }).catch(function () {
      output.textContent = window.location.protocol === 'file:' ? '直接打开模式不启用在线缓存' : '缓存服务未就绪';
    });
  }
  document.getElementById('clear-cache').addEventListener('click', function () {
    sendWorkerMessage({ type: 'CACHE_CLEAR' }).then(function (response) {
      cacheMessage.textContent = `已清除 ${response.count} 张缓存瓦片。`;
      refreshCacheStats();
    }).catch(function (error) { cacheMessage.textContent = error.message; });
  });

  if ('serviceWorker' in navigator && window.location.protocol !== 'file:') {
    navigator.serviceWorker.register('service-worker.js').then(function (registration) {
      return navigator.serviceWorker.ready.then(function () {
        serviceWorkerRegistration = registration;
        return sendWorkerMessage({ type: 'CACHE_CONFIG', settings: currentCacheSettings() });
      });
    }).then(refreshCacheStats).catch(function (error) { cacheMessage.textContent = `缓存初始化失败：${error.message}`; });
  } else {
    document.getElementById('cache-stats').textContent = '请通过 start_map.sh 启动缓存功能';
  }

  let onlineLayer = null;
  const onlineMessage = document.getElementById('online-message');
  const configuredToken = (window.APP_CONFIG && window.APP_CONFIG.tiandituToken) || '';

  function bringMapOverlaysToFront() {
    routeLayer.bringToFront();
    stations.bringToFront();
    pointLayer.bringToFront();
  }

  function activateOnlineLayer(token) {
    const imageUrl = MapUtils.tiandituUrl('img', token);
    const annotationUrl = MapUtils.tiandituUrl('cia', token);
    if (!imageUrl || !annotationUrl) return false;
    if (onlineLayer) map.removeLayer(onlineLayer);
    const imageLayer = L.tileLayer(imageUrl, { subdomains: '01234567', minZoom: 1, maxZoom: 18, maxNativeZoom: 18, attribution: '影像 © 天地图' });
    const nextOnlineLayer = L.layerGroup([
      imageLayer,
      L.tileLayer(annotationUrl, { subdomains: '01234567', minZoom: 1, maxZoom: 18, maxNativeZoom: 18, pane: 'shadowPane' }),
    ]);
    onlineLayer = nextOnlineLayer;
    imageLayer.once('tileload', function () {
      if (onlineLayer !== nextOnlineLayer) return;
      document.getElementById('map-mode').textContent = '在线影像';
      document.getElementById('map-mode').classList.add('online');
      onlineMessage.textContent = '在线影像加载成功；浏览过的瓦片将按设置缓存。';
    });
    onlineLayer.addTo(map);
    bringMapOverlaysToFront();
    document.getElementById('map-mode').textContent = '正在加载';
    document.getElementById('map-mode').classList.remove('online');
    onlineMessage.textContent = '正在通过浏览器端 Token 加载在线影像…';
    return true;
  }

  document.getElementById('disable-online').addEventListener('click', function () {
    if (onlineLayer) map.removeLayer(onlineLayer);
    onlineLayer = null;
    offlineLayer.addTo(map);
    bringMapOverlaysToFront();
    document.getElementById('map-mode').textContent = '本地影像';
    document.getElementById('map-mode').classList.remove('online');
    onlineMessage.textContent = '已关闭在线影像，当前使用本地影像。';
  });

  function startOnlineLayer() {
    if (!activateOnlineLayer(configuredToken)) {
      onlineMessage.textContent = '在线影像配置不可用，当前使用本地影像。';
    }
  }

  fitSquare(false);
  offlineLayer.once('load', function () {
    window.requestAnimationFrame(startOnlineLayer);
  });
  window.addEventListener('resize', function () { window.setTimeout(function () { fitSquare(false); }, 120); });
})();
