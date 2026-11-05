// livetest.mjs job (engine close-out round 2, curtain-wall glass A/B): js/three/dev/glasstest.html in ONE page load,
// then window.__glass.set() per variant (A/B weights x = round-3 inputs, y / z / w = reflection / interior / frame; IBL
// ground albedo) and a screenshot each: <OUT>/glass_<name>.png + <OUT>/glass.json (light inputs per variant).
//   SOFTGL=1 W=960 H=540 OUT=out/engine_r3/glass node livetest.mjs tools/build3/job_glass.mjs
// GLASSQ= extra query for the page (e.g. conc=0.36,0.35,0.33 from the app's debugInfo apronAlb).
// GV=<file.json>: instead of VARIANTS, a list [[name, setOpts], ...] passed to window.__glass.set() in order (ab, galb,
// fog, cam [yaw, pitch, dist, tgt], F0, T; settings persist between entries), e.g. out/engine_r3/glassdev/v1.json;
// measure with tools/build3/glass_meas.py dev <OUT>.
import fs from 'fs'; import path from 'path';
const FIELD = [0.3027, 0.2749, 0.2106], PAVED = [0.38, 0.37, 0.345]; // IBL ground: app's airfield mean / review finding's paved mean
const VARIANTS = [
  ['old', [1, 1, 1, 1], FIELD], ['old_paved', [1, 1, 1, 1], PAVED],
  ['old_refl', [1, 1, 0, 0], FIELD], ['old_hall', [1, 0, 1, 0], FIELD], ['old_frame', [1, 0, 0, 1], FIELD],
  ['new', [0, 1, 1, 1], FIELD], ['new_paved', [0, 1, 1, 1], PAVED],
  ['new_refl', [0, 1, 0, 0], FIELD], ['new_hall', [0, 0, 1, 0], FIELD], ['new_frame', [0, 0, 0, 1], FIELD],
];
export default async ({ page, shot, base, OUT }) => {
  const res = { err: [], variants: {} }; const save = () => fs.writeFileSync(path.join(OUT, 'glass.json'), JSON.stringify(res, null, 1));
  page.on('console', m => { if (m.type() === 'error') res.err.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => res.err.push(String(e.message).slice(0, 300)));
  const t0 = Date.now();
  await page.goto(base + 'js/three/dev/glasstest.html?n=4' + (process.env.GLASSQ ? '&' + process.env.GLASSQ : ''));
  await page.waitForFunction(() => window.__probe, null, { timeout: 0, polling: 500 });
  res.probe = await page.evaluate(() => window.__probe); res.loadS = (Date.now() - t0) / 1000; save();
  console.log('loaded', res.loadS, JSON.stringify(res.probe).slice(0, 600));
  if (!res.probe.ok) return;
  const list = process.env.GV ? JSON.parse(fs.readFileSync(process.env.GV, 'utf8')) : VARIANTS.map(([name, ab, galb]) => [name, { ab, galb, n: 8 }]);
  for (const [name, o] of list) {
    const tv = Date.now();
    res.variants[name] = await page.evaluate((o) => window.__glass.set(o), o);
    res.variants[name].s = (Date.now() - tv) / 1000; await shot('glass_' + name); save();
    console.log(name, res.variants[name].s, 's');
  }
};
