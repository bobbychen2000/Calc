// D1 forget-horizon check (review round 3, iteration 2, F7): the app against P1's relay in replay mode (spawned by the
// harness), full-ident relay so that unmasked keys exist. After the display has reached real data the job reconnects the
// page's StreamFeed with a seq from another relay process (?since=12345); the relay answers 'forget_horizon' and the app's
// onHorizon (traffic.forgetHorizon) must:
//  - keep every silent / parked aircraft that had a body (drawn, alpha > 0.5) - same opaque id, still drawn;
//  - show those aircraft by TYPE ONLY (no registration, callsign or operator in tr.ident; ident.withheld = 'horizon'),
//    unless the relay re-publishes the key in its current snapshot (then the relay's own record applies);
//  - mark none of them LADD / PIA (traffic.forget not called: counters.d1Forget unchanged, no maskWhy 'd1').
// Before the fix app.js did not pass onHorizon: the feed fell back to onForget(absent) and every such aircraft was masked
// 'd1' and faded out. The job prints counts only (no identity, no key) and writes them to out/phase2/horizon_<prefix>.json.
//   RELAY=spawn WAIT=90000 node livetest.mjs jobs/horizon.mjs
import fs from 'node:fs'; import path from 'node:path';
export default async ({ page, base, log, OUT }) => {
  const PREFIX = process.env.PREFIX || 'run';
  await page.goto(base + 'live.html?mode=live&fixedres=1');
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__hwdError); if (err) throw new Error(err);
  // wait for parked / silent aircraft with bodies (the display runs lookahead_s behind a freshly spawned relay)
  const until = Date.now() + +(process.env.WAIT || 90000);
  let pre = null;
  while (Date.now() < until) {
    await page.waitForTimeout(5000);
    pre = await page.evaluate(() => { const T = HWD.traffic, out = [];
      for (const tr of T.tracks.values()) { const D = tr.disp; if (!D.valid || !(D.alpha > 0.5) || !D.ground || tr.vehicle) continue;
        if (!(tr.stale || tr.phase === 'parked')) continue;
        const I = tr.ident || {}; out.push({ id: HWD.ui.o.idOf(tr.key), stale: !!tr.stale, hasReg: !!I.reg, hasCs: !!I.callsign, masked: !!I.masked, d1: (tr.info && tr.info.maskWhy) === 'd1' }); }
      return { list: out, d1Forget: T.counters.d1Forget || 0, horizons: T.counters.d1Horizon || 0, feed: !!HWD.feed() }; });
    log('waiting:', pre.list.length, 'parked / silent bodies,', pre.list.filter(q => q.stale).length, 'silent,', pre.list.filter(q => q.hasReg).length, 'with a registration');
    if (pre.list.filter(q => q.stale && q.hasReg).length >= 2) break;
  }
  if (!pre || !pre.feed) throw new Error('no relay feed (live mode needs RELAY=spawn)');
  // plant the horizon: a seq from another relay process, through the real reconnect path (?since=)
  await page.evaluate(() => { const f = HWD.feed(); f.seq = 12345; if (f.es) f.es.close(); f.es = null; f.sse(); });
  await page.waitForFunction((h0) => (HWD.traffic.counters.d1Horizon || 0) > h0, pre.horizons, { timeout: 30000 });
  await page.waitForTimeout(3000);
  const post = await page.evaluate((ids) => { const T = HWD.traffic, byId = new Map(); for (const tr of T.tracks.values()) byId.set(HWD.ui.o.idOf(tr.key), tr);
    return { d1Forget: T.counters.d1Forget || 0, horizons: T.counters.d1Horizon || 0, withheldN: T.counters.d1HorizonTracks || 0, last: HWD.lastHorizon || null,
      rows: ids.map(id => { const tr = byId.get(id); if (!tr) return { id, gone: true }; const D = tr.disp, I = tr.ident || {};
        return { id, gone: false, drawn: D.valid && D.alpha > 0.5, stale: !!tr.stale, hasReg: !!I.reg, hasCs: !!I.callsign, hasOp: !!I.operator, withheld: I.withheld || null, maskWhy: (tr.info && tr.info.maskWhy) || null, label: I.label === (tr.info && tr.info.icao) || !I.label ? 'type' : 'other' }; }) }; }, pre.list.map(q => q.id));
  const silentBefore = pre.list.filter(q => q.stale && q.hasReg).map(q => q.id);
  const S = post.rows.filter(r => silentBefore.includes(r.id));
  const fail = [];
  if (post.d1Forget !== pre.d1Forget) fail.push('traffic.forget was called (' + (post.d1Forget - pre.d1Forget) + ' keys marked LADD / PIA)');
  if (post.horizons !== pre.horizons + 1) fail.push('horizons ' + pre.horizons + ' -> ' + post.horizons);
  // (an aircraft the relay flagged LADD / PIA before - a masked 'x' key, maskWhy 'd1' - is type-only already and not a failure)
  const d1Before = new Set(pre.list.filter(q => q.d1).map(q => q.id));
  for (const r of post.rows) { if (r.gone) fail.push('a parked / silent aircraft was removed'); else if (!r.drawn) fail.push('a parked / silent aircraft lost its body'); if (r.maskWhy === 'd1' && !d1Before.has(r.id)) fail.push('marked LADD / PIA by the horizon'); }
  for (const r of S) if (!r.gone && (r.hasReg || r.hasCs || r.hasOp || r.withheld !== 'horizon')) fail.push('a silent aircraft still shows an identity after the horizon');
  const res = { before: { bodies: pre.list.length, silent: pre.list.filter(q => q.stale).length, silentWithReg: silentBefore.length, flaggedBefore: d1Before.size }, after: { kept: post.rows.filter(r => !r.gone && r.drawn).length, silentTypeOnly: S.filter(r => !r.hasReg && !r.hasCs && r.withheld === 'horizon').length, withheldTracks: post.withheldN, lastHorizon: post.last },
    d1Forget: [pre.d1Forget, post.d1Forget], fail };
  fs.writeFileSync(path.join(OUT, `horizon_${PREFIX || 'run'}.json`), JSON.stringify(res, null, 1));
  log('horizon', JSON.stringify(res));
  if (silentBefore.length < 1) throw new Error('no silent aircraft with an identity before the horizon: nothing was tested (raise WAIT)');
  if (fail.length) throw new Error('FAIL: ' + [...new Set(fail)].join('; '));
  log('PASS: ' + S.length + ' silent aircraft kept their bodies and show their type only; ' + post.rows.length + ' parked / silent bodies kept');
};
