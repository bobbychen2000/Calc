import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 1280, H = 720;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096 });
  registerStill('t2', W, H);
  const cams = [
    { pos: stToWorld(-150, -350, 280), target: stToWorld(-800, -850, 10), fov: 0.9, near: 1, split: 3000, far: 150000, shadowSplits: [300, 1200, 4000] },
    { pos: stToWorld(-300, -700, 25), target: stToWorld(-560, -920, 40), fov: 0.8, near: 0.5, split: 2500, far: 150000, shadowSplits: [200, 900, 3500] },
    { pos: stToWorld(-1000, 300, 180), target: stToWorld(-1100, -750, 10), fov: 0.9, near: 1, split: 3000, far: 150000, shadowSplits: [300, 1200, 4000] },
    { pos: stToWorld(-400, 900, 120), target: stToWorld(-700, 1300, 15), fov: 0.9, near: 1, split: 3000, far: 150000, shadowSplits: [300, 1200, 4000] },
  ];
  for (let i = 0; i < cams.length; i++) {
    const r = await app.page.evaluate(([c, i]) => window.renderStill(c, 't2', i, { exposure: 0.45, shutter: 0 }), [cams[i], i]);
    console.log('frame', i, JSON.stringify(r));
  }
  await app.close();
}
