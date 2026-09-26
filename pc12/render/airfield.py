"""
render.airfield -- photo-matched OUTDOOR environments for the ground presets of render/beauty.py: an airport
apron in front of a white hangar (apron_stbd34, photo CL_IMG_0517) and an Alpine airfield (nose_port_closeup,
photo MSN-3008_188, Buochs-like).  Everything is procedural or CC0: no photo pixels reach a render.

It is applied through render/lookdev.py's environment patch (ENV['outdoor'] = SETTINGS, keyed by preset name):
beauty.build_env builds only the SKY (the preset copy gets env 'airfield', so no shadow catcher and no HDRI
ground), then build() adds the rest.  Per preset:
  sky       a clear-sky Poly Haven 'pure sky' HDRI (CC0) for the sky light and the reflections, rotated so its
            sun sits at the measured azimuth; its sun disc is CAPPED in the world shader (per-channel min with
            'cap') and its energy above the cap is handed to a sun lamp, so the lamp can sit at the measured
            elevation with crisp shadows (angle 0.53 deg) without a second sun in the sky.  strength = the
            preset's light level (the exposure knob: sun and sky scale together; beauty's preset exposure,
            white balance and grade are left alone).  light_sat / light_zenith shape the sky LIGHT (saturation;
            a darker zenith -> deeper ground shadows while vertical faces keep the horizon light); look =
            what CAMERA rays (and a 'glossy' fraction of glossy rays) see of the sky: a brighter, more saturated
            copy -- the phone / press JPEGs render the sky much brighter than the sunlit apron, which no
            physical sky does (0517: sky at el 7-11 deg sRGB 140-178/191-215/242, sunlit asphalt 150).
  sun       az / el (MODEL azimuth, 0 = toward +x / aft, 90 = toward +y / starboard, the direction TOWARD the
            sun), measured from the photo's shadows: shadow-catcher masks of the posed aircraft (+ the hangar for
            0517) through the fitted camera for a grid of directions (5 deg steps), scored by IoU against the
            photo's dark-ground mask.  0517: aircraft alone az -150 el 40 (IoU 0.44, a broad optimum -165..-140 /
            35..45); with the hangar's shadow band in front of its door (reaching y ~ -13 m, 17 m out from the
            14 m facade) az -135 el 30-35 (IoU 0.49) -> -135 / 33.  188: az -150 el 35 (IoU 0.62).  Both photos
            have the sun AHEAD-PORT: in 0517 the starboard flank and the hangar door face away from it (shade), in
            188 the port side facing the camera is SUNLIT (beauty's preset had the sun on the starboard side,
            az +108, the port side in shade; the lookdev judges then ran it at exposure +1.5).  gain scales the
            HDRI's sun energy, colour overrides it.
  ground    a large plane (+-extent m round the camera) with a procedural surface; zones (polygons: gravel, a dark
            sealed strip, grass) lie 0.8 mm steps above it, markings 2.5 mm above it (0.3 mm steps, so crossing
            strokes are never coplanar -- a coplanar pair shadows itself black), still below z = 0 (the tyre
            contact).  Surfaces are node shaders in WORLD metres (TexCoord Object of identity-transform objects):
              asphalt / concrete / gravel: albedo x (large 10-20 m mottling) x (mid noise) x (aggregate Voronoi
                cells with random value / tint and bright specks) x repair patches x stains x crack lines;
                roughness from the mid noise, bump from the aggregate cells
              grass: green / dry-yellow patches, blade noise, bump
              paint: the substrate surface mixed with the paint (Principled) by a wear mask, the aggregate showing
                through
              cladding: base x grooves / seams (bands along an axis) x a faint noise (hangar door, facades)
              skyline: unlit (emission) = the sky's horizon radiance x rel, lighter toward the ridge, noise
  markings  painted lines as strips (polylines with a width, optional double line: two strokes centre-spaced
            'double' m), closed / open ellipses, rectangles; positions from the photo's yellow pixels
            back-projected through the fitted camera onto z = 0 (0517: the taxi lead-in curve past the nose and
            the double edge line with its corner at (-0.37, 7.62); 188: the stand centre line (BL ~ -0.1) with
            its stop bar at STA 2.75, the stand glyphs at STA 3.6-6.2 / BL -3.6..-2.0, a drain grate)
  props     simple backdrop geometry: box (optionally a gable / mono-pitch roof), quad (a facade panel), cylinder,
            tree (three displaced ellipsoid lobes + trunk), placed from the photo through the fitted camera
            (0517: hangar facade plane y = -30.0 +- 0.7 m from the door bottom for x 19-26, roof edge 13.2-14.2 m,
            door top 10.2-11.0 m, left corner x = 57.5; 188: tower ~140 m, hangars ~210 / 260 m, trees ~110 m)
  skyline   a ring (radius R round the camera) whose top follows a profile of (azimuth, elevation) points
            (188: the mountain ridge traced from the photo through its camera, invented outside the photo;
            0517: a low blocky skyline of a flat airport) + noise
The per-preset dicts can be overridden for one run through beauty's --set: pre['airfield'] (deep-merged over
SETTINGS[preset], e.g. --set airfield.sun.az=-140 --set airfield.sky.strength=1.2), or --set airfield=false
(beauty's own environment: the race-track HDRI with its shadow catcher).

HDRIs (Poly Haven, CC0 1.0, https://polyhaven.com/license; downloaded by beauty.ensure_hdri into
refs/cache/hdri/ and listed in its SOURCES.txt):
  qwantani_mid_morning_puresky  clear mid-morning sky, sun 40 deg, sun / sky horizontal irradiance ~6 (a clear,
                                dry sky with a deep zenith): the Alpine airfield (188: shade sRGB 24-33)
  kloofendal_43d_clear_puresky  (already in beauty.HDRIS) clear sky, sun 43 deg, sun / sky 3.1, a bluer, brighter
                                sky light: the apron (0517: the shaded hangar door 128/154/179 ~ the sunlit
                                asphalt, the shaded flank 0/37/100)

Verification (python3 render/lookdev.py --verify ... --sheet-dir refs/cache/overlays/env/<run>; numbers in the
lookdev docstring and the commit message).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

SKIES = {
    "qwantani_mid_morning_puresky": dict(res="4k", note="clear mid-morning sky, sun el 40 deg (Alpine airfield)"),
    "kloofendal_43d_clear_puresky": dict(res="4k", note="clear deep-blue sky, sun el 43 deg (apron, air-to-air)"),
}


# =============================================================================================================
# surfaces (linear albedo)
# =============================================================================================================
ASPHALT = dict(kind="asphalt", base=(0.180, 0.163, 0.140),
               large=(0.07, 0.10),              # (scale 1/m, amplitude): 10-20 m mottling
               mid=(0.9, 0.06),                 # 1 m variation
               agg=dict(scale=55.0, amp=0.22, tint=0.06, speck=0.04, speck_gain=1.8),
               patches=dict(scale=0.11, fraction=0.22, dark=0.86),
               stains=dict(scale=0.25, thr=0.62, dark=0.25),
               cracks=dict(scale=0.12, width=0.006, dark=0.45, density=0.45),
               rough=(0.72, 0.92), spec=0.35, bump=(0.30, 0.004))
# yellow marking paint: photo 0517 / 188 sunlit line pixels sRGB 247/229/163 and 250/237/193 (pale, near clipping)
PAINT_YELLOW = dict(kind="paint", base=(0.80, 0.60, 0.10), rough=0.55, spec=0.45, wear=(0.12, 1.6),
                    substrate="asphalt", agg_show=0.25)
GRASS = dict(kind="grass", base=(0.085, 0.110, 0.012), dry=(0.16, 0.15, 0.045), patch=(0.08, 0.35),
             blade=(18.0, 0.35), rough=0.9, spec=0.25, bump=(0.4, 0.01))

SETTINGS = {
    # ---------------------------------------------------------------------------------------------------------
    # CL_IMG_0517: apron in front of a large white hangar, grey asphalt, yellow taxi lines, gravel beyond the
    # double edge line, a dark office building aft of the hangar, a light mast, blue sky.  Camera livery
    # cams.json 'stbd_ground' (rms 7 px, hfov 29 deg: the visible sky is at el 5-12 deg).  Photo references
    # (sRGB): sunlit asphalt 148-157 (lin 0.29-0.34), shadow in front of the door 29/40/53, gravel 173/169/159,
    # shaded hangar door 127/152/177, sky 140/191/242 (el 11) .. 178/215/244 (el 7).
    # ---------------------------------------------------------------------------------------------------------
    "apron_stbd34": dict(
        sky=dict(hdri="kloofendal_43d_clear_puresky", strength=1.22, cap=40.0,
                 light_sat=0.75, light_zenith=(20.0, 0.45),
                 look=dict(sat=1.5, val=1.0, gain=2.9, horizon=(15.0, 1.25), glossy=0.5)),
        sun=dict(az=-135.0, el=33.0, gain=1.0, angle=0.53),
        ground=dict(extent=2500.0, surface="asphalt"),
        surfaces=dict(
            asphalt=ASPHALT,
            asphalt_dark=dict(ASPHALT, base=(0.085, 0.087, 0.088), stains=dict(scale=0.25, thr=0.7, dark=0.15)),
            gravel=dict(ASPHALT, base=(0.33, 0.30, 0.255), large=(0.15, 0.08), mid=(1.5, 0.08),
                        agg=dict(scale=22.0, amp=0.45, tint=0.12, speck=0.10, speck_gain=1.6), patches=None,
                        stains=dict(scale=0.4, thr=0.7, dark=0.2), cracks=None, rough=(0.85, 0.97),
                        bump=(0.8, 0.012)),
            paint_yellow=PAINT_YELLOW,
            door=dict(kind="cladding", base=(0.82, 0.83, 0.84), rough=0.25, spec=0.7,
                      grooves=dict(axis=(0, 0, 1), pitch=0.61, width=0.025, dark=0.55),
                      seams=dict(axis=(1, 0, 0), pitch=12.3, offset=4.0, width=0.08, dark=0.6)),
            cladding_white=dict(kind="cladding", base=(0.80, 0.81, 0.81), rough=0.25, spec=0.7,
                                grooves=dict(axis=(0, 0, 1), pitch=1.0, width=0.015, dark=0.75)),
            cladding_grey=dict(kind="cladding", base=(0.46, 0.47, 0.48), rough=0.6, spec=0.3,
                               grooves=dict(axis=(0, 0, 1), pitch=1.0, width=0.02, dark=0.8)),
            trim_dark=dict(kind="diffuse", base=(0.035, 0.037, 0.04), rough=0.5, spec=0.4),
            office=dict(kind="cladding", base=(0.025, 0.03, 0.035), rough=0.45, spec=0.35,       # glazing
                        grooves=dict(axis=(0, 0, 1), pitch=3.4, width=0.9, dark=3.0),           # floor slabs
                        seams=dict(axis=(1, 0, 0), pitch=1.8, width=0.12, dark=3.5)),           # mullions
            mast=dict(kind="diffuse", base=(0.30, 0.30, 0.30), rough=0.4, spec=0.5, metallic=0.6),
            skyline=dict(kind="skyline", rel=(0.50, 0.53, 0.58), top=(0.60, 0.63, 0.68), noise=(0.02, 0.25)),
        ),
        zones=[
            # gravel beyond the double edge line (outer edge of the double line, the wedge away from the aircraft)
            dict(surface="gravel", poly=((40.06, 0.84), (-0.11, 8.14), (-19.8, 25.32), (-20.0, 60.0), (40.0, 60.0))),
            # dark strip in front of the hangar door
            dict(surface="asphalt_dark", poly=((-20.0, -30.0), (60.0, -30.0), (60.0, -14.0), (-20.0, -12.5))),
        ],
        markings=[
            # taxi lead-in line: from far aft along the port side, under the nose, curving to starboard-forward
            dict(surface="paint_yellow", width=0.15,
                 pts=((70.0, -14.0), (40.0, -9.0), (18.6, -5.8), (8.0, -2.55), (3.2, -0.8), (1.78, -0.02),
                      (0.18, 1.03), (-1.29, 2.06), (-3.02, 3.57), (-5.21, 5.63), (-9.0, 9.4), (-16.0, 16.8),
                      (-40.0, 43.0))),
            # double edge line (two 0.15 m strokes, centres 0.30 m apart) with its corner at (-0.37, 7.62)
            dict(surface="paint_yellow", width=0.15, double=0.30,
                 pts=((40.0, 1.35), (11.0, 5.38), (1.03, 7.34), (-0.37, 7.62), (-1.25, 8.40), (-5.79, 12.44),
                      (-20.0, 25.1))),
        ],
        props=[
            # hangar: body, door (sectional panels, leaves 12.3 m), upper cladding, coping, dark corner column
            dict(kind="box", surface="cladding_grey", x=(-15.0, 57.5), y=(-80.0, -30.0), z=(0.0, 14.0)),
            dict(kind="quad", surface="door", p0=(-15.0, -29.97), p1=(55.5, -29.97), z=(0.0, 10.8)),
            dict(kind="quad", surface="cladding_white", p0=(-15.0, -29.97), p1=(57.5, -29.97), z=(10.8, 13.75)),
            dict(kind="box", surface="trim_dark", x=(-15.0, 57.6), y=(-30.25, -29.9), z=(10.7, 10.9)),
            dict(kind="box", surface="trim_dark", x=(-15.0, 57.7), y=(-30.3, -29.85), z=(13.75, 14.2)),
            dict(kind="box", surface="trim_dark", x=(55.5, 59.0), y=(-31.0, -29.8), z=(0.0, 14.2)),
            # floodlights on the upper facade
            *[dict(kind="box", surface="trim_dark", x=(xc - 0.25, xc + 0.25), y=(-29.9, -29.4), z=(10.6, 11.2))
              for xc in (48.9, 42.2, 28.1, 20.8)],
            # dark office building aft of the hangar (top edge back-projects to z 10-13.5 on y = -38), a light
            # mast and a lamp post
            dict(kind="box", surface="office", x=(62.0, 125.0), y=(-75.0, -38.0), z=(0.0, 12.5)),
            dict(kind="cylinder", surface="mast", centre=(118.0, -62.0), radius=0.35, z=(0.0, 36.0)),
            dict(kind="cylinder", surface="mast", centre=(120.0, -60.5), radius=0.10, z=(0.0, 9.0)),
        ],
        # distant low skyline (buildings / trees of a flat airport): blocky, 0.2-1.6 deg
        skyline=dict(surface="skyline", radius=900.0, seed=5, blocky=(3.0, 9.0),
                     profile=((-180.0, 0.9), (-120.0, 1.3), (-60.0, 0.7), (0.0, 1.1), (60.0, 1.6), (120.0, 0.9)),
                     noise=0.5),
    ),
    # ---------------------------------------------------------------------------------------------------------
    # MSN-3008_188: Alpine airfield (Buochs-like): light, warm concrete-coloured apron with the stand's yellow
    # centre line / stop bar / glyphs, a drain grate, grass beyond, a lattice control tower, two hangars (light
    # roof + facade, a dark hall behind), trees, a hut, the mountain ridge.  Camera cams_beauty.json 'nose_188'
    # (rms 36 px; its horizon runs ~3.7 deg off the photo's, so props stand on the RENDER's ground with their
    # tops at the photo's rows).  Photo references (sRGB): sunlit apron 176-199 (lin 0.35-0.56, R/B ~1.25),
    # shade 24-40, grass 129-139/137-151/54-65, mountains 0.40-0.55 x the sky just above the ridge
    # (187/208/233), trees 53/53/33, hangar roof 219, facade 195/201/203.
    # ---------------------------------------------------------------------------------------------------------
    "nose_port_closeup": dict(
        sky=dict(hdri="qwantani_mid_morning_puresky", strength=1.05, cap=40.0,
                 light_sat=0.75, light_zenith=(20.0, 0.45),
                 look=dict(sat=1.35, val=1.0, gain=3.3, horizon=(12.0, 1.2), glossy=0.35)),
        sun=dict(az=-150.0, el=35.0, gain=1.0, angle=0.53),
        ground=dict(extent=2500.0, surface="apron"),
        surfaces=dict(
            apron=dict(ASPHALT, base=(0.36, 0.34, 0.29), large=(0.06, 0.08), mid=(0.8, 0.05),
                       agg=dict(scale=70.0, amp=0.20, tint=0.05, speck=0.05, speck_gain=1.5),
                       patches=dict(scale=0.09, fraction=0.15, dark=0.9),
                       stains=dict(scale=0.3, thr=0.64, dark=0.35),
                       cracks=dict(scale=0.10, width=0.005, dark=0.5, density=0.4), bump=(0.25, 0.003)),
            paint_yellow=dict(PAINT_YELLOW, substrate="apron"),
            grate=dict(kind="cladding", base=(0.05, 0.05, 0.05), rough=0.55, spec=0.5, metallic=0.4,
                       grooves=dict(axis=(0, 1, 0), pitch=0.04, width=0.022, dark=0.15)),
            grass=GRASS,
            tower=dict(kind="diffuse", base=(0.36, 0.38, 0.38), rough=0.6, spec=0.4),
            tower_glass=dict(kind="diffuse", base=(0.03, 0.035, 0.04), rough=0.15, spec=0.6),
            roof_light=dict(kind="diffuse", base=(0.52, 0.52, 0.51), rough=0.6, spec=0.3),
            facade_light=dict(kind="cladding", base=(0.38, 0.40, 0.41), rough=0.6, spec=0.3,
                              grooves=dict(axis=(0, 0, 1), pitch=1.2, width=0.03, dark=0.8),
                              seams=dict(axis=(0, 1, 0), pitch=9.5, offset=0.0, width=0.25, dark=0.6)),
            roof_dark=dict(kind="diffuse", base=(0.19, 0.19, 0.18), rough=0.7, spec=0.3),
            ochre=dict(kind="cladding", base=(0.30, 0.25, 0.18), rough=0.8, spec=0.3,
                       grooves=dict(axis=(0, 0, 1), pitch=3.0, width=1.1, dark=0.35)),
            hut=dict(kind="diffuse", base=(0.30, 0.34, 0.29), rough=0.7, spec=0.3),
            mast=dict(kind="diffuse", base=(0.5, 0.5, 0.5), rough=0.4, spec=0.5),
            foliage=dict(kind="foliage", base=(0.030, 0.033, 0.013), var=0.5, rough=0.85),
            trunk=dict(kind="diffuse", base=(0.06, 0.05, 0.04), rough=0.9, spec=0.2),
            mountain=dict(kind="skyline", rel=(0.47, 0.53, 0.71), top=(0.62, 0.66, 0.80), noise=(0.004, 0.30),
                          green=(0.85, 1.0, 0.75)),
        ),
        zones=[
            # grass island on the port side past the wing, the airfield grass beyond the apron / taxiway
            dict(surface="grass", poly=((14.0, -7.3), (33.0, -8.3), (36.0, -12.0), (36.0, -80.0), (14.0, -80.0))),
            dict(surface="grass", poly=((55.0, -6.0), (700.0, -6.0), (700.0, -700.0), (55.0, -700.0))),
            dict(surface="grass", poly=((55.0, 26.0), (700.0, 26.0), (700.0, 700.0), (55.0, 700.0))),
        ],
        markings=[
            dict(surface="paint_yellow", width=0.15,
                 pts=((2.66, -0.10), (6.5, -0.06), (11.7, 0.22), (16.0, 0.31), (60.0, 1.3))),
            dict(surface="paint_yellow", width=0.15, pts=((2.75, -0.75), (2.75, 0.55))),              # stop bar
            # stand glyphs (partly in the photographer's shadow): a stroke, an oval, a 'P'
            dict(surface="paint_yellow", width=0.18, pts=((3.6, -3.50), (6.15, -3.60))),
            dict(surface="paint_yellow", width=0.16, ellipse=((5.03, -2.83), (1.02, 0.22))),
            dict(surface="paint_yellow", width=0.16, pts=((3.6, -2.40), (6.05, -2.40))),
            dict(surface="paint_yellow", width=0.16, ellipse=((4.2, -2.40), (0.6, 0.33)), arc=(180.0, 0.0)),
            dict(surface="grate", rect=((11.46, -3.45), (0.36, 0.95), 0.0)),
        ],
        props=[
            # lattice control tower ~140 m aft (az +4.6 deg): shaft, cab with a glazing band, roof, antennas
            dict(kind="box", surface="tower", x=(138.2, 141.8), y=(7.9, 11.5), z=(0.0, 17.2)),
            dict(kind="box", surface="tower", x=(136.5, 143.5), y=(6.7, 13.6), z=(17.2, 18.6)),
            dict(kind="box", surface="tower_glass", x=(136.9, 143.1), y=(7.1, 13.2), z=(18.6, 20.8)),
            dict(kind="box", surface="tower", x=(136.3, 143.7), y=(6.5, 13.8), z=(20.8, 21.5)),
            dict(kind="cylinder", surface="tower", centre=(139.0, 9.5), radius=0.12, z=(21.5, 24.3)),
            dict(kind="cylinder", surface="tower", centre=(141.0, 11.0), radius=0.10, z=(21.5, 23.6)),
            # hangar with a light mono-pitch roof rising away from the camera, door facade, ~210 m
            dict(kind="box", surface="facade_light", x=(205.0, 235.0), y=(-40.0, 12.5), z=(0.0, 9.0),
                 roof=dict(kind="mono", axis="x", z1=15.0, surface="roof_light")),
            # the dark hall behind it (gable ridge along y), ~260 m
            dict(kind="box", surface="roof_dark", x=(240.0, 290.0), y=(-56.0, 4.5), z=(0.0, 15.0),
                 roof=dict(kind="gable", axis="y", z1=27.0, surface="roof_dark")),
            # ochre office building, hut, flag pole
            dict(kind="box", surface="ochre", x=(145.0, 160.0), y=(-41.0, -30.0), z=(0.0, 13.3)),
            dict(kind="box", surface="hut", x=(86.0, 89.0), y=(-27.8, -25.0), z=(0.0, 7.0)),
            dict(kind="cylinder", surface="mast", centre=(91.6, -29.2), radius=0.06, z=(0.0, 13.0)),
            # trees ~110 m (crowns to z ~19)
            dict(kind="tree", centre=(107.0, -25.8), crown=((0.0, 0.0, 12.5), (6.5, 6.5, 7.0)), trunk=(0.4, 6.0),
                 surface="foliage", trunk_surface="trunk", seed=1),
            dict(kind="tree", centre=(106.5, -30.8), crown=((0.0, 0.0, 12.0), (5.5, 5.5, 6.5)), trunk=(0.35, 6.0),
                 surface="foliage", trunk_surface="trunk", seed=2),
            dict(kind="tree", centre=(110.0, -35.5), crown=((0.0, 0.0, 11.0), (6.0, 6.0, 6.5)), trunk=(0.35, 5.0),
                 surface="foliage", trunk_surface="trunk", seed=3),
            dict(kind="tree", centre=(118.0, -41.0), crown=((0.0, 0.0, 12.0), (6.0, 6.0, 7.0)), trunk=(0.35, 5.0),
                 surface="foliage", trunk_surface="trunk", seed=4),
        ],
        # mountain ridge ~7 km: traced from photo 188 through its camera (az -13.3 .. +9.1 deg and the left slope at
        # az 52.7 .. 56.5 deg), invented elsewhere (a valley ringed by 1-2 km peaks, lower toward the lake / north)
        skyline=dict(surface="mountain", radius=7000.0, seed=11, noise=0.35,
                     profile=((-17.0, 6.6), (-15.0, 6.9), (-13.26, 7.43), (-12.59, 8.15), (-11.93, 8.52),
                              (-11.33, 7.98), (-10.56, 7.43), (-9.71, 7.81), (-8.66, 8.56), (-7.41, 9.32),
                              (-6.59, 8.57), (-5.59, 7.72), (-4.72, 7.2), (-1.91, 7.83), (0.04, 8.32), (2.03, 8.81),
                              (4.05, 9.05), (6.11, 9.29), (7.79, 9.57), (9.06, 9.73), (15.0, 10.5), (25.0, 9.0),
                              (35.0, 10.5), (45.0, 11.5), (52.72, 12.0), (54.81, 12.2), (56.52, 12.43), (65.0, 11.0),
                              (80.0, 13.5), (100.0, 9.0), (120.0, 11.0), (140.0, 6.0), (160.0, 3.5), (180.0, 2.5),
                              (-160.0, 3.0), (-140.0, 5.5), (-120.0, 9.5), (-100.0, 12.0), (-80.0, 10.0),
                              (-60.0, 8.0), (-40.0, 6.0), (-25.0, 6.5))),
    ),
}


def _deep_merge(a, b):
    """a with b merged in recursively (render/lookdev.py merges pre['airfield'] over SETTINGS[preset])."""
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


# =============================================================================================================
# sky: registration, analysis (energy above the cap -> the sun lamp), the world shader edits
# =============================================================================================================
def register_skies(B):
    """Make beauty.ensure_hdri fetch our skies at their resolution (it defaults to 2k for unknown ids)."""
    for k, v in SKIES.items():
        B.HDRIS.setdefault(k, dict(v))


def sky_stats(path, cap):
    """Energy of the HDRI above 'cap' (the sun disc: normal irradiance per channel, treated as a point source) and
    what stays: horizontal irradiance of the capped sky, the mean horizon radiance (el 1-6 deg), the zenith.
    Cached next to the HDRI (<file>.airfield.json, keyed by cap)."""
    path = Path(path)
    cache = Path(str(path) + ".airfield.json")
    key = f"cap{float(cap):g}"
    try:
        d = json.loads(cache.read_text())
        if key in d:
            return d[key]
    except Exception:
        d = {}
    import bpy
    img = bpy.data.images.load(str(path), check_existing=True)
    W, H = img.size
    px = np.empty(W * H * 4, np.float32)
    img.pixels.foreach_get(px)
    rgb = px.reshape(H, W, 4)[..., :3].astype(np.float64)                  # row 0 = bottom
    el = (np.arange(H) + 0.5) / H * math.pi - math.pi / 2
    dw = (np.cos(el) * (math.pi / H) * (2 * math.pi / W))[:, None, None]
    above = np.clip(rgb - cap, 0.0, None)
    capped = np.minimum(rgb, cap)
    up = (el > 0)[:, None, None]
    En = (above * dw).sum((0, 1))
    Eh_sky = (capped * dw * np.sin(el)[:, None, None] * up).sum((0, 1))
    hz = (el > math.radians(1)) & (el < math.radians(6))
    horizon = capped[hz].reshape(-1, 3).mean(0)
    zen = capped[el > math.radians(80)].reshape(-1, 3).mean(0)
    res = dict(En_sun=[float(v) for v in En], Eh_sky=[float(v) for v in Eh_sky],
               horizon=[float(v) for v in horizon], zenith=[float(v) for v in zen], cap=float(cap), size=[W, H])
    d[key] = res
    try:
        cache.write_text(json.dumps(d, indent=1))
    except Exception:
        pass
    return res


def _dir_z(nt):
    """Z of the normalised environment lookup direction (after beauty's Mapping node)."""
    mp = next(n for n in nt.nodes if n.type == "MAPPING")
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(mp.outputs["Vector"], nrm.inputs[0])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(nrm.outputs["Vector"], sep.inputs[0])
    return sep.outputs["Z"]


def _ramp_el(nt, z, el0, el1, v0, v1):
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = math.sin(math.radians(el0))
    mr.inputs["From Max"].default_value = math.sin(math.radians(el1))
    mr.inputs["To Min"].default_value = float(v0)
    mr.inputs["To Max"].default_value = float(v1)
    nt.links.new(z, mr.inputs["Value"])
    return mr.outputs["Result"]


def _scale(nt, col, f):
    vm = nt.nodes.new("ShaderNodeVectorMath")
    vm.operation = "SCALE"
    nt.links.new(col, vm.inputs[0])
    if isinstance(f, (int, float)):
        vm.inputs["Scale"].default_value = float(f)
    else:
        nt.links.new(f, vm.inputs["Scale"])
    return vm.outputs["Vector"]


def _sky_world(S, sky):
    """Edit the world beauty.build_env made from the HDRI: cap the sun disc (min(env, cap) after the environment
    texture); sky['light_sat'] sets the saturation of the sky LIGHT, sky['light_zenith'] = (el_deg, gain) scales
    it smoothly from 1 at el_deg to gain at the zenith (a darker zenith: deeper ground shadows while vertical
    faces keep the horizon light); with sky['look'] = dict(sat, val, gain, horizon=(el_deg, gain at the
    horizon), glossy=fraction) CAMERA rays (and glossy rays, blended by 'glossy') see a graded copy of the capped
    sky: the photo's sky and its reflections in the paint are brighter and more saturated than the sky light
    that sets the shading (a phone / press JPEG renders the sky that way)."""
    w = S.sc.world
    nt = w.node_tree
    env = next((n for n in nt.nodes if n.type == "TEX_ENVIRONMENT"), None)
    if env is None:
        return dict(capped=False)
    cap = float(sky.get("cap", 40.0))
    links = [lk.to_socket for lk in nt.links if lk.from_node == env and lk.from_socket.name == "Color"]
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.blend_type = "DARKEN"
    _sock(mx.inputs, "Factor", "VALUE").default_value = 1.0
    nt.links.new(env.outputs["Color"], _sock(mx.inputs, "A", "RGBA"))
    _sock(mx.inputs, "B", "RGBA").default_value = (cap, cap, cap, 1.0)
    capped = _sock(mx.outputs, "Result", "RGBA")
    light = capped
    if sky.get("light_sat") is not None:                         # saturation of the sky LIGHT (diffuse fill)
        hl = nt.nodes.new("ShaderNodeHueSaturation")
        hl.inputs["Saturation"].default_value = float(sky["light_sat"])
        nt.links.new(capped, hl.inputs["Color"])
        light = hl.outputs["Color"]
    lz = sky.get("light_zenith")                                 # (el_deg, gain): sky LIGHT gain toward the zenith
    if lz:
        light = _scale(nt, light, _ramp_el(nt, _dir_z(nt), float(lz[0]), 90.0, 1.0, float(lz[1])))
    for s_ in links:
        nt.links.new(light, s_)
    res = dict(capped=True, cap=cap, light_sat=sky.get("light_sat"), light_zenith=lz)
    look = sky.get("look")
    if not look:
        return res
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    final = out.inputs["Surface"].links[0].from_socket
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = float(look.get("sat", 1.0))
    hsv.inputs["Value"].default_value = float(look.get("val", 1.0))
    hsv.inputs["Hue"].default_value = float(look.get("hue", 0.5))
    nt.links.new(capped, hsv.inputs["Color"])
    col = _scale(nt, hsv.outputs["Color"], float(look.get("gain", 1.0)))
    hz = look.get("horizon")                                     # (el_deg, gain at the horizon)
    if hz:
        col = _scale(nt, col, _ramp_el(nt, _dir_z(nt), 0.0, float(hz[0]), float(hz[1]), 1.0))
    bg2 = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(col, bg2.inputs["Color"])
    bg2.inputs["Strength"].default_value = float(sky.get("strength", 1.0))
    lp = nt.nodes.new("ShaderNodeLightPath")
    fac = lp.outputs["Is Camera Ray"]
    g = float(look.get("glossy", 1.0))
    if g > 0.0:                                                  # glossy rays: this fraction of the look
        gm = nt.nodes.new("ShaderNodeMath")
        gm.operation = "MULTIPLY"
        nt.links.new(lp.outputs["Is Glossy Ray"], gm.inputs[0])
        gm.inputs[1].default_value = g
        mxf = nt.nodes.new("ShaderNodeMath")
        mxf.operation = "MAXIMUM"
        nt.links.new(lp.outputs["Is Camera Ray"], mxf.inputs[0])
        nt.links.new(gm.outputs[0], mxf.inputs[1])
        fac = mxf.outputs[0]
    ms = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fac, ms.inputs[0])
    nt.links.new(final, ms.inputs[1])
    nt.links.new(bg2.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs["Surface"])
    res["look"] = dict(look)
    return res


