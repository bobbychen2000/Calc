// livetest.mjs job (integration review round 2, finding 2): why the domestic BA-B curtain wall reads as a black slab in the
// three.js low tier at the B20 gate view while Cycles shows mid-grey glass with light frames. One page load (low tier,
// ?b3donly=domestic&b3d=near), the gate view, then A/B variants applied live to the loaded domestic materials, one shot each:
//   base | finsOn (fin nodes forced visible) | noAO (glass aoMap off) | envX2 (glass envMapIntensity 2) | noNormal (normal map off)
// and the glass material's properties logged (what three built from the glTF).
//   flock out/.heavy.lock env SOFTGL=1 W=960 H=540 OUT=out/buildings3d/integ/r4/glass node livetest.mjs tools/blender/b3d_glass_job.mjs
import fs from 'fs'; import path from 'path';
export default async ({ page, shot, base, OUT }) => {
  const view = process.env.VIEW || 'gate:B20,110,1,12';
  await page.goto(base + 'live3.html?' + (process.env.QS || 'mode=snapshot&res=1&tier=low&b3d=near&b3donly=domestic'));
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 900000 });
  await page.evaluate(async () => { SFO.qa.hideUI(true); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  await page.waitForFunction(() => SFO.R.isComplete && SFO.R.isComplete() && SFO.R.frames > 2, null, { timeout: 0, polling: 500 });
  await page.waitForFunction(() => !SFO.R.b3d || SFO.R.b3d.done, null, { timeout: 0, polling: 1000 });
  const [k, a] = view.split(':'); const args = a.split(',');
  await page.evaluate(([k, args]) => { if (k === 'gate') SFO.qa.gate(args[0], +args[1], +args[2], +args[3]); else SFO.qa.look([+args[0], +args[1], +args[2]], +args[3], +args[4], +args[5], +(args[6] || 50)); }, [k, args]);
  await page.evaluate(() => { window.__f = SFO.R.frames; });
  await page.waitForFunction(() => { const B = SFO.R.b3d; return SFO.R.frames > window.__f + 12 && B.settled(); }, null, { timeout: 0, polling: 500 });
  const info = await page.evaluate(() => {
    const B = SFO.R.b3d; const out = { b3d: B.info().kind, units: B.info().unitsAtLod, mats: [] }; const seen = new Set();
    B.group.traverse(o => { if (!o.isMesh) return; for (const m of [].concat(o.material)) { if (seen.has(m) || !/^glass_ec|^mullion/.test(m.name)) continue; seen.add(m);
      out.mats.push({ name: m.name, type: m.type, color: m.color && m.color.toArray().map(v => +v.toFixed(3)), metal: m.metalness, rough: m.roughness, ior: m.ior, specI: m.specularIntensity,
        specC: m.specularColor && m.specularColor.toArray(), envI: m.envMapIntensity, map: !!m.map, ao: !!m.aoMap, aoI: m.aoMapIntensity, nrm: !!m.normalMap, nrmS: m.normalScale && m.normalScale.toArray(), side: m.side }); } });
    out.env = !!SFO.R.engine.scene.environment; out.r = SFO.R.debugInfo(); return out;
  });
  console.log('GLASS', JSON.stringify(info));
  const variants = [
    ['base', null],
    ['finsOn', 'fins'],
    ['noAO', 'ao'],
    ['envX2', 'env'],
    ['noNormal', 'nrm'],
  ];
  for (const [name, v] of variants) {
    await page.evaluate((v) => {
      const B = SFO.R.b3d; window.__glassV = v;
      B.group.traverse(o => {
        if (v === 'fins' && /_fins/.test(o.name)) { o.visible = true; o.userData.__force = true; }
        if (!o.isMesh) return;
        for (const m of [].concat(o.material)) {
          if (!/^glass_ec/.test(m.name)) continue;
          if (!m.userData.__orig) m.userData.__orig = { ao: m.aoMap, env: m.envMapIntensity, nrm: m.normalMap };
          const O = m.userData.__orig; m.aoMap = v === 'ao' ? null : O.ao; m.envMapIntensity = v === 'env' ? 2 * O.env : O.env; m.normalMap = v === 'nrm' ? null : O.nrm; m.needsUpdate = true;
        }
      });
      if (v === 'fins') { B.__u = B.update.bind(B); B.update = (p) => { B.__u(p); B.group.traverse(o => { if (o.userData.__force) o.visible = true; }); }; }
      else if (B.__u) { B.update = B.__u; delete B.__u; }
    }, v);
    const f0 = await page.evaluate(() => SFO.R.frames);
    await page.waitForFunction((f) => SFO.R.frames >= f + 10, f0, { timeout: 0, polling: 200 });
    await shot('glass_' + name);
  }
  fs.writeFileSync(path.join(OUT, 'glass_info.json'), JSON.stringify(info, null, 1));
};
