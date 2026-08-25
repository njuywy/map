(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.MapUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, function (character) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;',
      }[character];
    });
  }

  function formatCoordinate(value) {
    return Number(value).toFixed(9);
  }

  function buildPointPopup(point) {
    const latitude = formatCoordinate(point.lat);
    const longitude = formatCoordinate(point.lng);
    return [
      '<section class="point-popup">',
      `<strong>${escapeHtml(point.name)}</strong>`,
      '<dl>',
      `<div><dt>纬度</dt><dd>${latitude}°</dd></div>`,
      `<div><dt>经度</dt><dd>${longitude}°</dd></div>`,
      `<div><dt>坐标系</dt><dd>${escapeHtml(point.crs)}</dd></div>`,
      '</dl>',
      `<button type="button" id="copy-coordinate" data-coordinate="${latitude}, ${longitude}">复制经纬度</button>`,
      '</section>',
    ].join('');
  }

  function tiandituUrl(layer, token) {
    const cleanToken = String(token || '').trim();
    if (!cleanToken) return null;
    const cleanLayer = layer === 'cia' ? 'cia' : 'img';
    return `https://t{s}.tianditu.gov.cn/${cleanLayer}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${cleanLayer}&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${encodeURIComponent(cleanToken)}`;
  }

  function squareMercatorBounds(features, marginRatio) {
    const coordinates = features.flatMap(function (feature) {
      return feature.geometry && feature.geometry.type === 'LineString' ? feature.geometry.coordinates : [];
    });
    if (!coordinates.length) throw new Error('无法计算空线路的地图边界');
    const margin = Number.isFinite(marginRatio) ? Math.max(0, marginRatio) : 0.07;
    const mercator = coordinates.map(function (coordinate) {
      const longitudeRadians = coordinate[0] * Math.PI / 180;
      const latitudeRadians = coordinate[1] * Math.PI / 180;
      return [longitudeRadians, Math.log(Math.tan(Math.PI / 4 + latitudeRadians / 2))];
    });
    const xValues = mercator.map((point) => point[0]);
    const yValues = mercator.map((point) => point[1]);
    const minX = Math.min.apply(null, xValues);
    const maxX = Math.max.apply(null, xValues);
    const minY = Math.min.apply(null, yValues);
    const maxY = Math.max.apply(null, yValues);
    const side = Math.max(maxX - minX, maxY - minY) * (1 + margin * 2);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const inverseLatitude = (value) => (2 * Math.atan(Math.exp(value)) - Math.PI / 2) * 180 / Math.PI;
    return [
      [inverseLatitude(centerY - side / 2), (centerX - side / 2) * 180 / Math.PI],
      [inverseLatitude(centerY + side / 2), (centerX + side / 2) * 180 / Math.PI],
    ];
  }

  return { buildPointPopup, escapeHtml, formatCoordinate, squareMercatorBounds, tiandituUrl };
});
