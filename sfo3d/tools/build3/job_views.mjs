// livetest.mjs job: render named views of live3.html (three.js renderer) and/or live.html (old renderer) in one
// browser session, for side-by-side comparison.
//   SOFTGL=1 W=960 H=540 OUT=out/engine PAGES="live3.html,live.html" VIEWS="view:overview;gate:B26,60,1,14;hold:12;tower" \
//     node livetest.mjs tools/build3/job_views.mjs
// PAGES: comma list (default live3.html); QS: extra query (default mode=snapshot); FRAMES: frames to accumulate per view
// on the three.js page (TRAA converges over several frames; default 8); SETTLE: ms per view on the old page.
// Output: <OUT>/<prefix>_<view>.png with prefix 'new' for live3.html and 'old' for live.html (PREFIX_<page> overrides).
export default async ({ page, shot, base }) => {
  const pages = (process.env.PAGES || 'live3.html').split(',').filter(Boolean);
  const views = (process.env.VIEWS || 'view:overview').split(';').filter(Boolean);
  for (const pg of pages) {
    const three = /live3/.test(pg);
    const prefix = process.env['PREFIX_' + pg.replace(/\W/g, '_')] || (three ? 'new' : 'old');
    const t0 = Date.now();
    await page.goto(base + pg + '?' + (process.env.QS || 'mode=snapshot&res=1'));
    await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
    const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
    await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
    if (three) await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
    console.log(pg, 'ready in', ((Date.now() - t0) / 1000).toFixed(1), 's', three ? JSON.stringify(await page.evaluate(() => ({ backend: SFO.R.engine.backend, reversed: SFO.R.engine.reversed, tier: SFO.R.tier }))) : '');
    for (const v of views) {
      const [kind, arg] = v.split(':');
      const ok = await page.evaluate(([k, a]) => {
        const q = SFO.qa; const args = a ? a.split(',') : [];
        if (k === 'gate') return q.gate(args[0], +(args[1] || 38), +(args[2] || 1), +(args[3] || 9));
        if (k === 'look') { q.look([+args[0], +args[1], +args[2]], +args[3], +args[4], +args[5], +(args[6] || 50)); return true; }
        if (k === 'view') { SFO.view(args[0]); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
        if (k === 'tower') return q.tower(+(args[0] || 170), +(args[1] || 235), +(args[2] || 11));
        if (k === 'hold') return q.hold(+args[0], +(args[1] || 32));
        if (k === 'ac') return q.aircraft(args[0], +(args[1] || 60), args[2] ? +args[2] : null, +(args[3] || 10));
        if (k === 'light') { SFO.setLight(args[0]); return true; }
        if (k === 'thr') return q.threshold(args[0], +(args[1] || 180), +(args[2] || 7));
        return false;
      }, [kind, arg]);
      if (!ok) { console.log('view failed', v); continue; }
      if (kind === 'light') continue;
      const tv = Date.now();
      if (three) { const f0 = await page.evaluate(() => SFO.R.frames); const n = +(process.env.FRAMES || 8); await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 200 }); }
      else {
        await page.waitForTimeout(+(process.env.SETTLE || 2500));
        // the old app's dynamic resolution drops to 0.4x on a software rasteriser: render one frame at full size
        await page.evaluate(() => { const c = document.querySelector('canvas#gl'); SFO.R.resize(c.width, c.height); SFO.frameNow(); });
      }
      console.log(pg, v, ((Date.now() - tv) / 1000).toFixed(1), 's', three ? JSON.stringify(await page.evaluate(() => SFO.R.debugInfo())) : '');
      await shot(prefix + '_' + v.replace(/[^a-zA-Z0-9]+/g, '_'));
    }
  }
};
