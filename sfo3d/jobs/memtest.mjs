import fs from 'fs';
import { buildLive } from '../js/livedata.js';
export default async function ({ launch, startVideo, endVideo, OUT }) {
  const W = +(process.env.W || 1920), H = +(process.env.H || 1080);
  const live = buildLive(fs.readFileSync('live/metar.txt', 'utf8'), fs.readFileSync('live/adsb.csv', 'utf8'), 1790185885000);
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, env: live.env, live });
  const shots = await app.page.evaluate((l) => window.setupShots(l), live);
  const post = { exposure: 0.43, shutter: 0.5, bloom: 0.012 };
  await startVideo('v', W, H, 30, `${OUT}/memtest.mp4`, 18, 'medium');
  for (let f = 0; f < 16; f += 4) await app.page.evaluate(([a, b, post]) => window.renderShotFrames(0, a, b, 'v', 30, post), [f, f + 4, post]);
  await endVideo('v'); await app.close();
}
