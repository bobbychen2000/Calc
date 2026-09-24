#!/usr/bin/env python3
"""KSFO airfield lighting spec - research deliverable (docs/research/airfield_lighting.md).

Builds two machine-readable files for the renderer from FAA sources, FAA standards and a few public-domain imagery
measurements, keeping the provenance of every value:

  tools/env/lighting_spec.json      rules, photometry, colours, operating logic, per-runway-end facts + anchors
  tools/env/lighting_fixtures.json  the rules expanded into individual fixtures (world x/z, height, colour per face)

Provenance codes (field "src" / "prov"):
  pub  published SFO fact: FAA NASR APT_*.csv cycle 2026-09-03, Chart Supplement SW 3 SEP-29 OCT 2026, d-TPP 2609
       plates / airport diagram, FAA RWSL site graphic, FAA Digital Obstacle File (DOF)
  std  FAA standard geometry / photometry applied to SFO (AC 150/5340-30J, JO 6850.2C, AC 150/5345-xx, AC 70/7460-1N)
       - the standard is verified, its as-built application at SFO is NOT surveyed
  obs  measured by us on USDA NAIP 2024 0.6 m orthoimagery (public domain) in the app world frame
  inf  inferred (a choice inside a standard tolerance, or a value the sources do not give) - replace when better data
       arrives

Inputs (gitignored caches, see the report for URLs):
  refs/cache/xcheck/faa/APT_RWY_END.csv, APT_RWY.csv, APT_BASE.csv  (NASR 28-day subscription, cycle 2026-09-03)
  refs/cache/lighting/DAILY_DOF_CSV.ZIP                             (FAA DOF, currency 2026-09-18)
  refs/cache/osm/overpass_ksfo_latest.json                          (only a boolean cross-check flag, see apron masts)
  data/sfo_details.js                                               (app hold positions, to snap RWSL REL arrays)
World frame: tools/geo_frame.py (= js/geo.js), x east, z south, metres from the ARP, NAD83(2011).

Run:  python3 tools/env/build_lighting_spec.py
"""
import csv, io, json, math, os, sys, zipfile, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import geo_frame as GF  # noqa: E402

FT = 0.3048
OUT_SPEC = os.path.join(ROOT, 'tools', 'env', 'lighting_spec.json')
OUT_FIX = os.path.join(ROOT, 'tools', 'env', 'lighting_fixtures.json')
NASR_DIR = os.path.join(ROOT, 'refs', 'cache', 'xcheck', 'faa')
DOF_ZIP = os.path.join(ROOT, 'refs', 'cache', 'lighting', 'DAILY_DOF_CSV.ZIP')
OSM_JSON = os.path.join(ROOT, 'refs', 'cache', 'osm', 'overpass_ksfo_latest.json')
DETAILS_JS = os.path.join(ROOT, 'data', 'sfo_details.js')

