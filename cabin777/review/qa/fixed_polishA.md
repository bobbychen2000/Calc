# Cross-area polish A: integration hand-offs to room, suite and monuments

Items addressed to **room**, **suite** and **monuments** in `from_integration.md` (QA r1, r2 and r3 batches) after those
areas met the bar (room w16, suite w13, monuments w18). Each one was checked against `ref/ana/` and real in-flight photos
(`ref/web/`, gitignored) before it was implemented.

## Room

| item (batch) | verdict | change |
|---|---|---|
| jShell / jCap r 0.46 / 0.45 -> 0.34, satin rims (r1) | already done in room w12 | none |
| Padded header band reads as hammered metal (r2) | supported: the c_27315 band behind the headrest is smooth satin | `jBand` LAYER.leather -> LAYER.plastic, r 0.40 -> 0.45 (09c_room.js); band local contrast 0.154 -> 0.034 (w17b). The round-1 colour #5d5e66 read darker / more violet than the flap (w17a), so the colour is back to #656b73 |
| Charcoal shells / caps slate, 1.3-1.6x too light (r3) | darker: supported (q06 shell faces L96-116 vs c_27312 L53-63). Neutral: **not** taken. The official c_27312 / c_27315 shells are a cool violet-grey (h224-232, s0.14-0.20), and official photos win for colour; the render was slate-cyan (h211), so the hue moved toward violet rather than to neutral | round 1: `jShell` #595d64 -> #434349, `jCap` #5c6066 -> #4b4b50, `jShellIn` #4a4d53 -> #3e3e43 (shared 09_seats.js). Round 2 (w17b medium: the shaded near faces overshot, q09 L45 vs c_27314 L72-83; the photos read cool slate h~220, violet only on the darkest bits): `jShell` #4a4b51, `jCap` #4b4c51. q06 near shell faces L96 -> L79, q09 wall L54 |
| moodGlow no longer read (r2, FYI) | left in place (harmless one-line key) | none |

## Suite

| item (batch) | verdict | change |
|---|---|---|
| fShell r 0.45 -> 0.34 (r1) | supported: rim sheen lines in omaat_f2 / f5 and f_17301 | suite override `fShell` r 0.34 (09d_suite.js) |
| Bed sheet / duvet clip white in bed mode (r1, r2, r3) | supported: f_17304 bed L187, omaat_f59 L200 against q04 L225-227 | pad + bare-sheet corner #f0efea -> #c2beb6, duvet #d2cec6 -> #b0aca4, flap #b9b5ad -> #9b978f (keeps w13a's flap ~0.88x the duvet). The integrator's #d6d2ca / #c4c0b8 only reached L219 under the tone shoulder, so a second step. q04 sheet in shade L227 -> L207, sun patch L244 -> L236; frame > 235 16.5 % -> 12.5 % (the rest is windows / walls, not the bed) |
| (w13a low, same lines) aisle drape reads as a crisp ledge | cheap, in the same block | drape tucked under the rounded duvet edge (0.022 x 0.12, r 0.010) |
| Shallow ottoman recess (r2, r3) | supported: omaat_f11 shows a deep dark void under the tray and a thin grey plinth line | 0.05 x 0.40 lit plinth -> 0.03 x 0.025 strip set back 0.13 m, warm dark recess floor plate. q03 under the tray L55 -> L16 (omaat_f11 L24), warm |

## Monuments

| item (batch) | verdict | change |
|---|---|---|
| F front drapes cool light grey (r2, r3) | supported: omaat_f40 drapes #433f3c h20 against q01 #515053 h267 | `curtainFF` #6d6b6b -> #544c46 (10_mono.js; the integrator's #5f5650 would have stayed ~L82). m02 drape #636465 L100 h229 -> #4f4b47 L76 h30 (omaat_f40 #433f3c L64 h20) |

## Round 2 (raters' carried items in the same blocks)

| item | source | change |
|---|---|---|
| Suite duvet corner reads as overlays on an intact duvet | w13a/b, w14a/b medium | head band is a 0.035 slab whose corner is cut on the diagonal down to the pad; loft starts 0.30 aft (0.05 overlap); bare-sheet triangle removed; flap / roll on top |
| Suite wood flanks chestnut, not espresso | w13b, w14a/b medium | `fFlank` #33291f -> #2f2b22 (omaat_f60 R/G 1.08-1.13) |
| Ottoman recess overshoot, plinth line hidden | w14a low | plinth strip 0.06 further forward, recess floor #4a4038 -> #5e5248; q03 under / top 0.19 |
| curtainFF coffee / lavender split | w19a low (too saturated), w19b medium (lavender, from f_17313) | near-neutral #4f4c4a (m02 #4b4b4a L75). f_17313 is a rendering; the real omaat_f40 / omaatF_2 drapes are dark warm-neutral, so lavender was not taken |

Triangles: the slab and the recess plate add well under 100 triangles to the occupied bed / suite units; the sheet triangle
is gone. No change to the far LODs or the room meshes.

## Ratings

| area | before (last rating) | round 1 (A / B) | round 2 (A / B) |
|---|---|---|---|
| room | w16 8.5 / 8.5 | w17 8.5 / 8.5 | w18 8.5 / 8.5 |
| suite | w13 8.5 / 8.7 | w14 8.6 / 8.8 | w15 8.6 / 8.9 (w16 after round 3: pending) |
| monuments | w18 8.5 / 8.6 | w19 8.6 / 8.6 | w20 8.6 / 8.7 |

## Round 3 (suite only)

w15a kept the duvet corner as a medium (partly fixed): the round-2 head-band slab stood 1-2 cm proud of the lofted duvet
with a square window-head corner, and the flap / roll were near-coplanar (dashed fold line). Fix (f7c9416): one slab flush
with the loft's rounded edge (top 0.515), rounded window-head corner, loft from 0.25 aft, flap / roll at 0.527 / 0.531.
A lofted window-side head band (w15a's suggestion) was tried first and read as a separate pillow with a seam; dropped.
Room and monuments did not change after round 2, so their w18 / w20 ratings stand.
