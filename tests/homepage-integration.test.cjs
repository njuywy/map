const assert = require('assert').strict;
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');

for (const relativePath of [
  'source/index.html',
  'source/app.js',
  'source/map-data.js',
  'source/styles.css',
  'source/assets/tonghai-tianditu-satellite-square.jpg',
  'source/vendor/leaflet/leaflet.js',
  'archive/tonghai-railway-local-20260825/interactive-map/index.html',
  'archive/tonghai-railway-local-20260825/CGCS2000经纬度.xlsx',
]) {
  assert.equal(fs.existsSync(path.join(root, relativePath)), true, `${relativePath} is missing`);
}

const homepage = read('source/index.html');
assert.match(homepage, /id="map"/);
assert.match(homepage, /href="blog\/"/);
assert.match(homepage, /显示全部点位/);

const sandbox = { window: {} };
vm.runInNewContext(read('source/map-data.js'), sandbox);
const features = sandbox.window.MAP_DATA.features;
assert.equal(features.filter((feature) => feature.geometry.type === 'Point').length, 73);
assert.equal(features.filter((feature) => feature.geometry.type === 'LineString').length, 4);

const config = read('_config.yml');
assert.match(config, /index_generator:\s*\n\s+path:\s*blog/);
assert.match(config, /skip_render:[\s\S]*?-\s+["']?index\.html["']?/);
assert.match(read('source/categories/index.md'), /layout:\s*categories/);
assert.match(read('source/tags/index.md'), /layout:\s*tags/);

console.log('✓ railway map is the blog homepage and the original app is archived');
