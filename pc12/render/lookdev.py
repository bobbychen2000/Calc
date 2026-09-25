"""
render.lookdev -- photo-matched materials of PC-12 PRO MSN 3008 (N81DW) for the Blender renders.

    lookdev.apply(bpy.data.materials)           # after the glTF import (render/beauty.py calls it)
    lookdev.apply(scene_or_materials, overrides={"paint_blue": {"metallic": 0.5}, "_outline": {"width": 0.008}})
    python3 render/lookdev.py --json            # -> render/lookdev_materials.json (glTF / three.js values)
    python3 render/lookdev.py --verify hangar_port34,apron_stbd34 [--size 1200x800] [--samples 24]
            [--glb out/pc12_snapshot.glb] [--out out/tmp/lookdev] [--set KEY=VALUE ...] [--sheet-dir DIR]
        renders the beauty presets with these materials, then a flat material-ID pass of the same camera,
        and writes refs/cache/overlays/lookdev/<preset>_lookdev.jpg (or DIR/..: photo | render with the patches
        and a swatch table) + out/tmp/lookdev/<preset>_patches.json (Lab dE2000 of every patch / region).
        Presets with patches: hangar_port34, apron_stbd34, nose_port_closeup, air_below_left, wing_from_cabin.

apply() rebuilds the node tree of every material whose NAME (a '.001' suffix is ignored) is in SPEC; other
materials (the environment, most of the interior) are left alone.  Given the whole file (None /
bpy.data.materials / a Scene) it first
  * REASSIGN: moves primitives onto render-only materials (cabin-window panes -> glass_cabin, their rings ->
    seal_cabin, the wheel wells -> gear_bay; the GLB shares 'glass' / 'seal' / 'zinc_chromate' with parts
    that must look different);
  * OUTLINE: lays an 8 mm paint_champagne ribbon along every colour boundary of the white pinstripes (the
    MSN 3008 strokes are edged in silver-champagne; the livery has no such strokes yet);
  * ENV: wraps beauty.build_env (render/hooks.py allows lookdev to patch render.beauty; beauty.py is not
    edited), keyed by preset: the hangar OSB ceiling colour, a neutral ceiling zone the camera never sees and
    thinner LED strips (hangar), cabin / cockpit lights, the air preset's terrain albedo, and studio flags (the
    hero's key light-linked off the tyres, blades and seats); for the OUTDOOR ground presets (apron_stbd34,
    nose_port_closeup) render/airfield.py replaces beauty's race-track HDRI + shadow catcher with a photo-matched
    airfield (sky HDRI with a capped sun + a sun lamp at the photo's measured sun direction, procedural apron with
    markings, hangars / tower / trees / mountains; ENV['outdoor'], --set airfield=false for beauty's own).
It returns {name: kind} of what it rebuilt plus '_reassigned' / '_outline' / '_env' summaries.

Shading models (Principled BSDF, Cycles, multiscatter GGX):
  metallic paint   pigment + aluminium-flake base under a clear coat.  Base colour measured (below), Metallic
                   0.40 for the blue (round 3; 0.75-0.8 before) with a BROAD flake lobe, roughness 0.50: the
                   flakes mirror the environment tinted by the pigment over a wide cone, so panels away from the
                   specular direction keep a luminous 'face' instead of mirroring the dark ground / horizon as navy
                   (photos 188 / N81DW); the light blue is a narrower silver-blue lobe (metallic 0.70, roughness
                   0.37, round 4: the broad lobe made it a pastel periwinkle outdoors); Specular Tint = base colour
                   (the F82 tint: the flakes sit INSIDE the lacquer, so their reflection never goes white at
                   grazing -- the chrome look of the old setup; 'spec_tint' blends it toward white, unused),
                   dielectric Specular IOR Level 0.1 (base / lacquer interface).  Flake: per-cell random normals (Voronoi, 0.4 mm cells, object space, +-0.06) tilt
                   the BASE normal only and fade out between 1 and 4 m ray length (beyond that a pixel covers
                   thousands of flakes: their aggregate IS the base roughness, random normals only add noise);
                   a 17 cm roughness mottle +-0.03.  Coat: weight 1, roughness 0.03, IOR 1.5, smooth geometric
                   normal -> the crisp white reflections and the Fresnel rise to grazing.
  solid gloss      whites / pinstripes, radome black, painted gear: Metallic 0, base roughness 0.3, Specular IOR
                   Level 0.1, coat 1 / 0.03 / 1.5.
  PRO mask         trim_black (and the 'seal' frame strips / windshield post): anti-glare black, base 0.010,
                   roughness 0.5, Specular IOR Level 0.08 (a low-reflectance textured finish).  Photos 82 / 188:
                   no crisp reflections on it (the blue paint next to it mirrors the LED strips), a soft sheen.
  lining           BACK faces of every paint material, and of trim_black / seal, render as a satin light-grey
                   interior lining (LINING 0.55 in the cabin, 0.30 on the flight deck, x < 5.0 m: outdoors the
                   windshield and side windows are dark panes, photo 188): the skins are single-sided and
                   outward-wound, and the flight deck
                   has no side-wall / headliner, so through the glazing camera rays hit the skins from behind.
                   Round 1 left the mask's back faces black: the whole upper cockpit wall round the panes was
                   black from inside -- the main reason the flight deck read near-black through clear glass.
  thin glass       N-surface Fresnel mirror (R = N F / (1 + (N-1) F), IOR 1.5, GGX roughness 0.004) mixed with a
                   tinted Transparent BSDF (no refraction): windshield / flight-deck side windows one pane (N = 2,
                   7.7 % at normal incidence, neutral T .87/.87/.86 and .82 (round 4; greenish before), cabin
                   windows two-ply acrylic (T .82,
                   glass_cabin, N = 4, 14.3 %: the bright silver panes of photos 130 / 0517).  Shadow rays pass
                   the tint, so the interior is lit.
  cabin rings      seal_cabin: glossy dark grey (0.05, roughness 0.12, Specular 0.5) -- the NGX panes are flush
                   with a thin, barely darker edge, not a black ring.
  satin / rubber   blades satin black composite (0.015, roughness 0.45, Specular 0.25), de-ice boots glossy
                   black neoprene (0.012, 0.25, Specular 0.5: one crisp highlight), tyres black rubber (0.028,
                   roughness 0.45, Specular 0.5 = F0 4 %: the satin sheen of photo 130) with 4 circumferential
                   tread grooves (6 mm, at +-0.1 / +-0.3 of a tread 0.62 x the tyre width; a bump in the tyre's own
                   frame, object properties written by apply(): _tyre_frames) whose rounded shoulders carry the
                   rib highlights; red blade band 0.27/0.026/0.004, roughness 0.40, Specular 0.2.
  metals           polished spinner (F0 0.90, roughness 0.035), exhaust stacks: stainless F0 .50/.42/.30 with a
                   straw / bronze heat tint along the whole tube (from the root, STA 1.45) and a streaky polish noise
                   (roughness 0.06-0.16, up to 30 % tint, bump 0.35) ending in a jet-black outlet collar (station
                   x > 1.765 m: base 0.004, dielectric, roughness 0.85, Specular IOR Level 0.08 = F0 ~0.6 %: with
                   the default 0.5 the white hangar alone lifted it to a grey ~70; world x == model station in the
                   renders), soot-black back faces and inner wall / rim (exhaust_soot 0.006, roughness 0.60,
                   Specular 0.08), erosion sheaths (nickel, 0.22).
  interior         leather -> light grey 0.45, crew seats (leather_dark) 0.30; jambs tan / khaki; door seams dark.
  outline          paint_champagne (0.49/0.41/0.30, metallic 0.45, roughness 0.36, coat): 8 mm ribbons centred on
                   the stripe boundaries, 0.3 mm above the skin, parented to the source primitive (they follow the
                   pose), render visibility copied from it (camera-invisible fuselage in wing_from_cabin).

-------------------------------------------------------------------------------------------------------------
Measurements (photos in refs/cache/photos, git-ignored; boxes (x0, y0, x1, y1) in photo pixels; values are the
mean of the sRGB-decoded LINEAR pixels, i.e. the JPEG treated as sRGB -- press JPEGs carry a tone curve, so these
are estimates, cross-checked between three differently lit photos and normalised with in-photo references):

 A. hangar, MSN-3008_130 (1920x1280, white delivery hangar: white walls / epoxy floor = a near-uniform white
    'furnace', so a patch ~ its total reflectance x the room radiance).  References: white walls
    (50,300,250,500) lin .86, floor (1000,1100,1400,1200) .94 (sRGB 248, near clip), fuselage white band
    (720,660,900,680) .87/.88/.90 (white paint ~.85):
      blue fuselage side (700,590,760,625)  sRGB  73/105/166  lin .067/.140/.381
                         (870,548,925,570)  sRGB  72/ 98/157  lin .065/.124/.338
                         (980,560,1060,600) sRGB  82/103/154  lin .085/.136/.324
        -> total reflectance ~ .066/.130/.350 = base + the clear coat's mirror of the white room (~.05-.06)
      light-blue lower nose (700,700,800,730) sRGB 158/180/209 lin .352/.468/.645 (faces the brighter floor)
      PRO mask under the side window (1060,487,1120,497) sRGB 72/67/62 lin .077/.067/.060
      blade, upper (352,285,375,335) sRGB 63/62/62 lin .050 (satin black + white-room sheen)
      red band (355,80,390,88) sRGB 189/73/46 lin .49/.10/.05 (red pixels only: 189/74/46)
      exhaust (round 4): outlet collar (742,495,762,525) sRGB 16/17/21 mean, 13/15/18 median (jet black);
        stack body (620,495,720,522) 188/175/156 (warm straw-grey stainless, streaky reflections)
      nose tyre (round 4): sidewall (822,935,832,960) 60/61/59 (median 57), tread ribs (750,925,772,955)
        68/75/81 with 4 circumferential grooves (5 satin ribs)
      OSB ceiling, medians: (600,30,900,150) lin .57/.36/.11, mid .44/.29/.12, right .76/.55/.24
      stripe profiles (x = 760 .. 1170): the dark saturated band seen under the thin white line (x = 1050:
        sRGB 4/47/105 between the lines, 84/104/152 above) is absent at x = 1120 / 1170 and lies ABOVE the thin
        line at x = 950 -- a reflection horizon, not paint: the livery's navy line N1 is the base blue
    MSN-3008_82 (hangar close-up): mask below the side window (480,300,600,315) lin .035/.031/.026 (dark
      brown-black: a soft reflection of the OSB ceiling, no crisp LED lines), side window (580,150,640,190)
      sRGB 85/80/75, seat through it sRGB 83/81/81 (neutral grey), blue (100,200,200,230) lin .070/.183/.580;
      stripe edge profile x = 350: blue 76/92/134 | outline 191/185/182 (6-9 px ~ 8 mm: B1 is 84 px for its
      88 mm) | white 227/227/229 (round 4 re-measure: plateaus 189/184/182, 176/176/172, P2 158/155/151 ->
      outline / white .44-.66 linear, R/B 1.05-1.08; 188 x = 600: 172/165/156 beside 240, R/B 1.2-1.25) --
      every white stroke is edged in silver-champagne; door jamb (inside the doorway) sRGB 84/78/60 khaki
 B. apron, CL_IMG_0517 (1733x1300, iPhone, clear sky.  The starboard flank and the hangar door facing the
    camera are in SHADE, the sun is on the far (port) side: the aircraft's shadow falls toward the camera):
      white hangar door, same shade (700,420,900,480)   sRGB 127/152/177  lin .212/.315/.442
      blue under the cockpit (1000,690,1060,715)       sRGB   3/ 43/ 92  lin .001/.025/.109
      blue nose side (1110,670,1200,700)               sRGB   0/ 37/100  lin .000/.018/.129
        -> blue / door x 0.8 = .003/.063/.197 (the phone's saturation boost clips red to 0): a deep, saturated
           blue in shade -- the 'deep dark metallic blue' is the flake lobe mirroring dark surroundings
      sunlit tarmac (700,1100,1000,1200) lin .336; side window (1000,620,1040,640) lin .023/.042/.071 (a lit
      grey cockpit through the pane); mask below the side window (1005,646,1070,652) lin .037/.064/.103
 C. nose close-up, MSN-3008_188 (1950x1300, sun from starboard, the port side in shade lit by sky and the bright
    concrete apron):  white band (300,690,450,705) median sRGB 237/236/235 lin .84
      blue side (680,420,760,470) sRGB 16/67/156 lin .006/.057/.331 -> /white x .85 = .006/.057/.335
      mask below / aft of the side window (820,387,900,398) / (925,330,940,390): near black, soft sky sheen
      door jamb (984,430,998,600) sRGB 182/154/103 (tan / khaki with yellow speckles, sunlit), black seal
      groove and a light aluminium lip beside it; de-ice boot (1500,668,1700,684) sRGB 32/36/44, wing lower
      surface (1500,700,1700,712) 27/27/26 (neutral: the clear coat mirrors the grey asphalt)
      exhaust: polished with a bronze tint, the outlet end black (also photo 130: ~15 % of the visible stack)
 D. air-to-air N81DW (1924x1300): wing lower surface (1450,450,1550,520) sRGB 10/13/21 median (navy, C 13 at
    L 11), (700,880,850,930) 16/27/36; IMG_0459 (qualitative): wing upper = the blue (dark where it mirrors
    dark ground), de-ice boot (1900,850,1950,900) lin .028/.034/.038 in golden light, radar radome gloss black
    lin .009, tailplane silver-grey metallic.
 Base colours were then fitted through the renderer (AgX + the presets' grades) to the photo patches: the
 hangar furnace is metallic-independent and pins the albedo; the shade photos (B, C) fix the flop (metallic
 0.8).  Round 2 (judge round 1): blue re-hued to 292 deg / C 49 (188 is a vivid ultramarine; green was ~30 %
 high against the white in both the hangar and 188), light blue .25/.35/.56, whites .90/.905/.91.

Verification (python3 render/lookdev.py --verify ..., 1200x800, 24 spp (air / wing 16), out/pc12_snapshot.glb;
Lab dE2000 of the mean colour, photo vs render, same pixels; 'region' = the material's pixels in a flat material-
ID pass of the same camera, eroded against the camera misfit; white-normalised in brackets.  r1 = round 1,
r2 = round 2, r3 = this file (judge round 2 applied); nose with --set exposure=1.5, apron with --set sun_az=-100
(the photo's sun is on the port side), as the judges ran them):
                                          r1          r2          r3
  hangar_port34  paint_blue region      2.7 (4.9)   2.7 (4.1)   4.0 (5.5)   the up-facing blue now mirrors the neutral
                 blue side A / B / C     -        4.4/3.6/4.7 3.4/3.7/4.1  ceiling zone, not golden OSB (photo 130)
                 light blue nose patch   -          3.1         1.2         region 4.0 -> 3.5
                 white band patch       2.6         2.4 (0.6)   1.9 (0.6)
                 mask patch             4.4         5.4         3.7
                 side-window glass      9.3         9.4         5.3
                 windshield glass        -         10.5         3.0         158/140/114 (golden) -> 134/133/127
                 chrome region           -          3.7         1.6         (photo 142/139/135)
                 tyre region             -         13.7         6.1         43/45/45 -> 66/70/70 (photo 83/86/89)
                 de-ice boot patch       -          5.1         3.5
  nose_port_closeup  paint_blue region  3.4 (4.1)   3.2 (2.6)   2.3 (3.6)
                 blue side / cowl side   -       11.2 / 16.5  8.3 / 13.4  the cowl side mirrors the race-track ground
                 windshield glass        -         11.4         8.5         79/107/130 -> 60/94/120 (photo 66/79/106)
  apron_stbd34   side-window patch     21.6         5.5         5.7         lighting-limited: the shaded flank mirrors
                 blue nose side patch    -          8.1         5.3         the HDRI's dark camera-side hemisphere
                 paint_blue region      3.6         3.9         2.5
                 light blue region       -          4.9         6.2         lower surfaces mirror the bright sand
  air_below_left paint_blue region       -          8.6         7.0         sky patch 3.7: the render sky is darker
                 wing lower patches      -       3.5 / 3.8    2.7 / 4.0
                 paint_wing_dark region  -          9.9         3.8         cooler terrain (ENV terrain)
                 light blue region       -          5.8         6.6
  wing_from_cabin wing upper patch       -         12.6        11.3         de-ice boot A 5.5, radome 4.3
  hero (no photo) region means, sRGB: tyre / blade / side window 116 / 149 / 136 (r2) -> 43 / 13 / 38 (the key
                 flagged off tyres, blades and seats; interior lights 0.5), paint_blue 4/57/120 -> 41/95/172
 Round 4 (judge round 3 applied; same presets and settings; r3 -> r4, sRGB):
  hangar_port34  exhaust_polished region 9.7 -> 5.7 (197/183/162 vs 175/164/147, the region includes misfit blue;
                 stack-body pixels 195/182/164 vs the photo body box 188/175/156); outlet collar zone median 79/84/84
                 -> 25/28/29 (photo 16/17/21); light blue region 3.5 -> 1.3 (nose patch 1.2 -> 3.4, 147/171/203 vs
                 161/183/211); tyre body p50 72 -> 59 (photo sidewall 57-60; the region dE 6.1 -> 10.2 by design, its
                 photo mean holds rib highlights and hub / floor pixels); red band (ID mask) 201/96/79 -> 196/84/59
                 (photo 189/74/46); side-window glass 5.3 -> 5.0 (hue 120 -> 110), windshield 3.0 (reflection-bound);
                 paint_blue region 4.0 -> 3.9; outline pixels 202/205/205 -> 201/201/196 (a 1-px warm step, as in 130)
  nose_port_closeup  collar median 25/36/47 -> 2/4/6; outline core 176/176/172 -> 172/167/157 (photo plateau
                 172/165/156); light-blue region 20.9 -> 19.1 (C 20.7 -> 20.2: the region is the lower fuselage, which
                 in the photo mirrors dark shaded asphalt and the yellow line and in the render the bright race-track
                 ground -- environment, not paint; the hangar furnace confirms the blue albedo); exhaust region
                 21.4 -> 14.8
  apron_stbd34   light blue region 6.2 -> 4.2; the rest unchanged
  air_below_left paint_silver region 10.2 -> 6.1 (46/61/80 -> 54/58/70, photo 58/58/59); light blue 6.6 -> 4.1;
                 pinstripe 4.5 -> 3.0; wing lower patches 2.7 / 4.0 -> 2.5 / 3.6 (white-norm 1.6 / 1.6);
                 paint_wing_dark region 3.8 -> 4.9 (17/20/27 vs 24/33/44: with the neutral terrain the underside's
                 level is lighting-bound -- the navy base moves it only ~0.04 per unit); paint_white 9.6 -> 8.9
  hero           tyre p50 38 -> 44 (rib highlights: p90 67 -> 104), region 43/44/47 -> 59/61/64
 Regions that disagree for reasons outside the materials (camera misfit or environment): prop_blade regions
 (prop clocking), the nose close-up's tyre / boot / exhaust / light-blue regions and white-band patch (misfit:
 coverage 0.14), the red-band patch (58 % coverage: the blade is clocked differently; a crop reads right), the
 hangar ceiling patch (its box holds an LED strip; the OSB medians match), wing_dark / silver on the ground shots
 (thin, misregistered), the wing_from_cabin paint_blue region (misfit: mostly sky / terrain in the photo).
 Round 5 (ENVIRONMENT, render/airfield.py; materials unchanged).  Before = r4 as the judges ran it (race-track HDRI
 zwartkops_straight_afternoon + shadow catcher; nose --set exposure=1.5, apron --set sun_az=-100); after = the
 presets' own settings (no --set).  Same GLB / size / spp; the (env) patches are new in round 5:
  apron_stbd34   paint_blue region 2.5 -> 0.5, blue nose side 5.3 -> 2.0, blue under cockpit 6.4 -> 1.6, mask below
                 side window 9.1 -> 1.7, side window 5.9 -> 2.1, glass 13.6 -> 6.0, glass_cabin 8.2 -> 5.4, windshield
                 11.6 -> 8.1, pinstripe 16.4 -> 8.3, paint_white 7.8 -> 4.0, chrome 3.1 -> 1.9, de-ice boot 7.3 -> 5.4,
                 wing_dark 17.5 -> 13.2, light blue 4.2 -> 5.0; env: sky 17.5 -> 1.7, sunlit tarmac 8.6 -> 4.0, gravel
                 5.0 -> 3.0, tarmac shade 1.8 -> 5.0, hangar door 5.6 -> 7.7 (before: the race-track sky filled the box)
  nose_port_closeup  the photo's sun is AHEAD-PORT (the port side facing the camera is sunlit; beauty had it
                 starboard / in shade): blue cowl side 13.4 -> 2.4, blue side 8.3 -> 3.8, light blue region 19.1 -> 11.8,
                 pinstripe region 8.3 -> 5.9, mask below side window 11.5 -> 7.4, nose tyre patch (new) 7.1 -> 2.8, tyre
                 region 31.5 -> 19.1, de-ice boot 33.7 -> 20.9, windshield 8.3 -> 7.9, exhaust 14.8 -> 14.2, paint_blue
                 region 2.3 -> 2.9 (a little too saturated in direct sun); env: sunlit tarmac 61.6 -> 4.0, tarmac shade
                 29.5 -> 4.0, sky 11.9 -> 4.6, mountains 7.6 -> 4.5.  The white-band patch (30) and the tyre / boot
                 regions stay misfit-bound (camera nose_188, rms 36 px, coverage 0.12 on the band).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / "refs" / "cache"
PHOTO_DIR = CACHE / "photos"
LOOKDEV_DIR = CACHE / "overlays" / "lookdev"          # photo-derived images stay in the git-ignored cache
JSON_OUT = HERE / "lookdev_materials.json"
BLENDER_PY = os.environ.get("BLENDER_PYTHON", "/opt/venv-blender/bin/python")

# =============================================================================================================
# material spec (linear base colours).  kind: metal_paint | solid_paint | glass | dielectric | metal
# gltf: overrides for the glTF / three.js table (no F82 tint there: a lower metallic keeps the metallic paint
#       from going chrome at grazing)
# lining: True renders the BACK faces as the interior lining (LINING) -- default for the paints, opt-in otherwise
# Materials marked (render-only) are not in the GLB: apply() creates them and moves primitives onto them
# (REASSIGN) or builds geometry for them (OUTLINE); model/assemble.py can adopt them (see the JSON '_model').
# =============================================================================================================
COAT = dict(coat=1.0, coat_rough=0.03, coat_ior=1.5)
SPEC = {
    # ---- metallic paints (flake base under a clear coat)
    # round 2: hue 292 / chroma 49 (was 286 / 43): photo 188 is a vivid ultramarine (a* +16..+20) and the render's
    # green was ~30 % high against the white in both the hangar and 188 (blue / white per channel).
    # round 3: a BROADER flake lobe (metallic 0.80 -> 0.40, roughness 0.32 -> 0.50, base -5 %): with metallic 0.8 /
    # alpha ~0.1 the lobe was only ~+-15 deg wide, so every panel away from the specular direction mirrored the dark
    # ground / horizon and collapsed to navy (188 cowl side 0/35/88 vs photo 2/78/176; air 20/51/100 vs 44/78/122),
    # while the real paint stays a luminous ultramarine off-specular (a wide azure 'face' glow in the air photo).
    # The hangar furnace (metallic-independent) still pins the albedo; the coat keeps the LED lines crisp.
    "paint_blue":       dict(kind="metal_paint", base=(0.0066, 0.034, 0.205), metallic=0.40, rough=0.50,
                             gltf=dict(metallic=0.30, rough=0.50),
                             note="deep metallic blue: fuselage, fin, cowl, wing upper surfaces, pod body"),
    # round 3: a little more chroma (+B, hangar nose patch was ~13 % low in blue) and the same broader lobe as the blue
    # round 4: the broad lobe was wrong for the LIGHT blue: outdoors it read as a diffuse pastel periwinkle (188 lower
    # nose render 113/135/170 C 21 against a neutral silver 103/109/102 mirroring the concrete; region L +4 hangar,
    # +7 apron, +6 air).  Base -8 % and a narrower silver-blue metallic lobe (0.55 / 0.45 -> 0.70 / 0.37): the hangar
    # furnace pins the albedo whatever the metallic, outdoors the paint mirrors its surroundings nearly neutrally.
    "paint_blue_light": dict(kind="metal_paint", base=(0.215, 0.305, 0.55), metallic=0.70, rough=0.37,
                             gltf=dict(metallic=0.50, rough=0.38),
                             note="light metallic blue (silver-blue): lower nose / cowl, swoosh band, nose-gear doors"),
    # paint_navy: set equal to paint_blue below (the livery's N1 'navy line' is not on the aircraft)
    # round 4: the navy moved from the air preset's terrain into the paint (0.008/0.016/0.056 -> 0.009/0.018/0.070):
    # with the neutral terrain (ENV) the underside went grey (air region 17/20/25 against the photo's 24/33/44)
    "paint_wing_dark":  dict(kind="metal_paint", base=(0.009, 0.018, 0.070), metallic=0.45, rough=0.40,
                             gltf=dict(metallic=0.35, rough=0.42),
                             note="dark navy metallic: wing / winglet lower surfaces, belly fairing (air-to-air "
                                  "N81DW: navy, C/L ~1.2 in shade; 188: neutral where it mirrors the asphalt)"),
    # round 4: neutral (was B/R 1.15): the air photo's tailplane underside is a neutral grey 58/58/59 (render 46/61/80)
    "paint_silver":     dict(kind="metal_paint", base=(0.42, 0.42, 0.43), metallic=0.60, rough=0.34,
                             gltf=dict(metallic=0.55, rough=0.36), note="silver-grey metallic: tailplane"),
    # round 4: warmer, darker and less mirror-like (was 0.50/0.46/0.40, metallic 0.70, roughness 0.30): the old outline
    # mirrored the white room / sky (hangar 204/207/206, nose 160/164/168: cool, washed into the white).  Photo edge
    # profiles (plateaus, linear outline / adjacent white): 82 (hangar) .66 / .58 / .44 with R/B 1.05-1.08, 188 (sky
    # shade) .40-.47 with R/B 1.2-1.25 (the champagne keeps its warmth where the white goes neutral).  Target ~.5 and
    # R/B ~1.3-1.4 in the furnace: base lum .42 + ~.05 coat over the white's .95.  (Judge r3 proposed .40/.33/.22 --
    # ratio ~.41, R/B ~1.7: a gold line darker and yellower than either photo.)  Width 6 -> 8 mm (82: 7-9 px at
    # ~1 px / mm, B1 = 84 px for its 88 mm).  Checked on the 188 render: .50/.43/.34 gave an outline core of sRGB
    # 172/170/163 (R/B 1.13) against the photo plateau 172/165/156 (R/B 1.24) -> a little warmer, .49/.41/.30.
    "paint_champagne":  dict(kind="metal_paint", base=(0.49, 0.41, 0.30), metallic=0.45, rough=0.36,
                             flake_strength=0.03, gltf=dict(metallic=0.40, rough=0.38),
                             note="(render-only) ~8 mm champagne outline of every white pinstripe / swoosh "
                                  "(photo 82: sRGB 189/184/182 and 176/176/172 beside the white's 222-227; "
                                  "188: 172/165/156 beside 240)"),
    "paint_stripe":     dict(kind="metal_paint", base=(0.60, 0.50, 0.16), metallic=0.5, rough=0.35,
                             note="(unused by the MSN 3008 livery)"),
    # ---- solid gloss paints
    "paint_white":      dict(kind="solid_paint", base=(0.90, 0.905, 0.91), rough=0.30, note="gloss white"),
    "paint_pinstripe":  dict(kind="solid_paint", base=(0.90, 0.905, 0.91), rough=0.30,
                             note="white pinstripes and swooshes"),
    "paint_belly":      dict(kind="solid_paint", base=(0.62, 0.65, 0.67), rough=0.32, note="(unused)"),
    "paint_accent":     dict(kind="solid_paint", base=(0.08, 0.14, 0.24), rough=0.30, note="(unused)"),
    "paint_black":      dict(kind="solid_paint", base=(0.012, 0.013, 0.015), rough=0.30, spec=0.0,
                             note="gloss black radar-pod radome"),
    "trim_black":       dict(kind="dielectric", base=(0.010, 0.010, 0.012), rough=0.50, spec=0.08, lining=True,
                             note="PRO cockpit mask: anti-glare black round the glazing (photo 82: no crisp "
                                  "LED-strip reflections on it while the blue paint beside it mirrors them); back "
                                  "faces = cockpit lining (the mask skin is what the crew sees round the panes)"),
    "seal":             dict(kind="dielectric", base=(0.010, 0.010, 0.012), rough=0.50, spec=0.08, lining=True,
                             note="flight-deck glazing frame strips / windshield centre post (black like the mask, "
                                  "photos 130 / 82)"),
    "seal_cabin":       dict(kind="dielectric", base=(0.05, 0.055, 0.06), rough=0.12, spec=0.5,
                             note="(render-only) cabin-window / cargo-door / exit-hatch window rings: NGX panes are "
                                  "flush with only a thin, barely darker edge (photos 130, 0517) -- a glossy dark "
                                  "grey that mirrors the room like the pane instead of a black ring"),
    # ---- glazing (thin panes).  surfaces: reflecting surfaces, R = N F / (1 + (N - 1) F) (incoherent, no
    #      absorption between them): 2 = one pane (7.7 % at normal incidence), 4 = double pane (14.3 %)
    # round 4: neutral tints (G > R in all three shots before: hangar windshield hue 103 vs 82's 134/133/127 ->
    # 142/139/135, side window 132/133/129 vs 124/121/119, 188 windshield green +15)
    "glass_windshield": dict(kind="glass", tint=(0.87, 0.87, 0.86), ior=1.5, rough=0.004, surfaces=2,
                             gltf=dict(base=(0.02, 0.02, 0.02), alpha=0.30),
                             note="heated laminated windshield (neutral grey)"),
    "glass":            dict(kind="glass", tint=(0.82, 0.82, 0.82), ior=1.5, rough=0.004, surfaces=2,
                             gltf=dict(base=(0.02, 0.02, 0.02), alpha=0.35),
                             note="flight-deck side windows (stretched acrylic, light grey tint)"),
    "glass_cabin":      dict(kind="glass", tint=(0.82, 0.82, 0.82), ior=1.5, rough=0.004, surfaces=4,
                             gltf=dict(base=(0.03, 0.035, 0.04), alpha=0.45),
                             note="(render-only) cabin / cargo-door / exit windows: two-ply stretched acrylic, "
                                  "4 surfaces -> 14 % at normal incidence (the bright silver panes of photo 130)"),
    "lens":             dict(kind="glass", tint=(0.88, 0.89, 0.90), ior=1.5, rough=0.01,
                             gltf=dict(base=(0.85, 0.87, 0.9), alpha=0.15),
                             note="clear polycarbonate light lens"),
    # ---- propeller
    "prop_blade":       dict(kind="dielectric", base=(0.015, 0.015, 0.017), rough=0.45, spec=0.25,
                             note="satin black composite blade"),
    "prop_tip":         dict(kind="dielectric", base=(0.80, 0.80, 0.78), rough=0.36, spec=0.5,
                             note="white blade tip"),
    # round 4: less white-room sheen (spec 0.3 -> 0.2, roughness 0.36 -> 0.40) and a touch more yellow: hangar region
    # 203/91/68 (pink, L +5, C -7.6) against photo 189/73/46
    "prop_band_red":    dict(kind="dielectric", base=(0.27, 0.026, 0.004), rough=0.40, spec=0.2,
                             note="red blade band (hangar photo 189/73/46: a deep signal red, no pink sheen)"),
    "erosion":          dict(kind="metal", base=(0.66, 0.64, 0.60), rough=0.22, note="nickel erosion sheath"),
    # ---- rubber
    # round 3: rubber is an ordinary dielectric (F0 ~4 %, Specular 0.5; 0.25 gave ~2 %): hangar photo 130 shows a
    # charcoal tyre with a clear satin sheen (region 83/86/89), the render's was dead black (43/45/45)
    # round 4: darker and a little glossier (0.05 / 0.60 -> 0.028 / 0.45): the round-3 fit to the photo REGION mean
    # (83/86/89) chased rib-top highlights and hub / floor pixels pulled in by the camera misfit; photo 130's nose tyre
    # sidewall measures sRGB 56-60, tread ribs 67-81 (render r3 body p50 71).  grooves: 4 circumferential tread
    # grooves on the crown (photo 130: 5 satin ribs on the nose tyre) as a bump, in the tyre's own frame (apply()
    # stores it on every tyre object: _tyre_frames); 'tread' = the tread width as a fraction of the tyre width.
    "tire":             dict(kind="dielectric", base=(0.028, 0.028, 0.029), rough=0.45, spec=0.5,
                             grooves=dict(n=4, width=0.006, tread=0.62, depth=0.0025, floor_w=0.002, shoulder=0.003,
                                          floor=0.25, floor_rough=0.7),
                             note="tyre rubber: black, satin sheen, 4 circumferential tread grooves"),
    "deice_boot":       dict(kind="dielectric", base=(0.012, 0.012, 0.014), rough=0.25, spec=0.5,
                             note="pneumatic de-ice boots: near-black glossy neoprene with one crisp highlight "
                                  "(photo 188 sRGB 32/36/44 in shade; 130: bright room reflections)"),
    "black":            dict(kind="dielectric", base=(0.028, 0.028, 0.032), rough=0.50, spec=0.5,
                             note="satin black parts"),
    "inlet_dark":       dict(kind="dielectric", base=(0.018, 0.018, 0.022), rough=0.85, spec=0.3,
                             note="engine inlet / duct interior"),
    # ---- metals and painted gear
    "chrome":           dict(kind="metal", base=(0.90, 0.91, 0.92), rough=0.035,
                             note="polished spinner, oleo chrome, pitot"),
    # collar: the outlet end of the stacks is black (photos 130 / 188: a crisp dark band on the last ~15 % of the
    # stack), with a straw / bronze heat tint ahead of it; MODEL station x (world == model in the renders).
    # round 3: the band is JET black with a sharp edge (photo 130), not a dark-grey rounded metal cap: collar base
    # 0.025 -> 0.015, metallic 0.3 -> 0, roughness 0.45 -> 0.55; the polished tube a little sharper (0.10 -> 0.06).
    # The GLB's own black parts of the stacks (outlet collar band, inner wall, scarf rim: 'black') go to exhaust_soot.
    # The polished tube is an open, single-sided surface: its BACK faces (seen through the scarfed opening) render
    # soot black (back), not polished metal.
    # round 4: the collar read dark GREY (hangar ~70-100 against photo 130's 16/17/21 mean, 13/15/18 median): its
    # Specular IOR Level stayed 0.5 (F0 4 %), which alone mirrors the white hangar at ~70 -- base / roughness / metallic
    # barely moved it.  The collar now blends 'spec' too (0.08: F0 ~0.6 %, soot / porous oxide), base 0.004, roughness
    # 0.85; the back faces and exhaust_soot the same.  Tube: an even ivory mirror before (hangar 203/198/187 against
    # 175/164/147; photo 130 body box 188/175/156): base 0.66/0.58/0.46 -> 0.50/0.42/0.30 (above any real steel's F0
    # ~0.55 before), the straw / bronze heat tint along the WHOLE tube (tint_x0 1.66 -> 1.45, the stack root is at
    # STA 1.43), and 'polish': a streaky noise (world space, 28 /m, stretched 1:0.3 along the stack) that drives the
    # roughness between 0.06 and 0.16, pulls the colour up to 30 % toward the tint, and a bump (0.35 / 1 cm) for the
    # hand-polished waviness of photos 130 / 81 (the judge's 0.1 / 20 /m left the stack a smooth mirror at 1200 px;
    # 0.35 gives the streaky, wavy reflections without changing the colour: hangar body 192/179/161, photo 188/175/156).
    "exhaust_polished": dict(kind="metal", base=(0.50, 0.42, 0.30), rough=0.06,
                             collar=dict(x0=1.765, blend=0.006, tint_x0=1.45, tint=(0.52, 0.36, 0.20),
                                         base=(0.004, 0.004, 0.004), rough=0.85, metallic=0.0, spec=0.08),
                             polish=dict(scale=28.0, stretch=(0.30, 1.0, 1.0), detail=3.0, rough=(0.06, 0.16),
                                         tint_mix=0.30, bump=0.35, bump_distance=0.01),
                             back=dict(base=(0.006, 0.006, 0.006), rough=0.85, spec=0.08),
                             note="polished exhaust stacks (heat tint) with a heat-blackened outlet collar"),
    "exhaust_soot":     dict(kind="dielectric", base=(0.006, 0.006, 0.006), rough=0.60, spec=0.08,
                             note="(render-only) heat-blackened outlet band, inner wall and rim of the exhaust stacks "
                                  "(photo 130: a jet-black band with a crisp edge; 188: the dark inside of the scarfed "
                                  "opening); the GLB draws them in the shared satin 'black' (0.028), a dark-grey cap"),
    "wheel":            dict(kind="solid_paint", base=(0.62, 0.63, 0.64), rough=0.35, metallic=0.25,
                             coat=0.6, lining=False, note="painted wheel hubs"),
    "gear_leg":         dict(kind="solid_paint", base=(0.72, 0.73, 0.74), rough=0.32, coat=0.6, lining=False,
                             note="gloss white-grey painted gear legs / links"),
    "seam":             dict(kind="dielectric", base=(0.018, 0.018, 0.020), rough=0.60, spec=0.3,
                             note="door / hatch gap band (door_frames): a dark shadowed seam as in photos 130 / 0517 "
                                  "(the GLB's 0.16 grey drew light outlines round the doors)"),
    "gear_bay":         dict(kind="dielectric", base=(0.30, 0.31, 0.32), rough=0.55, spec=0.4,
                             note="(render-only) wheel-well liners, grey (the GLB's zinc_chromate yellow-green "
                                  "showed under the wing root; no MSN 3008 photo shows primer there)"),
    # ---- interior seen through the glazing (MSN 3008 photos 130 / 82 / 0517: light neutral-grey leather seats,
    #      light cockpit side walls; the model's tan leather made the panes read brown)
    "leather":          dict(kind="dielectric", base=(0.45, 0.445, 0.435), rough=0.55, spec=0.4,
                             note="light grey leather cabin seats (through-glass read of photos 130 / 82)"),
    "leather_dark":     dict(kind="dielectric", base=(0.30, 0.295, 0.29), rough=0.55, spec=0.4,
                             note="crew seats: mid-light grey (photo 0517: the pilot's seat back reads light grey "
                                  "through the side window)"),
    # door jambs: photos 188 (sun) and 82 (hangar) show a tan / khaki jamb with yellow speckles inside the black
    # door seal and a light aluminium lip -- neither light grey nor charcoal
    "jamb":             dict(kind="dielectric", base=(0.22, 0.165, 0.085), rough=0.70, spec=0.3,
                             note="door jambs (tan / khaki: photo 188 sRGB 182/154/103 in sun, 82 84/78/60 inside "
                                  "the doorway)"),
}
# the livery's navy line N1 under the thin white line P1: photos 130 / 82 / 188 show the base blue there (hangar
# region 91/122/182); the dark band seen under P1 in 82 moves relative to the stripes along the fuselage in 130 (a
# reflection horizon, not paint), and the white stripes are edged by thin champagne outlines instead (OUTLINE)
SPEC["paint_navy"] = dict(SPEC["paint_blue"], note="livery N1 line: rendered as the base blue (no navy line on MSN 3008)")


def _base_name(n):
    return re.sub(r"\.\d{3}$", "", n)


# =============================================================================================================
# Blender node builders
# =============================================================================================================
def _reset(m):
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    return nt, out


def _principled(nt, p, metallic=None):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.distribution = "MULTI_GGX"
    i = b.inputs
    base = tuple(p["base"])
    i["Base Color"].default_value = (*base, 1.0)
    i["Metallic"].default_value = float(p.get("metallic", 0.0) if metallic is None else metallic)
    i["Roughness"].default_value = float(p.get("rough", 0.4))
    i["IOR"].default_value = float(p.get("ior", 1.5))
    i["Specular IOR Level"].default_value = float(p.get("spec", 0.5))
    i["Coat Weight"].default_value = float(p.get("coat", 0.0))
    i["Coat Roughness"].default_value = float(p.get("coat_rough", 0.03))
    i["Coat IOR"].default_value = float(p.get("coat_ior", 1.5))
    return b


def _flake_normal(nt, scale, strength, fade=(1.0, 4.0)):
    """World-space shading normal tilted per flake cell: normalize(N + k (rand - 0.5)).  k fades out with the
    ray length (fade = (full, zero) metres): when a pixel covers thousands of flakes their aggregate IS the
    base roughness lobe, and per-sample random normals would only add noise (dark speckles after OIDN)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.feature = "F1"
    vor.inputs["Scale"].default_value = scale
    vor.inputs["Randomness"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    nt.links.new(vor.outputs["Color"], sub.inputs[0])
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(sub.outputs[0], sc.inputs[0])
    lp = nt.nodes.new("ShaderNodeLightPath")
    fd = nt.nodes.new("ShaderNodeMapRange")
    fd.clamp = True
    fd.inputs["From Min"].default_value, fd.inputs["From Max"].default_value = fade
    fd.inputs["To Min"].default_value, fd.inputs["To Max"].default_value = strength, 0.0
    nt.links.new(lp.outputs["Ray Length"], fd.inputs["Value"])
    nt.links.new(fd.outputs["Result"], sc.inputs["Scale"])
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    nt.links.new(geo.outputs["Normal"], add.inputs[0])
    nt.links.new(sc.outputs[0], add.inputs[1])
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(add.outputs[0], nrm.inputs[0])
    return nrm.outputs[0], geo.outputs["Normal"], tc


# back faces of the (single-sided, outward-wound) painted skins are the INSIDE of the aircraft: the model has
# no flight-deck side-wall lining, so through the glazing camera rays hit the skins from behind; render those
# (and the inner faces of open doors / gear doors, and the back of the PRO mask round the panes) as a satin
# light-grey interior lining instead of paint.  Round 2: 0.40 -> 0.55 (photo 0517: the lit cockpit reads light grey
# through the starboard side window, lin .023/.042/.071 in the shade, vs a near-black render even with clear panes).
# Round 3: split by station -- the flight deck (world x < 5.0 m: the side windows end at STA 4.35, the first cabin
# window is aft of 5.2) is lined darker, 0.30: outdoors (188) the windshield and side window are DARK panes with the
# interior barely visible, and the light lining made them milky; the cabin keeps 0.55 (0517 / 82: light-grey cabin).
LINING = dict(base=(0.55, 0.55, 0.54), rough=0.6, spec=0.4,
              flight_deck=dict(x1=5.0, blend=0.10, base=(0.30, 0.30, 0.295)))


def _lining(nt):
    """Principled lining shader; with LINING['flight_deck'] its base colour switches along the world x (== model
    station in the renders) from the flight-deck colour (x < x1) to the cabin colour over 'blend' metres."""
    q = {k: v for k, v in LINING.items() if k != "flight_deck"}
    lin = _principled(nt, q)
    fd = LINING.get("flight_deck")
    if fd:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        r = nt.nodes.new("ShaderNodeMapRange")
        r.clamp = True
        x1, bw = float(fd["x1"]), float(fd.get("blend", 0.1))
        r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = x1 - bw / 2, x1 + bw / 2
        nt.links.new(sep.outputs["X"], r.inputs["Value"])
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        ins = {(x.name, x.type): x for x in mx.inputs}
        nt.links.new(r.outputs["Result"], ins[("Factor", "VALUE")])
        ins[("A", "RGBA")].default_value = (*fd["base"], 1.0)
        ins[("B", "RGBA")].default_value = (*LINING["base"], 1.0)
        nt.links.new(next(x for x in mx.outputs if x.name == "Result" and x.type == "RGBA"), lin.inputs["Base Color"])
    return lin


def _finish(nt, out, shader, p):
    if p.get("lining", True):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        lin = _lining(nt)
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
        nt.links.new(shader, mix.inputs[1])
        nt.links.new(lin.outputs[0], mix.inputs[2])
        shader = mix.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])


