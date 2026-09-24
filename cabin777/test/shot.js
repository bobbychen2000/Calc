// Usage: node test/shot.js <outdir> [w h dpr] [views...]
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path');
const out = process.argv[2] || '/tmp/shots';
const W = +(process.argv[3] || 960), H = +(process.argv[4] || 600), DPR = +(process.argv[5] || 1);
const only = process.argv.slice(6);
const VIEWS = {
  door1: `__app.setView([-0.4,1.62,6.35], Math.PI+0.12, -0.05)`,
  polaris: `__app.setView([-1.3,1.62,8.2], Math.PI, -0.12)`,
  polarisBack: `__app.setView([1.3,1.62,17.4], 0, -0.15)`,
  seat3A: `(()=>{const s=__app.L.seats.find(q=>q.id==='3A'); __app.sit(s,{instant:true}); __app.anim=null; const e=__app.eyeFor(s); __app.cam.pos=e.pos; __app.cam.yaw=0; __app.cam.pitch=-0.15;})()`,
  pp: `__app.setView([1.14,1.62,25.1], Math.PI, -0.1)`,
  econ: `__app.setView([0.97,1.62,36.3], Math.PI, -0.06)`,
  econFwd: `__app.setView([-0.97,1.62,48.9], 0, -0.05)`,
  window31A: `(()=>{const s=__app.L.seats.find(q=>q.id==='31A'); __app.sit(s,{window:true, instant:true}); __app.anim=null; const e=__app.eyeFor(s); __app.cam.pos=[s.x-0.12,e.pos[1]+0.02,e.pos[2]]; __app.cam.yaw=1.35; __app.cam.pitch=-0.12;})()`,
  xray: `__app.setView([0,0.6,28], 0.35, 50*Math.PI/180, 'xray')`,
  night: `(()=>{__app.applyMood('sleep'); __app.applySky('night'); __app.setView([0.97,1.62,40.3], Math.PI, -0.05);})()`,
  galley: `__app.setView([0.2,1.62,50.6], 0, -0.1)`,
};
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
  const logs = [];
  page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
  await page.addInitScript(() => { window.__TEST__ = true; });
  const t0 = Date.now();
  await page.goto('file://' + (process.env.CABIN_PAGE || path.resolve(__dirname, '../dist/test.html')));
  await page.waitForFunction(() => window.__ready === true || document.querySelector('#fatal:not([hidden])'), null, { timeout: 120000 });
  console.log('ready in', Date.now() - t0, 'ms; build', await page.evaluate(() => window.__app && Math.round(__app.scene.buildTime)));
  await page.evaluate(() => { const h = document.getElementById('hint'); if (h) h.classList.add('gone'); });
  const names = only.length ? only : Object.keys(VIEWS);
  for (const n of names) {
    await page.evaluate(VIEWS[n]);
    const st = await page.evaluate(() => __app.renderNow());
    const t1 = Date.now();
    await page.evaluate(() => __app.renderNow());
    const ft = Date.now() - t1;
    await page.screenshot({ path: `${out}/${n}.png` });
    console.log(n, JSON.stringify(st), 'frame', ft, 'ms');
  }
  console.log(logs.slice(0, 40).join('\n'));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
