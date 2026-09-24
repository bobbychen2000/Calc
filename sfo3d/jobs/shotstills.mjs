// render a few stills from each shot for review
import fs from 'fs';
import { buildLive } from '../js/livedata.js';
export default async function ({ launch, registerStill }) {
  const W = +(process.env.W || 1280), H = +(process.env.H || 720);
  const live = buildLive(fs.readFileSync('live/metar.txt', 'utf8'), fs.readFileSync('live/adsb.csv', 'utf8'), 1790185885000);
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096, env: live.env, live });
  const shots = await app.page.evaluate((l) => window.setupShots(l), live);
  console.log(JSON.stringify(shots));
  registerStill('ss', W, H);
  const post = { exposure: 0.43, shutter: 0.5, bloom: 0.012, vignette: 0.24, grain: 0.008, sat: 1.1, gain: [1.02, 1.0, 0.97], lift: [-0.002, -0.002, 0.0] };
  const sel = process.env.SHOTS ? process.env.SHOTS.split(',').map(Number) : shots.map((_, i) => i);
  const fracs = process.env.FRACS ? process.env.FRACS.split(',').map(Number) : [0.1, 0.5, 0.9];
  let idx = 0;
  for (const i of sel) for (const fr of fracs) {
    const t = shots[i].dur * fr;
    const ms = await app.page.evaluate(([i, t, idx, post]) => window.renderShotStill(i, t, 'ss', idx, 30, post), [i, t, idx, post]);
    console.log('shot', i, shots[i].name, 't', t.toFixed(2), '->', 'ss_' + idx, Math.round(ms), 'ms');
    idx++;
  }
  await app.close();
}
