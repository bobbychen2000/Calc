// livetest.mjs job: phase-0 probe of three r186 WebGPURenderer in this browser (backend, TSL, CSM, GTAO, TRAA).
// SOFTGL=1 OUT=out/engine node livetest.mjs tools/build3/job_probe.mjs      (PROBE_Q="?debug=1&mode=..." to vary)
export default async ({ page, shot, base }) => {
  for (const q of (process.env.PROBE_Q || '?x=1').split(';')) {
    await page.goto(base + 'js/three/dev/probe.html' + q);
    await page.waitForFunction(() => window.__probe, null, { timeout: 0 });
    const r = await page.evaluate(() => window.__probe);
    console.log('probe' + q, JSON.stringify(r));
    await shot('probe_' + q.replace(/[^a-z0-9]+/gi, '_'));
  }
};
