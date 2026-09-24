import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 800, H = 450;
  const types = (process.env.TYPES || 'a20n,a21n,b738,b38m,b752,b763,b77w,b789,a359,b748,a388,e75l,crj9,bcs3').split(',');
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: types.map((t, i) => ({ type: t, s: -1200, t: 560, dir: [0, -1], liv: i })) });
  registerStill('l3', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  let idx = 0;
  for (let i = 0; i < types.length; i++) {
    const L = await app.page.evaluate((k) => { APP.scene.aircraft.forEach(a => { if (a.id.startsWith('T')) a.visible = a.id === 'T' + k; }); const ac = APP.scene.aircraft.find(a => a.id === 'T' + k); return [ac.T.L, ac.T.xMain, ac.T.Hc, ac.T.R, ac.T.wing.span]; }, i);
    const s = -1200, t = 560; const noseT = t - L[1]; const midT = noseT + L[0] * 0.5;
    const views = [
      { pos: P(s - L[0] * 0.7, noseT - L[0] * 0.45, L[2] + 2.5), target: P(s, midT - L[0] * 0.1, L[2] + 1), fov: 0.75 },
      { pos: P(s + L[0] * 0.55, t + L[0] * 0.75, L[2] + L[0] * 0.25), target: P(s, midT, L[2]), fov: 0.75 },
    ];
    for (const v of views) { const cam = { ...v, near: 0.2, split: 2500, far: 150000, shadowSplits: [150, 700, 3500] }; await app.page.evaluate(([c, idx]) => window.renderStill(c, 'l3', idx, { exposure: 0.45, shutter: 0 }), [cam, idx]); idx++; }
  }
  await app.close();
}
