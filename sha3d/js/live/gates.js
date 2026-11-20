// sha3d gates extension: OWNED BY THE GATES PACKAGE (stands from window.SHA_STANDS, jet bridges, VDGS, GSE, remote-stand
// buses and stairs). This stub registers nothing visible. Use js/live/ext.js: buildWorld(ctx) (ctx.stands = SHA_STANDS;
// return {items, gates, sprites}), pavement(api) for stand pads outside the OSM aprons, start(app) to attach a live
// system as app.scene.gateSys (items(nowMs) drawn each frame). Fork sfo3d@e3218d6 js/live/gates.js with injected data
// (arch.md R4), not module-scope imports.
import { registerExtension } from './ext.js';
registerExtension({ name: 'gates', order: 30 });
