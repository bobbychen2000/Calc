// livetest.mjs job: the 3-D tower in the three.js app (live3.html, ?b3donly=tower) under photo-matched sun and camera,
// for the tower review (docs/research/buildings3d.md, tower section): shaft / sky and cab-glass / sky luminance ratios
// against the reference photos t2 / t4 (Famartin 2025-08-12, CC BY-SA 4.0; reference only; the ratios are read offline on
// the PNGs, numbers in docs/research/buildings3d.md), and the app's tower view (eye height, in-cab glass state of the loaded family).
//   flock out/.heavy.lock env SOFTGL=1 W=960 H=540 OUT=out/buildings3d/app QS="mode=snapshot&res=1&b3donly=tower" \
//     node livetest.mjs tools/blender/tower_app_job.mjs
// VIEWS: ';'-separated name=t|look (t: ISO time of the environment clock or '-' to keep it; look: x,y,z,yaw,pitch,dist,fov as
// SFO.qa.look, or 'towercam' for the app's tower view). Default: the t2 and t4 photo cameras at the photo times (F2 heights),
// the airside view of the review (t2like) and the tower view. FRAMES: TRAA frames per view (default 8).
// Output: <OUT>/tapp_<name>.png and <OUT>/tower_app_info.json (b3d info, tower anchors, towerPos / eyeY, camera, in-cab state).
import fs from 'fs'; import path from 'path';
const DEF = [
  // t2: camera (-527.4, 479.9), 263.1 m from the axis at bearing 126.1, ~8.1 m above grade (F2: 12 deg below the rim);
  // target the axis 36 m up: dist 264.6, pitch -6.05; vertical fov 17 (f 8596 px of 2560) -> 18
  't2=2025-08-12T18:57:15Z|-740.5,39,324.5,126.1,-6.05,264.6,18',
  // t4: camera (-769.2, 248.6), 81.1 m at bearing 339.3, ~16.6 m (F2); target 38 m: dist 83.9, pitch -14.8; fov 44 -> 46
  't4=2025-08-12T16:10:05Z|-740.5,41,324.5,339.3,-14.8,83.9,46',
  // the review's airside view at the snapshot time (sun behind the camera)
  't2like=-|-740.5,33,324.5,126.6,-5.5,193,30',
  'towercam=-|towercam',
];
export default async ({ page, shot, base, OUT }) => {
  const views = (process.env.VIEWS ? process.env.VIEWS.split(';') : DEF).filter(Boolean).map(v => { const i = v.indexOf('='); const [t, l] = v.slice(i + 1).split('|'); return [v.slice(0, i), t, l]; });
  const t0 = Date.now();
  await page.goto(base + 'live3.html?' + (process.env.QS || 'mode=snapshot&res=1&b3donly=tower'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 900000 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
  await page.waitForFunction(() => !SFO.R.b3d || SFO.R.b3d.done, null, { timeout: 0, polling: 1000 });
  const info = { ready_s: (Date.now() - t0) / 1000, b3d: await page.evaluate(() => SFO.R.b3d ? SFO.R.b3d.info() : null),
    tower: await page.evaluate(() => SFO.R.b3d ? SFO.R.b3d.tower : null),
    towerPos: await page.evaluate(() => SFO.world.towerPos ? { xyz: [...SFO.world.towerPos], eyeY: SFO.world.towerPos.eyeY } : null), views: {} };
  console.log('ready', JSON.stringify(info));
  for (const [name, t, l] of views) {
    const r = await page.evaluate(([t, l]) => {
      if (t && t !== '-') { SFO.envCore.clock.overrideT = Date.parse(t); SFO.applyEnv(Date.now(), true); }
      if (l === 'towercam') { SFO.view('tower'); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); }
      else { const a = l.split(',').map(Number); SFO.qa.look([a[0], a[1], a[2]], a[3], a[4], a[5], a[6] || 50); }
      const st = SFO.env(); return { sun: st && st.sun ? { az: st.sun.az, el: st.sun.el } : null };
    }, [t, l]);
    const f0 = await page.evaluate(() => SFO.R.frames); const n = +(process.env.FRAMES || 8);
    await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 200 });
    const cam = await page.evaluate(() => { const c = SFO.R.engine && SFO.R.engine.camera; const b = SFO.R.b3d;
      return { pos: c ? c.position.toArray().map(v => +v.toFixed(2)) : null, inCab: b ? !!b._inCab : null, glassVisible: b && b.cabGlass.length ? b.cabGlass.map(o => o.material.visible) : null }; });
    info.views[name] = { t, look: l, ...r, ...cam };
    console.log(name, JSON.stringify(info.views[name]));
    await shot('tapp_' + name);
  }
  fs.writeFileSync(path.join(OUT, 'tower_app_info.json'), JSON.stringify(info, null, 1));
};
