import { stToWorld } from '../js/geo.js';
// render each aircraft type individually, 3/4 front view and side view
export default async function ({ launch, registerStill }) {
  const W = 960, H = 540;
  const types = (process.env.TYPES || 'a20n,a21n,b738,b38m,b752,b763,b77w,b789,a359,b748,a388,e75l,crj9,bcs3').split(',');
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: types.map((t, i) => ({ type: t, s: -1700 + i * 95, t: 530, dir: [0, -1], liv: i })) });
  registerStill('lu', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  let idx = 0;
  for (let i = 0; i < types.length; i++) {
    const L = await app.page.evaluate((k) => { const ac = APP.scene.aircraft.find(a => a.id === 'T' + k); ac.lod = 1; return [ac.T.L, ac.T.xMain, ac.T.Hc]; }, i);
    const s = -1700 + i * 95, t = 530; // aircraft main gear at (s,t), nose toward -t
    const nose = [s, t - L[1]];
    const views = process.env.VIEW === 'side' ? [[s + L[0] * 0.95, t - L[1] + L[0] * 0.5, L[2] + 2]] : [[s + L[0] * 0.55, t - L[1] - L[0] * 0.55, L[2] + 1.5]];
    for (const v of views) {
      const cam = { pos: P(v[0], v[1], v[2]), target: P(s, t - L[0] * 0.18, L[2]), fov: 0.75, near: 0.3, split: 2500, far: 150000, shadowSplits: [120, 700, 3500] };
      await app.page.evaluate(([c, idx]) => window.renderStill(c, 'lu', idx, { exposure: 0.45, shutter: 0 }), [cam, idx]); idx++;
    }
  }
  console.log('rendered', idx);
  await app.close();
}
