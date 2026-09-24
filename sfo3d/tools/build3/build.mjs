// Build script for the three.js renderer (live3.html).
//   node tools/build3/build.mjs            -> vendor/three/three.module.js (three r186 + TSL + add-ons, minified ESM)
//   node tools/build3/build.mjs --app      -> also out/build3/live3.bundle.js: the whole app (js/live/entry.js with the
//                                             same remaps as live3.html's import map) as one minified ES module
// Pinned: three 0.186.0, esbuild 0.28.2 (package.json devDependencies). three.js is MIT; its licence is copied next to
// the vendored module.
import * as esbuild from 'esbuild';
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const THREE_DIR = path.join(ROOT, 'node_modules', 'three');
const pkg = JSON.parse(fs.readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8'));
if (pkg.version !== '0.186.0') { console.error('three must be 0.186.0 (found ' + pkg.version + '): npm i -D three@0.186.0'); process.exit(1); }

const vendorOut = path.join(ROOT, 'vendor', 'three', 'three.module.js');
fs.mkdirSync(path.dirname(vendorOut), { recursive: true });
const r = await esbuild.build({
  entryPoints: [path.join(ROOT, 'tools', 'build3', 'three-entry.js')], bundle: true, format: 'esm', minify: true, target: 'es2020',
  outfile: vendorOut, legalComments: 'none', metafile: true, logLevel: 'warning',
  banner: { js: '/* three.js r186 (npm three@0.186.0), MIT licence: see LICENSE in this folder. WebGPURenderer + TSL + CSMShadowNode, GTAO, TRAA, Bloom, FXAA, SMAA. Built by tools/build3/build.mjs */' },
});
fs.copyFileSync(path.join(THREE_DIR, 'LICENSE'), path.join(ROOT, 'vendor', 'three', 'LICENSE'));
fs.writeFileSync(path.join(ROOT, 'vendor', 'three', 'VERSION.json'), JSON.stringify({ package: 'three', version: pkg.version, esbuild: esbuild.version, built: new Date().toISOString(), bytes: fs.statSync(vendorOut).size }, null, 1) + '\n');
console.log('vendor/three/three.module.js', fs.statSync(vendorOut).size, 'bytes');

if (process.argv.includes('--app')) {
  // the same module swaps as live3.html's import map (imports + the /js/three/ scope that keeps the originals)
  const J = (...p) => path.join(ROOT, 'js', ...p);
  const remap = {
    [J('gl.js')]: J('three', 'compat', 'gl.js'),
    [J('renderer.js')]: J('three', 'compat', 'renderer.js'),
    [J('scene.js')]: J('three', 'compat', 'scene.js'),
    [J('world', 'world.js')]: J('three', 'compat', 'world.js'),
  };
  const scopeKeep = new Set([J('renderer.js'), J('world', 'world.js')]);
  const plugin = { name: 'sfo-remap', setup(b) {
    b.onResolve({ filter: /.*/ }, (args) => {
      if (!args.path.startsWith('.')) return null;
      const abs = path.resolve(args.resolveDir, args.path);
      if (args.importer && args.importer.startsWith(J('three') + path.sep) && scopeKeep.has(abs)) return { path: abs };
      return remap[abs] ? { path: remap[abs] } : null;
    });
  } };
  const appOut = path.join(ROOT, 'out', 'build3', 'live3.bundle.js');
  await esbuild.build({ entryPoints: [J('live', 'entry.js')], bundle: true, format: 'esm', minify: true, target: 'es2020', outfile: appOut, plugins: [plugin], logLevel: 'warning' });
  console.log('out/build3/live3.bundle.js', fs.statSync(appOut).size, 'bytes');
}
