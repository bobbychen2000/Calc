# Second house exterior reconstruction — project notes for Claude Code

The same method as `house/` (read `house/CLAUDE.md`: pipeline, coordinates, viewer, packaging) applied to a second
listing: a 2008 two-storey Craftsman (grey cedar shingle, white trim, tapered columns on stone piers, wraparound front
porch, complex hip roofs with 50 solar panels), an attached 3-car garage, ~1 acre of grounds: gated paver driveway,
front lawns with curved flagstone walks, rear flagstone patio, pool + spa, stone outdoor fireplace, BBQ kitchen, vine
arbor, synthetic lawn, play structure in a wood-chip yard, fenced vegetable beds. Owner's brief (2026-11-27): "Construct
<listing> using similar approach to the last one we built".

**Public repo:** the listing photos and anything cut from their pixels live only in the git-ignored
`house2/refs/cache/` and `house2/out/`. Never commit them, and do not write the property's address or the listing URL
into committed files (the folder is called house2 for that reason).

## Sources
- 30 listing photos in `refs/cache/photos/` (2500 px): `p29` near-nadir drone aerial of the whole lot (the plan),
  `p28` high oblique drone view of the rear, `hero` / `p01` the front porch, `p18`-`p27` the rear yard, pool, fireplace,
  play area, garden; the rest are interiors.
- Listing facts: house 4,800 sq ft on two levels + 789 sq ft attached 3-car garage, lot 1.03 acres (44,866 sq ft),
  50-panel solar system, built 2008.
- The property video (Vimeo, 183 s, 4K source) cannot be fetched from this server: Vimeo answers every request from
  it with a Cloudflare human-verification page (the first house's video downloaded before that started). The owner
  supplied its frames every 100 ms instead (a screen recording of the player, 1362 x 766):
  `refs/cache/frames_all/frames/frame_<ms>ms.jpg` + `frame_timing.csv`. Shots used for SfM (`tools/sfm.py SHOTS`,
  ranges clear of the cross-dissolves; masks over the player's bar, icons, the watermark and the title):
  approach 14-16 s, pool top-down 21.5-22.8, front 24-26, front roof 26.5-28.3, play area + pool 123.5-126.5,
  rear 130-138.5 (three moves), top-down 139-141.5, lawn 142-146, rear 153.5-156.5, high orbit 157.5-160.5.

## Commands (run from `house2/`)
As in `house/CLAUDE.md`, with `house2` paths: `python3 -I model/build.py`, `node tools/shot.cjs ...` (dev server:
`python3 -m http.server 8777 --directory .` from `house2/`), `python3 -I tools/crop.py ...`, `python3 web/package.py`.
`python3 -I tools/vggt_run.py refs/cache/vggt/run1.txt refs/cache/vggt/run1.npz` = cameras + points of the 13 exterior
photos (CPU, ~20 min).

## Surveys
`survey/roof.json`, `site.json`, `front.json`, `rear.json`: every element in ORIGINAL image pixels of its photo
(written and then overlay-checked by agents; positions good to a few px).
