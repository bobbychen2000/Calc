// livetest.mjs job (close-out round 3, buildings track): live3.html views of the Blender assets that also LOG THE CAMERA RIG
// (target, yaw, pitch, dist, fov -> eye) and the sun (SFO.env().sun) per view, so a Cycles reference can be rendered from the
// same camera under the same sun (buildings-5: the BA-B glass was compared with a Cycles view of a different side / light).
//   flock out/.heavy.lock env SOFTGL=1 W=960 H=540 OUT=<dir> QS="mode=snapshot&res=1&tier=low&b3donly=domestic" \
//     VIEWS="pierB=gate:B20,110,1,12;i4like=look:..." node livetest.mjs tools/blender/c3_app_views_job.mjs
// VIEWS as in tools/blender/b3d_views_job.mjs (look / gate / tower); FRAMES frames per view (default 8).
// Output: <OUT>/c3_<name>.png and <OUT>/c3_info.json {name: {view, rig: {target, yaw_deg, pitch_deg, dist, fov_deg, eye}, sun}}.
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const views = (process.env.VIEWS || '').split(';').filter(Boolean).map(v => { const i = v.indexOf('='); return [v.slice(0, i), v.slice(i + 1)]; });
  const info = {}; const save = () => fs.writeFileSync(path.join(OUT, 'c3_info.json'), JSON.stringify(info, null, 1));
  const t0 = Date.now();
  await page.goto(base + 'live3.html?' + (process.env.QS || 'mode=snapshot&res=1'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 900000 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
  await page.waitForFunction(() => !SFO.R.b3d || SFO.R.b3d.done, null, { timeout: 0, polling: 1000 });
  console.log('ready in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  for (const [name, v] of views) {
    const [kind, arg] = v.split(':');
    const ok = await page.evaluate(([k, a]) => {
      const q = SFO.qa; const args = a ? a.split(',') : [];
      if (k === 'gate') return q.gate(args[0], +(args[1] || 38), +(args[2] || 1), +(args[3] || 9));
      if (k === 'look') { q.look([+args[0], +args[1], +args[2]], +args[3], +args[4], +args[5], +(args[6] || 50)); return true; }
      if (k === 'tower') return q.tower(+(args[0] || 170), +(args[1] || 235), +(args[2] || 11));
      return false;
    }, [kind, arg]);
    if (!ok) { console.log('view failed', v); continue; }
    await page.evaluate(() => { window.__b3dF = SFO.R.frames; });
    await page.waitForFunction(() => { const B = SFO.R.b3d; return !B || !B.settled || (SFO.R.frames > window.__b3dF + 12 && B.settled()); }, null, { timeout: 0, polling: 500 });
    const f0 = await page.evaluate(() => SFO.R.frames); const n = +(process.env.FRAMES || 8);
    await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 200 });
    info[name] = await page.evaluate((v) => {
      const r = SFO.rig, cp = Math.cos(r.pitch), off = [cp * Math.sin(r.yaw), Math.sin(r.pitch), -cp * Math.cos(r.yaw)];   // js/live/controls.js
      const eye = r.camera ? r.camera().pos : r.target.map((t, i) => t + r.dist * off[i]);   // camera() also applies the ground clamp
      const e = SFO.env(); const s = e && e.sun ? e.sun : null;
      return { view: v, rig: { target: r.target.slice(), yaw_deg: r.yaw * 180 / Math.PI, pitch_deg: r.pitch * 180 / Math.PI, dist: r.dist, fov_deg: r.fov * 180 / Math.PI, eye },
        sun: s ? Object.fromEntries(Object.entries(s).filter(([k, x]) => typeof x === 'number' || Array.isArray(x))) : null };
    }, v);
    console.log(name, JSON.stringify(info[name])); save();
    await shot('c3_' + name);
  }
  save();
};
