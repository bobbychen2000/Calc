import { stToWorld } from '../js/geo.js';
export default async function ({ launch }) {
  const W = +(process.env.W || 1280), H = +(process.env.H || 720);
  const app = await launch({ W, H, msaa: +(process.env.MSAA ?? 4), shadowRes: 4096 });
  const cams = [{ pos: stToWorld(3600, 120, 650), target: stToWorld(-300, -250, 0), fov: 0.85, near: 1, split: 3000, far: 150000 },
                { pos: stToWorld(1760, 290, 22), target: stToWorld(900, 235, 3), fov: 0.7, near: 0.5, split: 2500, far: 150000 }];
  const r = await app.page.evaluate((cams) => {
    const R = APP.R; const out = [];
    const g = document.querySelector('canvas').getContext('webgl2');
    const sync = () => { const px = new Uint8Array(4); g.bindFramebuffer(g.FRAMEBUFFER, R.final.fb); g.readPixels(0,0,1,1,g.RGBA,g.UNSIGNED_BYTE,px); };
    for (const c of cams) {
      const o = {};
      R.render(APP.scene, c, 0, { exposure: 0.45, shutter: 0 }); sync();
      let t0 = performance.now(); R.render(APP.scene, c, 0, { exposure: 0.45, shutter: 0 }); sync(); o.full = Math.round(performance.now() - t0);
      const all = APP.scene.items;
      for (const kind of ['ground', 'water', 'decal']) {
        APP.scene.items = all.filter(i => i.prog === kind);
        t0 = performance.now(); R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); o[kind] = Math.round(performance.now() - t0);
      }
      APP.scene.items = [];
      t0 = performance.now(); R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); o.empty = Math.round(performance.now() - t0);
      APP.scene.items = all; out.push(o);
    }
    return out;
  }, cams);
  console.log(JSON.stringify(r));
  await app.close();
}
