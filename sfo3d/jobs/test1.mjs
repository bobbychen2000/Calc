import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 1280, H = 720;
  const app = await launch({ W, H, msaa: 4, shadowRes: 2048 });
  registerStill('t1', W, H);
  const cams = [
    { pos: stToWorld(3600, 120, 650), target: stToWorld(-300, -250, 0), fov: 0.85, near: 1, split: 3000, far: 150000 },
    { pos: stToWorld(1760, 290, 22), target: stToWorld(900, 235, 3), fov: 0.7, near: 0.5, split: 2500, far: 150000 },
    { pos: stToWorld(-400, -400, 900), target: stToWorld(-800, -850, 0), fov: 0.9, near: 1, split: 3000, far: 150000 },
  ];
  for (let i = 0; i < cams.length; i++) {
    const r = await app.page.evaluate(([c, i]) => window.renderStill(c, 't1', i, { exposure: 0.45, shutter: 0 }), [cams[i], i]);
    console.log('frame', i, JSON.stringify(r));
  }
  await app.close();
}
