# Phase 2c: stands, jet bridges, VDGS, stand signs, remote-stand equipment

Date: 2026-11-20. Package P2c of Phase 2 (docs/PLAN.md §7), on the core fork (commit 8ca06f7, docs/phase2/core.md).
Fork base: sfo3d @ **e3218d6**. Nothing in `sfo3d/`, `pc12/` or `hwd3d/` was modified; nothing was committed.

Tags as in docs/PLAN.md: **obs** (seen in a source / measured), **inf** (inferred: rule, default or placeholder).
Standard: CAAC **MH 5001-2021** 《民用机场飞行区技术标准》 (docs/phase1/standards_refs.md §1; clauses cited below were read
in the local copy `refs/cache/standards/caac_mh5001_2021/MH5001-2021.pdf`, short parameters only).

**Result.** All 164 stands of `window.SHA_STANDS` are live gate objects. The 56 data bridges (13 seen on the Umbra SAR,
43 inferred from OSM gate nodes; one per stand) are sfo3d's apron-drive bridges - fixed walkway on columns, rotunda on its
pedestal, rotunda corridor, three telescoping tunnels, drive column and bogie, PCA unit, cab bubble with rotating cab,
bellows fitted to the drawn fuselage, service landing and stair, floodlight and beacon - built from the data's attach /
walkway / rotunda points. Each contact stand has a VDGS unit with a CAAC stand-number sign above it, and each bridge a
CAAC triangular-prism stand-number sign on its rotunda. Remote stands have post-mounted stand-number signs, an idle stair
unit as a cue, and passenger stairs plus apron buses when an aircraft is parked. A DEBUG option parks static aircraft
(models by URL from `../sfo3d/data/models/`) to check scale, docking and GSE. A DEBUG overlay draws every stand's lead-in
and push-back path. With the class reference aircraft parked, **54 of 56 bridges dock**. The two that do not (111, 235)
would need a cab turn beyond the sell sheet's limit (§2.6).

![T2 north pier, DEBUG aircraft parked](gates_t2_north_pier.png)

---

## 1. Files

Each forked file starts with `forked from sfo3d@e3218d6 <path>`.

| File | Status | Contents |
|---|---|---|
| `js/live/gates.js` | **rewritten** (was the core's stub; forked from sfo3d `js/live/airport.js` standGates + the `js/live/app.js` gate glue) | the extension: `shaGates(stands, hdgVec)` (data → gate objects), the reach fix (§2.4), `setGateWorld` input (T1 / T2 outlines, apron lanes, pavement), `gsign` program, the system start, DEBUG park and push overlay, light sprites, QA hooks, statistics and the legend text |
| `js/live/gate_system.js` | adapted (fork of sfo3d `js/live/gates.js`, committed half-done by the interrupted attempt; finished here) | the engine. Kept: bridge kinematics, docking paths, solids, rest poses per occupant, VDGS placement, GSE hull tests. Changed: §2-§5 (no module-scope data; world coordinates; `autoModel`, `autoRest`, SHA height targets, CAAC signs, remote stands, glazed sides, sign-housing fix). The interrupted attempt's duplicate imports (`newSignGeo` / `signQuad` / `meshOfSign` both imported and declared: a SyntaxError) and its calls of non-existent functions (`remoteGeo`, `stairShape` …) are resolved |
| `js/live/gate_signs.js` | **new** (fork of the `SIGN_VS` / `SIGN_FS` / `makeAtlas` parts of sfo3d `js/live/signs.js`) | the `gsign` program and the atlas of CAAC stand-number faces and VDGS display text; no FAA sign faces |
| `js/world/gates.js` | adapted | GSE meshes (sfo3d's set unchanged) + **new** passenger stairs (one mesh per 0.1 m of door sill) and apron bus; `stairDoors`, `stairShape`, `stairHull`, `BUS_HULL`. Removed: the SFO-grid import (`stToWorld`, which the sha3d `geo.js` does not export, so the core's copy could not load) and sfo3d's legacy offline `GateSystem` class |
| `jobs/gates.mjs` | **new** | the renders and checks of this report (`SOFTGL=1 OUT=docs/phase2 PREFIX=gates node livetest.mjs jobs/gates.mjs`) |
| `tools/gates/plate_compare.py` | **new** | the plate-vs-render comparison image (§8) |
| `docs/phase2/gates.md`, `gates_*.png` | **new** | this report, renders at deviceScaleFactor 1 |

No core file was edited: everything plugs in through `registerExtension({name: 'gates', …})` (js/live/ext.js).

## 2. Jet bridges

### 2.1 Data → gate objects (`shaGates`, sfo3d `standGates`)

World coordinates throughout: `g.nose` = the data stop point `[x, z]`, `g.dir` = `hdgVec(hdg)`. The engine's s,t helpers
(`stW`, `stD`) are the identity. Per bridge the data gives `attach`, `rotunda`, `walk` (attach → rotunda), `cab` (docked at
door 1 of the class reference, inf), `reach_m`, `src`. These map to the sfo3d fields `attachW`, `rotundaW`, `walkW`,
`cabW`. Walks shorter than 0.5 m become null: the T1 west face, where the rotunda is the facade gate node. The data has no
`model`, `ext_range`, `stow`, `rotunda_max_r`, `cab_convention` or `type_stops`. Those are inferred (§2.2-2.3) or take the
donor's defaults: cab sense CW = −1 as sfo3d inferred it, rotunda radius ≤ 2.45 m, and every type stopping with its
nose tip on the stop point, as in the data's `nose_note` (superseded: fix round 1 F1, the nose wheel stops on the node). Alternative positions 238A / 259A (`bridge_status: shared`)
share the bridge of 238 / 259 (`sharesBridgesOf`). The engine docks that bridge to whichever position is occupied.

Class limits come from the data's `class_max` and `span_max` (`maxSpan` = min(class, span_max + 0.1)). The accepted types
of a stand are the modelled types within those limits (sfo3d `acceptedTypes`).

### 2.2 Bridge model: `autoModel` (inf)

The make at ZSSS is unknown (PLAN §4). The Oshkosh AeroTech AT2 / AT3 sell-sheet table stays as an **inf placeholder**.
For each sheet model, the docked pivot distances (door + the model's cab spacer, from the rotunda) of the stand's accepted
types are tested against the model's range: operational retraction to max(operational extension, mechanical stop − 0.3 m),
as the engine's `jointOk`. Weights: the class reference 100, common SHA types 10 (A320 family, 737, A330, 787, 777,
A350, 767, 747; PLAN §1 fleet estimate), others 1. The highest score wins; among equals the shortest retraction, then
the shorter extension. A bridge that reaches nothing takes the longest unit. Result:

| Model | T1 | T2 |
|---|---|---|
| AT3 47/85 | – | 3 |
| AT3 52/100 | 1 | 10 |
| AT3 58/116 | 6 | 10 |
| AT3 61/127 | – | 6 |
| AT3 65/133 | – | 9 |
| AT3 68/144 | 6 | 2 |
| AT3 72/150 | – | 3 |

At 55 bridges every accepted type is within the chosen model's extension range (`b.modelWhy`). At 238 only the types
at 238 itself are; those at its alternative position 238A are not. 111 and 235 are in range but fail the cab turn (§2.6).
No AT2 was chosen: the docked reaches are 23-40 m.

### 2.3 Rest pose: `autoRest` (inf)

The data has no rest pose. A bridge rests **fully retracted towards door 1 of the class reference**. This is a common
rest pose; no ZSSS photo shows a resting bridge close enough to confirm it. `finishPrep` keeps that pose where it is
clear of:
- the stand's accepted aircraft by **3.75 m** (MH 5001-2021 table 4.13.5 note a: at a nose-in VDGS stand the clearance
  from the nose to "the movable end of a bridge at its return point" may be reduced to 3.75 m);
- the neighbours' aircraft (0.5 m);
- every fixed bridge part;
- the building outlines.

Otherwise it turns the pose by up to 80° (the rotunda swings 87.5°) and, failing that, extends it by up to 3 m.
All 56 retracted poses were clear as placed (`restTurned` 0, `restBlocked` 0). The engine's per-occupant parking
(sfo3d close-out round 7) moves a resting bridge out of the way of a neighbour's aircraft at run time. Its clearances
(code A/B 3.0, C 4.5, D-F 7.5 m) equal MH 5001-2021 table 4.13.5; the comment now cites that table.

### 2.4 Over-long reaches (inf)

Three data bridges are longer than any sell-sheet unit (AT3 72/150: 41.4 m operational, 43.7 m mechanical):
- 236: 44.8 m;
- 266: 48.4 m;
- 240: 52.5 m.

The data flags 240 and 266 itself ("the docked cab position or the rotunda (OSM gate node) is uncertain"). Without a
change they could never dock. `reachFix` (gates.js) therefore moves the rotunda out along the fixed link until the
docked reach is 43 m (at most 15 m) and extends the fixed link to it: **236 by 2.6 m, 266 by 8.7 m, 240 by 12.4 m**.
Each bridge records this in `b.rotundaMoved` and in `rotundaSrc`, and keeps the data point as `b.rotundaData`. Every
other bridge uses the data's rotunda unchanged; the engine's own drum-clearance shift (≤ 2 m) moved none.

### 2.5 Heights (inf)

- **Departure level** (`DEPARTURE_LEVELS`, the fixed walkway at the building), no published level:
  - **T1: 4.5 m**, inf. The T1 airside concourse roof reads 9 ± 2 m (standards_refs.md §3), so 4.5 m leaves the 3 m
    walkway under it. The walkway may slope 1:12, as in sfo3d.
  - **T2: 5.0 m, near level (≤ 1:60)**, obs-low. Photo 09 (T2 airside, 2013) shows the long glazed fixed links running
    level, one storey up, over the apron service road and its vehicles to the rotundas. The clearance of about 4.5 m is
    an eye estimate.
- **Rotunda floor**: sfo3d's minimax slope over the docked door sills, kept within the walkway's band. sha3d change:
  the height targets are the **common SHA types** wherever the bridge docks any of them. With every accepted type and a
  1:12 band, the regional jets' low sills had pulled the T2 C-stand floors down to 2.5 m, below what photo 09 shows.
  Result: T1 3.5-4.5 m (median 4.5); T2 4.2-5.0 m (median 4.5). The steepest docked tunnel of any accepted type is
  1:5.9 (T2 B stands with regional jets; the limit is 1:4).
- Slope limits 1:12 / 1:4 and the tunnel cross-sections are **US boarding-equipment design values** (FAA AC 150/5220-21C,
  36 CFR 1191), carried from the donor and labelled inf placeholders in the code. They are not marking, sign or lighting
  constants; no CAAC equivalent was transcribed.

### 2.6 Docking check (class reference parked at every bridge stand, `SHA.qa.gates().refDock`)

**54 / 56 dock.** The two that do not:

| Stand | Why | Note |
|---|---|---|
| 111 (T1 north face, EL) | cab turn 114° > the sheet's 92.5° cw | data rotunda = the end of an 11.7 m inferred fixed link off the facade |
| 235 (T2 north pier tip, C) | cab turn 97° | OSM gate node as the rotunda (inf) |

Both rest retracted when an aircraft parks. The fix belongs in the stand data (rotunda position); it is not tuned here.
Every DEBUG-parked aircraft in the renders below docks (§8).

### 2.7 Appearance

- **Glazed sides** (new material choice). Tunnels and fixed links use the objects shader's curtain-wall glass (mat 1,
  1.8 m mullions) on their sides, with plain roofs and floors. Photo 09 (docs/phase1/photos_credits.md) shows glazed
  fixed links and a glazed tunnel with an advertising panel at T2 (obs, appearance only). Photo 16 shows grey metal
  panels with windows on the outer tunnel near the cab, so all-glass sides are a simplification. T1 is assumed to be the
  same (inf). sfo3d's white steel tunnel with a window strip (mat 9) is not used.
- Each bridge's floodlight (at night) and beacon (flashing while the bridge moves) are drawn as light sprites by the
  extension's `lights` hook.

## 3. VDGS

- **Where:** at the 56 bridge stands. AIP (mirror) AD 2.20 3.2.2.3 lists 54 VDGS stands; `stands.md` §4 compares them
  locally (counts only).
- **Placement:** sfo3d's `vdgsSpot`. The unit stands on the stand centreline ahead of the stop (MH 5001-2021 9.4.6-1: on
  or near the extension of the stand centreline, visible from the left seat), at the first spot that no bridge part
  reaches in any pose (rest, docking paths, docked for every accepted type) with 0.5 m clearance.
  - A facade mount is tried first where the wall is within 14 m of the stop. Beyond that, posts come first and the
    facade (up to 45 m away) is only a fallback.
  - The wall must reach 4.2 m above the unit: T1 wall top 9 m (the concourse, photo ratio), T2 25 m (data rule).
- **Result:** all 56 units are **on posts** (5.2 m to the display base, inf). The ZSSS stops lie 20-40 m from the
  outlines: T2 fixed links are about 30 m long, and the T1 stops are about 25 m from the facade.
- **Display:** amber text on black, showing the stand number while idle and the docked type designator (A-VDGS, 9.5.7-2:
  "所引导的飞机的型号和机型"). Make and layout are unknown: **inf**.
