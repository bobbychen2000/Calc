import { stToWorld } from '../js/geo.js';
export default async function ({ launch }) {
  const W = +(process.env.W || 1280), H = +(process.env.H || 720);
  const app = await launch({ W, H, msaa: +(process.env.MSAA ?? 0), shadowRes: 4096 });
  const cam = { pos: stToWorld(3600, 120, 650), target: stToWorld(-300, -250, 0), fov: 0.85, near: 1, split: 3000, far: 150000 };
  const r = await app.page.evaluate(async (c) => {
    const { GROUND_VS } = await import('/js/shaders/ground.js');
    const R = APP.R; const o = {};
    const g = document.querySelector('canvas').getContext('webgl2');
    const sync = () => { const px = new Uint8Array(4); g.bindFramebuffer(g.FRAMEBUFFER, R.final.fb); g.readPixels(0,0,1,1,g.RGBA,g.UNSIGNED_BYTE,px); };
    const all = APP.scene.items;
    const time = (label, items) => { APP.scene.items = items; R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); const t0 = performance.now(); for (let i=0;i<2;i++) R.render(APP.scene, c, 0, { exposure: 1, shutter: 0 }); sync(); o[label] = Math.round((performance.now() - t0)/2); };
    time('empty', []);
    const FS0 = `#include <common>\n#include <fout>\nin vec3 vWP; in vec3 vN;\nvoid main(){ writeOut(vec3(0.2), vWP, 1.0); }`;
    R.addProgram('g0', GROUND_VS, FS0);
    const FS1 = `#include <common>\n#include <fout>\nin vec3 vWP; in vec3 vN;\nuniform sampler2D uAptAlb; void main(){ vec3 c = texture(uAptAlb, vWP.xz*0.0001).rgb; writeOut(c, vWP, 1.0); }`;
    R.addProgram('g1', GROUND_VS, FS1);
    const FS2 = `#include <common>\n#include <fout>\nin vec3 vWP; in vec3 vN;\nvoid main(){ vec3 c = applyFog(vec3(0.2), vWP); writeOut(c, vWP, 1.0); }`;
    R.addProgram('g2', GROUND_VS, FS2);
    const FS3 = `#include <common>\n#include <shadow>\n#include <fout>\nin vec3 vWP; in vec3 vN;\nvoid main(){ float s = getShadow(vWP, vec3(0,1,0), length(vWP-uCamPos)); writeOut(vec3(s), vWP, 1.0); }`;
    R.addProgram('g3', GROUND_VS, FS3);
    const ground = all.filter(i => i.prog === 'ground');
    time('groundFull', ground);
    for (const p of ['g0','g1','g2','g3']) time(p, ground.map(i => ({ ...i, prog: p })));
    APP.scene.items = all;
    return o;
  }, cam);
  console.log(JSON.stringify(r));
  await app.close();
}
