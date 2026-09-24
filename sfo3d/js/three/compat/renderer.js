// Stand-in for js/renderer.js under live3.html's import map: the app's `new Renderer(w, h, opts)` gets the three.js
// renderer (js/three/renderer3.js). sunTransmittance (CPU sun colour) is re-exported from the original module, which
// live3.html's import-map scope for /js/three/ resolves to the real file.
export { sunTransmittance } from '../../renderer.js';
export { Renderer3 as Renderer } from '../renderer3.js';
