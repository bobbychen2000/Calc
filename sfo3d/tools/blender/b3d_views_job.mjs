// livetest.mjs job: old vs new building renders of live3.html (three.js renderer): the first-pass extruded buildings
// (?b3d=0) and the Blender assets (data/buildings3d/*.glb, js/three/buildings3d.js) from the same camera views.
//   flock out/.heavy.lock env SOFTGL=1 W=960 H=540 OUT=out/buildings3d VIEWS="tower;look:..." node livetest.mjs tools/blender/b3d_views_job.mjs
// VIEWS: name=view pairs separated by ';' (name optional), view as in tools/build3/job_views.mjs:
//   look:x,y,z,yaw,pitch,dist[,fov] | gate:<stand>,<dist>,<side>,<pitch> | tower[:dist,yaw,pitch] | view:<name> | towercam
//   | light:<preset> (SFO.setLight, no shot; applies to the following views)
// MODES: comma list of b3d modes (default 'old,new'; old = ?b3d=0, new = default files, lod2 = ?b3d=lod2)
// QS: extra query (default mode=snapshot&res=1); FRAMES: frames accumulated per view (TRAA; default 8).
// ROOT (livetest.mjs): serve a snapshot instead of the working tree (other workflows' half-done edits can break the page).
// Output: <OUT>/cmp_<mode>_<name>.png, and <OUT>/cmp_info.json (renderer + b3d stats per view).
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const views = (process.env.VIEWS || 'tower').split(';').filter(Boolean).map(v => { const i = v.indexOf('='); return i > 0 ? [v.slice(0, i), v.slice(i + 1)] : [v.replace(/[^a-zA-Z0-9]+/g, '_'), v]; });
  const modes = (process.env.MODES || 'old,new').split(',').filter(Boolean);
  const info = {};
  for (const mode of modes) {
    const q = mode === 'old' ? 'b3d=0' : mode === 'new' ? '' : 'b3d=' + mode;
    const t0 = Date.now();
    await page.goto(base + 'live3.html?' + (process.env.QS || 'mode=snapshot&res=1') + (q ? '&' + q : ''));
    await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 900000 }); // a module that fails to link sets neither
    const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
    await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
    await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
    await page.waitForFunction(() => !SFO.R.b3d || SFO.R.b3d.done, null, { timeout: 0, polling: 1000 });
    console.log(mode, 'ready in', ((Date.now() - t0) / 1000).toFixed(1), 's', JSON.stringify(await page.evaluate(() => SFO.R.b3d ? SFO.R.b3d.info() : null)));
    for (const [name, v] of views) {
      const [kind, arg] = v.split(':');
      const ok = await page.evaluate(([k, a]) => {
        const q = SFO.qa; const args = a ? a.split(',') : [];
        if (k === 'gate') return q.gate(args[0], +(args[1] || 38), +(args[2] || 1), +(args[3] || 9));
        if (k === 'look') { q.look([+args[0], +args[1], +args[2]], +args[3], +args[4], +args[5], +(args[6] || 50)); return true; }
        if (k === 'view' || k === 'towercam') { SFO.view(k === 'towercam' ? 'tower' : args[0]); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
        if (k === 'tower') return q.tower(+(args[0] || 170), +(args[1] || 235), +(args[2] || 11));
        if (k === 'light') { SFO.setLight(args[0]); return true; }
        return false;
      }, [kind, arg]);
      if (!ok) { console.log('view failed', v); continue; }
      if (kind === 'light') continue;
      const f0 = await page.evaluate(() => SFO.R.frames); const n = +(process.env.FRAMES || 8);
      await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 200 });
      const di = await page.evaluate(() => ({ r: SFO.R.debugInfo(), b3d: SFO.R.b3d ? SFO.R.b3d.info() : null }));
      (info[mode] = info[mode] || {})[name] = { view: v, drawCalls: di.r.drawCalls, tris: di.r.tris, texMB: di.r.texMB, b3dLod: di.b3d && di.b3d.unitsAtLod };
      console.log(mode, name, JSON.stringify(info[mode][name]));
      await shot('cmp_' + mode + '_' + name);
    }
  }
  fs.writeFileSync(path.join(OUT, 'cmp_info.json'), JSON.stringify(info, null, 1));
};
