# SFO airport geometry: build report

Built by `tools/build_sfo_airport.py` from the SFO Museum *sfomuseum-data-architecture* checkout (`/home/user/Calc/sfo3d/tools/../refs/sfom-arch/data`, commit 5f64ee8e 2025-10-30, CDLA-Permissive-1.0): 2019 GeoJSON files scanned, 366 with `mz:is_current == 1` used.

- Output: `/home/user/Calc/sfo3d/data/sfo_airport.json`, **151.6 KB** (155227 bytes, compact JSON).
- World frame: x = east, z = south (m), origin ARP 37.6188056, -122.3754167; frame `ltp-nad83-2011` (exact GRS80 local tangent plane at the ARP, datum NAD83(2011); `tools/geo_frame.py` = `js/geo.js`); coordinates rounded to 0.1 m. `bounds` = [-2383.9, -2074.1, 1663, 1543.1].
- Datum note: the SFO Museum lon/lat are used as NAD83(2011). The source records carry no datum (GeoJSON/RFC 7946 nominally means WGS 84); the runway sanity check below measures the offset of the source runway polygons from the FAA NASR (NAD83) centrelines.
- Douglas-Peucker tolerances: terminal complex / terminals / boarding areas 0.4 m, runways 0.3 m, taxiways 0.3 m, structures 0.3 m. Rings < 20 m^2 dropped; holes kept.
- Rings: outer counter-clockwise / holes clockwise in (east, north) = (x, -z); open (first vertex not repeated). Every feature also carries its `id` (wof:id).

## Counts

| Category | Current source features | Output entries | Polygons | Rings (holes) | Vertices |
|---|---|---|---|---|---|
| terminalComplex | 1 | 1 | 1 | 12 (11) | 1046 |
| terminals | 4 | 4 | 4 | 10 (6) | 1086 |
| boardingAreas | 7 | 7 | 7 | 7 (0) | 545 |
| taxiways | 89 | 89 | 180 | 180 (0) | 3687 |
| runways | 4 | 4 | 8 | 8 (0) | 32 |
| structures: atc | 1 | 1 | 1 | 1 (0) | 4 |
| structures: garage | 5 | 5 | 6 | 7 (1) | 387 |
| structures: building | 2 | 2 | 2 | 2 (0) | 44 |
| structures: hangar | 1 | 1 | 1 | 1 (0) | 12 |
| structures: hotel | 1 | 1 | 1 | 1 (0) | 58 |
| structures: airtrain | 25 | 25 | 25 | 25 (0) | 427 |
| structures: rail | 1 | 1 | 1 | 25 (24) | 620 |
| gates (points) | 156 | 156 | | | |
| **total polygons** | | | 237 | 279 (42) | 7948 |

Gates: 116 at level 2 (terminal gates), 40 at level 0 (apron positions); 37 have a letter suffix (`variant: true`), 2 duplicate-name records flagged `dup`. Structures: the terminal complex is excluded from `structures`.

## Boarding areas

| Letter | Name | bbox [minx, minz, maxx, maxz] (m) | E-W x N-S (m) | Area (m^2) | Gates (level 2 / level 0) |
|---|---|---|---|---|---|
| A | Boarding Area A | [-1331.5, 512.9, -1132.5, 814.9] | 199 x 302 | 13958 | 16 / 11 |
| B | Boarding Area B | [-1008.6, 527.4, -756.6, 939.9] | 252 x 412 | 25514 | 28 / 3 |
| C | Boarding Area C | [-756.2, 358.8, -593.3, 466.5] | 163 x 108 | 5896 | 11 / 4 |
| D | Boarding Area D | [-740.5, 55.2, -475.6, 362.4] | 265 x 307 | 17196 | 17 / 0 |
| E | Boarding Area E | [-853.5, -86.9, -743.6, 75.6] | 110 x 162 | 6829 | 12 / 8 |
| F | Boarding Area F | [-1317.0, -266.9, -970.5, 152.0] | 346 x 419 | 23989 | 18 / 4 |
| G | Boarding Area G | [-1594.5, -3.0, -1130.8, 211.6] | 464 x 215 | 17010 | 14 / 10 |

## Gates by letter

Order as in the JSON. `(dup)` = later record of a duplicated name; `(L0)` = level 0 without a suffix.

| Letter | Count | Gates | Variants (letter suffix) |
|---|---|---|---|
| A | 27 | A1, A2, A3, A3 (dup), A4, A5, A6, A7, A8, A9, A10, A11, A12, A13, A14, A15 | A1T, A1V, A4R, A4T, A6R, A6S, A7T, A13R, A13S, A13V, A14T |
| B | 31 | B1, B1 (dup), B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B16, B17, B18, B19, B20, B21, B22, B23, B24, B25, B26, B27 | B20S, B23V, B27V |
| C | 15 | C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11 | C4R, C4U, C10R, C10T |
| D | 17 | D1, D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D14, D15, D16, D17, D18 | - |
| E | 20 | E2, E3, E4, E5, E6, E7, E8, E9, E10, E11, E12, E13 | E3K, E3T, E10U, E10V, E11U, E11V, E13K, E13T |
| F | 22 | F5, F6, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, F20, F21, F22 | F15K, F15L, F15M, F15N |
| G | 24 | G1, G2, G3, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G103 (L0), G104 (L0), G105 (L0) | G11R, G12S, G12T, G12V, G13R, G13S, G14T |

