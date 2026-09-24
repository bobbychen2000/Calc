import fs from 'fs';
import { buildLive } from '../js/livedata.js';
export default async function ({ launch, registerStill }) {
  const W = +(process.env.W || 3840), H = +(process.env.H || 2160);
  const live = buildLive(fs.readFileSync('live/metar.txt', 'utf8'), fs.readFileSync('live/adsb.csv', 'utf8'), 1790185885000);
  const app = await launch({ W, H, msaa: +(process.env.MSAA ?? 4), shadowRes: 4096, env: live.env, live });
  await app.page.evaluate((l) => window.setupShots(l), live);
  registerStill('perf', W, H);
  const post = { exposure: 0.45, shutter: 0.5 };
  const picks = [[0, 4.5], [1, 3.5], [2, 5.0], [3, 4.5], [4, 12.0], [5, 4.0], [6, 5.5]];
  let idx = 0;
  for (const [i, t] of picks) {
    // warm + timed
    await app.page.evaluate(([i, t, post]) => window.renderShotStill(i, t, 'perf', 99, 30, post), [i, t, post]);
    const ms = await app.page.evaluate(([i, t, idx, post]) => window.renderShotStill(i, t + 0.033, 'perf', idx, 30, post), [i, t, idx, post]);
    console.log('shot', i, 't', t, Math.round(ms), 'ms'); idx++;
  }
  await app.close();
}