def _sun_lamp(S, cfg, stats, strength):
    import bpy
    from mathutils import Vector
    az, el = math.radians(cfg["az"]), math.radians(cfg["el"])
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    En = np.asarray(stats["En_sun"]) * strength * cfg.get("gain", 1.0)
    col = np.asarray(cfg["colour"], float) if cfg.get("colour") else En / max(En.max(), 1e-9)
    power = float(cfg["strength"]) if cfg.get("strength") else float(En.max())
    ld = bpy.data.lights.new("airfield_sun", "SUN")
    ld.energy = power
    ld.color = tuple(float(c) for c in col)
    ld.angle = math.radians(cfg.get("angle", 0.53))
    lo = bpy.data.objects.new("airfield_sun", ld)
    S.sc.collection.objects.link(lo)
    lo.rotation_mode = "QUATERNION"
    lo.rotation_quaternion = Vector(tuple(-d)).to_track_quat("-Z", "Y")
    return dict(az=cfg["az"], el=cfg["el"], dir_model=d.round(4).tolist(), strength=round(power, 3),
                colour=[round(float(c), 3) for c in col], angle_deg=cfg.get("angle", 0.53))


# =============================================================================================================
# node helpers
# =============================================================================================================
def _sock(coll, name, typ):
    return next(x for x in coll if x.name == name and x.type == typ)


