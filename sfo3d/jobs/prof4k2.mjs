export default async function ({ launch, registerStill }) {
  const W = 3840, H = 2160;
  const app = await launch({ W, H, msaa: 4, shadowRes: 4096 });
  await app.page.evaluate(() => window.setupShots(null));
  registerStill('perf', W, H);
  for (const v of ['all', 'noWater', 'noGround', 'noSprites', 'noAircraft', 'noObj']) {
    const r = await app.page.evaluate(async ([v]) => {
      const S = APP.scene; const of = S.frame.bind(S);
      S.frame = (T) => { const fr = of(T); fr.items = fr.items.filter(it => !((v === 'noWater' && it.prog === 'water') || (v === 'noGround' && it.prog === 'ground') || (v === 'noSprites' && it.prog === 'sprite') || (v === 'noAircraft' && it.prog === 'aircraft') || (v === 'noObj' && (it.prog === 'obj' || it.prog === 'objI')))); return fr; };
      await window.renderShotStill(0, 4.5, 'perf', 98, 30, { exposure: 0.45, shutter: 0.5 });
      APP.R.profile = true; APP.R.prof = {};
      await window.renderShotStill(0, 4.533, 'perf', 97, 30, { exposure: 0.45, shutter: 0.5 });
      APP.R.profile = false; S.frame = of;
      return Object.fromEntries(Object.entries(APP.R.prof).map(([k, x]) => [k, Math.round(x)]));
    }, [v]);
    console.log(v, JSON.stringify(r));
  }
  await app.close();
}
