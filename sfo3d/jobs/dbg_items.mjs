export default async ({ page, shot, base }) => {
  await page.goto(base + 'live.html?mode=snapshot');
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: 0 });
  const r = await page.evaluate(() => {
    const it = SFO.world.items.filter(i => i.prog !== 'ground').map(i => i.prog + (i.mesh && i.mesh.count != null ? ':' + i.mesh.count : '') + (i.nearOnly ? ':near' : ''));
    const g = SFO.world.gates.find(q => q.name === 'G6');
    return { items: it.join(' '), g6: g && { nose: g.nose, dir: g.dir, maxLen: g.maxLen, bridges: g.bridges.length, w: g.w } };
  });
  console.log(JSON.stringify(r));
};