class _T:
    """Small node-tree builder for a material (world-metre coordinates: TexCoord Object)."""

    def __init__(self, m):
        try:
            m.use_nodes = True
        except Exception:
            pass
        self.nt = m.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.tc = self.nt.nodes.new("ShaderNodeTexCoord")
        self.vec = self.tc.outputs["Object"]

    def link(self, a, b):
        self.nt.links.new(a, b)

    def _in(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = float(v)
        elif isinstance(v, tuple):
            v = tuple(float(c) for c in v)
            sock.default_value = (*v, 1.0) if (len(v) == 3 and sock.type == "RGBA") else v
        else:
            self.link(v, sock)

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for k, v in enumerate((a, b, c)):
            if v is not None:
                self._in(n.inputs[k], v)
        return n.outputs[0]

    def noise(self, scale, detail=2.0, rough=0.5, vec=None, distortion=0.0):
        n = self.nt.nodes.new("ShaderNodeTexNoise")
        try:
            n.noise_dimensions = "3D"
        except Exception:
            pass
        self.link(vec if vec is not None else self.vec, n.inputs["Vector"])
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distortion
        return n.outputs["Fac"]

    def voronoi(self, scale, vec=None, randomness=1.0):
        n = self.nt.nodes.new("ShaderNodeTexVoronoi")
        n.feature = "F1"
        self.link(vec if vec is not None else self.vec, n.inputs["Vector"])
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = randomness
        sep = self.nt.nodes.new("ShaderNodeSeparateColor")
        self.link(n.outputs["Color"], sep.inputs["Color"])
        return n.outputs["Distance"], n.outputs["Color"], sep.outputs[0], sep.outputs[1]

    def mrange(self, v, a, b, lo=0.0, hi=1.0, smooth=False):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        if smooth:
            n.interpolation_type = "SMOOTHSTEP"
        self._in(n.inputs["Value"], v)
        n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
        n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = lo, hi
        return n.outputs["Result"]

    def mixc(self, fac, A, B, blend="MIX"):
        mx = self.nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = blend
        self._in(_sock(mx.inputs, "Factor", "VALUE"), fac)
        self._in(_sock(mx.inputs, "A", "RGBA"), A)
        self._in(_sock(mx.inputs, "B", "RGBA"), B)
        return _sock(mx.outputs, "Result", "RGBA")

    def scale_rgb(self, col, f):
        """colour x scalar factor (socket or number)."""
        vm = self.nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "SCALE"
        self._in(vm.inputs[0], col)
        self._in(vm.inputs["Scale"], f)
        return vm.outputs["Vector"]

    def dot(self, axis, vec=None):
        vm = self.nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "DOT_PRODUCT"
        self.link(vec if vec is not None else self.vec, vm.inputs[0])
        vm.inputs[1].default_value = tuple(float(a) for a in axis)
        return vm.outputs["Value"]

    def bsdf(self, base, rough, spec=0.5, metallic=0.0, normal=None):
        b = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self._in(b.inputs["Base Color"], base)
        self._in(b.inputs["Roughness"], rough)
        b.inputs["Specular IOR Level"].default_value = spec
        b.inputs["Metallic"].default_value = metallic
        if normal is not None:
            self.link(normal, b.inputs["Normal"])
        return b.outputs["BSDF"]

    def bump(self, height, strength, distance):
        n = self.nt.nodes.new("ShaderNodeBump")
        n.inputs["Strength"].default_value = strength
        n.inputs["Distance"].default_value = distance
        self.link(height, n.inputs["Height"])
        return n.outputs["Normal"]

    def emit(self, col, strength=1.0):
        n = self.nt.nodes.new("ShaderNodeEmission")
        self._in(n.inputs["Color"], col)
        n.inputs["Strength"].default_value = strength
        return n.outputs["Emission"]

    def finish(self, shader):
        self.link(shader, self.out.inputs["Surface"])


# =============================================================================================================
# surfaces
# =============================================================================================================
def _pavement(T, p):
    """Asphalt / concrete / gravel: (colour socket, roughness socket, normal socket, aggregate-value socket)."""
    sc, amp = p.get("large", (0.07, 0.1))
    f = T.math("MULTIPLY_ADD", T.noise(sc, 3.0, 0.5), 2 * amp, 1.0 - amp)
    sc, amp = p.get("mid", (0.9, 0.06))
    nm = T.noise(sc, 3.0, 0.55)
    f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", nm, 2 * amp, 1.0 - amp))
    ag = p.get("agg") or {}
    dist, colr, r0, r1 = T.voronoi(ag.get("scale", 55.0))
    a = ag.get("amp", 0.2)
    f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", r0, 2 * a, 1.0 - a))
    if ag.get("speck"):
        sp = T.math("GREATER_THAN", r1, 1.0 - ag["speck"])
        f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", sp, ag.get("speck_gain", 1.8) - 1.0, 1.0))
    pt = p.get("patches")                     # repair patches: irregular ~1/scale m cells, a fraction darker
    if pt:
        _, _, pr, _ = T.voronoi(pt["scale"], randomness=0.85)
        pm = T.math("GREATER_THAN", pr, 1.0 - pt["fraction"])
        f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", pm, pt["dark"] - 1.0, 1.0))
    st = p.get("stains")
    if st:
        ns = T.noise(st["scale"], 3.0, 0.6)
        m = T.mrange(ns, st["thr"], st["thr"] + 0.08, 0.0, 1.0, smooth=True)
        f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", m, -st["dark"], 1.0))
    cr = p.get("cracks")
    if cr:
        nc = T.noise(cr["scale"], 2.0, 0.5)
        dev = T.math("ABSOLUTE", T.math("SUBTRACT", nc, 0.5))
        line = T.mrange(dev, 0.0, cr["width"], 1.0, 0.0, smooth=True)
        d0 = 1.0 - cr.get("density", 0.5)
        dens = T.mrange(T.noise(0.05, 1.0, 0.5), d0 - 0.05, d0 + 0.05, 0.0, 1.0, smooth=True)
        f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", T.math("MULTIPLY", line, dens), -cr["dark"], 1.0))
    col = T.scale_rgb(tuple(p["base"]), f)
    if ag.get("tint"):
        # aggregate stones: a little random hue per cell (grey-dominated)
        tintc = T.mixc(0.8, colr, (0.5, 0.5, 0.5))
        col = T.mixc(ag["tint"], col, T.mixc(1.0, col, T.scale_rgb(tintc, 2.0), "MULTIPLY"))
    lo, hi = p.get("rough", (0.75, 0.92))
    rough = T.mrange(nm, 0.3, 0.7, lo, hi)
    bs, bd = p.get("bump", (0.3, 0.004))
    normal = T.bump(dist, bs, bd) if bs else None
    return col, rough, normal, r0


def _surface(S, name, p, cache):
    """Material for surface spec p (built once per name)."""
    if name in cache:
        return cache[name]
    import bpy
    m = bpy.data.materials.new(f"airfield_{name}")
    T = _T(m)
    kind = p["kind"]
    if kind == "asphalt":
        col, rough, normal, _ = _pavement(T, p)
        T.finish(T.bsdf(col, rough, p.get("spec", 0.35), normal=normal))
    elif kind == "paint":
        sub = cache.get("_specs", {}).get(p.get("substrate", "asphalt"), ASPHALT)
        col, rough, normal, agg = _pavement(T, sub)
        ground = T.bsdf(col, rough, sub.get("spec", 0.35), normal=normal)
        show = p.get("agg_show", 0.25)
        pc = T.scale_rgb(tuple(p["base"]), T.math("MULTIPLY_ADD", agg, show, 1.0 - 0.5 * show))
        paint = T.bsdf(pc, p.get("rough", 0.55), p.get("spec", 0.45), normal=normal)
        amount, sc = p.get("wear", (0.18, 1.6))
        wn = T.noise(sc, 4.0, 0.65)
        worn = T.mrange(T.math("MULTIPLY", wn, T.math("MULTIPLY_ADD", agg, 0.3, 0.85)), amount + 0.31,
                        amount + 0.39, 1.0, 0.0, smooth=True)
        mx = T.nt.nodes.new("ShaderNodeMixShader")
        T.link(worn, mx.inputs[0])
        T.link(ground, mx.inputs[1])
        T.link(paint, mx.inputs[2])
        T.finish(mx.outputs[0])
    elif kind == "grass":
        ps, pa = p.get("patch", (0.08, 0.35))
        n1 = T.noise(ps, 3.0, 0.55)
        dry = T.mrange(n1, 0.5, 0.75, 0.0, pa, smooth=True)
        col = T.mixc(dry, tuple(p["base"]), tuple(p["dry"]))
        bsc, bamp = p.get("blade", (18.0, 0.35))
        nb = T.noise(bsc, 4.0, 0.7)
        col = T.scale_rgb(col, T.math("MULTIPLY_ADD", nb, 2 * bamp, 1.0 - bamp))
        bs, bd = p.get("bump", (0.4, 0.01))
        T.finish(T.bsdf(col, p.get("rough", 0.9), p.get("spec", 0.25), normal=T.bump(nb, bs, bd)))
    elif kind == "cladding":
        f = 1.0
        for key in ("grooves", "seams"):
            g = p.get(key)
            if not g:
                continue
            c = T.math("ADD", T.dot(g["axis"]), g.get("offset", 0.0))
            fr = T.math("FRACT", T.math("DIVIDE", c, g["pitch"]))
            band = T.math("LESS_THAN", fr, g["width"] / g["pitch"])
            f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", band, g["dark"] - 1.0, 1.0))
        n = T.noise(0.3, 2.0, 0.5)
        f = T.math("MULTIPLY", f, T.math("MULTIPLY_ADD", n, 0.08, 0.96))
        T.finish(T.bsdf(T.scale_rgb(tuple(p["base"]), f), p.get("rough", 0.5), p.get("spec", 0.4),
                        metallic=p.get("metallic", 0.0)))
    elif kind == "diffuse":
        T.finish(T.bsdf(tuple(p["base"]), p.get("rough", 0.6), p.get("spec", 0.4), metallic=p.get("metallic", 0.0)))
    elif kind == "foliage":
        n1 = T.noise(0.6, 4.0, 0.6)
        n2 = T.noise(4.0, 3.0, 0.6)
        v = p.get("var", 0.5)
        f = T.math("MULTIPLY", T.math("MULTIPLY_ADD", n1, 2 * v, 1.0 - v), T.math("MULTIPLY_ADD", n2, 0.6, 0.7))
        T.finish(T.bsdf(T.scale_rgb(tuple(p["base"]), f), p.get("rough", 0.85), 0.3, normal=T.bump(n2, 0.6, 0.2)))
    elif kind == "skyline":
        # unlit: emission = sky horizon radiance (strength-scaled) x rel, lighter toward the ridge, noise patches
        hz = np.asarray(cache["_horizon"], float)
        low = hz * np.asarray(p.get("rel", (0.45, 0.47, 0.5)), float)
        top = hz * np.asarray(p["top"], float) if p.get("top") else low * 1.25
        t = T.mrange(T.dot((0, 0, 1)), 0.0, max(cache["_ring_z"], 1.0), 0.0, 1.0)
        col = T.mixc(t, tuple(float(c) for c in low), tuple(float(c) for c in top))
        sc, amp = p.get("noise", (0.004, 0.25))
        nn = T.noise(sc, 5.0, 0.6)
        col = T.scale_rgb(col, T.math("MULTIPLY_ADD", nn, 2 * amp, 1.0 - amp))
        if p.get("green"):                        # forested patches on the lower slopes
            g = T.mrange(T.noise(sc * 2.5, 3.0, 0.5), 0.45, 0.6, 0.0, 1.0, smooth=True)
            col = T.mixc(T.math("MULTIPLY", g, T.math("SUBTRACT", 1.0, t)), col,
                         T.mixc(1.0, col, tuple(p["green"]), "MULTIPLY"))
        T.finish(T.emit(col, 1.0))
    else:
        raise ValueError(f"airfield: unknown surface kind {kind!r}")
    cache[name] = m
    return m


# =============================================================================================================
# geometry
# =============================================================================================================
def _mesh(S, name, verts, faces, mat, smooth=False):
    import bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(float(c) for c in v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    if mat is not None:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    S.sc.collection.objects.link(o)
    S._extra.append(o)
    return o


def _upward(poly):
    """CCW (seen from above) vertex order -> +z normals."""
    P = np.asarray(poly, float)
    a = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    return list(poly) if a > 0 else list(poly)[::-1]


def _offset(P, d):
    """Polyline offset by d (left of the direction of travel positive), mitred joins."""
    P = np.asarray(P, float)
    n = len(P)
    T_ = np.diff(P, axis=0)
    T_ /= np.linalg.norm(T_, axis=1, keepdims=True)
    N = np.c_[-T_[:, 1], T_[:, 0]]
    out = np.empty_like(P)
    out[0] = P[0] + d * N[0]
    out[-1] = P[-1] + d * N[-1]
    for i in range(1, n - 1):
        m = N[i - 1] + N[i]
        m /= max(np.linalg.norm(m), 1e-9)
        out[i] = P[i] + d * m / max(float(m @ N[i]), 0.3)
    return out


def _strip(P, width, z, closed=False):
    P = np.asarray(P, float)
    if closed:
        P = np.vstack([P, P[:1]])
    A = _offset(P, 0.5 * width)
    Bv = _offset(P, -0.5 * width)
    if closed:                                    # mitre the seam too
        A[0] = A[-1] = 0.5 * (A[0] + A[-1])
        Bv[0] = Bv[-1] = 0.5 * (Bv[0] + Bv[-1])
    n = len(P)
    verts = [(x, y, z) for x, y in A] + [(x, y, z) for x, y in Bv]
    faces = [(i + 1, i, n + i, n + i + 1) for i in range(n - 1)]      # A left of travel: CCW from above
    return verts, faces


def _box(x, y, z):
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    V = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return V, F


def _roof(x, y, z1, zr, kind, axis):
    """Roof solid over a box top at z1, ridge at zr: 'mono' rises from the low eave at min x (axis 'x') / min y
    to the far side; 'gable' has its ridge along the axis."""
    (x0, x1), (y0, y1) = x, y
    if kind == "mono":
        if axis == "x":
            V = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (x1, y0, zr), (x1, y1, zr)]
            F = [(0, 1, 4), (3, 5, 2), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]
        else:
            V = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (x0, y1, zr), (x1, y1, zr)]
            F = [(0, 3, 4), (1, 5, 2), (0, 1, 5, 4), (3, 2, 5, 4), (0, 3, 2, 1)]
        return V, F
    if axis == "y":               # ridge along y at mid x
        xm = 0.5 * (x0 + x1)
        V = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (xm, y0, zr), (xm, y1, zr)]
        F = [(0, 1, 4), (2, 3, 5), (0, 4, 5, 3), (1, 2, 5, 4), (0, 3, 2, 1)]
    else:
        ym = 0.5 * (y0 + y1)
        V = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (x0, ym, zr), (x1, ym, zr)]
        F = [(3, 0, 4), (1, 2, 5), (0, 1, 5, 4), (2, 3, 4, 5), (0, 3, 2, 1)]
    return V, F


