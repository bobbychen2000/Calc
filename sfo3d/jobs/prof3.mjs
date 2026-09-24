import { stToWorld } from '../js/geo.js';
export default async function ({ launch }) {
  const W = 1280, H = 720;
  const app = await launch({ W, H, msaa: 0, shadowRes: 4096 });
  const cam = { pos: stToWorld(3600, 120, 650), target: stToWorld(-300, -250, 0), fov: 0.85, near: 1, split: 3000, far: 150000 };
  const r = await app.page.evaluate(async (c) => {
    const { GROUND_VS, GROUND_FS } = await import('/js/shaders/ground.js');
    const R = APP.R; const o = {};
    const g = document.querySelector('canvas').getContext('webgl2');
    const sync = () => { const px = new Uint8Array(4); g.bindFramebuffer(g.FRAMEBUFFER, R.final.fb); g.readPixels(0,0,1,1,g.RGBA,g.UNSIGNED_BYTE,px); };
    const all = APP.scene.items;
    const time = (label, items) => { APP.scene.items = items; R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); const t0 = performance.now(); for (let i=0;i<2;i++) R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); o[label] = Math.round((performance.now() - t0)/2); };
    const ground = all.filter(i => i.prog === 'ground');
    const variants = {
      full: GROUND_FS,
      noRunway: GROUND_FS.replace('vec2 local; vec3 rw = runwayAt(st, fw, local);', 'vec2 local; vec3 rw = vec3(0);'),
      noUrban: GROUND_FS.replace('if (urb > 0.01) {', 'if (false) {'),
      noDetail: GROUND_FS.replace('if (dist < 400.0)', 'if (false)'),
      noSpec: GROUND_FS.replace('vec3 H = normalize(uSunDir + V); float spec', 'vec3 H = vec3(0,1,0); float spec = 0.0; float xx').replace('col += uSunColor * spec * (1.0 - rough) * 2.0;',''),
      noCloudSh: GROUND_FS.replace('* cloudShadow(wp)', ''),
    };
    for (const k in variants) { R.addProgram('v_' + k, GROUND_VS, variants[k]); time(k, ground.map(i => ({ ...i, prog: 'v_' + k }))); }
    APP.scene.items = all;
    return o;
  }, cam);
  console.log(JSON.stringify(r));
  await app.close();
}
