# Adversarial visual QA — pass 1 report (renders qa1_*, 24 Sep 2026)

Status of each item: see docs/HANDOFF.md section 6.

Across the 11 frames I found about 70 concrete defects. The biggest problems are the same everywhere: untextured gray-box materials, aircraft in poses that couldn't happen, blank aprons with no stand markings, and a flat, washed-out tone map.

I zoomed and contrast-stretched every frame and measured pixels. I checked the code only to confirm root causes; I changed nothing. Coordinates are (x,y) in pixels from the top-left of the 1280x720 frames.

PER-IMAGE DEFECTS

1. qa1_gate_B12 (Alaska 737-800 at B12)
- A red nav-light glow floats in mid-air at (540,432). That is about 100 px (roughly 2 m) ahead of the left winglet root at ~(645,460), beside the foot of the bridge stair. It is attached to nothing.
- The aircraft is plain white from the cab to the right edge. There are no titles, cheatline, registration, panel lines, door outlines or grime. The engine cowling is white with a blue ring. Nothing reads as Alaska.
- There are no stand markings anywhere in the lower half: no yellow lead-in line, stop bar, red envelope lines or stand number. Contrast-stretching shows only a slab grid and one dirt blotch repeating.
- The gate is sterile: no chocks, ground power or air hose, belt loader, carts, catering, fuel truck or crew. There is one cone at the bottom edge.
- The jet bridge (400-665, 225-390) is untextured gray boxes. The cab meets the fuselage with a flat dark rectangle (655-665, 275-345) and no bellows around the door. The bridge sign (503-517, 288-307) is an unreadable 15-px smudge. "B12" is not legible anywhere.
- The facade glass is a flat, reflectionless dark grid. The two roll-up doors in the white base wall show diagonal moiré at (58-158, 290-357) and (295-367, 283-337).
- Exposure is flat: the darkest 1% of pixels is about 65/255 and the brightest about 222. Shadows are pale blue-gray, and nothing darkens where it touches the ground.
- The neighbouring aircraft's fin (1000-1180, 150-270) is a flat blue slab. The tower (1090-1135, 115-200) is a generic golf-tee shape.

2. qa1_gate_D5_45_1
- The "parked" Southwest 737 is not at a gate.
  - Its axis runs roughly parallel to the terminal, 40-60 m out on open apron.
  - It sits between the signs at (603,210) and (848,205), which appear to read D4 and D6 but are too soft to be sure.
  - No bridge is attached and no D5 sign is visible.