def build_metal_paint(m, p):
    nt, out = _reset(m)
    q = dict(COAT)
    q.update(spec=0.1)             # base / lacquer interface: small index contrast
    q.update(p)
    b = _principled(nt, q)
    # F82 tint: the base colour (no white grazing on the flakes); spec_tint t blends it toward white (1 = a plain
    # Schlick metal whose reflection whitens at grazing: a silver-blue flake read)
    t = float(q.get("spec_tint", 0.0))
    b.inputs["Specular Tint"].default_value = (*((1 - t) * c + t for c in q["base"]), 1.0)
    if q.get("flake", True):
        n_flake, n_geo, tc = _flake_normal(nt, q.get("flake_scale", 2500.0), q.get("flake_strength", 0.06))
        nt.links.new(n_flake, b.inputs["Normal"])
        nt.links.new(n_geo, b.inputs["Coat Normal"])
        mottle = nt.nodes.new("ShaderNodeTexNoise")
        mottle.inputs["Scale"].default_value = q.get("mottle_scale", 6.0)
        mottle.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], mottle.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        r, a = float(q["rough"]), float(q.get("mottle", 0.03))
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 0.7
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = r - a, r + a
        nt.links.new(mottle.outputs["Factor"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    _finish(nt, out, b.outputs[0], q)


def build_solid_paint(m, p):
    nt, out = _reset(m)
    q = dict(COAT)
    q.update(spec=0.1)
    q.update(p)
    b = _principled(nt, q)
    _finish(nt, out, b.outputs[0], q)


def build_dielectric(m, p):
    nt, out = _reset(m)
    q = dict(p)
    q.setdefault("lining", False)                 # opt-in for dielectrics (trim_black / seal: the mask skin)
    b = _principled(nt, q)
    if q.get("grooves"):
        _tyre_grooves(nt, b, q)
    _finish(nt, out, b.outputs[0], q)


# tyre frame: object custom properties written by apply() (_tyre_frames) on every object drawn in a material with
# 'grooves', read in the shader by Attribute nodes (type OBJECT): ld_tyre_s = object scale (the GLB is quantized:
# local coordinates are the unit box, so Object texture coordinates x ld_tyre_s = metres), ld_tyre_c = centre and
# ld_tyre_a = axle direction in those scaled local coordinates, ld_tyre_g = (outer radius, tread width, 0) in metres.
TYRE_PROPS = ("ld_tyre_s", "ld_tyre_c", "ld_tyre_a", "ld_tyre_g")


def _tyre_grooves(nt, b, q):
    """n circumferential grooves ('width' m wide at the rib surface, evenly spaced over the tread: at +-0.1 / +-0.3
    of the tread width for n = 4) on the crown, as a bump of 'depth' metres: a flat floor out to 'floor_w' from the
    groove centre, then a smooth rounded shoulder up to 'shoulder' m outside the groove edge (the rounded rib edges
    carry the satin rib highlights of photo 130); the groove is darker ('floor' x base) and rougher.
    Without the tyre-frame properties (apply() given only materials) the groove mask is empty: a plain tyre."""
    g = q["grooves"]
    n, w = int(g.get("n", 4)), float(g.get("width", 0.006))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    att = {}
    for k in TYRE_PROPS:
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_type = "OBJECT"
        a.attribute_name = k
        att[k] = a.outputs["Vector"]

    def vm(op, a, b_=None):
        v = nt.nodes.new("ShaderNodeVectorMath")
        v.operation = op
        nt.links.new(a, v.inputs[0])
        if b_ is not None:
            nt.links.new(b_, v.inputs[1])
        return v.outputs["Value" if op in ("DOT_PRODUCT", "LENGTH") else "Vector"]

    P = vm("SUBTRACT", vm("MULTIPLY", tc.outputs["Object"], att["ld_tyre_s"]), att["ld_tyre_c"])
    axial = vm("DOT_PRODUCT", P, att["ld_tyre_a"])
    sc = nt.nodes.new("ShaderNodeVectorMath")
    sc.operation = "SCALE"
    nt.links.new(att["ld_tyre_a"], sc.inputs[0])
    nt.links.new(axial, sc.inputs["Scale"])
    radial = vm("LENGTH", vm("SUBTRACT", P, sc.outputs["Vector"]))
    sg = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(att["ld_tyre_g"], sg.inputs[0])
    R, T = sg.outputs["X"], sg.outputs["Y"]
    pitch = _math(nt, "MAXIMUM", _math(nt, "DIVIDE", T, float(n + 1)), 1e-4)       # rib pitch (T / (n + 1))
    # distance to the nearest groove centre: grooves at (k + 1/2 - n/2) pitch ... for n even: +-pitch/2, +-3 pitch/2
    off = 0.5 if n % 2 == 0 else 0.0
    v = _math(nt, "ADD", _math(nt, "DIVIDE", axial, pitch), off)
    d = _math(nt, "MULTIPLY", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", v, _math(nt, "ROUND", v))), pitch)
    gr = nt.nodes.new("ShaderNodeMapRange")
    gr.interpolation_type = "SMOOTHSTEP"
    gr.clamp = True
    gr.inputs["From Min"].default_value = float(g.get("floor_w", 0.25 * w))
    gr.inputs["From Max"].default_value = 0.5 * w + float(g.get("shoulder", 0.003))
    gr.inputs["To Min"].default_value, gr.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(d, gr.inputs["Value"])
    # only the n grooves (|axial| < n/2 pitch + w) and only on the crown (radial > 0.8 R: not the sidewalls / bead)
    lim = _math(nt, "ADD", _math(nt, "MULTIPLY", pitch, 0.5 * n), 0.5 * w + float(g.get("shoulder", 0.003)))
    in_ax = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", axial), lim)
    in_cr = _math(nt, "GREATER_THAN", radial, _math(nt, "MULTIPLY", R, 0.8))
    groove = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", gr.outputs["Result"], in_ax), in_cr)
    bu = nt.nodes.new("ShaderNodeBump")
    bu.invert = True                                   # grooves are depressions
    bu.inputs["Strength"].default_value = 1.0
    bu.inputs["Distance"].default_value = float(g.get("depth", 0.0025))
    nt.links.new(groove, bu.inputs["Height"])
    nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    base = tuple(q["base"])
    fl = float(g.get("floor", 0.4))
    nt.links.new(_mixc(nt, groove, base, tuple(fl * c for c in base)), b.inputs["Base Color"])
    nt.links.new(_mixf(nt, groove, float(q.get("rough", 0.45)), float(g.get("floor_rough", 0.7))),
                 b.inputs["Roughness"])


def _tyre_frames(spec):
    """Write the TYRE_PROPS custom properties on every mesh object drawn in a material with 'grooves' (in its own
    local frame, so they follow the gear pose): the axle = the principal axis of least variance of the metric local
    vertices, the outer radius = their largest distance from it, the tread width = 'tread' x the axial extent."""
    import bpy
    mats = {k: v["grooves"] for k, v in spec.items() if v.get("grooves") and v.get("enabled", True)}
    if not mats:
        return {}
    done = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        names = [_base_name(s.material.name) for s in o.material_slots if s.material is not None]
        hit = [k for k in names if k in mats]
        if not hit or len(o.data.vertices) < 16:
            continue
        g = mats[hit[0]]
        co = np.empty(len(o.data.vertices) * 3, np.float64)
        o.data.vertices.foreach_get("co", co)
        M = np.array(o.matrix_world, dtype=np.float64)
        s = np.linalg.norm(M[:3, :3], axis=0)                       # local axis scales (rotation + scale)
        P = co.reshape(-1, 3) * s
        c = 0.5 * (P.min(0) + P.max(0))
        X = P - c
        w_, V = np.linalg.eigh(X.T @ X / len(X))
        a = V[:, 0]
        ax = X @ a
        rad = np.linalg.norm(X - np.outer(ax, a), axis=1)
        R, width = float(rad.max()), float(ax.max() - ax.min())
        T = float(g.get("tread", 0.62)) * width
        o["ld_tyre_s"] = [float(v) for v in s]
        o["ld_tyre_c"] = [float(v) for v in c]
        o["ld_tyre_a"] = [float(v) for v in a]
        o["ld_tyre_g"] = [R, T, 0.0]
        done[o.name] = dict(radius_m=round(R, 4), width_m=round(width, 4), tread_m=round(T, 4))
    return done


def _sock(coll, name, typ):
    return next(x for x in coll if x.name == name and x.type == typ)


def _mixc(nt, fac, A, B):
    """Mix (RGBA) node; A / B are colour tuples or sockets, fac a socket."""
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    nt.links.new(fac, _sock(mx.inputs, "Factor", "VALUE"))
    for k, v in (("A", A), ("B", B)):
        if isinstance(v, tuple):
            _sock(mx.inputs, k, "RGBA").default_value = (*v, 1.0)
        else:
            nt.links.new(v, _sock(mx.inputs, k, "RGBA"))
    return _sock(mx.outputs, "Result", "RGBA")


def _mixf(nt, fac, a, b_):
    """Mix (FLOAT) node; a / b_ are numbers or sockets, fac a socket."""
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "FLOAT"
    nt.links.new(fac, _sock(mx.inputs, "Factor", "VALUE"))
    for k, v in (("A", a), ("B", b_)):
        if isinstance(v, (int, float)):
            _sock(mx.inputs, k, "VALUE").default_value = float(v)
        else:
            nt.links.new(v, _sock(mx.inputs, k, "VALUE"))
    return _sock(mx.outputs, "Result", "VALUE")


def _math(nt, op, a, b_=None, clamp=False):
    """Math node; a / b_ are numbers or sockets."""
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for k, v in enumerate((a, b_)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[k].default_value = float(v)
        else:
            nt.links.new(v, n.inputs[k])
    return n.outputs[0]


def build_metal(m, p):
    """Metal (Metallic 1).  collar = dict(x0, blend, tint_x0, tint, base, rough, metallic, spec): along the WORLD x
    (= model station in the renders) the colour runs polished -> heat tint (tint_x0 .. x0) -> the collar
    (base / rough / metallic / Specular IOR Level) aft of x0 over a 'blend' metres wide edge: the heat-blackened
    exhaust outlet.  polish = dict(scale, stretch, detail, rough=(lo, hi), tint_mix, bump, bump_distance): a world-
    space noise (scale per metre, the position multiplied by 'stretch' first: streaks along x) that drives the
    roughness between lo and hi, pulls the colour up to tint_mix toward the collar's heat tint and bumps the normal
    (hand-polished stainless: wavy, streaky reflections); the collar's colour / roughness replace it aft of x0."""
    nt, out = _reset(m)
    q = dict(p)
    q["metallic"] = 1.0
    b = _principled(nt, q)
    c = q.get("collar")
    pol = q.get("polish")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    noise = None
    if pol:
        mp = nt.nodes.new("ShaderNodeVectorMath")
        mp.operation = "MULTIPLY"
        s = float(pol.get("scale", 20.0))
        mp.inputs[1].default_value = tuple(s * float(v) for v in pol.get("stretch", (1.0, 1.0, 1.0)))
        nt.links.new(geo.outputs["Position"], mp.inputs[0])
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 1.0
        nz.inputs["Detail"].default_value = float(pol.get("detail", 3.0))
        nt.links.new(mp.outputs[0], nz.inputs["Vector"])
        nr = nt.nodes.new("ShaderNodeMapRange")          # noise factor ~0.5 +- 0.15 -> 0 .. 1
        nr.clamp = True
        nr.inputs["From Min"].default_value, nr.inputs["From Max"].default_value = 0.3, 0.7
        nt.links.new(nz.outputs["Fac"], nr.inputs["Value"])
        noise = nr.outputs["Result"]
        if float(pol.get("bump", 0.0)) > 0.0:
            bu = nt.nodes.new("ShaderNodeBump")
            bu.inputs["Strength"].default_value = float(pol["bump"])
            bu.inputs["Distance"].default_value = float(pol.get("bump_distance", 0.01))
            nt.links.new(nz.outputs["Fac"], bu.inputs["Height"])
            nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    rough = float(q.get("rough", 0.1))
    col = tuple(q["base"])
    if pol:
        lo, hi = (float(v) for v in pol.get("rough", (rough, rough)))
        rough = _mixf(nt, noise, lo, hi)
    if c:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])

        def ramp(a, b_):
            r = nt.nodes.new("ShaderNodeMapRange")
            r.clamp = True
            r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = a, b_
            nt.links.new(sep.outputs["X"], r.inputs["Value"])
            return r.outputs["Result"]

        x0, bw = float(c["x0"]), float(c.get("blend", 0.005))
        tint = tuple(c.get("tint", q["base"]))
        f_tint = ramp(float(c.get("tint_x0", x0 - 0.1)), x0 - bw)
        f_col = ramp(x0 - bw / 2, x0 + bw / 2)
        col = _mixc(nt, f_tint, col, tint)
        if pol:
            col = _mixc(nt, _math(nt, "MULTIPLY", noise, float(pol.get("tint_mix", 0.3))), col, tint)
        col = _mixc(nt, f_col, col, tuple(c["base"]))
        rough = _mixf(nt, f_col, rough, float(c.get("rough", 0.45)))
        nt.links.new(_mixf(nt, f_col, 1.0, float(c.get("metallic", 0.3))), b.inputs["Metallic"])
        nt.links.new(_mixf(nt, f_col, float(q.get("spec", 0.5)), float(c.get("spec", q.get("spec", 0.5)))),
                     b.inputs["Specular IOR Level"])
    if not isinstance(col, tuple):
        nt.links.new(col, b.inputs["Base Color"])
    if not isinstance(rough, float):
        nt.links.new(rough, b.inputs["Roughness"])
    shader = b.outputs[0]
    bk = q.get("back")
    if bk:                                   # back faces of an open single-sided shell (the stack's inside): soot
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sb = _principled(nt, dict(bk))
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
        nt.links.new(shader, mix.inputs[1])
        nt.links.new(sb.outputs[0], mix.inputs[2])
        shader = mix.outputs[0]
    nt.links.new(shader, out.inputs["Surface"])


def build_glass(m, p):
    """Thin pane(s): mix(Transparent(tint), Glossy(white), R), R = N F / (1 + (N - 1) F) for N = p['surfaces']
    reflecting surfaces (2 = one pane: 2F/(1+F); 4 = a double-pane window), incoherent, no absorption between."""
    nt, out = _reset(m)
    n_s = float(p.get("surfaces", 2))
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*p["tint"], 1.0)
    gl = nt.nodes.new("ShaderNodeBsdfGlossy")
    gl.distribution = "GGX"
    gl.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    gl.inputs["Roughness"].default_value = float(p.get("rough", 0.004))
    fr = nt.nodes.new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = float(p.get("ior", 1.5))
    num = nt.nodes.new("ShaderNodeMath")
    num.operation = "MULTIPLY"
    num.inputs[1].default_value = n_s
    nt.links.new(fr.outputs[0], num.inputs[0])
    den = nt.nodes.new("ShaderNodeMath")
    den.operation = "MULTIPLY_ADD"                  # (N - 1) F + 1
    den.inputs[1].default_value = n_s - 1.0
    den.inputs[2].default_value = 1.0
    nt.links.new(fr.outputs[0], den.inputs[0])
    div = nt.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    div.use_clamp = True
    nt.links.new(num.outputs[0], div.inputs[0])
    nt.links.new(den.outputs[0], div.inputs[1])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(div.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    for attr, val in (("surface_render_method", "BLENDED"), ("use_backface_culling", False)):
        try:
            setattr(m, attr, val)
        except Exception:
            pass


BUILDERS = dict(metal_paint=build_metal_paint, solid_paint=build_solid_paint, dielectric=build_dielectric,
                metal=build_metal, glass=build_glass)


def resolved_spec(overrides=None):
    """SPEC with per-material overrides {name: {key: value}} (e.g. from beauty's --set lookdev.<mat>.<key>=v)."""
    spec = {k: dict(v) for k, v in SPEC.items()}
    for k, v in (overrides or {}).items():
        if k in spec and isinstance(v, dict):
            spec[k].update({kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()})
    return spec


def _materials_of(target):
    import bpy
    if target is None:
        return list(bpy.data.materials)
    if isinstance(target, bpy.types.Scene):
        mats = []
        for o in target.objects:
            for s in getattr(o, "material_slots", ()):
                if s.material is not None and s.material not in mats:
                    mats.append(s.material)
        return mats
    if isinstance(target, bpy.types.Material):
        return [target]
    return list(target)


def _whole_scene(target):
    """True when apply() was given the whole file (None / bpy.data.materials / a Scene): only then does it touch
    objects (REASSIGN, OUTLINE) and the environment (ENV)."""
    import bpy
    if target is None or isinstance(target, bpy.types.Scene):
        return True
    try:
        return target == bpy.data.materials
    except Exception:
        return False


def _merge(base, over):
    d = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            d[k].update(v)
        else:
            d[k] = tuple(v) if isinstance(v, list) and v and not isinstance(v[0], list) else v
    return d


# ---------------------------------------------------------------------------------------------------------------
# REASSIGN: primitives moved onto render-only materials: (object-name prefixes, GLB material, new material).
# The glTF import makes one object per primitive, named '<part>#<k>:geo'.  model/assemble.py can adopt these
# material names; until then the renders split them here.
# ---------------------------------------------------------------------------------------------------------------
REASSIGN = (
    (("glazing_cabin", "door_cargo", "exit_hatch"), "glass", "glass_cabin"),   # double-pane cabin windows
    (("glazing_cabin", "door_cargo", "exit_hatch"), "seal", "seal_cabin"),     # flush cabin-window rings
    (("gear_bays",), "zinc_chromate", "gear_bay"),                            # grey wheel wells
    (("exhaust_stacks",), "black", "exhaust_soot"),                           # jet-black stack collar / inside
)


def _reassign(rules):
    import bpy
    made, moved = {}, {}
    for prefixes, src, dst in rules:
        for o in bpy.data.objects:
            if o.type != "MESH" or not o.name.startswith(tuple(prefixes)):
                continue
            for slot in o.material_slots:
                if slot.material is None or _base_name(slot.material.name) != src:
                    continue
                if dst not in made:
                    m = bpy.data.materials.get(dst)
                    if m is None:
                        m = slot.material.copy()
                        m.name = dst
                    made[dst] = m
                slot.material = made[dst]
                moved.setdefault(dst, []).append(o.name)
    return {k: len(v) for k, v in moved.items()}


# ---------------------------------------------------------------------------------------------------------------
# OUTLINE: the white pinstripes / swooshes of MSN 3008 are edged with a ~8 mm champagne metallic line
# (photo 82: sRGB 191/185/182 on both edges of every white stroke, 227/227/229 inside; 188 / 130 the same).  The
# livery has no such strokes, so apply() lays a thin ribbon (paint_champagne) along every COLOUR boundary of the
# stripe primitives: a stripe boundary edge whose two ends lie within 'tol' of the boundary of a primitive of
# ANOTHER paint (part cuts, where the neighbour is the same white, and holes are skipped).  The ribbon is 'width'
# wide, centred on the edge, 'lift' above the skin, parented to the source object (it follows the pose) and
# copies its render visibility.  A livery.py outline stroke would replace this (see the JSON '_model').
# ---------------------------------------------------------------------------------------------------------------
OUTLINE = dict(enabled=True, stripes=("paint_pinstripe",), material="paint_champagne", width=0.008, lift=0.0003,
               tol=0.0015, weld=5e-5, overlap=0.25)


def _world_mesh(o):
    me = o.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    M = np.array(o.matrix_world, dtype=np.float64)
    V = co.reshape(-1, 3).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
    me.calc_loop_triangles()
    F = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", F)
    return V, F.reshape(-1, 3)


def _boundary(V, F, q):
    """Welded (grid q) boundary edges, oriented as in their triangle, and area-weighted welded vertex normals."""
    key = np.round(V / q).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    P = V[first]
    Fw = inv[F]
    Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 2] != Fw[:, 0])]
    fn = np.cross(P[Fw[:, 1]] - P[Fw[:, 0]], P[Fw[:, 2]] - P[Fw[:, 0]])
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, Fw[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    E = np.concatenate([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]])
    _, idx, cnt = np.unique(np.sort(E, 1), axis=0, return_index=True, return_counts=True)
    return P, N, E[idx[cnt == 1]]


