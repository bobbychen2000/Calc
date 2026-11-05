// Entry for the vendored three.js r186 bundle used by the new renderer (live3.html).
// three.js is MIT (node_modules/three/LICENSE, copied to vendor/three/LICENSE by build.mjs).
// One ES module = WebGPURenderer (with its automatic WebGL 2 fallback) + TSL + the add-ons the renderer uses, so the
// page needs no bare-specifier resolution and no CDN (the artifact CSP blocks CDN fetches of non-script assets).
export * from 'three/webgpu';
export { CSMShadowNode } from 'three/addons/csm/CSMShadowNode.js';
export { ao, default as GTAONode } from 'three/addons/tsl/display/GTAONode.js';
export { traa, default as TRAANode } from 'three/addons/tsl/display/TRAANode.js';
export { bloom, default as BloomNode } from 'three/addons/tsl/display/BloomNode.js';
export { fxaa } from 'three/addons/tsl/display/FXAANode.js';
export { smaa } from 'three/addons/tsl/display/SMAANode.js';
// glTF 2.0 loader for the Blender-built building assets (js/three/buildings3d.js, data/buildings3d/*.glb); it imports
// 'three' (build/three.module.js), which shares build/three.core.js with three/webgpu, so its classes are the same ones
export { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
export const THREE_REVISION_PINNED = '186';
