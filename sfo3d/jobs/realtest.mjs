// Render imported models side by side: front-quarter, side, and close cockpit views
import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = +(process.env.W || 960), H = +(process.env.H || 540);
  const list = (process.env.LIST || 'b738:b738,a320:a320,b789:b788,e75l:e75l,bcs3:bcs3,a321:a321').split(',').map(s => s.split(':'));
  const livs = (process.env.LIVS || '0,1,2,3,4,5').split(',').map(Number);
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: list.map(([t, m], i) => ({ type: t, model: m === '-' ? null : m, s: -1700 + i * 110, t: 530, dir: [0, -1], liv: livs[i % livs.length] })) });
  const n = await app.page.evaluate(() => window.modelsReady());
  console.log('models ready', n);
  registerStill('rt', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  const views = (process.env.VIEWS || 'fq,side,close').split(',');
  let idx = 0;
  for (let i = 0; i < list.length; i++) {
    const L = await app.page.evaluate((k) => { const ac = APP.scene.aircraft.find(a => a.id === 'T' + k); return [ac.T.L, ac.T.xMain, ac.T.Hc, ac.T.R, ac.T.Ln, ac.pos[1]]; }, i);
    const s = -1700 + i * 110, t = 530; const noseT = t - L[1]; const R = L[3], Ln = L[4], Hc = L[2] + L[5];
    const V = {
      fq: [P(s + R * 4.2, noseT - R * 4.5, Hc + R * 1.3), P(s, noseT + Ln * 0.8, Hc + R * 0.2), 0.62],
      side: [P(s + L[0] * 0.95, t - L[1] + L[0] * 0.48, Hc + R * 0.4), P(s, t - L[1] + L[0] * 0.48, Hc - R * 0.3), 0.62],
      close: [P(s + R * 1.9, noseT - R * 1.6, Hc + R * 1.35), P(s, noseT + Ln * 0.45, Hc + R * 0.55), 0.62],
      rear: [P(s - L[0] * 0.5, t - L[1] + L[0] * 1.05, Hc + R * 2.5), P(s, t - L[1] + L[0] * 0.5, Hc), 0.7],
    };
    for (const v of views) {
      const [cp, ct, fov] = V[v];
      const cam = { pos: cp, target: ct, fov, near: 0.2, split: 2500, far: 150000, shadowSplits: [80, 700, 3500] };
      await app.page.evaluate(([c, idx]) => window.renderStill(c, 'rt', idx, { exposure: 0.45, shutter: 0 }), [cam, idx]);
      console.log('rt_' + idx, list[i].join(':'), v); idx++;
    }
  }
  await app.close();
}
