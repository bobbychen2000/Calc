// Building views of SHA Live 3D (package P2d: terminals, tower, hangars, surroundings). Run through the harness:
//   SOFTGL=1 OUT=docs/phase2 PREFIX=buildings node livetest.mjs jobs/buildings.mjs
// VIEWS (';'-separated, default below): a name from NAMED, or look:x,y,z,yaw,pitch,dist[,fov] (SHA.qa.look), or
// view:<app view> (overview / t1 / t2 / tower / top / runways). Other env as jobs/views.mjs (T, QUERY, QUALITY, SHOWUI).
// Prints the terminals extension info (parts, hangars, towers, context blocks, far land cover) and the tower anchor.
const NAMED = {
  // T1 from the airside (west), the RWY 18L/36R side, as photo 02 (MNXANL 2023): tower behind the concourse, hall right
  t1: [[520, 2.5, 175], 270, 4, 620, 40],
  t1_close: [[480, 8, 220], 245, 10, 260, 50],
  // T2 from the airside (east), as the aerials 21 / 22: finger piers, central concourse, main hall behind
  t2: [[-1050, 2.5, 180], 100, 22, 1250, 50],
  t2_close: [[-1080, 8, 30], 120, 12, 360, 50],
  // the east control tower, close (photo 02 proportions) and from the apron
  tower: [[499.8, 24, 130.2], 262, 6, 140, 40],
  tower_far: [[499.8, 20, 130.2], 280, 3, 520, 30],
  // hangars: China Eastern (south-west, doors east) and the east hangar group (doors south)
  hangars: [[-800, 12, 1480], 95, 14, 330, 50],
  hangars_east: [[880, 10, -770], 205, 12, 420, 50],
  fbo: [[560, 6, 1080], 255, 12, 300, 50],
  hub: [[-1700, 10, 200], 125, 22, 1400, 50],
  sw: [[-950, 12, 1200], 100, 18, 700, 50],
  // oblique overview from the south-east (the core view) and a far one showing the surroundings and the haze
  overview: [[-300, 2.5, 150], 158, 33, 5600, 50],
  overview_far: [[-300, 2.5, 150], 150, 18, 11000, 55],
  // photo match, photo 02 (MNXANL 2023, 1920 x 1440, iPhone 1x lens: hfov 69.4 deg -> vfov 55.0 deg at 4:3): camera on the
  // RWY 18L/36R centreline abeam the tower (x -6, z 130, eye 4 m above the ground), optical axis 7.8 deg right of the tower
  // (tower at image x 770 of 1920) -> bearing 97.8 deg; rendered at 4:3. p02_tower: same camera, zoomed on the tower.
  p02: [[489.4, 2.5, 197.9], 277.8, 0.46, 500, 55.0, [1280, 960]],
  p02_tower: [[499.8, 24.5, 130.2], 270, -2.04, 506, 6.0, [960, 720]],
};
const DEFAULT = 'overview;overview_far;t1;t1_close;t2;t2_close;tower;tower_far;hangars;hangars_east;fbo;hub;sw';
export default async ({ page, shot, base, W, H }) => {
  const t = process.env.T || '2026-11-14T03:00:00Z';
  const q = `?fixedres=1&quality=${process.env.QUALITY || 'high'}&t=${encodeURIComponent(t)}${process.env.QUERY ? '&' + process.env.QUERY : ''}`;
  await page.goto(base + 'live.html' + q);
  await page.waitForFunction(() => window.__shaReady || window.__shaError, null, { timeout: 0 });
  const err = await page.evaluate(() => window.__shaError || null); if (err) { console.log('APP ERROR', err); throw new Error(err); }
  const info = await page.evaluate(() => SHA.qa.info());
  console.log('terminals', JSON.stringify(info.world.terminals));
  console.log('buildings', JSON.stringify(info.world.buildings), 'tower anchor', JSON.stringify(info.anchors.tower));
  if (!process.env.SHOWUI) await page.evaluate(() => SHA.qa.hideUI(true));
  const frames = (n) => page.evaluate((n) => new Promise(r => { let k = 0; const f = () => { if (++k >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }), n);
  for (const v of (process.env.VIEWS || DEFAULT).split(';').filter(Boolean)) {
    let ok = true;
    if (v.startsWith('look:')) { const p = v.slice(5).split(',').map(Number); await page.evaluate((p) => SHA.qa.look([p[0], p[1], p[2]], p[3], p[4], p[5], p[6] || 50), p); }
    else if (v.startsWith('view:')) ok = await page.evaluate((n) => SHA.qa.view(n), v.slice(5));
    else if (NAMED[v]) {
      const [tg, yaw, pitch, dist, fov, vp] = NAMED[v];
      if (vp) { await page.setViewportSize({ width: vp[0], height: vp[1] }); await frames(3); }
      await page.evaluate(([tg, yaw, pitch, dist, fov]) => SHA.qa.look(tg, yaw, pitch, dist, fov), [tg, yaw, pitch, dist, fov]);
    }
    else { console.log('unknown view', v); continue; }
    if (!ok) { console.log('view not available:', v); continue; }
    await frames(4); await frames(2);
    await shot((process.env.PREFIX || 'buildings') + '_' + v.replace(/[:,]/g, '_'));
    if (NAMED[v] && NAMED[v][5]) { await page.setViewportSize({ width: W, height: H }); await frames(3); }
  }
};
