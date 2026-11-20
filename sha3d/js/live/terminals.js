// sha3d terminals extension: OWNED BY THE TERMINALS PACKAGE (T1, T2 and piers, the control tower(s), hangars, the
// business-aviation terminal). This stub registers nothing visible. Use js/live/ext.js: claimBuildings(airport) returns
// the building ids (data/sha_airport.js buildings[].id, e.g. 'osm:way/93184730' = T1, 'osm:relation/21913345' = T2) and
// 'tower' for the control-tower stand-in that you draw yourself; buildWorld(ctx) returns the replacement items and
// anchors (e.g. {tower: {pos, eyeY}} for the tower view).
import { registerExtension } from './ext.js';
registerExtension({ name: 'terminals', order: 40 });
