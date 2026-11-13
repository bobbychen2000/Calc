// Phone UI check (fix round 2, docs/phase2_run.md section 7): every visible control is a touch target of at least 44 x 44 CSS
// px (Apple HIG), lies inside the viewport, and is not covered by another element at its centre (elementFromPoint).
// Checked in the default state, with the bottom sheet open, and with a detail card open. Fails (exit code 1) on any
// violation. Phone viewport: MOBILE=1 (390 x 844, DPR 1, touch).
// Not counted (listed as 'exempt'): inline text links of the credit line (#attrib; WCAG 2.2 SC 2.5.8 'inline' exception -
// the size of a link in a sentence is set by the line height), controls entirely below the bottom edge (the list sheet in its
// peek state hides them by design until it is opened), and controls of the list sheet under an open detail card (the card
// covers the sheet on phones until it is closed with its 44-px close button).
//   MOBILE=1 PREFIX=phoneui RELAY=none node livetest.mjs jobs/phone_ui.mjs
export default async ({ page, shot, base, errors, log }) => {
  await page.goto(base + 'live.html?mode=replay&fixedres=1');
  await page.waitForFunction(() => window.__hwdReady || window.__hwdError, null, { timeout: 0 });
  await page.waitForTimeout(+(process.env.WAIT || 12000));
  const MIN = 44;
  const scan = (state) => page.evaluate(({ MIN, state }) => {
    const vw = innerWidth, vh = innerHeight, bad = [], ok = [], exempt = [];
    const vis = (el) => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) return false; for (let p = el; p; p = p.parentElement) if (p.hidden) return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const name = (el) => el.id ? '#' + el.id : (el.getAttribute('aria-label') || el.textContent.trim().replace(/\s+/g, ' ').slice(0, 22) || el.className || el.tagName);
    for (const el of document.querySelectorAll('button, a[href], input, select, [role="button"], #list .row')) {
      if (!vis(el)) continue;
      // inside a scrolled container (the flight list, a sheet): only what is scrolled into its box counts
      let clipped = false, scroller = false; for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) { const cs = getComputedStyle(p); if (/(auto|scroll)/.test(cs.overflowY + cs.overflowX)) scroller = true; if (/(auto|scroll|hidden)/.test(cs.overflowY + cs.overflowX)) { const pr = p.getBoundingClientRect(), r = el.getBoundingClientRect(); if (r.bottom <= pr.top || r.top >= pr.bottom || r.right <= pr.left || r.left >= pr.right) clipped = true; } }
      if (clipped) continue;
      const r = el.getBoundingClientRect(); const n = name(el);
      const box = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
      if (el.tagName === 'A' && el.closest('#attrib')) { exempt.push([state, n, ...box, 'inline credit link']); continue; }
      if (r.top >= vh - 0.5) { exempt.push([state, n, ...box, 'below the bottom edge (sheet in peek)']); continue; }
      const why = [];
      if (r.width < MIN - 0.5 || r.height < MIN - 0.5) why.push('small');
      // (an element partly scrolled out of a scrolling list / sheet is reached by scrolling it - not off-screen)
      if (!scroller && (r.left < -0.5 || r.top < -0.5 || r.right > vw + 0.5 || r.bottom > vh + 0.5)) why.push('off-screen');
      const cx = Math.min(vw - 1, Math.max(0, r.x + r.width / 2)), cy = Math.min(vh - 1, Math.max(0, r.y + r.height / 2));
      const top = document.elementFromPoint(cx, cy);
      if (top && !(el === top || el.contains(top) || top.contains(el) && top.tagName === 'LABEL')) {
        if (top.closest('#card') && el.closest('#panel')) { exempt.push([state, n, ...box, 'list sheet under the open card']); continue; }
        why.push('covered by ' + name(top));
      }
      (why.length ? bad : ok).push([state, n, ...box, why.join(',')]);
    }
    return { bad, ok: ok.length, okList: ok.map(o => o[1] + ' ' + o[4] + 'x' + o[5]), exempt, scrollW: document.documentElement.scrollWidth, vw };
  }, { MIN, state });
  const res = [];
  res.push(await scan('default'));
  await shot('phoneui_default', { dom: true });
  await page.evaluate(() => { const g = document.querySelector('#grab'); if (g) g.click(); }); await page.waitForTimeout(2500);
  res.push(await scan('sheet_open'));
  await shot('phoneui_sheet', { dom: true });
  await page.evaluate(() => { const g = document.querySelector('#grab'); if (g) g.click(); }); await page.waitForTimeout(2500);
  const pick = await page.evaluate(() => { const t = HWD.qa.tracks().filter(x => x.drawn); return (t[0] || {}).id ?? null; });
  if (pick != null) { await page.evaluate((id) => HWD.qa.select(id, false), pick); await page.waitForTimeout(800); res.push(await scan('card_open')); await shot('phoneui_card', { dom: true }); }
  const bad = res.flatMap(r => r.bad), nOk = res.reduce((a, r) => a + r.ok, 0);
  log('PHONEUI', JSON.stringify({ checked: nOk + bad.length, ok: nOk, bad: bad.length, page_scroll_w: res[0].scrollW, vw: res[0].vw, console_errors: errors.length }));
  for (const b of bad) log('PHONEUI_BAD', JSON.stringify(b));
  log('PHONEUI_EXEMPT', JSON.stringify(res.flatMap(r => r.exempt).map(e => e[0] + ':' + e[1] + ':' + e[e.length - 1])));
  log('PHONEUI_OK', JSON.stringify(res[0].okList || []));
  if (bad.length || res[0].scrollW > res[0].vw) process.exitCode = 1;
};
