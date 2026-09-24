// Headless check of the app against a real relay (no screenshots):
//   python3 sfo_live_server.py --port 18731 --replay refs/cache/rec --from 2026-09-24T07:30Z --quiet &
//   RELAY=http://127.0.0.1:18731 SOFTGL=1 WAIT=40000 node livetest.mjs jobs/relaytest.mjs
// Prints, every 10 s: feed status text, tracks, phases, stand matches, routes known, and relay /api/status numbers.
export default async ({ page, base }) => {
  await page.goto(base + 'live.html?mode=live');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  const until = Date.now() + +(process.env.WAIT || 40000);
  while (Date.now() < until) {
    await page.waitForTimeout(10000);
    const info = await page.evaluate(async () => {
      const T = SFO.traffic; const tr = [...T.tracks.values()];
      const st = await (await fetch('api/status')).json();
      return {
        feed: document.querySelector('.feed, #feed, [data-feed]')?.textContent?.trim()?.slice(0, 60) || null,
        tracks: tr.length, stale: tr.filter(t => t.stale).length,
        phases: tr.reduce((m, t) => (m[t.phase] = (m[t.phase] || 0) + 1, m), {}),
        gates: tr.filter(t => t.gate).map(t => (t.info.flight || t.info.reg || t.hex).trim() + '@' + t.gate.name),
        routes: tr.filter(t => t.route).map(t => (t.info.flight || '').trim() + ':' + t.route.codes.join('-')).slice(0, 8),
        relay: { seq: st.merge.seq, aircraft: st.merge.aircraft, replayAt: st.relay.replay_position_utc, routes: st.routes.source, gates: st.gates.flights },
      };
    });
    console.log(JSON.stringify(info));
  }
};