def _cylinder(c, r, z, n=16):
    V = [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n), zz)
         for zz in z for k in range(n)]
    F = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    F.append(tuple(range(n))[::-1])
    F.append(tuple(range(n, 2 * n)))
    return V, F


def _tree(S, spec, mat, trunk_mat, k):
    import bpy
    cx, cy = spec["centre"]
    (ox, oy, oz), (rx, ry, rz) = spec["crown"]
    rng = np.random.default_rng(spec.get("seed", k))
    out = []
    for j in range(3):                                    # three overlapping lobes
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
        o = bpy.context.active_object
        o.name = f"airfield_tree_{k}_{j}"
        for poly in o.data.polygons:
            poly.use_smooth = True
        s = 0.75 if j else 1.0
        dx, dy, dz = (rng.uniform(-0.35, 0.35) * rx, rng.uniform(-0.35, 0.35) * ry, rng.uniform(-0.2, 0.25) * rz) \
            if j else (0.0, 0.0, 0.0)
        o.location = (cx + ox + dx, cy + oy + dy, oz + dz)
        o.scale = (rx * s, ry * s, rz * s)
        o.data.materials.append(mat)
        tex = bpy.data.textures.new(f"airfield_tree_{k}_{j}", "CLOUDS")
        tex.noise_scale = 0.35
        tex.noise_depth = 2
        md = o.modifiers.new("lumps", "DISPLACE")
        md.texture = tex
        md.texture_coords = "LOCAL"
        md.strength = 0.25
        md.mid_level = 0.5
        S._extra.append(o)
        out.append(o)
    tr, th = spec.get("trunk", (0.3, 5.0))
    V, F = _cylinder((cx, cy), tr, (0.0, th), 10)
    out.append(_mesh(S, f"airfield_trunk_{k}", V, F, trunk_mat))
    return out


