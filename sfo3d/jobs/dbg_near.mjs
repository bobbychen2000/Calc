export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  await page.evaluate(async () => { await new Promise(r => setTimeout(r, 2500)); });
  const r = await page.evaluate((names) => {
    const out = [];
    for (const n of names) {
      const g = SFO.world.gates.find(q => q.name === n); if (!g) continue;
      for (const t of SFO.traffic.tracks.values()) {
        const D = t.disp; const d = Math.hypot(D.x - g.w.x, D.z - g.w.z); if (d > 160) continue;
        out.push([n, t.info.flight || t.hex, t.info.icao, t.phase, t.gate ? t.gate.name : '-', d.toFixed(0), D.x.toFixed(1), D.z.toFixed(1), (D.hdg * 180 / Math.PI).toFixed(0), t.phys ? JSON.stringify(t.phys.off || t.phys.cur) : '']);
      }
    }
    return out;
  }, (process.env.NAMES || 'D4').split(','));
  for (const x of r) console.log(x.join(' | '));
};
