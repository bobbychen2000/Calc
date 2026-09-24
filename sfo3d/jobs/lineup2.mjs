import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 800, H = 450;
  const types = (process.env.TYPES || 'a20n,a21n,b738,b38m,b752,b763,b77w,b789,a359,b748,a388,e75l,crj9,bcs3').split(',');
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: types.map((t, i) => ({ type: t, s: -1700 + i * 100, t: 530, dir: [0, -1], liv: i })) });
  registerStill('l2', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  let idx = 0;
  for (let i = 0; i < types.length; i++) {
    const L = await app.page.evaluate((k) => { const ac = APP.scene.aircraft.find(a => a.id === 'T' + k); return [ac.T.L, ac.T.xMain, ac.T.Hc, ac.T.R]; }, i);
    const s = -1700 + i * 100, t = 530; const noseT = t - L[1]; const midT = noseT + L[0] * 0.5;
    const views = [
      { pos: P(s + L[0] * 0.62, noseT - L[0] * 0.42, L[2] + 1.0), target: P(s, midT - L[0] * 0.08, L[2] + 0.5), fov: 0.72 },
      { pos: P(s + L[0] * 1.15, midT, L[2] + 0.5), target: P(s, midT, L[2] + 1.0), fov: 0.62 },
      { pos: P(s + L[3] * 3.2, noseT - L[3] * 3.0, L[2] + L[3] * 0.9), target: P(s, noseT + L[3] * 0.9, L[2] + L[3] * 0.3), fov: 0.6 },
    ];
    for (const v of views) { const cam = { ...v, near: 0.2, split: 2500, far: 150000, shadowSplits: [120, 700, 3500] }; await app.page.evaluate(([c, idx]) => window.renderStill(c, 'l2', idx, { exposure: 0.45, shutter: 0 }), [cam, idx]); idx++; }
  }
  await app.close();
}
