# Cross-area polish A: integration hand-offs to room, suite and monuments

Items addressed to **room**, **suite** and **monuments** in `from_integration.md` (QA r1, r2 and r3 batches) after those
areas met the bar (room w16, suite w13, monuments w18). Each one was checked against `ref/ana/` and real in-flight photos
(`ref/web/`, gitignored) before it was implemented.

## Room

| item (batch) | verdict | change |
|---|---|---|
| jShell / jCap r 0.46 / 0.45 -> 0.34, satin rims (r1) | already done in room w12 | none |
| Padded header band reads as hammered metal (r2) | supported: the c_27315 band behind the headrest is smooth satin | `jBand` LAYER.leather -> LAYER.plastic, r 0.40 -> 0.45 (09c_room.js) |
| Charcoal shells / caps slate, 1.3-1.6x too light (r3) | PENDING | |
| moodGlow no longer read (r2, FYI) | left in place (harmless one-line key) | none |

## Suite

| item (batch) | verdict | change |
|---|---|---|
| fShell r 0.45 -> 0.34 (r1) | supported: rim sheen lines in omaat_f2 / f5 and f_17301 | suite override `fShell` r 0.34 (09d_suite.js) |
| Bed sheet / duvet clip white in bed mode (r1, r2, r3) | supported: f_17304 bed L187, omaat_f59 L200 against q04 L225-227 | pad + bare-sheet corner #f0efea -> #d6d2ca, duvet #d2cec6 -> #c4c0b8, flap #b9b5ad -> #aca89f (keeps w13a's flap ~0.88x the duvet) |
| (w13a low, same lines) aisle drape reads as a crisp ledge | cheap, in the same block | drape tucked under the rounded duvet edge (0.022 x 0.12, r 0.010) |
| Shallow ottoman recess (r2, r3) | supported: omaat_f11 shows a deep dark void under the tray and a thin grey plinth line | 0.05 x 0.40 lit plinth -> 0.03 x 0.025 strip set back 0.13 m, dark recess floor |

## Monuments

| item (batch) | verdict | change |
|---|---|---|
| F front drapes cool light grey (r2, r3) | supported: omaat_f40 drapes #433f3c h20 against q01 #515053 h267 | `curtainFF` #6d6b6b -> #5f5650 (10_mono.js) |
