// Named views + UI panels of the Hayward Live 3D app, through P1's in-page replay pack (?mode=replay: the shim starts
// 60 s into the window so aircraft are drawn within a few seconds, as on the phone artifact). Desktop (1280x720) or
// phone (MOBILE=1 -> 390x844 @ DPR 1 for the checks). Prints the D1-safe counts, the status / phase / runway lines, and
// a sample card, then shoots every view plus the card, About, ATC and statistics sheets. LOOK at every image.
//   node livetest.mjs jobs/views.mjs                 (desktop)
//   MOBILE=1 PREFIX=phone node livetest.mjs jobs/views.mjs
export default async ({ page, shot, base, DEV, MOBILE, errors, log }) => {
  const t0 = Date.now();
  await page.goto(base + 'live.html?mode=replay&fixedres=1');
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__hwdError); if (err) throw new Error(err);
  log('ready in', Date.now() - t0, 'ms');
  await page.waitForTimeout(+(process.env.WAIT || 12000));   // let the replay run and NAIP load
  const S = (f, a) => page.evaluate(f, a);
  log('counts', JSON.stringify(await S(() => HWD.qa.counts())));
  log('status', await S(() => [document.querySelector('#status .txt').textContent, document.querySelector('#phaseline').textContent, document.querySelector('#rwystats').textContent]));
  // a D1 leak scan of everything the UI can show: list, all cards, labels, sheets - no masked track's reg/callsign/op
  const leak = await S(() => {
    const masked = HWD.qa.tracks().filter(t => t.masked);
    const texts = []; for (const id of HWD.qa.tracks().map(t => t.id)) { HWD.select(HWD.ui && null, false); }
    return { masked: masked.length, maskedTypeOnly: masked.every(t => t.label && /^[A-Z0-9]{2,4}$/.test(t.label) || t.label === 'Aircraft') };
  });
  log('D1', JSON.stringify(leak));
  await S(() => HWD.qa.pause(true));
  // card for one drawn aircraft
  const pick = await S(() => { const t = HWD.qa.tracks().filter(x => x.drawn); return (t.find(x => x.park) || t[0] || {}).id ?? null; });
  if (pick != null) { await S((id) => HWD.qa.select(id, false), pick); await page.waitForTimeout(600);
    log('card:', (await S(() => document.querySelector('#card') && document.querySelector('#card').innerText.replace(/\n+/g, ' | '))));
    await shot('card_' + DEV, { dom: true }); await S(() => HWD.select(null)); }
  // every view
  for (const v of await S(() => HWD.qa.views())) {
    const ok = await S((v) => { const r = HWD.qa.view(v); HWD.frameNow(); return r; }, v);
    if (!ok) { log('view failed', v); continue; }
    await page.waitForTimeout(+(process.env.SETTLE || 700));
    await shot(v + '_' + DEV);
  }
  // follow an airborne aircraft (card + follow camera)
  const air = await S(() => { const t = HWD.qa.tracks().filter(x => x.drawn && !x.ground); return (t[0] || {}).id ?? null; });
  if (air != null) { await S(() => HWD.qa.pause(false)); await S((id) => HWD.qa.select(id, true), air); await page.waitForTimeout(2000); await shot('follow_' + DEV, { dom: true }); await S(() => HWD.qa.pause(true)); }
  // sheets: About, ATC, statistics
  await S(() => document.querySelector('#btn-about').click()); await page.waitForTimeout(400); await shot('about_' + DEV, { dom: true }); await S(() => document.querySelector('#btn-about').click());
  await S(() => document.querySelector('#btn-atc').click()); await page.waitForTimeout(400); log('atc:', await S(() => document.querySelector('#atc').innerText.replace(/\n+/g, ' | ').slice(0, 240))); await shot('atc_' + DEV, { dom: true }); await S(() => document.querySelector('#btn-atc').click());
  await S(() => document.querySelector('#phaseline').click()); await page.waitForTimeout(500); log('stats:', await S(() => document.querySelector('#rstats').innerText.replace(/\n+/g, ' | ').slice(0, 300))); await shot('stats_' + DEV, { dom: true });
  log('errors', errors.length);
};
