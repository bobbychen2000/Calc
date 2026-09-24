import { stToWorld } from '../js/geo.js';
export default async function ({ launch, registerStill }) {
  const W = 1280, H = 720;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, testAircraft: [
    { type: 'wide', s: 1200, t: 235, dir: [-1, 0], gear: 1, flaps: 0.8, liv: 0, landing: true, strobe: true },
    { type: 'narrow', s: 1100, t: 6.4, dir: [-1, 0], gear: 1, flaps: 0.6, spoilers: 1, liv: 1, landing: true },
    { type: 'mid', s: 900, t: 385, dir: [-1, 0], gear: 1, liv: 2 },
  ] });
  registerStill('t3', W, H);
  const P = (s, t, h) => stToWorld(s, t, h);
  const cams = [
    { pos: P(1150, 280, 12), target: P(1225, 235, 8), fov: 0.75, near: 0.3, split: 2500, far: 150000, shadowSplits: [150, 800, 3500] },
    { pos: P(1060, -20, 6), target: P(1100, 6.4, 4), fov: 0.8, near: 0.3, split: 2500, far: 150000, shadowSplits: [150, 800, 3500] },
    { pos: P(870, 420, 20), target: P(920, 385, 6), fov: 0.8, near: 0.3, split: 2500, far: 150000, shadowSplits: [150, 800, 3500] },
    { pos: P(-450, -650, 60), target: P(-700, -800, 5), fov: 0.9, near: 0.5, split: 2500, far: 150000, shadowSplits: [250, 1000, 3500] },
  ];
  for (let i = 0; i < cams.length; i++) {
    const r = await app.page.evaluate(([c, i]) => window.renderStill(c, 't3', i, { exposure: 0.45, shutter: 0 }), [cams[i], i]);
    console.log('frame', i, JSON.stringify(r));
  }
  await app.close();
}
