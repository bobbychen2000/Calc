// Forked from sfo3d/js/scene.js @ a967f9b. Kept: Scene(R, world), the per-frame item list (static world items + dynamic
// items), the program draw order for early-z (occluders first, ground last), the instanced additive light-sprite batch
// (20,000 sprites, same packing as sfo3d put()), the alpha-blended smoke batch, staticLights (sprite or (t) => sprites),
// smokeFns and extraItemFns hooks. Changed (fork map 2.5, risk 8): aircraft are generic *drawables* - any object with
// items(camPos) -> RenderItem[], lightSprites(t) -> Sprite[], commit() and `visible` - added with scene.add() and removed
// with scene.remove(); the scene imports nothing from js/aircraft/** and no gate system. scene.frame(t, camPos) calls
// world.staticSprites(t) when the world provides it only through staticLights (the app pushes it, fork map 2.10).
// OD4 iteration 3 (docs/phase3_models.md 15.7): put() packs a sprite's `pull` flag into iData.y (js/shaders/sprites.js:
// lights of detailed aircraft are pulled toward the camera by 3 m so the airframe beside a lens does not cut its disc).
// OD4 iteration 4 (review G1, docs/phase3_models.md 15.8): the pull alone let a light show through the airframe (the PC-12
// belly beacon on the wing root / fuselage side from any camera above the belly, the under-wing landing lamp through the
// wing): the sprite batch now asks the renderer for a copy of the scene depth (`needsDepth`, js/renderer.js copyDepth) when
// it holds a flagged sprite, and the sprite shader fades each flagged sprite by an occlusion test of its lens centre against
// that depth (js/shaders/sprites.js lensVisible). Unflagged sprites (airfield lights, placeholders) are drawn as before.
// OD4 iteration 5 (review F1 / F3, docs/phase3_models.md 15.9): a sprite is 32 floats (SPRITE_F; the light-sprite batch
// draws 8 instance vec4s): put() also packs the lamp's shape (s.occ) for that test.
// Dropped: parkAtGates (video era), the GateSystem / jet bridges, the procedural airliner programs ('aircraft', 'acr':
// P3 registers its own programs), stDir (SFO airport grid).
import { Mesh } from './gl.js';
import { v3 } from './math.js';
import { SPRITE_VS, SPRITE_FS, SMOKE_VS, SMOKE_FS } from './shaders/sprites.js';

const MAX_SPRITES = 20000;
// floats per light sprite (OD4 iteration 5: 16 as sfo3d + 16 for the lamp shape of a light on a detailed aircraft)
const SPRITE_F = 32;
// draw order (early-z): drawables' own programs and objects first, then decals / paint, then the ground last
const PRI = { acr: 0, aircraft: 0, ga: 0, obj: 1, objI: 1, sign: 1, decal: 2, mark: 2, paint: 2, water: 3, ground: 4 };