- **Housing fix:** the stand-number sign above the display was hidden inside its own housing (a sign-convention slip,
  also in the sfo3d donor: the housing's local z is the face normal). It now sits behind the face
  (`gates_t2_vdgs_234.png`).

## 4. CAAC stand-number signs (机位号码标记牌, MH 5001-2021 8.5)

| Clause | Rule | Implementation |
|---|---|---|
| 8.5.1 | a stand-number sign at every stand where possible | all 164 stands: VDGS-top sign at bridge stands, post sign elsewhere |
| 8.5.2 | at bridge stands, an additional sign on the bridge's **fixed end** (登机廊桥固定端) | a prism on a 0.6 m mast on each rotunda roof (56) |
| 8.5.3 | stand-mounted sign on the extension of the stand centreline, else offset to the **left** of the centreline (direction of entry); hung on buildings or ground-mounted | VDGS-top sign on the centreline; remote post at 6-24 m ahead of the stop on the centreline, else 4-10 m to the left; clear of buildings, apron lanes (taxiway 11.5 m, taxilane 7.5 m half-widths, inf) and the neighbours' class-reference planforms |
| 8.5.4 | **yellow background, black characters**; lit at night, preferably internally | atlas face `#f2c40c` / `#0a0a0a` (sRGB values inf: the app. I colour table is not transcribed); `gsign` faces emissive at night |
| 8.5.5 | the characters are the stand number (lat / lon optional, ≤ 1/4 height) | stand number only |
| 8.5.6 | numerals **≥ 600 mm**; margins: horizontal ≥ 1/20, vertical ≥ 1/5 of the face height (sign without lat / lon) | numerals 0.55 of the face height (vertical margins 0.225 each); horizontal margins 0.18; faces: VDGS 1.4 m (numerals 0.77 m), remote post 1.1 m (0.61 m) |
| 8.5.8 | bridge-mounted: same number as the stand served; **triangular prism** preferred; faces show only the stand number; angle between faces ≥ 60°; characters 1/2-3/4 of the face height | prism of three 1.2 m faces at 60° (numerals 0.66 m = 0.55 of the face), one face towards the arriving aircraft |

Mounting heights and the post design are **inf**. Photos 17 / 14 / 09 show yellow boards with black digits ("213",
"247"-"249", "256") on posts and above bridge heads. The pavement stand-number plates (6.2.16) belong to the markings
package; these signs do not duplicate them.

## 5. Remote stands and GSE

Remote and VIP stands use marshaller guidance (AIP (mirror) AD 2.20 3.2.2.3) and bus boarding (data
`remote[].service`, inf). They get no VDGS and no bridge.
- **Sign:** post-mounted (§4).
- **Empty stand:** an idle self-propelled stair unit (cue; inf). It is parked parallel to the stand axis at the stand
  head, or beside the stop where the head is grass or a lane: many remote rows end at the apron edge. It must be on
  pavement, off the lanes and outside every neighbour's class-reference planform. **94** placed (superseded: fix round 1 F3, 26 staged units): every non-business
  remote stand. Not at the business stands 301-312.
- **Parked aircraft** (`placeVehicles`, every hull sampled against the aircraft, the other aircraft, the bridges and the
  buildings, as sfo3d):
  - **passenger stairs** square to door 1L and the last left door (narrow bodies), or to doors 1L and 2L (wide bodies).
    The front edge is 0.15 m outside the widest skin over the door; the platform is at the fitted door sill
    (`stairDoors`);
  - **one or two apron buses** (narrow / wide body) parallel to the forward fuselage on the left. The bus is 14 × 3.0 ×
    3.1 m (inf);
  - sfo3d's set: belt loaders on the 737 / A320 cargo-door sills, baggage train, catering truck at R2, fuel truck,
    GPU, cones.
- **Unchanged from sfo3d:** the same GSE set appears at bridge stands. The GSE livery is generic; Chinese GSE liveries
  are an open fidelity item.
- **Stair geometry:** platform 1.8 × 1.7 m with 1.0 m rails, a 38° flight with 0.2 m risers over a 2.2 m chassis, and a
  driver cab under the platform when the sill is ≥ 2.35 m. All inf (no datasheet read).

## 6. DEBUG features

- `?park=<stand>[:<ICAO>],…` (also `contact`, `remote`, `all`), or `SHA.qa.park(stand, icao, animate)`. This parks a
  **static** aircraft at the stand (nose tip on the stop point, heading = stand heading; since fix round 1 F1 the nose-gear contact on the stop point). Default types by class: B
  E190, C A320 / B738 alternating by stand number, CL B752, D B763, E A333, EL B77W, F B748. The aircraft uses sfo3d's
  `.sfom` by URL with a neutral livery. The stand's bridge then docks (instantly, or animated at the sheet's rates with
  `animate`) and the GSE is placed. **Clearly debug:** while anything is parked, the scene note reads
  "DEBUG ?park=: n static aircraft (not traffic)", and the aircraft carry `debugPark`. There is no traffic engine
  before Phase 3, and nothing is parked without the option. Related hooks: `SHA.qa.unpark(stand)`, `unparkAll()`,
  `parked()`.
- `?debug=push` (or `debug=gates`) draws an overlay, not paint:
  - lead-ins, cyan;
  - push-back paths, magenta dashes (the data's `push.pts`: own lead-in reversed to the first apron lane or junction,
    inf);
  - push ends, magenta discs;
  - stop points, cyan discs;
  - data rotundas, blue;
  - data docked cabs, green.
- `?legend=1` (the core's legend slot) adds the gates line: "Jet bridges: 13 seen on SAR (observed), 43 from OSM gate
  nodes only (inferred), drawn alike; bridge model, rest pose, levels, VDGS position and GSE inferred".
- QA: `SHA.qa.gates()` returns the summary, the per-bridge table and the class-reference docking test.
  `SHA.qa.gate(name)` gives the accepted types, VDGS / sign spot and bridge details. `SHA.qa.bridgeView(name)` is a
  camera on the stand's bridge.

## 7. Observed vs inferred

| Element | Tag | Where kept |
|---|---|---|
| stand position, number, heading | obs (OSM), stop = nose-wheel stop (MH 5001-2021 6.2.16-7, OSM tagging; fix round 1 F1) | `g.src`, `g.posSrc`, data `nose_note` |
| bridge exists | obs at 13 (SAR corridor), inf at 43 (OSM gate node) | `b.src`, `g.bridgeStatus`; drawn alike (owner rule: flag, not style) |
| attach / walkway / rotunda | inf (data); 3 rotundas moved (inf) | `b.rotundaSrc`, `b.rotundaMoved`, `b.rotundaData` |
| bridge model, rest pose, levels, cab sense | inf | `b.modelUsed` / `modelSrc` / `modelWhy`, `b.autoRest`, `b.HbTag` / `HbSrc` |
| VDGS position and display | inf | `g.vdgsSrc` |
| stand signs | standard (MH 5001-2021 8.5), placement inf | §4 |
| stairs, buses, GSE | inf | §5 |
| DEBUG aircraft | debug, not traffic | scene note, `ac.debugPark` |

## 8. Renders and comparison

`jobs/gates.mjs`: time 2026-11-14 03:00Z (11:00 local), quality high, SOFTGL (llvmpipe), 1280 × 720, deviceScaleFactor 1.
DEBUG aircraft at 229, 230, 231, 233, 234, 237, 239 (T2 north pier), 113, 115, 121, 127, 102, 110 (T1), 401, 403, 404,
406 (west remote apron), 501, 502 (east remote apron). The terminals and markings in the renders come from the other
packages' work in progress (placeholder buildings, paint) and are not reviewed here. I looked at every render.

| File | View | What it shows / comparison |
|---|---|---|
| `gates_t2_north_pier.png` | T2 north pier from the north-east | the whole pier: fixed links on columns over the service strip, rotundas, retracted bridges at the empty stands, bridges docked at 229 (A333), 230 (B77W), 231, 233, 234 (A320 / B738), 237, 239; posts with VDGS. Layout as the stands plate's T2 north + middle panel |
| `gates_compare_plate_t2.png` | plate vs render, north up, about 1 px/m | left: the Phase 1 plate (Umbra SAR, OSM stands, bridges to the L1 door); right: our top view with the push-back overlay. Stands, bridge sides (left of the aircraft), fixed-link lengths (about 30 m from the pier) and bridge-less stands (218-220, 212-217) agree. The crop is matched by eye, not georeferenced. `tools/gates/plate_compare.py` |
| `gates_t2_pier_tip.png` | pier tip 232-236, low oblique | glazed tunnels and level fixed links, the rotunda prism signs, the long bridge of 231, docked 233 / 234 with belt loaders, tug and carts, GPU, cones. Photo 09 shows the same chain at T2: level glazed fixed link, rotunda, tunnel, drive column, cab with the service stair |
| `gates_t2_bridge_233.png` | close-up at the 233 rotunda | the **CAAC prism signs** "231" "232" "233" (yellow, black numerals; 8.5.8), glazed fixed links, a VDGS post from behind, the cab docked at the B738's door 1L. Photo 09 shows "256" and photo 14 shows "247"-"249" as yellow boards on top of the T2 bridge heads: the same place |
| `gates_t2_vdgs_234.png` | from the cockpit of the A320 at 234 | VDGS display "A320" (the docked type, 9.5.7) under the stand-number sign "234" (8.5.3 / 8.5.6) on its post on the stand centreline |
| `gates_t2_north_face.png`, `gates_t2_south_face_rest.png` | the pier's two long faces | resting bridges retracted towards their stands (autoRest), VDGS posts, docked wide bodies |
| `gates_t1_west_face.png`, `gates_t1_west_close.png` | T1 west face 113-127 | bridges whose rotunda is the facade gate node (no fixed walkway), docked 113 / 115 / 121 / 127, VDGS posts "114" "115". The tower stand-in on the T1 roof is the core placeholder (terminals package) |
| `gates_t1_north_face.png` | T1 north face 101-112 | rotundas at the end of the inferred fixed links (8-24 m), docked 102 / 110 (B77W); the east apron's remote stands in front with post signs and idle stair units |
| `gates_remote_west_apron.png` | west remote apron 401-413 | DEBUG aircraft at 401, 403, 404, 406 with stairs, buses and GSE; post signs on the grass ahead of the stops |
| `gates_remote_close_404.png` | 404 (A321, front) and 403 (B738) | sign "404" facing the arriving aircraft; at 403 the stairs at doors 1L and the last left door and a bus beside the forward fuselage; at 404 the front stair, fuel truck, catering truck |
| `gates_remote_idle_405.png` | 405-406 | the idle stair unit at an empty stand head (405); at 406 (A333) two stairs (doors 1L / 2L), buses, catering |
| `gates_remote_east_apron.png` | east remote apron 501-511 | 501 (B77W) and 502 (A333) with stairs and buses; idle stair units and post signs at 504-508 |
| `gates_push_t2_north_pier_top.png`, `gates_push_t2_south_top.png`, `gates_push_t1_top.png`, `gates_push_remote_west_top.png`, `gates_push_t2_plate_frame.png` | top-down, `?debug=push` | every stand's lead-in (cyan) and push-back path (magenta dashes) to its push end; the AIP-ruled push ends of 232-235 (TWY L12), 262-265 (L13) and 286-290 (L14) are not drawn (the data's push is the own lead-in, stands.md §5) |
| `gates_night_t2_pier_tip.png` | 20:30 local | the internally lit stand signs (8.5.4), tunnels lit from inside at 0.4 of a facade's glow (inf), cab floodlights |
| `gates_phone_t2.png` | 390 × 844, iPhone UA, touch, UI shown | `?legend=1` appends the gates line to the core's legend; the DEBUG note is in the panel. The layout holds at phone size |

What the photos show and the model does not:
- the advertising panels on some tunnels (09);
- the metal-panel sections of the outer tunnel near the cab (16);
- the PCA hoses (16);
- the apron floodlight masts (09, 14);
- the red-hatched bridge areas on the apron, which belong to the markings package.

Photo 14 also shows a small dark plate with the aircraft's registration digits just below the 777's nose. It may be a
VDGS display mounted low, or a bridge-head display. VDGS mounting at ZSSS stays unverified (§10).

## 9. Checks

- **No module-scope SFO data:** the gate files import no `data/*` module. Stands arrive as `ctx.stands`
  (`window.SHA_STANDS`), outlines as `ctx.airport`, lanes as `ctx.taxigraph`.
- **No FAA marking, sign or lighting constants:** `grep -i 'faa|5340|AC 150'` over the four gate files finds only the
  boarding-equipment references of §2.5 (labelled inf) and history comments.
- **Fork headers** are present in all four forked files.
- **Start-up cost:** the gate system builds in 0.7-1.0 s on this sandbox's software GL (CPU-bound path planning for 56
  bridges, measured in `summary.buildMs`).

## 10. Open issues

1. **Bridge make and kinematics are placeholders.** The Oshkosh AT2 / AT3 table and the US slope and section values
   (§2.2, §2.5) stand in for an unknown ZSSS make, possibly a Chinese manufacturer (unverified). Every bridge is labelled
   inf, but the dimensions are not ZSSS-sourced.
2. **111 and 235 cannot dock** (cab turn 114° / 97° > 92.5°). The rotunda positions are inferred: an inferred fixed link
   at T1, an OSM gate node at T2. Fixing them in the stand builder (`tools/airport/build_stands.py`) would beat a
   renderer-side override.
3. **Three rotundas moved** 2.6 / 8.7 / 12.4 m out along the fixed link (236 / 266 / 240) so that the bridges can dock
   (§2.4). This should be confirmed or replaced in the stand data, which already flags 240 / 266.
