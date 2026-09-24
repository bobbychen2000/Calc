# Area worker brief (parallel photo-QA sessions)

Several Claude sessions work at once, one per **area**. Each owns a disjoint set of files. All push to the same branch,
`claude/ana-777-cabin-3d-ts5kra`. The user is asleep and wants the cabin **as photo-realistic and detail-accurate as possible**.
Round 1 rated the cabin 4.6/10 on average against the real photos; round 2 rated it 5.4. The target is at least 8.5 in every area.
Work autonomously; nobody will answer questions before you finish.

First read `cabin777/CLAUDE.md` in full, especially "How the user wants this built" and "Parallel work", then `cabin777/REFERENCE777.md`.

## Areas

| area | owned files (edit only these) | QA views (`test/qa.js`) | latest rating |
|---|---|---|---|
| suite | `src/09d_suite.js` | q02_suiteAisle q03_suite1A q04_suite1Abed q05_suiteBehind | `review/qa/suite_r3.json` |
| room | `src/09c_room.js` | q06_roomMain q07_seat11A q08_seat12H q09_centrePair q10_seat14D | `review/qa/room_r3.json` |
| py | `src/09b_py.js` | q13_pyFront q14_seat26A | `review/qa/py_r3.json` |
| econ | `src/09a_econ.js` | q15_econFronts q16_econAisle q17_econBacks q18_seat35C | `review/qa/econ_r3.json` |
| ceiling | `src/07b_ceiling.js`, `src/08_bins.js` | q06_roomMain q13_pyFront q15_econFronts q16_econAisle q17_econBacks q01_door1 | `review/qa/ceiling_r2.json` (already fixed once; re-rate first) |
| shell | `src/07_shell.js` (sidewalls, window reveals, shades, dado + grilles, carpets, door linings) | q07_seat11A q14_seat26A q03_suite1A q16_econAisle q12_wing | `review/qa/sidewall_r2.json` (re-rate first) |
| monuments | `src/10_mono.js` (galleys, lavs, door-3 bar, closets, bulkheads + curtains, literature pockets, jump seats) | q01_door1 q11_bar3 q19_rearGalley q13_pyFront | `review/qa/monuments_r2.json` (re-rate first) |
| exterior | `src/11_exterior.js` (wing, raked tip, fairings, GE90-115B nacelle + pylon, livery seen from the cabin) | q12_wing q21_sunset | `review/qa/exterior_r2.json` (re-rate first) |
| lighting + integration | `src/04_shaders.js`, `src/12_scene.js`, `src/13_app.js`, `dist/` | all | the coordinating session keeps this area |

- **Shared files: small local edits only.**
  - `SEATMAT` material values in `src/09_seats.js`, plus `seatEye`/`seatPickBox` for your product.
  - `PHOTO_GAIN`, `PHOTO_ENC` and `LAYER_PARAMS` lines in `src/03_tex.js`.
  - Your entry in `test/make_swatches.py` and `tex/tex_<yours>.png`.
  - `UNITS` in `src/09_seats.js` or `STUDIO_UNITS` in `src/14_studio.js`, only if you need a new studio unit.
  - Mention every shared-file edit in the commit message.
- **Everything else another area owns.**
  - If you find an issue there, add it to `review/qa/from_<your area>.md`, addressed to the owning area, with evidence and a concrete fix.
  - After every pull, read the other workers' `review/qa/from_*.md` files and fix the items addressed to you.
  - Mark each item you fixed with `done (<commit>)` in your own `review/qa/fixed_<area>.md`.

## Setup (once)

```bash
cd cabin777
pip install pillow numpy
python3 test/fetch_refs.py                      # official ANA photos -> ref/ana (reference only, gitignored)
export B=/tmp/b; CABIN_DIST=$B python3 build.py # never build into dist/ and never commit dist/
```

Playwright and Chromium are preinstalled. A 930×575 frame takes about 10–30 s in SwiftShader, so render only your views. For close-ups use `DPR=2` and studio units (`node test/studio.js <out> review/spec_<area>.json`).

## Loop (up to 4 rounds)

Stop early when **both** raters score at least 8.5 with no high-severity issue, or after two rounds without a gain of 0.3 or more.

1. **Render.**
   - Build: `CABIN_DIST=$B python3 build.py`.
   - Render: `CABIN_PAGE=$B/test.html node test/qa.js /tmp/r<N> 930 575 <your views>`. This also writes `pairs.json`, which maps each view to its ANA reference photos.
   - Add studio close-ups of every sub-part you touch.
2. **Rate adversarially with two independent rater subagents** (Agent tool). Skip this in round 1 if your latest rating is `*_r3.json`; start from its issues instead.
   - Rater A is the skeptic: assume every detail is wrong until a real photo shows it right.
   - Rater B uses a different lens: geometry and proportion first, then materials, colour, lighting and artefacts. Artefacts include z-fighting, gaps, floating or intersecting parts, clipping and moiré.
   - Give both raters the render paths, `ref/ana/`, and the scope of your area.
   - Tell them to search the web for **more real in-cabin photos of every detail** and download them to `ref/web/<area>/`. Good sources: trip reports (OMAAT, TPG, Business Traveller, Sam Chui, Paddle Your Own Kanoo, SANspotter, Flyertalk, YouTube thumbnails, Flickr), ANA press kits, and the makers (Safran, JAMCO, Recaro, ZIM, Boeing, GE).
   - Many ANA page images are renderings. When a real photo disagrees with a rendering, the real photo wins.
   - Each rater returns: a 0–10 score per detail and overall; issues with severity, evidence (photo path or URL, sampled hex colours, measured proportions) and a concrete code-level fix; and anything unverifiable, as a question for the user.
   - Save the ratings to `review/qa/<area>_w<N>a.json` and `review/qa/<area>_w<N>b.json`.
3. **Fix.**
   - Fix every high and medium issue backed by evidence, and the cheap low ones.
   - Every value must trace to a source; mark it `[V]` (verified), `[D]` (derived) or `[A]` (approximated) in a short comment.
   - Where a rater is wrong, write down why.
   - Re-render, then look at your renders side by side with the reference photos (Read tool). Iterate until the issues are gone.
4. **Commit and push.**
   - Commit with explicit paths: `git commit -m "cabin777 <area> w<N>: ..." -- <files>`.
   - Then `git pull --rebase origin claude/ana-777-cabin-3d-ts5kra`, then `git push`. Retry on rejection. When resolving a conflict, keep both sides.
   - Rebuild after pulling, because other areas change the scene too.

## Rules

- **Phone-first performance.** Reuse instancing and patterns from your file and keep the triangle delta modest. Report triangles before and after (`__app.scene` meshes). Keep `build.py` fast.
- **Code style.** Match the surrounding code: compact, with the same comment density.
- **Photos.** Never commit or embed photos. Texture patterns may come from photos only as processed tiles in `tex/`, made with `test/make_swatches.py`.
- **Questions for the user.** Append to `review/qa/questions_<area>.md`; never block on them.
- **Finish.** Write `review/qa/<area>_report.md`: scores per round, what changed, sources, open questions. Add `review/qa/<area>_before_after.jpg`, a compact contact sheet of your own renders only (no photos), under 400 KB. Commit and push both.
