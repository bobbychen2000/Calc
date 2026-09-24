// Layout check without screenshots: the top bar, the view buttons, the flight panel and the popovers must not overlap.
//   SOFTGL=1 W=1280 H=720 node livetest.mjs jobs/layoutcheck.mjs   (also MOBILE=1 W=390 H=844)
export default async ({ page, base, W, H }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const r = await page.evaluate(() => {
    const box = (s) => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return b.width ? { l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right), b: Math.round(b.bottom) } : null; };
    const ov = (a, b) => a && b && a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
    const top = [...document.querySelectorAll('#top > *')].map(e => e.getBoundingClientRect()).filter(b => b.width).reduce((m, b) => ({ l: Math.min(m.l, b.left), t: Math.min(m.t, b.top), r: Math.max(m.r, b.right), b: Math.max(m.b, b.bottom) }), { l: 1e9, t: 1e9, r: -1e9, b: -1e9 });
    const views = box('#views'), panel = box('#panel'), stats = box('#rwystats'), attrib = box('#attrib');
    return { top, views, panel, stats, attrib, topViews: ov(top, views), viewsPanel: ov(views, panel), statsVisible: stats ? stats.b <= innerHeight && stats.t >= 0 : false, statusText: document.querySelector('#status').innerText };
  });
  console.log(W + 'x' + H, JSON.stringify(r));
};
