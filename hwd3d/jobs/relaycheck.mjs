// End-to-end check of the app against P1's relay (hwd_live_server.py --replay, spawned by the harness on a free port).
// A freshly spawned replay relay has no backlog, so its display (lookahead_s behind) reaches real data only after
// ~lookahead_s (docs/phase2_app.md I2); WAIT covers that. No screenshots - this checks the live relay code path.
//   RELAY=spawn WAIT=80000 node livetest.mjs jobs/relaycheck.mjs
export default async ({ page, base, log, relayURL }) => {
  await page.goto(base + 'live.html?mode=live&fixedres=1');
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__hwdError); if (err) throw new Error(err);
  log('relay', relayURL && relayURL.href, 'ping', JSON.stringify(await page.evaluate(async () => { const j = await (await fetch('api/ping')).json(); return { hwdlive: j.hwdlive, mode: j.mode, d1: j.features && j.features.d1_mode, look: j.features && j.features.replay && j.features.replay.lookahead_s }; })));
  const until = Date.now() + +(process.env.WAIT || 80000);
  while (Date.now() < until) { await page.waitForTimeout(10000);
    log(JSON.stringify(await page.evaluate(async () => { const c = HWD.qa.counts(); const st = await (await fetch('api/status')).json().catch(() => ({})); return { drawn: c.drawn, tracks: c.tracks, scope: c.scope, phases: c.phases, delayS: c.delayS, status: document.querySelector('#status .txt').textContent, relaySeq: st.merge && st.merge.seq }; }))); }
};
