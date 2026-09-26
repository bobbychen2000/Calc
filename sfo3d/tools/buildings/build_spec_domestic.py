"""Builds tools/buildings/spec_domestic.json - the research spec of SFO's domestic terminals: Harvey Milk Terminal 1
(Boarding Areas B and C), Terminal 2 (Boarding Area D) and Terminal 3 (Boarding Areas E and F), for the 2-D drawing
stage (docs/drawings/buildings/) and, after the owner's review, the 3-D build. Evidence and discussion:
docs/research/buildings_domestic.md.

Every item carries: value + unit, tag (pub = published by an original/primary source; obs = measured by us on public
imagery/data with the stated method; inf = derived from pub/obs values by stated arithmetic or assumption), sources
(ids into `sources`, each with its URL), source_urls (resolved for convenience), confidence (high / medium / low) and
status (verified / conflict / snippet-only / secondary-only / unverified). Nothing is guessed silently: what could not
be verified is listed in `unverified` and `open_questions` instead of getting a value.

Inputs: tools/buildings/dom_heights.json (dom_heights.py). Source documents, photos and imagery crops are cached in
refs/cache/buildings/domestic/ (gitignored); QA overlays with imagery are in out/buildings/domestic/ (local).
Usage: python3 tools/buildings/build_spec_domestic.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
H = json.load(open(os.path.join(HERE, 'dom_heights.json')))
HR = {r['id']: r for r in H['roofs']}
FT = 0.3048
ACC = '2026-09-26'
CACHE = 'refs/cache/buildings/domestic/src/'


def ftm(ft, nd=2):
    return round(ft * FT, nd)


# ------------------------------------------------------------------------------------------------------ sources
S = {
    # --- Terminal 3 West Civic Design Review (SF Arts Commission) - SFO / Turner / Gensler / TEF submittals
    'cdr_t3w_cd_2023': dict(title='Terminal 3 West Modernization Project - Civic Design Review, Construction Documents Phase 3 (Oct 2023), incl. 95% CD sheets 5A-A5.01.01/.02 "Exterior Elevations" and wall sections',
                            publisher='San Francisco International Airport / Turner / Gensler / TEF, submitted to the SF Arts Commission Civic Design Review Committee',
                            url='https://www.sf.gov/sites/default/files/2023-10/231004_CDRC_CD_FINAL.pdf', read='full',
                            cache=CACHE + '231004_CDRC_CD_FINAL.pdf (+ .txt)', accessed=ACC,
                            note='drawing sheets carry "(c) City and County of San Francisco ... reproduction prohibited": numbers are quoted as facts, no pixels are reused'),
    'cdr_t3w_sd_2024': dict(title='Terminal 3 West Modernization - Civic Design Review, Exterior Facades, Schematic Design Phase 1 (Mar 2024)',
                            publisher='SFO / Turner / Gensler / TEF', url='https://media.api.sf.gov/documents/240308_CDRC_SD_PHASE_1.pdf', read='full',
                            cache=CACHE + '240308_CDRC_SD_PHASE_1.pdf', accessed=ACC),
    'cdr_t3w_dd_2024': dict(title='SFO T3 West Modernization - Civic Design Review Phase 2, Design Development, Exterior Facades (Oct 2024)',
                            publisher='SFO / Turner / Gensler / TEF', url='https://www.sf.gov/sites/default/files/2024-10/241021_CDRC_DD_PHASE%202.pdf',
                            read='full', cache=CACHE + '241021_CDRC_DD_PHASE_2.pdf', accessed=ACC),
    'cdr_t3w_update_2026': dict(title='SFO T3 West Modernization - Civic Design Review, Exterior Facades, Post Phase 3 Update (18 May 2026)',
                                publisher='SFO / Turner / Gensler / TEF', url='https://media.api.sf.gov/documents/260518_SFO_T3W_CDRC_UPDATE.pdf',
                                read='full', cache=CACHE + '260518_SFO_T3W_CDRC_UPDATE.pdf', accessed=ACC),
    'cdr_t3w_c4c_2024': dict(title='Terminal 3 West Modernization Civic Design Review - Courtyard 4 Connector [C4C] Concept Phase (Mar 2024)',
                             publisher='SFO / Turner / Gensler / TEF', url='https://media.api.sf.gov/documents/240318_CDRC_Terminal_3_West_Modernization_-_C4C_update.pdf',
                             read='full', cache=CACHE + '240318_CDRC_Terminal_3_West_Modernization_-_C4C_update.pdf', accessed=ACC),
    'cdr_minutes_2016_08': dict(title='SF Arts Commission, Civic Design Review Committee - August 15, 2016 - Minutes (SFO Terminal 1 Center Renovation Project and New Boarding Area B Reconstruction Project, Phase 2)',
                                publisher='San Francisco Arts Commission', url='https://www.sfgov.org/arts/meeting/civic-design-review-committee-august-15-2016-minutes',
                                read='full', cache=CACHE + 'cdr_civic-design-review-committee-august-15-2016-minutes.html', accessed=ACC,
                                note='the presentations themselves (2016-2017) are not posted online; only the minutes'),
    'cdr_minutes_2016_03': dict(title='SF Arts Commission, Civic Design Review Committee - March 21, 2016 - Minutes (T1 Center and Boarding Area B, informational/conceptual)',
                                publisher='San Francisco Arts Commission', url='https://www.sfgov.org/arts/meeting/civic-design-review-committee-march-21-2016-minutes',
                                read='full', cache=CACHE + 'cdr_civic-design-review-committee-march-21-2016-minutes.html', accessed=ACC),
    # --- SFO
    'sfo_pr_t1_final': dict(title='SFO press release "SFO Opens Final Phase of Harvey Milk Terminal 1", 17 Jun 2024', publisher='San Francisco International Airport',
                            url='https://www.flysfo.com/about/media/press-releases/sfo-opens-final-phase-harvey-milk-terminal-1', read='full',
                            cache=CACHE + 'flysfo_t1_final.html', accessed=ACC),
    'sfo_pr_t3w': dict(title="SFO press release \"SFO's Terminal 3 West Modernization Project is Underway\", 20 Aug 2024", publisher='San Francisco International Airport',
                       url='https://www.flysfo.com/about/media/press-releases/sfos-terminal-3-west-modernization-project-underway', read='full',
                       cache=CACHE + 'flysfo_t3w.html', accessed=ACC),
    'sfom_reflectors': dict(title='SFO Museum, public art collection: James Carpenter, "Four Sculptural Light Reflectors" (Harvey Milk Terminal 1, Main Hall - Level 3 - Pre-Security)',
                            publisher='SFO Museum', url='https://www.sfomuseum.org/public-art/public-collection/four-sculptural-light-reflectors', read='full',
                            cache=CACHE + 'sfom_reflectors.html', accessed=ACC),
    'sfom_data': dict(title='SFO Museum architecture data (sfomuseum-data-architecture): terminal and boarding-area polygons, records 1947304259 (T1), 1947304591 (T2), 1947304447 (T3), 1947304261 (BA B), 1947304663 (BA C), 1947304595 (BA D), 1947304511 (BA E), 1947304451 (BA F); "sfo:level" 2 (boarding areas), inception 2024-11-05',
                      publisher='SFO Museum (CDLA-Permissive-1.0)', url='https://github.com/sfomuseum-data/sfomuseum-data-architecture', read='full',
                      cache='refs/sfom-arch/ ; data/sfo_airport.json', accessed=ACC),
    # --- architects / engineers / builders
    'arup_t1': dict(title='Arup project page "San Francisco International Airport Terminal 1 - The Harvey Milk Terminal"', publisher='Arup (MEP / aviation planning engineer, BA-B)',
                    url='https://www.arup.com/en-us/projects/san-francisco-international-airport-terminal-1/', read='full', cache=CACHE + 'arup_t1.html', accessed=ACC),
    'woodsbagot_bab': dict(title='Woods Bagot project page "Harvey Milk Terminal 1, Boarding Area B"', publisher='Woods Bagot (design JV HKS / Woods Bagot / ED2 / KYA)',
                           url='https://www.woodsbagot.com/projects/san-francisco-international-airports-harvey-milk-terminal-1-boarding-area-b/', read='full',
                           cache=CACHE + 'woodsbagot_bab.html', accessed=ACC),
    'hks_bab': dict(title='HKS project page "San Francisco International Airport\'s Harvey Milk Terminal 1, Boarding Area B"', publisher='HKS',
                    url='https://www.hksinc.com/what-we-do/projects/san-francisco-airports-terminal-1-redevelopment/', read='snippet',
                    cache=None, accessed=ACC, note='HTTP 403 to curl and WebFetch; search-engine extract only ("1 MW rooftop solar array")'),
    'dbia_bab': dict(title='DBIA project page "San Francisco International Airport Harvey Milk Terminal 1 Boarding Area B"', publisher='Design-Build Institute of America (award entry)',
                     url='https://dbia.org/project/san-francisco-international-airport-harvey-milk-terminal-1-boarding-area-b/', read='full', cache=CACHE + 'dbia_bab.html', accessed=ACC),
    'rdh_bab': dict(title='RDH Building Science case study "San Francisco International Airport - Harvey Milk Terminal 1, Boarding Area B"', publisher='RDH (building-enclosure consultant)',
                    url='https://www.rdh.com/our-case-studies/san-francisco-international-airport-harvey-milk-terminal-1-boarding-area-b/', read='full', cache=CACHE + 'rdh_bab.html', accessed=ACC),
    'cei_bab': dict(title='Cupertino Electric project page "San Francisco International Airport (SFO) Harvey Milk Terminal 1 Boarding Area B"', publisher='Cupertino Electric (electrical / solar contractor)',
                    url='https://www.cei.com/our-work/san-francisco-international-airport-sfo-harvey-milk-terminal-1-boarding-area-b', read='full', cache=CACHE + 'cei_bab.html', accessed=ACC),
    'webcor_bab': dict(title='Webcor project page "SFO Harvey Milk Terminal 1 Boarding Area B"', publisher='Webcor (design-build JV with Austin Commercial)',
                       url='https://www.webcor.com/projects/sfo-harvey-milk-terminal-1', read='full', cache=CACHE + 'webcor_bab.html', accessed=ACC),
    'southland_bab': dict(title='Southland Industries project page "San Francisco International Airport Terminal 1 Boarding Area B"', publisher='Southland Industries (mechanical)',
                          url='https://southlandind.com/project/san-francisco-international-airport-terminal-1-boarding-area-b', read='full', cache=CACHE + 'southland_bab.html', accessed=ACC),
    'aip_t1': dict(title='Airport Improvement magazine, "San Francisco Int\'l Rebuilds Terminal 1 for $2.4 Billion" (2020)', publisher='Airport Improvement (trade press quoting SFO, Woods Bagot, Gensler)',
                   url='https://airportimprovement.com/article/san-francisco-int-l-rebuilds-terminal-1-24-billion/', read='full', cache=CACHE + 'aip_t1.html', accessed=ACC),
    'kuthranieri_t1c': dict(title='Kuth Ranieri project page "San Francisco International Airport - Harvey Milk Terminal 1"', publisher='Kuth Ranieri (JV architect with Gensler, T1 Center)',
                            url='https://kuthranieri.com/san-francisco-international-airport-terminal-1c/', read='full', cache=CACHE + 'kuthranieri_t1c.html', accessed=ACC),
    'henselphelps_t1c': dict(title='Hensel Phelps project page "San Francisco International Airport (SFO) Harvey Milk Terminal 1"', publisher='Hensel Phelps (design-builder, T1 Center)',
                             url='https://www.henselphelps.com/project/san-francisco-international-airport-sfo-harvey-milk-terminal-1/', read='full', cache=CACHE + 'henselphelps_t1c.html', accessed=ACC),
    'aiasf_t1': dict(title='AIA San Francisco 2023 Design Awards honoree "SFO Harvey B. Milk Terminal"', publisher='AIA San Francisco',
                     url='https://archive.aiasf.org/architecture/design-awards/2023-design-award-honorees/sfo-harvey-b-milk-international-terminal/', read='full', cache=CACHE + 'aiasf_t1.html', accessed=ACC),
    'gensler_t2': dict(title='Gensler project page "San Francisco International Airport, Terminal 2"', publisher='Gensler',
                       url='https://www.gensler.com/projects/san-francisco-international-airport-terminal-2', read='full', cache=CACHE + 'gensler_t2.html', accessed=ACC),
    'aip_t2': dict(title='Airport Improvement magazine, "SFO Finds Deeper Shade of Green for Terminal 2" (2011)', publisher='Airport Improvement (quoting Turner and Gensler)',
                   url='https://airportimprovement.com/article/sfo-finds-deeper-shade-green-terminal-2/', read='full', cache=CACHE + 'aip_t2.html', accessed=ACC),
    'gbd_t2': dict(title='gb&d magazine "Case Study: SFO Terminal 2" (interview with Gensler)', publisher='gb&d',
                   url='https://gbdmagazine.com/gensler-terminal-2/', read='full', cache=CACHE + 'gbd_t2.html', accessed=ACC),
    'inhabitat_t2': dict(title='Inhabitat "Gensler\'s Green SFO Terminal Renovation to be Completed this April" (2011)', publisher='Inhabitat',
                         url='https://inhabitat.com/genslers-green-sfo-terminal-renovation-to-be-completed-this-april/', read='full', cache=CACHE + 'inhabitat_t2.html', accessed=ACC),
    'ida_bae': dict(title='International Design Awards, winner entry "San Francisco International Airport, Terminal 3, Boarding Area E" by Jeff Henry, Gensler', publisher='IDA (entry text by Gensler)',
                    url='https://www.idesignawards.com/winners/zoom.php?eid=9-9249-15', read='full', cache=CACHE + 'idesign_bae.html', accessed=ACC),
    'gensler_bae': dict(title='Gensler project page "San Francisco International Airport, Terminal 3, Boarding Area E"', publisher='Gensler',
                        url='https://www.gensler.com/projects/san-francisco-international-airport-terminal-3-boarding-area', read='full', cache=CACHE + 'gensler_bae.html', accessed=ACC),
    'hp_bae': dict(title='Hensel Phelps news "SFO Unveils Hensel Phelps Terminal 3, Boarding Area E Design-Build Renovation" and project page "SFO Terminal 3, Boarding Area E"', publisher='Hensel Phelps',
                   url='https://www.henselphelps.com/sfo-unveils-hensel-phelps-terminal-3-boarding-area-e-design-build-renovation/', read='full',
                   cache=CACHE + 'hp_bae_news.html, hp_bae.html', accessed=ACC),
    'bdc_bae': dict(title='Building Design + Construction, "First look: Gensler ups the ante on airport design with new SFO boarding area" (by Gensler), 6 Feb 2014',
                    publisher='BD+C (text supplied by Gensler)', url='https://www.bdcnetwork.com/building-sector-reports/airports/news/55158299/first-look-gensler-ups-the-ante-on-airport-design-with-new-sfo-boarding-area',
                    read='full', cache=CACHE + 'bdc_bae.html', accessed=ACC),
    'mka_t3e': dict(title='Magnusson Klemencic Associates "San Francisco (SFO) Terminal 3 East Retrofit and Expansion"', publisher='MKA (structural engineer)',
                    url='https://www.mka.com/projects/san-francisco-international-airport-sfo-terminal-3-east-retrofit-and-expansion/', read='full', cache=CACHE + 'mka_t3e.html', accessed=ACC),
    'mka_t3w': dict(title='Magnusson Klemencic Associates "San Francisco International Airport (SFO) Terminal 3 West and Modernization"', publisher='MKA (structural engineer)',
                    url='https://www.mka.com/projects/san-francisco-international-airport-sfo-terminal-3-west-and-modernization/', read='full', cache=CACHE + 'mka_t3w.html', accessed=ACC),
    'studio151_t3e': dict(title='Studio 151 "Project - SFO Terminal 3 East Concourse"', publisher='Studio 151 (special-systems consultant)',
                          url='https://www.studio151corp.com/project-sf-terminal-3', read='full', cache=CACHE + 'studio151_t3e.html', accessed=ACC),
    'turner_t3w': dict(title='Turner Construction "San Francisco International Airport Terminal 3 West Modernization"', publisher='Turner Construction',
                       url='https://www.turnerconstruction.com/projects/sfo-terminal-3-west-modernization', read='full', cache=CACHE + 'turner_t3w.html', accessed=ACC),
    'wiki_sfo': dict(title='Wikipedia "San Francisco International Airport" (terminal history section)', publisher='Wikipedia (secondary)',
                     url='https://en.wikipedia.org/wiki/San_Francisco_International_Airport', read='secondary', cache=CACHE + 'wiki_sfo.html', accessed=ACC,
                     note='used only for dates/architects of the original buildings, where no primary source was reachable'),
    # --- FAA
    'faa_dof': dict(title='FAA Digital Obstacle File DAILY_DOF_CSV (DOF.CSV dated 2026-09-18): obstacles 06-035320/321/322/323/330/331/332/351 (BLDG, survey JDATE 2013289, accuracy 1A = +-20 ft horizontal, +-3 ft vertical)',
                    publisher='FAA Aeronautical Information Services', url='https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP', read='full',
                    cache='refs/cache/lighting/DAILY_DOF_CSV.ZIP (+ DOF_README.txt)', accessed=ACC),
    'faa_oe_2012_7455': dict(title='FAA OE/AAA case 2012-AWP-7455-OE (existing antenna, "Short Perm Parking Garage", 130 ft AGL) = DOF 06-039216',
                             publisher='FAA Obstruction Evaluation / Airport Airspace Analysis', url='https://oeaaa.faa.gov/oeaaa/asn-display/asn-case-display-page.html?asn=2012-AWP-7455-OE',
                             read='full', cache=CACHE + 'oe_case_2012AWP7455OE.json', accessed=ACC),
    # --- imagery
    'naip': dict(title='USDA NAIP orthoimagery 2020 (DOQQ m_3712229_ne, flown 2020-05-24, Planetary Computer COG) and 2024 (flown 2024-05-20, USDA image service), 0.6 m GSD; world-grid rasters by tools/buildings/dom_naip_epochs.py',
                 publisher='USDA FPAC-BC Geospatial Enterprise Operations (public domain)', url='https://naipeuwest.blob.core.windows.net/naip/v002/ca/2020/ca_060cm_2020/37122/m_3712229_ne_10_060_20200524.tif',
                 read='full', cache='refs/cache/buildings/domestic/naip/', accessed=ACC,
                 note='2024 raster: refs/cache/naip/naip_2024_sfo_utm10n.tif (tools/imagery/naip_fetch.py); roofs lean by metres (relief displacement), handled in dom_heights.py'),
    'itb_research': dict(title='ITB research spec (parallel workflow): FAA DOF pole lean calibration on NAIP 2024 and the 2024 sun vector (pole 06-034826 shadow)',
                         publisher='this project', url='tools/buildings/itb_naip_measurements.json', read='full', cache='tools/buildings/itb_naip_measurements.json', accessed=ACC),
    'google_ref': dict(title="Owner's Google Maps screenshots (tools/sat/screens/, e.g. b1d51b0f = Boarding Area B), licensed imagery - reference only, never shipped",
                       publisher='Google (licensed)', url='tools/sat/screens/b1d51b0f-image.jpg', read='full', cache='tools/sat/screens/', accessed=ACC),
}

# ------------------------------------------------------------------------------------------------------- items
I = []


def item(id, group, name, value, unit, tag, sources, confidence, status='verified', **kw):
    d = dict(id=id, group=group, name=name, value=value, unit=unit, tag=tag, sources=sources,
             source_urls=[S[s]['url'] for s in sources], confidence=confidence, status=status)
    d.update(kw); I.append(d)


def hitem(rid, id, group, name, confidence, **kw):
    r = HR[rid]
    item(id, group, name, r['h_m'], 'm', 'obs', ['naip', 'itb_research', 'faa_dof'], confidence,
         value_ft=r['h_ft'], sd_m=r['h_sd_m'], method=H['equation'] + ' (dom_heights.py; |s20| calibrated 1.19 +- 0.03)',
         measurement={k: r[k] for k in ('band20', 'band24', 'p', 'den', 'k24_n', 'k20_n') if k in r}, **kw)


# ============================================================================================ common / method
item('frame', 'frame', 'Coordinate frame of all positions', 'ltp-nad83-2011 (tools/geo_frame.py): x east, z south, metres from the FAA ARP; heights in metres above the local apron unless stated',
     None, 'inf', ['sfom_data'], 'high')
item('outline.level', 'frame', 'What the SFO Museum boarding-area polygons are',
     'departure-level (sfo:level 2) floor outlines, not roof outlines; roof edges measured on NAIP lie 0-5 m outside them on the ESE (airfield) faces and 0-2 m inside on the WNW faces (see *.roof_edges)',
     None, 'obs', ['sfom_data', 'naip'], 'medium')
item('sun.2020', 'method', 'Sun / shadow vector on NAIP 2020 over the domestic terminals',
     dict(shadow_azimuth_deg=H['s20']['az_shadow'], shadow_len_per_m=H['s20']['abs'], shadow_len_sd=H['s20']['sd'], sun_elevation_deg=40.0),
     'deg, m/m', 'obs', ['naip', 'faa_dof', 'itb_research'], 'medium',
     method='ATCT shadow azimuth on NAIP 2020 (87.4 +- 1.5 deg), elevation fixed on the 2020-05-24 sun path (NOAA algorithm, dom_sun.py) and '
            'scaled so that FAA DOF 06-035331 (BA F arm roof, 34 ft) and Boarding Area A (k from DOF poles) are reproduced; implied time ~16:45 PDT')
item('sun.2024', 'method', 'Sun / shadow vector on NAIP 2024', dict(shadow_azimuth_deg=6.6, shadow_len_per_m=round(H['s24']['abs'], 3), sun_elevation_deg=72.5),
     'deg, m/m', 'obs', ['itb_research', 'naip'], 'high', method='FAA DOF pole 06-034826 (108 ft) shadow (ITB research); on the 2024-05-20 sun path at 13:14 PDT (dom_sun.py)')
item('control.ba_a', 'method', 'Control 1: Boarding Area A main-body roof (ITB pier) by the two-epoch method', HR['ba_a_body']['h_m'], 'm', 'obs', ['naip', 'itb_research'], 'medium',
     sd_m=HR['ba_a_body']['h_sd_m'], note='lean solved k24.x = %.3f vs 0.413 from the FAA DOF poles (ITB research, extrapolated 116 m): agreement 1 %%; '
                                          'the ITB research gives 17.0 m (low confidence) with its own single-epoch band' % HR['ba_a_body']['k24_x_if_east'])
item('control.ba_f_dof', 'method', 'Control 2: Boarding Area F north-east arm roof vs FAA DOF 06-035331', dict(measured_m=HR['ba_f_ne_arm']['h_m'], dof_m=ftm(34), dof_sd_m=ftm(3)),
     'm', 'obs', ['naip', 'faa_dof'], 'medium', note='DOF 34 ft AGL / 44 ft AMSL, 1A, surveyed 2013 (JDATE 2013289) at world (-1027.2, -211.2): roof of the arm, west edge. '
                                                   'Difference +0.67 m = 1.0 sigma of the measurement + DOF vertical tolerance')

# ============================================================================================ Harvey Milk T1
item('t1.name', 'harvey_milk_t1', 'Name / composition',
     'Harvey Milk Terminal 1 (formerly South Terminal, 1963): Boarding Area B (gates B2-B27), Terminal 1 Center (check-in, security, baggage claim) and Boarding Area C (C1-C11)',
     None, 'pub', ['sfo_pr_t1_final', 'wiki_sfo'], 'high')
item('t1.phases', 'harvey_milk_t1', 'Opening phases of the redevelopment',
     'BA-B first 9 gates + checkpoint + part of T1 Center: July 2019 (23 Jul 2019); 9 more gates + south check-in lobby: May 2020; BA-B complete 2021; final phase (north check-in lobby, mezzanine checkpoint, gates B3 and C1, connector linking all terminals post-security): 17 Jun 2024',
     None, 'pub', ['aip_t1', 'arup_t1', 'sfo_pr_t1_final'], 'high')
item('t1.team', 'harvey_milk_t1', 'Design / build teams',
     'BA-B: design-builder Austin Commercial + Webcor Builders JV, architects HKS / Woods Bagot / ED2 International / KYA JV (+ Tsao Design Group), engineer Arup; '
     'T1 Center: design-builder Hensel Phelps, architects Gensler / Kuth Ranieri JV; construction manager AECOM / Cooper Pugeda JV (T1C), WSP / Parsons Brinckerhoff / AGS (BA-B)',
     None, 'pub', ['aip_t1', 'arup_t1', 'dbia_bab', 'webcor_bab', 'kuthranieri_t1c', 'henselphelps_t1c', 'aiasf_t1'], 'high')
item('t1.area', 'harvey_milk_t1', 'Floor areas (published, differing definitions)',
     dict(ba_b_sf=[619150, 617700, 500000], t1_center_sf=[1100000, 900000]), 'sq ft', 'pub',
     ['dbia_bab', 'aip_t1', 'woodsbagot_bab', 'kuthranieri_t1c', 'henselphelps_t1c'], 'medium', status='conflict',
     note='BA-B: 619,150 sf (DBIA, Southland, RDH ~619,000), 617,700 sf "on 3 levels" (Airport Improvement 2020), 46,000 m2 / 500,000 sf (Woods Bagot); '
          'T1 Center: 1.1 million sf (Kuth Ranieri), 900,000 SF (Hensel Phelps)')

# --- Boarding Area B
item('bab.gates', 'boarding_area_b', 'Aircraft gates', 25, 'gates', 'pub', ['arup_t1', 'dbia_bab', 'woodsbagot_bab'], 'high',
     note='incl. 4 international swing gates (Airport Improvement); Webcor: "24 new gates"; Wikipedia counts 26 (B2-B27) after B3 opened in 2024')
item('bab.levels', 'boarding_area_b', 'Levels',
     'apron level + concourse (departure) level + mezzanine (airline clubs, international corridor): "two levels and a mezzanine" (Arup) = "three-story" (RDH) = "3 levels" (Airport Improvement)',
     None, 'pub', ['arup_t1', 'rdh_bab', 'aip_t1', 'dbia_bab'], 'high')
item('bab.structure', 'boarding_area_b', 'Structure', 'Type I cast-in-place concrete frame on a pile foundation; piles 100 ft deep (seismic)', None, 'pub',
     ['rdh_bab', 'webcor_bab', 'aip_t1'], 'high')
item('bab.glazing', 'boarding_area_b', 'Facade glazing',
     'electrochromic (View Dynamic Glass) glazing throughout the concourse level, 112,000 sq ft; Low-E high-performance glazing at the clerestory level; floor-to-ceiling windows at the gates',
     None, 'pub', ['arup_t1', 'aip_t1', 'woodsbagot_bab'], 'high')
item('bab.clerestory', 'boarding_area_b', 'Roof section: raised concourse with clerestory',
     'central concourse ceiling rises to a clerestory band glazed on both sides (interior photos 2019-2024 and Arup "clerestory level"); gate holdrooms along the airfield faces',
     None, 'pub', ['arup_t1'], 'medium', note='geometry (clerestory height and width) not published; visible in Commons photo p02 (Elbeaux 2024) and the Woods Bagot interior photos (reference only)')
item('bab.pv', 'boarding_area_b', 'Rooftop photovoltaic array', dict(power_MW=1.0, power_MWdc=1.2, panels=3000), 'MW / panels', 'pub',
     ['arup_t1', 'cei_bab', 'hks_bab', 'rdh_bab'], 'high', note='"1 MW solar array located on the building\'s roof" (Arup, RDH, HKS extract); "1.2-MWDC rooftop array consisting of nearly 3,000 photovoltaic (PV) panels" (Cupertino Electric)')
item('bab.pv_layout', 'boarding_area_b', 'PV layout on the roof (imaged)',
     'rows parallel to the pier axis, each ~5.5 m wide at ~9 m pitch, covering the concourse roof between the airfield edge and the central clerestory/skylight strip; a narrow row along the ESE (airfield) roof edge',
     None, 'obs', ['naip', 'google_ref'], 'medium', method='NAIP 2020/2024 cross-profiles (dom_profile.py) and the Google screenshot b1d51b0f (reference only)')
item('bab.roof_wells', 'boarding_area_b', 'Roof wells / courtyards on the landside (WNW) part',
     'the Civic Design Review Committee asked the team to investigate "the use of roof wells as intake zones" (Aug 2016); imagery shows long sunken roof courtyards with planting on the WNW side of the pier (north half) crossed by two bridges',
     None, 'pub', ['cdr_minutes_2016_08', 'naip', 'google_ref'], 'medium')
hitem('ba_b_south', 'bab.h_roof', 'boarding_area_b', 'Outer roof edge height above apron, south half (t -1238..-1176)', 'medium',
      note='the dark ESE perimeter strip (6 m) and the PV field shift alike between epochs (3.3 / 3.4 m), i.e. same height within +-1.5 m; the central clerestory rises above this (not measured)')
te = HR['ba_b_south'].get('true_edges', {})
item('bab.roof_edges', 'boarding_area_b', 'Lean-free roof edges, south half (world lines)', te, 'm', 'obs', ['naip'], 'medium',
     note='ESE roof edge 3.3 m outside the SFO Museum level-2 outline (roof overhang), WNW edge 1.6 m inside it; roof width 55.4 m vs outline 53.7 m (+-1 m)')
item('bab.materials', 'boarding_area_b', 'Exterior metal / glass palette',
     'glass and painted metal panels (airside); the team proposed metal spandrel panels instead of continuous louvres for exhaust/intake (CDR Phase 2, Aug 2016)',
     None, 'pub', ['cdr_minutes_2016_08'], 'medium', note='colours not published; T3W CDR cites "electrochromic glass (Terminal 1)" as a campus cue')

# --- T1 Center (main hall)
item('t1c.skylight_truss_h', 'terminal_1_center', 'Height of the skylight trusses above the Main Hall (Level 3) floor', 70, 'ft', 'pub', ['sfom_reflectors'], 'high',
     value_m=ftm(70), note='"inserted within the truss structure of the skylights, 70 feet above the floor" - floor = Main Hall, Level 3, pre-security; the floor elevation above the apron is not published')
item('t1c.skylight_reflectors', 'terminal_1_center', 'Skylight light reflectors (art, James Carpenter)', dict(count=4, length_ft=180, width_ft=30), 'ft', 'pub', ['sfom_reflectors'], 'high',
     value_m=dict(length=ftm(180), width=ftm(30)), note='each reflector sits in a skylight -> at least four skylights >= 55 m x 9 m; AIP 2020 (phase 1) mentions "three large skylights"')
item('t1c.skylights_count', 'terminal_1_center', 'Number of main-hall skylights', dict(sfo_museum=4, airport_improvement_2020=3), 'skylights', 'pub', ['sfom_reflectors', 'aip_t1'], 'medium',
     status='conflict', note='3 in the 2020 article (only half the hall existed then); 4 reflectors in the finished hall. Not identified on NAIP 2024 (roof is saturated white with PV)')
item('t1c.landside_facade', 'terminal_1_center', 'Landside (curb) facade',
     'two-tier fritted-glass curtain wall with vertical mullions (pattern "reminiscent of Redwood trees") above a continuous glass canopy over the departures curb; clear glass below the canopy; warm (wood) entries',
     None, 'pub', ['aip_t1', 'cdr_minutes_2016_08', 'cdr_t3w_dd_2024'], 'high', note='CDR Aug 2016: "fritted glass ... the top half material of the landside of the terminal, while the glass below the canopy would remain clear"; laminated-wood vestibules; photos: Commons p00 (Famartin 2025-08-12), RDH facade photos (reference only)')
item('t1c.roof_pv', 'terminal_1_center', 'Main-hall roof', 'roof almost entirely covered by PV rows laid out radially (fan) following the curved hall; three ~9 x 11 m light-blue glazed openings visible at world (-826, 460), (-815, 508), (-884, 530)',
     None, 'obs', ['naip'], 'low', method='visual reading of NAIP 2024 at 0.2 m/px (t1hall_2024_z.jpg); positions +-3 m, lean-affected')
item('t1c.h_roof', 'terminal_1_center', 'Main-hall roof height above apron', None, 'm', 'obs', ['naip', 'sfom_reflectors'], 'low', status='unverified',
     note='not measured: curved faces, the landside faces are over roadways/garage and the airfield face has a strip whose shadow is ambiguous; lower bound ~ Level 3 floor + 70 ft (21.3 m)')
item('t1.dof_2013', 'harvey_milk_t1', 'FAA DOF building points on the old (pre-2019) Terminal 1', dict(obst_06_035351_ft=50, obst_06_035323_ft=17, obst_06_035322_ft=24), 'ft AGL', 'pub', ['faa_dof'], 'low',
     status='verified', note='surveyed 2013 (JDATE 2013289): 06-035351 50 ft at (-881.4, 518.1) was on the old T1 center (demolished 2019-2023); 06-035323 17 ft at (-696.7, 628.7) and 06-035322 24 ft at (-620.2, 493.1) are on the apron today (old structures or jet bridges). Superseded - do not use for the new T1')

# --- Boarding Area C
item('bac.gates', 'boarding_area_c', 'Gates', 11, 'gates (C1-C11)', 'pub', ['wiki_sfo', 'sfo_pr_t1_final'], 'medium', status='secondary-only',
     note='gate C1 opened 17 Jun 2024 (SFO); total from Wikipedia')
item('bac.history', 'boarding_area_c', 'History', 'pier of the 1963 South Terminal (Welton Becket and Associates), renovated 1988 and "refreshed" with the T1 Center project (2024); between Jun 2020 and Oct 2024 counted as part of Terminal 2',
     None, 'pub', ['wiki_sfo', 'henselphelps_t1c'], 'low', status='secondary-only')
hitem('ba_c_east', 'bac.h_roof', 'boarding_area_c', 'Roof edge height above apron, east half, NNE face (single-face estimate)', 'low',
      note='single-face method with an assumed lean k24.x = 0.40 +- 0.06 (from the two-epoch sites); the west half gives an inconsistent band (neighbouring T1 structures in the 2020 shadow)')
item('bac.roof', 'boarding_area_c', 'Roof features (imaged)', 'two long dark bands along the pier on both sides of a lighter central spine (glazed roof monitors or dark roofing - unresolved), a light-blue glazed patch near world (-675, 415) on NAIP 2024, rounded ESE end',
     None, 'obs', ['naip'], 'low')

# ============================================================================================ Terminal 2 / BA D
item('t2.history', 'terminal_2', 'History', 'opened 27 Aug 1954 as the Central Terminal; rebuilt as the International Terminal (Gensler, 1983); closed 2000; renovated and reopened 14 Apr 2011 (Gensler with Turner, design-build, $383 M) with 14 gates',
     None, 'pub', ['gbd_t2', 'aip_t2', 'gensler_t2', 'wiki_sfo'], 'high')
item('t2.area_levels', 'terminal_2', 'Area / levels', '640,000 sq ft, two-level structure', None, 'pub', ['aip_t2'], 'high')
item('t2.daylight', 'terminal_2', 'Daylighting', 'custom clerestory windows and skylights over the ticketing lobby and recompose areas; transparent (west-facing) facade; interior "floating angular planes" (clouds) below the roof',
     None, 'pub', ['gbd_t2', 'aip_t2', 'inhabitat_t2'], 'high', note='positions/sizes of the clerestories and skylights are not published')
item('t2.pv', 'terminal_2', 'Photovoltaics', '456-kW PV system on an adjacent SFO building (not on T2) providing ~20 % of T2 power', None, 'pub', ['gbd_t2'], 'high')
item('t2.old_tower', 'terminal_2', 'Former ATCT on Terminal 2', 'the pre-2016 control tower stood on top of T2 (photos 2009, 2013); replaced by the 2016 ATCT; its removal date is covered by the tower research',
     None, 'pub', ['wiki_sfo'], 'medium', status='secondary-only')
item('t2.landside', 'terminal_2', 'Landside facade', 'light metal-panel box with the "Terminal 2" sign and a glass entry wall ("neutral exterior, warm interior"; "massing hierarchy") - T3W CDR campus study',
     None, 'pub', ['cdr_t3w_dd_2024'], 'medium')
item('bad.gates', 'boarding_area_d', 'Gates', 14, 'gates (D1-D12, D14-D16)', 'pub', ['gensler_t2', 'wiki_sfo'], 'high')
hitem('ba_d_head', 'bad.h_roof', 'boarding_area_d', 'Roof height above apron, D head (ESE face) paired with the south WNW face 90 m away', 'low',
      note='two-epoch method, but the two faces may belong to different roof levels; FAA DOF (2013) gives 25 ft (7.6 m) at (-486.9, 71.9) and 24 ft (7.3 m) at (-482.1, 257.8) near the head corners (+-6 m horizontal)')
item('bad.dof', 'boarding_area_d', 'FAA DOF building points at the D head', dict(obst_06_035330_ft=25, obst_06_035321_ft=24, obst_06_035320_ft=25), 'ft AGL', 'pub', ['faa_dof'], 'medium',
     note='06-035330 (-486.9, 71.9), 06-035321 (-482.1, 257.8), 06-035320 (-444.3, 194.0; 30 m east of the head, probably a jet bridge / apron structure). 2013 survey, T2 unchanged since 2011')
te = HR['ba_d_head'].get('true_edges', {})
item('bad.roof_edges', 'boarding_area_d', 'Lean-free roof edges used (world lines)', te, 'm', 'obs', ['naip'], 'low')
item('bad.roof', 'boarding_area_d', 'Roof features (imaged)', 'large trapezoidal head with two semicircular (horseshoe) roof features at its NW and SE ends and linear skylights; pier from T2 heading ESE',
     None, 'obs', ['naip'], 'low')

# ============================================================================================ Terminal 3 / BA E / BA F
item('t3.history', 'terminal_3', 'History', 'North Terminal by San Francisco Airport Architects (John Carl Warnecke and Associates, Dreyfuss + Blackford, minority architects): groundbreaking 22 Apr 1971, BA F opened 1979, BA E 1981; BA-E renovated 2014 and T3 East rebuilt (Hensel Phelps / Gensler; Wikipedia: 2015); T3 West modernisation under construction since Aug 2024 (completion expected 2029)',
     None, 'pub', ['wiki_sfo', 'sfo_pr_t3w', 'mka_t3e', 'studio151_t3e'], 'medium', status='secondary-only', note='original architects and dates only via Wikipedia')
item('t3.levels_datum', 'terminal_3', 'Project floor elevations (95% CD, Oct 2023)',
     dict(T3_L1_arrivals_TOC="11'-0\"", T3W_L1_arrivals_TOC="10'-3\"", T3_L2_departures_TOC="27'-0\"", T3_L2M_mezzanine_TOC="42'-6\"", T3_L3_FIS_corridor_TOC="45'-0\"",
          T3_R2_top_of_roof_high_pt="58'-6\"", T3W_top_of_parapet="66'-0\"", T3_R3_top_of_roof_high_pt="81'-0\""),
     'ft (project datum)', 'pub', ['cdr_t3w_cd_2023'], 'high', note='sheet 5A-A5.01.01/.02 level markers; datum not stated on the sheets (see t3.heights_above_L1)')
lv = {'L2 departures': 27.0 - 11.0, 'L2M mezzanine': 42.5 - 11.0, 'L3 FIS corridor': 45.0 - 11.0, 'R2 roof high point': 58.5 - 11.0,
      'R3 roof high point': 81.0 - 11.0, 'T3W parapet (new)': 66.0 - 10.25}
item('t3.heights_above_L1', 'terminal_3', 'Heights above the T3 arrivals floor (L1)', {k: dict(ft=v, m=ftm(v)) for k, v in lv.items()}, 'ft / m', 'inf',
     ['cdr_t3w_cd_2023'], 'high', method='elevation minus L1 TOC (11\'-0" T3, 10\'-3" T3W)',
     note='apron vs L1: DOF ground near T3 is 9-10 ft AMSL (06-035331: 44-34; 06-035332: 25-16); if the project datum is ~AMSL, L1 is 1-2 ft above the apron [inf, unverified]')
item('t3w.wall_field', 'terminal_3_west', 'Airside "field" facade wall section (new, under construction)',
     dict(arrivals_to_departures="16'-0\"", departures_to_international="18'-0\"", international_to_parapet="22'-0\"", arrivals_to_parapet="56'-0\"",
          parapet_above_roof="3'-6\" (0'-42\")", window_heights="10'-0\" x2 with a 2'-0\" horizontal mullion band"),
     'ft', 'pub', ['cdr_t3w_cd_2023'], 'high', note='CDR p.18; materials: ACM panel, aluminium window wall with vertical fins, accent frame / deluge concealment, single-ply roofing')
item('t3w.wall_gatehouse', 'terminal_3_west', 'Airside "gatehouse" facade wall section (new F1-F4 gatehouses)',
     dict(arrivals_to_departures="16'-9\"", departures_to_international="18'-0\"", arrivals_to_parapet="59'-7\"", parapet_above_roof="8'-0\" (mechanical penthouse screen)"),
     'ft', 'pub', ['cdr_t3w_cd_2023'], 'high', note='CDR p.20; roof = mechanical penthouse; escalator/stair behind glazing')
item('t3w.materials', 'terminal_3_west', 'New T3W exterior material legend (95% CD)',
     'ACM rainscreen panels "Duranar XL Whetstone Gray Metallic" (MP-50), "Duranar Sunstorm Norfolk Gray Mica" dark gray (MP-51), "Focus Black" (MP-52); perforated metal panel to match the existing T3E penthouse; electrochromic glazing (GL-50); insulated glass with frit (GL-51); laminated insulated skylight glazing (GL-60); aluminium window wall and vertical mullion fins (dark gray metallic)',
     None, 'pub', ['cdr_t3w_cd_2023'], 'high')
item('t3w.update_2026', 'terminal_3_west', 'Post-Phase-3 change (May 2026)', 'SFO and United agreed to enlarge the lounge: one additional storey on the airside / east side; Level 2M/3 club 22,950 SF, Level 4 club 22,450 SF, Level 5 mechanical penthouse 15,300 SF',
     None, 'pub', ['cdr_t3w_update_2026'], 'high', note='the as-built T3W massing is therefore not final; model the 2024 (pre-construction) state or the approved design only after the owner decides')
item('t3w.scope', 'terminal_3_west', 'T3W project scope', 'renovate the existing 650,000 sq ft western half of T3 (seismic retrofit, security, check-in), +200,000 sq ft new; new six-storey Courtyard 4 (C4C) building; FIS sterile connector to the ITB; complete replacement of the T3 facade; $2.6 B',
     None, 'pub', ['sfo_pr_t3w', 'mka_t3w', 'cdr_t3w_c4c_2024', 'turner_t3w'], 'high')
item('t3e.facade', 'terminal_3_east', 'T3 East exterior (existing, reference for T3W)',
     'clear perimeter glass with grey frit, metal panel (platinum), metal panel (dark gray metallic), aluminium vertical mullion fins, metal brow surround; rooftop mechanical penthouse clad in perforated/corrugated light-gray metal with wide-profile corrugated accent stripes',
     None, 'pub', ['cdr_t3w_cd_2023'], 'high', note='CDR p.8 and p.16 photos (reference only)')
item('t3e.size', 'terminal_3_east', 'T3 East size', dict(renovation_sf=400000, expansion_sf=53000, new_gates=3, mka_sf=320000, stories=3), 'sq ft', 'pub',
     ['studio151_t3e', 'mka_t3e'], 'medium', status='conflict', note='Studio 151: 400,000 SF renovation + 53,000 SF expansion adding 3 gates; MKA: 320,000 ft2, three-story')
item('t3.penthouses', 'terminal_3', 'Existing rooftop mechanical penthouses', 'one large penthouse on T3 East and a row of smaller penthouses on T3 West (CDR "Existing Massing"); new T3W penthouses added by the project',
     None, 'pub', ['cdr_t3w_cd_2023', 'cdr_t3w_dd_2024'], 'high', note='plan sizes and heights not dimensioned in the CDR set')
item('bae.renovation', 'boarding_area_e', 'BA-E renovation', 'design-build Hensel Phelps with Gensler and the KPA Group; unveiled 25 Jan 2014; $138 M; 10 United gates; complete demolition from the concourse level up and a 30,000 SF concourse expansion; LEED Gold; part of the T3 East capital program (68,800 sf BA-E + 150,000 sf eastern concourse)',
     None, 'pub', ['hp_bae', 'bdc_bae', 'gensler_bae', 'ida_bae'], 'high')
item('bae.area', 'boarding_area_e', 'BA-E area', dict(gensler_sf=65000, hensel_phelps_sf=68800), 'sq ft', 'pub', ['gensler_bae', 'hp_bae'], 'medium', status='conflict')
item('bae.roof', 'boarding_area_e', 'BA-E roof', '"With tapered edges overhanging clerestory glazing, the roof is structured with lightweight, long-span trusses concealed within a finished architectural ceiling" (middle two column rows removed)',
     None, 'pub', ['ida_bae'], 'high')
item('bae.facade', 'boarding_area_e', 'BA-E facade', 'clear perimeter glass (with grey frit where fritted), light-gray metal panel and dark-gray metallic metal panel bands above/below the glazing, aluminium vertical mullion fins (CDR photo keys 1-4)',
     None, 'pub', ['cdr_t3w_cd_2023'], 'high', note='CDR p.9 photos (reference only)')
hitem('ba_e_north', 'bae.h_roof', 'boarding_area_e', 'Roof (tapered fascia) edge height above apron, north part (t -350..-310)', 'medium',
      note='fascia edge and roof texture shift alike (2.2 / 2.5 m) -> one roof level at the edge; values from the s-profiles recorded in dom_heights.py')
item('baf.gates', 'boarding_area_f', 'Gates', 18, 'gates (F5-F22 today; F1-F4 being rebuilt by T3W)', 'pub', ['wiki_sfo', 'cdr_t3w_cd_2023'], 'medium', status='secondary-only')
item('baf.hub', 'boarding_area_f', 'BA-F rotunda', 'octagonal rotunda hub where the arms meet (CDR massing, NAIP)', None, 'pub', ['cdr_t3w_dd_2024', 'naip'], 'high')
hitem('ba_f_ne_arm', 'baf.h_roof_ne_arm', 'boarding_area_f', 'Roof height above apron, north-east arm', 'medium', note='control against FAA DOF 06-035331 (34 ft)')
item('baf.dof', 'boarding_area_f', 'FAA DOF building points on BA-F', dict(obst_06_035331_ft=34, obst_06_035332_ft=16), 'ft AGL', 'pub', ['faa_dof'], 'high',
     note='06-035331 (-1027.2, -211.2) roof of the NE arm; 06-035332 (-1022.1, -243.8) 16 ft at the arm tip (lower end structure or bridge rotunda)')
te = HR['ba_f_ne_arm'].get('true_edges', {})
item('baf.roof_edges', 'boarding_area_f', 'Lean-free roof edges of the NE arm (world lines)', te, 'm', 'obs', ['naip'], 'medium',
     note='ESE edge 1.8 m outside the level-2 outline, WNW edge 1.3 m inside')

# ============================================================================================ misc
item('garage_antenna', 'context', 'DOF 06-039216 "BLDG 130 ft" near T2/T3 is not a terminal', '130 ft AGL antenna on the Short-Term (central) Parking Garage, FAA study 2012-AWP-7455-OE',
     None, 'pub', ['faa_oe_2012_7455', 'faa_dof'], 'high')

# ------------------------------------------------------------------------------------------------------- photos
PH = json.load(open(os.path.join(HERE, '..', '..', 'refs', 'cache', 'buildings', 'domestic', 'photos', 'manifest.json')))
USE = {'p00.jpg': 'T1 landside facade (fritted glass, canopy) from the AirTrain, 2025', 'p02.jpg': 'BA-B concourse interior with the clerestory band, 2024',
       'p06.jpg': 'T2 with the old tower on top, from the AirTrain, 2013', 'p07.jpg': 'T2 2009 (old tower)', 'p13.jpg': 'T2 landside sign/facade 2025',
       'p16.jpg': 'T3/BA-G apron view 2018', 'p21.jpg': 'aerial overview 2022', 'p22.jpg': 'oblique aerial of T2/BA-D, ATCT, T3, BA-E, BA-F from the NE, Sep 2025 (best exterior reference)',
       'p23.jpg': 'oblique aerial 2025 (ITB AirTrain station, BA-G)'}
photos = []
for fn, v in PH.items():
    photos.append(dict(file='refs/cache/buildings/domestic/photos/' + v['local'], page=v['url'], title='File:' + fn, licence=', '.join(v['licence']),
                       author=(v['author'] or 'see page (creator template)')[:80], date=(v['date'] or '')[:40], camera=v.get('camera'),
                       use=USE.get(v['local'], v['note'])))

spec = dict(
    schema='sfo3d building spec v1',
    building='Domestic terminals: Harvey Milk Terminal 1 (Boarding Areas B, C), Terminal 2 (Boarding Area D), Terminal 3 (Boarding Areas E, F)',
    generated='2026-09-26', generator='tools/buildings/build_spec_domestic.py', doc='docs/research/buildings_domestic.md',
    frame=dict(id='ltp-nad83-2011', axes='world x east, z south, metres from the ARP; airport grid s (117.83 deg) / t (27.83 deg) as in tools/geo_frame.py'),
    status='RESEARCH DRAFT for owner review. No 2-D sheet or 3-D geometry has been built from it.',
    tags=dict(pub='published by an original source (SFO, SF Arts Commission CDR submittals, architect/engineer/builder, FAA) - see sources[].read',
              obs='measured by us on public imagery/data (NAIP 2020/2024, FAA DOF, SFO Museum footprints) with the stated method',
              inf='derived by stated arithmetic from pub/obs values'),
    confidence_scale='high = primary source read in full or a direct measurement checked against a control; medium = one source or a measurement +-1 m; low = single-face/assumed-lean measurement, conflicting or snippet sources',
    status_values=dict(verified='read first-hand / measured', conflict='sources disagree - all values listed', **{'snippet-only': 'only search-engine extracts could be read'},
                       **{'secondary-only': 'only via Wikipedia'}, unverified='no value could be verified - do not build on it without the owner'),
    sources=S, items=I, photos=photos,
    current_model_deviations=[
        'tools/build_terminal_parts.py: every pier PIER_H = 14.6 m. Measured: BA-B 12.9 +- 0.7, BA-E 13.5 +- 0.7, BA-F NE arm 11.0 +- 0.7 (DOF 10.4), BA-D ~8.9 (low), BA-C ~7.5 (low)',
        'tools/build_terminal_parts.py: HALL_H T1 20.0 / T2 19.0 / T3 21.0 m "approximate". Published T3: roof high points 47.5 ft (14.5 m, R2) and 70 ft (21.3 m, R3) above L1; T1 main hall skylight trusses 70 ft above the Level 3 floor; T2 not measured',
        'js/live/terminals.js: piers with glass curtain walls to 13.4 m, light roof with a skylight spine - BA-B has a PV-covered roof with a central clerestory and landside roof wells; BA-E has a tapered overhanging fascia over clerestory glazing; T3E/T3W have large mechanical penthouses',
        'SFO Museum polygons are level-2 floor outlines: measured roof edges overhang them by up to ~3-5 m on the airfield (ESE) faces',
    ],
    unverified=[
        'HKS Boarding Area B page (403): only a search extract',
        'Architect Magazine and Architizer BA-E / T2 pages (403); Wayback Machine refused',
        'flysfo.com "Harvey Milk Terminal 1 Redevelopment" page (403)',
        'Civic Design Review presentations for T1 Center / BA-B (2016-2017) are not online - only minutes',
        'Original architects/dates of the 1954 / 1963 / 1971-81 terminals: Wikipedia only',
    ],
    open_questions=[
        'Datum of the T3W CDR elevations (L1 = 11\'-0"): SFO project datum vs NAVD88 - ask SFO Design & Construction; needed to turn 58\'-6" / 81\'-0" into heights above the apron (currently taken relative to L1).',
        'T1 Center and T2 main-hall roof heights, clerestory/skylight geometry: not published; NAIP faces are curved or over roadways. A licensed photo with a scale reference or the Level-3 floor elevation would close it.',
        'BA-B clerestory: height/width of the raised central roof above the 12.9 m outer roof; BA-B north half and the landside roof wells not measured.',
        'BA-C and BA-D heights are low-confidence (single face / faces far apart); DOF 2013 points at D (24-25 ft) are 1.3-1.6 m below our 8.9 m.',
        'Which structures the DOF points 06-035320/322/323/332 represent (apron objects? rotundas?).',
        'T3W is under construction (2024-2029) with a 2026 design change (+1 storey airside): which state should the model show?',
        'Relief leans on NAIP 2020 vary irregularly across the site (frame/strip seams); a true orthophoto or lidar (none public) would remove the ambiguity.',
        'Cross-workflow: the ATCT shadow on NAIP 2020 with the calibrated |s20| = 1.19 implies the tower axis at x = -733.5 +- 3, about 7 m east of the tower research value (-740.5); worth re-checking there.',
    ],
)
json.dump(spec, open(os.path.join(HERE, 'spec_domestic.json'), 'w'), indent=1, ensure_ascii=False)
print('items', len(I), 'sources', len(S), 'photos', len(photos))
