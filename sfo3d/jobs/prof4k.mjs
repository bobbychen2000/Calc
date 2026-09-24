export default async function ({ launch, registerStill }) {
  const W = 3840, H = 2160;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096 });
  await app.page.evaluate(() => window.setupShots(null));
  registerStill('perf', W, H);
  for (const [i, t] of [[0, 4.5], [4, 12.0], [5, 4.0]]) {
    const r = await app.page.evaluate(async ([i, t]) => {
      await window.renderShotStill(i, t, 'perf', 98, 30, { exposure: 0.45, shutter: 0.5 });
      APP.R.profile = true; APP.R.prof = {};
      const t0 = performance.now();
      const S = APP.scene; const of = S.frame.bind(S); let fT = 0; S.frame = (T) => { const a = performance.now(); const r = of(T); fT += performance.now() - a; return r; };
      await window.renderShotStill(i, t + 0.033, 'perf', 97, 30, { exposure: 0.45, shutter: 0.5 });
      S.frame = of; APP.R.profile = false;
      const tris = {}; 
      return { total: Math.round(performance.now() - t0), sceneFrameJS: Math.round(fT), ...Object.fromEntries(Object.entries(APP.R.prof).map(([k, v]) => [k, Math.round(v)])) };
    }, [i, t]);
    console.log('shot', i, JSON.stringify(r));
  }
  await app.close();
}