def _outline(cfg):
    import bpy
    from mathutils import Vector
    from mathutils.kdtree import KDTree
    stripes = tuple(cfg.get("stripes", ("paint_pinstripe",)))
    q, tol, w, lift = float(cfg["weld"]), float(cfg["tol"]), float(cfg["width"]), float(cfg["lift"])

    def mat_of(o):
        ms = [_base_name(s.material.name) for s in o.material_slots if s.material is not None]
        return ms[0] if len(ms) == 1 else None

    src, oth = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name.startswith("outline_"):
            continue
        m = mat_of(o)
        if m in stripes:
            src.append(o)
        elif m is not None and (m.startswith("paint_") or m == "trim_black"):
            oth.append(o)
    pts = []
    for o in oth:
        P, _, B = _boundary(*_world_mesh(o), q)
        if len(B):
            pts.append(P[np.unique(B)])
    if not src or not pts:
        return dict(objects=0)
    pts = np.vstack(pts)
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(Vector(p), i)
    kd.balance()
    mat = bpy.data.materials.get(cfg["material"]) or bpy.data.materials.new(cfg["material"])
    n_obj, n_edges, length = 0, 0, 0.0
    for o in src:
        P, N, B = _boundary(*_world_mesh(o), q)
        if not len(B):
            continue
        ids = np.unique(B)
        near = np.zeros(len(P), bool)
        near[ids] = [kd.find(Vector(P[i]))[2] <= tol for i in ids]
        B = B[near[B[:, 0]] & near[B[:, 1]]]
        if not len(B):
            continue
        a, b = P[B[:, 0]], P[B[:, 1]]
        t = b - a
        L = np.linalg.norm(t, axis=1, keepdims=True)
        ok = L[:, 0] > 1e-6
        a, b, t, L, B = a[ok], b[ok], t[ok], L[ok], B[ok]
        th = t / L
        e = float(cfg.get("overlap", 0.25)) * w                 # overlap at the joints (no gaps on bends)
        a2, b2 = a - th * e, b + th * e
        na, nb = N[B[:, 0]], N[B[:, 1]]
        sa = np.cross(na, th)
        sb = np.cross(nb, th)
        sa /= np.maximum(np.linalg.norm(sa, axis=1, keepdims=True), 1e-12)
        sb /= np.maximum(np.linalg.norm(sb, axis=1, keepdims=True), 1e-12)
        h = 0.5 * w
        quad = np.stack([a2 - sa * h + na * lift, b2 - sb * h + nb * lift,
                         b2 + sb * h + nb * lift, a2 + sa * h + na * lift], 1)      # normal = +n
        verts = quad.reshape(-1, 3)
        faces = np.arange(len(verts)).reshape(-1, 4)
        me = bpy.data.meshes.new(f"outline_{o.name}")
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.update()
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"outline_{o.name}", me)
        for c in (o.users_collection or [bpy.context.scene.collection]):
            c.objects.link(ob)
        ob.parent = o                                            # follows the pose (doors)
        ob.matrix_parent_inverse = o.matrix_world.inverted()
        ob.hide_render = o.hide_render
        for attr in ("visible_camera", "visible_diffuse", "visible_glossy", "visible_transmission",
                     "visible_volume_scatter", "visible_shadow"):
            try:
                setattr(ob, attr, getattr(o, attr))
            except Exception:
                pass
        n_obj += 1
        n_edges += len(B)
        length += float(L.sum())
    return dict(objects=n_obj, edges=n_edges, length_m=round(length, 1), width_m=w)