4. **Departure levels** are a guess at T1 (4.5 m) and an eye estimate from one photo at T2 (5.0 m, level links). The
   rotunda floors are fitted to the common types (§2.5). A published section, or a photo-measured level with a solved
   camera as sfo3d did, would replace them.
5. **VDGS:** make, display and mounting are unknown. All 56 units are on posts; whether ZSSS mounts them on posts or on
   the facade or bridge head is unverified. 56 VDGS stands here vs 54 in the AIP (mirror): the stand builder's local
   comparison shows 4 of our contact stands are not AIP VDGS stands. They keep their units until the data marks them.
6. **Push-back:** the overlay shows the data's push (own lead-in reversed). The AIP's holding-point pushes (232-235 →
   L12, 262-265 → L13, 286-290 → L14, 4xx → L11) are not transcribed (OD3) and not drawn.
7. **GSE fleet:**
   - generic liveries;
   - the stair and bus sizes are not sourced;
   - the two-stair practice, and an idle stair at every non-business remote stand (94), are cues, not observations;
   - stairs and buses appear only with a parked aircraft (the DEBUG option until Phase 3 parks traffic).
8. **Glazed material at T1** is assumed (T2 from photo 09). The T2 fixed links, which standards_refs.md §2.3 describes
   as two-level, are drawn as one walkway.
9. *(Closed by fix round 1 F1: the stop point is the nose-wheel stop.)* **Stop point = nose tip** of every type (data `nose_note`); per-type stop offsets (sfo3d `type_stops`) do not exist
   for ZSSS. A VDGS stop usually refers to the nose wheel or the pilot, so the DEBUG aircraft and the docked bridges may
   sit a few metres off the real pose.
10. **Start-up:** the 56-bridge preparation takes 0.7-1.0 s here (CPU-bound path planning, measured in software GL).
    Phone cost is unmeasured on a real device. sfo3d's 120 bridges took longer and ran on phones.
11. **Phase 3 hook-up:**
    - the traffic engine should call `scene.gateSys.setOccupant(g, typeKey, animate, now, {nose, dir}, icao)` as
      sfo3d's `applyGate`;
    - for 238A / 259A it should call it on the base stand (`g.sharesBridgesOf`);
    - it should set `gateSys.aircraftFootprints`, which the DEBUG park sets now;
    - it can use `extension`, `pushClearEta`, `undockEarly`, `expectArrival` and `makePlan` as in sfo3d.

## Fix round 1 (2026-11-21)

Findings of `docs/phase2/review_visual.md` assigned to the gates package: M5, M2, L4, L6, L7, L8 and the airfield-lighting
note. The UI items (L7, L8, lighting line) are also listed in `relay_ui.md` (fix round 1), which owns the shell files.
Files changed: `js/live/gate_system.js`, `js/live/gates.js`, `tools/airport/build_stands.py`, `data/sha_stands.js/.json`
(regenerated), `js/live/shell.js`, `js/live/ui.js`, `js/live/about.js`, `live.css`, `jobs/gates.mjs`, `jobs/ui.mjs`, this
report and `relay_ui.md`. `js/live/gate_signs.js` and `js/world/gates.js` are unchanged. Check renders are in
`out/fix1/gates/` (gitignored): `before/` was rendered with the Phase 2 code before any edit, `after/` and `ui/` with the
fixed code; the six composites `docs/phase2/fix1_gates_*.png` are made from deviceScaleFactor 1 renders (1280 × 720,
1440 × 900, iPhone 15 393 × 659). I looked at every render listed below.

### F1 (M5): one stop convention - the stand stop node is the nose-wheel stop

**Decision.** The stand's `nose` (the OSM `aeroway=parking_position` node, where the markings package paints the stop line)
is the **nose-wheel stop** of every type. Sources:
- CAAC MH 5001-2021 **6.2.16-7** (read in the local copy, `markings.md` §5): "如果对飞机有人工或设备引导，停止线应设在对正于
  拟定停止点上的鼻轮位置并与对准线成直角" - with manual or equipment guidance the stop line is set at the **nose-wheel**
  position of the intended stop point, square to the alignment line (only without guidance at the left-seat pilot). Every
  ZSSS stand has guidance: VDGS at the contact stands, marshallers at the remote and VIP stands (AIP (mirror) AD 2.20
  3.2.2.3, `sha_stands.json` `aip_facts.marshaller`).
- OSM tagging of `aeroway=parking_position` (wiki page, read 2026-11-21): "Put a node where the nose wheel stops"; for the
  way, "the last node of the way should be where the nose wheel is parked". The 164 ZSSS stop nodes carry only `ref`; they
  are the last nodes of the lead-in ways (`stand_geom.py`).

**Phase 3 contract (traffic parks the same way).** A type `T` parks with its nose-gear contact on the node and heading
`hdgVec(hdg)`, so its nose tip lies `noseGearX(T)` metres ahead of the node. `js/live/gate_system.js` exports
`noseGearX(T, modelKey)` and `standTip(stand, T, modelKey)` (the nose tip `[x, y, z]`); the traffic engine passes
`{nose: [tip[0], tip[2]], dir}` to `gateSys.setOccupant(...)` and places the model with `ac.pos = tip - dir × T.xMain`, as
`gates.js park()` does. `noseGearX` is the drawn model's own nose-gear contact where the model stands on its own gear
(sfo3d model metadata `MODEL_FEATURES[m].contact.nose` through the fitted station map `T.fit.rx`: B738 4.32 m, B77W 6.25 m)
and otherwise the published station `T.xNose` (`js/aircraft/types.js`, where the procedural gear is drawn: A320 / A321
5.07, A333 6.67, B763 4.55, B748 7.74, E190 4.13, CRJ900 2.24 m). The painted stop line stays at the node.