## Gates vs building outline

`edge` = nearest point on the (simplified, as-published) outer boundary of the terminal complex, or of a boarding-area polygon when that is > 0.05 m closer; `out` = outward unit normal of that boundary edge; `dist` = gate-to-edge distance. At a vertex the adjacent edge whose normal best matches the gate direction is used. Test: `edge + out * 5 m` must lie outside the terminal complex.

- Level-2 gates (116): dist min 0.0 / median 1.6 / max 18.4 m; 112 inside the terminal complex, 116 inside the building (terminal complex or a boarding area).
- Level-0 positions (40): dist min 10.8 / median 26.1 / max 170.0 m; 40 outside the building (apron stands, not doors).
- Edge taken from a boarding-area polygon (closer than the terminal complex): 41 gates.

## Anomalies

**Duplicate gate names (2).** Both records kept; `dup: true` is set on the later entry, which is ordered to be the *older* record (the first entry is the newest, consistent with the 2024 terminal outlines).

- A3: id 1947304811 (2024-11-05, level 2); id 1763588393 (2021-11-09, level 2, dup); identical position.
- B1: id 1947304807 (2024-11-05, level 2); id 1745882229 (2021-05-25, level 2, dup); 12.6 m apart.

**Outward-normal test (edge + out * 5 m outside the terminal complex).** 153 of 156 gate records pass with the nearest edge; 3 fail:

- A3 (id 1947304811): nearest edge (Boarding Area A, 2.7 m) has out [-0.884, -0.468], probe inside the terminal complex -> fallback edge at 11.5 m, out [-0.891, -0.455].
- A3 (dup) (id 1763588393): nearest edge (Boarding Area A, 2.7 m) has out [-0.884, -0.468], probe inside the terminal complex -> fallback edge at 11.5 m, out [-0.891, -0.455].
- A4 (id 1947304081): nearest edge (Boarding Area A, 9.7 m) has out [-0.884, -0.468], probe inside the terminal complex -> fallback edge at 18.4 m, out [-0.891, -0.455].

Fallback = nearest boundary point on an edge >= 3 m long that faces away from the gate and has open space ahead (the probe and points 2.5 m to either side of it are outside the terminal complex). These entries carry `fallback: true`.

Cause: at the root of pier A the nearest edges are either an internal boarding-area partition or the side of a ~1.5 m wide slot between the pier and the slab west of it, so no nearest-edge normal can point at the apron.

**Normals from facade jogs.** For 4 gates the edge supplying the normal is shorter than 3 m (a jog in the facade); `out` is the normal of the chord spanning +-3 m of boundary instead: B1 (dup) (10 deg change), B27V (44 deg change), C3 (46 deg change), F5 (53 deg change).

**Gates > 30 m from the building boundary (17).** All are level-0 apron positions:

A1T 40.2 m, A7T 36.6 m, A13R 30.4 m, A13S 33.0 m, A14T 32.4 m, F15K 45.6 m, F15L 86.7 m, F15M 86.0 m, F15N 47.7 m, G11R 30.4 m, G12T 39.4 m, G13R 40.7 m, G13S 36.7 m, G14T 51.9 m, G103 166.8 m, G104 168.5 m, G105 170.0 m.

Level-2 gates more than 5 m from the nearest boundary (inside the building): A4 9.7 m, D17 11.4 m, D18 6.9 m.

**Level-2 gates whose parent record is not current (7)** (older snapshots still flagged current; included as instructed): A3 dup (2021-11-09), B1 dup (2021-05-25), C2 (2021-11-09), C9 (2021-11-09), D2 (2024-06-17), E4 (2021-11-09), F5 (2024-06-17).

The 40 level-0 positions all date from 2021-05-25 and hang off the airport campus record.

**Overlapping structures.** 24 footprints form 11 groups of overlapping duplicates (bbox IoU > 0.3), all AirTrain stations: the source has two current generations of station footprints (ids 17297919xx/17300514xx and 17635885xx), and some stations appear twice within the newer one. The app may want to draw one footprint per group:

