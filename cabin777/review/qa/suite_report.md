# THE Suite (first class): area report

Owned file: `src/09d_suite.js`. Shared edits, all small and local:
- `SEATMAT` f* values in `src/09_seats.js`.
- The suite seat plaque in `buildSeats` (09_seats.js).

## Scores

Each round had two independent raters. A is the skeptic; B looks at geometry first.

| round | A | B | ratings |
|---|---|---|---|
| r3 (start) | 6.3 (single rater) | | `suite_r3.json` |
| w1 | 6.1 | 6.4 | `suite_w1a/b.json` |
| w2 | 6.7 | 7.3 | `suite_w2a/b.json` |
| w3 | 7.2 | 7.4 | `suite_w3a/b.json` |
| w4 | 7.8 | 7.8 | `suite_w4a/b.json` (no high-severity issues) |

- The brief allows 4 rounds, so the suite stops at 7.8, below the 8.5 target.
- Fixes made after the w4 ratings are not rated yet: the solid centre-fin wedge, the forward arm moved outboard, and the duvet separated from the pad.
- Before/after sheet: `suite_before_after.jpg` (own renders only).

## What changed (commits e93c66f, 7244177, c49334e, 41b5158, 978e39b, 4425808, 6a358b3, 44cf870 and the final commit)

Sources are real in-flight photos in `ref/web/suite/` (79 files, listed in `INDEX.md`; gitignored) plus ANA's real photos f_17313/17314. Every value carries a [V], [D] or [A] comment in the code.

- **Shell:**
  - Squared, flat-topped caps replace the 0.085 round bullnose (omaat_f7/f5, pb_20).
  - The forward aisle corner is one thick flat-topped arm (omaat_f4).
- **Aisle exterior:**
  - Two equal 0.50 m sliding leaves are parked at either end of a ~0.64 m opening (omaat_f7, up_empty).
  - Frames are 0.055 and mid-dark, with rounded half-round ribs (pb_20, omaat_f4).
  - The fixed wardrobe run is dark wood (pb_20).
  - Ribs are deliberately 15 per leaf against about 22 in reality, because finer ribs alias to moiré [A].
- **Screen wall:**
  - The window wing is 0.08 with a rounded top corner, plus a small taupe shelf.
  - A 60° angled aisle pier (~0.22 wide) carries a grey-rimmed reflective pill mirror and a reading spot (omaat_f10).
  - A taupe top closes the triangle behind the pier.
  - The centre suites get a solid dark-wood wedge between the D and G screens (omaat_f3/f4).
  - The centre-suite mirror stays inside the shell (the r3 bug where it floated in the aisle is fixed).
- **Window console:**
  - A taupe fascia sits over a near-black body with a long grille, a bin seam and a trim line (omaat_f7, up_privacy_wall).
  - The tray insert is tapered warm wood (omaat_f47).
  - Keypad and handset sit in 12° tilted docks (f_17313).
  - The outlets pocket was removed: the sockets are inside the bin (omaat_f16).
- **Seat:**
  - It is 0.72 wide (34 in, thepointsanalyst). In the 1.10 m centre suite it is capped by the available room at 0.63.
  - The back is taller and nearly upright (top ~1.14 m, 5°).
  - The back sits in a lighter taupe niche (jambs plus header) with ~0.075 reading spots, shown off (omaat_f5/f9).
  - The headrest flap is neutral grey, 1.2× the back, hung from the top edge (omaat_f9).
  - The leg rest is flush, and the lavender pillow is a plump rectangle.
- **Ottoman:** a cantilevered cushion on a taupe tray over an open void (omaat_f10, pb_30).
- **Centre divider:** lowered by default, as in most photos (omaat_f1/f3/f5). `opts.divider = 1` raises it. It has a thin rail with a tab.
- **Bed:**
  - The duvet is narrower than the pad, offset to the window side, with a turn-down.
  - The white pillow is propped up, with the lavender pillow low in front (omaat_f46).
- **Materials:**
  - Flap, fabric (warm grey, no mauve), cool table wood, lavender pillow, dark door frames, console body.
  - The plaque is a flush slot a shade darker than the cap.
- **Triangles:** the suite unit went from 11.1k to 12.0k (window) and from 11.4k to 11.6k (centre). The far LOD is unchanged at 158.

## Raters who were wrong, or trade-offs made

- **Carpet colour.** The photo gatherer said the carpet was blue-grey. The daylight close-up pb_30 shows brown heather with navy flecks; the blue comes from mood lighting. Reported to shell, now applied.
- **Mirror.** The photo gatherer said there was no wall mirror. The pill on the pier reflects (omaat_f10, up_forward_look), so it is modelled as a mirror.
- **Door ribs.** Both raters asked for about 23 ribs per leaf. That is kept at 15 to stop moiré on phones [A].
- **Pier width from the seat (w4a).** The pier is foreshortened from the seat, because a 1.24 m window suite cannot fit a 0.28 m pier beside a 0.976 m bezel. Left as is.

## Open (other areas / user)

- **Integrator:** tint layer-15 atlas glow by the material colour, so the plaque text glows blue-violet (`from_suite.md` #3).
- **Lighting:** the suite interior renders about 2× too dark, and the sun patches on the bed are blocky (`from_suite.md`).
- **User** (`questions_suite.md`):
  - Centre-suite width. Photos imply ~1.2 m against 1.10 in `05_layout.js`.
  - A divider toggle.
  - A closed-door state.
  - Whether there is one fin or two between the centre screens.
