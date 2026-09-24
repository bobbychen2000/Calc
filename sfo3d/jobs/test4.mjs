import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 1280, H = 720;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096 });
  registerStill('t4', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  const g = await app.page.evaluate(() => APP.world.gates.filter(x => x.pier === 'D' || x.pier === 'G').map(x => ({ id: x.id, nose: x.nose, dir: x.dir, wide: x.wide })));
  console.log(JSON.stringify(g.slice(0, 6)));
  const g0 = g.find(x => x.id.startsWith('G')) || g[0];
  const n = g0.nose, d = g0.dir;
  const cams = [
    { pos: P(n[0] - d[0] * 70 + d[1] * 45, n[1] - d[1] * 70 - d[0] * 45, 14), target: P(n[0] - d[0] * 15, n[1] - d[1] * 15, 5), fov: 0.8, near: 0.3, split: 2500, far: 150000, shadowSplits: [150, 800, 3500] },
    { pos: P(n[0] - d[0] * 30 - d[1] * 25, n[1] - d[1] * 30 + d[0] * 25, 6), target: P(n[0], n[1], 5), fov: 0.9, near: 0.3, split: 2500, far: 150000, shadowSplits: [120, 800, 3500] },
    { pos: P(-500, -700, 120), target: P(-800, -850, 5), fov: 0.9, near: 0.5, split: 2500, far: 150000, shadowSplits: [300, 1200, 3500] },
  ];
  for (let i = 0; i < cams.length; i++) {
    const r = await app.page.evaluate(([c, i]) => window.renderStill(c, 't4', i, { exposure: 0.45, shutter: 0 }), [cams[i], i]);
    console.log('frame', i, JSON.stringify(r));
  }
  await app.close();
}
