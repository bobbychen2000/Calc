# Brand liveries: requests to other owners (from the aircraft / liveries workflow), 24 Sep 2026

From: owner of `js/aircraft/**`, `js/live/aircraft.js`, `js/live/lookup.js`, `js/live/models.js`, `js/shaders/aircraft*.js`,
`data/brands.js`, `data/liveries/**`, `tools/liveries/**`. Implementation notes: `docs/research/liveries_impl.md`.

What changed for everybody:

- Every `data/models/*.sfom` now has a **livery atlas** as texture 0 (`head.atlas`, `tools/liveries/atlas.py`): fuselage,
  fin, tailplane, nacelle skins, pylons, wing tips and gear doors in one uniform layout (WebP, RGBA). Geometry and
  `MODEL_DIMS` / `MODEL_FEATURES` are unchanged; vertex counts changed (vertices are duplicated along chart seams).
  Alpha of the atlas: 1 paint, 0.75 unchanged dark skin, **< 0.5 cabin-window glass** painted into the atlas (737-800,
  747-400, A330-300, A380, CRJ200 have no window geometry).
- `js/live/models.js` marks the atlas draw (`draw.atlas = true`, uniforms `uAtlas = 1`, `uLivTex = 0`) and decodes WebP.
- A **brand livery** is one texture in that layout: `data/liveries/<BRAND>/<model>[@<type>]-{hi,mid,lo}.webp`
  (2048 / 1024 / 512 px), listed in `data/liveries/manifest.json` and `manifest.js`.
- The **brand** an aircraft wears: `js/live/lookup.js` `brandFor({airline, reg, hex, icaoType})` and
  `liveryForAirline(icao, reg, hex, icaoType)`: registration table (US DOT BTS, observed) -> series / operator majority
  (inferred) -> callsign airline. The livery object carries `brand`, `brandName`, `brandSrc` ('obs' | 'inf'),
  `brandWhy`, `reg`, `special`. `LiveAircraft` resolves the brand itself from its ICAO address (US N-number, verified
  decoding) while the track does not carry the registration, and exposes the resolved livery as `ac.liv`.

| File (owner) | Request |
|---|---|
| `js/live/traffic.js` | In `setInfo`, pass the registration, address and type: `tr.livery = liveryForAirline(al, I.reg, tr.hex, I.icao);` and publish `tr.brand = tr.livery.brand; tr.brandSrc = tr.livery.brandSrc;` (the three.js `LiveryLibrary.brandOf(tr)` reads `tr.brand`). One line; without it the legacy renderer still resolves on the aircraft, but the track (UI, three.js) sees only the callsign-level brand (e.g. every SkyWest E175 = United Express, `inf`). |
| `js/three/aircraft.js` | `LiveryLibrary`: the manifest is published. Entries: `{brand, model, file (= files.mid), files: {hi, mid, lo}, types, painted_as, variants: [{types, files, file, painted_as}]}`. Please (1) take the brand from `ac.liv.brand` (resolved per aircraft) before `tr.brand`; (2) pick the variant whose `types` contains `ac.type` (the TYPES key), else the entry: 737-900 / 787-9 / 787-10 / 757-300 / A350-1000 ... have their own bakes painted on the stretched fuselage; (3) resolution: `window.SFO_LIVERY_RES` or `hi` for `?quality=ultra`, else `mid`; (4) treat texture-0 alpha < 0.5 as window glass (dark glossy, warm cabin light at night like kind 1) for the atlas draws (`draw.atlas`), with or without a brand texture: `js/shaders/aircraft_real.js` shows the reference implementation (`winA`). `js/aircraft/liveries.js liveryTextureFor(brand, modelKey, typeKey, res)` does (2) and (3) and can be imported directly. |
| `js/live/about.js` (About / credits) | Add: "Airline names, logos and liveries are trademarks of their respective owners. They are re-drawn here for a non-commercial depiction of real traffic; no endorsement is implied." and "Livery textures: baked by tools/liveries from our own vector drawings on the FlightGear / FlightAirMap model textures (GPL-2.0, see docs/ATTRIBUTION_models.md); fonts: SIL Open Font License." |
| `js/live/ui.js` (aircraft panel) | Show the brand when it differs from the callsign airline: `ac.liv.brandName` (e.g. "United Express") with `ac.liv.brandSrc === 'inf'` marked as inferred (tooltip `ac.liv.brandWhy`). |
| packaging (artifact, 16 MB) | Ship the `lo` set only for the brands in the snapshot (`python3 tools/liveries/build.py --list-snapshot` prints the files, ~15-40 KB each) and set `window.SFO_LIVERY_RES = 'lo'` and `window.SFO_LIVERY_BASE` next to `SFO_MODEL_BASE`. The standalone app ships all three sets (`data/liveries/`). |
