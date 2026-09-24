export default async function ({ launch, startVideo, endVideo, OUT }) {
  const W = +(process.env.W || 3840), H = +(process.env.H || 2160), fps = 30;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096 });
  await app.page.evaluate(() => window.setupShots(null));
  const shot = +(process.env.SHOT || 4), f0 = +(process.env.F0 || 300), n = +(process.env.N || 24);
  await startVideo('v', W, H, fps, OUT + '/vidtest.mp4', 16, process.env.PRESET || 'medium');
  const t0 = Date.now();
  const r = await app.page.evaluate(([s, f0, f1]) => window.renderShotFrames(s, f0, f1, 'v', 30, { exposure: 0.45, shutter: 0.5, bloom: 0.012, vignette: 0.22, grain: 0.01 }), [shot, f0, f0 + n]);
  await endVideo('v');
  console.log('frames', n, 'wall per frame', ((Date.now() - t0) / n / 1000).toFixed(2), 's', JSON.stringify(r));
  await app.close();
}