- Garage A AirTrain Station [1729791949]; Garaga A AirTrain Station [1763588581]
- Garage G AirTrain Station [1729791947]; Garage G AirTrain Station [1763588575]
- Grand Hyatt Hotel AirTrain Station [1729791967]; Grand Hyatt Hotel AirTrain Station [1763588555]
- International Terminal A Air Train Station [1729791961]; International Terminal (G) AirTrain Station [1763588567]
- International Terminal G Air Train Station [1729791965]; International Terminal (A) AirTrain Station [1763588569]
- Long Term Parking AirTrain Station [1730051431]; Long Term Parking AirTrain Station [1763588559]
- Terminal 1 Air Train Station [1729791955]; Terminal One AirTrain Station [1763588563]
- Terminal 2 Air Train Station [1729791959]; Terminal Two AirTrain Station [1763588561]
- Terminal 3 Air Train Station [1729791957]; Terminal Three AirTrain Station [1763588573]
- West Field Road AirTrain Station (Inbound) [1729791953]; Westfield Road AirTrain Station (Inbound) [1763588571]; Westfield Road AirTrain Station (Inbound) [1763588577]
- West Field Road AirTrain Station (Outbound) [1729791951]; Westfield Road AirTrain Station (Outbound)g [1763588557]; Westfield Road AirTrain Station (Outbound)g [1763588579]

  Name clash: co-located International Terminal stations carry different letters ("International Terminal A Air Train Station" vs "International Terminal (G) AirTrain Station"; "International Terminal G Air Train Station" vs "International Terminal (A) AirTrain Station"). By position the older records are right (A is the southern station, at the Garage A / Boarding Area A end), so the "(A)"/"(G)" names of the 17635885xx records are swapped. Published as in the source.

Source name typos kept as-is: "Garaga A AirTrain Station", "Westfield Road AirTrain Station (Outbound)g", "Westfield Road AirTrain Station (Outbound)g".

**Geometry clean-up.**

- Dropped rings < 20 m^2: SFO Terminal Complex [1947304067] hole 0.06 m^2; SFO Terminal Complex [1947304067] hole 0.00 m^2; SFO Terminal Complex [1947304067] hole 0.01 m^2; International Terminal [1947304069] hole 0.06 m^2; Terminal 2 [1947304591] hole 0.01 m^2; Taxiway S2/S3 [1730008905] hole 13.34 m^2; Taxiway S2/S3 [1730008905] outer 0.23 m^2; Long Term Parking AirTrain Station [1763588559] outer 4.96 m^2; Long Term Parking AirTrain Station [1763588559] outer 4.67 m^2; AirTrain Rail [1779914099] hole 16.55 m^2.
- Max distance from any source vertex to the published outline: terminal complex 0.42 m (tol 0.4); terminals 0.42 m (tol 0.4); boarding areas 0.44 m (tol 0.4); runways 0.07 m (tol 0.3); taxiways 0.33 m (tol 0.3); structures 0.32 m (tol 0.3). Larger values come only from removed defects (zero-width spikes and self-crossing slivers).
- Output validity: 0 polygons with crossing edges, 0 with touching edges; all rings have >= 3 vertices.

## Runway sanity check

**Runway designations swapped in the source:** polygon 1730008753 is named "RUNWAY 01R/19L" (wof:name, sfo:id, sfomuseum:name) but lies 230 m off that centerline and is 2333 m long vs 2637 m surveyed; published as "RUNWAY 01L/19R"; polygon 1730008751 is named "RUNWAY 01L/19R" (wof:name, sfo:id, sfomuseum:name) but lies 227 m off that centerline and is 2638 m long vs 2332 m surveyed; published as "RUNWAY 01R/19L". Each polygon matches the other runway's surveyed centerline to within ~1.5 m and ~1 m in length, and its own to within neither, so the build publishes the matching designation as `name` and keeps the source designation as `srcName`.

Polygon centroid (area-weighted, all parts) and long axis from the second moments of area; length/width = extent of the vertices along/across that axis. Surveyed centerline = line between the two surveyed runway ends (same projection). Offsets are perpendicular distances from the surveyed centerline (+ = left of the low-to-high numbered direction); "beyond ends" = how far the polygon extends past each surveyed end along the centerline (negative = stops short).

| Runway (published name) | Centroid x, z (m) | Polygon axis (deg T) | Polygon L x W (m) | Surveyed axis (deg T) | Surveyed L (m) | d-heading (deg) | Offset: centroid / axis ends (m) | Beyond ends (m) |
|---|---|---|---|---|---|---|---|---|
| RUNWAY 01L/19R (src: RUNWAY 01R/19L) | -129.1, 195.1 | 27.81 / 207.81 | 2333 x 61 | 27.80 / 207.80 | 2332 | +0.003 | +1.1 / +1.2, +1.1 | 1L +1.1, 19R -0.1 |
| RUNWAY 01R/19L (src: RUNWAY 01L/19R) | 111.2, 229.4 | 27.80 / 207.80 | 2638 x 61 | 27.80 / 207.80 | 2637 | +0.000 | +1.2 / +1.2, +1.2 | 1R +1.0, 19L -0.0 |
| RUNWAY 10L/28R | 12.7, -259.1 | 117.80 / 297.80 | 3619 x 61 | 117.80 / 297.80 | 3618 | +0.001 | -0.1 / -0.1, -0.1 | 10L +1.3, 28R -0.3 |
| RUNWAY 10R/28L | -28.2, -22.2 | 117.80 / 297.80 | 3470 x 61 | 117.80 / 297.80 | 3469 | -0.001 | -0.2 / -0.2, -0.1 | 10R +1.2, 28L -0.3 |
