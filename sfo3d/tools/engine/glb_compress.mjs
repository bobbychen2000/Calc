// Post-process a Blender-exported .glb for the web runtime (docs/research/engine.md, "Blender role"):
//   textures -> KTX2 / Basis Universal (KHR_texture_basisu; ETC1S for AO/lightmaps, UASTC optional),
//   geometry -> meshopt compression (EXT_meshopt_compression, decoded by three.js' meshopt_decoder).
// Encoders: glTF-Transform 4.5 (MIT), ktx2-encoder 0.6 (MIT, basis_universal WASM), meshoptimizer (MIT).
// The npm packages live outside the repo (third-party downloads): pass their node_modules parent via MODULES.
//
// Run: MODULES=refs/cache/engine/node node tools/engine/glb_compress.mjs in.glb out.glb [--uastc]
import { pathToFileURL } from 'url';
import path from 'path';
import fs from 'fs';

const MOD = path.resolve(process.env.MODULES || 'refs/cache/engine/node');
// resolve an ESM entry point (package "exports": node > import > default) under MOD/node_modules
function resolveEsm(name) {
  const parts = name.split('/'); const pkg = name.startsWith('@') ? parts.slice(0, 2).join('/') : parts[0];
  const sub = '.' + name.slice(pkg.length); const dir = path.join(MOD, 'node_modules', pkg);
  const pj = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'));
  let e = pj.exports; if (typeof e === 'string' || (e && !Object.keys(e).some((k) => k.startsWith('.')))) e = { '.': e };
  let t = e ? e[sub] : null;
  const pick = (x) => typeof x === 'string' ? x : x && (pick(x.node) || pick(x.import) || pick(x.default));
  t = pick(t) || (sub === '.' ? (pj.module || pj.main || 'index.js') : sub);
  return path.join(dir, t);
}
const load = async (name) => import(pathToFileURL(resolveEsm(name)).href);

const [inp, out] = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const uastc = process.argv.includes('--uastc');
const { NodeIO } = await load('@gltf-transform/core');
const { ALL_EXTENSIONS, EXTMeshoptCompression, KHRTextureBasisu } = await load('@gltf-transform/extensions');
const { meshopt, dedup, prune } = await load('@gltf-transform/functions');
const { MeshoptEncoder, MeshoptDecoder } = await load('meshoptimizer');
const { ktx2 } = await load('ktx2-encoder/gltf-transform');
const sharp = (await load('sharp')).default;

await MeshoptEncoder.ready; await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(inp);
const imageDecoder = async (buffer) => {
  const { data, info } = await sharp(buffer).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data: new Uint8Array(data), width: info.width, height: info.height };
};
const t0 = Date.now();
await doc.transform(dedup(), prune(),
  ktx2({ isUASTC: uastc, generateMipmap: true, qualityLevel: 128, compressionLevel: 2, imageDecoder }),
  meshopt({ encoder: MeshoptEncoder, level: 'medium' }));
await io.write(out, doc);
const inB = fs.statSync(inp).size, outB = fs.statSync(out).size;
const tex = doc.getRoot().listTextures().map((t) => ({ name: t.getName(), mime: t.getMimeType(), bytes: t.getImage().byteLength }));
const used = doc.getRoot().listExtensionsUsed().map((e) => e.extensionName);
console.log(JSON.stringify({ in: inp, out, inBytes: inB, outBytes: outB, ratio: +(outB / inB).toFixed(3), mode: uastc ? 'UASTC' : 'ETC1S', seconds: (Date.now() - t0) / 1000, extensionsUsed: used, textures: tex }, null, 1));
