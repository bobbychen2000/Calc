// Shell review cameras (wave 3c, w12+), rendered like test/qa.js. Usage:
//   CABIN_PAGE=/tmp/b/test.html node review/qa/shell_views.js <outdir> [w h] [names...]
// yaw 0 looks forward (-z), PI aft (+z), +PI/2 left (-x), -PI/2 right (+x). Every view resets to boarding / day / shades open.
// __shade(z, side, level): nearest window (electric: 1 sheer, 2 blackout; manual: 1 half, 2 closed)
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path'), fs = require('fs');
const out = process.argv[2], W = +(process.argv[3] || 900), H = +(process.argv[4] || 560), only = process.argv.slice(5);
const page0 = process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html');
const PRE = `window.__S=(id)=>__app.L.seats.find(q=>q.id===id);
window.__sit=(id,yaw,pitch)=>{const s=__S(id); __app.sit(s,{instant:true}); __app.anim=null; const e=__app.eyeFor(s); __app.cam.pos=[...e.pos]; __app.cam.yaw=yaw; __app.cam.pitch=pitch;};
window.__rel=(id,dx,y,dz,yaw,pitch)=>{const s=__S(id); __app.setView([s.x+dx,y,s.z+dz],yaw,pitch);};
window.__shade=(z,side,level)=>{const ws=__app.scene.layout.windows; let b=-1,d=1e9; ws.forEach((w,i)=>{if(w.side===side&&Math.abs(w.z-z)<d){d=Math.abs(w.z-z);b=i;}}); __app.scene.setWindow(b,level);};
window.__shades=(z0,z1,side,level)=>{__app.scene.layout.windows.forEach((w,i)=>{if(w.side===side&&w.z>z0&&w.z<z1)__app.scene.setWindow(i,level);});};`;
const v = (x, y, z, yaw, pitch = -0.1) => `__app.setView([${x},${y},${z}],${yaw},${pitch})`;
// [camera expression, what the view should show]
const VIEWS = {
  s01_jWallL: [v(-1.1, 1.62, 22.0, 'Math.PI/2-0.35', -0.12), 'THE Room left sidewall and windows from the aisle, looking forward'],
  s02_yWallL: [v(-1.25, 1.62, 50.5, 'Math.PI/2-0.5', -0.12), 'economy left sidewall, windows, dado, grilles, looking forward'],
  s03_pyWallR: [v(1.35, 1.62, 40.5, '-Math.PI/2+0.55', -0.1), 'PY right sidewall and tubs, looking forward'],
  s04_fWall: [v(-0.4, 1.75, 10.6, 'Math.PI/2-0.25', -0.18), 'THE Suite left wall above the suites'],
  s05_jShades: [`(()=>{__shades(18,32,-1,2); ${v(-1.1, 1.62, 30.0, 'Math.PI/2-0.45', -0.08)}})()`, 'THE Room blackout shades closed, receding row'],
  s06_door2L: [v(0.2, 1.6, 16.8, 'Math.PI/2', -0.1), 'door 2L lining, surround, viewing window, floor'],
  s07_door4L: [v(0.0, 1.6, 44.3, 'Math.PI/2+0.25', -0.1), 'door 4L and neighbouring wall'],
  s08_yShadesMix: [`(()=>{__shades(46,56,1,1); __shade(48.2,1,2); __shade(51.2,1,0); ${v(1.25, 1.62, 54.5, '-Math.PI/2-0.5', -0.12)}})()`, 'economy right wall with manual shades half / closed / open'],
  s09_fWin: [`__sit('1A',Math.PI/2+0.2,-0.02)`, 'THE Suite window bowl, close'],
  b_jClose: [`(()=>{__shade(25.15,-1,2); ${v(-2.15, 1.2, 25.15, 'Math.PI/2', -0.04)}})()`, 'THE Room window, blackout closed, face on'],
  b_jSheer: [`(()=>{__shade(25.15,-1,1); ${v(-2.15, 1.2, 25.15, 'Math.PI/2', -0.04)}})()`, 'THE Room window, sheer down'],
  ra_yWin: [`__rel('35A',0.95,1.42,-0.38,Math.PI/2,-0.12)`, 'economy window tub face on'],
  ra_pyWin: [`__rel('26K',-0.95,1.45,-0.5,-Math.PI/2,-0.12)`, 'PY window tub face on'],
  b_dadoY2: [`__rel('30A',0.25,1.15,-0.6,Math.PI/2+0.25,-0.8)`, 'economy dado and grilles, low'],
  b_doorWin: [v(-1.55, 1.45, 16.8, 'Math.PI/2', 0.05), 'door 2L viewing window, close'],
  ra_door2floor: [v(0.6, 1.62, 16.8, 'Math.PI/2', -0.8), 'door 2 cross-aisle floor: vinyl and carpet'],
  ra_jWin: [`__sit('11A',Math.PI/2-0.25,0.0)`, 'THE Room window from seat 11A'],
  ra_carpetY: [`__rel('33C',0.5,1.62,0,Math.PI,-0.7)`, 'economy aisle carpet'],
};
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1) });
  const logs = [];
  page.on('pageerror', (e) => logs.push('pageerror ' + e.message));
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + page0);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } });
  await page.evaluate(PRE);
  for (const n of (only.length ? only : Object.keys(VIEWS))) {
    const [expr] = VIEWS[n];
    try { await page.evaluate(expr); } catch (e) { logs.push(n + ' view error ' + e.message); }
    await page.evaluate(() => { __app.renderNow(); __app.renderNow(); });
    await page.screenshot({ path: path.join(out, n + '.png'), timeout: 240000 });
    await page.evaluate(() => { if (__app.seated) { __app.setBed(false); __app.seated = null; __app.hideSeatBar(); } __app.mode = 'walk'; __app.scene.setAllWindows(0); __app.applyMood('boarding'); __app.applySky('day'); });
    console.log('shot', n);
  }
  fs.writeFileSync(path.join(out, 'views.json'), JSON.stringify(Object.fromEntries(Object.entries(VIEWS).map(([k, x]) => [k, x[1]])), null, 1));
  console.log(logs.join('\n'));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
