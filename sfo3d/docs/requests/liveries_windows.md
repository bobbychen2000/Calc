# Cabin windows, fuselage plugs, neutral variants, freighters: requests to other owners (25 Sep 2026)

From: owner of `js/aircraft/**`, `js/live/aircraft.js`, `js/live/models.js`, `js/shaders/aircraft*.js`, `data/models/**`,
`data/liveries/**`, `tools/liveries/**`. Background: owner feedback "I see two sets of windows on these livery planes";
details and verification in `docs/research/liveries_impl.md` §8.

What changed for everybody (reload `data/models/*.sfom` and `data/liveries/**` together, the atlas layout changed):

- **Exactly one row of cabin windows per deck, at the manufacturer's stations** (Boeing CAD 3-views, Airbus AC,
  Bombardier APM; `tools/liveries/windows_ref.py`, `tools/liveries/windows.py`). On 11 of the 21 models the artist's
  windows (glass objects, openings in the skin, windows painted in the source texture) were removed in the atlas step
  and the reference row is painted into the livery textures (atlas alpha < 0.5 = glass). Kept artist glass: MD-11,
  757-200, A321 (they match the drawings), E-Jets, CRJ700/900, A220, 747-8 (no usable drawing).
- **Glass alpha is now 0.1** (was 0; WebP encoders dropped the colour of fully transparent texels). The existing
  `winA = 1 - smoothstep(0.35, 0.6, a)` needs no change.
- **Fuselage plugs**: the atlas splits every model at its plug stations (`js/aircraft/fit.js PLUG_AT`) into a 2 cm band
  with its own texels, so a stretched type (737-900, 787-10, ...) no longer smears one texel column over the plug.
  Negative plugs (737-700 on the 737-800 model, 767-200, A330-200/-800) now **remove** the section instead of sliding
  the aft body over the forward body (`js/live/models.js` `plugShift`, used by `decodeModel`, so the three.js path gets it
  through `geometryOf` / `getModel` automatically).
- **Neutral variants** (`_N` in `data/liveries/manifest.json`): the white, titles-free skin of every type whose airframe
  or window row differs from its model's own type (e.g. `_N/b738@b737`, `_N/a321@a21n`). An aircraft without a brand bake
  wears it with the brand's runtime colours (zone recolouring, `uLivTex = 0`), so its windows are right too.
- **Freighters**: brands flagged `cargo` in the manifest (`FDX`, `UPS`) get no painted windows; the kept artist glass of
  their models (MD-11, 757, 747-8) is shaded as painted-over window plugs (`js/shaders/aircraft_real.js` `uNoCabin`).

| File (owner) | Request |
|---|---|
| `js/three/aircraft.js` | (1) After the brand lookup, fall back to `neutralTextureFor(modelKey, typeKey, res)` from `js/aircraft/liveries.js` and draw it like the model's own atlas (zone recolouring, no `liveryTex` branch), else the model's atlas; `liveryTextureFor()` now returns `null` when the brand has no bake for the type's airframe (it no longer hands out a bake painted for another fuselage length). (2) Freighters: `brandIsCargo(brand)` from the same module -> in `realMaterial`, glass (kind 1) aft of the flight deck (`LP.x < -uFusB.z`) is shaded as paint in the top colour (`uTop`), no cabin light (reference: `js/shaders/aircraft_real.js`, `uNoCabin`). (3) Nothing else: plugs come with `decodeModel`. |
| packaging (artifact, 16 MB) | The `lo` file list for the snapshot changed (neutral variants added, variant names changed): re-run `python3 tools/liveries/build.py --list-snapshot`. |
