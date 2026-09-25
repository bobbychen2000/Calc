// Build script for the three.js renderer (live3.html).
//   node tools/build3/build.mjs            -> vendor/three/three.module.js (three r186 + TSL + add-ons, minified ESM)
//                                             and vendor/three/three.debug.js (same, not minified: js/three/dev/probe.html?debug=1)
//   node tools/build3/build.mjs --app      -> also out/build3/live3.bundle.js: the whole app (js/live/entry.js with the
//                                             same remaps as live3.html's import map) as one minified ES module, with
//                                             the MSDF sign atlas copied next to it (out/build3/assets/, where
//                                             js/three/signs.js looks for it: new URL('./assets/', import.meta.url))
// Pinned: three 0.186.0, esbuild 0.28.2 (package.json devDependencies). three.js is MIT; its licence is copied next to
// the vendored module.
//
// Two source patches are applied while bundling (and the build fails if the patched text is not found, so a three.js
// update cannot silently drop them):
//   examples/jsm/tsl/utils/TAAUtils.js samplePreviousDepth: with a reversed depth buffer on the WebGL 2 backend the
//   previous depth was passed raw to getViewPosition(), which maps depth*2-1 (the WebGL [-1,1] convention) while the
//   reversed projection (EXT_clip_control, [0,1]) expects the raw value: the reprojected depth came out behind the
//   camera and TRAA's disocclusion test never fired (ghosting when the background is revealed; review round 1).
//   Patched: reversed depth -> view z (perspectiveDepthToViewZ, reversed-aware), view position = view ray through uv
//   scaled to that z. Same result on WebGPU, correct on WebGL 2. The non-reversed path is unchanged.
//   GPUTextureViewDescriptor (src/renderers/webgpu/descriptors/, bundled in build/three.webgpu.js, which is what
//   'three/webgpu' resolves to): three sets swizzle = 'rgba' on every texture view.
//   Chromium 141 (and any browser whose WebIDL has the older dictionary form of the proposed swizzle member) rejects
//   the string with "TypeError: The provided value is not of type 'GPUTextureComponentSwizzle'" at the first render
//   pass, so nothing renders on WebGPU (found by the first WebGPU run, tools/build3/wgpu_run.mjs, 25 Sep 2026). The
//   member is left undefined instead (not passed): the default is the identity swizzle, which is what 'rgba' means,
//   and three never sets another value.
import * as esbuild from 'esbuild';
import fs from 'fs'; import path from 'path'; import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const THREE_DIR = path.join(ROOT, 'node_modules', 'three');
const pkg = JSON.parse(fs.readFileSync(path.join(THREE_DIR, 'package.json'), 'utf8'));
if (pkg.version !== '0.186.0') { console.error('three must be 0.186.0 (found ' + pkg.version + '): npm i -D three@0.186.0'); process.exit(1); }

// ---------------------------------------------------------------- source patches (pinned to three 0.186.0)
const PATCHES = [{
  file: /build[\\/]three\.webgpu(\.nodes)?\.js$/,
  edits: [["		this.swizzle = 'rgba';", "		this.swizzle = undefined; // SFO patch: see tools/build3/build.mjs"], ["		this.swizzle = 'rgba';", "		this.swizzle = undefined;"]],
}, {
  file: /examples[\\/]jsm[\\/]tsl[\\/]utils[\\/]TAAUtils\.js$/,
  edits: [
    ['getViewPosition, logarithmicDepthToViewZ,', 'getViewPosition, logarithmicDepthToViewZ, perspectiveDepthToViewZ,'],
    ['	const positionView = getViewPosition( uv, depth, previousCameraProjectionMatrixInverse );',
      '	let positionView;\n' +
      '	if ( builder.renderer.reversedDepthBuffer === true && builder.renderer.logarithmicDepthBuffer !== true && camera.isOrthographicCamera !== true ) {\n' +
      '		// SFO patch (tools/build3/build.mjs): reversed depth -> view z, then the view ray through uv (depth 1 = near plane on both backends)\n' +
      '		const viewZ = perspectiveDepthToViewZ( depth, cameraNearFar.x, cameraNearFar.y );\n' +
      '		const ray = getViewPosition( uv, float( 1 ), previousCameraProjectionMatrixInverse );\n' +
      '		positionView = ray.mul( viewZ.div( ray.z ) );\n' +
      '	} else {\n' +
      '		positionView = getViewPosition( uv, depth, previousCameraProjectionMatrixInverse );\n' +
      '	}'],
  ],
}];
const patchPlugin = { name: 'sfo-three-patches', setup(b) {
  b.onLoad({ filter: /(TAAUtils\.js|three\.webgpu(\.nodes)?\.js)$/ }, async (args) => {
    const P = PATCHES.find(p => p.file.test(args.path)); if (!P) return null;
    let src = await fs.promises.readFile(args.path, 'utf8');
    for (const [a, c] of P.edits) { if (!src.includes(a)) throw new Error('three.js patch target not found in ' + args.path + ': ' + a.slice(0, 80)); src = src.replace(a, c); }
    return { contents: src, loader: 'js' };
  });
} };

const vendorDir = path.join(ROOT, 'vendor', 'three');
fs.mkdirSync(vendorDir, { recursive: true });
const common = { entryPoints: [path.join(ROOT, 'tools', 'build3', 'three-entry.js')], bundle: true, format: 'esm', target: 'es2020', legalComments: 'none', logLevel: 'warning', plugins: [patchPlugin] };
const banner = '/* three.js r186 (npm three@0.186.0), MIT licence: see LICENSE in this folder. WebGPURenderer + TSL + CSMShadowNode, GTAO, TRAA, Bloom, FXAA, SMAA. Patched: TAAUtils samplePreviousDepth (reversed depth), GPUTextureViewDescriptor swizzle (see tools/build3/build.mjs). Built by tools/build3/build.mjs */';
const vendorOut = path.join(vendorDir, 'three.module.js'), debugOut = path.join(vendorDir, 'three.debug.js');
await esbuild.build({ ...common, minify: true, outfile: vendorOut, banner: { js: banner } });
await esbuild.build({ ...common, minify: false, outfile: debugOut, banner: { js: banner } });
fs.copyFileSync(path.join(THREE_DIR, 'LICENSE'), path.join(vendorDir, 'LICENSE'));
fs.writeFileSync(path.join(vendorDir, 'VERSION.json'), JSON.stringify({ package: 'three', version: pkg.version, esbuild: esbuild.version, patches: ['TAAUtils.samplePreviousDepth (reversed depth)', 'GPUTextureViewDescriptor.swizzle (undefined)'], built: new Date().toISOString(), bytes: fs.statSync(vendorOut).size }, null, 1) + '\n');
console.log('vendor/three/three.module.js', fs.statSync(vendorOut).size, 'bytes; three.debug.js', fs.statSync(debugOut).size, 'bytes');

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
  await esbuild.build({ entryPoints: [J('live', 'entry.js')], bundle: true, format: 'esm', minify: true, target: 'es2020', outfile: appOut, plugins: [plugin, patchPlugin], logLevel: 'warning' });
  // the MSDF sign atlas, where signs.js resolves it relative to the bundle (window.SFO_ASSET_BASE overrides)
  const aDir = path.join(path.dirname(appOut), 'assets'); fs.mkdirSync(aDir, { recursive: true });
  for (const f of fs.readdirSync(J('three', 'assets'))) fs.copyFileSync(J('three', 'assets', f), path.join(aDir, f));
  console.log('out/build3/live3.bundle.js', fs.statSync(appOut).size, 'bytes, + assets/', fs.readdirSync(aDir).join(', '));
}
