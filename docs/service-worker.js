importScripts('cache-utils.js');

const TILE_CACHE = 'tianditu-tiles-v1';
const META_CACHE = 'tianditu-tiles-meta-v1';
const CONFIG_CACHE = 'tianditu-cache-config-v1';
const CONFIG_KEY = new URL('/__tile-cache-config', self.location.origin).toString();
const DEFAULT_SETTINGS = { enabled: true, maxAgeDays: 30, maxEntries: 2000 };
let writesSinceTrim = 0;

self.addEventListener('install', function (event) {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function (event) {
  event.waitUntil(self.clients.claim());
});

async function readSettings() {
  const cache = await caches.open(CONFIG_CACHE);
  const response = await cache.match(CONFIG_KEY);
  if (!response) return DEFAULT_SETTINGS;
  try {
    return CacheUtils.sanitizeSettings(await response.json());
  } catch (error) {
    return DEFAULT_SETTINGS;
  }
}

async function writeSettings(settings) {
  const sanitized = CacheUtils.sanitizeSettings(settings);
  const cache = await caches.open(CONFIG_CACHE);
  await cache.put(CONFIG_KEY, new Response(JSON.stringify(sanitized), { headers: { 'Content-Type': 'application/json' } }));
  await trimCache(sanitized.maxEntries);
  return sanitized;
}

async function metadataFor(key) {
  const cache = await caches.open(META_CACHE);
  const response = await cache.match(key);
  if (!response) return null;
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

async function deleteTile(key) {
  const tileCache = await caches.open(TILE_CACHE);
  const metadataCache = await caches.open(META_CACHE);
  await Promise.all([tileCache.delete(key), metadataCache.delete(key)]);
}

async function cacheNetworkTile(request, key, response, maxEntries) {
  const cacheable = response.type === 'opaque'
    || (response.ok && String(response.headers.get('Content-Type') || '').startsWith('image/'));
  if (!cacheable) return;
  const tileCache = await caches.open(TILE_CACHE);
  const metadataCache = await caches.open(META_CACHE);
  await Promise.all([
    tileCache.put(key, response.clone()),
    metadataCache.put(key, new Response(JSON.stringify({ cachedAt: Date.now() }))),
  ]);
  writesSinceTrim += 1;
  if (writesSinceTrim >= 25) {
    writesSinceTrim = 0;
    await trimCache(maxEntries);
  }
}

async function trimCache(maxEntries) {
  const tileCache = await caches.open(TILE_CACHE);
  const keys = await tileCache.keys();
  if (keys.length <= maxEntries) return;
  const datedKeys = await Promise.all(keys.map(async function (request) {
    const metadata = await metadataFor(request);
    return { request, cachedAt: metadata ? metadata.cachedAt : 0 };
  }));
  datedKeys.sort((left, right) => left.cachedAt - right.cachedAt);
  await Promise.all(datedKeys.slice(0, keys.length - maxEntries).map((item) => deleteTile(item.request)));
}

async function tileResponse(request) {
  const settings = await readSettings();
  if (!settings.enabled) return fetch(request);
  const key = CacheUtils.normalizedTileKey(request.url, self.location.origin);
  if (!key) return fetch(request);
  const tileCache = await caches.open(TILE_CACHE);
  const cached = await tileCache.match(key);
  if (cached) {
    const metadata = await metadataFor(key);
    const maxAgeMilliseconds = settings.maxAgeDays * 24 * 60 * 60 * 1000;
    if (metadata && Date.now() - metadata.cachedAt <= maxAgeMilliseconds) return cached;
  }
  try {
    const response = await fetch(request);
    await cacheNetworkTile(request, key, response, settings.maxEntries);
    return response;
  } catch (error) {
    if (cached) return cached;
    throw error;
  }
}

async function clearTiles() {
  const tileCache = await caches.open(TILE_CACHE);
  const count = (await tileCache.keys()).length;
  await Promise.all([caches.delete(TILE_CACHE), caches.delete(META_CACHE)]);
  return count;
}

async function cacheStats() {
  const tileCache = await caches.open(TILE_CACHE);
  const settings = await readSettings();
  return { count: (await tileCache.keys()).length, settings };
}

self.addEventListener('fetch', function (event) {
  if (event.request.method === 'GET' && CacheUtils.isTiandituTileUrl(event.request.url)) {
    event.respondWith(tileResponse(event.request));
  }
});

self.addEventListener('message', function (event) {
  const message = event.data || {};
  const reply = event.ports && event.ports[0];
  if (message.type === 'CACHE_CONFIG') {
    event.waitUntil(writeSettings(message.settings).then((settings) => reply && reply.postMessage({ ok: true, settings })));
  } else if (message.type === 'CACHE_CLEAR') {
    event.waitUntil(clearTiles().then((count) => reply && reply.postMessage({ ok: true, count })));
  } else if (message.type === 'CACHE_STATS') {
    event.waitUntil(cacheStats().then((stats) => reply && reply.postMessage({ ok: true, stats })));
  }
});
