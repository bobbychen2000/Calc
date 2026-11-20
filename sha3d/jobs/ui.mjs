// UI shell renders (P2e): modes, status pill, legend, stand labels / card, list search, Settings, About - on a phone and a
// laptop. Run through the harness, e.g.
//   SOFTGL=1 DEVICE='iPhone 15' OUT=docs/phase2 PREFIX=ui_phone node livetest.mjs jobs/ui.mjs
//   SOFTGL=1 W=1440 H=900 OUT=docs/phase2 PREFIX=ui_laptop node livetest.mjs jobs/ui.mjs
//   SOFTGL=1 W=1440 H=900 RELAY=http://127.0.0.1:8791 SCENES=live OUT=docs/phase2 PREFIX=ui_laptop node livetest.mjs jobs/ui.mjs
// SCENES (','-separated, default 'snapshot,offline'): snapshot = the default page (snapshot mode, its recorded weather and
// instant) with legend / labels / card / search / settings / About shots; offline = ?relay=1 with no relay answering;
// live = ?relay=1 through a relay (MOCK_RELAY=1 or RELAY=...). Prints the UI state it checks (mode, status text, runway).
export default async ({ page, shot, base, W, H }) => {
  const phone = W <= 760;
  const quality = process.env.QUALITY || (phone ? 'low' : 'high');
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  const settle = async (n = 6) => { await frames(n); await page.waitForTimeout(400); await frames(2); };
  async function open(q) {
    await page.goto(base + 'live.html?fixedres=1&quality=' + quality + (q ? '&' + q : ''));
    await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
    const err = await page.evaluate(() => window.__shaError || null); if (err) throw new Error(err);
    await page.waitForTimeout(1500); await settle(8);
    const st = await page.evaluate(() => ({ mode: SHA.qa.mode(), status: document.querySelector('#status').innerText.replace(/\s+/g, ' '), clock: document.querySelector('#clock').innerText.replace(/\s+/g, ' '),
      note: document.querySelector('#note').textContent, runway: (() => { const m = SHA.runwayMode(); return m && { dir: m.dir, arr: m.arr, dep: m.dep, rule: m.rule, report: m.report && m.report.raw, reason: m.reason }; })() }));
    console.log('state', JSON.stringify(st));
    return st;
  }
  const clickStand = async (name) => {
    const ok = await page.evaluate((n) => { const e = document.querySelector(`#slabels [data-stand="${n}"]`); if (!e || e.style.display === 'none') return false; const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }, name);
    if (ok) { if (phone) await page.touchscreen.tap(ok[0], ok[1]); else await page.mouse.click(ok[0], ok[1]); return true; }
    return false;
  };
  const scenes = (process.env.SCENES || 'snapshot,offline').split(',');
  if (scenes.includes('snapshot')) {
    await open('');
    await shot(process.env.PREFIX + '_snapshot_overview');
    await page.evaluate(() => SHA.qa.openLegend(true)); await settle(2);
    await shot(process.env.PREFIX + '_legend');
    await page.evaluate(() => SHA.qa.openLegend(false));
    // T2 with stand labels; tap / click a label -> stand card
    await page.evaluate(() => SHA.qa.view('t2')); await settle(8);
    console.log('labels shown (t2 view):', JSON.stringify(await page.evaluate(() => SHA.qa.standLabels().length)));
    await shot(process.env.PREFIX + '_t2_labels');
    // a visible label inside the free part of the viewport (not under the sheet / panel), nearest the centre
    const cand = await page.evaluate(([W, H, phone]) => [...document.querySelectorAll('#slabels [data-stand]')].filter(e => e.style.display !== 'none').map(e => { const r = e.getBoundingClientRect(); return { n: e.dataset.stand, x: r.x + r.width / 2, y: r.y + r.height / 2 }; })
      .filter(p => p.x > 20 && p.x < W - 20 && p.y > 110 && p.y < H - (phone ? 200 : 60) && (phone || p.x > 400)).sort((a, b) => Math.hypot(a.x - W / 2, a.y - H / 2) - Math.hypot(b.x - W / 2, b.y - H / 2)).map(p => p.n), [W, H, phone]);
    let clicked = false; for (const n of cand.slice(0, 3)) { if (await clickStand(n)) { clicked = n; break; } }
    if (!clicked) await page.evaluate(() => SHA.qa.selectStand('233', false));
    await settle(4); console.log('stand card via', clicked ? 'label ' + clicked : 'qa.selectStand', '->', await page.evaluate(() => !document.querySelector('#card').hidden ? 'card shown: ' + document.querySelector('#card .fl b').textContent : 'NO CARD'));
    await shot(process.env.PREFIX + '_stand_card_label');
    await page.evaluate(() => { const b = document.querySelector('#card button[data-act="fly"]'); b && b.click(); });
    await page.waitForTimeout(2200); await settle(6);
    await shot(process.env.PREFIX + '_stand_card_fly');
    await page.evaluate(() => SHA.qa.closeCard());
    // list search for stands (phone: the sheet opens)
    await page.evaluate(() => SHA.qa.search('25')); if (phone) await page.evaluate(() => SHA.qa.sheet('open')); await settle(3);
    await shot(process.env.PREFIX + '_search_stands');
    await page.evaluate(() => { SHA.qa.search(''); SHA.qa.sheet('peek'); });
    await page.evaluate(() => SHA.qa.openSettings(true)); await settle(2);
    await shot(process.env.PREFIX + '_settings');
    await page.evaluate(() => SHA.qa.openAbout(true)); await settle(2);
    await shot(process.env.PREFIX + '_about');
    await page.evaluate(() => { const a = document.querySelector('#about'); const h = [...a.querySelectorAll('h4')].find(x => /Sources/.test(x.textContent)); a.scrollTop = h ? h.offsetTop - 8 : a.scrollHeight / 2; }); await settle(2);
    await shot(process.env.PREFIX + '_about_licences');
    await page.evaluate(() => { const a = document.querySelector('#about'); a.scrollTop = a.scrollHeight; }); await settle(2);
    await shot(process.env.PREFIX + '_about_end');
    const about = await page.evaluate(() => document.querySelector('#about').innerText);
    for (const k of ['OpenStreetMap', 'ODbL', 'ADSB.lol', 'Copernicus Sentinel', 'WorldDEM', 'Umbra', 'WorldCover', 'standing data', 'Mictronics', 'NOAA/NWS', 'AIP China', 'MH 5001-2021', 'GPL-2.0', 'trademarks', 'simulated and inferred', 'No ATC audio'])
      console.log('about has', k, about.includes(k) ? 'ok' : 'MISSING');
    await page.evaluate(() => SHA.qa.openAbout(false));
  }
  if (scenes.includes('offline')) {
    // no relay answering (the harness may proxy one: block the API for this scene)
    const block = (r) => r.fulfill({ status: 503, contentType: 'text/plain', body: 'no relay' });
    await page.route(/\/api\//, block);
    const st = await open('relay=1');
    await page.unroute(/\/api\//, block);
    console.log('check: relay requested but absent ->', st.mode.mode === 'snapshot' && /Relay offline/.test(st.status) ? 'snapshot + Relay offline ok' : 'FAIL');
    await shot(process.env.PREFIX + '_relay_offline');
  }
  if (scenes.includes('live')) {
    const st = await open('relay=1');
    console.log('check: live ->', st.mode.mode === 'live' && st.mode.relay && /Live/.test(st.status) ? 'live ok' : 'FAIL');
    await page.evaluate(() => SHA.qa.openLegend(true)); await settle(2);
    await shot(process.env.PREFIX + '_live');
    await page.evaluate(() => SHA.qa.openAbout(true)); await settle(2);
    await shot(process.env.PREFIX + '_live_about');
  }
};
