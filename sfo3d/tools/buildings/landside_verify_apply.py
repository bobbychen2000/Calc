"""Apply the adversarial fact-check (docs/research/buildings_landside.md '## Verification') to
tools/buildings/spec_landside.json: a `verification` record {verdict, evidence, date} on every checked value, refuted or
disputed values corrected with the previous value kept in `corrected` {old_value, old_note, reason}, new values,
sources, conflicts and open questions appended. Idempotent (re-running replaces the records, never re-corrects a value
twice). Called by tools/buildings/landside_verify.py (step 'apply') and at the end of build_spec_landside.py, so a
rebuilt spec keeps the corrections.

Evidence numbers come from out/buildings/landside/verify/verify.json (landside_verify.py; NAIP 2024 world raster,
FAA DOF.CSV 2026-11-03, SFO Museum WOF records, re-fetched sources in refs/cache/buildings/landside/src/verify_*).
Verdicts: CONFIRMED (an independent check agrees), PLAUSIBLE (consistent, not pinned tighter), DISPUTED (an
independent check conflicts), CORRECTED / REFUTED (shown wrong), NOT RE-CHECKED (source unreachable).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, 'spec_landside.json')
DATE = '2026-11-04'

V = {   # value id -> (verdict, evidence)
    'naip_epoch': ('CORRECTED', 'Not one moment for every building. The terminal-area and North Field frames cast noon '
                   'shadows to the north, but the Superbay frame was flown with the sun in the ESE: the ESE door facade '
                   'is sunlit and imaged as a 10-m bright band, and a 5-6 m shadow lies beyond the WNW roof edge '
                   '(verify.json superbay profile). That fits about 10:45-11:35 PDT. On 2024-05-20 the sun peaks at '
                   '72.59 deg at 13:06 PDT (NOAA algorithm, landside_verify.sun_pos), so cot e >= 0.313 everywhere.'),
    'parking_supply_2018': ('CONFIRMED', 'RADP App. E.1 re-read: "South Garage A 1,008 / 577", "South Garage G 1,151 / '
                            '254"; Central 6,459 = 5,674 public + 785 employee. The June 2017 sheet in the same appendix '
                            'splits ITA 902/683 and ITG 1,130/275 with the same totals.'),
    'cg_built': ('CORRECTED', 'RADP Historic Resources Evaluation (App. B/E, June 2018): Building 195 "Years constructed: '
                 '1963-1981"; "The first section ... designed by architect Edward B. Page ... constructed between 1963 and '
                 '1965"; "the first four floors occupying approximately the eastern third of the garage - was partially '
                 'demolished and absorbed by the later phases"; "Following the completion of the central parking garage '
                 'in 1980". App. A Build Year 1974 (note 1: "generally reflect the completion of construction"). SFO '
                 'Museum inception "1981~" (approximate). Dreyfuss + Blackford: completed 1981.'),
    'cg_levels': ('CONFIRMED', 'DEIR p. 2-34 "five-level"; D+B "five levels"; NOP "five-level, 81-foot-tall".'),
    'cg_height': ('CONFIRMED (number) / definition still unknown', 'DEIR p. 2-34 and NOP re-read: "five-level, '
                  '81-foot-tall". No NAIP check: elevated roadways surround the garage, so no shadow falls on grade, and '
                  'the 2-D scan is weak (best 5.0 m toward 143 deg).'),
    'cg_floor_area': ('CONFIRMED', 'DEIR Table: "Building 195 3,680,000".'),
    'cg_spaces': ('CONFIRMED', 'DEIR p. 2-34 "(6,460 parking spaces)".'),
    'cg_clearance': ('CONFIRMED', 'flysfo parking: "Maximum height 6\'6" (78")".'),
    'cg_void': ('CONFIRMED', 'D+B: "landscaped central open space 200 feet in diameter".'),
    'cg_void_obs': ('CONFIRMED', 'shapely re-computation: hole area 2,709.9 m2, area-equivalent diameter 58.74 m, minimum '
                    'enclosing 58.96 m, centre (-930.8, 275.5).'),
    'cg_footprint': ('CONFIRMED', 'shapely: 64,391.8 m2, minimum rectangle 275.3 x 275.0 m at 27.8 deg.'),
    'cg_airtrain_level': ('CONFIRMED', 'flysfo getting-around: "AirTrain Stations are located at Zones B, D and F. Take '
                          'the elevator or stairs to Level 5."'),
    'cg_dof': ('CONFIRMED', 'DOF.CSV 2026-11-03: 06-034812 POLE 109/112 1A, 06-034813 POLE 101/105 1A (both JDATE '
               '2013289); 06-039216 BLDG 130/136 4D, action A, JDATE 2016246 (added 2016).'),
    'garage_a_levels': ('CONFIRMED', 'Tutor Perini: "the $60 million, nine-level concrete parking garage" (singular, '
                        'for the 3,200 spaces of both).'),
    'garage_g_levels': ('CONFIRMED', 'as Garage A (one Tutor Perini sentence).'),
    'garage_a_airtrain_level': ('CONFIRMED', 'flysfo: "From International Garages A and G, take the elevator or stairs to '
                                'Level 7."'),
    'garage_g_airtrain_level': ('CONFIRMED', 'as Garage A.'),
    'garage_a_clearance': ('CONFIRMED', 'flysfo: "Maximum height 8\'2" (98")".'),
    'garage_g_clearance': ('CONFIRMED', 'as Garage A.'),
    'garage_a_footprint': ('CONFIRMED', 'shapely: 9,202.0 m2 in 2 parts, 281.8 x 54.7 m at 72.8 deg.'),
    'garage_g_footprint': ('CONFIRMED', 'shapely: 7,676.3 m2, 282.3 x 71.6 m at 63.6 deg.'),
    'garage_a_height': ('DISPUTED (the 25-30 m photo reading)', 'NAIP 2024: the ribbed WEST facade of the helix drum is '
                        'imaged as a band from the outline (flysfo ground trace; the drum base lies on it, drums.jpg) to the '
                        'drum top ring, 13.25 m median over 45 rows. k = 0.334 from the ITB high-mast-pole model, used '
                        'here INSIDE its calibrated range (x -1622..-1346; the drum is at x -1530). That gives a drum top '
                        'of 39.6 m (IQR 38.9-40.2; about +-2 m incl. k). The 2-D scan agrees on the direction (best '
                        '13.0 m due east). So the drum stands at about 38-40 m, which refutes "about three levels above '
                        'the AirTrain, 25-30 m" for the drum. The parking roof deck is still unmeasured: it can be lower '
                        'than the drum crown, which has "arched openings at the top".'),
    'garage_g_height': ('DISPUTED (the 25-30 m photo reading)', 'NAIP 2024 drum band 12.0 m median over 57 rows, k 0.319 '
                        '(x -1585, inside the pole range): drum top 37.6 m (IQR 37.6-39.9). The 2-D scan does not '
                        'reproduce the research\'s 12.0 m east peak as a 2-D maximum (its peaks are scattered: (-24, -2), '
                        '(-14.5, -5), (18, -15)); the 1-D value stands only as a 1-D peak. The roof deck is still '
                        'unmeasured.'),
    'ltp1_built': ('DISPUTED', 'RADP App. A: Building 795 Build Year 1994. SFO Museum: "1997~" (approximate).'),
    'ltp1_team': ('CONFIRMED', 'Willis: "designed by Joseph Chow & Associates, Inc. and constructed by Tutor Saliba".'),
    'ltp1_spaces': ('CONFIRMED', 'RADP App. E.1: "LTP Garage 1 3,109"; "LT Parking 3,109".'),
    'ltp1_clearance': ('CONFIRMED', 'flysfo: "Garage 1 - maximum height 6\'10" (82")".'),
    'ltp1_dof': ('CONFIRMED', 'DOF.CSV 2026-11-03: 06-035207 BLDG 86/98 1A inside the outline; 06-035206 BLDG 91/100 1A, '
                 '0.7 m outside it; JDATE 2013289; grade 9-12 ft AMSL. The shadow test below puts the north-end parapet '
                 'at about 16.5 m, so both points are about 10 m above it (towers or helix tops).'),
    'ltp1_levels': ('PLAUSIBLE', 'flysfo: "the station on Level 5 of the Long-Term Parking Garage"; DLR: "connector at '
                    'level 5". The shadow parapet height of about 16.5 m fits a roof deck at Level 5 (4 storeys of about '
                    '3.8 m plus a parapet). Not published.'),
    'ltp1_footprint': ('CONFIRMED', 'shapely: 14,428.9 m2, 177.0 x 93.7 m at 154.6 deg. A ground trace at the north end: '
                       'the roof edge imaged -2.75 m along the shadow direction, against -2.79 m predicted from the '
                       '5.5-m east lean.'),
    'ltp1_scan': ('CORRECTED', 'The east lean is 5.5 m (2-D scan, best peak (5.5, 0)), and the north-end shadow gives '
                  'h = 16.5 m, so k = 0.33 m per m here. The ITB model, extrapolated, gives 0.14. That model is invalid '
                  'in this frame, which explains the research\'s 37-m "contradiction".'),
    'ltp2_levels': ('CONFIRMED', 'DLR "six-level"; ENR "six-story"; DBIA "6-story"; Langan "6-story".'),
    'ltp2_floor_height': ('CONFIRMED', 'ENR: "A 12-ft floor height and reductions in the number of columns".'),
    'ltp2_roof_deck_h': ('PLAUSIBLE, NAIP inconclusive', 'The north-edge shadows run 3.5-5.5 m from the outline (h '
                         '11-17 m). But the imaged roof edge lies 1.75-3.25 m inside the outline, where the 1.8-m lean '
                         'predicts 0.5 m, so the outline is not a clean ground trace here. Neither method can confirm or '
                         'refute 60 ft.'),
    'ltp2_area': ('CONFIRMED as published', 'DLR 1,190,300 sq ft; ENR, DBIA and Langan "1.2 million".'),
    'ltp2_spaces': ('CONFIRMED', 'DLR, ENR, DBIA and Langan 3,600; CHS 3,500.'),
    'ltp2_structure': ('CORRECTED (wording)', 'DBIA: "The garage was divided into seismically separated structures" - '
                       '"separated", not "isolated" (base isolation is a different system), and no count. "Four" comes '
                       'only from the Buehler page, which now returns a script shell (74 chars of text), so it is '
                       '[unverified]. DLR confirms the lightwell, the 5,000-SF ground floor, the Morse-code tower and '
                       '"Louvered towers at three corners".'),
    'ltp2_built': ('CONFIRMED', 'DEIR: "Long-Term Parking Garage #2, which was completed in 2020 after publication of '
                   'the NOP"; ENR Best Projects Oct 2019; SFO Museum inception 2018.'),
    'ltp2_link': ('CONFIRMED', 'DLR: "Connected on the east to the existing Long Term Parking Garage No. 1 via a '
                  'vehicular connector at level 5".'),
    'ltp2_clearance': ('CONFIRMED', 'flysfo: "Garage 2 - maximum height 8\'2" (98")".'),
    'ltp2_footprint': ('CONFIRMED', 'shapely: 18,819.4 m2, 175.1 x 170.8 m at 64.6 deg.'),
    'rcc_identity': ('CONFIRMED', 'DEIR: "rental car center (RAC; Building 780)"; App. A: 779 station, 780 RCC, 782 QTA.'),
    'rcc_built': ('DISPUTED', 'RADP App. A Build Year 1998 for Buildings 779, 780 and 782. SFO Museum "2000~" (approximate).'),
    'rcc_levels': ('CONFIRMED', 'Tutor Perini "five-story"; Conrac "five levels of garage and customer service areas on '
                   'first and fourth floors".'),
    'rcc_height': ('CONFIRMED (number) / DISPUTED (as the roof height)', 'DEIR p. 2-36 re-read: "The existing 66-foot-'
                   'tall, 1,488,000-square-foot rental car center (RAC; Building 780) ready-return garage". The FAA DOF '
                   '1A survey (+-3 ft vertical) puts the roof outline at 54 ft at three points and 59 ft at one, all on '
                   'the west (AirTrain) side, so 66 ft is 7-12 ft above the surveyed roof edge. Read it as the tallest '
                   'element, not the parapet.'),
    'rcc_height_check': ('REFUTED', 'The 3.0-m peak was the third strongest. The 2-D scan ranks (8.5, 2.5) m first and '
                         '(5.5, 1.0) second, and the 1-D profile had the same choice. k = 0.154 is the ITB model '
                         'extrapolated 600 m west, and the model fails in the North Field (k 0.30-0.33 measured at the CAC '
                         'and LTP Garage 1, against 0.14-0.19 modelled). So the "agreement" with 66 ft is not evidence.'),
    'rcc_dof': ('CORRECTED (positions)', 'DOF.CSV 2026-11-03 re-mapped: all four BLDG points lie on the WEST (AirTrain) '
                'side. 06-035203 (54 ft) is near the SW corner (-2243.6, -960.6); 06-035204 (59 ft) is mid-west '
                '(-2260.2, -1042.3); 06-035205 (54 ft) is west (-2272.0, -1095.0); 06-035329 (54 ft) is NW (-2278.6, '
                '-1140.3). There is none at the NE corner. The TANK 06-034240 (60 ft) is 6.4 m west of the outline. '
                'Missed by the research: 06-035328 BLDG 34 ft 1A, 1.5 m outside the SE part at (-2119.2, -1087.0). '
                'Grade 9-11 ft AMSL.'),
    'rcc_area': ('CONFIRMED', 'DEIR: "1,488,000-square-foot". Divided by 5 levels this is 27,650 m2, against a 30,443 '
                 'm2 outline.'),
    'rcc_stalls': ('CONFIRMED', 'DEIR: "about 2,485 ready-return stalls".'),
    'rcc_footprint': ('CONFIRMED', 'shapely: 30,442.9 m2, 203.5 x 197.2 m.'),
    'rcc_future': ('CONFIRMED', 'DEIR (12): converted to "a public parking garage with about 3,700 spaces".'),
    'gh_identity': ('CONFIRMED', 'DEIR: "The Grand Hyatt at SFO (Building 55)".'),
    'gh_opened': ('CONFIRMED', 'Hyatt release dated October 7, 2019 (2019 release re-read).'),
    'gh_stories': ('CONFIRMED', 'DBIA "12-story high rise, Type 1 construction"; Webcor "12 levels above grade"; AGA '
                   '"12-story structure"; SF Chronicle "12-story".'),
    'gh_lobby_level': ('CONFIRMED', 'SF Chronicle: "Guests arriving by road will take elevators up to the fourth floor '
                       'lobby"; Webcor: "a fourth-floor light rail station".'),
    'gh_rooms': ('CONFIRMED', '2019 release: "351 rooms including 22 suites, 14,435 square feet"; Webcor 21 suites, 215 '
                 'stalls; 133,000 kWh PV.'),
    'gh_site': ('CONFIRMED (conflict stands)', '2019 release "4.2-acres"; 2016 release and Webcor "4.7-acre site".'),
    'gh_footprint': ('CONFIRMED (number) / not a ground trace of the slab', 'shapely: 3,311.3 m2, 107.4 x 57.6 m. On NAIP '
                     'the outline (src sfomuseum) covers the west crescent and podium, and the white PV roof of the slab '
                     'lies largely east of its concave edge (z_hyatt.jpg). The lean method cannot separate podium and '
                     'slab here.'),
    'gh_height': ('STILL UNKNOWN', 'No independent measure. The outline is not a ground trace of the slab (gh_footprint), '
                  'and the slab\'s north shadow falls on the elevated AirTrain station and roadways. The provisional 44 m '
                  '(40-48) stays [inf, low].'),
    'cac_identity': ('CONFIRMED', 'DEIR: "The Consolidated Administration Campus Phase 1 building (Building 674) was '
                     'completed in 2018".'),
    'cac_opened': ('CONFIRMED', 'MCK: "opened in the summer of 2018"; SFO Museum "2018-06".'),
    'cac_stories': ('CONFIRMED', 'Cavagnero "four-story steel building"; Webcor "four levels above grade"; MCK "four '
                    'story".'),
    'cac_floor_height': ('CONFIRMED', 'Perkins&Will: "increasing the floor-to-floor heights from 13 feet to 15 feet".'),
    'cac_height': ('CONFIRMED within +-1.5 m (NAIP shadow)', 'North-edge shadows on grade (edges 1, 2, 5) run 5.75-6.0 m '
                   'along the shadow direction from the outline. That gives h = 17.4-19.2 m for cot e 0.313-0.33 '
                   '(about +-1.6 m for +-0.5 m of reading). The outline is a ground trace there: the imaged roof edge '
                   'lies -2.25 to -2.75 m along u, against -1.7 to -2.6 m predicted from the 5.5-m east lean. That fits '
                   '4 x 15 ft = 18.3 m plus a parapet. The research\'s NAIP scan value of 28.6 m (extrapolated k 0.19) '
                   'is REFUTED: the lean here is 0.30 per m of height.'),
    'cac_area': ('CONFIRMED (conflict gone)', 'Cavagnero, MCK and Perkins&Will all read 135,000 sq ft in the 2026-11-04 fetch; the 136,000 is not found on the Perkins&Will page any more.'),
    'cac_footprint': ('CONFIRMED (number)', 'shapely: 4,752.5 m2, 141.3 x 51.4 m at 64.0 deg. NEW: 135,000 sq ft over 4 '
                      'floors is 3,135 m2 per floor, 34 % less than the outline. The outline (src unknown) probably '
                      'takes in the court, canopies or a larger ground floor.'),
    'cac_phase2': ('CONFIRMED', 'DEIR fn. 45 re-read (Case No. 2019-006583ETM, issued on May 17, 2021). The DEIR\'s '
                   'cumulative list: demolition of Building 676 (the former Design & Construction building) "is '
                   'scheduled to occur with construction of the Consolidated Administration Campus Phase 2 ... '
                   'anticipated to begin in 2025". It is not known whether construction has started.'),
    'sb_identity': ('CONFIRMED', 'DEIR: "an aircraft maintenance facility, known as the Superbay Hangar (Building 1060)".'),
    'sb_built': ('CONFIRMED (conflict stands)', 'Weitz "Originally built in 1969"; RADP App. A Build Year 1969; SFO Museum '
                 'negative "June 12, 1970" (construction); SFO Museum inception "1972~".'),
    'sb_bays': ('CONFIRMED', 'Weitz: "four maintenance bays, six levels of office space, and a centrally located '
                'workshop".'),
    'sb_height_dof': ('CONFIRMED', 'DOF.CSV 2026-11-03: 06-001451 BLDG 135/144 1A, lighting R, action C, JDATE 2011356. '
                      'It is not part of the 2013 batch. In the building frame the point sits at a = +17.9 m, b = -58.9 m: '
                      'the ESE edge of the spine near its SSW end.'),
    'sb_height_pub': ('CONFIRMED as published', 'Deep3DS "a 140-foot tall roof".'),
    'sb_interior_h': ('CONFIRMED', 'Weitz: "approximately 120 feet from the finished floor, which is the height of the '
                      'inside of the hangar".'),
    'sb_footprint_pub': ('CONFIRMED as published', 'Deep3DS "250,000 square foot-building footprint"; Weitz 420,550 sq ft.'),
    'sb_cantilever': ('CONFIRMED as published; the research\'s decomposition REFUTED', 'Deep3DS re-read: "light-gage '
                      'steel beams that cantilever over 230 feet from the center of the hangar in each direction". '
                      'Measured FROM THE CENTRE, so tip to tip is at least 140.2 m. It is not "2 x 70 + spine". '
                      'NAIP: the imaged roof is 165 m long (a = +-82.5 m = 271 ft from the centre line) and the spine is '
                      '32 m wide, so each side extends about 66.5 m (218 ft) beyond the spine. Missed by the research: '
                      'Deep3DS also says "a cantilever system having 50 foot wide structural bays" (see sb_roof_bays_obs).'),
    'sb_footprint': ('CONFIRMED', 'shapely: 22,201.4 m2, 165.9 x 134.5 m at 117.8 deg, centre (-93.9, -860.1).'),
    'sb_layout': ('CORRECTED', 'NAIP rectified roof (sb_rect.jpg, superbay_rhythm). Spine a = -14..+18 m, 32 m wide '
                  '(not 25-30). Each cantilever side is folded into 8 bays of 17.3 m along the spine: autocorrelation '
                  'period 17.0 m on both sides (r 0.73 / 0.69), fold spacing 17.4 / 17.5 m, each bay a light / shaded '
                  'pair with darker grey tip panels. The roof spans about 138 m along the spine. The "two bays of '
                  '~67 m" per side (aircraft positions) do not show on the roof and stay [inf]. The doors face WNW and '
                  'ESE: the ESE door facade is imaged as a sunlit 10-m band in this morning frame.'),
    'sb_roof_shift': ('CONFIRMED', '2-D scan best (-7.0, -7.5) m (bearing 317 deg), 10.3 m.'),
    'moc_large_hangar_h': ('CONFIRMED', 'DOF.CSV 2026-11-03: 06-035289 132/141, 06-035290 117/126, 06-035288 116/125, '
                           'all 1A, unlit (U), JDATE 2013289.'),
    'moc_other_dof': ('CONFIRMED', 'DOF.CSV 2026-11-03: 06-035303 107 ft (-1980, -1764), 06-035245 92 ft (-1943, -2273), '
                      '06-035292 79 ft (-2020, -1989), 06-035284 75 ft (-1782, -1690), 06-035327 74 ft (-1771, -1665), '
                      '06-035291 70 ft (-1926, -1854); all 1A BLDG.'),
    'moc_history': ('CONFIRMED (secondary)', 'PCAD: Austin Company, "325,000-square-foot", "c. 1947"; AirlineReporter: '
                    '"In 1948, United Airlines established a maintenance base". The SOM hangar is not covered here.'),
    'at_opened': ('CONFIRMED', 'Wikipedia "opened on February 24, 2003"; SFO Museum station inception 2003-02-24; SF-03-10 '
                  '(dated Feb 27, 2003): Mayor Brown "will officially open ... on Monday, March 3, 2003"; fact sheet '
                  '"Opening March 2003", "$430 million".'),
    'at_team': ('CONFIRMED', 'Fact sheet: Parsons Brinckerhoff / MGE Eng. / Manna (guideways), Lea + Elliott, '
                'Tutor-Saliba, Bombardier.'),
    'at_vehicle': ('CONFIRMED', 'Fact sheet: "Vehicle Size 9\'3" wide x 39\'6" long", 32,000 pounds, Teal Blue Metallic, '
                   '38 vehicles, centre guide beam, 600 VAC rectified to 300 VDC, 5 substations; 2021 release: 41 '
                   'vehicles.'),
    'at_length': ('CONFIRMED as published / PLAUSIBLE reading', 'Fact sheet "Five miles of two independent loops"; 2021 '
                  'release "over 6 miles of fully automated concrete guideways"; Wikipedia "three miles (4.8 km)". The '
                  'rail polygon\'s centreline is 7.8 km = 4.9 mi as a route, extension included, so "over 6 miles" '
                  'probably counts track on the twin sections.'),
    'at_ext': ('CONFIRMED', '2021 release, Airport World and PTT "1,900 feet"; PGH Wong "1,900-foot guideway extension"; '
               'PTT "US$172m project, which launched in August 2016"; "$259M construction project".'),
    'at_height_ext': ('CONFIRMED as published', '2021 release: "running 50 feet above a public roadway".'),
    'at_height_general': ('CONFIRMED as published (conflict stands)', 'RADP App. B: "elevated 35 to 40 feet above ground '
                          'at its highest point".'),
    'at_rail_polygon': ('CONFIRMED (reproduced)', 'landside_naip_measure.rail() re-run: 57,727 m2; width p10-p90 '
                        '4.5 / 4.8 / 5.1 / 9.5 / 11.5 m; centreline 7,818 m.'),
    'at_maintenance': ('CONFIRMED', 'Fact sheet: "24-hour control room, five service bays, an AirTrain test track and a '
                       'two-level employee parking structure".'),
}

V.update({
    'garage_a_built': ('CONFIRMED', 'RADP App. A: "95 N/A Parking Garage A Parking 2000"; SFO Museum 2000.'),
    'garage_g_built': ('CONFIRMED', 'RADP App. A: "495 N/A Parking Garage G Parking 2000"; SFO Museum 2000.'),
    'gh_team': ('CONFIRMED', 'Webcor: "Hornberger+Worstell, ED2 International"; DBIA design-build award.'),
    'cac_team': ('CONFIRMED', 'Cavagnero: "in collaboration with Perkins + Will and Webcor"; MCK: "the $84 Million '
                 'project", ground-breaking September 1, 2016.'),
    'cac_form': ('CONFIRMED', 'Cavagnero: "A bend in the main structure, visible from the outside, provides a cloistered '
                 'interior protected space"; "the southern and western exposures are shaded with exterior louvers".'),
    'ltp2_team': ('CONFIRMED (cost)', 'DBIA: "This $154.6 million parking garage".'),
    'sb_future': ('CONFIRMED', 'DEIR: "construction of a new 95-foot-tall, 181,000-square-foot standalone hangar".'),
    'at_stations': ('CONFIRMED', 'Fact sheet "Number of Stations 9", "Spacing 0.3 miles"; Wikipedia: the Grand Hyatt '
                    'infill station ($15 million); the T3 station closed from November 4, 2025 to 2027; flysfo station '
                    'levels 4 / 5 / 7.'),
    'moc_identity': ('NOT RE-CHECKED', 'no United or SFO building record was found; NAIP outlines only.'),
})
DEFAULT = ('NOT RE-CHECKED', 'Not re-checked in the 2026-11-04 fact-check. Roof-car counts were not re-run (+-30 %; see '
           'naip_epoch: the frames differ in time). Photo-based facade notes rest on Commons photos that could not be '
           're-fetched (Commons API HTTP 429).')

CORRECT = {   # value id -> (field updates, reason); old value/note kept in 'corrected'
    'naip_epoch': (dict(value='2024-05-20; NOT one moment: noon-like north shadows over the terminal area and the North '
                              'Field (sun el <= 72.59 deg, cot e 0.313-0.33 for 12:40-13:40 PDT), a morning sun from '
                              'the ESE in the Superbay frame (about 10:45-11:35 PDT)', confidence='medium'),
                   'frames differ in time (Superbay frame: sunlit ESE facade, WNW shadow)'),
    'cg_built': (dict(value='1963-1981', unit='years (phased)', range=[1963, 1981], confidence='high',
                      note='Built in phases. The first section (Edward B. Page, with Gould & Degenkolb, 1963-65; the '
                           'first four floors over about the eastern third) was partially demolished and absorbed into '
                           'the 1969-1981 enlargement by the San Francisco Airport Architects (Dreyfuss + Blackford with '
                           'John Carl Warnecke & Associates), completed 1980-81. RADP App. A Build Year 1974. It is not a '
                           'separate earlier garage that stood until 1981.'),
                 'RADP Historic Resources Evaluation (Years constructed 1963-1981; first section partially demolished '
                 'and absorbed)'),
    'ltp1_built': (dict(range=[1994, 1997], confidence='low',
                        note='RADP App. A Build Year 1994 ("generally reflect the completion of construction"); SFO '
                             'Museum inception 1997~ (approximate).'),
                   'RADP App. A gives 1994'),
    'rcc_built': (dict(range=[1998, 2000], confidence='low',
                       note='RADP App. A Build Year 1998 for 779 / 780 / 782; SFO Museum inception 2000~ (approximate); '
                            'AirTrain service from Feb 2003.'),
                  'RADP App. A gives 1998'),
    'rcc_height_check': (dict(value=None, value_m=None, confidence='none',
                              note='WITHDRAWN. The 3.0-m peak was not the strongest, and the extrapolated k is invalid '
                                   'in the North Field. The FAA DOF 1A roof-outline points give 54 ft (16.5 m, three '
                                   'points) and 59 ft (18.0 m, one point) on the west side: use them for the parapet.',
                              parapet_dof_m=[16.46, 17.98]),
                         'cherry-picked third peak and an invalid lean model'),
    'rcc_dof': (dict(value='DOF BLDG 54 ft (06-035203 near the SW corner, 06-035205 west, 06-035329 NW) and 59 ft '
                           '(06-035204 mid-west) AGL, all on the west (AirTrain) side of the roof outline; TANK 60 ft '
                           '(06-034240) 6.4 m west of the outline at the AirTrain station; BLDG 34 ft (06-035328) 1.5 m '
                           'outside the SE part. All 1A, JDATE 2013289, grade 9-11 ft AMSL.'),
                'positions re-mapped (no NE-corner point; 34-ft point missed)'),
    'garage_a_height': (dict(drum_top_m=39.6, drum_top_range_m=[38.0, 41.5], range_m=[25, 41.5],
                             note='NOT PUBLISHED. Helix drum top (west end) 39.6 m: NAIP west-facade band 13.25 m '
                                  'median, divided by the ITB pole k 0.334 (inside the calibrated x range). The parking '
                                  'roof deck is still unmeasured; it is at or below the drum crown. The earlier "25-30 m '
                                  'from the AirTrain photo" is refuted for the drum.'),
                        'NAIP drum band, independent of the outline-wide scan'),
    'garage_g_height': (dict(drum_top_m=37.6, drum_top_range_m=[36.0, 40.0], range_m=[25, 40.0],
                             note='NOT PUBLISHED. Helix drum top (west end) 37.6 m: NAIP west-facade band 12.0 m '
                                  'median, divided by k 0.319 (inside the pole range). The 2-D scan does not reproduce '
                                  'the 12.0 m east peak as a 2-D maximum. The roof deck is still unmeasured.'),
                        'NAIP drum band'),
    'ltp1_scan': (dict(value='east lean 5.5 m = 0.33 per m of height (north-end parapet 16.5 m by shadow); ITB k model '
                             'invalid here', confidence='medium'),
                  'lean measured with a shadow-derived height'),
    'ltp2_structure': (dict(value='seismically separated structures (number: "four" per Buehler, [unverified]); '
                                  'central lightwell; open cast-in-place concrete frame; ground floor 5,000 sq ft '
                                  'customer space; elevator tower with mirrored glass panels spelling "San Francisco" in '
                                  'Morse code; louvered towers at three corners'),
                       '"isolated" is not in any source (DBIA: "separated"); the count is from an unreadable page'),
    'cac_height': (dict(range_m=[17.4, 19.5], shadow_obs_m=[17.4, 19.2],
                        note='4 x 15 ft = 60 ft (18.3 m) to the roof, plus a parapet. NAIP north shadows on grade: '
                             'h = 17.4-19.2 m (edges 1, 2, 5; the outline is a ground trace there). The old NAIP scan '
                             'value of 28.6 m was refuted (k model invalid: lean 0.30 per m).'),
                   'shadow measurement narrows the range; the old scan value is refuted'),
    'sb_layout': (dict(value='central spine (offices/workshop) along the 27.8-deg grid, 32 m wide (a = -14..+18 m from '
                             'the outline centre); cantilevered folded roofs to the WNW and ESE, each about 66.5 m '
                             'beyond the spine (roof 165 m overall); 8 roof bays of 17.3 m along the spine per side '
                             '(about 138 m); doors on the WNW and ESE faces', tag='obs', confidence='medium',
                       spine_width_m=32.0, roof_bay_m=17.3, roof_bays_per_side=8),
                  'NAIP rectified roof: spine width, bay rhythm, cantilever beyond the spine'),
}

NEW_VALUES = [
    dict(id='sb_roof_bays_obs', building='superbay', group='structure', value=17.3, unit='m', value_m=17.3, tag='obs',
         confidence='medium', src=['naip', 'verify'],
         note='Roof fold rhythm along the 27.8-deg spine axis, both cantilever sides: autocorrelation 17.0 m '
              '(r 0.73 / 0.69), fold spacing 17.4 / 17.5 m (median of 7). That is 8 bays over about 138 m. CONFLICTS '
              'with Deep3DS "50 foot wide structural bays" (15.24 m, 9 bays over 137 m). The relief displacement cannot '
              'stretch the period by 13 %.'),
    dict(id='sb_structural_bays_pub', building='superbay', group='structure', value=50, unit='ft', value_m=15.24,
         tag='pub', confidence='low', src=['deep3ds_superbay'],
         note='"a cantilever system having 50 foot wide structural bays" (Deep3DS); see sb_roof_bays_obs.'),
    dict(id='ltp1_parapet_obs', building='ltp_garage_1', group='height', value=16.5, unit='m', value_m=16.5, tag='obs',
         confidence='medium', src=['naip', 'verify'], range_m=[15.9, 16.8],
         note='North-end parapet by shadow: the shadow runs 5.25 m from the outline along the shadow direction (edges '
              '10, 12), and cot e is 0.313-0.33. The outline is a ground trace there: the roof edge is imaged -2.75 m '
              'along u, against -2.79 m predicted from the 5.5-m east lean. DOF 86/91 ft are about 10 m higher '
              'elements.'),
    dict(id='cg_first_section', building='central_garage', group='history', value='1963-1965', tag='pub',
         confidence='high', src=['radp_appx'],
         note='First section by Edward B. Page / Gould & Degenkolb: four floors over about the eastern third, partially '
              'demolished and absorbed by the 1969-1981 enlargement (RADP Historic Resources Evaluation).'),
]

NEW_SOURCES = {
    'verify': dict(title='tools/buildings/landside_verify.py -> out/buildings/landside/verify/verify.json (adversarial '
                         'fact-check, 2026-11-04)', url='tools/buildings/landside_verify.py', type='own measurement'),
}

NEW_CONFLICTS = [
    'Superbay roof bays: Deep3DS "50 foot wide structural bays" (15.24 m) against the NAIP roof fold rhythm of 17.3 m '
    '(8 per side over about 138 m).',
    'RCC height: DEIR "66-foot-tall" against the FAA DOF 1A roof outline at 54 ft (3 points) and 59 ft (1 point).',
    'Build years: RADP App. A (Build Year = completion) gives LTP Garage 1 1994, RCC / station / QTA 1998 and the '
    'Central garage 1974 (constructed 1963-1981). SFO Museum gives 1997~, 2000~ and 1981~.',
    'NAIP lean model: the ITB pole model k(x) = 0.7553 + 0.0002753 x gives 0.14-0.19 in the North Field, but the CAC '
    'and LTP Garage 1 measure 0.30-0.33 per m (shadow heights with the 2-D lean). Each NAIP frame has its own nadir.',
    'CAC: 135,000 sq ft over 4 floors (3,135 m2 per floor) against a 4,752 m2 outline.',
]

NEW_OPEN = [
    'Garages A / G: the roof-deck height (the NAIP drum tops are 37.6-39.6 m). A NAIP measurement of the deck needs a '
    'free deck edge on the west, or a north shadow on grade; or an SFO drawing.',
    'Superbay: is the 17.3 m roof fold the structural bay (Deep3DS says 50 ft)? Is a drawing or a photo with a scale '
    'available?',
    'Photo licences: the Commons API was rate-limited (HTTP 429) on 2026-11-04. The 13 reference photos were not '
    're-checked.',
]


def apply(path=SPEC):
    spec = json.load(open(path))
    vals = {v['id']: v for v in spec['values']}
    for vid, v in vals.items():
        if vid in {nv['id'] for nv in NEW_VALUES}:
            v['verification'] = dict(verdict='NEW (fact-check)', evidence=v.get('note', ''), date=DATE)
            continue
        verdict, ev = V.get(vid, DEFAULT)
        v['verification'] = dict(verdict=verdict, evidence=ev, date=DATE)
    for vid, (upd, reason) in CORRECT.items():
        v = vals.get(vid)
        if v is None:
            continue
        if 'corrected' not in v:
            v['corrected'] = dict(old={k: v.get(k) for k in upd}, reason=reason, date=DATE)
        v.update(upd)
    have = set(vals)
    for nv in NEW_VALUES:
        if nv['id'] not in have:
            nv = dict(nv, verification=dict(verdict='NEW (fact-check)', date=DATE))
            spec['values'].append(nv)
        else:
            vals[nv['id']].update(nv)
    spec['sources'].update(NEW_SOURCES)
    for c in NEW_CONFLICTS:
        if c not in spec['conflicts']:
            spec['conflicts'].append(c)
    for q in NEW_OPEN:
        if q not in spec['open_questions']:
            spec['open_questions'].append(q)
    spec['verification'] = dict(date=DATE, doc='docs/research/buildings_landside.md ## Verification',
                                tool='tools/buildings/landside_verify.py + landside_verify_apply.py',
                                checked=len(V), corrected=len(CORRECT), new_values=len(NEW_VALUES))
    spec['status'] = (spec['status'].split(' | ')[0] + ' | adversarially fact-checked ' + DATE +
                      ' (see the doc\'s Verification section)')
    bad = [(v['id'], s) for v in spec['values'] for s in v['src'] if s not in spec['sources']]
    assert not bad, bad
    json.dump(spec, open(path, 'w'), indent=1, ensure_ascii=False)
    print('applied verification to', path, len(V), 'checked,', len(CORRECT), 'corrected,', len(NEW_VALUES), 'new')


if __name__ == '__main__':
    apply()
