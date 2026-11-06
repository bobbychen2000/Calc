# Close-out round 3: consolidated open residuals (2026-11-06)

Machine-readable list: `docs/requests/closeout3_findings.json` (`groups.<track>.findings`, `owner_decisions`, `notes`).
One entry per real problem, owned by the track whose files must change (`routed_from` = the requesting track).
Built from the round-2 / continuation verifier and fixer outputs, the buildings workflow's last review and fix round,
the building manifests, `integration.json` (03:59Z), the `*_closeout.md` requests and `tools/sat/check.py`
(ISSUES 0, APP ISSUES 0, 17 WARNINGS). Not a scored QA pass.

| Track | Critical | Major | Minor | Total |
|---|---|---|---|---|
| static | 0 | 2 | 11 | 13 |
| bridges | 0 | 3 | 8 | 11 |
| realtime | 0 | 5 | 12 | 17 |
| aircraft | 0 | 1 | 9 | 10 |
| env | 0 | 3 | 13 | 16 |
| buildings | 0 | 4 | 10 | 14 |
| integration | 0 | 2 | 4 | 6 |
| **all** | 0 | 20 | 67 | 87 |

No critical item is open: the one critical finding of the last rounds (the ITB departures deck) is fixed in an
unreviewed round; its remaining part (the outer roadway band's level) is `integration-2`, major.

## Majors by track

**static**
- `static-1` Real aircraft drawn on unpaved cells of cluttered aprons (G/A pier aprons, FBO, south of pier B, ARFF apron); offpave.mask 1.38 M frames / 377 aircraft. (from realtime)
- `static-2` Observed (bridge, type) pairs refused for data reasons: A1 / A2 L2 reach, A6 / A11 upper deck, F11 L2 stow, F15 twin drums; models do not cover the stops. (from bridges)

**bridges**
- `bridges-1` One inferred 5.4 m departure level: 1,004 docked tunnels > 1:12, G7 / G8 / F5 slope refusals, BA-G walkways pierce the 6.5 m bump-outs, BA-C / BA-D roofs below the concourse floor. (from buildings)
- `bridges-2` Rotunda corridor drawn through the own fixed walkway on A12, F5, F14, F17, F19, F21 L1 (0.18-0.65 m2). (from static)
- `bridges-3` Regression: 737 MAX forward belt-loader conveyor ends 0.29-0.36 m below the fuselage (unpitched belly ellipse). (from aircraft)

**realtime**
- `realtime-1` Regression: lock.ref keeps a lock with no absolute bound (SWR35G drawn 7.9 m off G5 for 2 h 37 min, then removed as a ghost).
- `realtime-2` Parked aircraft removed on silence through occupy / stationary / ghost / 8 h expiry (8 aircraft, 340 aircraft-min).
- `realtime-3` A waiting ghost stays drawn on a newly heard parked aircraft at the same stand; cab through the fuselage (G13, G10).
- `realtime-4` Engine parks aircraft where their bridge cannot reach although the stop pose docks (bridge.refused 1.08 M frames / 19 aircraft).
- `realtime-5` An aircraft drawn inside the terminal ("building" 803 frames, unchanged; UAL1180 B77W at G8). (from bridges)

**aircraft**
- `aircraft-1` No stance-aware belly for consumers: the MAX nose-up stance moved renderedCrown but not Hc, which broke the belt-loader ellipse (`bridges-3`); fitted lower lobe above the ACAP cargo sills. (from bridges; restored to the source's major by the completeness critic)

**env**
- `env-1` unreviewed fix round: verify - env-fix2's 22 "fixed" items (incl. the critical aureole cut).
- `env-2` Wet apron mirrors no objects in daylight rain (no SSR / planar pass).
- `env-3` Aircraft in its own landing-light glow in night fog: veil fix not render-confirmed.

**buildings**
- `buildings-1` unreviewed fix round: verify - tower / ITB / domestic / landside fix round 2.
- `buildings-2` T2 shell over the departures curb roadway; the road is only cut at the wall (interim); move the T2 landside face 17-18 m east. (from integration)
- `buildings-3` AirTrain piers stand in road decks (3) and caps hang 3.25 m over a deck. (from integration)
- `buildings-4` F7 / F8 L1 drums 1.06 / 1.05 m inside the BA_F footprint and F8 L1 tunnel docked inside it (re-checked today). (from bridges)

**integration**
- `integration-1` unreviewed fix round: verify - ITB deck, T2 cut / solid test, phone per-unit loading, guideway clearance, LOD2 checker.
- `integration-2` ITB departures: outer ~10 m band built as a lower deck with a 0.4-0.6 m slit, against NAIP's continuous deck.

## Cross-track hand-offs worth knowing

- **Departure levels** (`bridges-1`): one inferred 5.4 m level drives the steep tunnels, the G7 / G8 / F5 slope
  refusals, the BA-G walkways piercing the 6.5 m bump-outs and the 23 BA-C / BA-D bulkheads. The buildings track
  now has photo evidence (BA-G walkway top <= 6.0 m, BA-C / BA-D floor ~3.5-4.0 m); bridges owns the change.
- **Drums vs assets** (`buildings-4`): re-checked today, 7 -> 3 overlaps; F7 / F8 L1 (1.06 / 1.05 m) and the F8 L1
  docked tunnel (0.58 m2) remain. `integration-5` / `bridges-6` let gates.js test against the real footprints.
- **Belt loaders** (`bridges-3` and `aircraft-1`, both major): the MAX stance broke the unpitched belly ellipse; bridges
  sets the conveyors from the pitched skin, aircraft publishes a stance-aware belly.
- **Domestic departures loop** (`buildings-14`, minor, new): the 4.877 m [unk] curb placeholder leaves a 3.53 m soffit
  over at-grade roads (manifest `#roadways.deviations[0]`); buildings sources the curb level, integration rebuilds.
- **Pavement** (`static-1`, major): real aircraft still drawn on unpaved cells of cluttered aprons.
- **Realtime** (`realtime-1..5`): lock without an absolute bound, removals on silence, a waiting ghost drawn over a
  parked aircraft, parking where the bridge cannot reach, an aircraft inside the terminal at G8.
- **Unreviewed fix rounds**: `env-1`, `buildings-1`, `integration-1` ask for an independent verify.

## Owner decisions

- `OD-1` Runway-configuration source when no ADS-B flow is seen (env Q9): may we use SFO's runway use programme (if you have it) or D-ATIS via atis.info (no published terms)? Default: ADS-B flow; else METAR fallback limited to the West / Southeast plans (Southeast only if the 28 tailwind >= 5 kt or crosswind >= 20 kt with a 19 headwind), instrument only on ends with a published approach; tagged I on the HUD.
- `OD-2` A clear civil-twilight reference photo looking west at SFO with open terms (dusk colour). Default: E3 dusk is judged against the CPU sky model; the 2016 photo is tagged "overcast dusk, not a colour reference".
- `OD-3` Night photos of SFO (env Q7): apron floodlight colour per terminal, jet-bridge lights, terminal glazing glow, the tower at night - a release gate of the night look. Default: Floodlight colour and mast-lamp intensity unchanged (NV), 25 % side / back lobe floor (I).
- `OD-4` Tower height family: F2 (rim 64.0 m, observation-anchored) or F1 (rim 67.36 m = published 221 ft)? Default: F2 (tower.glb); F1 via ?b3dtower=f1.
- `OD-5` Courtyard 3 Connector office block height (and its penthouse). Default: 33.0 m [inf] (range 32-36), penthouse top 38.0 m [obs, low].
- `OD-6` Grand Hyatt at SFO roof height. Default: 44 m [inf] (range 40-48).
- `OD-7` A real-GPU / phone run: A-PERF of the phone tier, the buildings near-mode and an SSR / planar reflection pass for wet airside objects. Default: Phone-tier caps (3/4 flood samples, 2 occlusion taps, <= 64 aureoles), wet surfaces mirror only the sky / IBL and lamps; all unmeasured on hardware.
- `OD-8` Rewrite git history to drop the 27 MB OSM pages and the 16 MB libvips binary (ee3822b)? Default: Left in history.
- `OD-9` Start the scored 7/10 visual QA loop? Default: Not run; this round is fix / verify only.
- `OD-10` flysfo-derived stand fields (names, classes, types; P1 / P2): keep, keep with attribution, or ADS-B only (keeps 3 of the 66 P1 types)? Default: Committed values kept; the flysfo snapshot stays local; refs/cache/stands/flysfo_provenance.json lists them.
- `OD-11` data/snapshot.js contains adsb.fi records whose terms forbid licensing: keep, rebuild from adsb.lol-only records, or remove from the public repo? Default: Published as is.
- `OD-12` Approve liveries for CAL / EVA cargo titles, CSG and JSX (photo references needed). Default: No brand drawn for these.
- `OD-13` Openly licensed reference photos of Boarding Areas B and A (facades). Default: BA-B materials unverified (published descriptions); BA-A bays are placeholders with BA-G band heights [inf].
- `OD-14` Which jet-bridge manufacturers / models does SFO use (A2 L2 needs 43.0 m for an A35K, beyond every Oshkosh unit)? Default: Oshkosh AeroTech datasheet ranges with <= 0.3 m over-travel (inferred); 158 dockings beyond the operational extension.
- `OD-15` Env Q1: where is the SFO rotating beacon? Default: No beacon drawn.
- `OD-16` Env Q2: which stations on the 28L / 28R approach piers are lit (night photos / imagery)? Default: FAA default station geometry from the landing threshold (NV).
- `OD-17` Env Q3: centreline lights on 10R/28L and 1L/19R (CS / NASR say yes, the AD note implies no). Default: RCL on all four runways (CS + NASR).
- `OD-18` Env Q4: taxiway lighting at a few holds (green centreline vs blue edge, lead-on / off coding, stop bars, RGLs). Default: Blue edge lights at the L-861T 2 cd minimum, labelled inf; no centreline / stop bars / RGLs.
- `OD-19` Env Q5 / Q6: REIL style (uni- / omnidirectional) and PAPI aiming set / night setting. Default: REIL style E unidirectional; PAPI HG4 + night 20 %.
- `OD-20` Env Q8: show archived real SFO weather as dated presets in the artifact, or only the snapshot's own weather? Default: Archived presets only via ?wx=; the snapshot ships its own 30 METARs / 7 TAFs.
- `OD-21` Env Q10: is the 28L MALSR controlled separately (TBL 3-4-7) or through the HIRL (TBL 3-4-9)? Default: TBL 3-4-7 (RAIL row since env-fix2).
- `OD-22` Env Q11: parked, powered aircraft at gates - nav and logo lights on or off? Default: Off when parked.
- `OD-23` Env Q12: add @takram/three-atmosphere (MIT) and ship its stars.bin (BSC5 terms unstated)? Default: No takram, no starfield; js/three/sky.js fallback.
- `OD-24` Env Q13: default night look - photographic (auto-exposed) or eye-like (darker, blue shift)? Default: Photographic auto-exposure.
- `OD-25` Env Q14: request the Falchi light-pollution raster (CC BY-NC 4.0) - is the app strictly non-commercial? Default: Artificial zenith luminance 3 mcd/m2 (x10 under a low deck), read coarsely from the published figure.
- `OD-26` Env Q15: may we survey windsock positions on NAIP (public domain), with X-Plane / OSM only as locators? Default: No windsocks drawn (wind drives water and rain slant).
- `OD-27` Env Q16: a licensable photo / video source to calibrate pavement drying and puddle look? Default: Wetness constants NV.
- `OD-28` Env Q17: FMH-1 (2019) PDF and Kasten & Czeplak (1980), if you can download them. Default: Not used.

## Left out (fixed with evidence) and lead items

See `notes` in the JSON.

## Completeness critic (2026-11-06)

Checked adversarially against the same sources (every `c3src` file, `manifest.json`, `integration.json` 03:59Z, the five
`*_closeout.md`). Every critical / major residual is present or shown fixed by a later source with evidence; the
consolidator's "left out as fixed" claims hold (gates.js / traffic.js / ground.js md5 = the replay roots 6a0aef2d /
4ff3753c / 0a5d8f0b; phone artifact 50daff2; chevrons 17.0 / 30.48 m; invariants.mjs uses `solids` / `bridgesOf` /
`doorOf`). Changes made in the JSON:

- `aircraft-1` minor -> **major**: the source (verify2 aircraft findings[0], a regression) is major and gives the
  stance-aware belly to the aircraft track first; nothing supported the lower severity of the split.
- New `buildings-14` (minor): the domestic departures loop has a 3.53 m soffit over at-grade roads (4.877 m [unk] curb
  placeholder; `manifest.json#roadways.deviations[0]`), below the 4.6 m the solve enforces elsewhere and not listed as a
  conflict in `integration.json`.
- Routed requests now stated in the owning track: `realtime-3` (send null before a different occupant; bridges verify2
  findings[0]), `buildings-12` (pier mullion finish in the spec; engine_closeout R2.4), `env-12` (`js/live/signs.js`
  counts retired polygons as movement surface; static_closeout R2.3), `integration-4` (WASM decoders belong in env's
  `vendor/**`).
- Evidence added: `realtime-11` (bridge.hit.tail 383 frames / 1 key and bridge.hit.wing 35, untraced), `env-1`
  (unexplained E4 light flicker 254 -> 0 between consecutive frames), `env-5` (strobe / tail white ~6,500 K [I]),
  `buildings-10` (open round-1 drawing requests; three-track AirTrain approach not modelled).

Track assignments follow the file-ownership table. `needs_owner` stays true only for the five owner-only items
(`static-13`, `realtime-17`, `aircraft-7`, `buildings-11`, `buildings-13`); the 28 owner decisions are unchanged.
Totals now: 87 entries, 0 critical / 20 major / 67 minor.