def _skyline(S, spec, C, mat):
    """Ring of radius R round C: top z = C_z + R tan(el(az)), el from the (periodic) profile + noise (or
    blocky: piecewise-constant segments of 'blocky' = (min, max) deg width)."""
    R = float(spec["radius"])
    prof = sorted(spec["profile"], key=lambda t: t[0])
    az_p = np.array([a for a, _ in prof])
    el_p = np.array([e for _, e in prof])
    az_p = np.r_[az_p - 360.0, az_p, az_p + 360.0]
    el_p = np.r_[el_p, el_p, el_p]
    n = int(spec.get("segments", 1440))
    az = np.linspace(-180.0, 180.0, n, endpoint=False)
    el = np.interp(az, az_p, el_p)
    rng = np.random.default_rng(spec.get("seed", 1))
    amp = float(spec.get("noise", 0.3))
    if spec.get("blocky"):
        w0, w1 = spec["blocky"]
        edges = [-180.0]
        while edges[-1] < 180.0:
            edges.append(edges[-1] + rng.uniform(w0, w1))
        idx = np.searchsorted(edges, az, side="right") - 1
        off = rng.uniform(-1.0, 1.0, len(edges)) * amp
        el = np.clip(el + off[idx], 0.15, None)
    else:
        # ridge noise: periodic sums of sines, ~0.5-5 deg features
        for f, a in ((3, 1.0), (7, 0.6), (17, 0.35), (41, 0.2), (97, 0.1)):
            el = el + amp * a * np.sin(np.radians(az) * f + rng.uniform(0, 2 * math.pi))
    zt = C[2] + R * np.tan(np.radians(el))
    zb = -max(60.0, 0.02 * R)
    xs, ys = C[0] + R * np.cos(np.radians(az)), C[1] + R * np.sin(np.radians(az))
    verts = [(x, y, zb) for x, y in zip(xs, ys)] + [(x, y, z) for x, y, z in zip(xs, ys, zt)]
    faces = [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]      # facing the centre
    return _mesh(S, "airfield_skyline", verts, faces, mat), float(np.max(zt))