# ============================================================================================== sources (cited by id)
SOURCES = {
    'nasr': dict(title='FAA NASR 28-day subscription, APT_BASE/APT_RWY/APT_RWY_END/APT_RMK.csv, cycle effective 2026-09-03',
                 url='https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/',
                 cache='refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip'),
    'nasr_layout': dict(title='FAA NASR "APT DATA LAYOUT.pdf" (field/code definitions), in the same zip', cache='refs/cache/xcheck/faa/03_Sep_2026_APT_CSV.zip'),
    'cs': dict(title='FAA Chart Supplement Southwest, SAN FRANCISCO INTL p.275-276, 3 SEP 2026 to 29 OCT 2026',
               url='https://aeronav.faa.gov/afd/03sep2026/sw_275_03SEP2026.pdf', cache='refs/cache/lighting/sw_275_03SEP2026.pdf'),
    'ad': dict(title='FAA Airport Diagram AL-375, SW-2 03 SEP 2026 to 01 OCT 2026', url='https://aeronav.faa.gov/d-tpp/2609/00375ad.pdf',
               cache='refs/cache/xcheck/faa/00375ad_2609.pdf'),
    'tpp': dict(title='FAA d-TPP cycle 2609 SFO approach plates (ILS 28R/28L/19L, CAT II/III, GLS, RNAV)', url='https://aeronav.faa.gov/d-tpp/2609/00375IL28R.PDF',
                cache='refs/cache/lighting/tpp/'),
    'ac30j': dict(title='FAA AC 150/5340-30J Design and Installation Details for Airport Visual Aids (2018-02-12, current; errata 2020-11-17)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5340-30J.pdf', cache='refs/cache/lighting/150-5340-30J.pdf'),
    'jo6850': dict(title='FAA Order JO 6850.2C Visual Guidance Lighting Systems (effective 2022-08-30, status Active)',
                   url='https://www.faa.gov/documentLibrary/media/Order/FAA_Order_6850.2C.pdf', cache='refs/cache/lighting/FAA_Order_6850.2C.pdf'),
    'ac46f': dict(title='FAA AC 150/5345-46F Specification for Runway, Taxiway, Heliport and Vertiport Light Fixtures (2024-09-30)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5345-46F-Fixtures.pdf', cache='refs/cache/lighting/AC-150-5345-46F-Fixtures.pdf'),
    'ac28h': dict(title='FAA AC 150/5345-28H Precision Approach Path Indicator (PAPI) Systems (2019-07-29)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-28H.pdf', cache='refs/cache/lighting/150-5345-28H.pdf'),
    'ac51b': dict(title='FAA AC 150/5345-51B Specification for Discharge-Type Flashing Light Equipment (REIL/ODALS) (2010-09-08)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_51b.pdf', cache='refs/cache/lighting/150_5345_51b.pdf'),
    'ac12f': dict(title='FAA AC 150/5345-12F Specification for Airport and Heliport Beacons (2010-09-24)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150_5345_12f.pdf', cache='refs/cache/lighting/150_5345_12f.pdf'),
    'ac43j': dict(title='FAA AC 150/5345-43J Specification for Obstruction Lighting Equipment (2019-03-11)',
                  url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/150-5345-43J.pdf', cache='refs/cache/lighting/150-5345-43J.pdf'),
    'ac7460': dict(title='FAA AC 70/7460-1N Obstruction Marking and Lighting (2026-08-11, cancels 7460-1M)',
                   url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/2026-07-13_AC_70_7460-1N_Obstruction_Marking_and_Lighting_FINAL_CLEAN.pdf',
                   cache='refs/cache/lighting/2026-07-13_AC_70_7460-1N_Obstruction_Marking_and_Lighting_FINAL_CLEAN.pdf'),
    'eb67d': dict(title='FAA Engineering Brief 67D Light Sources Other Than Incandescent and Xenon (chromaticity boundaries)',
                  url='https://www.faa.gov/sites/faa.gov/files/2024-07/eb_67d_rev.pdf', cache='refs/cache/lighting/eb_67d_rev.pdf'),
    'jo7110': dict(title='FAA JO 7110.65BB Air Traffic Control, Chapter 3 Section 4 Airport Lighting (online edition)',
                   url='https://www.faa.gov/air_traffic/publications/atpubs/atc_html/chap3_section_4.html', cache='refs/cache/lighting/jo7110_65_chap3_section_4.html'),
    'aim': dict(title='FAA AIM Chapter 2 Section 1 Airport Lighting Aids (online)', url='https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap2_section_1.html',
                cache='refs/cache/lighting/aim_chap2_section_1.html'),
    'rwsl': dict(title='FAA "Runway Status Lights at San Francisco (SFO)" graphic (PDF created 2017-11-13)', url='https://www.faa.gov/air_traffic/technology/rwsl/media/SFO.pdf',
                 cache='refs/cache/lighting/rwsl_SFO.pdf'),
    'dof': dict(title='FAA Digital Obstacle File, DAILY_DOF_CSV.ZIP (DOF.CSV dated 2026-09-18), horizontal datum WGS 84',
                url='https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP', cache='refs/cache/lighting/DAILY_DOF_CSV.ZIP'),
    'naip': dict(title='USDA NAIP 2024 (flown 2024-05-20) 0.6 m orthoimagery, public domain, resampled to the world grid (docs/research/imagery.md)',
                 cache='refs/cache/naip/naip_2024_world_0.5m_bgr.npy'),
    'sfo2013': dict(title='SFO Airport Commission memo "Runway Safety Area Project Update - Runway Threshold Changes" 2013-06-20 (NTSB docket copy)',
                    url='https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=pdf&FileName=ATC+3-SFO+RSA+Construction+Update-Rel.pdf&ID=398528',
                    cache='refs/cache/lighting/ntsb_ATC3_SFO_RSA_Construction_Update.pdf'),
    'ac5360': dict(title='FAA AC 150/5360-13A Airport Terminal Planning (2018-07-13) para 7.5 Apron Lighting; cancelled AC 150/5360-13 (1988) Table 4-1',
                   url='https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC-150-5360-13A-Airport-Terminal-Planning.pdf', cache='refs/cache/lighting/AC-150-5360-13A.pdf'),
    'xplane': dict(title='X-Plane Scenery Gateway KSFO pack 112022 apt.dat (community data, cross-check only)', cache='refs/cache/xplane/'),
    'osm': dict(title='OpenStreetMap via Overpass, 2026-09-24T09:07Z (ODbL; cross-check flags only, no geometry copied)', cache='refs/cache/osm/overpass_ksfo_latest.json'),
}

# ============================================================================================== colours (EB-67D)
# Aviation colour chromaticity regions for LED fixtures, FAA EB 67D para 2.1.1-2.1.2 (CIE 1931 x,y intersection points).
# 'lin_srgb' = linear sRGB of the region's area centroid at max channel = 1 (derived by us; green/yellow/red/blue lie
# OUTSIDE the sRGB gamut, negative channels clipped) - a rendering convenience, not an FAA value.
COLOURS = {
    'white':  dict(xy=[[0.320, 0.356], [0.440, 0.433], [0.440, 0.383], [0.320, 0.292]], centroid=[0.378, 0.364], lin_srgb=[1.0, 0.6137, 0.4107], in_gamut=True),
    'green':  dict(xy=[[0.014, 0.750], [0.129, 0.600], [0.312, 0.600], [0.302, 0.692]], centroid=[0.180, 0.665], lin_srgb=[0.0, 1.0, 0.0358], in_gamut=False, note='"Green (ICAO Modified)"'),
    'blue':   dict(xy=[[0.090, 0.137], [0.186, 0.214], [0.233, 0.167], [0.148, 0.025]], centroid=[0.161, 0.129], lin_srgb=[0.0, 0.1587, 1.0], in_gamut=False, note='"Blue (ICAO)"'),
    'yellow': dict(xy=[[0.547, 0.452], [0.536, 0.444], [0.593, 0.387], [0.613, 0.387]], centroid=[0.573, 0.417], lin_srgb=[1.0, 0.1887, 0.0], in_gamut=False, note='"Yellow (CIE S 004/E-2001)"'),
    'red':    dict(xy=[[0.680, 0.320], [0.660, 0.320], [0.690, 0.290], [0.710, 0.290]], centroid=[0.685, 0.305], lin_srgb=[1.0, 0.0, 0.0], in_gamut=False, note='"Restricted Red (CIE S 004/E-2001 restricted region)"'),
}
COL = {'W': 'white', 'Y': 'yellow', 'G': 'green', 'R': 'red', 'B': 'blue'}

# ============================================================================================== fixture photometry
# AC 150/5345-46F Table 3-1 (in-pavement), 3-2 (directional elevated), 3-3 (omni elevated); main beam = ellipse (runway) /
# rectangle (taxiway) extremities in degrees, H = horizontal (+ = toward runway centreline for toed fixtures), V =
# elevation; cd = minimum AVERAGE intensity in the main beam (all points >= 50 %), ten = 10 % isocandela curve.
# Max allowed average = 3 x specified (46F para 3.3.5).
FIXTURES = {
    'L-850A': dict(use='runway centreline (in-pavement), bi/unidirectional white, red', main=dict(h=[-5, 5], v=[0.2, 9]), ten=dict(h=[-7, 7], v=[-4, 13]), cd=dict(white=5000, red=750), src='ac46f T1-1,T3-1'),
    'L-850B': dict(use='touchdown zone (in-pavement), unidirectional white, toed 4 deg', main=dict(h=[-1, 9], v=[2, 9]), ten=dict(h=[-3, 11], v=[-0.5, 11.5]), cd=dict(white=5000), src='ac46f T3-1 note (i): data for toed-left'),
    'L-850C': dict(use='runway edge in pavement (intersections, displaced thr)', main=dict(h=[-2, 9], v=[0.2, 7]), ten=dict(h=[-4, 11], v=[-2.5, 9.5]), cd=dict(white=10000, yellow=5000, green=3300, red=1500), src='ac46f T3-1'),
    'L-850D': dict(use='runway threshold/end in pavement', beams=[dict(colour='green', main=dict(h=[-2, 9], v=[1, 10]), cd=3300, note='toed'), dict(colour='red', main=dict(h=[-6, 6], v=[0.2, 4.7]), ten=dict(h=[-7.5, 7.5], v=[-2.5, 7.5]), cd=2500)], src='ac46f T3-1'),
    'L-850E': dict(use='MALS / runway threshold, unidirectional green in pavement', main=dict(h=[-6, 6], v=[1, 9]), cd=dict(green=5000), note='minimum (not average) intensity', src='ac46f T3-1'),
    'L-850T': dict(use='RWSL takeoff hold light, unidirectional red', main=dict(h=[-5, 5], v=[0.2, 9]), ten=dict(h=[-7, 7], v=[-4, 13]), cd=dict(red=1500), note='traffic-signal red (ITE ST-017)', src='ac46f T3-1'),
    'L-852A': dict(use='taxiway CL straight, >=1200 RVR, narrow', main=dict(h=[-10, 10], v=[1, 4]), ten=dict(h=[-16, 16], v=[0.5, 10]), cd=dict(yellow=20, green=20), src='ac46f T3-1'),
    'L-852B': dict(use='taxiway CL curves, >=1200 RVR, wide', main=dict(h=[-30, 30], v=[1, 4]), ten=dict(h=[-30, 30], v=[0.5, 10]), cd=dict(yellow=20, green=20), src='ac46f T3-1'),
    'L-852C': dict(use='taxiway CL straight, <1200 RVR, narrow', main=dict(h=[-3.5, 3.5], v=[1, 8]), ten=dict(h=[-4.5, 4.5], v=[0, 13]), cd=dict(yellow=200, green=200), src='ac46f T3-1'),
    'L-852D': dict(use='taxiway CL curves, <1200 RVR, wide', main=dict(h=[-30, 30], v=[1, 10]), ten=dict(h=[-30, 30], v=[0, 15]), cd=dict(white=150, yellow=100, green=100), src='ac46f T3-1'),
    'L-852E': dict(use='taxiway intersection omni yellow >=1200 RVR', main=dict(h=[-180, 180], v=[1, 8]), cd=dict(yellow=50), src='ac46f T3-1'),
    'L-852F': dict(use='taxiway intersection omni yellow <1200 RVR', main=dict(h=[-180, 180], v=[1, 10]), cd=dict(yellow=200), src='ac46f T3-1'),
    'L-852G': dict(use='in-pavement runway guard light, yellow, alternately flashing', main=dict(h=[-24, 24], v=[1, 10]), ten=dict(h=[-30, 30], v=[0.5, 13]), cd=dict(yellow=1000), flash=dict(fpm=[30, 32], duty=0.5, pattern='even/odd fixtures alternate'), src='ac46f T3-1; ac30j 4.8.6.2.5'),
    'L-852J': dict(use='taxiway CL curves >=1200 RVR', main=dict(h=[-3.5, 35], v=[1, 4]), ten=dict(h=[-4.5, 36], v=[0.5, 15]), cd=dict(yellow=20, green=20), src='ac46f T3-1'),
    'L-852K': dict(use='taxiway CL curves <1200 RVR', main=dict(h=[-3.5, 35], v=[1, 10]), ten=dict(h=[-5.5, 37], v=[0, 15]), cd=dict(yellow=100, green=100), src='ac46f T3-1'),
    'L-852S': dict(use='stop bar (in-pavement) and RWSL runway entrance light, unidirectional red', main=dict(h=[-24, 24], v=[1, 10]), ten=dict(h=[-30, 30], v=[0.5, 13]), cd=dict(red=300), src='ac46f T3-1'),
    'L-852T': dict(use='taxiway edge in pavement, omni blue', main=dict(h=[-180, 180], v=[1, 6]), cd=dict(blue=2), note='minimum; visible 15-90 deg', src='ac46f T3-1 note (h)'),
    'L-804': dict(use='elevated runway guard light, 2 yellow lamps alternately flashing', main=dict(circle_deg=8), ten=dict(circle_deg=25), cd=dict(yellow=3000), note='>=1000 cd within +-15 deg circle', flash=dict(fpm=[45, 50], duty=0.5, off_ratio=0.17), src='ac46f T3-2 note (f); ac46f 3.x flasher'),
    'L-861E': dict(use='elevated threshold/end, non-precision', beams=[dict(colour='green', main=dict(h=[-1.5, 1.5], v=[3.5, 5.5]), cd=300), dict(colour='green', main=dict(h=[-3, 3], v=[1.5, 7.5]), cd=180), dict(colour='green', main=dict(h=[-5, 5], v=[0, 9]), cd=90), dict(colour='red', main=dict(h=[-5, 5], v=[0, 9]), cd=10)], src='ac46f T3-2'),
    'L-861T': dict(use='elevated taxiway/apron edge, omni blue', main=dict(h=[-180, 180], v=[0, 6]), cd=dict(blue=2), note='minimum 2 cd 0-6 deg; visible 15-90 deg', src='ac46f T3-3'),
    'L-862': dict(use='elevated HIRL edge (precision runways)', main=dict(h=[-2, 9], v=[0, 7]), ten=dict(h=[-4, 11], v=[-2.5, 9.5]), cd=dict(white=10000, yellow=5000, green=2500, red=2000), note='plus >=50 cd white omnidirectionally at all elevations to 15 deg (circling)', src='ac46f T3-2 note (c)'),
    'L-862E': dict(use='elevated threshold/end (precision runways)', beams=[dict(colour='red', main=dict(h=[-6, 6], v=[0.2, 4.7]), ten=dict(h=[-7.5, 7.5], v=[-2.5, 7.5]), cd=2500), dict(colour='green', main=dict(h=[-2, 9], v=[1, 10]), cd=3200)], src='ac46f T3-2'),
    'L-862S': dict(use='elevated stop bar, unidirectional red', main=dict(h=[-7, 7], v=[-4, 4]), ten=dict(h=[-14, 14], v=[-8, 8]), cd=dict(red=2000), src='ac46f T3-2'),
    'PAPI_LHA': dict(use='PAPI lamp housing assembly (L-880), white above / red below a sharp transition', isocandela=[
        dict(white=30000, red=15000, h=[-2, 2], v=[-2, 2], shape='circle r=2'), dict(white=20000, red=10000, h=[-4, 4], v=[-2.5, 2.5]),
        dict(white=14000, red=7000, h=[-6, 6], v=[-3, 3]), dict(white=8000, red=4000, h=[-8, 8], v=[-3.5, 3.5]), dict(white=5000, red=2500, h=[-10, 10], v=[-4, 4])],
        transition=dict(arcmin_centre=3, arcmin_edge=5), note='contour extents read from AC 150/5345-28H Figure 3-1 (stadium shapes; +-0.25 deg reading error); V measured from the LHA aiming angle; LED PAPI light only within +-10.5 deg azimuth (JO 6850.2C 504b); night modes ~5 % and ~20 % of day (28H 3.3.8)',
        src='ac28h Fig 3-1, 3.2.1, 3.3.6-3.3.8'),
    'L-849E_REIL': dict(use='REIL unidirectional, 3 steps (style E)', main=dict(h=[-15, 15], v=[0, 10]), cd_effective=dict(high=15000, medium=1500, low=300), flash=dict(fpm=120, sync_ms=20), note='tolerance +-50 %; omni style F: 5000/1500/300 cd at 2-10 deg, 60 fpm; SFO REIL style not published', src='ac51b T1, 3.4.2'),
    'L-802A_beacon': dict(use='high-intensity rotating beacon, alternating white/green', cd_effective_white={'1-2': 37500, '3-7': 75000, '8-10': 37500}, green_factor=0.15, beam_centre_deg=5,
                          flash=dict(fpm_equipment=[22, 26], fpm_installation=[24, 30], duration_ms=[75, 300]), note='AC 150/5345-12F 3.3.1 (equipment 22-26 fpm) vs AC 150/5340-30J 6.1.3 and AIM (24-30 fpm)', src='ac12f T1; ac30j 6.1'),
    'L-810': dict(use='red obstruction light, steady (or L-810(F) flashing 30 fpm)', cd=dict(red=32.5), v_beam=dict(spread_min=10, centre=[4, 20]), flash_F=dict(fpm=[27, 33]), src='ac43j 3.4.1.2'),
    'L-864': dict(use='medium-intensity flashing red obstruction light', cd_effective=dict(red=2000), tol=0.25, v_beam_min=3, min_in_beam=750, flash=dict(fpm=[27, 33], duration='1/2-2/3 period (incandescent) or 100-1333 ms'), src='ac43j 3.4.1.5, T3-5'),
    'L-865': dict(use='medium-intensity flashing white', cd_effective=dict(day=20000, night=2000), flash=dict(fpm=40), src='ac43j T3-4, T3-5'),
    'ALS_PAR56_300W': dict(use='ALSF-2 steady-burning white (FAA-E-2408 Q20A/PAR-56 300 W 20 A; coloured = 500 W)', vertical_spread_deg=12, cd=None,
                           note='12 deg vertical spread from JO 6850.2C 206a; intensity NOT in any FAA document we could obtain (a vendor listing gives ~38,000 cd centre for Q20A/PAR56/C - unverified)', src='jo6850 204a, 206a'),
    'MALS_PAR38': dict(use='MALS steady-burning white (PAR-38 spot; 150PAR38/SP in Table 2-2); threshold PAR-56 300 W green', cd=None, note='intensity not published in the obtained FAA documents', src='jo6850 204b'),
    'SFL_flasher': dict(use='sequenced flasher (ALSF-2 / RAIL / MALSF), bluish-white', aim_deg=6, rate='each flasher 2 flashes/s, sequence outermost -> threshold', cd=None,
                        steps='ALSF-2 3 steps 100/20/2.3 %; MALS* 100/10/2.3 %', note='FAA-E-2998/FAA-E-2689 photometry not obtained', src='jo6850 200b, 206, T2-3'),
}

# ============================================================================================== operation (JO 7110.65BB)
# Visibility in statute miles (surface/prevailing, or RVR equivalent where marked). 'on' logic per paragraph.
OPERATION = {
    'src': 'jo7110 3-4-2..3-4-19 (tables transcribed); SFO tower facility directives may override (unknown)',
    'twilight_note': 'TBL 3-4-3: twilight = sunset to 30 min after sunset and 30 min before sunrise to sunrise',
    'hirl_rcl_tdz_steps': dict(src='jo7110 TBL 3-4-8', day={'5': '<1', '4': '1-<2', '3': '2-<3', '2': 'on request', '1': 'on request'},
                               night={'5': 'on request', '4': '<1', '3': '1-<3', '2': '3-5', '1': '>5'}, note='"*and/or appropriate RVR equivalent"'),
    'runway_edge_on': 'sunset-sunrise for runways in use; sunrise-sunset when surface visibility < 2 SM (jo7110 3-4-10)',
    'als_on': 'sunset-sunrise when serving the landing runway (or approach to it); day when ceiling < 1000 ft or visibility <= 5 SM (jo7110 3-4-5)',
    'als_steps': dict(src='jo7110 TBL 3-4-5', day={'5': '<1 (or RVR <= 6000 ft)', '4': '1-<3', '3': '3-<5', '2': '5-<7', '1': 'on request'},
                      night={'5': 'on request', '4': 'on request', '3': '<1 (or RVR <= 6000 ft)', '2': '1-3', '1': '>3'}),
    'alsf2_vs_ssalr': 'operate ALSF-2 when prevailing visibility <= 3/4 SM or RVR <= 4000 ft (pilot request / controller); otherwise operate the SSALR mode (jo7110 3-4-9)',
    'sfl_on': 'visibility < 3 SM and instrument approaches to that runway, or on request; SFL cannot run when the ALS is off (jo7110 3-4-7)',
    'malsr_3step': dict(src='jo7110 TBL 3-4-7', day={'3': '<2', '2': '2-5', '1': 'on request'}, night={'3': '<1', '2': '1-<3', '1': '>=3'}),
    'reil_3step': dict(src='jo7110 TBL 3-4-1', day={'3': '<2', '2': '2-5', '1': 'on request'}, night={'3': '<1', '2': '1-<3', '1': '>=3'}, on='when the associated runway lights are lighted'),
    'papi_5step': dict(src='jo7110 TBL 3-4-4', day='step 4', night='step 3', other='1,2,5 on request',
                       note='basic FAA PAPI is photo-electric: day mode when north-sky vertical illuminance rises to 50-60 fc, night below 25-35 fc, 45-75 s delay (AC 150/5345-28H 3.3.6)'),
    'taxiway_5step': dict(src='jo7110 TBL 3-4-12', day={'5': '<1', '4': 'on request', '3': 'on request'}, night={'4': '<1', '3': '>=1'}),
    'obstruction': 'sunset-sunrise if controls exist (jo7110 3-4-17); red lights switch on when north-sky illuminance falls below 60 fc, before 35 fc (AC 70/7460-1N 5.3)',
    'beacon': 'sunset-sunrise, and by day when ceiling or visibility below basic VFR (jo7110 3-4-18); NASR BCN_LGT_SKED = SS-SR',
    'rwsl': 'automatic intensity, operated continuously (jo7110 3-4-19); RELs light when high-speed traffic on runway or arrival within ~1 mi; THLs when runway occupied ahead of a departure (AIM 2-1-6)',
}
INTENSITY_STEPS = {
    'HIRL_RCL_TDZ_TWYCL_5step_pct': [100, 25, 5, 1.2, 0.15], 'HIRL_lamp_current_A': [6.6, 5.2, 4.1, 3.4, 2.8], 'src_hirl': 'ac30j 2.6.4.1',
    'MIRL_MITL_3step_pct': [100, 30, 10], 'src_mirl': 'ac30j 2.6.4.2',
    'ALSF2_steady_pct': [100, 20, 4, 0.8, 0.16], 'ALSF2_flasher_pct': [100, 20, 2.3], 'MALS_steady_pct': [100, 20, 4], 'MALS_flasher_pct': [100, 10, 2.3],
    'ALSF2_flasher_mapping': 'steady steps 4-5 -> flashers high, step 3 -> medium, steps 1-2 -> low', 'src_als': 'jo6850 T2-3',
    'REIL_pct_from_cd': [100, 10, 2], 'src_reil': 'ac51b T1 (15000/1500/300 cd)',
    'REIL_follows_HIRL': 'HIRL step 1-2 -> REIL low, 3 -> medium, 4-5 -> high (jo6850 405a)',
    'PAPI_night_pct': [5, 20], 'src_papi': 'ac28h 3.3.8',
}

# ============================================================================================== SFO facts
INSTRUMENT_ENDS = {  # d-TPP 2609 IAPs per end (AirNav index of the same cycle, plates cached): no IAP to 1L/1R
    '10L': 'RNAV (GPS) RWY 10L', '10R': 'RNAV (RNP) Z / RNAV (GPS) Y RWY 10R', '28L': 'ILS or LOC, SA CAT II, GLS, RNAV (GPS) RWY 28L',
    '28R': 'ILS or LOC, SA CAT I, CAT II-III, GLS, RNAV RWY 28R', '19L': 'ILS or LOC, GLS, RNAV (GPS) RWY 19L', '19R': 'GLS, RNAV (GPS) Y/Z RWY 19R',
}
PLATE_GP = {  # electronic / RNAV glide path on the plates (deg, TCH ft) - differs from the VGSI (notes "VGSI and ... not coincident")
    '28R': dict(gs=3.00, tch=55, plate='00375IL28R Amdt 15B'), '28L': dict(gs=2.85, tch=53, plate='00375IL28L Amdt 27C'),
    '19L': dict(gs=3.00, tch=55, plate='00375IL19L Amdt 23A'), '10L': dict(gs=3.00, tch=55, plate='00375R10L Amdt 3 (RNAV GP)'),
    '19R': dict(gs=3.15, tch=55, plate='00375RY19R Amdt 4 (RNAV GP)'), '10R': dict(gs=3.00, tch=60, plate='00375RY10R Amdt 2A (LNAV/VNAV descent angle)'),
}
PLATE_VGSI = {'28R': (3.00, 68), '28L': (2.85, 67), '19L': (3.00, 71), '10L': (3.00, 80), '10R': (3.00, 68)}  # "(VGSI Angle x/TCH y)" notes; 19R none (coincident)

# PAPI LHAs measured on NAIP 2024 (obs): along ft from the NASR landing threshold, lateral ft LEFT of the centreline for
# LHA 1..4 (1 = nearest runway). Orange lamp housings on concrete pads detected by colour and fitted to a 4-unit row at
# 30 ft pitch; +-5 ft (0.6 m pixels + ~0.3-1 m registration). Reproduce: tools/env/lighting_naip_measure.py.
PAPI_OBS = {
    '10L': dict(along=1556, lat=[177, 207, 237, 268], hits=4, note='2 of 4 fitted automatically, all 4 confirmed visually'),
    '10R': dict(along=1298, lat=[157, 188, 218, 248], hits=4, note='3 of 4 fitted automatically, 4th confirmed visually'),
    '19L': dict(along=1344, lat=[161, 191, 221, 251], hits=4),
    '19R': dict(along=1023, lat=[176, 206, 236, 266], hits=4),
    '28L': dict(along=1369, lat=[173, 203, 233, 263], hits=4),
    '28R': dict(along=1369, lat=[173, 204, 234, 264], hits=4),
}
# ALS pier structures seen on NAIP 2024 (obs): crossmember stations in ft from the NASR landing threshold (+-10 ft),
# read visually from runway-aligned 0.25 m resamples (refs/cache/lighting/naip/zoom_28.png, als_19.png).
ALS_PIERS_OBS = {
    '28R': dict(shoreline_ft=-650, crossmembers_ft=[700, 800, 900, 1000, 1100, 1200, 1300], crossmember_width_ft=110,
                far_end_ft='beyond NAIP coverage (> ~2350 ft)', pile_caps_every_ft=100,
                note='7 crossmembers of equal width; equipment platforms at ~1150 and ~1390 ft'),
    '28L': dict(shoreline_ft=-650, crossmembers_ft=[1000, 1300], crossmember_width_ft={'1000': 82, '1300': 103},
                far_end_ft='> 3000 ft (continues past the NAIP edge)', pile_caps_every_ft=100),
    '19L': dict(shoreline_ft=-500, crossmembers_ft=[1000, 1200], far_end_ft=1400, pile_caps_every_ft=100,
                note='pier ends at ~1400 ft = MALSF length; the 1200-ft member is wider and brighter (newer?)'),
    '19R': dict(note='no pier / no structure beyond the shoreline (consistent with NASR: no ALS)'),
}
# FAA RWSL graphic (pub, schematic): REL labels as placed on the drawing, with the runway they sit on; THL ends.
RWSL_THL_ENDS = ['10L', '10R', '28L', '28R', '1L', '1R']
RWSL_REL = [('R', '10L/28R'), ('E', '10L/28R'), ('E', '10L/28R'), ('L', '10L/28R'), ('C', '10L/28R'),
            ('Q', '10R/28L'), ('K', '10R/28L'), ('D', '10R/28L'), ('T', '10R/28L'), ('E', '10R/28L'), ('L', '10R/28L'), ('P', '10R/28L'),
            ('F2', '10R/28L'), ('C', '10R/28L'), ('F', '10R/28L'),
            ('M', '1L/19R'), ('H', '1L/19R'), ('H', '1L/19R'), ('G', '1L/19R'), ('G', '1L/19R'), ('F1', '1L/19R'), ('F1', '1L/19R'), ('F', '1L/19R'), ('C', '1L/19R'),
            ('F', '1R/19L'), ('C', '1R/19L'), ('E', '1R/19L')]
# label anchor positions in the world frame from an 8-point affine fit of the graphic's runway polygons to the NASR ends
# (residual 40-80 m - the graphic is schematic); used only to pick the nearest same-name hold.
RWSL_REL_XY = [[-1206, -935], [-165, -230], [-89, -339], [386, 61], [1601, 557], [-1145, -621], [-858, -469], [-648, -357], [-553, -330],
               [-358, -42], [269, 283], [608, 465], [1290, 828], [1534, 676], [1419, 894], [-597, 1222], [-613, 1015], [-444, 1010],
               [-318, 719], [-426, 658], [-243, 305], [-111, 332], [-181, 171], [102, -338], [30, 255], [288, -234], [715, -745]]


# ============================================================================================== helpers
def rd(v, n=2):
    return round(v, n)


def load_nasr():
    ends, rwys, base = {}, {}, None
    for fn in ('APT_RWY_END.csv', 'APT_RWY.csv', 'APT_BASE.csv'):
        p = os.path.join(NASR_DIR, fn)
        if not os.path.exists(p):
            sys.exit('missing %s - download the NASR APT CSV zip (cycle 2026-09-03) into refs/cache/xcheck/faa/' % p)
        for r in csv.DictReader(open(p, encoding='latin-1')):
            if r['ARPT_ID'] != 'SFO':
                continue
            if fn == 'APT_RWY_END.csv':
                ends[r['RWY_END_ID'].lstrip('0')] = r
            elif fn == 'APT_RWY.csv':
                rwys[r['RWY_ID'].replace('01', '1')] = r
            else:
                base = r
    return ends, rwys, base


def f(r, k):
    v = r.get(k, '').strip()
    return float(v) if v else None


class Frame:
    """Runway-end frame: origin at the runway END point (NASR), u = landing direction, l = left of u (x east, z south)."""

    def __init__(self, ends, E, O):
        r = ends[E]
        self.E, self.O = E, O
        self.R = GF.ll_to_world(f(r, 'LAT_DECIMAL'), f(r, 'LONG_DECIMAL'))
        ro = ends[O]
        self.RO = GF.ll_to_world(f(ro, 'LAT_DECIMAL'), f(ro, 'LONG_DECIMAL'))
        dx, dz = self.RO[0] - self.R[0], self.RO[1] - self.R[1]
        self.L = math.hypot(dx, dz)
        self.u = (dx / self.L, dz / self.L)
        self.l = (self.u[1], -self.u[0])
        if r['LAT_DISPLACED_THR_DECIMAL'].strip():
            self.T = GF.ll_to_world(f(r, 'LAT_DISPLACED_THR_DECIMAL'), f(r, 'LONG_DISPLACED_THR_DECIMAL'))
        else:
            self.T = self.R
        self.disp = (self.T[0] - self.R[0]) * self.u[0] + (self.T[1] - self.R[1]) * self.u[1]  # metres along
        self.hdg = (math.degrees(math.atan2(self.u[0], -self.u[1])) + 360) % 360

    def at(self, along_m, left_m, from_threshold=False):
        o = self.T if from_threshold else self.R
        return (o[0] + along_m * self.u[0] + left_m * self.l[0], o[1] + along_m * self.u[1] + left_m * self.l[1])


def xz(p):
    return [rd(p[0]), rd(p[1])]


# ============================================================================================== build
def build():
    ends, rwys, base = load_nasr()
    pairs = [('10L', '28R'), ('10R', '28L'), ('1L', '19R'), ('1R', '19L')]
    FR = {}
    for a, b in pairs:
        FR[a] = Frame(ends, a, b); FR[b] = Frame(ends, b, a)

    spec = dict(schema='sfo3d.airfield_lighting.v1', generated=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'),
                generator='tools/env/build_lighting_spec.py', report='docs/research/airfield_lighting.md',
                frame=dict(id=GF.FRAME_ID, axes='x east, z south, metres from the ARP (FAA NASR 37.6188056 N, -122.3754167 E)', ground_note='heights h are metres above local ground/pavement; ALS light plane = threshold elevation (NAVD88 ft per NASR)'),
                provenance={'pub': 'published SFO fact (NASR, Chart Supplement, TPP, FAA RWSL graphic, DOF)', 'std': 'FAA standard applied to SFO, as-built not surveyed',
                            'obs': 'measured on NAIP 2024 public-domain orthoimagery', 'inf': 'inferred / chosen inside a standard tolerance'},
                sources=SOURCES, colours=COLOURS, fixtures=FIXTURES, intensity_steps=INTENSITY_STEPS, operation=OPERATION)

    spec['airport'] = dict(
        beacon=dict(lens=base['BCN_LENS_COLOR'], lens_meaning='WG = white-green, lighted land airport', schedule=base['BCN_LGT_SKED'], type='L-802A (std: high-intensity systems present, ac30j 6.1.4.1)',
                    position=None, position_note='NOT published in NASR/CS/AD; not in X-Plane or the cached OSM - open question', src='pub nasr APT_BASE BCN_LENS_COLOR, BCN_LGT_SKED'),
        airport_lighting_schedule=base.get('LGT_SKED') or None, lgt_sked_note='blank in NASR: no published schedule - lights per ATC (tower attended continuously, CS)',
        wind_indicator=base['WIND_INDCR_FLAG'], wind_indicator_note='Y-L = lighted wind indicator (NASR); X-Plane has 8 windsocks, OSM 1 - positions not FAA-published',
        rwsl=dict(in_operation=True, src='pub nasr APT_RMK "RWY STATUS LGTS IN OPN."; CS "Rwy status lgts in operation"; AD "Runway Status Lights in operation."'),
        rvr='TMR (touchdown, midfield, rollout) at all 8 ends (NASR RWY_VISUAL_RANGE_EQUIP_CODE)',
    )

    # --------------------------------------------------------------------------------------- per-runway facts + anchors
    runways = []
    fixtures = []   # groups

    def group(system, end, ftype, prov, emit, pts, note=None, **kw):
        g = dict(system=system, end=end, type=ftype, prov=prov, emit=emit, n=len(pts), pts=pts)
        if note: g['note'] = note
        g.update(kw)
        fixtures.append(g)

    for a, b in pairs:
        rw = rwys[a + '/' + b]
        Fa, Fb = FR[a], FR[b]
        L_ft = float(rw['RWY_LEN']); W_ft = float(rw['RWY_WIDTH'])
        edge_lat = W_ft / 2 + 10   # std 2-10 ft outside pavement; 10 ft recommended for jets (ac30j 2.3.1.2.1) & = MALS 23-light rule
        R = dict(id=a + '/' + b, length_ft=L_ft, width_ft=W_ft, geodesic_length_m=rd(Fa.L), surface=rw['SURFACE_TYPE_CODE'] + '-' + rw['TREATMENT_CODE'],
                 edge=dict(type='HIRL', src='pub nasr RWY_LGT_CODE=HIGH; CS "HIRL"'), centreline=dict(present=True, src='pub CS "CL"; nasr CNTRLN_LGTS_AVBL_FLAG=Y both ends'),
                 edge_lateral_ft=dict(value=edge_lat, prov='inf', note='std 2-10 ft outside the 200-ft pavement; 10 ft chosen (jet runways, and MALS threshold row of 23 lights on 10-ft centres coincident with the edge lights, JO 6850.2C 200d)'),
                 ends={})
        # ---- edge lights (both sides), uniform spacing <= 200 ft between the threshold/end light lines
        N = math.ceil(L_ft / 200.0)
        sp = L_ft / N
        R['edge_spacing_ft'] = dict(value=rd(sp), n_spaces=N, prov='inf', rule='uniform, <= 200 ft, symmetric, referenced to threshold/runway-end lights (ac30j 2.3.1.2.1)')
        pts = []
        for k in range(1, N):
            s_ft = k * sp
            cols = []
            for trav, disp_ft, rem_ft in ((a, Fa.disp / FT, L_ft - s_ft), (b, Fb.disp / FT, s_ft)):
                pos_from_end = (s_ft if trav == a else L_ft - s_ft)
                caution = min(2000.0, L_ft / 2)
                if pos_from_end < disp_ft:
                    c = 'R'
                elif trav in INSTRUMENT_ENDS and rem_ft <= caution:
                    c = 'Y'
                else:
                    c = 'W'
                cols.append(c)
            for side in (1, -1):
                p = Fa.at(s_ft * FT, side * edge_lat * FT)
                pts.append(xz(p) + [0.36] + cols)
        group('runway_edge', a + '/' + b, 'L-862 (L-850C where on other runway/taxiway pavement)', 'std+inf',
              {'face0': dict(seen_by=a, emit_dir=[rd(-Fa.u[0], 4), rd(-Fa.u[1], 4)]), 'face1': dict(seen_by=b, emit_dir=[rd(Fa.u[0], 4), rd(Fa.u[1], 4)])}, pts,
              note='point = [x, z, h, colour seen by face0 traffic, colour seen by face1 traffic]; red = before that direction\'s displaced threshold, yellow = caution zone min(2000 ft, L/2) for instrument ends (ac30j 2.3.1.1.2, 2.3.2.1.2, Fig A-7/A-9)')
        # ---- runway centreline lights L-850A, 50 ft, first/last light 50-87.5 ft from the pavement end, centred
        n = round((L_ft - 150) / 50.0)
        gap = (L_ft - n * 50) / 2
        R['rcl'] = dict(spacing_ft=50, end_gap_ft=rd(gap), n_lights=n + 1, prov='std+inf', rule='50 ft +-2 ft, first light 75 ft +12.5/-25 from the runway end (ac30j 3.3.1.1, Fig A-34); lateral offset <= 2.5 ft to one side unknown (0 used)')
        pts = []
        # colour for a-traffic: remaining r measured to the far pavement end (Fig A-7 note 6)
        idx_alt = {a: 0, b: 0}
        cols_all = []
        positions = [gap + k * 50 for k in range(n + 1)]
        for trav in (a, b):
            seq = positions if trav == a else list(reversed(positions))
            disp_ft = (Fa.disp if trav == a else Fb.disp) / FT
            cmap = {}
            alt = 0
            for s_ft in seq:
                pos_from_end = s_ft if trav == a else L_ft - s_ft
                rem = L_ft - pos_from_end
                if pos_from_end < disp_ft:
                    c = '-'          # blanked toward the approach (displaced area <= 700 ft, ac30j 3.3.1.3.1)
                elif rem > 3000:
                    c = 'W'
                elif rem > 1000:
                    c = 'R' if alt % 2 == 0 else 'W'; alt += 1
                else:
                    c = 'R'
                cmap[s_ft] = c
            cols_all.append(cmap)
        for s_ft in positions:
            p = Fa.at(s_ft * FT, 0)
            pts.append(xz(p) + [0.0, cols_all[0][s_ft], cols_all[1][s_ft]])
        group('runway_centreline', a + '/' + b, 'L-850A', 'std+inf',
              {'face0': dict(seen_by=a, emit_dir=[rd(-Fa.u[0], 4), rd(-Fa.u[1], 4)]), 'face1': dict(seen_by=b, emit_dir=[rd(Fa.u[0], 4), rd(Fa.u[1], 4)])}, pts,
              note="colour per travel direction: white; alternating red/white (starting red) from 3000 to 1000 ft remaining; red last 1000 ft; '-' = blanked (displaced area, approach direction)")

        for E, O in ((a, b), (b, a)):
            F = FR[E]; r = ends[E]
            disp_ft = f(r, 'DISPLACED_THR_LEN') or 0.0
            e = dict(
                heading_true=rd(F.hdg, 2), runway_end=dict(lat=f(r, 'LAT_DECIMAL'), lon=f(r, 'LONG_DECIMAL'), world=xz(F.R), elev_ft=f(r, 'RWY_END_ELEV'), src='pub nasr'),
                landing_threshold=dict(world=xz(F.T), displaced_ft=disp_ft, elev_ft=f(r, 'DISPLACED_THR_ELEV') or f(r, 'RWY_END_ELEV'), tdze_ft=f(r, 'TDZ_ELEV'),
                                       lat=f(r, 'LAT_DISPLACED_THR_DECIMAL') or f(r, 'LAT_DECIMAL'), lon=f(r, 'LONG_DISPLACED_THR_DECIMAL') or f(r, 'LONG_DECIMAL'), src='pub nasr'),
                declared_ft=dict(TORA=f(r, 'TKOF_RUN_AVBL'), TODA=f(r, 'TKOF_DIST_AVBL'), ASDA=f(r, 'ACLT_STOP_DIST_AVBL'), LDA=f(r, 'LNDG_DIST_AVBL'), src='pub nasr = CS'),
                instrument=E in INSTRUMENT_ENDS, iap=INSTRUMENT_ENDS.get(E), marking=r['RWY_MARKING_TYPE_CODE'], ils=r['ILS_TYPE'] or None,
                als=r['APCH_LGT_SYSTEM_CODE'] or None, reil=r['RWY_END_LGTS_FLAG'] == 'Y', tdz=r['TDZ_LGT_AVBL_FLAG'] == 'Y', rcl_flag=r['CNTRLN_LGTS_AVBL_FLAG'] == 'Y',
                rvr=r['RWY_VISUAL_RANGE_EQUIP_CODE'], vgsi=r['VGSI_CODE'] or None, vgsi_angle=f(r, 'VISUAL_GLIDE_PATH_ANGLE'), vgsi_tch_ft=f(r, 'THR_CROSSING_HGT'),
                src_flags='pub nasr APT_RWY_END (APCH_LGT_SYSTEM_CODE, RWY_END_LGTS_FLAG=REIL, TDZ_LGT_AVBL_FLAG, CNTRLN_LGTS_AVBL_FLAG, VGSI_CODE, VISUAL_GLIDE_PATH_ANGLE, THR_CROSSING_HGT) = CS p.275',
                caution_zone_ft=(min(2000.0, L_ft / 2) if E in INSTRUMENT_ENDS else 0.0),
                plate_glidepath=PLATE_GP.get(E), plate_vgsi_note=PLATE_VGSI.get(E),
                thl=E in RWSL_THL_ENDS,
            )
            u_back = [rd(-F.u[0], 4), rd(-F.u[1], 4)]   # emission toward the approach
            u_fwd = [rd(F.u[0], 4), rd(F.u[1], 4)]
            # ---- threshold / end lights
            if disp_ft == 0:
                pts = [xz(F.at(-5 * FT, s * lat * FT)) + [0.36] for s in (1, -1) for lat in (80, 90, 100, 110)]
                group('threshold_end', E, 'L-862E (or L-850D in pavement)', 'std+inf', {'green': dict(seen_by=E, emit_dir=u_back), 'red': dict(seen_by=O, emit_dir=u_fwd)}, pts,
                      note='2 groups of 4 on 10-ft centres, outermost in line with the edge lights (ac30j 2.3.2.2.1 item 6, Fig A-3); 2-10 ft before the threshold (5 ft used, inf); split green (outward) / red (toward runway)')
            else:
                pts = [xz(F.at(-5 * FT, s * lat * FT)) + [0.36] for s in (1, -1) for lat in (80, 90, 100, 110)]
                group('runway_end', E, 'L-862E/L-850D red', 'std+inf', {'red': dict(seen_by=O, emit_dir=u_fwd)}, pts,
                      note='pavement end of a displaced-threshold runway: red toward the runway only (ac30j Fig A-5/A-9)')
                pts = [xz(F.at(0, s * lat * FT, True)) + [0.36] for s in (1, -1) for lat in (110, 120, 130, 140)]
                group('threshold_wingbar', E, 'L-862E green unidirectional', 'std+inf', {'green': dict(seen_by=E, emit_dir=u_back)}, pts,
                      note='displaced threshold: innermost in line with the edge lights, the rest outward on 10-ft centres, aligned with the approach-side edge of the threshold marking (ac30j 2.3.2.2.2, Fig A-5 note 6)')
            # ---- TDZ
            if e['tdz']:
                pts = [xz(F.at(k * 100 * FT, s * lat * FT, True)) + [0.0] for k in range(1, 31) for s in (1, -1) for lat in (36, 41, 46)]
                group('tdz', E, 'L-850B', 'std', {'white': dict(seen_by=E, emit_dir=u_back, toe_in_deg=4)}, pts,
                      note='30 bars per side at 100 ft (+-2) from 100 ft to 3000 ft; 3 lights on 5-ft centres, inner light 36 ft from CL (72 ft between rows); toed 4 deg toward CL (ac30j 3.3.2, Fig A-35)')
                e['tdz_rule'] = 'bars 100..3000 ft from the landing threshold (pub flag, std geometry)'
            # ---- REIL
            if e['reil']:
                pts = [xz(F.at(0, s * (W_ft / 2 + 40) * FT, True)) + [0.7] for s in (1, -1)]
                group('reil', E, 'L-849 (style not published)', 'pub+std+inf', {'white': dict(seen_by=E, emit_dir=u_back, aim_up_deg=10, toe_out_deg=15)}, pts,
                      note='in line with the threshold lights, 40 ft from the runway edge (tolerance to 75 ft laterally, 30 ft downwind/100 ft upwind); unidirectional aimed 10 deg up, toed out 15 deg; both flash in sync (JO 6850.2C 401-402; ac51b 3.4.2). NAIP shows candidate pads at 1L ~33 ft before the threshold line (unconfirmed)')
            # ---- PAPI
            if e['vgsi'] == 'P4L':
                th = math.radians(e['vgsi_angle'])
                D_pub = e['vgsi_tch_ft'] / math.tan(th)
                ob = PAPI_OBS.get(E)
                lhas = [xz(F.at(ob['along'] * FT, lat * FT, True)) + [0.8] for lat in ob['lat']]
                aim_std = [e['vgsi_angle'] + d / 60 for d in (30, 10, -10, -30)]
                aim_hg4 = [e['vgsi_angle'] + d / 60 for d in (35, 15, -15, -35)]
                e['papi'] = dict(side='left', n=4, angle_deg=e['vgsi_angle'], tch_ft=e['vgsi_tch_ft'], src='pub nasr VGSI_CODE P4L + CS "PAPI(P4L)-GA x TCH y"',
                                 dist_from_tch_ft=rd(D_pub, 0), dist_obs_ft=ob['along'], dist_obs_minus_pub_ft=rd(ob['along'] - D_pub, 0), lateral_obs_ft=ob['lat'],
                                 lha_world=lhas, lha_h_m=dict(value=0.8, prov='inf', note='beam centres within +-1 in of one plane, +-1 ft of the runway CL elevation at the glide-path intercept (JO 6850.2C 506d)'),
                                 aiming_deg_std=[rd(x, 4) for x in aim_std], aiming_deg_hg4=[rd(x, 4) for x in aim_hg4],
                                 aiming_note='LHA1 = nearest runway. JO 6850.2C Table 5-2: standard +30/+10/-10/-30 arcmin, height group 4 on runways with a published GPA +35/+15/-15/-35; which SFO uses is not published (HG4 likely: B747/777/A350 traffic, all six ends have a GPA) - inf',
                                 obs_prov='obs naip 2024 (+-5 ft)')
                group('papi', E, 'PAPI_LHA (L-880)', 'obs+pub', {'split': dict(seen_by=E, emit_dir=u_back)}, [p + [rd(a_, 4)] for p, a_ in zip(lhas, aim_hg4)],
                      note='point = [x, z, h, aiming angle deg (HG4 set, inf)]; white above the aiming angle, red below (3 arcmin transition)')
            # ---- ALS
            als = e['als']
            if als:
                elev = e['landing_threshold']['elev_ft']
                e['als_detail'] = dict(type=als, plane_elev_ft=elev, plane_note='single horizontal plane at the threshold centreline elevation (JO 6850.2C 201a); SFO piers over the bay - see als_piers_observed',
                                       stations_referenced_to='landing (displaced) threshold per JO 6850.2C 15/200 and the SFO 2013 memo (ALS changed when 28L/28R thresholds moved); pier crossmembers do not settle which stations are lit',
                                       piers_observed=ALS_PIERS_OBS.get(E))
                _als(group, F, E, als, u_back, W_ft, e)
            R['ends'][E] = e
        runways.append(R)
    spec['runways'] = runways

    # --------------------------------------------------------------------------------------- RWSL
    thl_rule = dict(type='L-850T', rows=2, lateral_ft=6, first_ft=375, tol_ft=25, spacing_ft=100, per_row=16, length_ft=1500,
                    reference='runway end (start of takeoff roll) - inf; ac30j G.2.4 says "from the runway threshold"; for displaced-threshold ends the two readings differ by 300-640 ft',
                    src='ac30j G.2.4, Fig G-3')
    for E in RWSL_THL_ENDS:
        F = FR[E]
        pts = [xz(F.at((375 + 100 * k) * FT, s * 6 * FT)) + [0.0] for k in range(16) for s in (1, -1)]
        group('rwsl_thl', E, 'L-850T', 'pub+std+inf', {'red': dict(seen_by=E, emit_dir=[rd(-F.u[0], 4), rd(-F.u[1], 4)])}, pts,
              note='THL presence from the FAA SFO RWSL graphic (pub); geometry std; reference point inf')
    holds = []
    if os.path.exists(DETAILS_JS):
        s = open(DETAILS_JS).read(); holds = [h for h in json.loads(s[s.find('{'):s.rfind('}') + 1])['holds'] if h.get('kind') == 'runway']
    rel = []
    for (tw, rwy), P in zip(RWSL_REL, RWSL_REL_XY):
        cands = [h for h in holds if h.get('rwy') == rwy and h.get('twy') and tw in h['twy'].replace('/', ' ').split()]
        best = min(cands, key=lambda h: math.hypot(h['p'][0] - P[0], h['p'][1] - P[1])) if cands else None
        rel.append(dict(taxiway=tw, runway=rwy, graphic_xy=P, hold=(dict(p=best['p'], text=best.get('text'), twy=best['twy'], dist_m=rd(math.hypot(best['p'][0] - P[0], best['p'][1] - P[1]), 0)) if best else None)))
    spec['rwsl'] = dict(src='pub rwsl graphic (schematic, 2017) + nasr/CS/AD remark "in operation"', thl_ends=RWSL_THL_ENDS, thl_rule=thl_rule,
                        rel_rule=dict(type='L-852S red', first='2 ft before the hold marking (holding side)', lateral='2 ft from taxiway CL, opposite side of the CL lights', spacing_ft='<= 50, >= 12.5, equidistant',
                                      next_to_last='2 ft before the runway edge stripe', last='2 ft beside the runway CL lights toward the taxiway', min_count=6, src='ac30j G.2.1-G.2.3, Fig G-1/G-2'),
                        rel=rel, rel_note='one entry per label on the FAA graphic, snapped to the nearest app hold (data/sfo_details.js) with the same taxiway and runway; which side/which of two parallel holds is lit is not resolvable from the graphic (dist_m shows the schematic offset)')

    # --------------------------------------------------------------------------------------- rules not tied to SFO survey
    spec['rules'] = RULES

    # --------------------------------------------------------------------------------------- obstructions (DOF) + masts
    spec['obstructions'], spec['apron_masts'] = _dof()
    spec['conflicts'] = CONFLICTS
    spec['open_questions'] = OPEN_Q
    return spec, fixtures


def _als(group, F, E, als, u_back, W_ft, e):
    """Standard ALS geometry (JO 6850.2C 200, Figures 2-1..2-4). Stations in ft from the landing threshold; lateral + = left."""
    def P(st, lat):
        return xz(F.at(-st * FT, lat * FT, True))
    h = 0.0  # height above the light plane is 0 by definition (plane = threshold elevation); renderer sets absolute elev
    white = {'white': dict(seen_by=E, emit_dir=u_back)}
    if als == 'ALSF2':
        cl = [P(st, k * 40.5 / 12) + [h, st] for st in range(100, 2401, 100) for k in (-2, -1, 0, 1, 2)]
        group('als_centreline_bar', E, 'ALS_PAR56_300W', 'pub+std', white, cl, note='24 bars x 5 white, 40.5 in spacing, stations 100..2400 ft (JO 6850.2C Fig 2-1); point = [x,z,h,station ft]; SSALR subset = stations 200,400..1400', ssalr_stations=list(range(200, 1401, 200)))
        side = [P(st, s * lat) + [h, st] for st in range(100, 901, 100) for s in (1, -1) for lat in (36, 41, 46)]
        group('als_side_row', E, 'ALS_PAR56_500W red', 'pub+std', {'red': dict(seen_by=E, emit_dir=u_back)}, side, note='9 side-row barrettes each side, 3 red lights 5 ft apart, in line with the TDZ rows (36/41/46 ft), stations 100-900 (Fig 2-1 note 1); ALSF-2 mode only')
        b500 = [P(500, s * lat) + [h, 500] for s in (1, -1) for lat in (13.875, 18.875, 23.875, 28.875)]
        group('als_500ft_bar', E, 'ALS_PAR56_300W', 'pub+std+inf', white, b500, note='4 white lights 5 ft apart each side, equidistant between side-row and centreline bars (Fig 2-1 note 2; offsets derived: inf); ALSF-2 mode only')
        b1000 = [P(1000, s * lat) + [h, 1000] for s in (1, -1) for lat in range(15, 51, 5)]
        group('als_1000ft_bar', E, 'ALS_PAR56_300W', 'pub+std', white, b1000, note='8 lights each side, 5 ft apart, 15..50 ft from CL -> 100-ft bar of 21 lights incl. the centreline bar (200a, Fig 2-1). SSALR mode uses 15..35 ft (70-ft crossbar, 200c)', ssalr_lateral_ft=[15, 20, 25, 30, 35])
        thr = [P(0, lat) + [h, 0] for lat in range(-145, 146, 5)]
        group('als_threshold_bar', E, 'green (semiflush FAA-E-2952 in pavement)', 'pub+std+inf', {'green': dict(seen_by=E, emit_dir=u_back)}, thr,
              note='green on 5-ft centres across the runway and ~45 ft beyond each edge, within 10 ft of the threshold (200a): 59 lights for a 200-ft runway (FAA page says 49 "typical" = 150-ft runway) - inf; SSALR mode: row on 10-ft centres coincident with the edge lights (200c)')
        fl = [P(st, 0) + [h, st, 24 - st // 100] for st in range(2400, 999, -100)]
        group('als_flasher', E, 'SFL_flasher', 'pub+std', {'white': dict(seen_by=E, emit_dir=u_back, aim_up_deg=6)}, fl,
              note='15 sequenced flashers stations 1000..2400 (200b); point = [x,z,h,station,sequence index 0 = first to fire]; 2 sequences/s; up to 4 ft below the plane and 5 ft outward (202c3); SSALR mode: flashers only at 1600..2400 (RAIL)')
        e['als_detail']['modes'] = dict(ALSF2='full', SSALR='threshold row 10-ft, bars 200..1400 @200 ft, 70-ft crossbar at 1000, RAIL 1600..2400', rule='jo7110 3-4-9')
        e['als_detail']['elevation_setting_deg'] = {'src': 'JO 6850.2C Table 2-1 (3 deg glide slope; shift by GS-3; 6..9 deg limits)', **{str(k): v for k, v in ALSF2_AIM.items()}}
    else:   # MALSR / MALSF (MALS core)
        cl = [P(st, k * 2.5) + [h, st] for st in range(200, 1401, 200) for k in (-2, -1, 0, 1, 2)]
        group('als_centreline_bar', E, 'MALS_PAR38', 'pub+std', white, cl, note='7 bars x 5 white, ~2.5 ft spacing, stations 200..1400 (JO 6850.2C 200d, Fig 2-3)')
        cb = [P(1000, s * lat) + [h, 1000] for s in (1, -1) for lat in (23, 25.5, 28, 30.5, 33)]
        group('als_1000ft_bar', E, 'MALS_PAR38', 'pub+std+inf', white, cb, note='two 5-light bars centred 28 ft either side -> 66-ft crossbar (200d, Fig 2-3 "28\'"; offsets inf)')
        thr = [P(0, lat) + [h, 0] for lat in range(-110, 111, 10)]
        group('als_threshold_bar', E, 'green PAR-56 300 W / L-850E in pavement', 'pub+std', {'green': dict(seen_by=E, emit_dir=u_back)}, thr,
              note='23 green lights on 10-ft centres coincident with the edge lights for a 200-ft runway, centre light on CL (200d; FAA MALSR page "18 to 33")')
        if als == 'MALSR':
            fl = [P(st, 0) + [h, st, (2400 - st) // 200] for st in range(2400, 1599, -200)]
            note = 'RAIL: 5 sequenced flashers 1600..2400 ft (200f, Fig 2-4)'
        else:
            fl = [P(st, 0) + [h, st, (1400 - st) // 200] for st in (1400, 1200, 1000)]
            note = 'MALSF: 3 sequenced flashers on the outermost bars 1000/1200/1400 (200e); ALS length 1400 ft'
        group('als_flasher', E, 'SFL_flasher', 'pub+std', {'white': dict(seen_by=E, emit_dir=u_back, aim_up_deg=6)}, fl, note=note + '; 2 sequences/s')
        e['als_detail']['elevation_setting_deg'] = {'src': 'JO 6850.2C Table 2-2 (MALS, 3 deg GS; shift by GS-3)', **{str(k): v for k, v in MALS_AIM.items()}}


ALSF2_AIM = {3000: 8.0, 2900: 7.9, 2800: 7.9, 2700: 7.8, 2600: 7.7, 2500: 7.7, 2400: 7.6, 2300: 7.6, 2200: 7.5, 2100: 7.4, 2000: 7.4, 1900: 7.3, 1800: 7.2,
             1700: 7.2, 1600: 7.1, 1500: 7.0, 1400: 7.0, 1300: 6.9, 1200: 6.9, 1100: 6.8, 1000: 6.7, 900: 6.7, 800: 6.6, 700: 6.5, 600: 6.5, 500: 6.4,
             400: 6.3, 300: 6.3, 200: 6.2, 100: 6.2, 0: 6.1}
MALS_AIM = {0: 3.1, 200: 3.2, 400: 3.3, 600: 3.4, 800: 3.4, 1000: 3.5, 1200: 3.6, 1400: 3.7}

RULES = {
    'runway_edge': dict(src='ac30j 2.3.1', colour='white; yellow in the caution zone (last 2000 ft or half length, whichever less) toward an instrument-approach end; red before a displaced threshold toward that approach',
                        lateral='2-10 ft outside full-strength pavement (10 ft recommended for jets)', spacing='<= 200 ft, uniform, symmetric', intersections='HIRL on CAT III runways: L-850C in-pavement at intersections to keep spacing; others: in-pavement if gap > 400 ft',
                        height_max_in=14, steps=5),
    'threshold_end': dict(src='ac30j 2.3.2', rule='2 groups of 4 (instrument) on 10-ft centres, outermost in line with edge lights, 2-10 ft before threshold; green outward / red inward; displaced threshold: green wing bars outboard (inner light in line with edge lights), red end lights at the pavement end'),
    'stopway': dict(src='ac30j 2.4', rule='unidirectional red in the takeoff direction along the stopway edges; SFO: NASR/CS publish no stopway (blast pads only) - do not draw'),
    'rcl': dict(src='ac30j 3.3.1, Fig A-34; AIM 2-1-5', spacing_ft=50, colour='white; alternating red/white from 3000 to 1000 ft remaining; red last 1000 ft', displaced='<= 700 ft displaced area: blanked in the approach direction'),
    'tdz': dict(src='ac30j 3.3.2, Fig A-35', rule='2 rows of 3-light bars, 100-ft spacing, 100..3000 ft, inner light 36 ft from CL, 5-ft light spacing, toed 4 deg'),
    'alsf2': dict(src='jo6850 200a-b, Fig 2-1, 202-206, T2-1, T2-3', summary='bars every 100 ft to 2400 ft, 1000-ft 100-ft-wide crossbar, 500-ft barrettes, red side rows 100-900 ft in line with TDZ, green threshold bar, 15 SFL 1000-2400'),
    'ssalr': dict(src='jo6850 200c, Fig 2-2; jo7110 3-4-9', summary='mode of ALSF-2 for better weather: bars 200..1400 every 200 ft, 70-ft crossbar at 1000, threshold row on 10-ft centres, RAIL flashers 1600..2400'),
    'mals': dict(src='jo6850 200d, Fig 2-3', summary='threshold row 10-ft centres (23 lights on 200-ft runway), 7 five-light bars 200..1400, 66-ft crossbar at 1000'),
    'malsf': dict(src='jo6850 200e', summary='MALS + 3 SFL on the three outermost bars'),
    'malsr': dict(src='jo6850 200f, Fig 2-4', summary='MALS + RAIL: 5 SFL at 1600..2400'),
    'papi': dict(src='jo6850 500-506, T5-1, T5-2; ac28h', rule='4 LHAs, left side, inboard LHA 50 ft +25/-0 from the edge, 30 ft +-1 apart, perpendicular to CL; sited so the visual path matches the published GPA/TCH (HG4: GPA source distance + 300 ft +50/-0); aiming +-30/10 arcmin (HG4 +-35/15)', obstacle_surface='OCS from 300 ft in front of the PAPI at (3rd LHA aim - 1 deg), +-10 deg, 4 SM', coverage='incandescent ~+-14 deg, LED +-10.5 deg azimuth'),
    'reil': dict(src='jo6850 400-407; ac51b', rule='2 synchronised flashers, 40 ft from edge in line with threshold lights; unidirectional aimed 10 deg up / 15 deg toe-out (120 fpm) or omni (60 fpm)'),
    'taxiway_centreline': dict(src='ac30j 4.3, T4-1; ac46f', colour='green; lead-on/lead-off alternate green/yellow from runway CL (green first) to one light beyond the runway hold or ILS critical-area hold (ending yellow); crossing a runway: alternating',
                               spacing_ft={'straight': [100, 50], 'curve_R_ge_1200': [100, 50], 'curve_R_400_1199': [50, 25], 'curve_R_75_399': [25, 12.5], 'acute_exit': [50, 50], 'note': '[>=1200 RVR, <1200 RVR]'},
                               lateral='<= 2 ft offset (2.5 ft to fixture CL), consistent side', beam='straight: parallel to path; curves bidirectional parallel to tangent, unidirectional toed-in to meet CL at ~4 spacings', sfo_status='SFO taxiway CL lights: NOT FAA-published per taxiway (X-Plane community data draws them widely) - unverified'),
    'taxiway_edge': dict(src='ac30j 2.5, T2-1, Fig A-16', colour='blue omni (L-861T elevated <= 14 in / L-852T inset)', spacing='straight > 200 ft: <= 200 ft; 100-200 ft sections: <= 100 ft; curves per Fig A-16 by radius; >= 3 lights on arcs > 30 deg', lateral='2-10 ft outside the full-strength pavement', sfo_status='unverified per taxiway'),
    'rgl_elevated': dict(src='ac30j 4.4.2, 4.4.5-4.4.6; ac46f L-804', rule='pair of alternately flashing yellow lamps each side of the taxiway at the runway hold, 10-17 ft outside the taxiway edge, aimed at the cockpit 150-200 ft before the hold, 5-10 deg up; 45-50 flashes/min', sfo_status='unverified'),
    'rgl_in_pavement': dict(src='ac30j 4.4.3-4.4.4, 4.8.6.2.5; ac46f L-852G', rule='row across the full taxiway 2 ft on the holding side of the hold marking, 9 ft 10 in centres, facing away from the runway; even/odd alternate, each 30-32 flashes/min', sfo_status='unverified'),
    'stop_bar': dict(src='ac30j 4.5; AIM 2-1-5', rule='in-pavement red L-852S 2 ft on the holding side of the hold marking, 9 ft 10 in centres + elevated red L-862S each side <= 10 ft outside the edge; required below 600 RVR on lit taxiways to active runways', sfo_status='SFO SMGCS plan / low-visibility routes not found - unverified'),
    'clearance_bar': dict(src='ac30j 4.7', rule='3 in-pavement yellow lights on 5-ft centres, 2 ft on the holding side of a taxiway/taxiway hold'),
    'beacon': dict(src='ac30j 6.1; ac12f; AIM', rule='white/green alternating, 24-30 flashes/min (installation AC & AIM) / 22-26 fpm (equipment spec), beam centre 5 deg, mounted above surrounding obstructions'),
    'obstruction': dict(src='ac7460 5.2, 5.5; ac43j', rule='<= 150 ft AGL: steady red L-810 (double at top); > 150 ft: flashing red L-864 (2000 cd, 30 fpm) at top, L-810(F) flashing at intermediate levels (150-350 ft), all synchronised'),
    'apron_flood': dict(src='ac5360 7.5 (current, no numbers; refers to IES RP-37-15); cancelled AC 150/5360-13 (1988) para 52 + Table 4-1', rule='mounted floodlights preferred, aimed/shielded against glare to pilots and ATC, overlapping sources from several directions; cancelled 1988 guidance: 5.0 fc (54 lx) at apron areas, 0.15 fc (1.6 lx) general AOA, mounts 25-50 ft at <= 200 ft spacing',
                        sfo='DOF-surveyed poles 60-157 ft AGL around the aprons (high masts), see apron_masts'),
    'wind_cone': dict(src='ac30j 6.6', rule='lit wind cones required for night air-carrier ops; constant illumination independent of lighting step; SFO: NASR "Y-L" (lighted), positions not FAA-published'),
}

CONFLICTS = [
    dict(id='rcl_coverage', text='Chart Supplement "HIRL CL" on all four runways and NASR CNTRLN_LGTS_AVBL_FLAG=Y at all 8 ends vs the lighting note on the airport diagram and plates "TDZL/RCLS Rwys 19L and 28R".',
         resolution='spec follows CS+NASR (RCL on all runways); flagged for owner/imagery confirmation', severity='medium'),
    dict(id='papi_28R_distance', text='NASR/CS/plate VGSI TCH 68 ft at 3.00 deg puts the 28R PAPI 1298 ft from the threshold; NAIP 2024 shows the LHAs at 1369 ft (71 ft further, = ILS GS source 1049 ft + 300 ft HG4 rule). 10L +30 ft, 28L +23 ft, 19R -31 ft, 19L -11 ft, 10R 0 ft.',
         resolution='use the observed LHA positions with the published angle; keep the published TCH as a label', severity='low'),
    dict(id='beacon_rate', text='Beacon flash rate: AC 150/5345-12F equipment 22-26 fpm vs AC 150/5340-30J 6.1.3 and AIM 24-30 fpm.', resolution='use 24 fpm (inside both)', severity='low'),
    dict(id='als_count', text='ALSF-2 green threshold lights: FAA pages "49" (typical, 150-ft runway) vs geometry rule (5-ft centres, 45 ft beyond each edge) = 59 on SFO 200-ft runways.', resolution='59 (rule), inf', severity='low'),
    dict(id='app_approach_lights', text='js/geo.js already lists only the 3 NASR ALS (28R ALSF2, 28L MALSR, 19L MALSF); its comment attributes "TDZL/RCLS Rwys 19L and 28R" to the Chart Supplement - that wording is on the AD/plates; the CS says "TDZL" under 28R and 19L.', resolution='comment fix only', severity='info'),
]
OPEN_Q = [
    'Rotating beacon position (not in NASR/CS/AD/X-Plane/cached OSM): ask the owner or find a photo; do not draw until located.',
    'Which ALS stations are lit on the 28L/28R piers: pier crossmembers (NAIP) sit at 700-1300 ft (28R) and 1000/1300 ft (28L) from the displaced thresholds; lights assumed at FAA stations from the landing threshold. Night imagery/photos would settle it.',
    'RCL on 10R/28L and 1L/19R (CS/NASR yes vs AD/plate note) - check a close photo or higher-resolution imagery for in-pavement fixtures.',
    'SFO taxiway lighting per taxiway (centreline green vs blue edge, lead-on/off colour coding, clearance bars, stop bars, elevated vs in-pavement RGLs): no FAA publication; X-Plane KSFO has 837 green-CL, 732 blue-edge, 108 amber hold-line and 81 alternating green/amber segments (community data). Needs the SFO SMGCS plan or imagery/photos.',
    'REIL style (unidirectional vs omnidirectional) at 10L/1L/1R.',
    'PAPI aiming set (standard vs height-group 4).',
    'Apron floodlight fixture photometry and aiming at SFO (no public source); DOF gives pole positions/heights only.',
    'SFO tower facility directives for lighting steps (JO 7110.65 tables are the default).',
]


def _dof():
    obst, masts = [], []
    if not os.path.exists(DOF_ZIP):
        return [dict(note='DOF not cached')], []
    lat0, lon0 = GF.ARP_LAT, GF.ARP_LON
    osm_masts = []
    if os.path.exists(OSM_JSON):
        d = json.load(open(OSM_JSON))
        osm_masts = [(e['lat'], e['lon']) for e in d['elements'] if e.get('tags', {}).get('man_made') == 'mast' and e['tags'].get('tower:type') == 'lighting']
    with zipfile.ZipFile(DOF_ZIP) as z:
        rows = csv.DictReader(io.TextIOWrapper(z.open('DOF.CSV'), encoding='latin-1'))
        for r in rows:
            try:
                la = float(r['LATDEC']); lo = float(r['LONDEC'])
            except ValueError:
                continue
            if abs(la - lat0) > 0.05 or abs(lo - lon0) > 0.06:
                continue
            x, zz = GF.wgs84_to_world(la, lo)
            dist = math.hypot(x, zz)
            if dist > 4500:
                continue
            typ = r['TYPE'].strip(); agl = int(r['AGL']); lt = r['LIGHTING'].strip()
            rec = dict(oas=r['OAS'], type=typ, agl_ft=agl, amsl_ft=int(r['AMSL']), lighting=lt, marking=r['MARKING'].strip(), accuracy=r['ACCURACY'].strip(),
                       verified=r['VERIFIED STATUS'].strip() == 'O', world=[rd(x, 1), rd(zz, 1)], dist_m=round(dist), study=r['FAA STUDY'].strip() or None, jdate=r['JDATE'].strip())
            if lt not in ('U', 'N'):
                std = ('L-864 flashing red at top (+ L-810(F) intermediate), inf from AC 70/7460-1N 5.5' if agl > 150 else 'L-810 steady red (double at top), inf from AC 70/7460-1N 5.2.2.1') if lt == 'R' else None
                rec['fixture_inferred'] = std
                obst.append(rec)
            if typ == 'POLE' and agl >= 60 and dist < 3000:
                near = min((math.hypot((la - a) * 110574, (lo - b) * 111320 * math.cos(math.radians(lat0))) for a, b in osm_masts), default=None)
                rec['osm_lighting_mast_within_15m'] = (near is not None and near < 15)
                masts.append(rec)
    obst.sort(key=lambda r: r['dist_m']); masts.sort(key=lambda r: r['dist_m'])
    return obst, masts


def main():
    spec, groups = build()
    spec['fixture_file'] = os.path.relpath(OUT_FIX, ROOT)
    spec['fixture_counts'] = {}
    for g in groups:
        spec['fixture_counts'][g['system']] = spec['fixture_counts'].get(g['system'], 0) + g['n']
    json.dump(spec, open(OUT_SPEC, 'w'), indent=1)
    fx = dict(schema='sfo3d.airfield_lighting_fixtures.v1', generated=spec['generated'], frame=spec['frame'], spec='tools/env/lighting_spec.json',
              colour_codes={k: v for k, v in COL.items()} | {'-': 'none/blanked'}, groups=groups)
    json.dump(fx, open(OUT_FIX, 'w'), separators=(',', ':'))
    print('wrote', OUT_SPEC, os.path.getsize(OUT_SPEC), 'bytes;', OUT_FIX, os.path.getsize(OUT_FIX), 'bytes')
    print('fixture counts', spec['fixture_counts'], 'total', sum(spec['fixture_counts'].values()))


if __name__ == '__main__':
    main()