**What follows the convention.**
- Engine (`gate_system.js`): every place that took the node as a nose tip now uses the type's tip - the class reference's
  door for the auto rest pose, `autoModel`, `standAircraft`, `dockTargets`, `staticPlans`, `upperDockExt`, `makePlan` /
  `pose` / `dockFrom` without a pose, `parkOcc`, `neighbourPrints`. A new `frontOf(g)` (the farthest-forward nose tip of the
  stand's accepted types and class reference) is the base of the VDGS spot, the VDGS geometry and the remote stand-number
  post (8.5.3: ahead of the stop on the centreline). The engine's own per-family `type_stops` hook stays empty.
- DEBUG park (`gates.js`): the model is placed by its nose-gear contact; the docked bridge cab follows (it docks door 1 of the
  model as placed). `SHA.qa.park()` returns `noseGear`.
- Data (`build_stands.py`, re-run): `bridges[].cab` (and `reach_m`, `cab_pose`) are now door 1 of the class reference parked
  with its nose wheel on the node (`NOSE_GEAR_M`, also written as `class_ref.<cls>.nose_gear_m` / `nose_gear_src`), and
  `nose_note` / `note` state the convention. The Phase 1 bridge rules (which second bridges are kept, the T1 fixed-link
  length) still use the Phase 1 cab, so the bridge set, rotundas and walkways do not move: re-tuning them is an open item.

**Data diff** (`out/fix1/gates/stands_diff.txt`, every field of the old and new `sha_stands.json` compared; the build is
deterministic, a second run gives the same bytes):

| Field | Changed | Note |
|---|---|---|
| `stands[].bridges[].cab` | 111 of 112 coordinates | moved 2.2-7.7 m forward along the stand axis (class reference nose-gear station) |
| `stands[].bridges[].reach_m` | 56 of 56 | median 4.2 m shorter (0.4-5.7 m) |
| `stands[].bridges[].cab_pose` | 56 | text: "... its nose wheel on the stop node" |
| `stands[].bridges[].reach_flag` | 1 removed | 266: 48.4 -> 43.9 m, below the 45 m flag; 240 keeps it (52.5 -> 47.7 m) |
| `stands[].area`, `remote[].area` | 93 + 48 | L6 (below) |
| `nose_note`, `note` | 1 + 1 | the convention |
| `class_ref.<cls>.nose_gear_m`, `.nose_gear_src` | 7 + 7 added | new fields |
| everything else (positions, headings, classes, span limits, excl / alt groups, bridges' attach / rotunda / walk / src / evidence, remote, push, counts, checks) | 0 | unchanged |

**Docking check** (class reference at every bridge stand, `SHA.qa.gates().refDock`): **54 / 56 dock, as before**. The two
that do not are the same (111: cab turn 119° (was 114°), 235: 99° (was 97°), both > the sheet's 92.5°). The rotunda
moves of §2.4 shrink: 236 no longer needs one (reach 39.9 m), 266 moves 1.45 m (was 8.65), 240 5.95 m (was 12.35). The
`autoModel` choice shifts with the shorter reaches (AT3 47/85 3 -> 8, 52/100 11 -> 16, 58/116 16 -> 11, 61/127 6 -> 13,
65/133 9 -> 3, 68/144 8 -> 1, 72/150 3 -> 4); 2 rest poses are now turned clear (was 0); the VDGS units are 52 posts and
4 facade units (was 56 posts), because the front moved 2-8 m nearer the facade. All 11 DEBUG-parked bridge stands of the
check run dock (229, 230, 231, 233, 234, 237, 239, 113, 115, 102, 110).

Evidence: `fix1_gates_stop_233.png` - top view at 233 (B738), before: the stop line under the nose tip; after: the nose tip
4.3 m ahead of it; and a low view where the nose-gear wheels stand on the yellow stop line. The docked cab and the red
bridge-area band (drawn by the markings package from the data cab) moved with it. Renders:
`out/fix1/gates/before/b_nose233_top.png`, `after/g_fix1_nose233_top.png`, `after/n_nw233_q1.png`.
**Status: fixed.** Open: the painted stand envelopes, safety lines, hatching and equipment areas (markings package) still
put the class planform's nose at the node; at 233 the red nose-clearance line now crosses the B738's nose (handoff).

### F2 (M2): apron floodlight masts

`LiveGateSystem.placeMasts()` (inf, comments in the code) places **73 masts**, 30 m high, each with a six-lamp head aimed
25° down towards the apron, a service platform and a concrete base (galvanised grey; make unknown). Photos 02, 09, 14, 16
and 17 show such masts; photo 09 (T2 north pier) shows them on the apron edge of the service road, about on the rotunda
line, between stands. Candidates per stand: at a contact stand beside its rotunda along the facade (±8-30 m, on the
rotunda line or up to 6 m apron-side); at a remote stand ahead of its front or between the noses of neighbouring stands.
A candidate is accepted (stands in area / number order) when it is clear of:
- the terminal outlines (4 m) and the runway strips (150 m from a runway centreline);
- every stand's class-reference planform (nose wheel on the node) grown by the table 4.13.5 clearance, and the painted
  envelopes of the markings package (+1 m);
- the swept path of every lead-in (class reference along it, same clearance; for code C equal to MH 5001-2021 table 4.9.5
  col. (13) within 0.1 m);
- taxiway / taxilane centrelines by table 4.9.5 col. (11) / (13) for the largest code letter of the stands within 150 m
  (C 26.0 / 22.5, D 37.0 / 33.5, E 43.5 / 40.0, F 51.0 / 47.5 m);
- the bridges' fixed walkways and drums (3 m) and every tunnel axis in the rest pose and along every docking path (6 m);
- the VDGS and stand-sign posts (3 m);
- the masts already placed: max(80 m, 1.8 × the stand's spacing to its nearest neighbour), so about one per two stands.

A mast must also stand on the apron, or at a remote row on the grass verge within 12 m of it. The service roads themselves
are not in the data: the rotunda-line rule keeps the masts out of the band between facade and rotundas, where photo 09
shows the road. Result by area:

| Area | Stands | Masts |
|---|---|---|
| T2 apron 2 | 70 | 32 |
| T1 north / west face | 6 + 7 | 3 + 2 |
| east apron (north of T1) | 30 | 11 |
| business apron (north-east) | 12 | 5 |
| east remote apron | 16 | 9 |
| west remote apron (apron 4) | 13 | 7 |
| south-west apron (apron 6) | 10 | 4 |

Five stands have no mast within 120 m: 333-337, whose heads face an apron lane, so every candidate is inside the
table 4.9.5 distance. The placement takes 0.2-0.4 s at start-up. At night the `lights` hook draws each head's six aimed
lamp sprites (warm white, directional) and a faint all-round head glow (night factor > 0.5, the same photocell as the
cab floodlights, inf). QA: `SHA.qa.masts()` gives `{stats, masts [{p, face, h, stand, area, at, src: 'inf'}], uncovered}`.
The gates legend line names them as inferred.

Evidence: `fix1_gates_masts_day.png` - T2 pier before (no masts) / after, and a zoom of the north pier: poles on the
rotunda line between the bridges, as in photo 09. `fix1_gates_masts_night.png` - the Phase 2 night render
(`view_night_t2pier.png`, no masts) next to the same view after the fix (21:30 local): lamp heads glowing along both piers;
every head is lit from any side. Renders: `before/b_t2pier.png`, `after/a_t2pier.png`, `after/g_fix1_masts_t2_north.png`,
`after/g_fix1_masts_t1.png`, `after/an2_night_t2pier.png`, `after/g_fix1_night_masts_t2.png`. **Status: fixed** (positions
inf). The ground's night apron flood (markings package, uniform) could fall off with the distance from these masts
(handoff).

### F3 (L4): idle airstairs staged, not at every stand head

`stageIdleStairs()` replaces the per-stand idle unit. The 94 non-business remote stands are grouped by area in stand-number
order, four per group, and each group gets **at most one** unit. It is parked in a painted equipment area of the group
(MH 5001-2021 6.2.20 设备区, from `SHA.markings.apron().equipment`), along the area's long side; if none fits, at the apron
edge ahead of the group's stand fronts. Either way it stands on pavement, off the lanes and buildings and outside every
class-reference planform. **26 placed, all 26 in equipment areas** (was 94, one at every stand head). A unit is not drawn
while an aircraft is parked at a stand within 60 m: `placeVehicles` then draws the stairs at that aircraft's doors. The
legend line now says: "Idle airstairs: 26, at most one per 4 remote stands, staged in the equipment areas: cues inf, not
seen". QA: `SHA.qa.idleStairs()`.

Evidence: `fix1_gates_idle_stairs.png` - west remote apron 401-413 before (a unit at every empty stand head) and after (two
units in this frame; the masts stand at the apron edge). Renders: `before/b_remote_west.png`, `after/a_remote_west.png`,
`after/g_fix1_idle_west.png`. **Status: fixed.**

### F4 (L6): area names

`build_stands.py` `area_of`: "T2 aprons Nr. 2" -> **"T2 apron 2"** (93 stands, 48 remote entries); "west remote apron
(Apron Nr. 4)" -> "west remote apron (apron 4)"; "south-west apron (Apron Nr. 6)" -> "south-west apron (apron 6)". The card
title now reads "T2 APRON 2" (`fix1_gates_ui_laptop.png`, `fix1_gates_ui_phone.png`). `gates.js` still finds the
terminal from the "T1" / "T2" prefix. **Status: fixed.**

### F5 (L7, L8, airfield lighting): UI shell

Details in `relay_ui.md` (fix round 1):
- **L7:** the credit line sits on a dark strip (contrast measured in `jobs/ui.mjs` against the worst case, the strip over
  white: text 9.4:1, links 10.8:1 / 6.7:1). The laptop card keeps its bottom edge above the strip (`--attrib-h`). Phone
  and laptop both report "not covered".
- **L8:** the clock and the snapshot pill say "UTC+8" (Beijing time); About says "Times are Beijing time (UTC+8)".
- **Lighting:** a legend line "Airfield lighting: not modelled yet (Phase 5): no runway or taxiway lights, stop bars or
  approach lights at night..." and the same statement in About ("Not included").

**Status: fixed.**

### Checks

- `SOFTGL=1 SCENES=snapshot node livetest.mjs jobs/integration.mjs`: 0 errors, 0 warnings, 0 page errors ("clean"); also
  `SCENES=park`: clean (run after the code changes; the night sprite tweak was re-checked with the snapshot scene).
- No-browser tests: `test_geo_js.mjs` all passed, `test_frame.py` OK, `test_buildings3d.mjs` all passed, `test_relay.py`
  7 OK. `node --check` passes for every changed module.
- `jobs/gates.mjs` has two new sets, `SET='fix1;fix1night'`: the 233 top and nose-gear views, masts by day and night, and
  the staged stairs. They are not in the default list. The job also prints the mast and idle-stair statistics.
- No FAA constant was added. The new clearances are MH 5001-2021 table 4.9.5 and table 4.13.5. Everything else new is
  labelled `inf`: mast height, head, spacing and placement rules; the idle-stair rule; the lamp colour.

Commands:

```
SOFTGL=1 OUT=out/fix1/gates/after PREFIX=a VIEWS='park:233+234+404;look:-760.58,2.5,-138.65,77,80,40@nose233_top;t2pier;stand:404,-,75,1,22;look:-880,2.5,-1430,70,22,260,50@remote_west' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/gates/after PREFIX=g SET='fix1;fix1night' PARK='229,230,231:A320,233,234,237,239,113,115,102,110,401,403,404:A321,406' node livetest.mjs jobs/gates.mjs
SOFTGL=1 OUT=out/fix1/gates/after PREFIX=n VIEWS='park:233;look:-760.58,1.2,-138.65,300,4,20,40@nw233_q1' node livetest.mjs jobs/views.mjs
SOFTGL=1 OUT=out/fix1/gates/after PREFIX=an2 T=2026-11-20T13:30:00Z VIEWS='park:229+230+231+233+234;t2pier@night_t2pier' node livetest.mjs jobs/views.mjs
SOFTGL=1 W=1440 H=900 SCENES=snapshot OUT=out/fix1/gates/ui PREFIX=ui_laptop node livetest.mjs jobs/ui.mjs
SOFTGL=1 DEVICE='iPhone 15' SCENES=snapshot OUT=out/fix1/gates/ui PREFIX=ui_phone node livetest.mjs jobs/ui.mjs
python3 -I tools/airport/build_stands.py
```

### Open after this round

1. **Markings follow-up (handoff):** the stand envelopes, safety lines, hatched overlaps and equipment areas still put the
   class planform's nose at the node. They should move forward by `class_ref.<cls>.nose_gear_m`.
2. **Phase 1 bridge rules** (SPARE_REACH second-bridge selection, the BRIDGE_REACH T1 fixed-link length) were kept on the
   Phase 1 cab so that no bridge moved. Re-tuned on the new cab, the T1 fixed links would be ~4-5 m shorter and the 250
   spare-gate bridge (45.15 m) might qualify.
3. The table 4.9.5 distances are a local copy in `gate_system.js` with the clause cited. They belong in
   `js/live/caac_markings.js`, the one parameter table (handoff).
4. Masts: 333-337 have none (lane distance). Heights, heads and positions are not surveyed. Masts are opaque geometry but
   cast no light onto aircraft and GSE: the ground flood is the markings package's uniform term.

### Integration notes (fix round 1, 2026-11-21)

- Open items 1 and 3 are done. `caac_decals.js` shifts the painted envelopes, safety lines, hatching and equipment areas
  forward by `class_ref.<cls>.nose_gear_m`. `caac_markings.js` carries table 4.9.5 (`separation.twyCLToObject` /
  `taxilaneCLToObject`, read off the local copy: col. (11) C 26.0 / D 37.0 / E 43.5 / F 51.0 m, col. (13) C 22.5 /
  D 33.5 / E 40.0 / F 47.5 m; 9.2.7 applies them to apron floodlight supports), and `placeMasts` reads them from there
  (same values, so the masts did not move: still 73, the same rejection counts).
- **Side effect on the staged idle stairs (L4): 20 of 26 groups now get a unit** (was 26; all 20 in equipment areas).
  The 6 groups without one are the whole west remote apron (401-413, 4 groups) and T2 apron 2 remote 286-290 (2 groups).
  At those stands the paved surface ends 0-1.5 m ahead of the stop node (`pavedAt` along the heading), so the shifted
  equipment areas reach onto the unpaved band and no fallback spot fits. Under the nose-wheel convention the class C
  noses there also reach ~4-5 m past the pavement edge, and the red envelope fronts and the 设备区 boxes are painted on
  the band (`view_stand_404.png`). The Sentinel-2 hint reads the band ahead of 403 / 404 / 287 as neutral grey
  (134-171 in the 8-bit hint, against 170-206 on the apron and ~(93, 98, 89) on the grass further out): probably
  another OSM apron gap like H2, not grass. Proposed for round 2: extend the H2 airside fill (or an inferred
  `apron_fill` in `build_airport.py`) over these strips where S2 reads paved.

## Fix round 2 (2026-11-21)

Answers `docs/phase2/review_visual_fix1.md`, finding **N1** (medium, new): the apron floodlight masts of fix round 1 stood
in the app's own stand cameras. Files changed: `js/live/gate_system.js` (the stand camera, mast placement),
`js/live/gates.js` (mast lamp sprites, `SHA.qa.camSubject`), `js/live/shell.js` ("Fly to stand", `SHA.qa.standCam`; also in
`relay_ui.md` fix round 2), `jobs/gates.mjs` (sets `fix2` / `fix2night`, the stand-camera check). Renders are in
`out/fix1/gates2/` (gitignored), 1280 × 720 at deviceScaleFactor 1, and I looked at all of them. `before/` is the fix-round-1
code (the reviewer's own `out/review1/` renders where named); `after/` is this round's code, with the buildings and
markings fixers' concurrent edits in it.

### N1: masts in the stand cameras

**Before** (fix-round-1 code, measured in the page: `out/fix1/gates2/before/b_mastcam.json`): 73 masts. On the "Fly to
stand" camera (side +1), a pole came within 3 m of the centre sight line (camera to target, 3-D) at 7 of the 56 bridge
stands (109, 113, 115, 121, 248, 264, 274: the review's six plus 113, where the pole stands just below the camera), and
within 5 m at 13. Over all 164 stands it was 24 and 40: the review counted only contact stands, but the remote candidates
"ahead of the stand front, between the stands" lie on the camera's ahead-left line, so 52 of 106 remote stands also had a
mast inside the review's ±12 m strip. At 233 the mast split the named day, phone and laptop views; at night the head glow
sprite (s = 1.6 m) drew a ~220 px disk (`view_night_stand_233.png`).

**What changed**

1. **One stand camera** (`gate_system.js` `STAND_CAM`, `standCamWedge`; a UI choice, inf): target 18 m behind the stop
   node, horizontal direction 0.75 × heading + 0.66 × left × side, 24° down, 90 m (120 m for E / EL / F), fov 50°. These
   are the numbers `shell.js flyToStand` and `SHA.qa.stand` already used; `flyToStand` now reads them from here.
2. **An image test, not a ground strip** (`standCamPos`). A mast pole (0-31 m) stands in a stand camera when, projected
   into that camera and not wholly behind the subject, it passes within **4°** of the subject's image (about 55 px at
   1280 × 720). It also counts when, standing in front of the target, it crosses the centre band of the frame (**±8°**).
   The subject is the convex hull of the projected target (3 m), the stop node (1 m) and `camSubject(g)`: the class
   reference parked with its nose wheel on the node (nose tip 3 m, wing tips 4 m, tail 9 m), every bridge rotunda as
   placed (5 m) and every docked cab (4 m). All values are inf. I first built the review's ±12 m ground strip about the
   sight line, then a fan of such strips to the nose tip, node and rotunda. With the strip, the 248 mast moved 14 m off the
   line, and in that run's render it stood right beside the B77W's nose: the pole passed about 13 px left of the nose tip.
   A later run overwrote that render; this sentence is the record of what I saw. A tall pole near the camera sweeps
   across the subject even when its foot is clear on the ground, so the test has to be done in the image. I also tried
   the VDGS display as a subject point. The result was 61 masts and 20 stands without a mast within 120 m, the whole T2
   north pier tip among them, so the VDGS is not a subject point; in the renders it stays visible beside the masts.
3. **Placement** (`placeMasts`). A candidate is rejected ("stand camera") when it stands in side +1 of any contact stand,
   or when it would leave a remote stand with both sides blocked. With `MAST_CAM_STRICT_REMOTE = true`, side +1 of the
   remote stands is also kept clear; I tested that: 68 masts, but only 2 left on the business apron, so the default is
   false. `SHA.qa.masts().stats.cameras` gives the contact stands with side +1 blocked, the remote side +1 / -1 counts
   and the stands with both sides blocked.
4. **"Fly to stand"** (`shell.js`). It takes side +1 unless a mast stands in it and side -1 is clearer.
   `SHA.qa.standCam(name)` returns the side and both clearances. The camera uses the stand's exact heading (the card
   record is rounded to 1°) and the subject points of the placement (`SHA.qa.camSubject`).
5. **Lamp sprites** (`gates.js` `mastSprite`, an inf display rule). The projected radius of every mast sprite is capped at
   **24 px**. The sprite shader draws the quad at 1.6 × s, pulled min(2 m, 0.05 d) towards the camera; the cap uses the
   same numbers. The sprite also fades out (smoothstep) between 40 m and 10 m from the camera.

**Result** (`jobs/gates.mjs SET=fix2`, `out/fix1/gates2/after/render2.log`):
- **67 masts** (73 before): T2 apron 2 28 (32), T1 north / west face 2 + 2 (3 + 2), east apron 10 (11), business 5,
  east remote 9, west remote 7, south-west 4. "stand camera" rejected 379 candidates.
- **Contact stands with a mast in side +1: none.** No remote stand has both sides blocked; "Fly to stand" takes side -1
  at 48 remote stands and at 0 contact stands.
- On the side taken, no stand of the 164 has a pole within 3 m or 5 m of the centre sight line (before: 24 / 40), and
  none has a mast inside the subject or centre margins.
- The other stands of the review: 109, 115, 121, 248, 264 and 274 all fly to side +1, with clearances 1.0-14.7 × the
  margin.
- **Stands with no mast within 120 m: 8** (5 before). 333-337 as before (their heads face an apron lane), plus 126
  (T1 west face) and 231 / 232 (T2 north pier tip). Of their own candidates, the stand-camera test rejected 28 (126),
  40 (231) and 27 (232). The rest failed on buildings, bridge sweeps, posts, envelopes, lanes or spacing
  (`SHA.qa.masts().uncovered`, printed by the job).
- The placement takes 0.4-0.5 s (was 0.2-0.3 s).
- The markings package's apron light pools read the mast list at run time and follow it (n = 67 in the log).

**Renders** (looked at):
- **248, "Fly to stand" (B77W parked).** Before: the pole stood at the rotunda in mid-frame. After: the nearest mast
  stands beside the VDGS post, at the edge of the service road, about 70 px left of the nose. The nose, bridge and cab
  are clear; the VDGS unit is visible just left of the pole (`g_fix2_fly_248.png`).
- **274.** Before: a mast in front of the 274 rotunda. After: the nearest mast is at the 273 rotunda at the left edge.
- **115.** The review's mast in front of the stand is gone. The nearest pole stands left of the B738's nose, beside the
  113 equipment area.
- **233.** "Fly to stand", the named view `stand:233,-,70,1,24` and the night view of the same camera show no mast at
  all: B738 docked, bridge, VDGS and sign clear.
- **The other named stand views** (`jobs/views.mjs` `stand:113,-,75,1,22`, `stand:102,-,110,1,20`, `stand:404,-,75,1,22`,
  aircraft parked; `out/fix1/gates2/after/v_stand_*.png`). At 113 a mast now stands at the left frame edge (there was
  none before). At 102 the mast at the 103 rotunda is still at the left, and a second pole enters at the bottom right
  edge. At 404 a mast stands between the 403 and 404 heads at the left. All of them are clear of the aircraft, bridge and
  stairs. These cameras differ a little from "Fly to stand" (nearer, flatter), which the placement checks.
- **Night (21:30 local).** The named night view of 233 shows no mast and no lamp disk now; before, it showed the ~220 px
  disk. "Fly to stand" 233 at night is clean as well; far masts show as small dots on the horizon. For the cap itself,
  the job puts a lamp head 22 m in front of the camera (the 236 mast at the T2 pier tip). The six aimed lamps draw as
  six disks of about 45-50 px, and nothing larger. The job's measurement agrees: the largest uncapped radius would have
  been 96 px, the drawn one is 24 px (`mast sprites fix2_night_mast_near {"maxRadiusPxUncapped":96.1,
  "maxRadiusPxDrawn":24}`). At 60 m it is 34 px uncapped and 24 px drawn: a compact six-lamp cluster
  (`g_fix2_night_mast_near.png`, `g_fix2_night_mast_mid.png`). The aircraft are lit in these renders through the
  buildings fixer's concurrent N3 change, not through this one.

Evidence: `fix2_gates_fly_248_274.png` (before / after, 248 and 274), `fix2_gates_stand_233_115.png` (the named 233 view
before / after, "Fly to stand" 233 and 115), `fix2_gates_night_233.png` (the named night view before / after, "Fly to
stand" 233 at night, and a lamp head 22 m from the camera). The masts do not depend on the parked aircraft (the
placement uses the class reference planforms), so the before renders without aircraft and the after renders with
them show the same masts.

| Id | What changed | Evidence | Status |
|---|---|---|---|
| N1 | Stand camera defined once (`STAND_CAM`). Masts are rejected by an image-space test (pole vs the hull of the class reference, rotundas and cabs, ±4°; centre band ±8°): side +1 of every contact stand clear, at least one side of every remote stand clear. "Fly to stand" picks the clear side. Mast lamp sprites capped at 24 px projected radius and faded within 40 m of the camera. | `fix2_gates_fly_248_274.png`, `fix2_gates_stand_233_115.png`, `fix2_gates_night_233.png`; `out/fix1/gates2/after/g_fix2_*.png`, `v_stand_113/102/404.png`; job log: 0 stands with a mast within 5 m of the sight line on the side taken (before 40); near lamp head 96 px uncapped -> 24 px drawn | fixed |

### Checks

- `jobs/gates.mjs SET='fix2;fix2night'`: the stand-camera check above. All parked bridges docked (229, 230, 231, 233,
  234, 113, 115, 121, 248, 274).
- Console: `SOFTGL=1 SCENES=snapshot node livetest.mjs jobs/integration.mjs` -> "console 7 messages (0 error, 0 warning),
  page errors 0, HTTP>=400 0, failed requests 0 -> clean" (`out/fix1/gates2/integ_snapshot.log`). The `fix2` / `fix2night` runs
  (DEBUG park, day and 21:30) logged no error or warning either.
- No-browser tests: `test_geo_js.mjs` all passed, `test_frame.py` OK, `test_relay.py` 7 OK, `test_metar_zsss_js.mjs`
  all passed, `test_buildings3d.mjs` all passed. `node --check` passes for the four changed modules / jobs.
- No FAA constant and no SFO value. Every new value is a UI or display choice and is labelled inf: the stand camera, the
  margins, the subject heights and the sprite cap / fade.

### Open after this round

1. **Fewer masts.** 6 masts fewer, and 126, 231 and 232 now have no mast within 120 m. Photos show masts on the T2 pier tip. If the owner prefers
   coverage to clean stand views, `STAND_CAM.subjDeg` / `centreDeg` trade one against the other.
2. Remote stands fly to their right side (side -1) where a mast stands on the left. Neighbouring remote stands can
   therefore open from different sides.
3. N5 (low, not in this round's list): the mast list still depends on the quality tier through the post list. The new
   camera test adds no tier dependence.
4. Handoffs: `CLAUDE.md` (lead) still says "`masts()` (73 inferred apron floodlight masts)". It should read 67 and name
   `SHA.qa.standCam()` / `SHA.qa.camSubject()` and `STAND_CAM` (the stand camera, `gate_system.js`).
   `app.js SHA.qa.stand` (core) could take its defaults from `STAND_CAM` / `standCamWedge`; it has the same numbers now.

## Fix round 3 (2026-11-27)

Answers `docs/phase2/review_visual_fix2.md` findings **V2** (medium, the residual of N1: masts in the near field of the
"Fly to stand" cameras), **V4** (low: masts in painted equipment areas, base plates over the pavement edge) and **N5** (low:
the mast list depends on the quality tier). Files changed: `js/live/gate_system.js` (the near-field test, the placement
rules, the gap fill, the statistics), `js/live/gates.js` (a tier-independent pavement test, the equipment areas passed to
the placement, the legend line, `SHA.qa.pavedVec`), `js/live/shell.js` ("Fly to stand" side choice and `SHA.qa.standCam`;
also in `relay_ui.md` fix round 3), `jobs/gates.mjs` (sets `fix3` / `fix3night` / `fix3low`, `CHECK_ONLY=1`, the checks).
Renders are in `out/fix3/gates/` (gitignored): `before/` is the fix-round-2 code, `final/` this round's code; `a1`-`a3` and
`after/` are intermediate runs. 1280 × 720, deviceScaleFactor 1, SOFTGL, high tier unless noted; I looked at all of them.
The renders park DEBUG aircraft (`?park=`) at 228, 238A, 259, 264 and 270 (the review's renders had none there).

### Before (the fix-round-2 code; `out/fix3/gates/before/check.log`, the same job)

- **67 masts** at the high tier, **66** at the low tier; **8 stands** with no mast within 120 m (333-337, 126, 231, 232).
- **Near field**, every stand on the side "Fly to stand" takes: 25 contact and 9 remote stands had a mast head (a corner of
  the 4.2 × 2.7 m head box) or its pole above 10 m in the 16:9 frame at a depth under 45 m, or a pole within 25 m of the
  camera (my sampled test). The review probe's own test (head / mid / foot sample in the frame, a 3 m head >= 60 px):
  14 contact + 7 remote = the review's 21 stands. Nearest head corner: 238A 8.0 m (the review: head centre 10.3 m),
  264 12.7 m, 270 12.6 m, 228 18.2 m, 259 20.9 m.
- **Equipment areas**: the feet of the 323 and 325 masts inside an equipment ring (328's and 325's); the 228 mast 1.44 m
  from 229's.
- **Base plates**: at 29 masts (high) / 30 (low) a plate corner + 1 m read `pavedAt` < 0.5; 525's centre read 0.
- **Tiers**: 13 mast positions differ between high and low (306, 312, 525, 218-225, 275, 284, 403, 407, 412). The cause is
  not the post list (fix round 2 guessed that) but `pavedAt`: the ground's CPU copy samples the airfield map at the tier's
  resolution (1.0 m high, 1.6 m low, 0.75 m ultra; 2 m cells read from their first pixel), so candidates near a pavement
  edge flipped; the rejection counts that differ (post, spacing) follow from the different masts placed before them.

### What changed

1. **Near field of a stand camera** (`gate_system.js` `standCamNear(W, q, h)`, `standCamNearList(W, masts)`; new
   `STAND_CAM` values, all inf, a UI camera choice). A mast is in the near field of camera W when its head (a sphere of
   `headR` 2.2 m about `MAST_H` - 0.8 m: the six-lamp head and platform) or its pole above `nearPoleMin` 10 m projects into
   the frame (vertical fov 50°, width `aspect` 16 / 9: the laptop frame; a portrait phone sees a narrower part of it) at a
   depth under `nearDepth` 45 m (the review's figure: a 3 m head stays under about 50 px), or when the pole comes within
   `nearDist` 25 m of the camera (3-D). The pole is clipped to the depth range and tested against the frame rectangle
   (Liang-Barsky), so a pole crossing the frame with both ends outside counts.
2. **Placement** (`placeMasts`). A stand-camera side is clear only when no mast is in its subject / centre margins (fix
   round 2) **and** none is in its near field. A contact stand keeps side +1 (the bridge side) clear (`MAST_CAM_CONTACT`
   'side1'; 'either' would let it fly from its right side and gave 61 masts / 1 uncovered in a test run with a 1 m plate
   margin); a remote stand
   keeps at least one side clear. Cameras whose stop node is within 200 m of the candidate are tested (was 160 m: the near
   field reaches about 45 m past a camera that hovers up to 130 m from its node). The alternative positions on a base
   stand's bridge (238A, 259A) have their own camera: their node and heading, the base stand's bridges as subject - the
   camera `shell.js` builds (`SHA.qa.camSubject`).
3. **Gap fill** (coverage). The near-field rule empties the rotunda line in front of most contact-stand cameras (they hover
   over the facade 45-55 m to the left of the stand, so their near field covers the rotunda line towards the left
   neighbour). A stand still without a mast within `MAST_GAP_R` 120 m after the pass gets one more try on a polar grid
   about its stop node (radii 24-108 m by 12 m, every 15°, nearest first) under every rule, the head facing the node
   (`at: 'gap fill'`; inf). 8 masts are placed so (for 309, 333, 336, 112, 228, 250, 265, 289).
4. **Equipment areas** (V4). `gates.js` passes `SHA.markings.apron().equipment` (MH 5001-2021 6.2.20 设备区, the markings
   package's rings) to `placeMasts`; a candidate is rejected when its base plate is within `MAST_EQUIP_CLEAR` 2 m of a
   ring, i.e. its foot within 2 m + the plate's half diagonal (3.13 m). The review asked 2 m from the foot; from the plate
   reads better in the top views (the 323 render with 2 m from the foot still showed a plate at a box corner).
5. **Pavement** (V4 / N5). The candidate's base plate is tested, not only its centre: the centre and the four corners of
   the 1.6 m plate grown by `MAST_PAVE_MARGIN` 2 m (the review's 1 m plus 1 m for the 2 m cells of the ground map's CPU
   copy, so that the review's own `pavedAt` probe at the corners + 1 m passes as well). The test is the new
   **tier-independent** `vectorPavement` (`gates.js`): the polygons the airfield map's pavement channel is painted from
   (`paintAirfieldMap`: runway, shoulders / blast pads, taxiway, taxiway shoulders, aprons, helipads) and the 'paved' fills
   the packages add through their `pavement(api)` hook (terminals.js: airside fill, stand-head fill), tested exactly
   (even-odd per fill call as the canvas fills them, edges bucketed in 25 m rows). The staged idle stairs use it too.
   `SHA.qa.pavedVec(x, z)` exposes it.
6. **"Fly to stand"** (`shell.js`): side +1 if it is clear (subject and near field); else side -1 if clear; else side +1
   if its subject is clear; else the side with the larger subject clearance. `SHA.qa.standCam(name)` also returns `near`:
   the masts in the near field of each side (`relay_ui.md`).
7. **Statistics** (`SHA.qa.masts().stats`): `hash` (FNV-1a of the positions to 0.01 m; equal on every tier), `paved`
   ('vector (tier-independent)'), `equipmentAreas` (261), `rules`, and `cameras` = `{contactSide1, contactNear1}` (contact
   stands with side +1 blocked / blocked by the near field: both must be empty), `contactClear` / `contact` (58 / 58),
   `remoteSide1`, `remoteSide2`, `remoteNear` [side +1, side -1] (remote sides with a near-field mast; the side "Fly to
   stand" takes is always clear), `bothSides` (empty), `near` {depth, dist, poleMin}, `contactRule`. `uncovered` lists the
   stands without a mast within 120 m and why their own candidates failed. Rejection reasons now include 'stand camera
   near field' and 'equipment area'.
8. **Legend** (`gates.js`): "Apron floodlight masts: 58, about one per 3 stands, kept out of the "Fly to stand" views; as in
   photos, but positions and form inf." The phone (low) and laptop (high) legends read the same count.
9. **Job** (`jobs/gates.mjs`): `SET='fix3;fix3night;fix3low'`, `CHECK_ONLY=1` for the checks without renders. For every
   stand it rebuilds the camera the app flies to (the side `SHA.qa.standCam` picks, `standCamWedge` with the stand's own node
   and exact heading and `SHA.qa.camSubject`) and lists the near-field masts three ways: an independent sampled test (the
   pole every 0.5 m from 10 m to the head, the eight head-box corners, the 3-D distance), the app's `standCamNear`, and the
   review probe's test. It also checks the four named stand views of `jobs/views.mjs` (233, 113, 102, 404), the equipment
   areas (foot within 2 m, and the nearest foot), the base plates + 1 m (raster `pavedAt` at this tier and the vector test),
   the coverage and the hash; `fix3low` reloads at quality=low and compares the list. It prints "fix3 requirements: met" or
   FAILED (and exits 1) when a contact-stand camera has a near-field mast, a foot is within 2 m of an equipment area, a plate
   is off pavement, or the tiers differ; it also counts console errors / warnings / page errors.

### Result (`out/fix3/gates/final/check.log`, `check2.log`, `check3.log`; `jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1`)

| | before | after |
|---|---|---|
| masts (high / low tier) | 67 / 66 | **58 / 58**, hash `edc568b` on both, identical lists |
| stands with no mast within 120 m | 8 (333-337, 126, 231, 232) | **3** (310, 121, 126) |
| "Fly to stand" cameras with a near-field mast (sampled test), contact / remote | 25 / 9 | **0 / 0** |
| same, the app's `standCamNear` (all stands); the review probe's test (3 m head >= 60 px), contact + remote | 32; 14 + 7 | **0; 0 + 0** |
| named stand views 233, 113, 102, 404 with a near-field mast | - | **0** |
| subject clearance < 1 on the side taken | 0 | 0 |
| mast feet in or within 2 m of an equipment area | 3 (323, 325 inside; 228 at 1.44 m) | **0** (nearest 3.16 m, 321) |
| base plates + 1 m with a corner off pavement (`pavedAt` high / low) | 29 / 30 | **0 / 0** (vector test: 0) |
| "Fly to stand" side -1 (contact stands) | 45 (0) | 42 (0) |
| placement time | 0.4-0.5 s | 1.1-1.3 s |

By area (before -> after): T2 apron 2 29 -> 22, T1 north face 2 -> 3, T1 west face 2 -> 1, east apron 10 -> 11, business
apron 5 -> 3, east remote 9 -> 8, west remote 6 -> 6, south-west 4 -> 4. By placement: 13 on the rotunda line, 27 ahead
of a stand front, 10 between stand noses, 8 gap fill. Rejected candidates: 'stand camera near field' 464, 'stand camera'
552, 'equipment area' 409, 'not paved' 930 (plate + 2 m), spacing 3352. The three stands still without a mast: 310
(business apron: every candidate's plate + 2 m off the pavement or in a lane clearance), 121 and 126 (T1 west face: 'stand
camera' and 'building'). The five stands of the review now fly to side +1 with subject clearances 7.3 (238A), 9.3 (264),
4.1 (270), 9.1 (228) and 24.9 (259) × the margin and no near-field mast.

**Coverage trade.** 9 masts fewer than fix round 2, but 5 fewer uncovered stands. Test runs with the rules overridden
(`placeMasts({rules})`, plate margin 1 m, equipment clearance 2 m from the foot, no gap fill): 52 masts / 18 uncovered with
the near-field rule, 61 / 10 without it; the gap fill then brought 52 / 18 to 59 / 4. The light map
of the markings package reads the mast list at run time, so its pools follow the 58 masts; the stand floor it adds this
round makes stand lighting independent of them.

### Renders (looked at)

- **"Fly to stand" 238A, 264, 270, 228, 259 by day** (`fix3_gates_fly_day.png`; `out/fix3/gates/before/b_fix3_fly_*.png`,
  `final/a_fix3_fly_*.png`). Before: at 238A the 238 mast head fills the lower right quarter, seen from just above; at 264
  the 265 mast's pole and head stand in the lower left over the pier; at 270 the 270 mast head is right of centre, about
  250 px wide; at 228 and 259 a 30 m pole stands right of the aircraft's right wing tip with the head at the top. After: no
  mast in any of the five frames' foreground. At 270 one pole stands by the 269 rotunda at the left and one far out on the
  apron, both in the middle distance (heads about 20-30 px); at 228 two far poles stand at the upper left by the pier.
  The A320 / B738, the docked bridge, the VDGS and the stand sign are unobstructed in all five.
- **238A at 21:30** (`fix3_gates_night_238A.png`). Before: the black six-lamp head in the lower right. After: no mast; the
  aircraft and bridge are lit, the far masts show as small lamp points on the horizon.
- **Equipment areas and plates** (`fix3_gates_v4_equipment_plates.png`; the review's own cameras, before = its renders
  `out/review2/day/rv2_mast323_top.png`, `rv2_mast325_top.png`, `rv2_nose608_top.png`). 323: the mast foot is no longer
  inside the box; the nearest mast (328's) stands between the noses of 323 and 328, 6-7 m from the four boxes around it.
  325: no mast within 54 m (the next one is at the left edge). 608: the mast at the lower left (607's) now has its plate about two
  plate widths inside the stand-head concrete instead of on its edge.
- **Gap-fill masts** (`fix3_gates_gapfill.png`, top views at 84°): at 112 (T1 north face) the mast stands at the stand
  head beside the lead-in, 6 m from the equipment box; at 333-337, whose heads face an apron lane, two masts stand between
  the stands. In these near-top views the head is drawn displaced from the foot by the perspective, and the long thin
  line is the pole's shadow.
- **The named view `t2pier`** (`out/fix3/gates/after/v_t2pier.png`, an intermediate run with 59 masts) still shows masts
  along the T2 north pier, fewer than in `view_t2pier.png`.

Evidence: `fix3_gates_fly_day.png`, `fix3_gates_night_238A.png`, `fix3_gates_v4_equipment_plates.png`,
`fix3_gates_gapfill.png` (composites of 1280 × 720 renders at deviceScaleFactor 1, scaled 0.5).

| Id | What changed | Evidence | Status |
|---|---|---|---|
| V2 | Near-field term `standCamNear` (head or pole above 10 m in the 16:9 frame at a depth under 45 m, or the pole within 25 m; inf) in the placement: a camera side is clear only with no near-field mast; contact side +1 clear, remote one side; 238A / 259A with their own camera. "Fly to stand" prefers the side with no near-field mast. Gap fill for stands left without a mast. `jobs/gates.mjs fix3` reports every stand camera with a near-field mast (three tests) and requires 0 for contact stands. | `fix3_gates_fly_day.png`, `fix3_gates_night_238A.png`; `out/fix3/gates/final/check.log`: contact 0 / remote 0 (before 25 / 9; review probe 21 -> 0), named stand views clear; 58 masts, 3 uncovered (before 67, 8) | fixed |
| V4 | Equipment areas passed to `placeMasts`: the base plate 2 m clear of every ring (foot >= 3.13 m). Base plate + 2 m on pavement at its centre and four corners, by the tier-independent vector test. | `fix3_gates_v4_equipment_plates.png`; feet within 2 m of a ring 3 -> 0 (nearest 3.16 m); plates + 1 m off `pavedAt` 29 / 30 -> 0 / 0 | fixed |
| N5 | Placement reads a vector pavement test built from the polygons the airfield map is painted from (+ the packages' pavement fills) instead of the tier-resolution `pavedAt`; idle stairs too. `stats.hash`; `fix3low` compares the tiers. | `check.log` / `check2.log`: high and low 58 masts, hash `edc568b`, identical lists, legend "58" on both | fixed |

### Checks

- `jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1` (high and low): requirements met on both tiers, tiers SAME, console 0
  errors / 0 warnings / 0 page errors. `SET='fix3;fix3night'` (renders, DEBUG park, day and 21:30): console clean; every
  parked bridge docked (228, 238A on 238's bridge, 259, 264, 270).
- `SOFTGL=1 SCENES=snapshot node livetest.mjs jobs/integration.mjs`: "console 7 messages (0 error, 0 warning), page
  errors 0, HTTP>=400 0, failed requests 0 -> clean" (`out/fix3/gates/integ.log`).
- No-browser tests: `test_geo_js.mjs` all passed, `test_buildings3d.mjs` all checks passed, `test_metar_zsss_js.mjs` all
  passed, `test_frame.py` OK, `test_relay.py` 7 OK. `node --check` passes for `gates.js`, `gate_system.js`, `shell.js`,
  `jobs/gates.mjs`.
- No FAA constant and no SFO value. The new values (near field, plate margin, equipment clearance, gap-fill grid,
  `MAST_GAP_R`) are UI or placement choices, all labelled inf; the equipment areas are the markings package's MH 5001-2021
  6.2.20 rings; the lane / envelope clearances (table 4.9.5, 4.13.5) are unchanged.

### For CLAUDE.md (the integrator)

- `SHA.qa`, gates: `masts()` (**58** inferred apron floodlight masts, the same list on every quality tier (`stats.hash`),
  base plate + 2 m on pavement, clear of the stand cameras incl. their near field and of the equipment areas;
  `stats.cameras`, `uncovered`), `pavedVec(x, z)` (the placement's tier-independent pavement test); shell: `standCam(name)`
  (the "Fly to stand" side, both clearances and the near-field masts per side).
- Harness: `jobs/gates.mjs` `SET='fix3;fix3night;fix3low'` (`CHECK_ONLY=1`: checks only): every stand's "Fly to stand"
  camera and the named stand views against the near field (contact stands must be 0), equipment areas, base plates,
  coverage and the tier hash; "fix3 requirements: met" or FAILED (exit 1).
- Conventions, "Stand camera": also a near field (`STAND_CAM.nearDepth` 45 m, `nearDist` 25 m, `nearPoleMin` 10 m,
  `standCamNear`; inf): a side is clear only when no mast is in its subject / centre margins or its near field; contact
  stands keep side +1 clear, remote stands one side; "Fly to stand" takes side +1 if clear, else a clear side -1. Masts:
  stands still without one within 120 m get a gap-fill try; placement is tier-independent (`gates.js vectorPavement`: the
  polygons the airfield map is painted from plus the packages' `pavement(api)` fills - a package that adds pavement through
  that hook counts automatically, and its hook is now called a second time, with `api.rect` null and `api.res` 1).

### Open after this round

1. Coverage: 310, 121 and 126 have no mast within 120 m; the T2 apron has 22 masts (29). `MAST_CAM_CONTACT = 'either'`
   (contact stands may fly from their right side) would give 61 masts and 1 uncovered stand; it is a UI choice for the
   owner.
2. The review's optional emissive lamp face (a near head not a black block at night) is not done: no mast is in a
   "Fly to stand" near field any more. A user who orbits from there can still bring a head close; the lamp sprite cap and
   near fade of fix round 2 still apply.
3. Placement takes 1.1-1.3 s on this sandbox (0.4-0.5 s before), once at start-up: the near-field test and the gap fill.
4. Handoff (buildings, `js/live/terminals.js`): its `pavement(api)` hook is now also called by `gates.js vectorPavement`
   (a recording api: `fill` / `line`, `rect` null, `res` 1). It only reads the data and sets `fillInfo` to the same values,
   so nothing needs to change; keep it free of call-count side effects.

## Fix round 4 (2026-11-27)

Answers `docs/phase2/review_visual_fix3.md` **F1** (medium: a 30 m mast is the largest foreground object of the app's Tower
view), **F3** (low: masts at 45-80 m that frame the subject of a "Fly to stand" view), **F4** (low: a mast plate on a painted
envelope line) and **F7** (low: ~1.4 s of main-thread start-up). This round owned all of gates, markings and buildings
(`markings.md` and `buildings.md` have F2 / F5 and F6); the regression checks for the whole round are at the end of this
section. Files changed: `js/live/gate_system.js` (Tower view cameras, near field 55 m, envelope clearance, finer gap fill,
dry pass, inputs hash and stored placement), `js/live/gates.js` (tower anchor, `data/sha_masts.json` prefetch, pavement
signature, `SHA.qa.mastsLive`, legend), `js/live/shell.js` (comment), `jobs/gates.mjs` (Tower view, middle distance, envelope
and cache checks; sets `fix4`, `masts`), new `data/sha_masts.json` / `.js`. "Before" is HEAD (96aafa9), run in an exported
copy of the tree (`out/fix4/beforeroot/`) with the new job, so both sides use the same checks; renders in `out/fix4/`
(gitignored), SOFTGL llvmpipe, 1280 x 720, deviceScaleFactor 1, high tier unless noted; I looked at all of them.

### What changed

1. **Tower view cameras in the placement (F1)**. `towerViewCams(anchors.tower, runways)` rebuilds the app's Tower view
   (`app.js view('tower')`, same formulas: eye 0.5 m inside the cab glass at `eyeY`, facing the 18L/36R midpoint, `cabYaw`)
   in both framings: landscape (vertical 46 deg, pitch from `terraceHalf / terraceY` = -7.0 deg, 16:9) and portrait (pitch
   -11 deg; one frame holding every phone of aspect 0.46-0.66: half width tan 20 deg, half height 36 deg). Both are kept clear
   like a contact stand's side +1: no mast in their near field (`TOWER_CAM.nearDepth` **90 m**: head or pole above 10 m in
   the frame closer than 90 m, or the pole within 25 m of the eye) and none in their subject / centre band (the view target,
   +-8 deg in front of it). The review asked for about 70 m: with 70 m the gap fill re-placed mast "115" at 79 m, still the
   largest object in the laptop frame (45 px, lower left); with 90 m it lands out of both frames and also covers 121. All inf.
   `standCamNear` / `standCamPos` take the frame (`W.tanX / tanY`) and near depth per camera for this.
2. **Near field 45 -> 55 m (F3)**. `STAND_CAM.nearDepth` 55 m for every stand camera (both sides; the shell's "Fly to stand"
   side choice uses the same function, so placement and UI agree): past 45 m the 4.2 m head was still 60-72 px at
   1280 x 720; at 55 m a head in the frame is at most ~59 px. The review's alternative (a pole nearer than 60 m keeping
   2 x subjDeg from the subject hull) was implemented and tried with it: at 55 m it rejected nothing more (same mast hash), so
   it was removed again. Alone (with 45 m) it gave 57 masts, 4 uncovered and still 5 heads >= 60 px. inf.
3. **Gap fill grid** (coverage after 1 and 2): `MAST_GAP_GRID` radii 18-114 m by 6 m, every 7.5 deg (was 24-108 m by 12 m,
   every 15 deg). With the old grid the 55 m rule left 269 uncovered (56 masts). inf.
4. **Envelope clearance (F4)**: `MAST_ENV_CLEAR` 2 m - a candidate is rejected when its base plate is within 2 m of a painted
   envelope line (`SHA.markings.apron().envelopes`, the safety line), i.e. its foot within 3.13 m, in the main pass and the gap
   fill (rejection 'envelope clearance'). inf.
5. **Stored placement (F7)**. The placement is deterministic and tier-independent, so it is stored: `jobs/gates.mjs SET=masts`
   loads the page with `?masts=live`, takes the page's own live pass and writes `data/sha_masts.json` / `.js` (`inputs`,
   `hash`, `masts`, `uncovered`, `stats` without times). The page (`gates.js`) fetches the JSON in `buildWorld` (so `start()`
   finds it resolved: awaiting a fetch in `start()` let the render loop draw one more llvmpipe frame first, 1-3 s) and
   `placeMasts({cache})` uses it only when `cache.inputs` equals the FNV-1a hash of this page's inputs: the source text of the
   placement code (`placeMasts`, `camSubject`, the camera tests, `towerViewCams`, the footprint / building helpers), its
   constants and rules, and every derived input (stands, footprints, lead-in sweeps, bridge parts and docking sweeps, posts,
   building outlines, lanes, runways, envelopes, equipment areas, the pavement signature `vectorPavement().sig`, the stand
   and Tower cameras). Otherwise (or with `?masts=live`) the live pass runs and the page logs (console.log, not a warning)
   that the file is stale and how to rebuild it. `stats.source` says 'cache' / 'live'; `SHA.qa.mastsLive(rules)` runs a dry
   live pass (places nothing). Deferring the pass after the first frame was the alternative; it was not chosen because every
   consumer (light map, legend, shell, jobs) reads the list right after `__shaReady`.
6. Legend: "... kept out of the "Fly to stand" views and the Tower view's foreground ...".
7. `jobs/gates.mjs`: the fix3 checks now also print and require (a) no mast in the near field (90 m) of the app's real Tower
   camera (`SHA.qa.view('tower')`, read from `SHA.rig.camera()`, independent of `towerViewCams`) at the job viewport and at the
   iPhone 15 portrait viewport 393 x 659, (b) no foot within 3.13 m of an envelope line, (c) the page used the stored list and
   it equals a dry live pass; they print the heads >= 40 px at >= 45 m on the side "Fly to stand" takes (F3). `SET=fix4`
   renders the views below; `SET=masts` writes the stored placement.

### Result (`jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1`; `out/fix4/before/check.log`, `out/fix4/gates/check2.log`)

| | before (HEAD) | after |
|---|---|---|
| masts (high / low), hash | 58 / 58, `edc568b` | **58 / 58**, `84264519`, identical lists (tiers SAME) |
| stands with no mast within 120 m | 3 (310, 121, 126) | **2** (310, 126) |
| Tower view, laptop 1280 x 720: masts in the 90 m near field; largest head | 1 ("115", depth 52 m); 65 px | **0**; 3 px (1.3 km) |
| Tower view, phone 393 x 659: same | 1 ("115"); 41 px | **0**; 2 px (1.4 km) |
| feet within 3.13 m of a painted envelope line (F4) | 3 (289 1.18 m, 328 2.25 m, 268 2.96 m) | **0** (nearest 3.35 m, "112") |
| "Fly to stand" (side taken): stands with a head >= 60 px at >= 45 m | 8 (contact 6: 115, 224, 229, 260, 261, 274; remote 307, 317) | **0** |
| same, head >= 40 px (40-72 px band) | 74 (contact 18) | 66 (contact 13; largest 54 px at 259) |
| contact-stand cameras with a near-field mast (sampled / app / review 60 px test) | 0 / 0 / 0 (at 45 m) | 0 / 0 / 0 (at 55 m) |
| feet within 2 m of an equipment area; plates + 1 m off pavement | 0; 0 | 0 (nearest 3.17 m); 0 |
| "Fly to stand" side -1 (contact) | 42 (0) | 44 (0) |
| placement on the page (llvmpipe) | 1.08-1.20 s | **24-58 ms** (stored; prep 6-7 ms + hash 13-17 ms); the live pass of the new rules 1.9-2.5 s |
| page source | live | `cache`, inputs `904af9ec` equal on high and low; equal to a dry live pass |

By area unchanged (T2 apron 2: 22, east apron 11, east remote 8, west remote 6, south-west 4, T1 north 3, business 3, T1
west 1); by placement: ahead of a stand front 25, between stand noses 11, rotunda line 7, gap fill 15 (was 27 / 10 / 13 / 8).
The T1 west face mast "115" moved from the rotunda line (440.5, 124.6) to (399.2, 186.2) by the gap fill, behind the 115 /
120 tails, out of both Tower frames; it now also covers 121. Rejections include 'tower view near field' 4 and 'envelope
clearance' 451. Rule variants tried (dry passes, `out/fix4/exp.mjs`): subject band 8 deg / 60 m with 45 m: 57 masts / 4
uncovered / 5 heads >= 60 px; 55 m, old grid: 56 / 4 / 0; 50 m: 57 / 4 / 1; 55 m + new grid, tower 70 m: 58 / 3 / 0
(the "115" mast at 79 m in the laptop frame); tower 90 m or 110 m: 58 / 2 / 0 (chosen: 90 m). With every new rule off, the
refactored pass reproduces the HEAD hash `edc568b`.

**Start-up (F7)** (`out/fix4/f7probe.mjs`; time from navigation to `__shaReady`, llvmpipe, other agents loading the 4 CPUs,
load 3-5): HEAD 10.9-12.8 s with a 1.08-1.20 s placement; interleaved loads of this round: stored list 8.9-11.5 s (placement
33-47 ms) against `?masts=live` 12.0-13.1 s (placement 1.9-2.1 s). The light map's pool pass (markings, on the first frame
after the masts) is unchanged at 0.20-0.36 s. So the ~1.4 s is now ~0.25 s; the remaining part is the pool pass.

### Renders (looked at; `fix4_gates_tower_envelope.png`, `fix4_gates_fly_middle.png`)

- **Tower view** (`view_towercab`, `view_phone_towercab`, `out/fix4/gates/a_fix4_towercab.png`): the "115" mast is gone from
  both framings; the laptop frame shows the shadow of the re-placed mast at its lower left edge (the pole stands 111 m from
  the eye, 46 deg left of the view axis, outside the frame); the next mast heads are 2-3 px at 1.3-1.4 km.
- **"Fly to stand" 274, 229, 260, 115, 224** (aircraft parked; before/after): the 47-50 m masts that framed the subject are
  gone; at 260 and 115 a pole now stands far behind the aircraft (small heads near the top); at 224 only a pole's shadow enters the
  left edge; 274 and 229 have no mast in the foreground or middle distance.
- **The mast by 290** from straight above: before, the plate sat on the red 290 line; after, the nearest mast is 3.35 m
  (foot) from any envelope line.
- **Named views**: `view_towercab` / `view_phone_towercab` clear; `view_tower` (the orbit view from outside) now shows the
  re-placed "115" on the T1 west apron in the foreground, as a mast seen from outside the cab should be; `view_stand_113`
  shows the same "112" mast at the right as in round 3 (its position did not change; at 51.6 m it is now inside the 55 m
  near field of this QA view, which is not the app's "Fly to stand" camera for 113 - that one is clear); **`view_bridge_230`
  and day `view_t2pier` show a new pole next to the B77W at 230**: the gap-fill mast for 231 at (-816.2, -234.2), placed
  because the 55 m rule removed the mast that covered 231 in round 3. It passes every rule and is outside the 230 / 231
  "Fly to stand" frames' 40 px band, but in `view_bridge_230` it is the strongest vertical in the frame (open below).

### Checks

- `jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1`: "fix3 requirements: met" on high and low (contact near field 0, equipment
  0, plates 0, Tower view 0, envelope 0, stored list used and equal to a live pass), tiers SAME, console 0 / 0 / 0.
- `SET=fix4` (renders, DEBUG park 113, 115, 224, 229, 233, 260, 274): every bridge docked, console clean.
- No-browser tests and the named views: see "Regression checks (whole round)" below.

### Regression checks (whole round 4: gates, markings, buildings)

- `jobs/markings.mjs LIGHTTABLE=1` (21:30): 58 masts, **0 of 164 stand nodes below the stand level** (1.137; 55 at it, min /
  p10 / median / max 1.137 / 1.137 / 1.324 / 1.98), `check926` other-apron min / stand mean **0.500** (stands avg:min 1.13,
  other 1.38). The job compared the node factor rounded to 3 decimals with the level rounded to 4 and listed 55 nodes at the
  level as "below" (1.137 < 1.1373); it now compares the unrounded factor (tolerance 0.0005, below one 8-bit step 0.0098).
- Named view set re-rendered with the four commands of `integration.md` "Fix round 3" I3 (25 `view_*.png`, all looked at, in
  before / after sheets `out/fix4/sheets/`): pixels changed > 8 levels: 0.0-0.1 % in the runway, T1, T2, overview, stand
  233 / 102 / 404 and laptop stand views (mast positions only; `view_hold_H1` and `view_stand_404` identical), 0.3-0.8 % in
  `t2pier`, `stand_113`, `tower`, `towercab`, `bridge_230`, `phone_towercab`, 1.4-2.2 % in the two legend views (the legend's
  new wording), and by design the night views: `view_night_hold_H1` 94 % (F5: the black ground is now dark grey),
  `view_night_stand_233` 39 % (F5 beyond the taxilane; F2 under the bridges), `view_night_t2pier` 8 %. All 10 parked aircraft
  placed, all bridges docked, orientation checks ok.
- Console: `MOCK_RELAY=1 SCENES=snapshot,park,live jobs/integration.mjs` -> "INTEGRATION: all scenes clean" (each scene 0
  errors, 0 warnings, 0 page errors, HTTP >= 400 0, failed requests 0; the fetch of `data/sha_masts.json` included).
- No-browser: `test_buildings3d.mjs` all passed (stand-head fill 21 rings / 69 stands), `test_geo_js.mjs` passed,
  `test_relay.py` 11 / 11 OK, `test_metar_zsss_js.mjs` passed, `test_frame.py` OK; `node --check` on every changed module and job.

### Open after this round

1. The gap-fill mast for 231 stands beside the B77W at 230 in `view_bridge_230` and `view_t2pier` (both QA / named views,
   not app cameras). Moving it needs either another camera in the placement (not a UI view) or a gap-fill preference for
   positions behind the stand rows; left for the review to judge.
2. `view_stand_113` (QA view, 75 m / 22 deg) has the "112" head at 51.6 m, inside 55 m; unchanged position since round 3.
3. 310 and 126 still have no mast within 120 m (business apron: plate + 2 m off pavement or in a lane clearance; T1 west face:
   stand camera / building).
4. The stored placement must be rebuilt (`SOFTGL=1 SET=masts node livetest.mjs jobs/gates.mjs`) after any change to the
   placement code or its inputs (stands, bridges, markings envelopes / equipment areas, pavement fills, the tower anchor);
   until then the page places the masts live (correct, ~2 s slower) and `jobs/gates.mjs fix3` reports FAILED. Package P3-E
   may add methods to `gate_system.js`; methods outside the hashed list do not invalidate the file.
5. The pool pass (0.20-0.36 s, first frame after the masts) was not changed.

## Verification fixes, round 1 (2026-11-27)

Answers the adversarial verification of fix round 4 (findings F1-wide-aspect medium, F3-gapfill-frames-subject low,
NAMED-231-mast low, F7-stale-cost low; F2 in `markings.md`; F4, F5, F6 and the regression checks were confirmed). Files
changed: `js/live/gate_system.js` (`TOWER_CAM`, `standCamHead`, the gap-fill rank, `MAST_GAP_HEAD` / `MAST_GAP_SUBJ`),
`js/live/gates.js` (stale-cache warning), `jobs/gates.mjs` (Tower view at five viewports, the review probe's test, the 1440 x 900
and gap-fill head lines), `data/sha_masts.json` / `.js` (rebuilt), `docs/phase2/fix4_verify_tower_fly.png` (new composite),
the 25 named views, `CLAUDE.md`. "Before" = the fix-round-4 state (stored hash `84264519`, inputs `904af9ec`; the verifier's
renders in `out/review4/`); scratch, probes and renders in `out/fix4/v1/` (gitignored). All parameters below are inf (UI
camera choices). I looked at every render named here.

### F1-wide-aspect (medium): the Tower view at any aspect

The verifier was right: `app.js view('tower')` keeps a 46 deg vertical field on every landscape aspect, so a 1920 x 970
window shows 80 deg across and the gap-fill mast "112" (139 m from the eye, 38.5 deg off the axis) stood in the frame with a
45 px head; `towerViewCams` had tested only a 16:9 frame. `app.js` is not a file of this package, so the fix is in the
placement:

- `TOWER_CAM.land.aspect` 16/9 -> **2.4**: the widest landscape frame in practice (21:9 monitors 2.33-2.39, iPhone 15
  landscape 2.14, 1920 x 970 1.98); every narrower landscape frame lies inside it (the pitch does not depend on the aspect).
- `TOWER_CAM.port.tanX` tan 20 deg -> **tan 29 deg**: the union of every portrait frame of aspect 0.3-1 (the app's portrait
  field is 58-72 deg vertical; at aspect 0.66-1, e.g. a portrait tablet, the half width reaches 29 deg).
- The near field as an angle: `TOWER_CAM.headDeg` **1.0 deg** -> `nearDepth` 4.4 m / tan 1 deg = **250 m** (was 90 m): a
  head in either frame is < 15 px at 1280 x 720, < 20 px at 1920 x 970, < 22 px at 1920 x 1080.

Why 250 m and not less (dry passes in one page, `out/fix4/v1/exp.mjs`, wide frames + the gap-fill rank below):

| tower near depth | masts | stands without a mast within 120 m | nearest mast in a Tower frame (1280 x 720 / 1920 x 970 px) |
|---|---|---|---|
| 90 m (wide frames) | 59 | 3 (310, 121, 126) | "114" at 111 m, 34 / 46 px; "113" at 181 m (fails the review probe) |
| 120 m, 150 m | 58 | 6 (310, 114, 115, 120, 121, 126) | "113" at 181 m, 23 / 31 px (fails the review probe: >= 20 px within 300 m) |
| 200 m, **250 m** (chosen) | **57** | **7** (310, **113, 114, 115, 120**, 121, 126) | 1.22 km, 3-5 px |

The T1 west face stands 113-121 are 57-168 m from the tower eye, right in front of it: every position the other rules
(stand cameras, building, lanes, envelopes, equipment areas) leave for a mast near them is in the Tower frame 100-181 m from
the eye. So the clear Tower view costs the T1 west face its masts (the brief's "keep T1 west face coverage" could be met only
with a mast in the Tower foreground, which the verifier's own probe fails). Those stands stay lit to the stand level at night
by the light map's floors (fix round 3, V1; `jobs/markings.mjs LIGHTTABLE=1` below: 0 of 164 nodes below the level). The
alternative that would keep them: cap the horizontal field in `app.js view('tower')` at ~74 deg on wide screens (lower the
vertical field when aspect > 16:9) - then the 16:9 frame and 90 m of round 4 suffice. That is the lead's file and call
(requests list).

Result (`jobs/gates.mjs SET='fix3;fix3low' CHECK_ONLY=1`, `out/fix4/v1/check.log`; the job now tests the app's own camera at
the job viewport 1280 x 720, 1920 x 970, iPhone 15 landscape 734 x 343, iPhone 15 portrait 393 x 659 and a portrait tablet
820 x 1080, with two tests each: the sampled near field (< 250 m) and the review probe's (a head in the frame within 300 m
that is >= 20 px)): **0 / 0 at all five viewports, both tiers**; the nearest head in any frame is 1.22-1.50 km away (1-5 px).
The verifier's own probe (`out/review4/rv4.mjs`, run unchanged at 1920 x 970, 1440 x 900 and 734 x 343,
`out/fix4/v1/rv/*_probe.json`): `f1fail` [] at all three (before: ["112"] at 1920 x 970), nearest mast in frame 1,220 m
(before 139 m). Renders: `out/fix4/v1/rv/{fhd,lap,pland}_towercab.png` - the "112" pole at the right edge and the
re-placed "115" mast's shadow at the lower left are gone (`fix4_verify_tower_fly.png`, top two rows). `jobs/gates.mjs`
requirement: no mast in the near field and none in the probe's test at any of the five viewports.

### F3-gapfill-frames-subject (low) and NAMED-231-mast (low): the gap fill's choice

The gap fill took the nearest grid candidate that passed every rule, so its masts stood 55-70 m in front of stand cameras
("268" left of the 268 nose, "259" in its own view, "112" in 113's). It now ranks the grid (`placeMasts`, `headCost`):

- for each candidate, the largest lamp head it shows in the camera each stand takes ("Fly to stand": side +1 of a contact
  stand, side +1 of a remote stand while clear, else side -1; `standCamHead` = 2 x headR / depth when the head is in the
  16:9 frame) divided by `MAST_GAP_HEAD` = tan 3.0 deg (a 4.4 m head at >= 84 m: < 40 px at 1280 x 720, < 50 px at
  1440 x 900 with the 50 deg field), and in the Tower view cameras divided by tan `TOWER_CAM.headDeg`;
- `MAST_GAP_SUBJ` 2: a candidate within 2 x the subject margin of a taken camera's subject (`standCamPos` d < 2, i.e. within
  8 deg of the parked aircraft, rotundas and cabs) ranks as if its head were 2 / d times the limit;
- candidates under both limits are equal and stay nearest first (as before); the rest follow by ascending cost (stable sort,
  deterministic; the hash is the same on both tiers).

Stated as angles, so the metric does not depend on the viewport (the verifier's request). Tried and not kept: the same rank in
the main pass (59 masts, 311 also uncovered, heads >= 60 px at 1440 x 900 at 7 stands instead of 5); `MAST_GAP_SUBJ` 0 / 1.5 /
3 (3 moves the 231 mast, see below).

| "Fly to stand", side taken | before (round 4) | after |
|---|---|---|
| job: stands with a head >= 40 px at 1280 x 720 at >= 45 m | 66 (contact 13) | **56 (contact 4**: 102 42 px, 110 43, 246 40, 256 50 - all main-pass masts) |
| job: stands with a head >= 60 px at 1440 x 900 (x 1.25) | 10 (contact 5) | **5 (contact 1**: 256) |
| job: gap-fill masts with a head >= 40 px at 1280 x 720 in a taken camera | 9 (largest "259" 54 px in 259's view) | 4 ("309" 41, "323" 40, "335" 43, "336" 41 px: east remote apron rows with no candidate under the limit) |
| review probe (`rv4.mjs`, 1440 x 900, head box nearest corner): heads >= 40 px | 71 (contact 14) | **62 (contact 7)** |
| review probe: heads >= 60 px at 1440 x 900 | 23 | **17** (all main-pass masts: 284 / 280 / 326 / 301 / 305 at 55-65 m beside remote stands, 256) |
| review probe: 268 / 259 / 113 / 261 (largest head) | 48 px (268) / 56 (259) / 51 (112) / 44 (263) | none >= 30 / 37 px at 87 m / none >= 30 / 40 px at 82 m |
| near field (55 m) on a contact stand's taken side | 0 | 0 |

Renders (1440 x 900, aircraft parked as the verifier had them, `out/fix4/v1/day/`, pairs `out/fix4/v1/cmp_fly*.png`):
**268** - the pole left of the nose is gone (the nearest mast is now the "264" gap fill beyond the bridges, 134 m, 30 px);
**113** - the "112" pole beside the aircraft is gone, no mast in the view; **259** - its mast moved from 60 m beside the
aircraft to 90 m behind it, on the open apron (45 px at 900 rows); **261**, **260** - similar to before, the masts slightly
farther. `fix4_verify_tower_fly.png` (rows 3-4).

**NAMED-231 stays open.** The "231" gap-fill mast (-816.2, -234.2) did not move: in every app camera its head is < 40 px
(230: 103 m, 32 px at 1440 x 900; 231: 102 m), so the rank has no reason to move it; it remains beside the B77W at 230 in the
QA views `view_bridge_230` (69 m, 47 px at 1280 x 720) and `view_t2pier`. `MAST_GAP_SUBJ` 3 does move it (to -757, -236), but
into 231's own "Fly to stand" frame (80 m, 40 px at 1280 x 720) and `view_stand_233` (120 m); trading an app camera for a QA
view, so not kept. Putting the QA views themselves into the placement is possible but would tune the app to its test set;
left for the owner / next review.

### F7-stale-cost (low)

A stored placement whose `inputs` do not match is now a console **warning** (`gates.js`), so every job that requires a clean
console (`jobs/integration.mjs`, `jobs/gates.mjs`, the review probes) fails on a stale file. Tested by serving a copy with
`inputs` "deadbeef" (`out/fix4/v1/stale.mjs`, `page.route`): `stats.source` "live (cache stale: inputs deadbeef)", the live
pass 1.76 s, the same hash `1b7bccfe`, and the warning "[gates] masts: data/sha_masts.json does not match this page ...
rebuild it with SOFTGL=1 SET=masts node livetest.mjs jobs/gates.mjs". Package P3-E (edits `gates.js` / `gate_system.js`) should
end with `SOFTGL=1 SET=masts node livetest.mjs jobs/gates.mjs` and then `SET='fix3;fix3low' CHECK_ONLY=1` (requests list,
CLAUDE.md conventions).

### Stored placement and checks after the fixes

- `SET=masts`: 57 masts, hash **`1b7bccfe`**, inputs **`db34b7b8`**, uncovered 7, live pass 1.88 s; equal to the dry pass of the
  experiments. By area: T2 apron 2 22, east apron 11, east remote 8, west remote 6, south-west 4, T1 north 3, business 3,
  T1 west face 0 (was 1). By placement: ahead of a stand front 25, between stand noses 11, rotunda line 7, gap fill 14 (was
  15). Rejections 'tower view near field' 64 (was 4).
- `SET='fix3;fix3low' CHECK_ONLY=1` (`out/fix4/v1/check.log`): **"fix3 requirements: met" on high and low**, tiers SAME
  (`1b7bccfe`); contact near field 0 (sampled, app and review tests), side -1 at 38 stands (contact 0), equipment 0 (nearest
  3.17 m), plates 0, envelope 0 (nearest foot 3.51 m, "112" to 111's line), the named stand views clear (`stand:113` too:
  the 51.6 m "112" of round 4 is gone), Tower view 0 at five viewports, page source `cache`, equal to a live pass; placement
  on the page 36-38 ms, the live pass 2.2-2.4 s; console 0 / 0 / 0.
- Pages ready in 4.8-5.3 s (review probe, three viewports, stored list used).

### Regression checks (round 4 + this round)

- `jobs/markings.mjs LIGHTTABLE=1` (21:30, `out/fix4/v1/markings/lighttable.log`): 57 masts, **0 of 164 stand nodes below the
  stand level** (51 at it; min / p10 / median / max 1.098 / 1.098 / 1.235 / 1.98), `check926` other min / stand mean
  **0.500** (stands avg:min 1.15, other 1.40). The stand level is 1.098 (was 1.137: fewer pools near T1 lower the pools' mean
  over the envelopes; the floors follow it).
- Named views re-rendered with the four commands of `integration.md` "Fix round 3" I3 (`out/fix4/v1/views/views.sh`, 16.5
  min; all 25 looked at, contact sheets `out/fix4/v1/all_*.png`, pairs `out/fix4/v1/sheet_*.png`): pixels changed > 8 levels
  against round 4: `view_tower` 0.40 % (the T1 west face mast in the foreground is gone), `view_towercab` 0.24 % (its shadow
  gone), `view_stand_113` 0.94 % (the "112" pole right of the aircraft and the "115" mast at the left gone), `view_night_t2pier`
  1.01 % (lamp positions), `view_phone_t2_legend` 2.20 % / `view_laptop_live_t2` 0.15 % (the legend says 57), `view_stand_102`
  0.14 %, the rest 0.00-0.07 % (`view_hold_H1`, `view_night_hold_H1`, `view_stand_404`, `view_phone_stand_233` identical). All
  22 DEBUG parked aircraft placed, all 20 bridges docked, orientation checks ok (4 x 3), no stale-cache warning in any log.
- Console: `MOCK_RELAY=1 SCENES=snapshot,park,live jobs/integration.mjs` -> "INTEGRATION: all scenes clean" (0 errors, 0
  warnings, 0 page errors, HTTP >= 400 0, failed requests 0 in each).
- No-browser: `test_buildings3d.mjs` all checks passed (stand-head fill 21 rings / 69 stands / 28,181 m2), `test_geo_js.mjs`
  passed, `test_relay.py` 12 tests OK, `test_metar_zsss_js.mjs` passed, `test_frame.py` OK; `node --check` on the changed files.

### Open after this round

1. NAMED-231 (above): the "231" gap-fill mast beside the B77W at 230 in the QA views `view_bridge_230` / `view_t2pier`.
2. The T1 west face (113, 114, 115, 120, 121) and 310, 126 have no mast within 120 m; reversible by an `app.js` field cap
   (lead) plus `TOWER_CAM` back to 16:9 / 90 m.
3. Main-pass masts still show 50-59 px heads (1280 x 720) at 55-65 m beside some remote stands (284 / 280 / 326 / 301 / 305)
   and at 256 (rotunda line); the main pass was left as designed (ranking it did not help, above).