# =============================================================================================================
# build
# =============================================================================================================
def build_env_preset(pre, cfg):
    """Preset copy for beauty.build_env: the sky only (HDRI rotated so its sun sits at the lamp's azimuth)."""
    q = dict(pre)
    sky = cfg["sky"]
    q.update(env="airfield", hdri=sky["hdri"], strength=float(sky.get("strength", 1.0)), sun_az=float(cfg["sun"]["az"]),
             sun_lamp=None, ground_gain=None, ground_albedo=None, camera_grade=None, camera_sky=None)
    return q


def build(S, pre, cam, info, cfg, B):
    """Everything but the sky (built by B.build_env from build_env_preset()): cap the HDRI sun, the sky light /
    look, the sun lamp, ground, zones, markings, props, skyline.  B = the render.beauty module in use."""
    sky = cfg["sky"]
    hdri = B.ensure_hdri(sky["hdri"])
    stats = sky_stats(hdri, sky.get("cap", 40.0))
    strength = float(sky.get("strength", 1.0))
    done = dict(sky=dict(hdri=sky["hdri"], strength=strength, world=_sky_world(S, sky),
                         licence="CC0 1.0 (Poly Haven)", Eh_sky=[round(v * strength, 3) for v in stats["Eh_sky"]]))
    done["sun"] = _sun_lamp(S, cfg["sun"], stats, strength)
    specs = dict(cfg.get("surfaces", {}))
    cache = {"_specs": specs, "_horizon": [v * strength for v in stats["horizon"]], "_ring_z": 1.0}
    C = np.asarray(cam.C, float)

    def mat(name):
        return _surface(S, name, specs[name], cache)

    g = cfg.get("ground", {})
    E = float(g.get("extent", 2500.0))
    z0 = -0.003
    _mesh(S, "airfield_ground", [(C[0] - E, C[1] - E, z0), (C[0] + E, C[1] - E, z0), (C[0] + E, C[1] + E, z0),
                                 (C[0] - E, C[1] + E, z0)], [(0, 1, 2, 3)], mat(g.get("surface", "asphalt")))
    for k, zn in enumerate(cfg.get("zones", ())):
        poly = _upward([tuple(p) for p in zn["poly"]])
        _mesh(S, f"airfield_zone_{k}", [(x, y, z0 + 0.0008 * (1 + k)) for x, y in poly], [tuple(range(len(poly)))],
              mat(zn["surface"]))
    zm = z0 + 0.0025
    for k, mk in enumerate(cfg.get("markings", ())):
        m = mat(mk["surface"])
        zk = zm + 0.0003 * k                                 # own level: crossing strokes never coplanar
        if "rect" in mk:
            (cx, cy), (lx, ly), yaw = mk["rect"]
            c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            pts = [(cx + c * u - s * v, cy + s * u + c * v) for u, v in
                   ((-lx / 2, -ly / 2), (lx / 2, -ly / 2), (lx / 2, ly / 2), (-lx / 2, ly / 2))]
            _mesh(S, f"airfield_mark_{k}", [(x, y, zk) for x, y in pts], [(0, 1, 2, 3)], m)
            continue
        closed = False
        if "ellipse" in mk:
            (cx, cy), (ax_, ay_) = mk["ellipse"]
            a0, a1 = mk.get("arc", (0.0, 360.0))
            closed = "arc" not in mk
            ts = np.radians(np.linspace(a0, a1, 72, endpoint=not closed))
            pts = np.c_[cx + ax_ * np.cos(ts), cy + ay_ * np.sin(ts)]
        else:
            pts = np.asarray(mk["pts"], float)
        cl = [pts] if not mk.get("double") else [_offset(pts, 0.5 * mk["double"]), _offset(pts, -0.5 * mk["double"])]
        for j, P in enumerate(cl):
            V, F = _strip(P, mk["width"], zk, closed)
            _mesh(S, f"airfield_mark_{k}_{j}", V, F, m)
    n_props = 0
    for k, pr in enumerate(cfg.get("props", ())):
        kind = pr["kind"]
        if kind == "box":
            V, F = _box(pr["x"], pr["y"], pr["z"])
            _mesh(S, f"airfield_box_{k}", V, F, mat(pr["surface"]))
            rf = pr.get("roof")
            if rf:
                V, F = _roof(pr["x"], pr["y"], pr["z"][1], rf["z1"], rf["kind"], rf.get("axis", "x"))
                _mesh(S, f"airfield_roof_{k}", V, F, mat(rf.get("surface", pr["surface"])))
        elif kind == "quad":
            (x0, y0), (x1, y1) = pr["p0"], pr["p1"]
            za, zb = pr["z"]
            V = [(x0, y0, za), (x1, y1, za), (x1, y1, zb), (x0, y0, zb)]
            _mesh(S, f"airfield_quad_{k}", V, [(0, 1, 2, 3)], mat(pr["surface"]))
        elif kind == "cylinder":
            V, F = _cylinder(pr["centre"], pr["radius"], pr["z"])
            _mesh(S, f"airfield_cyl_{k}", V, F, mat(pr["surface"]), smooth=True)
        elif kind == "tree":
            _tree(S, pr, mat(pr["surface"]), mat(pr.get("trunk_surface", pr["surface"])), k)
        else:
            raise ValueError(f"airfield: unknown prop kind {kind!r}")
        n_props += 1
    sk = cfg.get("skyline")
    if sk:
        R = float(sk["radius"])
        el_max = max(e for _, e in sk["profile"]) + float(sk.get("noise", 0.3)) * 2.3
        cache["_ring_z"] = C[2] + R * math.tan(math.radians(el_max))
        _skyline(S, sk, C, mat(sk["surface"]))
    done.update(ground=dict(surface=g.get("surface", "asphalt"), extent_m=E, zones=len(cfg.get("zones", ())),
                            markings=len(cfg.get("markings", ())), props=n_props,
                            skyline=None if not sk else dict(radius_m=sk["radius"], surface=sk["surface"])),
                sky_horizon=[round(v, 4) for v in cache["_horizon"]])
    if info is not None:
        info["airfield"] = done
    return done