# ---------------------------------------------------------------------------------------------------------------
# ENV: environment corrections that belong to the look (render/hooks.py lets lookdev patch render.beauty in
# place; beauty.py itself is not edited).  apply() wraps beauty.build_env once per process.  Settings are keyed by
# PRESET name (info['preset']; beauty.render_preset sets it) and fall back to the preset's env ('studio_cyc' covers
# the turntable, which is built from the hero preset without a preset name).  Before the preset's environment is
# built:
#   terrain   {preset: ground_albedo} replaces the preset's terrain albedo (air shots: the radiance below the
#             horizon that the undersides mirror and are lit by).  Round 4: neutral 0.10 (round 3's blue .08/.10/.125,
#             added to push the wing underside to navy, tinted every neutral underside blue: tailplane silver 46/61/80
#             against the photo's 58/58/59, white 131/139/148 against 165/164/167; beauty's own is a warm .13/.11/.08)
# after it:
#   osb       hangar OSB ceiling colour ramp (dark, light), linear albedo.  Photo 130 ceiling, same camera, same
#             pixels (medians): lin .57/.36/.11 (left) .44/.29/.12 (mid) .76/.55/.24 (right), R:G:B 1 : .63-.73 :
#             .20-.31; round-1 render .41/.22/.09, .51/.29/.14, .40/.21/.07 (1 : .51-.57) -- too orange and too dark:
#             the panes, spinner and exhaust mirrored it as brown bands.  AgX + the grade desaturate the bright
#             ceiling, so the albedo ratio sits below the photo's (rendered ratio ~ albedo ratio + .05 in G)
#   hangar    what the UPWARD reflections see (photo 130: spinner top, exhaust top and windshield mirror white /
#             neutral with a few THIN LED lines; the render mirrored the golden OSB crossed by wide LED bands):
#             panel = a neutral grey ceiling zone (painted roof deck / services) just under the OSB wherever the
#             photo does not show the ceiling: poly (x, y) at height z, albedo.  The polygon is the part of the
#             ceiling the solved 'port_hangar_130' camera never sees, with ~60 px / 0.5 m of margin (its visible
#             ceiling starts at x = 14.0 / 11.4 / 7.5 / 4.9 m for y = -4 / 0 / 6 / 10; nothing port of y = -5);
#             albedo 0.22 = the OSB ramp's mean luminance (.16 .. .29), so the room's diffuse light stays the same
#             (a white 0.8 panel lifted the whole furnace: blue side region dE 3.7 -> 11.8, windshield 174/173/166;
#             0.30 left it ~3 % bright: paint_blue region 4.8 -> 4.0, side-window glass 6.9 -> 5.3 at 0.22, the
#             windshield 2.2 -> 3.0).  strip_width = LED strip
#             width factor (0.12 m -> 0.06 m at the same power: thin lines in the paint instead of wide bands)
#   interior  cabin / cockpit lights (camera-invisible area lights under the cockpit roof and the cabin ceiling),
#             (x, y, z, size_x, size_y, watts) in MODEL coordinates, pointing down; presets / envs -> (power scale,
#             colour).  Round 3: keyed by PRESET.  Outdoors the flight deck of MSN 3008 is DARK through the glass
#             (188: the red BRAKES ON card is about all that shows), so nose_port_closeup has none.  Hero / studio:
#             the seats glowing white through the glazing were lit by the KEY, not by these lights (hero side-window
#             region sRGB 129 with the lights at 0.15 AND at 0; with the key flagged off the seats (flags) 10 at 0.15
#             -- a black hole -- and 37 at 0.5: dim grey seat shapes, a dark flight deck as in 188), so the studio
#             keeps 0.5 behind the seat flag; apron_stbd34 keeps 0.25 (round 5, airfield environment: side window
#             38/54/74 against the photo's 41/58/75, the glass region still a little dark); before round 5 it was a
#             stop-gap: its side
#             window in 0517 is bright mostly by REFLECTION of the shaded hangar door / sky, which the race-track HDRI
#             does not have (an environment fix, not a material one); hangar: warm LED cabin lights (0.3)
#   flags     {preset or env: dict(materials, lights)}: light-link the named softboxes AWAY from the objects of
#             those materials (a studio flag).  The hero's 9-14 kW boxes over-light the black parts so much that
#             AgX's shoulder shows a 0.05-albedo tyre as mid grey: tyre region sRGB 121 against 235 for the white
#             stripe with Specular 0.03 AND with Specular 0 (measured) -- it is the DIFFUSE key / overhead light,
#             not a sheen, so a material override cannot fix it; flagging the overhead / key / rims off the tyres
#             and blades leaves them the low fill, the backdrop glow and the HDRI (tyre 121 -> 43, blade 133 -> 13:
#             black rubber with a shoulder sheen, satin-black blades against the grey backdrop).  The seats
#             (leather, leather_dark) are flagged too: the key shone straight through the side window onto the
#             pilot's seat (see interior).  beauty's own linking: this worktree's overhead / rims light only the
#             cyclorama (its EXCLUDE lookup fails and leaves the floor INCLUDE); Calc-s2's beauty.py does the same on
#             purpose (floor_only) and already takes the blades off the key -- in both the flag's effective part is
#             the key, and the EXCLUDE entries merge into beauty's receiver collections
#   materials {preset or env: {material: {key: value}}} per-preset material overrides, rebuilt after the env
#             (none by default)
#   outdoor   {preset: settings} = render/airfield.py SETTINGS: for these presets _env_pre hands beauty.build_env a
#             sky-only preset copy (env 'airfield': the sky HDRI rotated to the measured sun azimuth, no shadow
#             catcher) and _env_post builds the rest (capped HDRI sun + sun lamp, sky light / camera look, ground,
#             markings, props, skyline).  pre['airfield'] (--set airfield.sun.el=38 ...) is deep-merged over the
#             settings, --set airfield=false keeps beauty's environment.
# ---------------------------------------------------------------------------------------------------------------
ENV = dict(
    osb=((0.25, 0.150, 0.036), (0.44, 0.265, 0.062)),
    hangar=dict(panel=dict(poly=((-8.0, -4.5), (13.8, -4.5), (13.5, -4.0), (8.2, 4.0), (-8.0, 4.0)),
                           z=8.45, albedo=0.22), strip_width=0.5),
    interior=dict(lights=((3.95, 0.0, 2.58, 0.55, 0.9, 3.0),         # flight-deck dome / flood
                          (6.85, 0.0, 2.64, 3.6, 0.5, 60.0)),         # cabin ceiling wash
                  presets=dict(hangar_port34=(0.3, (1.0, 0.97, 0.92)), apron_stbd34=(0.25, (0.82, 0.90, 1.0)),
                               nose_port_closeup=(0.0, (1.0, 1.0, 1.0)), hero=(0.5, (1.0, 0.98, 0.95))),
                  envs=dict(hangar=(0.3, (1.0, 0.97, 0.92)), studio_cyc=(0.5, (1.0, 0.98, 0.95)),
                            studio_white=(0.3, (1.0, 0.98, 0.95)))),
    terrain=dict(air_below_left=(0.10, 0.10, 0.10)),
    flags=dict(studio_cyc=dict(materials=("tire", "prop_blade", "leather", "leather_dark"),
                               lights=("overhead", "key", "rim_R", "rim_L"))),
    materials=dict(),
    outdoor=None,                     # set below: render/airfield.py SETTINGS (keyed by preset)
)
_STATE = dict(spec=None)          # the spec apply() last built (for the per-preset material overrides)