- Even as a colour scheme, the livery is wrong. The top is pastel periwinkle (measured RGB 140,164,203) over a white belly, and the tail is uniform periwinkle with no red or yellow. Real Southwest is dark "Bold Blue" (about #304CB2) over a silver belly, with red and yellow accents.
- The baggage-cart train sits under the right wingtip. The winglet and green nav light appear to grow out of the tug's roof at (882-900, 340-410). Ground equipment inside the wingtip envelope is wrong: at best an ugly visual overlap, at worst an intersection.
- The cart sides are uniform salmon pink under slate lids (715-890, 435-555), which looks like placeholder material. The yellow box at (735-787, 372-390) has no features, and the tug is a tall white box.
- An unidentifiable sloping blue-and-white segmented bar floats in front of the glass, right of the D6 docking-guidance display (875-978, 252-277).
- The gate signs and docking-guidance displays are small and blurry, and their amber text is unreadable.
- The corrugated base wall shows moiré at (770-1025, 285-330). The right bridge's shadow is full of irregular light holes at (990-1130, 343-390).
- The apron has only faint white lane lines: no yellow lead-in lines or stop bars for any of the visible bridges.

3. qa1_gate_B25_55_1_14
- The foreground A321 (bottom-left) sits diagonally beside the docked aircraft, not on any stand. In frame, its right wing crosses the docked aircraft's left wingtip at (650-800, 460-500). With no stand markings, this reads as a wingtip conflict.
- Both nav lights float free:
  - a red dot at (620,467), about 40 px ahead of the docked aircraft's left wingtip at ~(660,470);
  - a green dot at (772,449), off the foreground aircraft's right wingtip at ~(790,470).
- Neither A321neo has sharklets. Both visible wingtips end flat, at (657-672, 465-475) and (772-797, 467-477).
- Both fuselages are plain white with only two door outlines. The tail at the right edge is plain dark blue.
- The retracted bridges at the pier tip are jammed together at (465-700, 215-290), with tunnels and cabs touching or overlapping. They should fan out to separate rest positions.
- The facade gate signs (430-740, 190-240) are illegible.
- Edges are aliased. The foreground wing's leading edge is stair-stepped with a dotted highlight crawling along it. The light mast's shadow breaks into a dotted line at (1035-1230, 362-385).
- A featureless white box sits on the apron at (782-870, 302-340).

4. qa1_gate_F10_60_1_20
- The CRJ-200 (570-775, 262-330) sits at an arbitrary angle on open apron, about 50 m from the building. It is not on a stand, has no stairs, equipment or chocks, and lines up with nothing.
- Its shadow is blocky and stair-stepped because shadow-map resolution is too low at this range.
- The lower ~55% of the frame is empty concrete with an obviously repeating dirt blotch and no markings. None of the four F-gate bridges has a lead-in line; only white service-lane lines exist.
- The bridges are box primitives. The tunnel signs near (150,335) and (370,300) are illegible, and the facade signs (F7/F8/F10?) are fuzzy.
- The hillside at the top-left (0-450, 40-95) is a gray-and-white checkerboard of large blurry squares (the procedural city smeared on the slope). A blank white slab building sits at (120-260, 75-95).

5. qa1_hold_0
- The holding-position marking (315-940, 375-415) renders as one yellow line with a sawtooth, not two solid plus two dashed lines.
- The dashed lines that should run along both sides of the taxiway centerline for the last 150 ft (FAA "enhanced centerline") appear only on the right, from ~(700,440) to (1170,720). The left dashed line is missing or sits on top of the centerline.
- The centerline wobbles beyond the bar (420-660, 300-405), and the left edge line kinks at (390,380).
- Pavement edges smear into wide blurry gradients (left: 250-380, 300-540; right: 900-1280, 290-440). They look like fog rather than a paved edge with shoulders.
- The runway beyond the hold line is an unreadable jagged light strip (250-700, 265-290).
- The hills at the right (650-1280, 170-235) show vertical gray, green and red streaks: texture stretched down the slopes.
- The standing sign (1128-1190, 342-367) is illegible at about 40 m, and its location panel blurs to olive.
- A blank gray box building sits at (903-1007, 222-245).

6. qa1_hold_12
- The hold bar is collapsed into a sawtooth the same way (210-1030, 375-420).
- The same centerline dashes are wrong the other way here. There are two dashed lines on each side of the centerline, five lines in total (700-1170, 440-720); there should be one per side.
- The centerline wobbles beyond the bar (430-650, 300-400). The double edge line has a hard kink at (300,372), while the pavement edge beside it is a soft blur.
- The runway beyond the bar renders as jagged light-gray slivers and staircases (140-640, 270-305).
- The left grass-to-pavement edge is a blur 100-200 px wide (0-250, 300-600).
- A giant untextured white box (0-245, 185-250) has no doors, windows, signage or roof edge.
- A smeared gray-white blotch sits on the distant ground at (245-350, 215-240).

7. qa1_thr_28L
- The runway number shows the "L" (622-653, 360-370) but only one digit-sized blob for "28", right of the centerline (646-670, 345-352). The "2" is missing.
- The displaced threshold has only the centerline arrowhead (620-660, 440-485). FAA/AIM requires a row of arrowheads across the full runway width just before the threshold bar.
- The runway centerline stripes are effectively invisible. Only the in-pavement light dots along x≈640 show.
- The tyre-rubber area in the touchdown zone is a dark smudge with a faint checker texture (610-670, 280-320), not streaks along the wheel tracks.
- The runway and grass edges are haloed and blurred (700-900, 280-450) and stair-stepped in the distance.
- The aircraft's nav lights sit ahead of the wingtips: red at (390,468) against the far tip at ~(366,462), and green at (535,655) against the near tip at ~(490,655). The livery is generic white and blue.
- The aircraft stands about 60° off the runway axis in the displaced area, and no painted line explains that pose.

8. qa1_thr_28R_120_5
- The "2" is missing here too: the "R" is at (627-662, 359-368), then a single blob right of centerline at (648-678, 344-352).
- There is the same single arrowhead (570-715, 510-615) and no row of arrowheads at the bar (y≈490-510).
- No centerline stripes are visible. The rubber smudge is at (610-670, 290-330).
- The yellow taxiway line on the right (1010-1080, 377-443) runs onto the runway, over the white edge stripe, and dead-ends inside the outer threshold stripes.
- The far runway edges are stair-stepped (350-640, 330-380).
- Verified correct, so leave these alone: 16 threshold stripes, green threshold lights, touchdown-zone bars at 500 ft, aiming point at 1,000 ft.

9. qa1_tower
- The tower is a symmetric golf-tee shape.
  - The glass cab is a thin, centred dark band (600-685, 225-242), not the large offset glass cab of the real tower.
  - The flat roof disc (y≈205-212) floats about 15 px above the cab rim, held up only by the mast.
- The terminal roofs are flat off-white planes with a few identical boxes. The whole foreground roof (490-1280, 420-720) is one slab with no seams, parapets, drains, skylights or screened equipment; it reads as plaster.
- On the garage deck (0-420, 380-720) the cars are flat squares and confetti, some of them large bright-red squares. They have no car proportions, no shadows and no consistent rows.
- Distant traffic has three problems:
  - two aircraft overlap at the far pier tip (720-800, 289-340);
  - two sit nose-to-tail with no separation (1107-1192, 277-293);
  - the aircraft at the right edge (1192-1280, 307-337) appears to stand on the tan infield, with its gear shadows on sand.
- The distant airfield is heavily stair-stepped.

10. qa1_look (International Terminal)
- The great hall roof (445-830, 330-380) is a thin, nearly flat pale-blue sheet with a wavy front edge, laid on the lower building's roof. There is no 83-ft glazed hall under it, no wing-shaped profile, no skylight bands and no truss rhythm. It reads as a tarp.
- The garage roofs are white and red dot noise. On the right garage (785-1060, 490-720) the rows of cars curve in S-shapes across a rectangular deck.
- The garage facades are a checkerboard of small window-like holes instead of continuous horizontal openings between concrete bands.
- The right garage and the edge of the pier (800-1280, 440-720) sit in bare tan sand. That area should be roads, ramps and landscaping.
- The central garage roof is uniform speckle. The distant runways are stair-stepped, and a blank white slab sits on the horizon at (290-380, 185-205).

11. qa1_view_overview
- The coastline west of the airport is a pixel staircase (440-610, 450-720), with steps tens of metres long.
- The city is a visibly tiled grid of identical cells. One commercial zone is a blurry field of white rectangles (0-420, 510-720). No buildings have height.
- The hills are smooth tan blobs with flat dark-green paint splotches, for example at (30-120, 240-270).
- The airport itself is a uniform tan slab. The whole view reads as a low-resolution map render, not a flight sim.

TOP 15, RANKED BY DAMAGE TO REALISM

1. Gray-box materials on everything: aircraft, bridges, terminals, roofs and hangar boxes.
   Fix: build full PBR material sets (colour, normal, roughness and ambient-occlusion maps).
   - Aircraft: panel lines, door and exit outlines, antennas, exhaust and grime streaks.
   - Glass: reflection probes or interior mapping, plus mullion depth.
   - Bridges: corrugation normal maps, glazed tunnel sides, a bellows canopy.
   - Roofs: membrane seams, parapets, drains, skylights, screened HVAC.
   - Hangars: doors and signage.

2. Aircraft in impossible poses: the D5 737 parallel to the terminal and off-gate, the F10 CRJ at a random angle, the B25 A321 wing crossing a docked wingtip, and the overlapping and on-sand traffic in the tower view.
   Fix: snap every parked aircraft to its stand pose, with the nose wheel on the stop mark, the heading on the lead-in line and the bridge on the front left door. Check wingtip and tail clearance against neighbours. Clamp ground traffic to the taxiway network and paved areas, with minimum spacing. Hold stale position reports at the last valid stand or taxi pose.

3. Blank aprons.
   Fix: stand markings already exist but are turned off by default (/home/claude/sfo3d/js/live/world.js:56, `opts.standMarkings`). Turn them on, deriving them from each gate's nose position and heading. Add stop marks per aircraft type, painted stand numbers, red wingtip-envelope lines, hatched no-parking boxes, bridge wheel boxes and equipment-restraint lines. Break the repeating dirt tile with world-space variation and oil stains at engine and APU positions.

4. Washed-out tone mapping. In every frame the darkest pixels are about 40/255 or higher and the brightest about 223/255 or lower.
   Fix: switch to ACES or AgX with a proper exposure and white point. Cut the ambient light filling the shadows and reduce near-range haze. Add screen-space ambient occlusion for contact darkening at gear, bridge wheels and building bases.

5. The ground texture smears at shallow viewing angles, which is why pavement edges blur, markings vanish and runways turn into staircases. The airfield texture is baked at 0.8 m per texel (/home/claude/sfo3d/js/world/world.js:92), and anisotropic filtering is `window.ANISO||1`, effectively off (/home/claude/sfo3d/js/world/world.js:74; /home/claude/sfo3d/js/world/textures.js:50 and :122).
   Fix: set 16x anisotropic filtering on all ground textures. Render thin markings (centerlines, hold bars, runway stripes, numbers) as vector decals or distance-field textures instead of baking them at 0.8 m. Give pavement a crisp edge with shoulders.

6. Runway marking errors: the missing "2" on both runways, invisible centerline stripes, no arrowhead row at the displaced threshold, and a taxiway line over the 28R edge stripe.
   Fix: the likely cause of the missing "2" is that runway digits are sampled from a mip-mapped texture and hard-thresholded (/home/claude/sfo3d/js/shaders/ground.js, glyph() and lines 66-73), so thin strokes drop out when shrunk. Use a distance-field glyph atlas with derivative-based smoothing, or vector decals. Add the row of arrowheads across the width before the threshold bar. Stop taxiway centerlines at the runway edge, or draw a proper lead-on line that breaks where it crosses white markings.

7. Liveries. Southwest renders pastel periwinkle (measured 140,164,203). The colours in /home/claude/sfo3d/js/live/lookup.js:40-49 are written as display colours but used as linear values: Southwest's [0.18,0.30,0.64] comes out around (118,149,209). Every fuselage is otherwise blank, and the A321neo has no sharklets.
   Fix: convert the livery table from sRGB to linear. Add the cheatlines, belly colours and tail accents. Add sharklet and winglet geometry per type. If trademarks rule out logos, at least add generic titles and registrations.

8. Floating nav lights in B12, B25 and 28L. Light positions come from a generated wing shape (/home/claude/sfo3d/js/aircraft/model.js:305-308, used by /home/claude/sfo3d/js/aircraft/fleet.js:113-115), but close up the real 3D model is drawn (/home/claude/sfo3d/js/live/aircraft.js:111), so they don't match.
   Fix: take nav and strobe positions from each real model's wingtip vertices, or store light positions per model in the model manifest.

9. Background terrain and city: streaks on slopes, checkerboard blocks, a stair-step coastline and paint-blob vegetation.
   Fix: use triplanar or slope-aware texture mapping. Build the shoreline from vector or distance-field data instead of the low-resolution mask. Near SFO, replace the procedural city with aerial imagery or extruded building footprints, and fade to imagery at range.

10. Hold-short and centerline-dash errors.
    - The four-line hold bar collapsing into a sawtooth is an aliasing and resolution problem; the geometry itself is correct (12-in lines, 12-in gaps, 3-ft dashes).
    - The dashes beside the centerline are one-sided at hold_0 and doubled at hold_12. /home/claude/sfo3d/js/live/markings.js:114-115 draws them as a straight segment along the hold direction instead of offsetting the actual centerline.
    Fix: add temporal or multisample anti-aliasing. Generate the dashes by offsetting the real centerline by ±12 in over the last 150 ft, and remove duplicate hold entries. Smooth centerline and edge-line paths with arcs or splines.

11. Aliasing and shadow artifacts: jagged wing and fuselage edges, blocky mid-range shadows, the dotted mast shadow, the speckled bridge shadow, and moiré on corrugated walls and doors.
    Fix: temporal or 4x multisample anti-aliasing plus highlight anti-aliasing. Use a tighter near shadow cascade with soft filtering. Move corrugation out of the colour texture into mip-mapped normal maps.

12. ATC tower: a thin centred cab, a floating roof disc and a symmetric shaft.
    Fix: remodel to the real profile, with a curved tapered shaft and a large offset cab with sloped glass and an attached roof, at correct 221-ft proportions.

13. International Terminal and garages: a tarp-like roof, no great-hall volume, confetti cars in curved rows, office-window garage facades, and a garage standing in sand.
    Fix: model the 705 x 210 ft glazed hall, up to 83 ft high, under the real wing-shaped roof with skylight bands. Place cars on each deck's own stall grid. Give the garages horizontal concrete-band facades and surround them with roads and landscaping.

14. Ground equipment and turnaround realism: the D5 cart train under a wingtip, pink placeholder carts and a blank yellow box, and no equipment at all at B12.
    Fix: place equipment from stand-relative templates with keep-out zones for wingtips, engines and bridge wheels. Add chocks, cones, power and air hoses on the bridges, and belt loaders at the cargo doors. Use realistic tugs and carts, with curtains or mixed bags.

15. Jet bridges: plain boxes, no bellows, illegible gate signs, and retracted bridges crammed together or overlapping at the B25 pier tip.
    Fix: build a detailed apron-drive bridge with canopy, drive bogie, glazed tunnel and rotunda roof. Make gate numbers large enough to read (about 1 m characters) on the cab, tunnel and facade. Park retracted bridges at separate, non-overlapping rest positions for each gate.

Zoomed crops backing these findings are in /tmp/claude-0/-home-claude/cb34e0fe-afbb-50d6-aace-62df48a9873a/scratchpad/crops/.