export class Scene {
  constructor(R, world) {
    this.R = R; this.world = world; this.drawables = []; this.staticLights = []; this.smokeFns = []; this.extraItemFns = [];
    R.addProgram('sprite', SPRITE_VS, SPRITE_FS);
    R.addProgram('smoke', SMOKE_VS, SMOKE_FS);
    const quad = new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, -1, 0, 1, 1, 0, -1, 1, 0]);
    this.smokeMesh = new Mesh({ pos: quad });
    this.spriteMesh = new Mesh({ pos: quad });
    this.spriteBuf = new Float32Array(SPRITE_F * MAX_SPRITES);
    this.spriteCount = 0;
  }
  // a drawable: { items(camPos), lightSprites(t), commit(), visible }
  add(d) { if (d && !this.drawables.includes(d)) this.drawables.push(d); return d; }
  remove(d) { const i = this.drawables.indexOf(d); if (i >= 0) this.drawables.splice(i, 1); return d; }
  frame(t, camPos) {
    const R = this.R;
    const items = this.world.items.slice();
    for (const d of this.drawables) {
      if (d.visible === false) continue;
      const it = d.items(camPos); for (let i = 0; i < it.length; i++) items.push(it[i]);
    }
    items.sort((a, b) => (PRI[a.prog] ?? 5) - (PRI[b.prog] ?? 5));
    for (const fn of this.extraItemFns) items.push(...fn(t));
    // light sprites
    let n = 0, nPull = 0; const B = this.spriteBuf;
    const put = (s) => {
      if (n >= MAX_SPRITES) return; const o = n * SPRITE_F;
      B[o] = s.p[0]; B[o + 1] = s.p[1]; B[o + 2] = s.p[2]; B[o + 3] = s.s; B[o + 4] = s.c[0]; B[o + 5] = s.c[1]; B[o + 6] = s.c[2]; B[o + 7] = s.i;
      const d = s.dir || [0, 1, 0]; B[o + 8] = d[0]; B[o + 9] = d[1]; B[o + 10] = d[2]; B[o + 11] = s.dir ? (s.k || 4) : 0; B[o + 12] = s.lens ? 1 : 0;
      B[o + 13] = s.pull ? 1 : 0;   // OD4 it. 3: pulled toward the camera by its drawn radius (js/shaders/sprites.js; detailed aircraft)
      if (s.pull) nPull++;          // OD4 it. 4 (G1): ... and faded by the lens occlusion test against the scene depth
      // OD4 it. 5 (F1 / F3): the lamp's own shape for that test (js/aircraft/detailed.js lightSprites s.occ: world centre c,
      // unit axes a0 / a1, half extents h, shape 1 ellipsoid / 2 box, geom 1 = its surface is in the scene depth, face =
      // { n, cos } for a one-sided lamp patch): iData.z / w, iL0..iL3 (js/shaders/sprites.js lensVisible); none -> 0
      const L = s.occ;
      if (L) { B[o + 14] = L.shape; B[o + 15] = L.geom;
        B[o + 16] = L.c[0]; B[o + 17] = L.c[1]; B[o + 18] = L.c[2]; B[o + 19] = L.h[0];
        B[o + 20] = L.a0[0]; B[o + 21] = L.a0[1]; B[o + 22] = L.a0[2]; B[o + 23] = L.h[1];
        B[o + 24] = L.a1[0]; B[o + 25] = L.a1[1]; B[o + 26] = L.a1[2]; B[o + 27] = L.h[2];
        const f = L.face; B[o + 28] = f ? f.n[0] : 0; B[o + 29] = f ? f.n[1] : 0; B[o + 30] = f ? f.n[2] : 0; B[o + 31] = f ? f.cos : -2; }
      else { for (let k = 14; k < SPRITE_F; k++) B[o + k] = 0; B[o + 31] = -2; }
      n++;
    };
    for (const d of this.drawables) { if (d.visible === false || !d.lightSprites) continue; const L = d.lightSprites(t); for (let i = 0; i < L.length; i++) put(L[i]); }
    for (const L of this.staticLights) { if (typeof L === 'function') L(t).forEach(put); else put(L); }
    this.spriteCount = n;
    this.spriteMesh.setInstances(B.subarray(0, n * SPRITE_F), n, SPRITE_F / 4);
    // smoke particles (back to front)
    const parts = []; for (const fn of this.smokeFns) parts.push(...fn(t));
    if (parts.length) {
      const cp = R.curCam ? R.curCam.pos : camPos || [0, 0, 0];
      parts.sort((a, b) => v3.dist(b.p, cp) - v3.dist(a.p, cp));
      const SB = new Float32Array(parts.length * 16);
      parts.forEach((q, i) => { const o = i * 16; SB[o] = q.p[0]; SB[o + 1] = q.p[1]; SB[o + 2] = q.p[2]; SB[o + 3] = q.s; SB[o + 4] = q.a; SB[o + 5] = q.seed; });
      this.smokeMesh.setInstances(SB, parts.length);
      items.push({ mesh: this.smokeMesh, prog: 'smoke', blend: 'alpha', bbox: null, castShadow: false, noCull: true,
        uniforms: () => { const C = R.curCam; const right = v3.norm(v3.cross(C.dir, C.up)); const up = v3.cross(right, C.dir); return { uCamRight: right, uCamUp: up }; } });
    }
    if (n) items.push({ mesh: this.spriteMesh, prog: 'sprite', blend: 'add', bbox: null, castShadow: false, noCull: true, needsDepth: nPull > 0,
      uniforms: () => { const C = R.curCam; const right = v3.norm(v3.cross(C.dir, C.up)); const up = v3.cross(right, C.dir);
        return { uCamRight: right, uCamUp: up, uFovScale: 2 * Math.tan(C.fov / 2) / R.H, uSceneDepth: R.sceneDepth || R.noDepth, uOcclude: R.sceneDepth ? 1 : 0 }; } });
    return { items };
  }
  commit() { for (const d of this.drawables) if (d.commit) d.commit(); }
}
