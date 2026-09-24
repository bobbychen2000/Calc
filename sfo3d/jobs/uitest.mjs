// UI check (step 3): detail card (gate vs SFO, runway, data age, deep links), runway statistics sheet, ATC sheet
// (feeds, badges, highlight, audio delay), status bar. Headless metrics first; screenshots only with SHOTS=1.
//   SOFTGL=1 MODE=snapshot node livetest.mjs jobs/uitest.mjs
//   MOBILE=1 W=390 H=844 DPR=2 SOFTGL=1 SHOTS=stats,atc node livetest.mjs jobs/uitest.mjs
//   RELAY=http://127.0.0.1:18731 SOFTGL=1 MODE=live WAIT=150000 node livetest.mjs jobs/uitest.mjs
export default async ({ page, base, shot }) => {
  const SH = process.env.SHOTS || ''; const want = (k) => SH === '1' ? k !== 'about' : SH.split(',').includes(k); // SHOTS=1 or SHOTS=card,stats,atc,about
  const errors = []; page.on('pageerror', (e) => errors.push(String(e && e.message || e)));
  const mode = process.env.MODE || 'snapshot'; const pre = process.env.PREFIX || ('ui_' + (process.env.MOBILE ? 'phone' : 'desk') + '_' + mode);
  await page.goto(base + 'live.html?mode=' + mode);
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.waitForTimeout(+(process.env.WAIT || 20000));
  const S = async (f, a) => page.evaluate(f, a);
  console.log('status:', await S(() => [document.querySelector('#status .txt').textContent, document.querySelector('#status').title]));
  console.log('stats line:', await S(() => document.querySelector('#rwystats').textContent));
  // card for a parked aircraft with a gate, else any ground aircraft
  const hex = await S(() => { const t = [...SFO.traffic.tracks.values()]; const g = t.find(x => x.gate && x.info.flight) || t.find(x => x.disp.valid && x.info.flight); return g && g.hex; });
  if (hex) {
    await S((h) => SFO.select(h, false), hex); await page.waitForTimeout(1500);
    console.log('card:', await S(() => document.querySelector('#card').innerText.replace(/\n+/g, ' | ')));
    console.log('card links:', await S(() => [...document.querySelectorAll('#card a')].map(a => a.href)));
    if (want('card')) await shot(pre + '_card');
  }
  // every aircraft at a stand: does the card agree with SFO's plan? (gate rows only)
  const gsum = await S(() => { const out = { agree: 0, differ: 0, noPlan: 0, ex: [] };
    for (const t of SFO.traffic.tracks.values()) { if (!t.gate || !t.info.flight) continue; SFO.select(t.hex, false); const dd = [...document.querySelectorAll('#card dt')].find(d => d.textContent === 'Gate' || d.textContent === 'Stand');
      const txt = dd ? dd.nextElementSibling.textContent : ''; const k = /per SFO/.test(txt) ? 'agree' : /SFO says/.test(txt) ? 'differ' : 'noPlan'; out[k]++; if (k !== 'noPlan' && out.ex.length < 12) out.ex.push(t.info.flight.trim() + ': ' + txt); }
    SFO.select(null); return out; });
  console.log('gate rows:', JSON.stringify(gsum));
  if (hex) { await S((h) => SFO.select(h, false), hex); await page.waitForTimeout(500); }
  // stats sheet
  await S(() => document.querySelector('#rwystats').click()); await page.waitForTimeout(1500);
  console.log('stats sheet:', await S(() => { const p = document.querySelector('#rstats'); return { hidden: p.hidden, text: p.innerText.slice(0, 600).replace(/\n+/g, ' | ') }; }));
  if (want('stats')) await shot(pre + '_stats');
  // ATC sheet: open, highlight the Ground feed, set a 10 s delay
  await S(() => document.querySelector('#btn-atc').click()); await page.waitForTimeout(1000);
  const atc0 = await S(() => { const p = document.querySelector('#atc'); return { hidden: p.hidden, feeds: p.querySelectorAll('.feed').length, faa: p.querySelectorAll('.fq.faa').length, latc: p.querySelectorAll('.fq.latc').length, links: [...p.querySelectorAll('a.listen')].slice(0, 3).map(a => a.href) }; });
  console.log('atc:', JSON.stringify(atc0));
  const counts = await S(() => { const a = SFO.atc(); return Object.fromEntries(Object.entries(a.likely).map(([k, v]) => [k, v.length])); });
  console.log('likely per feed:', JSON.stringify(counts));
  const mount = process.env.TUNE || 'ksfo_gnd';
  await S((m) => SFO.atcCmd('tune', m), mount); await page.waitForTimeout(1200);
  console.log('tuned:', await S(() => ({ btn: document.querySelector('#btn-atc').textContent, labels: document.querySelectorAll('.lbl.atc').length, rows: document.querySelectorAll('.row .atcchip').length, tuned: document.querySelector('#atc .tuned')?.innerText.replace(/\n+/g, ' | ').slice(0, 300) })));
  if (want('atc')) await shot(pre + '_atc');
  const before = await S(() => ({ d: SFO.traffic.audioDelay, tD: Date.now() - SFO.traffic.displayTime() }));
  await S(() => SFO.atcCmd('delay', 10)); await page.waitForTimeout(3000);
  const after = await S(() => ({ d: SFO.traffic.audioDelay, lag: Date.now() - SFO.traffic.displayTime(), status: document.querySelector('#status .txt').textContent, jumps: SFO.traffic.counters.timeJumps }));
  console.log('audio delay:', JSON.stringify({ before, after }));
  await S(() => SFO.atcCmd('delay', 0)); await S(() => SFO.atcCmd('tune', null));
  if (want('about')) { await S(() => document.querySelector('#btn-about').click()); await page.waitForTimeout(800); await shot(pre + '_about'); }
  console.log('page errors:', errors.length ? errors.slice(0, 5) : 'none');
};