def _airfield():
    """render/airfield.py (the outdoor environments), importable whichever way lookdev itself was imported."""
    try:
        from render import airfield as A
    except ImportError:
        import airfield as A
    return A


ENV["outdoor"] = _airfield().SETTINGS


def _outdoor(pre, env, info):
    """The airfield settings of this preset (ENV['outdoor'][preset] deep-merged with pre['airfield']) or None;
    --set airfield=false keeps beauty's own environment."""
    table = env.get("outdoor")
    name = (info or {}).get("preset")
    if not table or name not in table or pre.get("airfield") is False:
        return None
    cfg = table[name]
    if isinstance(pre.get("airfield"), dict):
        cfg = _airfield()._deep_merge(cfg, pre["airfield"])
    return cfg


def _beauty_modules():
    mods = []
    for name in ("__main__", "beauty", "render.beauty"):
        m = sys.modules.get(name)
        if m is not None and hasattr(m, "build_env") and hasattr(m, "render_preset") and m not in mods:
            mods.append(m)
    return mods


def _keyed(table, pre, info):
    """table[preset name] if present, else table[env] (None if neither)."""
    if not table:
        return None
    name = (info or {}).get("preset")
    if name in table:
        return table[name]
    return table.get(pre.get("env"))


def _env_pre(pre, env, info, B=None):
    """Preset copy with the lookdev terrain albedo, or for an outdoor preset the sky-only copy that
    render/airfield.py completes in _env_post (the original dict is not changed)."""
    oc = _outdoor(pre, env, info)
    if oc is not None:
        A = _airfield()
        if B is not None:
            A.register_skies(B)
        if info is not None:
            info.setdefault("lookdev_env", {})["outdoor"] = dict(was=dict(env=pre.get("env"), hdri=pre.get("hdri"),
                                                                           sun_az=pre.get("sun_az")))
        return A.build_env_preset(pre, oc)
    alb = _keyed(env.get("terrain"), pre, info)
    if alb is None or pre.get("ground_albedo") is None:
        return pre
    q = dict(pre)
    q["ground_albedo"] = tuple(float(v) for v in alb)
    if info is not None:
        info.setdefault("lookdev_env", {})["terrain_albedo"] = dict(was=list(pre["ground_albedo"]), now=list(q["ground_albedo"]))
    return q


