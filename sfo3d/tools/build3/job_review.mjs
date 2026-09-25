// livetest.mjs job: the review-round views of live3.html in one page load (day, dusk, night), with per-view metrics
// (debugInfo: per-frame draw calls, texture memory, retained CPU image copies, exposure) and optional HDR dumps of the
// resolved pre-tone-mapping image (TRAA output, half float) for grading the display transform offline.
//   SOFTGL=1 W=960 H=540 OUT=out/engine2 PAGE="live3.html?tier=high" HDR=1 node livetest.mjs tools/build3/job_review.mjs
// VIEWS (optional, ';'-separated) overrides the default list; items: overview | gate:<stand>,<d>,<side>,<pitch> | tower |
// thr:<rwy>,<d>,<pitch> | hold:<i>,<d> | ac:<hex|ual|wide>,<d>[,<yaw>,<pitch>] | acside:<hex|ual>,<d> | light:<real|day|dusk|night>
// | orbit:<hex|ual>,<d> (TRAA ghosting check: 12 frames sweeping 3 deg/frame around the aircraft, shot, then 16 static
// frames at the same pose, shot; the difference image is the ghosting). PREFIX (default 'rv') names the shots.
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const pg = process.env.PAGE || 'live3.html';
  const P = process.env.PREFIX || 'rv';
  const t0 = Date.now();
  let crashed = false; page.on('crash', () => { crashed = true; console.log('PAGE CRASHED (renderer process gone: out of memory?) at', ((Date.now() - t0) / 1000).toFixed(0), 's'); });
  const guard = setInterval(() => { if (crashed) { console.log('aborting'); process.exit(3); } }, 2000);
  await page.goto(base + pg + (pg.includes('?') ? '&' : '?') + (process.env.QS || 'mode=snapshot&res=1'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
  console.log(pg, 'ready', ((Date.now() - t0) / 1000).toFixed(1), 's', JSON.stringify(await page.evaluate(() => ({ backend: SFO.R.engine.backend, tier: SFO.R.tier }))));
  const tr = await page.evaluate(() => SFO.qa.tracks().filter(t => t.gate));
  const pick = (re) => (tr.find(t => re.test(t.flight || '')) || {}).hex;
  const ids = { ual: pick(/^UAL/) || (tr[0] || {}).hex, wide: (tr.find(t => /B77|B78|A35|A38|B74|A33/.test(t.icao || '')) || {}).hex };
  const hexOf = (a) => ids[a] || a;
  const frames = async (n) => { const f0 = await page.evaluate(() => SFO.R.frames); await page.waitForFunction(([f, n]) => SFO.R.frames >= f + n, [f0, n], { timeout: 0, polling: 200 }); };
  const N = +(process.env.FRAMES || 8);
  const views = (process.env.VIEWS || 'overview;gate:B26,60,1,14;tower;thr:28R,900,3;hold:12,300;ac:ual,38;acside:ual,55;light:dusk;gate:B26,60,1,14;light:night;gate:B26,60,1,14;tower;ac:ual,38').split(';').filter(Boolean);
  let light = 'real';
  for (const v of views) {
    const [k, argS] = v.split(':'); const a = argS ? argS.split(',') : [];
    if (k === 'light') { await page.evaluate((m) => SFO.setLight(m), a[0]); light = a[0]; await page.waitForFunction(() => !SFO.R.bakes || !SFO.R.bakes.pending, null, { timeout: 0, polling: 300 }); await frames(2); continue; }
    if (k === 'orbit') {
      const hex = hexOf(a[0]); const d = +(a[1] || 45);
      const t = await page.evaluate((h) => { const t = SFO.traffic.tracks.get(h); return t ? t.disp.hdg * 180 / Math.PI : null; }, hex); if (t == null) { console.log('orbit: no track', hex); continue; }
      await page.evaluate(([h, d, y]) => SFO.qa.aircraft(h, d, y, 8), [hex, d, t + 60]); await frames(N);
      for (let i = 1; i <= 12; i++) { await page.evaluate(([h, d, y]) => SFO.qa.aircraft(h, d, y, 8), [hex, d, t + 60 + 3 * i]); await frames(1); }
      await shot(`${P}_${light}_orbit_moving`);
      await frames(16); await shot(`${P}_${light}_orbit_settled`);
      continue;
    }
    const ok = await page.evaluate(([k, a]) => {
      const q = SFO.qa; const hx = (s) => s;
      if (k === 'overview') { SFO.view('overview'); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
      if (k === 'gate') return q.gate(a[0], +(a[1] || 38), +(a[2] || 1), +(a[3] || 9));
      if (k === 'tower') return q.tower();
      if (k === 'thr') return q.threshold(a[0], +(a[1] || 180), +(a[2] || 7));
      if (k === 'hold') return q.hold(+a[0], +(a[1] || 32));
      if (k === 'ac') return q.aircraft(hx(a[0]), +(a[1] || 60), a[2] ? +a[2] : null, +(a[3] || 6));
      if (k === 'acside') { const t = SFO.traffic.tracks.get(a[0]); if (!t) return false; return q.aircraft(a[0], +(a[1] || 55), t.disp.hdg * 180 / Math.PI + 90, 4); }
      if (k === 'look') { q.look([+a[0], +a[1], +a[2]], +a[3], +a[4], +a[5], 40); return true; }
      return false;
    }, [k, (k === 'ac' || k === 'acside') ? [hexOf(a[0]), ...a.slice(1)] : a]);
    if (!ok) { console.log('view failed', v); continue; }
    const tv = Date.now(); await frames(N);
    const name = `${P}_${light}_${k}_${(argS || '').replace(/\W+/g, '_')}`.replace(/_+$/, '');
    console.log(name, ((Date.now() - tv) / 1000).toFixed(1), 's', JSON.stringify(await page.evaluate(() => ({ ...SFO.R.debugInfo(), jsHeapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null }))));
    await shot(name);
    if (process.env.HDR) {
      const d = await page.evaluate(async () => {
        const E = SFO.R.engine; const rt = E.traaNode._resolveRenderTarget; const px = await E.renderer.readRenderTargetPixelsAsync(rt, 0, 0, rt.width, rt.height);
        const u8 = new Uint8Array(px.buffer, px.byteOffset, px.byteLength); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
        return { w: rt.width, h: rt.height, type: px.constructor.name, expo: E.expo.value, b64: btoa(s) };
      });
      fs.writeFileSync(path.join(OUT, name + '.hdr16'), Buffer.from(d.b64, 'base64'));
      fs.writeFileSync(path.join(OUT, name + '.hdr.json'), JSON.stringify({ w: d.w, h: d.h, type: d.type, expo: d.expo }));
    }
  }
  clearInterval(guard);
  console.log('total', ((Date.now() - t0) / 1000).toFixed(1), 's');
};
