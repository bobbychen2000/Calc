// sha3d markings extension: OWNED BY THE MARKINGS PACKAGE (CAAC MH 5001-2021 runway / taxiway / apron markings, and
// signs). This stub registers nothing visible. Use js/live/ext.js: shaderChunks.sha_ground_paint (procedural paint in the
// ground shader; signature in js/shaders/ground.js) and / or buildWorld (decal ribbons, sign meshes) + groundUniforms.
// Parameters: docs/phase1/standards_refs.md (CAAC values with clause numbers) or a clearly marked 'inf' placeholder; no
// FAA constants (sfo3d's js/live/markings.js, js/live/signs.js and the runway marks in its js/shaders/ground.js are FAA).
import { registerExtension } from './ext.js';
registerExtension({ name: 'markings', order: 20 });
