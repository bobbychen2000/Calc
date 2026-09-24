// Apron equipment: high-mast floodlights (pole, head frame, luminaires), with night lamp sprites.
import { Geo } from '../geom.js';
import { m4 } from '../math.js';
import { GROUND_Y } from '../geo.js';

const G = GROUND_Y;
const GALV = [0.52, 0.53, 0.54, 1], E_GALV = [0.42, 0.65, 0, 0];
const CONC = [0.55, 0.54, 0.51, 1], E_CONC = [0.9, 0, 2, 0];
const DARK = [0.12, 0.12, 0.13, 1], E_DARK = [0.5, 0.3, 0, 0];
const LAMP = [1.0, 0.93, 0.82, 1], E_LAMP = [0.15, 0, 14, 0]; // mat 14: lit at night
export const MAST_H = 27;

export function buildMasts(masts) {
  const g = new Geo();
  const sprites = [];
  for (const [x, z] of masts) {
    const yaw = Math.atan2(-x - 900, -z - 300); // head frame roughly facing the terminal core
    const M = m4.mul(m4.translate(x, G, z), m4.rotY(yaw));
    g.cylinder(0.85, 0.7, 14, CONC, E_CONC, m4.translate(x, G, z), true);
    g.lathe([[0.34, 0.7], [0.3, 6], [0.22, 18], [0.16, MAST_H - 0.6]], 12, GALV, E_GALV, m4.translate(x, G, z), true);
    // head: service platform ring + frame bar + six luminaires tilted toward the ramp
    g.lathe([[0.2, MAST_H - 0.9], [1.25, MAST_H - 0.8], [1.25, MAST_H - 0.62], [0.2, MAST_H - 0.55]], 16, DARK, E_DARK, m4.translate(x, G, z), false);
    g.box([-2.1, MAST_H - 0.25, -0.12], [2.1, MAST_H + 0.05, 0.12], GALV, E_GALV, M);
    for (let i = 0; i < 6; i++) {
      const u = -1.75 + i * 0.7; const tilt = -0.55 - (i % 2) * 0.2;
      const L = m4.mul(M, m4.mul(m4.translate(u, MAST_H - 0.1, 0.25), m4.rotX(tilt)));
      g.box([-0.3, -0.12, 0], [0.3, 0.12, 0.55], DARK, E_DARK, L);
      g.box([-0.26, -0.13, 0.04], [0.26, -0.11, 0.51], LAMP, E_LAMP, L, ['ny']);
      const p = m4.xform(L, [0, -0.2, 0.3]); sprites.push({ p, c: [1, 0.9, 0.75], i: 900, s: 0.5, dir: m4.xdir(L, [0, -1, 0.3]), k: 2 });
    }
  }
  return { geo: g.data(), sprites };
}
