"""Build tools/buildings/spec_landside.json - the research spec for SFO's landside buildings (parking garages, AirTrain
guideway and stations, Grand Hyatt at SFO, Rental Car Center, Consolidated Administration Campus / SFO Museum
facilities, and the maintenance hangars seen from the airfield: Superbay and the United Airlines MOC).

Research draft for the owner's review (docs/research/buildings_landside.md). Nothing here is approved for drawing or
3-D yet. Every value carries: value, unit (value_m when a length), tag pub|obs|inf, confidence, source ids (see
SOURCES) and a note stating what exactly the number is and how it was obtained.
  pub = transcribed from an original or primary source (SFO, SF Planning EIR, FAA, architect/engineer/contractor, trade
        press quoting them); obs = measured by us (NAIP 2024, SFO Museum geometry, FAA DOF, licensed photos) with the
        method stated; inf = derived by us from pub/obs under a stated assumption - must be confirmed.
Measured numbers are read from tools/buildings/landside_naip_measurements.json (tools/buildings/landside_naip_measure.py).
Downloads (web pages, PDFs, Commons thumbnails) are in refs/cache/buildings/landside/ (gitignored).

Usage: python3 tools/buildings/build_spec_landside.py   -> tools/buildings/spec_landside.json
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'landside_naip_measurements.json')))
B = M['buildings']
FT = 0.3048
C = 'refs/cache/buildings/landside/src/'

SOURCES = {
    'radp_deir': dict(title='SF Planning, SFO Recommended Airport Development Plan (RADP) Draft EIR, April 2025, Case No. '
                            '2017-007468ENV, SCH 2019050013 (Ch. 2 Project Description, pp. 2-5..2-40)',
                      url='https://ceqanet.lci.ca.gov/2019050013/3/Attachment/11Kyqq', type='primary (CEQA, lead agency '
                      'SF Planning; sponsor SFO)', cache=C + 'radp_deir_2025.pdf'),
    'radp_appx': dict(title='RADP Draft EIR Appendices A-G, April 2025 (A: NOP 2019; B: Initial Study incl. E.2 '
                            'Aesthetics and visual simulations; E.1: "Existing SFO Parking Information", memo to SFO of '
                            '26 Jun 2018, Table 1-1 Existing parking supply)',
                      url='https://files.ceqanet.lci.ca.gov/251582-3/attachment/BG1oT278S0KLo_J9GLLCoEtRiJMVmoDMo7ymfZHbivTCRYzqkOIfPVdzDW3l6fyMJ27ugjUEP2nsm6ux0',
                      type='primary (CEQA)', cache=C + 'ceqa_251582-3.pdf'),
    'radp_nop': dict(title='RADP Notice of Preparation of an EIR, 22 May 2019', type='primary (CEQA)',
                     url='https://files.ceqanet.lci.ca.gov/251582-2/attachment/Fs6wnks-wJqMOZWG2LguShqJHLMXyIWsfRYSvrFzGL2VYNtz1bweGuhFgqhUz8wAU_5X4oeKzE5JBCE10',
                     cache=C + 'ceqa_251582-2.pdf'),
    'radp_rtc': dict(title='RADP Responses to Comments, Nov 2025 (Final EIR certification hearing 20 Nov 2025)',
                     type='primary (CEQA)', url='https://files.ceqanet.lci.ca.gov/251582-5/attachment/jsWJ52D74QjjdNqbpa6eaOYsA8uWxChG8Na2rOMEJIawrjDxWROUXrF_juktwcfHO_9zmEpTVMqcQvaJ0',
                     cache=C + 'ceqa_251582-5.pdf'),
    'sfplan_nod_cac': dict(title='SF Planning Notice of Determination, 1986.638E Addendum 6, SFO Consolidated '
                                 'Administration Campus, Case 2019-006583ETM, final approval 18 Apr 2023, filed 20 Apr 2023 (6.6-acre site)',
                           url='https://media.api.sf.gov/documents/23.0000024_SFO_Consolidated_Administration_Campus.pdf',
                           type='primary (CEQA notice; scanned)', cache=C + 'sfgov_cac_23-0000024.pdf'),
    'db_1981': dict(title='Dreyfuss + Blackford Architecture, "San Francisco International Airport Parking Structure" '
                          '(completed 1981, JV with John Carl Warnecke and Associates)',
                    url='https://www.dreyfussblackford.com/project/san-francisco-international-airport-parking-structure/',
                    type='architect', cache=C + 'db_central_garage.html'),
    'flysfo_parking': dict(title='flysfo.com Parking (garage height limits)', url='https://www.flysfo.com/to-from/parking',
                           type='primary (SFO)', cache=C + 'flysfo_parking2.html'),
    'flysfo_ltp': dict(title='flysfo.com Long-Term Parking', url='https://www.flysfo.com/to-from/parking/long-term',
                       type='primary (SFO)', cache=C + 'flysfo_ltp.html'),
    'flysfo_around': dict(title='flysfo.com Getting Around SFO (AirTrain station levels)',
                          url='https://www.flysfo.com/to-from/getting-around-sfo', type='primary (SFO)',
                          cache=C + 'flysfo_getting_around.html'),
    'flysfo_airtrain_fs': dict(title='SFO AirTrain Fact Sheet, 7/03', type='primary (SFO)',
                               url='https://www.flysfo.com/sites/default/files/default/download/about/news/pressres/fact-sheet/pdf/AirTrain_Fact_Sheet.pdf',
                               cache=C + 'flysfo_airtrain_factsheet_2003.pdf'),
    'flysfo_pr_2003': dict(title='SFO news release SF-03-10 "Mayor Brown to inaugurate SFO AirTrain system", 27 Feb 2003',
                           url='https://www.flysfo.com/sites/default/files/SF-03-10.pdf', type='primary (SFO)',
                           cache=C + 'flysfo_SF-03-10.pdf'),
    'flysfo_pr_2021': dict(title='SFO news release "SFO Completes AirTrain Extension to Long-Term Parking", 5 May 2021',
                           url='https://www.flysfo.com/media/press-releases/sfo-completes-airtrain-extension-long-term-parking',
                           type='primary (SFO)', cache=C + 'flysfo_pr_airtrain_ext_2021.html'),
    'aw_airtrain_leed': dict(title='Airport World, "SFO\'s newest AirTrain stations earn LEED gold certification" (quotes SFO)',
                             url='https://airport-world.com/sfos-newest-airtrain-stations-earn-leed-gold-certification/',
                             type='trade press', cache=C + 'aw_airtrain_leed.html'),
    'ptt_2021': dict(title='Passenger Terminal Today, "Skanska completes AirTrain extension at San Francisco International Airport"',
                     url='https://www.passengerterminaltoday.com/news/accessibility/skanska-completes-airtrain-extension-at-san-francisco-international-airport.html',
                     type='trade press', cache=C + 'ptt_airtrain.html'),
    'pghwong': dict(title='PGH Wong Engineering, SFO AirTrain Extension Project (CM)', type='consultant',
                    url='https://pghwong.com/project/san-francisco-international-airport-sfo-airtrain-extension-project/',
                    cache=C + 'pghwong_airtrain.html'),
    'wiki_airtrain': dict(title='Wikipedia, AirTrain (San Francisco International Airport), rev. 13 May 2026',
                          url='https://en.wikipedia.org/wiki/AirTrain_(San_Francisco_International_Airport)',
                          type='secondary (used only to find primary refs)', cache=C + 'wiki_airtrain.html'),
    'tutor_itb': dict(title='Tutor Perini, SFO International Terminal (incl. the International Terminal parking garage)',
                      url='https://www.tutorperini.com/projects/aviation/sfo-international-terminal/', type='contractor',
                      cache=C + 'tutor_itb.html'),
    'tutor_rcc': dict(title='Tutor Perini, SFO Rental Car Center', url='https://www.tutorperini.com/projects/aviation/sfo-rental-car-center/',
                      type='contractor', cache=C + 'tutor_rcc.html'),
    'conrac_sol': dict(title='Conrac Solutions, SFO Consolidated Rental Car Facility', url='https://www.conracsolutions.com/project/sfo',
                       type='operator/consultant', cache=C + 'conrac_rcc.html'),
    'willis_ltp1': dict(title='Willis Construction, "SFO Long Term Parking Garage" (architectural precast; architect Joseph '
                              'Chow & Associates, contractor Tutor Saliba)', url='https://willisconstruction.com/sfo-long-term-parking-garage/',
                        type='subcontractor', cache=C + 'willis_ltp.html'),
    'dlr_ltp2': dict(title='DLR Group, San Francisco International Airport Long-Term Parking Garage (No. 2)',
                     url='https://www.dlrgroup.com/work/san-francisco-international-airport-long-term-parking-garage/',
                     type='architect', cache=C + 'dlr_ltp2.html'),
    'buehler_ltp2': dict(title='Buehler Engineering, SFO Long-Term Parking Garage No. 2', url='https://buehlerengineering.com/project/sfo-ltpg2',
                         type='structural engineer', cache=C + 'buehler_ltp2.html'),
    'enr_ltp2': dict(title='ENR California Best Projects 2019, "SFO Long-Term Parking Garage 2: Airport/Transit", 30 Sep 2019',
                     url='https://www.enr.com/articles/47644-sfo-long-term-parking-garage-2-airporttransit', type='trade press',
                     cache=C + 'enr_ltp2.html'),
    'dbia_ltp2': dict(title='DBIA, San Francisco International Airport Long Term Garage 2', url='https://dbia.org/project/san-francisco-international-airport-long-term-garage/',
                      type='industry award', cache=C + 'dbia_ltp2.html'),
    'langan_ltp2': dict(title='Langan, SFIA Long Term Parking Garage No. 2', url='https://www.langan.com/portfolio/sfo-parking-garage-2',
                        type='geotechnical engineer', cache=C + 'langan_ltp2.html'),
    'chs_ltp2': dict(title='CHS Consulting Group, SFO Long-Term Parking Garage #2', type='traffic consultant',
                     url='http://www.chsconsulting.net/portfolio/design-build-projects/san-francisco-international-airport-long-term-parking-garage-2/',
                     cache=C + 'chs_ltp2.html'),
    'hyatt_pr_2019': dict(title='Hyatt / SFO news release "Hyatt and San Francisco International Airport Proudly Announce '
                                'Opening of Grand Hyatt at SFO", 7 Oct 2019', url='https://newsroom.hyatt.com/news-releases?item=123896',
                          type='primary (owner + operator)', cache=C + 'hyatt_pr.html'),
    'hyatt_pr_2016': dict(title='Hyatt news release "Hyatt and San Francisco International Airport Announce Plans for a '
                                'Grand Hyatt Hotel", Jan 2016', url='https://newsroom.hyatt.com/012216Hyatt-And-San-Francisco-International-Airport-Announce-Plans-For-A-Grand-Hyatt-Hotel',
                          type='primary (owner + operator)', cache=C + 'hyatt_pr2016.html'),
    'dbia_hyatt': dict(title='DBIA, Grand Hyatt at SFO (2020 award)', url='https://dbia.org/project/grand-hyatt-at-sfo/',
                       type='industry award (team submission)', cache=C + 'dbia_hyatt.html'),
    'webcor_hyatt': dict(title='Webcor, Grand Hyatt at San Francisco International Airport', type='design-builder',
                         url='https://www.webcor.com/projects/grand-hyatt-at-san-francisco-international-airport-sfo',
                         cache=C + 'webcor_hyatt.html'),
    'aga_hyatt': dict(title='Architectural Glass & Aluminum, SFO Grand Hyatt', url='https://www.aga-ca.com/portfolio/sfo-grand-hyatt/',
                      type='curtain-wall subcontractor', cache=C + 'aga_hyatt.html'),
    'hw_hyatt': dict(title='Hornberger + Worstell, Grand Hyatt at SFO', url='https://www.hornbergerworstell.com/projects/grand-hyatt-sfo/',
                     type='architect', cache=C + 'hw_hyatt.html'),
    'sfchron_hyatt': dict(title='SF Chronicle / SFGate (Chris McGinnis), "12-story Hyatt hotel rising next to SFO runways", '
                                '2 Oct 2018', url='https://www.sfchronicle.com/chris-mcginnis/article/Grand-Hyatt-hotel-SFO-construction-13276463.php',
                          type='press (topping-out report, SFO photos)', cache=C + 'sfchron_hyatt.html'),
    'cavagnero_cac': dict(title='Mark Cavagnero Associates, SFO Consolidated Administration Campus',
                          url='https://www.cavagnero.com/project/sfo-consolidated-administration-campus/', type='architect',
                          cache=C + 'cavagnero_cac.html'),
    'pw_cac': dict(title='Perkins&Will, SFO Consolidated Administration Campus', url='https://perkinswill.com/project/sfo-consolidated-administration-campus/',
                   type='architect', cache=C + 'pw_cac.html'),
    'webcor_cac': dict(title='Webcor, SFO Consolidated Administration Campus', url='https://www.webcor.com/projects/sfo-consolidated-administration-campus',
                       type='design-builder', cache=C + 'webcor_cac.html'),
    'mck_cac': dict(title='MCK Americas, Consolidated Administration Campus (CAC), Phase I', url='https://www.mckinc.net/buildings-hospitality/sfo-cac',
                    type='construction manager', cache=C + 'mck_cac.html'),
    'weitz_superbay': dict(title='Weitz, San Francisco International Airport Superbay Hangar (fire-suppression replacement)',
                           url='https://www.weitz.com/projects/san-francisco-international-airport-superbay-hangar/',
                           type='contractor', cache=C + 'weitz_superbay.html'),
    'weitz_superbay_story': dict(title='Weitz, "Building A Legacy: SFO Superbay Hangar"', url='https://www.weitz.com/building-a-legacy-sfo-superbay-hangar/',
                                 type='contractor', cache=C + 'weitz_superbay_story.html'),
    'deep3ds_superbay': dict(title='Deep Design Studio, "Case Study: San Francisco Superbay Hangar for American and United '
                                   'Airlines" (3-D laser scan for Berger Steel)', url='https://www.deep3ds.com/san-francisco-superbay-hangar-american-united-airlin/',
                             type='survey consultant', cache=C + 'deep3ds_superbay.html'),
    'sfom_superbay_neg': dict(title='SFO Museum collection 2011.032.2456, negative "Super Bay Hangar construction" (12 Jun 1970)',
                              url='https://collection.sfomuseum.org/objects/1511948883/', type='primary (archive record)',
                              cache=C + 'sfom_superbay_neg.html'),
    'pcad_united': dict(title='PCAD, San Francisco Municipal Airport, United Airlines Maintenance Facility (Austin Co., c. 1947)',
                        url='https://pcad.lib.washington.edu/building/12969/', type='secondary (architecture database)',
                        cache=C + 'pcad_united.html'),
    'airlinereporter_2018': dict(title='AirlineReporter, "Chix Fix and a 777 BBQ" (United SFO base est. 1948), Oct 2018',
                                 url='https://www.airlinereporter.com/2018/10/chix-fix-and-a-777-bbq-celebrating-family-day-with-united-airlines/',
                                 type='secondary (press)', cache=C + 'airlinereporter_moc.html'),
    'faa_dof': dict(title='FAA Digital Obstacle File DAILY_DOF_CSV (DOF.CSV dated 2026-09-18); accuracy 1A = +-20 ft '
                          'horizontal / +-3 ft vertical, 4D = +-250 ft / +-50 ft; horizontal datum WGS 84',
                    url='https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP', type='primary (FAA)',
                    cache='refs/cache/lighting/DAILY_DOF_CSV.ZIP, dof_sfo_4500m.json, DOF_README.txt'),
    'faa_oe_2012_7455': dict(title='FAA OE/AAA case 2012-AWP-7455-OE (existing antenna, "Short Perm Parking Garage", '
                                   'sponsor City and County of San Francisco): 130 ft AGL, 6 ft site elev., 136 ft AMSL, '
                                   'Determined - No Hazard', url='https://oeaaa.faa.gov/oeaaa/oe3a/external/portal-api/caseFiling/dynamicCaseDataByAsn.do',
                             type='primary (FAA)', cache=C + 'oe_2012AWP7455OE.json'),
    'sfom': dict(title='SFO Museum sfomuseum-data-architecture (Who\'s On First records: names, addresses, inception '
                       'dates, geometry source), via data/sfo_airport.json and refs/sfom-arch', type='primary (SFO Museum), CDLA-Permissive-1.0',
                 url='https://github.com/sfomuseum-data/sfomuseum-data-architecture', cache='refs/sfom-arch/'),
    'naip': dict(title='USDA NAIP 2024 (flown 2024-05-20, 0.6 m), world raster 0.5 m (frame ltp-nad83-2011); public domain',
                 url='https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer',
                 type='imagery (measurement only)', cache='refs/cache/naip/naip_2024_world_0.5m_bgr.npy'),
    'itb_study': dict(title='docs/research/buildings_itb.md s.2.2 (NAIP east-lean model k(x) and sun at acquisition)',
                      url='docs/research/buildings_itb.md', type='this project'),
    'measure': dict(title='tools/buildings/landside_naip_measure.py -> landside_naip_measurements.json (this study)',
                    url='tools/buildings/landside_naip_measurements.json', type='this project'),
}

PHOTOS_NOTE = ('Wikimedia Commons photos used as REFERENCE ONLY (facades, level counts, proportions); thumbnails in '
               'refs/cache/buildings/landside/photos/ (gitignored), full metadata in commons_meta.json there. '
               'Camera GPS in EXIF is not trusted (the 243 mm telephoto shot of the Hyatt carries a position 125 m from '
               'the hotel, which cannot frame the whole building).')
PHOTOS = [
    ('Harvey Milk Terminal 1 Community Day - July 2019 (7391).jpg', 'Gregory Varnum', 'CC BY-SA 4.0', '2019-07-20',
     'grand_hyatt', 'near-orthographic (243 mm eq.) airside elevation of the concave east facade: floor count and '
     'proportions, rooftop penthouse, corner masts, podium'),
    ('Harvey Milk Terminal 1 Community Day - July 2019 (7433).jpg', 'Gregory Varnum', 'CC BY-SA 4.0', '2019-07-20',
     'grand_hyatt', 'curved curtain wall, tall north block, podium, link to the AirTrain station'),
    ('Grand Hyatt at SFO.jpg', 'Suiren2022', 'CC BY-SA 4.0', '2022-05-28', 'grand_hyatt',
     'porte-cochere ("55"), dark metal-panel podium with glazed openings, projecting glass bay'),
    ('Grand Hyatt at SFO station from the northwest, December 2019.JPG', 'Pi.1415926535', 'CC BY-SA 3.0', '2019-12-19',
     'airtrain', 'hotel infill AirTrain station and enclosed bridge'),
    ('Garage A station from the east, October 2020.jpg', 'Pi.1415926535', 'CC BY-SA 4.0', '2020-10-17', 'garage_a',
     'precast panel grid, perforated metal screens, helix drum; guideway section with centre guide beam'),
    ('Garage G and SFO station, August 2018.JPG', 'Pi.1415926535', 'CC BY-SA 3.0', '2018-08-05', 'garage_g',
     'west helix end of Garage G (level bands), elevator tower above parapet, BART/AirTrain station roof'),
    ('Aerial view of San Francisco International Airport station, September 2025.JPG', 'Pi.1415926535', 'CC BY-SA 4.0',
     '2025-09-09', 'garage_g', 'aerial from the east: Garage G roof deck with cars, helix, long white station canopy'),
    ('San Francisco Bay Trail near SFO Long-Term Parking garage, May 2021.jpg', 'Pi.1415926535', 'CC BY-SA 4.0',
     '2021-05-22', 'ltp_garage_2', 'open concrete frame, 5 slab bands + roof with PV canopies'),
    ('Long-Term Parking station from the southwest, May 2021.JPG', 'Pi.1415926535', 'CC BY-SA 4.0', '2021-05-22',
     'airtrain', 'LTP AirTrain station, guideway on T-piers, pedestrian bridge to garage "794", helix of LTP Garage 1'),
    ('Rental Car Center station from the north, May 2021.jpg', 'Pi.1415926535', 'CC BY-SA 4.0', '2021-05-22',
     'rental_car_center', 'RCC west facade (board-formed concrete, ribbon windows, canted corrugated-metal upper wall), '
     'station canopy, cylindrical perforated-metal stair/elevator tower, guideway'),
    ('SFO maintenance hangar from Bay Trail.JPG', 'BrokenSphere', 'CC BY-SA 3.0', '2009-03-31', 'superbay',
     'large hangar with a central ridge and roofs falling to both sides; identification as the Superbay is ours '
     '[unverified]'),
    ('2025-08-12 09 02 08 View north along AirTrain SFO ... U.S. Route 101 (Bayshore Freeway) ....jpg', 'Famartin',
     'CC BY-SA 4.0', '2025-08-12', 'airtrain', 'guideway along US 101 (West Field)'),
    ('Aerial view of US 101 - I-380 interchange, September 2022.JPG', 'Pi.1415926535', 'CC BY-SA 4.0', '2022-09-30',
     'ltp', 'oblique aerial of the North Field: LTP garages, RCC, United MOC'),
]


def V(id_, building, group, value, unit=None, tag='pub', conf='high', src=(), note='', value_m=None, **kw):
    d = dict(id=id_, building=building, group=group, value=value)
    if unit:
        d['unit'] = unit
    if value_m is None and unit == 'ft' and isinstance(value, (int, float)):
        value_m = round(value * FT, 2)
    if value_m is not None:
        d['value_m'] = value_m
    d.update(tag=tag, confidence=conf, src=list(src))
    if note:
        d['note'] = note
    d.update(kw)
    return d


def fp(tag):
    return B[tag]['footprint']


def cars(tag):
    return B[tag].get('roof_cars')


def scan(tag, i=0):
    return B[tag]['shift_scan']['peaks'][i]


VALUES = []
add = VALUES.append

# ------------------------------------------------------------------ common
add(V('naip_epoch', 'all', 'imagery', '2024-05-20, about 13:25 PDT (sun az ~187 deg, el ~72.4 deg; from a DOF pole shadow '
      'in the ITB study)', tag='inf', conf='medium', src=['naip', 'itb_study'],
      note='Roof-deck car counts below are for this moment (a Monday around 1:30 pm).'))
add(V('parking_supply_2018', 'all', 'parking', 'Central 6,459 (5,443 public domestic + 105 ParkFAST + 126 valet + 785 '
      'employee on Level 4); Garage A 1,585 (1,008 public + 577 employee); Garage G 1,405 (1,151 + 254); LTP Garage 1 '
      '3,109; LTP Garage 2 (net) 3,000; West Field Employee Garage 1,722; Superbay Hangar lot 1,046', 'spaces',
      src=['radp_appx'], note='Appendix E.1, memo of 26 Jun 2018, Table 1-1 "Existing parking supply at public and employee lots".'))

# ------------------------------------------------------------------ Central (Domestic) Parking Garage, Building 195
cg = 'central_garage'
f = fp(cg)
add(V('cg_identity', cg, 'identity', 'Central Parking Garage ("Domestic Garage"), Building 195, 195 Lower Domestic Loop; '
      'in the middle of the terminal loop, ringed by the roadways, curbsides and the AirTrain guideway with the T1, T2, T3 '
      'stations', src=['radp_deir', 'sfom', 'flysfo_parking']))
add(V('cg_built', cg, 'identity', 1981, 'year', src=['db_1981', 'sfom'],
      note='Dreyfuss + Blackford with John Carl Warnecke and Associates (joint venture). SFO Museum also records an '
           'earlier Central Parking Garage 1963-1981 (id 1360665035).'))
add(V('cg_levels', cg, 'levels', 5, 'levels', src=['radp_deir', 'db_1981'],
      note='"existing five-level, 81-foot-tall ... Central Parking Garage" (RADP DEIR p. 2-34); "parking for 7,000 '
           'automobiles on five levels ... direct ramps to each of the five parking levels" (D+B).'))
add(V('cg_height', cg, 'height', 81, 'ft', src=['radp_deir', 'radp_nop'], conf='high (number) / low (definition)',
      note='What the 81 ft measures (roof deck, parapet or top of stair/elevator towers) is not stated [unverified].'))
add(V('cg_floor_area', cg, 'area', 3680000, 'sq ft', src=['radp_deir'],
      note='3,680,000 sq ft / 5 levels = 68,400 m2 per level, close to the 64,392 m2 SFO Museum footprint.'))
add(V('cg_spaces', cg, 'parking', 6460, 'spaces', src=['radp_deir', 'radp_appx'],
      note='6,459 in the 2018 memo; 7,000 at opening (D+B, 1981). Level 4 is employee parking (785 spaces, 2018).'))
add(V('cg_clearance', cg, 'parking', '6 ft 6 in (78 in)', src=['flysfo_parking'], note='maximum vehicle height'))
add(V('cg_void', cg, 'plan', 'central circular open space, 200 ft (61 m) diameter, surrounded by the up and down ramps',
      src=['db_1981']))
add(V('cg_void_obs', cg, 'plan', f['holes'][0]['mean_diameter_m'], 'm', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum polygon hole, centre {f['holes'][0]['centre']}, area {f['holes'][0]['area_m2']} m2 "
           '(193 ft vs 200 ft published).', value_m=f['holes'][0]['mean_diameter_m']))
add(V('cg_footprint', cg, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum 1360665043 (src 'sfomuseum', possibly traced from imagery); minimum rectangle "
           f"{f['min_rect']['length_m']} x {f['min_rect']['width_m']} m, sides on the 27.8/117.8 deg airport grid, "
           f"centre {f['min_rect']['centre']}."))
add(V('cg_airtrain_level', cg, 'connections', 'AirTrain T1, T2, T3 stations on garage Level 5; reached from the '
      'terminals by mezzanine-level (Level 3) skybridges near checkpoints B, D, F', src=['flysfo_around'],
      note='1981 design: enclosed bridges with moving walkways to the terminals and tunnels at the first level (D+B).'))
add(V('cg_ground', cg, 'use', 'ground floor: taxi staging; the Central Utility Plant is on the ground floor',
      src=['radp_deir']))
add(V('cg_dof', cg, 'height', 'DOF 06-034812 POLE 109 ft AGL and 06-034813 POLE 101 ft AGL (1A, 2013 survey) stand on '
      'the roof deck (light poles); 06-039216 BLDG 130 ft AGL (4D) = the filed antenna of FAA case 2012-AWP-7455-OE on '
      'the garage', src=['faa_dof', 'faa_oe_2012_7455'], conf='medium',
      note='Pole tops 101-109 ft vs 81 ft structure: consistent with roof-mounted poles of 20-28 ft if the roof deck is '
           'near 81 ft, but the roof-deck height itself is not published [inf].'))
c = cars(cg)
add(V('cg_roof_cars', cg, 'roof', 'about 300 (+-100) cars on the roof deck', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"Visual estimate on NAIP 2024 (QA {c['qa']}). The automatic detector reports {c['cars_detected']} but is "
           'inflated by ramp kerbs, the helix ring and rooftop structures; not usable here. Stalls in straight rows in '
           'each quadrant, some angled stalls along the ramps; four curved ramp/island "petals" and the central helix.'))
add(V('cg_future', cg, 'status', 'RADP Project #6 "Central Hub" would demolish the garage (seismically deficient) and '
      'build a nine-level, up to 175-ft structure; EIR certified Nov 2025, not built', src=['radp_deir', 'radp_rtc'],
      conf='high', note='Model the existing 1981 garage.'))
add(V('cg_scan', cg, 'height', 'NAIP roof-shift scan inconclusive', tag='obs', conf='low', src=['measure'],
      note=f"peaks dx {[p['dx_m'] for p in B[cg]['shift_scan']['peaks']]} m vs {round(0.497 * 81 * FT, 1)} m expected "
           'for 81 ft at k 0.497: the polygon is probably not a ground footprint, and the ring guideway dominates the edges.'))

# ------------------------------------------------------------------ International Garages A (Bldg 95) and G (Bldg 495)
for tag, bno, addr, st in (('garage_a', 95, '95 South Link Road', 'Garage A AirTrain Station, Building 97'),
                           ('garage_g', 495, '495 North Link Road', 'Garage G BART and AirTrain Station, Building 497')):
    f = fp(tag); c = cars(tag); pk = scan(tag)
    nm = 'Garage A' if tag == 'garage_a' else 'Garage G'
    add(V(f'{tag}_identity', tag, 'identity', f'International {nm}, Building {bno}, {addr}; west of the ITB '
          + ('north of South Link Road' if tag == 'garage_a' else 'south of North Link Road') + f'; integral {st}',
          src=['radp_deir', 'sfom']))
    add(V(f'{tag}_built', tag, 'identity', 2000, 'year', src=['sfom'], conf='medium',
          note='SFO Museum inception 2000 (with the International Terminal).'))
    add(V(f'{tag}_levels', tag, 'levels', 9, 'levels', src=['tutor_itb'], conf='medium',
          note='Tutor Perini: "$60 million, nine-level concrete parking garage with post-tensioned beams and deck slabs, '
               'architectural precast concrete, and prefabricated metal/composite panels ... connects to the '
               'International Terminal via a steel truss pedestrian bridge and an integral ART Station". Singular '
               '"garage" for the two structures; 3,200 spaces at opening. Split-level (half-level) numbering is not '
               'excluded [unverified].'))
    add(V(f'{tag}_airtrain_level', tag, 'connections', 'AirTrain station reached from garage Level 7', src=['flysfo_around'],
          note='Garage G: the AirTrain platform is one level above the BART station (Wikipedia; secondary).'))
    add(V(f'{tag}_clearance', tag, 'parking', '8 ft 2 in (98 in)', src=['flysfo_parking'], note='maximum vehicle height'))
    add(V(f'{tag}_footprint', tag, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
          note=f"SFO Museum {f['sfom_id']} (src flysfo); {f['n_polys']} polygon(s); minimum rectangle "
               f"{f['min_rect']['length_m']} x {f['min_rect']['width_m']} m, long side {f['min_rect']['long_side_heading_deg']} deg, "
               f"centre {f['min_rect']['centre']}. Helix (circular ramp drum) at the west end."))
    add(V(f'{tag}_height', tag, 'height', None, 'm', tag='obs', conf='low', src=['measure', 'naip', 'itb_study'],
          note=f"NOT PUBLISHED [unverified]. NAIP roof-shift scan: strongest east shift dx {pk['dx_m']} m -> "
               f"{pk['h_if_true_footprint_m']} m with k {B[tag]['shift_scan']['k_model']} (inside the k-model range), "
               'if the SFO Museum polygon is the ground footprint. The photo of the Garage G helix from the AirTrain '
               '(Aug 2018) shows about three levels plus the parapet above the AirTrain line of sight, which suggests a '
               'lower roof deck (~25-30 m); the 34-36 m scan value may be the stair/elevator towers or the station canopy.',
          range_m=[25, 36]))
    add(V(f'{tag}_roof_cars', tag, 'roof', c['cars_detected'], 'cars', tag='obs', conf='low', src=['naip', 'measure'],
          note=f"detector count (+-30 %) on {c['roof_region_m2']} m2 of roof region = {c['cars_per_1000m2']} cars per "
               f"1,000 m2; car rows run at ~{c['car_row_axis_heading_deg']} deg (along the garage long axis) "
               f"[coherence {c['row_axis_coherence']}]; QA {c['qa']}"))
add(V('garage_ag_facade', 'garage_a', 'facade', 'light architectural precast concrete panels in a square grid; parking '
      'levels screened by prefabricated perforated metal panels with horizontal slots; cylindrical helix drum at the west '
      'end with continuous horizontal bands and arched openings at the top; square stair/elevator towers rise above '
      'the parapet; AirTrain passes through the garage at the station', tag='obs', conf='medium',
      src=['tutor_itb'], photos=['Garage A station from the east, October 2020.jpg', 'Garage G and SFO station, August 2018.JPG']))

# ------------------------------------------------------------------ Long-Term Parking Garage 1 (Bldg 795)
t = 'ltp_garage_1'; f = fp(t); c = cars(t)
add(V('ltp1_identity', t, 'identity', 'Long-Term Parking Garage #1, Building 795, 795 South Airport Boulevard (North '
      'Field)', src=['radp_deir', 'sfom']))
add(V('ltp1_built', t, 'identity', 1997, 'year', src=['sfom'], conf='medium', note='SFO Museum inception 1997.'))
add(V('ltp1_team', t, 'identity', 'architect Joseph Chow & Associates; contractor Tutor Saliba; architectural precast '
      'panels by Willis Construction', src=['willis_ltp1'], conf='medium'))
add(V('ltp1_spaces', t, 'parking', 3109, 'spaces', src=['radp_appx']))
add(V('ltp1_clearance', t, 'parking', '6 ft 10 in (82 in)', src=['flysfo_ltp']))
add(V('ltp1_dof', t, 'height', 'DOF 06-035207 BLDG 86 ft AGL (inside the footprint, south-west part) and 06-035206 BLDG '
      '91 ft AGL (0.7 m outside the north-east corner); both 1A, 2013 survey', src=['faa_dof'], conf='high',
      value_m=[round(86 * FT, 1), round(91 * FT, 1)],
      note='Probably the tops of stair/elevator towers or helix parapets rather than the roof deck [inf].'))
add(V('ltp1_levels', t, 'levels', None, tag='obs', conf='low', src=['dlr_ltp2', 'flysfo_ltp'],
      note='NOT PUBLISHED [unverified]. Garage 2 connects to Garage 1 "via a vehicular connector at level 5" (DLR), and '
           'the AirTrain station bridge lands on "Level 5 of the Long-Term Parking Garage" (SFO), so Garage 1 has at '
           'least 5 levels.'))
add(V('ltp1_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']} (src flysfo); minimum rectangle {f['min_rect']['length_m']} x "
           f"{f['min_rect']['width_m']} m, long side {f['min_rect']['long_side_heading_deg']} deg; three circular helix "
           'ramps at the corners (north, south-east, south) on NAIP.'))
add(V('ltp1_roof_cars', t, 'roof', c['cars_detected'], 'cars', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"{c['cars_per_1000m2']} per 1,000 m2 (detector); manual check 28 cars in 1,600 m2 = 17.5 per 1,000 m2. "
           'Cars stand at ~70 deg, i.e. 90-deg stalls off drive aisles that run along the long axis (155 deg). Roughly '
           'half the roof stalls were occupied [inf: 30-33 m2 gross per stall].'))
add(V('ltp1_scan', t, 'height', 'NAIP roof-shift scan not usable', tag='obs', conf='low', src=['measure'],
      note=f"peak dx {scan(t)['dx_m']} m would give {scan(t)['h_if_true_footprint_m']} m with the extrapolated k "
           f"{B[t]['shift_scan']['k_model']}, inconsistent with the DOF 86-91 ft; k is not calibrated in this NAIP frame."))

# ------------------------------------------------------------------ Long-Term Parking Garage 2 (Bldg 794)
t = 'ltp_garage_2'; f = fp(t); c = cars(t)
add(V('ltp2_identity', t, 'identity', 'Long-Term Parking Garage #2, Building 794, 794 South Airport Boulevard; on the '
      'north-west corner of former surface Lot DD, south-west of Garage 1', src=['radp_deir', 'sfom', 'dlr_ltp2', 'buehler_ltp2']))
add(V('ltp2_built', t, 'identity', '2018-2019 (SFO Museum inception 2018; ENR best project 2019; "completed in 2020" per '
      'RADP DEIR footnote 48)', src=['sfom', 'enr_ltp2', 'radp_deir'], conf='medium'))
add(V('ltp2_team', t, 'identity', 'progressive design-build: Nibbi Brothers (GC); DLR Group | Kwan Henmi with FMG '
      'Architects; Watry/Buehler (structural); Langan (geotechnical); CHS (traffic); $154.6 M',
      src=['dlr_ltp2', 'buehler_ltp2', 'chs_ltp2', 'langan_ltp2', 'dbia_ltp2']))
add(V('ltp2_levels', t, 'levels', 6, 'levels', src=['dlr_ltp2', 'enr_ltp2', 'buehler_ltp2', 'langan_ltp2', 'dbia_ltp2'],
      note='"six-level"/"6-story"; the Bay Trail photo (May 2021) shows 5 open floors under the roof deck, i.e. the '
           'roof is level 6.'))
add(V('ltp2_floor_height', t, 'height', 12, 'ft', src=['enr_ltp2'], note='"A 12-ft floor height" (floor-to-floor).'))
add(V('ltp2_roof_deck_h', t, 'height', 60, 'ft', tag='inf', conf='medium', src=['enr_ltp2', 'dlr_ltp2'],
      note='5 x 12 ft, assuming level 1 at grade and a uniform 12-ft floor-to-floor; parapet and PV canopies on top '
           'are extra (canopy height unknown).'))
add(V('ltp2_area', t, 'area', 1190300, 'sq ft', src=['dlr_ltp2'], conf='medium',
      note='1.2 M sq ft (ENR, DBIA, Langan), 1.25 M (Buehler).'))
add(V('ltp2_spaces', t, 'parking', 3600, 'spaces', src=['dlr_ltp2', 'enr_ltp2', 'dbia_ltp2'],
      note='3,500 (CHS); 3,000 net (2018 memo, before completion).'))
add(V('ltp2_structure', t, 'structure', 'four seismically isolated (separated) structures; central lightwell; open '
      'cast-in-place concrete frame; ground floor 5,000 sq ft customer space; elevator tower with mirrored glass panels '
      'spelling "San Francisco" in Morse code', src=['buehler_ltp2', 'dlr_ltp2', 'dbia_ltp2', 'enr_ltp2']))
add(V('ltp2_roof_pv', t, 'roof', 'roof largely covered by photovoltaic canopies (net-positive garage); cars park '
      'beneath/between the canopy rows', src=['enr_ltp2', 'dlr_ltp2', 'buehler_ltp2'], conf='high',
      note='SFO/Skanska: 2,700 PV panels on "the roof of the SFO Long Term Parking Garage" power ~40 % of the two new '
           'AirTrain stations (ptt_2021, aw_airtrain_leed) - which garage is not stated.'))
add(V('ltp2_link', t, 'connections', 'vehicular (and pedestrian) connector to Garage 1 at level 5; AirTrain LTP station '
      'pedestrian bridge at level 5', src=['dlr_ltp2', 'langan_ltp2', 'flysfo_ltp']))
add(V('ltp2_clearance', t, 'parking', '8 ft 2 in (98 in)', src=['flysfo_ltp']))
add(V('ltp2_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']} (src flysfo); minimum rectangle {f['min_rect']['length_m']} x "
           f"{f['min_rect']['width_m']} m, long side {f['min_rect']['long_side_heading_deg']} deg; stepped west edge. "
           f"1,190,300 sq ft / 6 = 18,430 m2 per level, matching."))
add(V('ltp2_facade', t, 'facade', 'exposed concrete frame: columns and deep spandrel beams, open bays without screens; '
      '5 slab bands + roof parapet with PV canopy above', tag='obs', conf='medium', src=[],
      photos=['San Francisco Bay Trail near SFO Long-Term Parking garage, May 2021.jpg']))
add(V('ltp2_roof_cars', t, 'roof', c['cars_detected'], 'cars', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"{c['cars_per_1000m2']} per 1,000 m2 (detector; PV canopy edges add false positives, cars under canopies "
           'are hidden).'))

# ------------------------------------------------------------------ Rental Car Center (Bldg 780/782, station 779)
t = 'rental_car_center'; f = fp(t); c = cars(t)
add(V('rcc_identity', t, 'identity', 'Rental Car Center, Building 780 (ready-return garage), 780 North McDonnell Road; '
      'Rental Car Quick Turnaround Facility Building 782; Rental Car Center AirTrain Station Building 779 on its west side',
      src=['radp_deir', 'sfom']))
add(V('rcc_built', t, 'identity', 2000, 'year', src=['sfom', 'flysfo_pr_2003'], conf='medium',
      note='SFO Museum inception 2000; served by the AirTrain Blue Line from Feb/Mar 2003.'))
add(V('rcc_levels', t, 'levels', 5, 'levels', src=['tutor_rcc', 'conrac_sol'],
      note='"five-story" (Tutor Perini, $67 M); "five levels of garage and customer service areas on first and fourth '
           'floors" (Conrac Solutions).'))
add(V('rcc_height', t, 'height', 66, 'ft', src=['radp_deir', 'radp_appx'], conf='high (number) / low (definition)',
      note='"the existing 66-foot-tall, 1,488,000-square-foot rental car center (RAC; Building 780) ready-return garage".'))
add(V('rcc_height_check', t, 'height', scan(t)['h_if_true_footprint_m'], 'm', tag='obs', conf='low',
      src=['measure', 'naip'], value_m=scan(t)['h_if_true_footprint_m'],
      note=f"NAIP roof-shift dx {scan(t)['dx_m']} m / extrapolated k {B[t]['shift_scan']['k_model']}; agrees with 66 ft = "
           '20.1 m (a check of the method, not an independent survey).'))
add(V('rcc_dof', t, 'height', 'DOF BLDG 54 ft (06-035203, -35205, -35329) and 59 ft (06-035204) AGL on the roof '
      'outline; TANK 60 ft (06-034240) 6 m west of it at the AirTrain station', src=['faa_dof'], conf='high',
      note='The "TANK" matches the cylindrical perforated-metal stair/elevator tower at the RCC station in the May 2021 '
           'photo [inf]. 54-59 ft points vs 66 ft: roof parapet vs tallest element - definitions unverified.'))
add(V('rcc_area', t, 'area', 1488000, 'sq ft', src=['radp_deir']))
add(V('rcc_stalls', t, 'parking', 2485, 'ready-return stalls', src=['radp_deir']))
add(V('rcc_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']} (src flysfo): polygon covers the garage and the triangular south-east part; "
           f"minimum rectangle {f['min_rect']['length_m']} x {f['min_rect']['width_m']} m. 1,488,000 sq ft / 5 = "
           '27,650 m2 per level.'))
add(V('rcc_facade', t, 'facade', 'west (AirTrain) side: board-formed concrete with horizontal ribbon windows at the '
      'customer-service level and a canted, green-grey corrugated-metal upper wall', tag='obs', conf='medium', src=[],
      photos=['Rental Car Center station from the north, May 2021.jpg']))
add(V('rcc_roof_cars', t, 'roof', c['cars_detected'], 'cars', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"{c['cars_per_1000m2']} per 1,000 m2 (detector) - the densest roof: rental cars in long nose-to-tail lanes "
           'at ~115-125 deg, mostly white/silver and black; tan concrete deck with white lane lines (manual window '
           'x -2230..-2190, z -1110..-1070: ~35-40 cars in 1,600 m2).'))
add(V('rcc_future', t, 'status', 'RADP Project #12 would convert Building 780 into Long-Term Parking Garage #4 (about '
      '3,700 spaces) without new construction; a new CONRAC is planned on Lot DD', src=['radp_deir'], conf='high'))

# ------------------------------------------------------------------ Grand Hyatt at SFO (Bldg 55) + hotel station
t = 'grand_hyatt'; f = fp(t)
add(V('gh_identity', t, 'identity', 'Grand Hyatt at SFO, Building 55, 55 South McDonnell Road; west of Garage A, south of '
      'South Link Road; AirTrain "Grand Hyatt at SFO" station (59 South McDonnell Rd) with an enclosed bridge',
      src=['radp_deir', 'sfom', 'hyatt_pr_2019']))
add(V('gh_opened', t, 'identity', '2019-10-07', src=['hyatt_pr_2019']))
add(V('gh_team', t, 'identity', 'owner SFO (Airport Commission), operator Hyatt; architect Hornberger + Worstell with '
      'ED2 International ("ED21" in the 2019 release); design-builder Webcor; curtain wall Architectural Glass & Aluminum',
      src=['hyatt_pr_2016', 'hyatt_pr_2019', 'sfchron_hyatt', 'webcor_hyatt', 'aga_hyatt', 'hw_hyatt']))
add(V('gh_stories', t, 'levels', 12, 'stories', src=['dbia_hyatt', 'webcor_hyatt', 'aga_hyatt', 'sfchron_hyatt'],
      note='"12-story high rise, Type 1 construction" (DBIA); "one structure with 12 levels above grade" (Webcor).'))
add(V('gh_structure', t, 'structure', 'Type I concrete; post-tensioned flat slabs with concrete columns and shear walls',
      src=['webcor_hyatt', 'dbia_hyatt'], conf='medium',
      note='"post-tensioned concrete flat slab" is from an Arup project-page search snippet only (page 404) [unverified].'))
add(V('gh_lobby_level', t, 'connections', 'guests arriving by road take elevators to the fourth-floor lobby; AirTrain '
      'station connects at the fourth floor', src=['sfchron_hyatt', 'webcor_hyatt']))
add(V('gh_rooms', t, 'use', '351 rooms incl. 22 suites (21 per Webcor); 14,435 sq ft meeting space; 215 surface stalls; '
      'roof-mounted PV (133,000 kWh/yr); no rooftop deck', src=['hyatt_pr_2019', 'webcor_hyatt', 'sfchron_hyatt']))
add(V('gh_site', t, 'plan', '4.2 acres (2019 release) / 4.7-acre site (2016 release, Webcor)', src=['hyatt_pr_2019',
      'hyatt_pr_2016', 'webcor_hyatt'], conf='medium'))
add(V('gh_plan_shape', t, 'plan', 'crescent-shaped slab: convex facade to the west (US 101), concave all-glass facade '
      'to the east (airfield); taller straight block at the north end next to the AirTrain station; 2-3-storey podium '
      'clad in dark metal panels on the east/south side with large glazed openings and a porte-cochere', tag='obs',
      conf='medium', src=['sfom', 'naip'], photos=['Harvey Milk Terminal 1 Community Day - July 2019 (7391).jpg',
                                                  'Harvey Milk Terminal 1 Community Day - July 2019 (7433).jpg',
                                                  'Grand Hyatt at SFO.jpg'],
      note='Curvature from the SFO Museum polygon (west edge bulges west of its chord, east edge bows in).'))
add(V('gh_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']} (src 'sfomuseum'): minimum rectangle {f['min_rect']['length_m']} x "
           f"{f['min_rect']['width_m']} m, long axis {f['min_rect']['long_side_heading_deg']} deg; includes the podium "
           'and the connector to the station.'))
add(V('gh_facade', t, 'facade', 'unitised glass curtain wall, vertical mullion grid, one spandrel band per floor; roof '
      'parapet with 4 corner masts; dark stepped mechanical penthouse near mid-length', tag='obs', conf='medium',
      src=['aga_hyatt'], photos=['Harvey Milk Terminal 1 Community Day - July 2019 (7391).jpg']))
add(V('gh_height', t, 'height', 44, 'm', tag='inf', conf='low', src=['dbia_hyatt'], value_m=44, range_m=[40, 48],
      note='NOT PUBLISHED [unverified]. Photo 7391 (near-orthographic): grade-to-parapet = 13.2 typical upper-floor '
           'pitches (podium = 3.2 pitches, recessed colonnade level = 1, tower = ~9). With a typical hotel floor-to-floor '
           'of 3.2-3.5 m (assumption) -> 42-46 m; NAIP roof-shift scan peaks at dx 11-12 m -> 36-40 m (low confidence; '
           'the strongest peak, 5.5 m -> 18 m, is probably the podium). Needs an SFO drawing or the FAA OE/AAA filing.'))

# ------------------------------------------------------------------ Consolidated Administration Campus (SFO Museum)
t = 'cac'; f = fp(t)
add(V('cac_identity', t, 'identity', 'SFO Consolidated Administration Campus (CAC) Phase I, 674 West Field Road (West '
      'Field, next to the West Field Road AirTrain station); houses airport departments and the SFO Museum\'s '
      'collection storage, conservation and preparation shops on the ground floor', src=['sfom', 'cavagnero_cac',
      'pw_cac', 'mck_cac', 'webcor_cac']))
add(V('cac_opened', t, 'identity', 'summer 2018', src=['mck_cac', 'sfom'], note='SFO Museum inception 2018-06.'))
add(V('sfo_museum_library', t, 'identity', 'the SFO Museum\'s public Aviation Library and Louis A. Turpen Aviation Museum '
      'is not in the CAC but in the International Terminal Main Hall, level 3 (record 1947304235, since 2024-11-05); '
      'SFO Museum galleries are spread through the terminals', src=['sfom'], conf='high'))
add(V('cac_team', t, 'identity', 'Mark Cavagnero Associates with Perkins&Will; progressive design-build with Webcor; '
      'CM MCK; $84 M; LEED Gold', src=['cavagnero_cac', 'pw_cac', 'webcor_cac', 'mck_cac']))
add(V('cac_stories', t, 'levels', 4, 'stories', src=['cavagnero_cac', 'webcor_cac', 'mck_cac'],
      note='"four-story steel building"; three office levels over a ground floor with the museum spaces.'))
add(V('cac_floor_height', t, 'height', 15, 'ft', src=['pw_cac'],
      note='"increasing the floor-to-floor heights from 13 feet to 15 feet".'))
add(V('cac_height', t, 'height', 64, 'ft', tag='inf', conf='medium', src=['pw_cac', 'cavagnero_cac'], range_m=[18.3, 20.5],
      note='4 x 15 ft = 60 ft to the roof + parapet/screens (assumed 2-7 ft). NAIP roof-shift scan (extrapolated k): '
           f"dx {scan(t)['dx_m']} m -> {scan(t)['h_if_true_footprint_m']} m, low confidence."))
add(V('cac_area', t, 'area', 135000, 'sq ft', src=['cavagnero_cac', 'mck_cac'], note='136,000 sq ft per Perkins&Will.'))
add(V('cac_form', t, 'facade', 'a bend in the main bar (visible outside) encloses a protected court; reduced '
      'window-to-wall ratio; exterior louvers on the south and west; interior stair tower with a light well',
      src=['cavagnero_cac', 'pw_cac']))
add(V('cac_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']}: minimum rectangle {f['min_rect']['length_m']} x {f['min_rect']['width_m']} m, "
           f"long side {f['min_rect']['long_side_heading_deg']} deg (bent bar)."))
add(V('cac_phase2', t, 'status', 'SFO CAC Addendum, Case 2019-006583ETM (issued 17 May 2021 per RADP DEIR fn. 45; '
      'NOD: 1986.638E Addendum 6, final approval 18 Apr 2023, 6.6-acre site): a new '
      'consolidated administration building, demolition of Building 676 and a new parking garage there, West Field '
      'AirTrain platform expansion (AirTrain mechanical room moved into the garage), two pedestrian bridges to the '
      'station', src=['radp_deir', 'sfplan_nod_cac'], conf='high',
      note='RADP DEIR footnote 45. Heights/extent of the Phase II garage not found; whether it is built by 2026 is '
           'unverified.'))

# ------------------------------------------------------------------ Superbay hangar (Bldg 1060)
t = 'superbay'; f = fp(t)
add(V('sb_identity', t, 'identity', 'Superbay Hangar, Building 1060, 1060 North Access Road (East Field, near the '
      'Seaplane Harbor, north of runways 10/28 and west of the 19R/19L ends); American Airlines and United Airlines',
      src=['radp_deir', 'sfom', 'weitz_superbay_story', 'deep3ds_superbay']))
add(V('sb_built', t, 'identity', '1969-1972 for American Airlines 747s', src=['weitz_superbay_story', 'sfom_superbay_neg',
      'sfom', 'deep3ds_superbay'], conf='medium',
      note='"Originally built in 1969" (Weitz); SFO Museum negative of construction dated 12 Jun 1970; SFO Museum '
           'inception 1972.'))
add(V('sb_bays', t, 'use', 'four maintenance bays (four 747-size aircraft), six levels of office space and a central '
      'workshop; fire pump equipment on the 6th floor', src=['weitz_superbay_story']))
add(V('sb_height_dof', t, 'height', 135, 'ft', src=['faa_dof'],
      note='DOF 06-001451 BLDG 135 ft AGL / 144 ft AMSL, accuracy 1A, lighting R (red obstruction light), JDATE 2011356; '
           'point at the south end of the central spine.'))
add(V('sb_height_pub', t, 'height', 140, 'ft', src=['deep3ds_superbay'], conf='medium',
      note='"140-foot tall roof" (round number; DOF 135 ft preferred).'))
add(V('sb_interior_h', t, 'height', 120, 'ft', src=['weitz_superbay'], conf='medium',
      note='"The wet sprinkler system is approximately 120 feet from the finished floor, which is the height of the '
           'inside of the hangar."'))
add(V('sb_footprint_pub', t, 'area', 250000, 'sq ft', src=['deep3ds_superbay'], conf='medium',
      note='"250,000 square foot-building footprint"; Weitz gives 420,550 sq ft (total floor area incl. office levels).'))
add(V('sb_cantilever', t, 'structure', 'light-gauge steel roof beams cantilever over 230 ft from the centre of the hangar '
      'in each direction; "open volume of about 12,000,000 cubic feet" (per side or in total - ambiguous)', src=['deep3ds_superbay'], conf='medium'))
add(V('sb_footprint', t, 'plan', f['area_m2'], 'm2', tag='obs', src=['sfom', 'measure'],
      note=f"SFO Museum {f['sfom_id']} (src unknown): {round(f['area_m2'] / FT / FT)} sq ft; minimum rectangle "
           f"{f['min_rect']['length_m']} x {f['min_rect']['width_m']} m ({round(f['min_rect']['length_m'] / FT)} x "
           f"{round(f['min_rect']['width_m'] / FT)} ft), long side on the 117.8-deg grid, centre {f['min_rect']['centre']}."))
add(V('sb_layout', t, 'plan', 'central spine (offices/workshop) along the 27.8-deg grid (NNE-SSW), about 25-30 m wide; '
      'cantilevered hangar roofs to the WNW and ESE, ~70 m deep each (165.9 m overall = 2 x ~70 m + spine), each side '
      'split into two bays of ~67 m along the spine; doors on the WNW and ESE faces', tag='inf', conf='low',
      src=['naip', 'deep3ds_superbay', 'weitz_superbay_story'],
      note='From the NAIP roof pattern (bright raised spine, transverse roof ribs) combined with the published 230-ft '
           'cantilever and four bays. The Bay Trail photo (2009, identification unverified) shows roofs falling from a '
           'central ridge to both sides.'))
add(V('sb_roof_shift', t, 'plan', '(-7.0, -7.5) m', tag='obs', conf='low', src=['measure'],
      note='NAIP roof image vs SFO Museum polygon (2-D gradient scan): roof imaged to the north-west, i.e. this frame '
           'leans roofs NW (k ~0.25 per m if the polygon is the footprint and h = 41 m) - opposite to the terminal '
           'area; see docs/research/imagery.md s.6 (Super Bay shifts west).'))
add(V('sb_future', t, 'status', 'RADP Project #18: a new 95-ft, 181,000 sq ft two-widebody hangar on the Superbay '
      'employee lot (1,046 spaces) - planned only', src=['radp_deir', 'radp_appx']))

# ------------------------------------------------------------------ United Airlines MOC hangars
t = 'united_moc'
mo = M['moc']
add(V('moc_identity', t, 'identity', 'United Airlines Maintenance and Operation Center (MOC), North Field, along North '
      'Access Road', src=['radp_deir']))
add(V('moc_history', t, 'identity', 'United maintenance base at SFO since 1948 (AirlineReporter); c. 1947 325,000 sq ft '
      'maintenance facility by the Austin Company for 11 DC-3/DC-4/DC-6 (PCAD); a 1956-58 SOM (Myron Goldsmith) '
      'cantilever hangar existed - whether it still stands is [unverified]', src=['airlinereporter_2018', 'pcad_united'],
      conf='low'))
lh = mo['moc_large_hangar']
add(V('moc_large_hangar', t, 'plan', lh['area_m2'], 'm2', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"Imaged roof (relief not removed) {lh['min_rect']['length_m']} x {lh['min_rect']['width_m']} m, long side "
           f"{lh['min_rect']['long_side_heading_deg']} deg, centre {lh['min_rect']['centre']}, corners "
           f"{lh['corners_imaged']} (+-3 m). {lh['note']}.",
      dof=[f"{d['oas']} {d['agl_ft']} ft ({d['agl_m']} m) at {d['world']}" for d in lh['dof']]))
add(V('moc_large_hangar_h', t, 'height', 132, 'ft', src=['faa_dof'], conf='high (points) / low (which roof part)',
      note='DOF 1A BLDG points on this hangar block: 132 ft (06-035289, NE part), 117 ft (06-035290, NW corner), 116 ft '
           '(06-035288, south end). Roof sections step down; section heights between the points are unknown.'))
bh = mo['moc_barrel_hangars']
add(V('moc_barrel_hangars', t, 'plan', bh['area_m2'], 'm2', tag='obs', conf='low', src=['naip', 'measure'],
      note=f"Imaged roof {bh['min_rect']['length_m']} x {bh['min_rect']['width_m']} m, centre {bh['min_rect']['centre']}; "
           f"{bh['note']}."))
add(V('moc_other_dof', t, 'height', 'other DOF 1A BLDG tops in the MOC: 107 ft (06-035303, -1980,-1764), 92 ft '
      '(06-035245), 79 ft (06-035292), 75/74 ft (06-035284/-35327, -1780,-1680), 70 ft (06-035291), 61 ft, 60 ft',
      src=['faa_dof'], conf='high', note='Building identities not matched; the 107-ft point sits on the long western '
      'shop/hangar block along McDonnell Road.'))

# ------------------------------------------------------------------ AirTrain
t = 'airtrain'; r = M['airtrain_rail']
add(V('at_opened', t, 'identity', 'opened 24 Feb / 3 Mar 2003 (inauguration 3 Mar 2003); $430 M', src=['flysfo_pr_2003',
      'flysfo_airtrain_fs', 'wiki_airtrain']))
add(V('at_team', t, 'identity', 'guideways: engineer Parsons Brinckerhoff / MGE Eng. / Manna Consultants, contractor '
      'Tutor-Saliba; operating system: Lea+Elliott (engineer), Bombardier (CX-100)', src=['flysfo_airtrain_fs']))
add(V('at_vehicle', t, 'vehicle', "CX-100, 9'3\" wide x 39'6\" long, 32,000 lb, teal blue metallic; 38 cars (2003), 41 "
      '(2021); up to 3-car trains; rubber tyres, centre guide beam, guideway-mounted power rail (600 V AC rectified to '
      '300 V DC, 5 substations)', src=['flysfo_airtrain_fs', 'flysfo_pr_2021'], value_m=[2.82, 12.04]))
add(V('at_length', t, 'length', '"five miles of two independent loops" (2003); "over 6 miles of fully automated '
      'concrete guideways" (2021, after the 1,900-ft extension)', src=['flysfo_airtrain_fs', 'flysfo_pr_2021'],
      conf='medium'))
add(V('at_ext', t, 'length', 1900, 'ft', src=['flysfo_pr_2021', 'aw_airtrain_leed', 'pghwong'],
      note='extension beyond the Rental Car Center to Long-Term Parking, "running 50 feet above a public roadway"; '
           'Skanska + WSP progressive design-build ($172 M Skanska contract; $259 M program); opened May 2021.'))
add(V('at_height_ext', t, 'height', 50, 'ft', src=['flysfo_pr_2021'], conf='medium',
      note='extension height above the public roadway it crosses.'))
add(V('at_height_general', t, 'height', '35 to 40 ft above ground at its highest point', src=['radp_appx'],
      conf='low', note='RADP Initial Study footnote 19 - conflicts with the 50 ft of the extension and with the station '
      'levels in the garages; treat as [unverified].'))
add(V('at_stations', t, 'stations', '9 stations in 2003 (average spacing 0.3 mi) + Grand Hyatt infill (Oct 2019; $15 M per Wikipedia, secondary) + '
      'Long-Term Parking (May 2021) = 11: Terminal 1, 2, 3 (Buildings 279, 379, 479; Level 5 of the Domestic Garage), '
      'International Terminal A and G (197, 179; ITB Level 4), Garage A (97) and Garage G/BART (497) (garage Level 7), '
      'Grand Hyatt (hotel 4th floor), West Field Road (677), Rental Car Center (779), Long-Term Parking (797; bridge to '
      'LTP garage Level 5)', src=['flysfo_airtrain_fs', 'flysfo_around', 'flysfo_ltp', 'radp_deir', 'sfchron_hyatt',
      'wiki_airtrain']))
add(V('at_lines', t, 'use', 'Red Line: clockwise terminal loop (~9 min); Blue Line: counter-clockwise, adds West Field '
      'Road, RCC and LTP (~25 min); T3 station closed 4 Nov 2025 - 2027 for T3 West works', src=['flysfo_around',
      'aw_airtrain_leed', 'wiki_airtrain'], conf='medium'))
add(V('at_rail_polygon', t, 'plan', r['centreline_length_est_m'], 'm', tag='obs', conf='medium', src=['sfom', 'measure'],
      note=f"SFO Museum 'AirTrain Rail' {r['sfom_id']} (src sfo): area {r['area_m2']} m2, perimeter {r['perimeter_m']} m "
           f"-> ~{r['centreline_length_est_m']} m of polygon centreline; width percentiles {r['width_percentiles_m']} m "
           '(single guideway ~4.8-5.1 m, twin guideways ~9.5-11.5 m).', value_m=r['centreline_length_est_m']))
add(V('at_section', t, 'structure', 'concrete guideway deck with two running surfaces and a centre guide beam per '
      'track, side walkway with galvanised railing; single-column T-piers along the extension; stations with '
      'platform-edge door cabins and curved metal canopies', tag='obs', conf='medium', src=['flysfo_airtrain_fs'],
      photos=['Garage A station from the east, October 2020.jpg', 'Rental Car Center station from the north, May 2021.jpg',
              'Long-Term Parking station from the southwest, May 2021.JPG']))
add(V('at_station_domestic', t, 'structure', 'Terminal 1/2/3 stations (on the Domestic Garage ring): long glazed platform '
      'enclosures with platform-door cabins under a single-pitch metal roof carried on X-braced steel struts, a dark '
      'horizontally-ribbed metal stair/elevator tower at one end; the ring guideway is a concrete trough with a side '
      'walkway and lamp posts; roadway viaducts below stand on large cylindrical columns with drum capitals',
      tag='obs', conf='medium', src=[],
      photos=["2025-08-12 09 12 06 View of AirTrain SFO's Terminal 2 station and the control tower (Famartin, CC BY-SA 4.0)"]))
add(V('at_maintenance', t, 'structure', 'maintenance facility: 24-hour control room, five service bays, test track and a '
      'two-level employee parking structure', src=['flysfo_airtrain_fs']))

CONFLICTS = [
    'AirTrain height: "35 to 40 feet above ground at its highest point" (RADP Initial Study fn. 19) vs the extension '
    '"running 50 feet above a public roadway" (SFO 2021) and stations on garage Level 5/7.',
    'AirTrain length: "five miles of two independent loops" (2003 fact sheet) vs "over 6 miles of guideways" (2021) vs '
    '"three miles" (Wikipedia, route length).',
    'Central garage capacity: 7,000 (1981, D+B) vs 6,459 (2018 memo) vs 6,460 (2025 DEIR) - capacity changed over time.',
    'LTP Garage 2: 1,190,300 / 1.2 M / 1.25 M sq ft; 3,600 / 3,500 / 3,000 (net) stalls; completion 2019 (ENR) vs 2020 '
    '(RADP DEIR fn. 48).',
    'Grand Hyatt: site 4.2 acres (2019) vs 4.7 acres (2016); 22 vs 21 suites; associate architect "ED21" vs "ED2 '
    'International".',
    'Superbay: built 1969 (Weitz) vs 1970 construction photo vs 1972 (SFO Museum); roof 140 ft (Deep3DS) vs DOF 135 ft; '
    'footprint 250,000 sq ft (Deep3DS) vs 420,550 sq ft (Weitz, total) vs 238,970 sq ft (SFO Museum polygon).',
    'CAC floor area 135,000 (architect, CM) vs 136,000 sq ft (Perkins&Will).',
    'Garages A/G height: NAIP roof-shift 34-36 m vs ~25-30 m suggested by the level count seen from the AirTrain; '
    'neither is published.',
    'LTP Garage 1: NAIP scan (37 m) contradicts the DOF 86-91 ft - the north-field NAIP lean is not calibrated.',
    'SFO Museum AirTrain stations: the newer duplicate polygons 1763588569 "International Terminal (A)" (north end of '
    'the ITB) and 1763588567 "(G)" (south end) have A and G swapped relative to 1729791961/1729791965 and the terminal '
    'layout (A = south, G = north). data/ not edited.',
]

OPEN_QUESTIONS = [
    'Published heights (roof deck, parapet, top of towers) for Garages A and G, the Grand Hyatt, LTP Garage 1 and the CAC; '
    'and what the published 81 ft (Central) and 66 ft (RCC) measure. Best route: SFO Planning & Environmental Affairs '
    '/ SFO GIS (building data with heights, the "sfogis" source of SFO Museum), or the as-built drawings.',
    'FAA OE/AAA NRA filings for the hotel (c. 2016-17), LTP Garage 2 (c. 2017), CAC (c. 2016) and the AirTrain extension '
    '(c. 2017-19) would give surveyed AGL/AMSL heights; the public OE/AAA area search only returns the last ~12 months, '
    'so the ASNs are needed (ask SFO).',
    'Master Plan EIR addenda (Case 1986.638E) for the hotel, LTP Garage 2 / AirTrain extension and CAC (2015-2019) '
    'were not found online; SF Planning may provide them.',
    'Garage A/G level numbering: 9 levels with the AirTrain at Level 7 - are these split (half) levels?',
    'LTP Garage 1: number of levels and helix positions; roof-deck height.',
    'Grand Hyatt: floor-to-floor heights, parapet and penthouse heights; exact tower outline vs podium in plan.',
    'Superbay: roof section (spine height vs cantilever edge), door opening widths/heights, which faces carry doors.',
    'United MOC: building list/numbers, hangar identities, door sizes and roof-section heights; lean-corrected '
    'footprints (no SFO Museum outlines). United or SFO facility plans.',
    'AirTrain guideway: deck width, parapet height, pier spacing and height profile along the alignment (2003 '
    'Parsons Brinckerhoff design drawings, or photogrammetry); station roof heights.',
    'NAIP lean in the North Field and East Field frames is not calibrated; a DOF-pole calibration like the ITB study '
    'would turn the roof-shift scans into usable height checks there.',
    'Central garage exterior: facade material and opening pattern of the outer walls (hidden behind the roadways and '
    'the AirTrain ring in the photos found); interior photos show waffle/joist slabs, board-formed concrete walls and '
    'lettered parking areas ("Area C, Level 3").',
    'Roof-deck car counts are single-epoch (Monday 2024-05-20 ~13:25 PDT) and +-30 %; the procedural model needs an '
    'occupancy rule (e.g. by time of day) that the owner should choose.',
]


def main():
    spec = dict(
        id='sfo_landside_buildings',
        title='SFO landside buildings (garages, AirTrain, Grand Hyatt, Rental Car Center, CAC/SFO Museum, maintenance '
              'hangars) - research spec',
        status='RESEARCH DRAFT for owner review (2026-09-26). Not approved; no 2-D sheet or 3-D model built from it yet.',
        doc='docs/research/buildings_landside.md',
        frame='ltp-nad83-2011 (tools/geo_frame.py = js/geo.js): x east, z south, metres from the ARP; headings true, '
              'clockwise from north; heights in ft/m above local grade unless noted',
        tags=dict(pub='published by an original or primary source; value transcribed, not measured',
                  obs='measured by us on NAIP 2024 / SFO Museum geometry / FAA DOF / licensed photos with a stated method',
                  inf='derived by us from pub + obs under a stated assumption; must be confirmed before it is treated as fact'),
        confidence_scale='high = consistent primary sources or a direct measurement with small error; medium = one '
                         'source or a measurement with a stated error; low = conflicting sources, snippet-only source, '
                         'or a derivation with an unverified assumption',
        buildings=['central_garage', 'garage_a', 'garage_g', 'ltp_garage_1', 'ltp_garage_2', 'rental_car_center',
                   'grand_hyatt', 'cac', 'superbay', 'united_moc', 'airtrain'],
        sources=SOURCES,
        photos=dict(note=PHOTOS_NOTE, items=[dict(file='File:' + p[0], author=p[1], licence=p[2], date=p[3], building=p[4],
                                                  use=p[5]) for p in PHOTOS]),
        values=VALUES,
        conflicts=CONFLICTS,
        open_questions=OPEN_QUESTIONS,
        measurements='tools/buildings/landside_naip_measurements.json',
    )
    out = os.path.join(HERE, 'spec_landside.json')
    json.dump(spec, open(out, 'w'), indent=1, ensure_ascii=False)
    # self-check: every src id exists
    bad = [(v['id'], s) for v in VALUES for s in v['src'] if s not in SOURCES]
    assert not bad, bad
    ids = [v['id'] for v in VALUES]
    assert len(ids) == len(set(ids)), 'duplicate value ids'
    print('wrote', out, len(VALUES), 'values,', len(SOURCES), 'sources')


if __name__ == '__main__':
    main()
