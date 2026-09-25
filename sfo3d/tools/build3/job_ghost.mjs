// livetest.mjs job: TRAA disocclusion A/B (review round 1). Runs js/three/dev/ghosttest.html with the vendored (patched)
// three and, if PREV is set to an unpatched build (e.g. `git show <rev>:vendor/three/three.module.js > out/three_prev.js`),
// the same test through an import map that points the vendor module at it. Prints window.__probe of each.
import fs from 'fs'; import path from 'path';
export default async ({ page, base, shot }) => {
  const pages = ['js/three/dev/ghosttest.html?v=patched'];
  if (process.env.PREV) {
    const html = fs.readFileSync('js/three/dev/ghosttest.html', 'utf8').replace('<head>', '<head><script type="importmap">{"imports":{"/vendor/three/three.module.js":"/' + process.env.PREV + '"}}</script>');
    fs.mkdirSync('out/ghost', { recursive: true }); fs.writeFileSync('out/ghost/ghost_prev.html', html); pages.push('out/ghost/ghost_prev.html?v=unpatched');
  }
  for (const p of pages) {
    await page.goto(base + p);
    await page.waitForFunction(() => window.__probe, null, { timeout: 0, polling: 500 });
    console.log('GHOST', p, JSON.stringify(await page.evaluate(() => window.__probe)));
    await shot('ghost_' + p.replace(/^.*v=/, ''));
  }
};
