export default async function ({ launch, registerStill }) {
  const W = 640, H = 360;
  const app = await launch({ W, H, msaa: 0, shadowRes: 4096 });
  await app.page.evaluate(() => window.setupShots(null));
  registerStill('dbg', W, H);
  const post = { exposure: 0.45, shutter: 0 };
  const variants = ['all', 'noAircraft', 'noObj', 'noObjI', 'none'];
  for (let i = 0; i < variants.length; i++) {
    const r = await app.page.evaluate(async ([v, i, post]) => {
      const S = APP.scene; const orig = S.frame.bind(S);
      S.frame = (T) => { const fr = orig(T); fr.items = fr.items.map(it => { const c = Object.assign({}, it);
        if (v === 'noAircraft' && it.prog === 'aircraft') c.castShadow = false;
        if (v === 'noObj' && it.prog === 'obj') c.castShadow = false;
        if (v === 'noObjI' && it.prog === 'objI') c.castShadow = false;
        if (v === 'none') c.castShadow = false; return c; }); return fr; };
      const ms = await window.renderShotStill(2, 0.8, 'dbg', i, 30, post);
      S.frame = orig; return ms;
    }, [variants[i], i, post]);
    console.log(variants[i], r);
  }
  await app.close();
}