def _hangar(S, cfg):
    bpy = S.bpy
    done = {}
    k = cfg.get("strip_width")
    if k and float(k) != 1.0:
        k = float(k)
        n = 0
        for o in list(S.sc.objects):
            if not o.name.startswith("strip_") or o.type != "MESH":
                continue
            me = o.data
            ys = [v.co.y for v in me.vertices]
            c = 0.5 * (min(ys) + max(ys))
            for v in me.vertices:
                v.co.y = c + (v.co.y - c) * k
            me.update()
            n += 1
        em = bpy.data.materials.get("led_strip")
        if em is not None and n:
            for nd in em.node_tree.nodes:
                if nd.type == "BSDF_PRINCIPLED":
                    nd.inputs["Emission Strength"].default_value /= k
        done["strip_width_factor"] = k
    pan = cfg.get("panel")
    if pan:
        z, alb = float(pan.get("z", 8.45)), float(pan.get("albedo", 0.3))
        poly = [(float(x), float(y), z) for x, y in pan["poly"]][::-1]      # clockwise from above: normal down
        m = S.new_material("lookdev_ceiling_panel", color=(alb, alb, alb), rough=0.85, spec=0.3)
        me = bpy.data.meshes.new("lookdev_ceiling_panel")
        me.from_pydata(poly, [], [tuple(range(len(poly)))])
        me.update()
        me.materials.append(m)
        ob = bpy.data.objects.new("lookdev_ceiling_panel", me)
        S.sc.collection.objects.link(ob)
        done["ceiling_panel"] = dict(poly=[list(v[:2]) for v in poly[::-1]], z=z, albedo=alb)
    return done


def _flags(S, fl):
    """Exclude the objects drawn in fl['materials'] from the lights named in fl['lights'] (Blender light linking:
    EXCLUDE entries in the light's receiver collection; a collection holding only EXCLUDE entries still lights
    everything else, so the lights' existing links -- beauty's floor exclusion -- keep working)."""
    bpy = S.bpy
    mats = set(fl.get("materials", ()))
    objs = [o for o in S.sc.objects if o.type == "MESH" and any(
        sl.material is not None and _base_name(sl.material.name) in mats for sl in o.material_slots)]
    lights = []
    for o in S.sc.objects:
        if o.type != "LIGHT" or _base_name(o.name) not in fl.get("lights", ()):
            continue
        try:
            ll = o.light_linking
            coll = ll.receiver_collection
            if coll is None:
                coll = bpy.data.collections.new(f"lookdev_flag_{o.name}")
                ll.receiver_collection = coll
            for ob in objs:
                if coll.objects.get(ob.name) is None:
                    coll.objects.link(ob)
            # collection_objects has no name lookup (Blender 5.0: 'does not support string lookups'); its items
            # run parallel to coll.objects
            names = [ob.name for ob in objs]
            for co, ob in zip(coll.collection_objects, coll.objects):
                if ob.name in names:
                    co.light_linking.link_state = "EXCLUDE"
            lights.append(o.name)
        except Exception as e:                       # Blender < 4.0: no light linking
            return dict(error=str(e))
    return dict(lights=lights, objects=len(objs))


