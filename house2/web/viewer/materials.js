// Material library: the GLB's materials are replaced by NAME.
// Entries come from the look modules in ./looks/ (one per asset family, each exporting register(lib)); the plain
// table below is the fallback for names no look module has claimed yet.  An entry is either a spec
//   { color, roughness, metalness, emissive, emissiveDay, emissiveDusk, glass, water }
// or a factory  (ctx) => THREE.Material  for textured / shader materials, where
//   ctx = { THREE, renderer, anisotropy, quality: 'high' | 'low', time: 'day' | 'dusk', envGain }.
// LIGHT (stage.js LOOK, sky.js; calibrated on the photos, do not re-tune materials against anything else): a neutral
// tone curve (display = scene colour up to ~0.76, soft shoulder above), a sunlit white wall (albedo 0.87) renders
// ~245, in open shade ~180.  The image-based light is ctx.envGain times brighter than the sky looks (the lifted
// shade of the photos): mirror-like materials (glass, water, polished metal) should set
// envMapIntensity = 1 / ctx.envGain (and again in lib.onTime) so their reflections match the visible sky.
// lib.onTime(fn) registers a callback fn(time) for day / dusk changes; lib.onTick(fn) a per-frame callback
// fn(seconds) for animated materials (the stage then renders continuously).
import * as THREE from 'three';
import * as surfaces from './looks/surfaces.js';
import * as water from './looks/water.js';
import * as plants from './looks/plants.js';
import * as fixtures from './looks/fixtures.js';
import * as glazing from './looks/glazing.js';
import * as furniture from './looks/furniture.js';
import * as house2 from './looks/house2.js';      // this property's own finishes: registered last, overrides the shared ones

export const FALLBACK = {
  siding_lap: { color: 0xf1f0ec, roughness: 0.72 },
  siding_bb: { color: 0xf1f0ec, roughness: 0.75 },
  trim_white: { color: 0xf4f3ef, roughness: 0.6 },
  soffit_white: { color: 0xe9e8e3, roughness: 0.8 },
  roof_seam: { color: 0x2b2f35, roughness: 0.42, metalness: 0.75 },
  roof_shingle: { color: 0x6c6c6e, roughness: 0.95 },
  roof_flat: { color: 0x3a3b3d, roughness: 0.9 },
  gutter_dark: { color: 0x202225, roughness: 0.5, metalness: 0.6 },
  frame_black: { color: 0x17181a, roughness: 0.5, metalness: 0.2 },
  glass: { color: 0x1d2a33, roughness: 0.06, glass: true },
  door_navy: { color: 0x1c2233, roughness: 0.45 },
  door_garage: { color: 0xf2f1ed, roughness: 0.6 },
  door_wood: { color: 0x5b3020, roughness: 0.55 },
  metal_awning: { color: 0x26282b, roughness: 0.45, metalness: 0.7 },
  chimney_white: { color: 0xf1f0ec, roughness: 0.75 },
  chimney_cap: { color: 0x25272a, roughness: 0.45, metalness: 0.7 },
  stone_veneer: { color: 0xb3aa9a, roughness: 0.9 },
  bluestone: { color: 0x7e8a92, roughness: 0.8 },
  paver_drive: { color: 0x8a8782, roughness: 0.9 },
  concrete: { color: 0xb9b6ae, roughness: 0.9 },
  coping: { color: 0xd9d4c8, roughness: 0.8 },
  pool_tile: { color: 0x2f5f8f, roughness: 0.3 },
  pool_water: { color: 0x39b6d6, roughness: 0.05, water: true },
  pergola_metal: { color: 0x3b3d40, roughness: 0.5, metalness: 0.5 },
  fence_wood: { color: 0x9a5a34, roughness: 0.85 },
  lawn: { color: 0x4f7a2c, roughness: 1.0 },
  mulch: { color: 0x5a3a26, roughness: 1.0 },
  soil: { color: 0x4a3c30, roughness: 1.0 },
  asphalt: { color: 0x4b4b4d, roughness: 0.95 },
  light_fixture: { color: 0x141516, roughness: 0.5, metalness: 0.4 },
  light_glow: { color: 0xfff1cf, roughness: 0.4, emissive: 0xffd9a0, emissiveDay: 0.15, emissiveDusk: 4.0 },
  solar: { color: 0x0d1016, roughness: 0.25, metalness: 0.3 },
  skylight_glass: { color: 0x9db2c2, roughness: 0.08 },
  foliage: { color: 0x3f6a2a, roughness: 0.9 },
  foliage_dark: { color: 0x2c4a22, roughness: 0.9 },
  foliage_gold: { color: 0xd9a51c, roughness: 0.9 },
  foliage_red: { color: 0xa32a1c, roughness: 0.9 },
  bark: { color: 0x5d5346, roughness: 1.0 },
  furniture_dark: { color: 0x34363a, roughness: 0.7 },
  furniture_wood: { color: 0x8a5a36, roughness: 0.7 },
  cushion: { color: 0xdcdcd8, roughness: 0.95 },
  neighbor_wall: { color: 0xb5b9bd, roughness: 0.9 },
  ground_far: { color: 0x717d66, roughness: 1.0 },
  neighbor_roof: { color: 0x5c5d60, roughness: 0.95 },
  interior_glow: { color: 0xffe2b0, roughness: 1.0, emissive: 0xffc98a, emissiveDay: 0.0, emissiveDusk: 2.2 },
};

