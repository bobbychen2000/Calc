// Brand x model livery textures (baked by tools/liveries/, listed in data/liveries/manifest.js): which texture an
// aircraft of a given brand, imported model and type wears, at which resolution.
//
// Every imported model (data/models/*.sfom) has a livery atlas as texture 0 (tools/liveries/atlas.py): the fuselage, fin,
// tailplane, nacelles, pylons, wing tips and gear doors laid out in one uniform texture. A livery is one texture in that
// layout, so wearing it is a single texture swap (js/live/aircraft.js here, js/three/aircraft.js in the three.js renderer).
// Types rendered with fuselage plugs (737-900 on the 737-800 model, 787-9/-10 on the 787-8 model, ...) or with a different
// cabin-window row than the model's own type (737 MAX 8 vs 737-800, A321neo vs A321, ...) have their own bake
// ("variants"), painted on the stretched airframe with that type's windows; the pseudo-brand `_N` holds their neutral skin.
// Resolutions: hi 2048 (stills, ?quality=ultra), mid 1024, lo 512 (small devices / snapshot artifact). Default 'auto':
// mid, or hi for the models whose atlas is coarse at mid (manifest `pxm` / 2 < 11 px per metre: A330, A350, A380, 747,
// MD-11), so a widebody's titles are as sharp as a narrowbody's; set window.SFO_LIVERY_RES to force one size.
import { LIVERY_MANIFEST } from '../../data/liveries/manifest.js';
import { TYPES } from './types.js';
import './fit.js';        // TYPES[t].fit (plugs) is filled in by fit.js at import

const byKey = new Map();
for (const e of LIVERY_MANIFEST.entries || []) byKey.set(e.brand + ':' + e.model, e);

export function liveryRes() {
  if (typeof window === 'undefined') return 'mid';
  if (window.SFO_LIVERY_RES) return window.SFO_LIVERY_RES;
  const q = new URLSearchParams(window.location ? window.location.search : '').get('quality');
  return q === 'ultra' ? 'hi' : 'auto';
}
const AUTO_MIN_PXM = 11;     // px per metre wanted at the default resolution (narrowbodies: 16-28 at mid)
export function liveryBase() { return (typeof window !== 'undefined' && window.SFO_LIVERY_BASE) || 'data/liveries/'; }

// airframe of a type on its model: the fuselage plugs (js/aircraft/fit.js); a bake painted for another airframe of the
// same model would smear its titles over a plug
const plugSig = (t) => { const p = TYPES[t] && TYPES[t].fit && TYPES[t].fit.plugs; return p ? p.d1 + '/' + p.d2 : ''; };
function pick(e, typeKey) {
  for (const v of [e, ...(e.variants || [])]) if (v.types && v.types.includes(typeKey)) return v;
  return null;
}
function fileOf(e, f, res) {
  if (res === 'auto') res = e.pxm && e.pxm / 2 < AUTO_MIN_PXM ? 'hi' : 'mid';
  return (f.files && (f.files[res] || f.files.mid || f.files.hi)) || f.file || null;
}
// -> { url, brand, model, types, key, neutral } or null when no baked livery exists for this brand on this model.
// The bake painted for this type (its fuselage plugs and its cabin-window row, tools/liveries/windows.py) when there is
// one; else a bake of the brand for the same airframe; else null (the caller falls back to neutralTextureFor).
export function liveryTextureFor(brand, modelKey, typeKey, res = liveryRes()) {
  if (!brand || !modelKey) return null;
  const e = byKey.get(brand + ':' + modelKey); if (!e) return null;
  let f = pick(e, typeKey);
  if (!f) for (const v of [e, ...(e.variants || [])]) if (v.painted_as && plugSig(v.painted_as) === plugSig(typeKey)) { f = v; break; }
  if (!f) return null;
  const file = fileOf(e, f, res); if (!file) return null;
  return { url: liveryBase() + file, brand, model: modelKey, types: f.types || e.types, key: file, neutral: false };
}
// the neutral (white, titles-free) skin baked for a type whose airframe or cabin windows differ from its model's own type
// (pseudo-brand `_N`), or null: the model's own atlas is right for it. Worn with the brand's runtime colours
// (uLivTex = 0: zone recolouring, as the model's own atlas).
export function neutralTextureFor(modelKey, typeKey, res = liveryRes()) {
  const e = byKey.get('_N:' + modelKey); if (!e) return null;
  const f = pick(e, typeKey); if (!f) return null;
  const file = fileOf(e, f, res); if (!file) return null;
  return { url: liveryBase() + file, brand: null, model: modelKey, types: f.types, key: file, neutral: true };
}
export const LIVERY_BRANDS = LIVERY_MANIFEST.brands || {};
// freighter brands: no cabin windows (js/shaders/aircraft_real.js uNoCabin)
export function brandIsCargo(brand) { return !!(brand && LIVERY_BRANDS[brand] && LIVERY_BRANDS[brand].cargo); }
