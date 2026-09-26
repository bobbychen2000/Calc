# Requests from the static fix-up (26 Sep 2026)

From the owner of the static data (`data/sfo_*`, `tools/stands/**`, `tools/build_*.py`, `js/live/airport.js`
standGates / landside) to the workflows that own the files named below. What changed in the data and why:
`docs/research/stands_rebuild.md` §15. Nothing here is committed by me.

## 1. Real-time workflow (`tools/live/**`, `js/live/traffic.js`)

1. **`tools/live/gatecheck.py` still uses the legacy projection.** Its docstring and code reimplement the old
   `js/geo.js llToEN` (ARP 37.6188056 N / -122.3754167 E, 110990 m per degree latitude, 111320 cos(lat) per degree
   longitude, x = E, z = -N). The app and every data file are in the `ltp-nad83-2011` frame since the frame switch
   (`tools/geo_frame.py` = `js/geo.js`; `docs/requests/geo_frame_switch.md`). Its `check` verdicts therefore compare
   aircraft and stands in two frames (offsets of metres at the piers). Please convert with
   `geo_frame.wgs84_to_world(lat, lon)` (as `tools/stands/adsb_parked.py` does) and re-run the 24 Sep comparison.
   (`tools/stands/build_stands.py` imports gatecheck only for its flysfo readers - unaffected.)
2. **Stands whose axis moved** (ADS-B axis, `axis_adsb`): D3 (13.1 -> 25.6 deg, nose +4.7 m along / -2.8 m lateral),
   D4 (1.0 -> 26.5 deg), D9 (257.5 -> 269.1 deg, nose -4.2 / +6.5 m). 9 / 7 / 3 aircraft with SFO stand windows parked
   there consistently; the OSM lead-ins and NAIP 2024 show the earlier layout. Any cached stand geometry (matcher
   tables, snapshot-derived tests, `tools/live/invariants.mjs` expectations) needs re-reading from `data/sfo_stands.js`.
   `leadin` of these stands is a straight inferred 40 m line (`leadin_src`).
3. **Per-family stops changed** (the family ADS-B reference is now the median over stands, not over aircraft; the
   A220 reference had flipped between -15.0 and -10.4 m with one aircraft): new `type_stops` D10 A220 -11.9 m, D11
   A220 -9.4 m; E12 families at -17.8 m; F-pier inferred stops shifted by <= 1.5 m. G7's A319 stop (-27.7 m) is GONE:
   it came from one 234 s hold before SFO's stand window (`stops_rejected`). If traffic.js uses per-type stops
   (static_geometry_round3/4 requests), it must read `type_stops` fresh; if it still uses one stop per stand, nothing
   changes for it.
4. **Classes from final plans** (`superseded_types`): D5 E -> CL (its only B772 plan was moved to F15), E12 CL -> C
   (B753 moved to F11), G12 keeps E from a superseded plan only (flagged in `cls_src`). standFits limits follow.
5. **Pairs below ICAO** now carry evidence per neighbour (`below_icao`: SFO plan overlaps, ADS-B-confirmed windows,
   the type pairs SFO plans together and their clearance). For 7 of 12 pairs the types SFO actually plans together
   clear ICAO; the below-ICAO case is a combination SFO does not plan. If traffic.js ever places aircraft that SFO did
   NOT allocate (strict ADS-B matching), it should honour `types_ok` on F19 / F20 on every path
   (`types_ok_all_paths`, unchanged request from round 4: the only remaining APP ISSUE, 1.9 m).
6. **A32x / A220 ADS-B reference** (unchanged, restated because round 4 read it as a stop difference): A320-family
   aircraft report positions 1.8 m behind the nose (per-stand median), B737 9.4 m, E-Jets 13.4 m, A220 5.7 m. Inferred
   explanation: transponders that apply the DO-260B "position offset applied" correction report the nose-referenced
   point; the 737 fleet reports the GNSS antenna. Evidence it is not a stop difference: at the B-pier stands the A32x
   positions lie within 4 m of the model nose, and an A32x nose 8 m further forward would be inside the bridge / facade
   there. The app's single `ANT = 0.2 L` fits the Boeing family only.

## 2. Bridges workflow (`js/live/gates.js`)

1. New per-bridge fields passed by `standGates()`: `shortUnit` (F5 L1: an imaged bridge shorter than every Oshkosh
   unit - its `extRange` 6.7-8.0 m is below 9.846 m ON PURPOSE; please do not clamp it to the datasheet minimum) and
   `dockOutWhy` (A1 / A2 L2: `{B78X: reason}` - the 787-10's L2 door is beyond the longest datasheet unit, so the L2
   stays at `stowW` and only L1 docks; `dockTypesOut` already contains B78X).
2. Alternative positions: `sharedBridgeUse` on B5S / B16S / C9V lists, per base bridge, `osm_id`, `of`, `door`,
   `dock_types` (the alternative's accepted types that bridge docks within its range), `dock_types_out` and
   `rest_clear_m` (its data rest pose vs the alternative's envelope: B5 L1 2.8 m, B16 L1 1.8 m, C9 L1 1.1 m). One
   bridge still exists once (drawn by the base gate); dock it to whichever of base / alternative is occupied (they are
   mutually exclusive, `excl`). B11S has its own bridge.
3. Rest poses (`stowW`) changed at F14 / F17 / F19 / F21 L1: where no pose keeps the ICAO clearance the builder now
   keeps the pose with the LARGEST clearance (F17 1.0 -> 2.7 m, F14 3.2 -> 5.0, F19 3.3 -> 5.3, F21 3.0 -> 3.9 m).
   Still below the ICAO 7.5 m for the 757: listed as evidence conflicts (the OSM rotunda itself is 3.5-5.7 m from the
   757 wing there).
4. D3 / D4 / D9 bridges now dock to the moved stands (same OSM bridges; new docked directions and rest poses).

## 3. Buildings workflow (`tools/buildings/**`)

`data/sfo_buildings.*` (still generated by `tools/build_terminal_parts.py`) is cut back at the T1 north face and the T3
landside face by the OSM "Departures" / "Arrivals" carriageways (1254 m2 / 534 m2; `footprint_accuracy.trimmed`).
`data/sfo_landside.*` (new, OSM, ODbL) carries landside roads (at-grade and elevated footprints) and car parks with
`kind: 'garage'` for the multi-storey garages - usable as footprints if you model the landside buildings.
