// Render the full video. env: W,H,FPS,OUT_NAME,SHOTS (subset), CRF, PRESET, LIVE (json file)
import fs from 'fs';
import { buildLive } from '../js/livedata.js';
export default async function ({ launch, startVideo, endVideo, OUT }) {
  const W = +(process.env.W || 960), H = +(process.env.H || 540), fps = +(process.env.FPS || 30);
  const live = process.env.NOLIVE ? null : buildLive(fs.readFileSync('live/metar.txt', 'utf8'), fs.readFileSync('live/adsb.csv', 'utf8'), +(process.env.SNAP_MS || 1790185885000));
  const app = await launch({ W, H, msaa: +(process.env.MSAA ?? 4), shadowRes: +(process.env.SHADOW || 4096), env: live ? live.env : undefined, live });
  const shots = await app.page.evaluate((l) => window.setupShots(l), live);
  const sel = process.env.SHOTS ? process.env.SHOTS.split(',').map(Number) : shots.map((_, i) => i);
  const post = { exposure: +(process.env.EXPOSURE || 0.43), shutter: 0.5, bloom: 0.012, vignette: 0.24, grain: 0.008, sat: 1.1, gain: [1.02, 1.0, 0.97], lift: [-0.002, -0.002, 0.0] };
  const name = process.env.OUT_NAME || 'preview';
  const perShot = !!process.env.PER_SHOT;
  if (!perShot) await startVideo('v', W, H, fps, `${OUT}/${name}.mp4`, +(process.env.CRF || 18), process.env.PRESET || 'medium');
  const t0 = Date.now(); let total = 0;
  for (const i of sel) {
    const n = Math.round(shots[i].dur * fps);
    const file = `${OUT}/${name}_shot${i}.mp4`;
    if (perShot) { if (fs.existsSync(file) && !process.env.FORCE) { console.log('skip existing', file); continue; } await startVideo('v', W, H, fps, file + '.part.mp4', +(process.env.CRF || 18), process.env.PRESET || 'medium'); }
    const chunk = 30; let f = 0; const ts = Date.now();
    while (f < n) {
      const f1 = Math.min(n, f + chunk);
      await app.page.evaluate(([s, a, b, fps, post]) => window.renderShotFrames(s, a, b, 'v', fps, post), [i, f, f1, fps, post]);
      f = f1; total += f1 - (f1 - chunk < 0 ? 0 : f1 - chunk);
      process.stdout.write(`shot ${i} ${f}/${n} ${((Date.now() - ts) / f / 1000).toFixed(2)}s/f\r`);
    }
    if (perShot) { await endVideo('v'); fs.renameSync(file + '.part.mp4', file); }
    console.log(`\nshot ${i} done: ${n} frames in ${((Date.now() - ts) / 1000).toFixed(0)}s`);
  }
  if (!perShot) await endVideo('v');
  console.log('ALL DONE in', ((Date.now() - t0) / 60000).toFixed(1), 'min');
  await app.close();
}
