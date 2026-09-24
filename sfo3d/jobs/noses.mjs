import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = +(process.env.W || 640), H = +(process.env.H || 360);
  const types = (process.env.TYPES || 'a20n,b738,b752,b763,b77w,b789,a359,b748,a388,e75l,crj9,bcs3').split(',');
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: types.map((t, i) => ({ type: t, s: -1700 + i * 110, t: 530, dir: [0, -1], liv: i })) });
  registerStill('ns', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  let idx = 0;
  for (let i = 0; i < types.length; i++) {
    const L = await app.page.evaluate((k) => { const ac = APP.scene.aircraft.find(a => a.id === 'T' + k); return [ac.T.L, ac.T.xMain, ac.T.Hc, ac.T.R, ac.T.Ln, ac.pos[1]]; }, i);
    const s = -1700 + i * 110, t = 530; const noseT = t - L[1];
    const V = process.env.VIEW || 'fq'; const R = L[3], Ln = L[4], Hc = L[2] + L[5];
    const views = {
      fq: [P(s + R * 3.4, noseT - R * 3.4, Hc + R * 1.5), P(s, noseT + Ln * 0.42, Hc + R * 0.75), 0.5],
      side: [P(s + R * 6.5, noseT + Ln * 0.55, Hc + R * 0.9), P(s, noseT + Ln * 0.55, Hc + R * 0.55), 0.45],
      front: [P(s, noseT - R * 6, Hc + R * 1.3), P(s, noseT + Ln * 0.3, Hc + R * 0.55), 0.45],
      close: [P(s + R * 1.6, noseT - R * 1.0, Hc + R * 1.45), P(s, noseT + Ln * 0.5, Hc + R * 0.85), 0.62],
    };
    const [cp, ct, fov] = views[V];
    const cam = { pos: cp, target: ct, fov, near: 0.2, split: 2500, far: 150000, shadowSplits: [80, 700, 3500] };
    await app.page.evaluate(([c, idx]) => window.renderStill(c, 'ns', idx, { exposure: 0.45, shutter: 0 }), [cam, idx]); idx++;
  }
  await app.close();
}
