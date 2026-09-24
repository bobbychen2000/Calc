export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  await page.waitForTimeout(1500);
  const r = await page.evaluate(async () => {
    const T = SFO.traffic; const out = { models: [], near: [] };
    for (const a of SFO.scene.aircraft) out.models.push([a.id, a.type, a.modelKey, !!a.model]);
    try { await Promise.all(SFO.scene.aircraft.map(a => a.ready)); } catch (e) { out.err = String(e); }
    out.after = SFO.scene.aircraft.filter(a => a.model).length;
    for (const tr of T.tracks.values()) {
      const f = tr.last; if (!f.ground) continue;
      let best = null;
      for (const g of T.gates) { const d = Math.hypot(f.x - g.w.x, f.z - g.w.z); if (!best || d < best.d) best = { g: g.name, d: Math.round(d), lat: Math.round(-(f.x - g.w.x) * g.w.dz + (f.z - g.w.z) * g.w.dx), lon: Math.round((f.x - g.w.x) * g.w.dx + (f.z - g.w.z) * g.w.dz), bridge: g.bridge }; }
      out.near.push([tr.info.flight, tr.info.icao, Math.round(f.gs / 0.514), tr.phase, tr.gate ? tr.gate.name : '-', JSON.stringify(best)]);
    }
    return out;
  });
  console.log('models', JSON.stringify(r.models.slice(0, 8)), 'after', r.after, r.err || '');
  for (const n of r.near) console.log(n.join('  '));
};
