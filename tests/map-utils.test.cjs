const assert = require('assert').strict;
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const projectRoot = path.resolve(__dirname, '../source');
const tests = [];
const test = (name, run) => tests.push({ name, run });

test('required browser entry points exist', () => {
  for (const relativePath of ['index.html', 'app.js', 'map-utils.js', 'cache-utils.js', 'service-worker.js', 'map-data.js', 'styles.css']) {
    assert.equal(fs.existsSync(path.join(projectRoot, relativePath)), true, `${relativePath} is missing`);
  }
});

test('point popup exposes CGCS2000 latitude and longitude to nine decimals', () => {
  const utils = require(path.join(projectRoot, 'map-utils.js'));
  const html = utils.buildPointPopup({
    name: '目标点位',
    lat: 31.832086581,
    lng: 121.077742102,
    crs: 'CGCS2000（EPSG:4490）',
  });

  assert.match(html, /31\.832086581/);
  assert.match(html, /121\.077742102/);
  assert.match(html, /CGCS2000/);
});

test('Tianditu URL only exists when a token is configured', () => {
  const utils = require(path.join(projectRoot, 'map-utils.js'));
  assert.equal(utils.tiandituUrl('img', ''), null);
  assert.match(utils.tiandituUrl('img', 'example-token'), /img_w\/wmts/);
  assert.match(utils.tiandituUrl('cia', 'example-token'), /LAYER=cia/);
});

test('page loads Leaflet locally and exposes accessible map controls', () => {
  const html = fs.readFileSync(path.join(projectRoot, 'index.html'), 'utf8');
  assert.match(html, /vendor\/leaflet\/leaflet\.js/);
  assert.match(html, /id="map"/);
  assert.match(html, /id="show-point"/);
  assert.match(html, /id="fit-route"/);
});

test('map data includes every converted workbook point and multiple railway segments', () => {
  const source = fs.readFileSync(path.join(projectRoot, 'map-data.js'), 'utf8');
  const sandbox = { window: {} };
  vm.runInNewContext(source, sandbox);
  const features = sandbox.window.MAP_DATA.features;
  const points = features.filter((feature) => feature.geometry.type === 'Point');
  const lines = features.filter((feature) => feature.geometry.type === 'LineString');

  assert.equal(points.length, 73);
  assert.deepEqual(Array.from(points[0].geometry.coordinates), [121.052559163, 31.824126966]);
  const lastPoint = points[points.length - 1];
  assert.deepEqual(Array.from(lastPoint.geometry.coordinates), [121.1611085, 31.928844681]);
  assert.equal(points[0].properties.name, '点位 1');
  assert.equal(lastPoint.properties.source_row, 74);
  assert.ok(lines.length >= 4);
  assert.ok(lines.every((line) => line.geometry.coordinates.length >= 2));
});

test('railway display bounds form a square in Web Mercator', () => {
  const utils = require(path.join(projectRoot, 'map-utils.js'));
  const source = fs.readFileSync(path.join(projectRoot, 'map-data.js'), 'utf8');
  const sandbox = { window: {} };
  vm.runInNewContext(source, sandbox);
  const lines = sandbox.window.MAP_DATA.features.filter((feature) => feature.geometry.type === 'LineString');
  const bounds = utils.squareMercatorBounds(lines, 0.07);
  const south = bounds[0][0];
  const west = bounds[0][1];
  const north = bounds[1][0];
  const east = bounds[1][1];
  const mercatorY = (lat) => Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));

  assert.ok(Math.abs((east - west) * Math.PI / 180 - (mercatorY(north) - mercatorY(south))) < 1e-10);
});

test('tile cache keys exclude the Tianditu token', () => {
  const cacheUtils = require(path.join(projectRoot, 'cache-utils.js'));
  const tileUrl = 'https://t2.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&LAYER=img&TILEMATRIX=15&TILEROW=10&TILECOL=20&tk=secret-token';
  const key = cacheUtils.normalizedTileKey(tileUrl, 'http://127.0.0.1:8088');

  assert.match(key, /tile-cache\/img\/15\/20\/10/);
  assert.doesNotMatch(key, /secret-token|tk=/);
  assert.equal(cacheUtils.normalizedTileKey('https://example.com/tile.png', 'http://127.0.0.1:8088'), null);
  assert.deepEqual(
    cacheUtils.sanitizeSettings({ enabled: false, maxAgeDays: 999, maxEntries: 5 }),
    { enabled: false, maxAgeDays: 365, maxEntries: 100 },
  );
  assert.deepEqual(
    cacheUtils.sanitizeSettings({}),
    { enabled: true, maxAgeDays: 30, maxEntries: 20000 },
  );
  assert.equal(cacheUtils.sanitizeSettings({ maxEntries: 99999 }).maxEntries, 20000);
});

test('page exposes cache settings and uses a light-blue railway style', () => {
  const html = fs.readFileSync(path.join(projectRoot, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(projectRoot, 'app.js'), 'utf8');
  for (const id of ['cache-enabled', 'cache-days', 'cache-limit', 'clear-cache', 'cache-stats']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(app, /#79d7ee/i);
  assert.doesNotMatch(app, /routeOutline/);
  assert.match(html, /class="map-square"/);
  assert.doesNotMatch(html, /class="sidebar"/);
});

test('online imagery opens by default without asking for a token and can be closed', () => {
  const html = fs.readFileSync(path.join(projectRoot, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(projectRoot, 'app.js'), 'utf8');
  const configSource = fs.readFileSync(path.join(projectRoot, 'config.js'), 'utf8');
  const sandbox = { window: {} };
  vm.runInNewContext(configSource, sandbox);

  assert.equal(sandbox.window.APP_CONFIG.tiandituToken, '8311ec3baf61aca104ce358a2fcdbb6d');
  assert.doesNotMatch(html, /id="token-input"|id="enable-online"/);
  assert.match(html, /id="disable-online"[^>]*>关闭在线影像</);
  assert.match(app, /cacheLimit\.max = CacheUtils\.DEFAULT_SETTINGS\.maxEntries/);
  assert.doesNotMatch(app, /safeStorage(?:Get|Set)\('tiandituToken'|tokenInput/);
  assert.match(app, /activateOnlineLayer\(configuredToken\)/);
  assert.match(app, /id="disable-online"|getElementById\('disable-online'\)/);
});

test('default imagery stays visible while browser-token tiles load', () => {
  const app = fs.readFileSync(path.join(projectRoot, 'app.js'), 'utf8');
  const activationStart = app.indexOf('function activateOnlineLayer');
  const closeHandlerStart = app.indexOf("document.getElementById('disable-online')", activationStart);
  const activationSource = app.slice(activationStart, closeHandlerStart);

  assert.ok(activationStart >= 0 && closeHandlerStart > activationStart);
  assert.doesNotMatch(activationSource, /removeLayer\(offlineLayer\)/);
  assert.match(activationSource, /onlineLayer\.addTo\(map\)/);
  assert.match(activationSource, /imageLayer\.once\('tileload'/);
  assert.match(app, /createPane\('offlinePane'\)/);
  assert.match(app, /pane: 'offlinePane'/);
  assert.match(app, /offlineLayer\.once\('load',[\s\S]*requestAnimationFrame\(startOnlineLayer\)/);
});

let failures = 0;
for (const { name, run } of tests) {
  try {
    run();
    console.log(`✓ ${name}`);
  } catch (error) {
    failures += 1;
    console.error(`✗ ${name}`);
    console.error(error.stack || error);
  }
}
process.exitCode = failures ? 1 : 0;
