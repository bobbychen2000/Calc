// Stand-in for js/world/world.js under live3.html's import map: everything is the original module (CITY_RECT,
// CITYFAR_RECT, ... via the /js/three/ scope) except bakeGround, whose GLSL bakes become the TSL bakes of
// js/three/ground.js GroundBakes, run by the three.js renderer (queued until it has initialised).
export * from '../../world/world.js';
export function bakeGround(R, world, log = () => { }, opts = {}) {
  if (!R.requestBake) throw new Error('bakeGround: not the three.js renderer');
  R.requestBake(world, opts);
  // the old bake set these; the app does not read them afterwards, but keep the fields present
  world.bakes = world.bakes || { three: true };
}