def _env_post(S, pre, env, info=None, cam=None, B=None):
    bpy = S.bpy
    done = {}
    oc = _outdoor(pre, env, info)
    if oc is not None and cam is not None and B is not None:
        _airfield().build(S, pre, cam, info, oc, B)
        done["outdoor_built"] = "render/airfield.py"
    m = bpy.data.materials.get("osb_ceiling")
    if m is not None and env.get("osb"):
        for n in m.node_tree.nodes:
            if n.type == "VALTORGB":
                for el, c in zip(n.color_ramp.elements, env["osb"]):
                    el.color = (*c, 1.0)
        done["osb"] = [list(c) for c in env["osb"]]
    if pre.get("env") == "hangar" and env.get("hangar"):
        done.update(_hangar(S, env["hangar"]))
    ic = env.get("interior") or {}
    sel = _keyed(ic.get("presets"), pre, info)
    if sel is None:
        sel = _keyed(ic.get("envs"), pre, None)
    if ic.get("lights") and sel is not None and float(sel[0]) > 0.0:
        from mathutils import Euler
        scale, colour = sel
        for k, (x, y, z, sx, sy, w) in enumerate(ic["lights"]):
            ld = bpy.data.lights.new(f"lookdev_interior_{k}", "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = float(sx), float(sy)
            ld.energy = float(w) * float(scale)
            ld.color = tuple(float(c) for c in colour)
            ob = bpy.data.objects.new(f"lookdev_interior_{k}", ld)
            ob.location = (float(x), float(y), float(z))
            ob.rotation_euler = Euler((0.0, 0.0, 0.0))          # area lights emit along -Z: down
            for attr in ("visible_camera", "visible_glossy", "visible_transmission"):
                try:
                    setattr(ob, attr, False)
                except Exception:
                    pass
            S.sc.collection.objects.link(ob)
        done["interior_lights"] = dict(n=len(ic["lights"]), scale=float(scale), colour=list(colour))
    elif sel is not None:
        done["interior_lights"] = dict(n=0, scale=0.0)
    fl = _keyed(env.get("flags"), pre, info)
    if fl:
        done["flags"] = _flags(S, fl)
    mo = _keyed(env.get("materials"), pre, info)
    if mo and _STATE.get("spec"):
        rebuilt = {}
        for mat in bpy.data.materials:
            nm = _base_name(mat.name)
            if nm in mo and nm in _STATE["spec"]:
                p = dict(_STATE["spec"][nm])
                p.update({kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in mo[nm].items()})
                BUILDERS[p["kind"]](mat, p)
                rebuilt[mat.name] = mo[nm]
        done["materials"] = rebuilt
    if info is not None and done:
        info.setdefault("lookdev_env", {}).update(done)
    return done


def _patch_beauty(env):
    patched = []
    for B in _beauty_modules():
        cur = B.build_env
        state = getattr(cur, "_lookdev", None)
        if state is not None:
            state["env"] = env
        else:
            state = {"env": env}

            def build_env(S, pre, cam, info, _orig=cur, _state=state, _B=B):
                r = _orig(S, _env_pre(pre, _state["env"], info, _B), cam, info)
                _env_post(S, pre, _state["env"], info, cam, _B)
                return r
            build_env._lookdev = state
            build_env.__doc__ = cur.__doc__
            B.build_env = build_env
        patched.append(B.__name__)
    return dict(patched=patched)


def apply(target=None, overrides=None, verbose=False):
    """Rebuild the materials of target (bpy.data.materials / a Scene / a list of materials / None = all) whose
    name is in SPEC.  overrides: {material: {key: value}} (keys of SPEC entries; 'enabled': False skips one) plus
    '_env' / '_outline' (dicts merged into ENV / OUTLINE; '_outline': {'enabled': False} skips the ribbons) and
    '_reassign': False.  Given the whole file (None / bpy.data.materials / a Scene) it first splits the REASSIGN
    primitives onto their render-only materials, lays the OUTLINE ribbons and patches the environment (ENV).
    Returns {material name: kind} of the rebuilt ones (+ '_reassigned' / '_outline' / '_env' summaries)."""
    if overrides is False:                               # --set lookdev=false: keep the importer's materials
        return {}
    ov = dict(overrides or {})
    spec = resolved_spec(ov)
    extra = {}
    if _whole_scene(target):
        extra["_env"] = _patch_beauty(_merge(ENV, ov.get("_env")))
        if ov.get("_reassign", True) is not False:
            extra["_reassigned"] = _reassign(REASSIGN)
        oc = _merge(OUTLINE, ov.get("_outline"))
        if oc.get("enabled", True):
            extra["_outline"] = _outline(oc)
        tf = _tyre_frames(spec)
        if tf:
            extra["_tyre_frames"] = tf
    _STATE["spec"] = spec
    done = {}
    for m in _materials_of(target):
        p = spec.get(_base_name(m.name))
        if p is None or not p.get("enabled", True):
            continue
        BUILDERS[p["kind"]](m, p)
        done[m.name] = p["kind"]
    if verbose:
        print(f"[lookdev] rebuilt {len(done)} materials: {', '.join(sorted(done))}; {extra}", flush=True)
    done.update(extra)
    return done


# =============================================================================================================
# glTF / three.js table
# =============================================================================================================
def gltf_table(overrides=None):
    """{material: glTF PBR values} for the viewer and model/assemble.MATERIALS (linear factors; KHR_materials_
    clearcoat / transmission / ior names).  Metallic paints use their 'gltf' metallic (no F82 tint in glTF)."""
    out = {}
    for name, p in resolved_spec(overrides).items():
        g = dict(p.get("gltf", {}))
        kind = p["kind"]
        if kind == "glass":
            # alphaMode BLEND (plain glTF / three.js transparent): a dark base carrying only the specular
            # reflections, alpha ~ 1 - transmittance; with KHR_materials_transmission use 'transmission_variant'
            # (the base colour then filters the transmitted light like the Blender tint)
            base = g.get("base", p["tint"])
            d = dict(baseColorFactor=[*map(float, base), float(g.get("alpha", 0.5))], metallicFactor=0.0,
                     roughnessFactor=0.02, clearcoatFactor=0.0, clearcoatRoughnessFactor=0.0,
                     ior=float(p.get("ior", 1.5)), alphaMode="BLEND", doubleSided=True,
                     transmission_variant=dict(baseColorFactor=[*map(float, p["tint"]), 1.0], transmissionFactor=1.0,
                                               roughnessFactor=float(p.get("rough", 0.004)), metallicFactor=0.0,
                                               ior=float(p.get("ior", 1.5)), thin=True))
        else:
            metallic = 1.0 if kind == "metal" else float(g.get("metallic", p.get("metallic", 0.0)))
            coat = float(p.get("coat", 1.0 if kind in ("metal_paint", "solid_paint") else 0.0))
            d = dict(baseColorFactor=[*map(float, p["base"]), 1.0], metallicFactor=metallic,
                     roughnessFactor=float(g.get("rough", p.get("rough", 0.4))),
                     clearcoatFactor=coat, clearcoatRoughnessFactor=float(p.get("coat_rough", 0.03)) if coat else 0.0,
                     ior=float(p.get("ior", 1.5)))
            if kind != "metal":            # KHR_materials_specular: F0 scale (Blender Specular IOR Level 0.5 = 1)
                spec = float(p.get("spec", 0.1 if kind in ("metal_paint", "solid_paint") else 0.5))
                d["specularFactor"] = round(2.0 * spec, 3)
            if kind == "metal_paint":
                d["blender_metallic"] = float(p["metallic"])
                d["blender_roughness"] = float(p["rough"])
            if p.get("collar"):            # not a glTF factor: a station-dependent colour (texture / shader)
                d["render_collar"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p["collar"].items()}
            if p.get("back"):              # back faces of an open shell (three.js: side=DoubleSide + gl_FrontFacing)
                d["render_back_faces"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p["back"].items()}
            if p.get("polish"):            # streaky roughness / tint noise + bump (three.js: a noise roughness map)
                d["render_polish"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in p["polish"].items()}
            if p.get("grooves"):           # circumferential tread grooves (three.js: a normal map on the tyre)
                d["render_grooves"] = dict(p["grooves"])
        if kind == "glass":
            d["surfaces"] = int(p.get("surfaces", 2))
        d["kind"] = kind
        d["note"] = p.get("note", "")
        d["srgb_hex"] = _hex(d["baseColorFactor"][:3])
        out[name] = d
    return out


def _hex(rgb):
    c = [1.055 * v ** (1 / 2.4) - 0.055 if v > 0.0031308 else 12.92 * v for v in rgb]
    return "#" + "".join(f"{int(round(255 * min(max(v, 0.0), 1.0))):02X}" for v in c)


def write_json(path=JSON_OUT):
    doc = dict(
        _about="render/lookdev.py SPEC as glTF 2.0 PBR values (linear baseColorFactor; clearcoat = "
               "KHR_materials_clearcoat, transmissionFactor = KHR_materials_transmission, ior = KHR_materials_ior). "
               "three.js MeshPhysicalMaterial: color = baseColorFactor[:3] (linear), metalness, roughness, "
               "clearcoat, clearcoatRoughness, ior, transmission (+ opacity = baseColorFactor[3] for BLEND). "
               "Metallic paints: glTF has no F82 tint, so metallicFactor is lower than Blender's (blender_metallic) "
               "to keep grazing reflections from going chrome; the clear coat carries the gloss. specularFactor = "
               "KHR_materials_specular (F0 scale; low for the base layer under a clear coat and the anti-glare "
               "mask). Not representable in glTF: the paint flake normals, and the interior lining that "
               "lookdev.apply() puts on the BACK faces of the paint materials (three.js: side=DoubleSide + "
               "an onBeforeCompile gl_FrontFacing switch, or a lining mesh in the model).",
        _model=dict(
            note="render-time changes in lookdev.apply() that belong in the model (model/assemble.py, "
                 "model/livery.py); the viewer can mirror them",
            reassign=[dict(parts=list(pp), from_material=a, to_material=b) for pp, a, b in REASSIGN],
            outline=dict(material=OUTLINE["material"], width_m=OUTLINE["width"],
                         rule=f"a ~{OUTLINE['width'] * 1000:.0f} mm paint_champagne stroke along every colour boundary "
                              "of the white pinstripes / swooshes (livery strokes), photos 82 / 130 / 188"),
            paint_navy="livery stroke N1 is the base blue on MSN 3008 (no navy line): paint_navy == paint_blue",
            back_faces="paint_* and trim_black / seal back faces render as the interior lining (LINING base "
                       f"{list(LINING['base'])}, roughness {LINING['rough']}; flight deck, model station x < "
                       f"{LINING['flight_deck']['x1']} m: base {list(LINING['flight_deck']['base'])}); exhaust_polished "
                       "back faces: render_back_faces (soot)",
            exhaust="the GLB 'black' primitives of exhaust_stacks (outlet band, inner wall, rim) render as "
                    "exhaust_soot; exhaust_polished: render_collar (station-dependent heat tint and black outlet "
                    "collar), render_polish (noise roughness / tint + bump)",
            tyre_grooves="tire: render_grooves = 4 circumferential tread grooves (6 mm) at +-0.1 / +-0.3 of the tread "
                         "width (tread = 0.62 x tyre width) on the crown; a bump in the renders (lookdev "
                         "_tyre_grooves); the model could cut them or the viewer use a normal map"),
        materials=gltf_table())
    Path(path).write_text(json.dumps(doc, indent=1))
    return path


# =============================================================================================================
# verification: patches, colour science
# =============================================================================================================
def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_lab(rgb):
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = np.asarray(rgb, float) @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


# Hand-picked patches (photo pixels of the full-size photo; the render is the same camera scaled) and material
# regions (the render's flat material-ID pass, eroded by 'erode' px of the render so a camera misfit does not
# cross an edge; the SAME pixels are averaged in photo and render).  'exclude': photo boxes with things the
# model does not have (people, stairs, logos, chocks).
VERIFY = {
    "hangar_port34": dict(
        photo="cand/pn_first-pc12-pro-hando_MSN-3008_130.webp", erode=5,
        patches=[("blue side A", "paint_blue", (700, 590, 760, 625)),
                 ("blue side B", "paint_blue", (870, 548, 925, 570)),
                 ("blue side C", "paint_blue", (980, 560, 1060, 600)),
                 ("white band", "paint_pinstripe", (720, 660, 900, 680)),
                 ("light blue nose", "paint_blue_light", (700, 700, 800, 730)),
                 ("mask below side win", "trim_black", (1060, 487, 1120, 497)),
                 ("blade upper", "prop_blade", (352, 285, 375, 335)),
                 ("red band", "prop_band_red", (355, 80, 390, 88)),
                 ("de-ice boot stbd", "deice_boot", (1550, 700, 1750, 712)),
                 ("wall (env)", None, (50, 300, 250, 500)),
                 ("ceiling (env)", None, (600, 30, 900, 150))],
        regions=["paint_blue", "paint_blue_light", "paint_pinstripe", "paint_navy", "paint_wing_dark", "trim_black",
                 "glass", "glass_cabin", "glass_windshield", "seal_cabin", "prop_blade", "prop_band_red", "tire",
                 "chrome", "exhaust_polished", "deice_boot", "jamb"],
        exclude=[(1300, 530, 1520, 960), (1180, 560, 1480, 1000), (1150, 960, 1920, 1090), (1060, 505, 1170, 560),
                 (640, 960, 920, 1040), (330, 190, 400, 280), (470, 360, 540, 420)]),
    "apron_stbd34": dict(
        photo="cand/pn_first-pc12-pro-hando_CL_IMG_0517.webp", erode=4,
        patches=[("blue nose side", "paint_blue", (1110, 670, 1200, 700)),
                 ("blue under cockpit", "paint_blue", (1000, 690, 1060, 715)),
                 ("blue crown (sky refl)", "paint_blue", (1150, 580, 1250, 600)),
                 ("mask below side win", "trim_black", (1005, 646, 1070, 652)),
                 ("side window", "glass", (1000, 620, 1040, 640)),
                 ("hangar door (env)", None, (700, 420, 900, 480)),
                 ("tarmac sun (env)", None, (700, 1100, 1000, 1200)),
                 ("tarmac shade (env)", None, (1450, 840, 1700, 860)),
                 ("gravel (env)", None, (50, 1100, 250, 1250)),
                 ("sky (env)", None, (50, 30, 300, 120))],
        regions=["paint_blue", "paint_blue_light", "paint_pinstripe", "paint_wing_dark", "trim_black", "glass",
                 "glass_cabin", "glass_windshield", "prop_blade", "chrome", "paint_white", "paint_silver",
                 "deice_boot"],
        exclude=[(1280, 800, 1400, 910), (760, 800, 900, 900), (990, 660, 1080, 695)]),
    "nose_port_closeup": dict(
        photo="cand/pn_first-pc12-pro-hando_MSN-3008_188.webp", erode=10,
        patches=[("blue side", "paint_blue", (680, 420, 760, 470)),
                 ("blue cowl side", "paint_blue", (320, 350, 420, 420)),
                 ("white band", "paint_pinstripe", (300, 690, 450, 705)),
                 ("mask below side win", "trim_black", (820, 387, 900, 398)),
                 ("mask aft of side win", "trim_black", (925, 330, 940, 390)),
                 ("nose tyre", "tire", (270, 1080, 330, 1200)),
                 ("tarmac sun (env)", None, (600, 1150, 900, 1280)),
                 ("tarmac shade (env)", None, (500, 880, 800, 950)),
                 ("sky (env)", None, (1000, 20, 1500, 120)),
                 ("mountains (env)", None, (1380, 450, 1420, 480))],
        regions=["paint_blue", "paint_blue_light", "paint_pinstripe", "trim_black", "glass", "glass_windshield",
                 "paint_wing_dark", "tire", "deice_boot", "jamb", "exhaust_polished"],
        exclude=[(1150, 470, 1500, 1250), (940, 640, 1300, 1060), (810, 400, 960, 480), (560, 770, 740, 840),
                 (780, 150, 960, 400)]),
    # air-to-air from below (sun on the camera side, undersides in shade): wing / belly navy, boots
    "air_below_left": dict(
        photo="cand/pn_first-pc12-pro-hando_PC-12-PRO-N81DW.webp", erode=3,
        patches=[("wing lower R", "paint_wing_dark", (1450, 450, 1550, 520)),
                 ("wing lower L", "paint_wing_dark", (700, 880, 850, 930)),
                 ("sky (env)", None, (200, 150, 500, 300))],
        regions=["paint_blue", "paint_blue_light", "paint_pinstripe", "paint_wing_dark", "paint_silver", "paint_white",
                 "glass_cabin", "deice_boot"],
        exclude=[(372, 385, 411, 411), (411, 428, 551, 490), (918, 778, 1076, 831)]),       # flag, N81DW, PC-12 PRO
    # golden hour from the right cockpit window: boot, pod radome, wing upper surface
    "wing_from_cabin": dict(
        photo="cand/pn_first-pc12-pro-hando_IMG_0459.webp", erode=4,
        patches=[("de-ice boot A", "deice_boot", (1880, 860, 1930, 890)),
                 ("de-ice boot B", "deice_boot", (1960, 990, 2020, 1010)),
                 ("pod radome", "paint_black", (1380, 540, 1480, 600)),
                 ("wing upper", "paint_blue", (2100, 850, 2250, 950))],
        regions=["paint_blue", "paint_black", "deice_boot", "paint_wing_dark", "paint_pinstripe"]),
}


def _id_codes(n):
    """index (1..215) <-> linear emission colour with levels 0, .2, .., 1 per channel (base-6 digits)."""
    return [tuple(((i // 36) % 6 / 5.0, (i // 6) % 6 / 5.0, (i % 6) / 5.0)) for i in range(n)]


def id_render(png):
    """Flat material-ID pass of the current scene/camera (after the beauty render; destroys the materials).
    Returns {material base name: index}."""
    import bpy
    sc = bpy.context.scene
    mats = list(bpy.data.materials)
    codes = _id_codes(len(mats) + 1)
    table = {}
    for i, m in enumerate(mats, start=1):
        nt, out = _reset(m)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*codes[i], 1.0)
        em.inputs["Strength"].default_value = 1.0
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        table.setdefault(_base_name(m.name), []).append(i)
    w = bpy.data.worlds.new("id_black")
    try:
        w.use_nodes = True
    except Exception:
        pass
    bgn = [n for n in w.node_tree.nodes if n.type == "BACKGROUND"]
    if bgn:
        bgn[0].inputs["Strength"].default_value = 0.0
    sc.world = w
    for o in sc.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    c = sc.cycles
    c.samples, c.use_adaptive_sampling, c.use_denoising = 1, False, False
    c.max_bounces = 0
    c.filter_width = 0.01
    sc.render.use_motion_blur = False
    sc.render.film_transparent = True
    vs = sc.view_settings
    vs.view_transform = "Standard"
    try:
        vs.look = "None"
        vs.use_white_balance = False
    except Exception:
        pass
    vs.exposure, vs.gamma = 0.0, 1.0
    ims = sc.render.image_settings
    ims.file_format, ims.color_mode, ims.color_depth = "PNG", "RGBA", "8"
    sc.render.filepath = str(png)
    bpy.ops.render.render(write_still=True)
    Path(str(png) + ".json").write_text(json.dumps(table))
    return table


def decode_ids(png):
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGBA")).astype(float) / 255.0
    lv = np.clip(np.rint(srgb_to_lin(a[..., :3]) * 5), 0, 5).astype(int)
    idx = lv[..., 0] * 36 + lv[..., 1] * 6 + lv[..., 2]
    idx[a[..., 3] < 0.5] = 0
    return idx


def _erode(mask, r):
    if r <= 0:
        return mask
    H, W = mask.shape
    S = np.pad(mask.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    y0 = np.clip(np.arange(H) - r, 0, H)
    y1 = np.clip(np.arange(H) + r + 1, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W)
    x1 = np.clip(np.arange(W) + r + 1, 0, W)
    tot = S[y1][:, x1] - S[y0][:, x1] - S[y1][:, x0] + S[y0][:, x0]
    full = (y1 - y0)[:, None] * (x1 - x0)[None, :]
    return mask & (tot == full) & (np.arange(H)[:, None] >= r) & (np.arange(H)[:, None] < H - r) \
        & (np.arange(W)[None, :] >= r) & (np.arange(W)[None, :] < W - r)


def _stats(img_lin, sel):
    px = img_lin[sel]
    if len(px) == 0:
        return None
    m = px.mean(0)
    return dict(lin=[round(float(v), 4) for v in m], lab=[round(float(v), 2) for v in lin_to_lab(m)],
                srgb=[int(round(255 * v)) for v in np.clip(
                    np.where(m <= 0.0031308, 12.92 * m, 1.055 * np.clip(m, 1e-9, None) ** (1 / 2.4) - 0.055), 0, 1)],
                n=int(len(px)))


def analyse(preset, render_png, id_png, table, out_json=None, sheet=None):
    """dE2000 of the patches / regions of VERIFY[preset] between the photo and the render."""
    from PIL import Image
    v = VERIFY[preset]
    ren = Image.open(render_png).convert("RGB")
    W, H = ren.size
    ph = Image.open(PHOTO_DIR / v["photo"]).convert("RGB")
    W0, H0 = ph.size
    sx, sy = W / W0, H / H0
    ph = ph.resize((W, H), Image.LANCZOS)
    R = srgb_to_lin(np.asarray(ren).astype(float) / 255.0)
    P = srgb_to_lin(np.asarray(ph).astype(float) / 255.0)
    ids = decode_ids(id_png)
    excl = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in v.get("exclude", []):
        excl[int(y0 * sy):int(math.ceil(y1 * sy)), int(x0 * sx):int(math.ceil(x1 * sx))] = True
    rows = []
    # white reference (in-image, known albedo ~0.85): the eroded white-paint regions, same pixels in both
    wm = _erode(np.isin(ids, sum((table.get(k, []) for k in v.get("white", ("paint_pinstripe", "paint_white"))),
                                 [])), v.get("erode", 4)) & ~excl
    white = (P[wm].mean(0), R[wm].mean(0)) if wm.sum() >= 30 else None

    def row(kind, label, mat, sel_p, sel_r, box=None, cover=None):
        a, b = _stats(P, sel_p), _stats(R, sel_r)
        d = round(de2000(a["lab"], b["lab"]), 1) if a and b else None
        dn = None
        if a and b and white is not None:
            # white-normalised (von Kries per channel, white -> 0.85): the material, without the preset's
            # exposure / white balance / lighting-level differences
            na = lin_to_lab(np.clip(np.asarray(a["lin"]) / white[0] * 0.85, 0, None))
            nb = lin_to_lab(np.clip(np.asarray(b["lin"]) / white[1] * 0.85, 0, None))
            dn = round(de2000(na, nb), 1)
        rows.append(dict(kind=kind, label=label, material=mat, photo=a, render=b, dE2000=d, dE2000_white_norm=dn,
                         box=box, coverage=cover))

    for label, mat, (x0, y0, x1, y1) in v["patches"]:
        bx = (int(x0 * sx), int(y0 * sy), max(int(x0 * sx) + 1, int(round(x1 * sx))),
              max(int(y0 * sy) + 1, int(round(y1 * sy))))
        sel = np.zeros((H, W), bool)
        sel[bx[1]:bx[3], bx[0]:bx[2]] = True
        cover = None
        if mat is not None:
            codes = table.get(mat, [])
            cover = round(float(np.isin(ids[sel], codes).mean()), 2)
        row("patch", label, mat, sel, sel, bx, cover)
    for mat in v["regions"]:
        codes = table.get(mat, [])
        m = _erode(np.isin(ids, codes), v.get("erode", 4)) & ~excl
        if m.sum() < 30:
            continue
        row("region", mat, mat, m, m, cover=int(m.sum()))
    res = dict(preset=preset, render=str(render_png), size=[W, H], rows=rows,
               white_ref=None if white is None else dict(photo=[round(float(x), 4) for x in white[0]],
                                                         render=[round(float(x), 4) for x in white[1]],
                                                         n=int(wm.sum())))
    if out_json:
        Path(out_json).write_text(json.dumps(res, indent=1))
    if sheet:
        _sheet(ph, ren, ids, rows, table, v, sheet, preset)
    return res


def render_regions(render_png, id_png, table, mats=None, erode=2, min_px=150, out_json=None):
    """Mean colour of each material's eroded region in a render without a reference photo (the hero): the
    tyre / blade / white stripe / glazing values the round-2 judge quoted (sRGB of the graded 8-bit PNG)."""
    from PIL import Image
    R = srgb_to_lin(np.asarray(Image.open(render_png).convert("RGB")).astype(float) / 255.0)
    ids = decode_ids(id_png)
    out = {}
    for mat in (mats or sorted(table)):
        m = _erode(np.isin(ids, table.get(mat, [])), erode)
        if m.sum() >= min_px:
            out[mat] = _stats(R, m)
    if out_json:
        Path(out_json).write_text(json.dumps(out, indent=1))
    return out


def _sheet(ph, ren, ids, rows, table, v, path, preset):
    from PIL import Image, ImageDraw, ImageFont
    W, H = ren.size
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except Exception:
        f = fb = ImageFont.load_default()
    pad, bar = 10, 34
    n = len(rows)
    rh = 26
    tab_h = rh * ((n + 1) // 2) + 40
    sheet = Image.new("RGB", (2 * W + 3 * pad, H + bar + 2 * pad + tab_h), (24, 25, 28))
    sheet.paste(ph, (pad, bar + pad))
    sheet.paste(ren, (2 * pad + W, bar + pad))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), f"PHOTO  {Path(v['photo']).name}", fill=(235, 235, 235), font=fb)
    d.text((2 * pad + W, 8), f"RENDER  {preset}  + render/lookdev.py", fill=(235, 235, 235), font=fb)
    for k, r in enumerate(rows):
        if r["box"]:
            x0, y0, x1, y1 = r["box"]
            for ox in (pad, 2 * pad + W):
                d.rectangle((ox + x0 - 1, bar + pad + y0 - 1, ox + x1, bar + pad + y1), outline=(255, 0, 255), width=2)
                d.text((ox + x0, bar + pad + y1 + 1), str(k + 1), fill=(255, 0, 255), font=f)
    y = H + bar + 2 * pad + 8
    colw = (2 * W + pad) // 2
    for k, r in enumerate(rows):
        cx = pad + (k % 2) * colw
        cy = y + (k // 2) * rh
        for j, s in enumerate((r["photo"], r["render"])):
            if s:
                d.rectangle((cx + j * 34, cy, cx + j * 34 + 30, cy + rh - 4), fill=tuple(s["srgb"]))
        cov = "" if r["coverage"] is None else (f" cov {r['coverage']}" if r["kind"] == "patch" else f" {r['coverage']} px")
        txt = (f"{k + 1 if r['box'] else '-'} {r['kind'][0]} {r['label'][:24]:24s} photo {r['photo']['srgb'] if r['photo'] else '-'}"
               f" render {r['render']['srgb'] if r['render'] else '-'}  dE {r['dE2000']} n{r['dE2000_white_norm']}{cov}")
        d.text((cx + 72, cy + 3), txt, fill=(230, 230, 230), font=f)
    LOOKDEV_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=90)


# =============================================================================================================
# CLI
# =============================================================================================================
def _have_bpy():
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def verify(names, glb, out_dir, size, samples, sets, sheet_dir=None):
    """Render the presets through render/beauty.py (materials by its lookdev hook), ID pass, analysis; sheets into
    sheet_dir (default refs/cache/overlays/lookdev/)."""
    sys.path.insert(0, str(ROOT))
    from render import beauty
    beauty.VQA_DIR = LOOKDEV_DIR / "vqa"                   # never overwrite the lead's compare images
    out_dir = Path(out_dir)
    results = {}

    def write_compare(name, render_png, info):
        idp = out_dir / f"{name}_id.png"
        table = id_render(idp)
        if name in VERIFY:
            sd = Path(sheet_dir) if sheet_dir else LOOKDEV_DIR
            sd.mkdir(parents=True, exist_ok=True)
            results[name] = analyse(name, render_png, idp, table, out_json=out_dir / f"{name}_patches.json",
                                    sheet=sd / f"{name}_lookdev.jpg")
            for r in results[name]["rows"]:
                print(f"   {r['kind']:6s} {r['label']:24s} photo {r['photo']['srgb'] if r['photo'] else '-'} "
                      f"render {r['render']['srgb'] if r['render'] else '-'} dE2000 {r['dE2000']} "
                      f"white-norm {r['dE2000_white_norm']} cov {r['coverage']}", flush=True)

    beauty.write_compare = write_compare
    finish = beauty.finish_png

    def finish_png(png, grade=None, white_bg=False):     # presets without a photo: ID pass + region means
        finish(png, grade, white_bg)
        name = Path(png).stem
        if name in beauty.PRESETS and not beauty.PRESETS[name].get("photo"):
            idp = out_dir / f"{name}_id.png"
            table = id_render(idp)
            results[name] = render_regions(png, idp, table, out_json=out_dir / f"{name}_regions.json")
            for mat, st in results[name].items():
                print(f"   region {mat:24s} render {st['srgb']} n {st['n']}", flush=True)

    beauty.finish_png = finish_png
    argv = ["--preset", ",".join(names), "--glb", str(glb), "--out", str(out_dir), "--size", size, "--compare"]
    if samples:
        argv += ["--samples", str(samples)]
    for s in sets:
        argv += ["--set", s]
    beauty.main(argv)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="write render/lookdev_materials.json")
    ap.add_argument("--verify", default=None, help="comma list of beauty presets to render + analyse")
    ap.add_argument("--glb", default=str(ROOT / "out" / "pc12.glb"))
    ap.add_argument("--out", default=str(ROOT / "out" / "tmp" / "lookdev"))
    ap.add_argument("--size", default="1200x800")
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--set", action="append", default=[], help="passed to render/beauty.py --set")
    ap.add_argument("--sheet-dir", default=None, help="where the photo | render sheets go (default "
                                                      "refs/cache/overlays/lookdev/; keep them in the git-ignored cache)")
    ap.add_argument("--analyse", nargs=3, metavar=("PRESET", "RENDER_PNG", "ID_PNG"),
                    help="re-run the analysis of an existing render + its ID pass (<ID_PNG>.json = id table)")
    a = ap.parse_args(argv)
    if a.json:
        print("wrote", write_json())
    if a.analyse:
        pr, rp, ip = a.analyse
        res = analyse(pr, rp, ip, json.loads(Path(ip + ".json").read_text()),
                      out_json=Path(a.out) / f"{pr}_patches.json", sheet=LOOKDEV_DIR / f"{pr}_lookdev.jpg")
        for r in res["rows"]:
            print(f"   {r['kind']:6s} {r['label']:24s} photo {r['photo']['srgb'] if r['photo'] else '-'} "
                  f"render {r['render']['srgb'] if r['render'] else '-'} dE2000 {r['dE2000']} "
                  f"white-norm {r['dE2000_white_norm']} cov {r['coverage']}")
    if a.verify:
        if not _have_bpy():
            return subprocess.call([BLENDER_PY, str(Path(__file__).resolve())] + (argv or sys.argv[1:]), cwd=str(ROOT))
        verify([n.strip() for n in a.verify.split(",") if n.strip()], a.glb, a.out, a.size, a.samples, a.set,
               a.sheet_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
