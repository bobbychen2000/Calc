// Visual QA for the ANA 777-300ER cabin: render a fixed list of views (each paired with the closest official ANA
// reference photo in ref/ana/, see REF) into a folder, plus <outdir>/pairs.json for photo-vs-model rating.
// Usage: node test/qa.js <outdir> [w h] [names...]      (QA_PAGE=/abs/path/test.html to render another build)
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const path = require('path'), fs = require('fs');
const out = process.argv[2];
const W = +(process.argv[3] || 930), H = +(process.argv[4] || 575);
const only = process.argv.slice(5);
const page0 = process.env.QA_PAGE || process.env.CABIN_PAGE || path.resolve(__dirname, '../dist/test.html');
// helpers evaluated in the page: seat lookup, sit, view relative to a seat, walk view, lie flat, look out
const PRE = `window.__S=(id)=>__app.L.seats.find(q=>q.id===id);
window.__sit=(id,yaw,pitch)=>{const s=__S(id); __app.sit(s,{instant:true}); __app.anim=null; const e=__app.eyeFor(s); __app.cam.pos=[...e.pos]; if(yaw!==undefined){__app.cam.yaw=yaw; __app.cam.pitch=pitch;}};
window.__rel=(id,dx,y,dz,yaw,pitch)=>{const s=__S(id); __app.setView([s.x+dx,y,s.z+dz],yaw,pitch);};
window.__settle=()=>{const a=__app.anim; if(a&&a.to){__app.cam.pos=[...a.to.pos]; __app.cam.yaw=a.to.yaw; __app.cam.pitch=a.to.pitch;} __app.anim=null;};
if(!window.__pp){window.__pp=M4.perspective; M4.perspective=(f,a,n,far)=>window.__pp(f,a,window.__near||n,far);}`;   // window.__near: per-view near clip (reset after every view)
const walk = (x, y, z, yaw, pitch) => `__app.setView([${x},${y},${z}], ${yaw}, ${pitch})`;
// [camera expression, reference photos (ref/ana or ref/web), what the view should show]
const VIEWS = {
  // eye just inside door 1L looking across the cross-aisle (the old eye stood in the 0.6 m gap between the closets, integration r3)
  q01_door1: [walk(-2.0, 1.62, 5.45, -1.85, -0.06), [], 'boarding at L1: door-1 cross-aisle, galley front, door 1R lining, F closets'],
  q02_suiteAisle: [`__rel('2D',1.82,1.8,-0.6,0.75,-0.55)`, ['f_17301'], 'THE Suite from the aisle, fluted shells, 43in screens'],
  q03_suite1A: [`__sit('1A',0.12,-0.2)`, ['f_17306', 'f_17300'], 'seated in 1A: screen wall, ottoman, window console'],
  q04_suite1Abed: [`(()=>{__sit('1A'); __app.toggleBed(); __settle();})()`, ['f_17304'], '1A in bed mode'],
  q05_suiteBehind: [`__rel('1A',0.29,1.62,0.2,0.15,-0.42)`, ['f_17313'], 'window suite seen from behind: console, ottoman, screen wall'],
  q06_roomMain: [walk(1.15, 1.8, 24.0, 0.05, -0.3), ['c_27312'], 'THE Room main cabin from the right aisle'],
  q07_seat11A: [`__sit('11A',Math.PI,-0.25)`, ['c_27316'], 'seated in 11A'],
  q08_seat12H: [`__rel('12H',-0.8,1.78,1.3,-0.7,-0.55)`, ['c_27300', 'c_27303'], '12H seat from above/behind'],
  q09_centrePair: [`__rel('18D',-0.62,1.85,-1.45,-Math.PI/2,-0.6)`, ['c_27314', 'c_27313'], 'centre pair 17E/18D seen across the aisle'],
  q10_seat14D: [`__rel('14D',-0.57,1.72,1.02,-0.6,-0.55)`, ['c_27315'], '14D from above the aisle'],
  q11_bar3: [walk(-1.35, 1.62, 31.6, 'Math.PI+0.35', -0.1), [], 'door-3 self-service bar'],
  q12_wing: [`(()=>{const s=__S('19A'); __app.sit(s,{instant:true}); __app.lookOut(s); __settle();})()`, [], 'window view of the wing and GE90'],
  q13_pyFront: [`__rel('25C',0.35,1.75,-0.72,Math.PI+0.45,-0.3)`, ['py_37302'], 'PY cabin from the front'],
  q14_seat26A: [`__rel('26A',1.3,1.3,-0.85,Math.PI*0.7,-0.2)`, ['py_37301', 'py_37303'], 'PY window pair from the side'],
  q15_econFronts: [`(()=>{window.__near=1.25; ${walk(0, 1.55, 48.05, 'Math.PI', -0.26)}})()`, ['y_47300'], 'economy seat fronts looking aft (econ w24: row 34 D-G framed as y_47300, row 33 behind the near clip)'],
  q16_econAisle: [walk(1.0, 1.85, 47.3, 'Math.PI+0.42', -0.36), ['y_47301'], 'economy from the right aisle looking aft (econ w24: framed as y_47301)'],
  q17_econBacks: [`(()=>{const P=[0.722, 1.543, 49.048]; if(!window.__pf){window.__pf=M4.perspective; M4.perspective=(f,a,n,far)=>{const q=window.__fovAt; return window.__pf(q&&__app.mode==='walk'&&__app.cam.pos.every((v,i)=>Math.abs(v-q.p[i])<1e-6)?q.f:f,a,n,far);};} window.__fovAt={p:P,f:67.5*Math.PI/180}; window.__near=0.45; ${walk('P[0]','P[1]','P[2]','-Math.PI/2+0.002', -0.572)}})()`, ['y_47303'], 'economy H-K from the right aisle looking outboard (econ w46: landmark resection on y_47303 - 6 armrest noses + 2 windows, rms 3.0 px; fovY 67.5 deg for this view only via window.__fovAt, near clip 0.45 past the 33G back the eye stands beside; was (0.6, 1.35, 49.4) yaw -pi/2+0.25 pitch -0.42 fovY 58)'],
  q18_seat35C: [`__sit('35C',0,-0.25)`, ['y_47305'], 'seated in 35C: seatback screen'],
  q19_rearGalley: [walk(0.0, 1.62, 58.9, 'Math.PI', -0.08), [], 'rear galley at door 5'],
  q20_night: [`(()=>{__app.applyMood('sleep'); __app.applySky('night'); ${walk(1.15, 1.8, 24.0, 0.05, -0.2)}})()`, [], 'THE Room at night'],
  q21_sunset: [`(()=>{__app.applyMood('dining'); __app.applySky('sunset'); __app.scene.setAllWindows(0); ${walk(0.97, 1.62, 44.0, '-Math.PI*0.62', -0.02)}})()`, [], 'sunset through the windows'],
  q22_xray: [`(()=>{__app.applyMood('boarding'); __app.applySky('day'); __app.setView([0,0.6,26], 0.3, 55*Math.PI/180, 'xray')})()`, [], 'x-ray overview'],
};
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: +(process.env.DPR || 1) });
  const logs = [];
  page.on('pageerror', (e) => logs.push('pageerror ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/ERR_TUNNEL|ERR_CERT/.test(m.text())) logs.push('console ' + m.text()); });
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + page0);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  await page.evaluate(() => { for (const id of ['top', 'bottom', 'hint', 'loading']) { const e = document.getElementById(id); if (e) e.style.visibility = 'hidden'; } });
  await page.evaluate(PRE);
  const pairs = {};
  for (const n of (only.length ? only : Object.keys(VIEWS))) {
    const [expr, refs, what] = VIEWS[n];
    try { await page.evaluate(expr); } catch (e) { logs.push(n + ' view error ' + e.message); }
    await page.evaluate(() => __app.renderNow());
    await page.evaluate(() => __app.renderNow());
    await page.screenshot({ path: path.join(out, n + '.png'), timeout: 240000 });
    await page.evaluate(() => { if (__app.seated) { __app.setBed(false); __app.seated = null; __app.hideSeatBar(); } __app.mode = 'walk'; __app.scene.xray = false; window.__near = 0; __app.applyMood('boarding'); __app.applySky('day'); });
    pairs[n] = { img: path.resolve(out, n + '.png'), refs: refs.map((r) => path.resolve(__dirname, '../ref/ana', r + '-lang-multi.jpg')), what };
    console.log('shot', n);
  }
  fs.writeFileSync(path.join(out, 'pairs.json'), JSON.stringify(pairs, null, 1));
  console.log(logs.join('\n'));
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
