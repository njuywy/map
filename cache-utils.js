(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  }
  root.CacheUtils = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function isTiandituTileUrl(rawUrl) {
    try {
      const url = new URL(rawUrl);
      return /^t[0-7]\.tianditu\.gov\.cn$/i.test(url.hostname)
        && /^\/(img|cia)_w\/wmts$/i.test(url.pathname)
        && String(url.searchParams.get('REQUEST')).toLowerCase() === 'gettile';
    } catch (error) {
      return false;
    }
  }

  function normalizedTileKey(rawUrl, origin) {
    if (!isTiandituTileUrl(rawUrl)) return null;
    const url = new URL(rawUrl);
    const layer = String(url.searchParams.get('LAYER') || '').toLowerCase();
    const zoom = url.searchParams.get('TILEMATRIX');
    const column = url.searchParams.get('TILECOL');
    const row = url.searchParams.get('TILEROW');
    if (!layer || !zoom || !column || !row) return null;
    return `${origin}/__tile-cache/${encodeURIComponent(layer)}/${encodeURIComponent(zoom)}/${encodeURIComponent(column)}/${encodeURIComponent(row)}`;
  }

  function sanitizeSettings(settings) {
    const source = settings || {};
    const days = Math.min(365, Math.max(1, Number(source.maxAgeDays) || 30));
    const entries = Math.min(10000, Math.max(100, Number(source.maxEntries) || 2000));
    return { enabled: source.enabled !== false, maxAgeDays: days, maxEntries: entries };
  }

  return { isTiandituTileUrl, normalizedTileKey, sanitizeSettings };
});
