// load, report stand occupancy + physics stats, then render named views
export default async ({ page, shot, base }) => {
  const mode = process.env.MODE || 'snapshot';
  await page.goto(base + 'live.html?mode=' + mode);
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.evaluate(async () => { SFO.qa.hideUI(true); await new Promise(r => setTimeout(r, 2500)); await Promise.all(SFO.scene.aircraft.map(a => a.ready)); });
  const info = await page.evaluate(() => ({ occ: SFO.qa.gatesOccupied(), phys: SFO.physics.stats,
    moved: [...SFO.traffic.tracks.values()].filter(t => t.phys && t.phys.off && (t.phys.off[0] || t.phys.off[1])).map(t => [t.info.flight || t.hex, t.phys.off.map(v => v.toFixed(1)).join(','), t.phys.ok]) }));
  console.log('occupied', info.occ.join(' ')); console.log('physics', JSON.stringify(info.phys)); console.log('moved', JSON.stringify(info.moved));
  const views = (process.env.VIEWS || '').split(';').filter(Boolean);
  for (const v of views) {
    const [kind, arg] = v.split(':');
    const ok = await page.evaluate(([k, a]) => {
      const q = SFO.qa; const args = a ? a.split(',') : [];
      if (k === 'gate') return q.gate(args[0], +(args[1] || 38), +(args[2] || 1), +(args[3] || 9));
      if (k === 'look') { q.look([+args[0], +args[1], +args[2]], +args[3], +args[4], +args[5], +(args[6] || 50)); return true; }
      if (k === 'view') { SFO.view(args[0]); SFO.rig.anim && (SFO.rig.anim.t = 99); SFO.rig.update(0); return true; }
      if (k === 'tower') return q.tower(+(args[0] || 170), +(args[1] || 235), +(args[2] || 11));
      if (k === 'hold') return q.hold(+args[0], +(args[1] || 32));
      if (k === 'ac') return q.aircraft(args[0], +(args[1] || 60), args[2] ? +args[2] : null, +(args[3] || 10));
      return false;
    }, [kind, arg]);
    if (!ok) { console.log('view failed', v); continue; }
    await page.waitForTimeout(+(process.env.SETTLE || 2200));
    await shot((process.env.PREFIX || 'qa') + '_' + v.replace(/[^a-zA-Z0-9]+/g, '_'));
  }
};
