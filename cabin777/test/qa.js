// Visual QA: render a fixed list of views into a folder. Usage: node test/qa.js <outdir> [w h] [names...]
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/home/claude/.npm-global/lib/node_modules/playwright')); }
const path = require('path');
const out = process.argv[2];
const W = +(process.argv[3] || 800), H = +(process.argv[4] || 500);
const only = process.argv.slice(5);
const sit = (id, yaw, pitch, extra = '') => `(()=>{const s=__app.L.seats.find(q=>q.id==='${id}'); __app.sit(s,{instant:true}); __app.anim=null; const e=__app.eyeFor(s); __app.cam.pos=[...e.pos]; __app.cam.yaw=${yaw}; __app.cam.pitch=${pitch}; ${extra}})()`;
const walk = (x, z, yaw, pitch, y = 1.62) => `__app.setView([${x},${y},${z}], ${yaw}, ${pitch})`;
const VIEWS = {
  q01_door1: walk(-0.4, 6.35, 'Math.PI+0.12', -0.05),
  q02_foyer: walk(0.3, 7.6, 0, 0.3),
  q03_polFwd: walk(-1.3, 17.3, 0, -0.18),
  q04_seat3A: sit('3A', 0.2, -0.18),
  q05_seat2F: `(()=>{const s=__app.L.seats.find(q=>q.id==='2F'); __app.sit(s,{instant:true}); __app.anim=null;})()`,
  q06_bed3A: `(()=>{const s=__app.L.seats.find(q=>q.id==='3A'); __app.sit(s,{instant:true}); __app.anim=null; __app.toggleBed(); const a=__app.anim; if(a){__app.cam.pos=[...a.to.pos]; __app.cam.yaw=a.to.yaw; __app.cam.pitch=a.to.pitch; __app.anim=null;}})()`,
  q07_midGalley: walk(1.25, 22.2, 'Math.PI', 0.02),
  q08_pp: walk(1.14, 25.2, 'Math.PI', -0.12),
  q09_seat21C: sit('21C', 0, -0.15),
  q10_econAft: walk(0.97, 30.0, 'Math.PI', -0.05),
  q11_wing31A: `(()=>{const s=__app.L.seats.find(q=>q.id==='31A'); __app.sit(s,{instant:true}); __app.lookOut(s); __app.anim && (()=>{const a=__app.anim; __app.cam.pos=[...a.to.pos]; __app.cam.yaw=a.to.yaw; __app.cam.pitch=a.to.pitch; __app.anim=null;})();})()`,
  q11b_seat31A: sit('31A', 1.05, -0.12),
  q12_door3: walk(-0.2, 35.4, 0.9, -0.1),
  q13_aftGalley: walk(0.1, 49.7, 'Math.PI', -0.05),
  q14_night: `(()=>{__app.applyMood('sleep'); __app.applySky('night'); ${walk(0.97, 40.3, 'Math.PI', -0.05)}})()`,
  q15_sunset: `(()=>{__app.applyMood('dining'); __app.applySky('sunset'); __app.scene.setAllWindows(0); ${walk(0.97, 44.0, '-Math.PI*0.62', -0.02)}})()`,
  q16_xray: `(()=>{__app.applyMood('boarding'); __app.applySky('day'); __app.setView([0,0.6,26], 0.3, 55*Math.PI/180, 'xray')})()`,
};
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  const logs = [];
  page.on('pageerror', (e) => logs.push('pageerror ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/ERR_TUNNEL/.test(m.text())) logs.push('console ' + m.text()); });
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + path.resolve(__dirname, '../dist/test.html'));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } });
  for (const n of (only.length ? only : Object.keys(VIEWS))) {
    await page.evaluate(VIEWS[n]);
    await page.evaluate(() => __app.renderNow());
    await page.screenshot({ path: path.join(out, n + '.png') });
    await page.evaluate(() => { if (__app.seated) { __app.setBed(false); __app.seated = null; __app.hideSeatBar(); } __app.mode = 'walk'; __app.scene.xray = false; });
    console.log('shot', n);
  }
  console.log(logs.join('\n'));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