export const CLAY = new THREE.MeshStandardMaterial({ color: 0xe9e7e2, roughness: 0.92, metalness: 0 });
export const CLAY_GLASS = new THREE.MeshStandardMaterial({ color: 0x8fa3b3, roughness: 0.35, metalness: 0 });
export const CLAY_WATER = new THREE.MeshStandardMaterial({ color: 0xb7d3df, roughness: 0.3, metalness: 0 });

export class Materials {
  constructor(renderer, quality = 'high') {
    this.cache = new Map();
    this.entries = new Map(Object.entries(FALLBACK));
    this.kinds = new Map();               // name -> { glass, water, cutout, noShadow }: flags the stage needs
    this.timeFns = [];
    this.tickFns = [];
    this.time = 'day';
    this.ctx = { THREE, renderer, quality, time: 'day', envGain: 1, anisotropy: renderer ? renderer.capabilities.getMaxAnisotropy() : 1 };
    const lib = {
      add: (name, entry, kind) => { this.entries.set(name, entry); if (kind) this.kinds.set(name, kind); },
      onTime: (fn) => this.timeFns.push(fn),
      onTick: (fn) => this.tickFns.push(fn),
      ctx: this.ctx,
    };
    for (const mod of [surfaces, water, plants, fixtures, glazing, furniture, house2]) if (mod.register) mod.register(lib);
  }

  // the GLB's own factors for a name the look modules do not define (zone builders add materials faster than looks)
  seed(m) {
    if (!m || !m.name || this.entries.has(m.name) || !m.color) return;
    this.entries.set(m.name, { color: m.color.getHex(), roughness: m.roughness ?? 0.8, metalness: m.metalness ?? 0 });
  }

  kind(name) {
    const e = this.entries.get(name);
    return this.kinds.get(name) || (e && typeof e === 'object' ? { glass: !!e.glass, water: !!e.water } : {});
  }

  get(name) {
    if (this.cache.has(name)) return this.cache.get(name);
    let e = this.entries.get(name);
    if (!e) { console.warn('material not in the library:', name); e = { color: 0xff00ff, roughness: 0.8 }; }
    let m;
    if (typeof e === 'function') {
      m = e(this.ctx);
    } else {
      m = new THREE.MeshStandardMaterial({ color: e.color, roughness: e.roughness ?? 0.8, metalness: e.metalness ?? 0 });
      if (e.emissive !== undefined) { m.emissive = new THREE.Color(e.emissive); m.emissiveIntensity = e.emissiveDay ?? 0; }
      if (e.glass) m.envMapIntensity = 1.0 / this.ctx.envGain;
      if (e.water) { m.transparent = true; m.opacity = 0.86; m.envMapIntensity = 1.0 / this.ctx.envGain; }
      m.userData.spec = e;
    }
    m.name = name;
    this.applySwatch(name, m);
    if (this.hook) this.hook(m);
    this.cache.set(name, m);
    return m;
  }

  // Swatches: small patches cut from the photographs (model/swatch.py), tiled with the model's UVs (metres).  The
  // patch carries the material's colour, so the base colour goes white; the relief of the procedural look stays.
  setSwatches(list, base) {
    this.swatches = list || {};
    this.swatchBase = base;
    for (const [name, m] of this.cache) this.applySwatch(name, m);
  }

  applySwatch(name, m) {
    const s = (this.swatches || {})[name];
    if (!s || m.userData.swatch || !m.isMeshStandardMaterial) return;
    m.userData.swatch = true;
    new THREE.TextureLoader().load(this.swatchBase + s.image, (t) => {
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.repeat.set(1 / s.size[0], 1 / s.size[1]);
      t.anisotropy = this.ctx.anisotropy;
      m.map = t;
      m.color.setRGB(1, 1, 1);
      // a look whose relief draws joints (flagstone, pavers, stacked stone) hands over a plain relief: the patch has its own
      if (m.userData.swatchNR) m.normalMap = m.userData.swatchNR;
      m.needsUpdate = true;
      if (this.onChange) this.onChange();
    });
  }

  clay(name) {
    const k = this.kind(name);
    return k.glass ? CLAY_GLASS : k.water ? CLAY_WATER : CLAY;
  }

  setTime(t) {
    this.time = this.ctx.time = t;
    for (const m of this.cache.values()) {
      const s = m.userData.spec;
      if (s && s.emissive !== undefined) m.emissiveIntensity = t === 'dusk' ? (s.emissiveDusk ?? 1) : (s.emissiveDay ?? 0);
    }
    for (const fn of this.timeFns) fn(t);
  }

  tick(seconds) {
    for (const fn of this.tickFns) fn(seconds);
    return this.tickFns.length > 0;
  }
}
