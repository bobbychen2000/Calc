// Brand x model livery textures (baked by tools/liveries/, listed in data/liveries/manifest.js): which texture an
// aircraft of a given brand, imported model and type wears, at which resolution.
//
// Every imported model (data/models/*.sfom) has a livery atlas as texture 0 (tools/liveries/atlas.py): the fuselage, fin,
// tailplane, nacelles, pylons, wing tips and gear doors laid out in one uniform texture. A livery is one texture in that
// layout, so wearing it is a single texture swap (js/live/aircraft.js here, js/three/aircraft.js in the three.js renderer).
// Types rendered with fuselage plugs (737-900 on the 737-800 model, 787-9/-10 on the 787-8 model, ...) have their own
// bake ("variants"), painted on the stretched airframe, so titles are not smeared by a plug.
// Resolutions: hi 2048 (stills, ?quality=ultra), mid 1024, lo 512 (small devices / snapshot artifact). Default 'auto':
// mid, or hi for the models whose atlas is coarse at mid (manifest `pxm` / 2 < 11 px per metre: A330, A350, A380, 747,
// MD-11), so a widebody's titles are as sharp as a narrowbody's; set window.SFO_LIVERY_RES to force one size.
import { LIVERY_MANIFEST } from '../../data/liveries/manifest.js';

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

// -> { url, brand, model, types, key } or null when no baked livery exists for this brand on this model
export function liveryTextureFor(brand, modelKey, typeKey, res = liveryRes()) {
  if (!brand || !modelKey) return null;
  const e = byKey.get(brand + ':' + modelKey); if (!e) return null;
  let f = e;
  for (const v of e.variants || []) if (v.types.includes(typeKey)) { f = v; break; }
  if (res === 'auto') res = e.pxm && e.pxm / 2 < AUTO_MIN_PXM ? 'hi' : 'mid';
  const file = (f.files && (f.files[res] || f.files.mid || f.files.hi)) || f.file;
  if (!file) return null;
  return { url: liveryBase() + file, brand, model: modelKey, types: f.types || e.types, key: file };
}
export const LIVERY_BRANDS = LIVERY_MANIFEST.brands || {};
