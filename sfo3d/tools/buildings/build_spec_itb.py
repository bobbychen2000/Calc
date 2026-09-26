"""Builds tools/buildings/spec_itb.json - the verified-dimension spec of the International Terminal Building (ITB,
now the Senator Dianne Feinstein International Terminal) with its main hall roof and Boarding Areas A and G, for the
2-D drawing stage (docs/drawings/buildings/) and, after the owner's review, the 3-D build.

Every value carries: tag (pub = published by an original/primary source; obs = measured by us on public imagery or
data with a stated method; inf = inferred/derived from pub/obs values by stated arithmetic), sources (ids into
`sources`), confidence (high / medium / low) and, where applicable, the conflicting values. Nothing is guessed
silently: items without an original source are listed under `unverified` / `open_questions` instead of getting a value.

Inputs: tools/buildings/itb_naip_measurements.json (itb_naip_measure.py), tools/buildings/itb_photo_skyline.json
(itb_photo_skyline.py). Source documents and photos are cached in refs/cache/buildings/itb/ (gitignored).
Usage: python3 tools/buildings/build_spec_itb.py
"""
import json, math, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, 'itb_naip_measurements.json')))
PH = json.load(open(os.path.join(HERE, 'itb_photo_skyline.json')))
FT = 0.3048
ACC = '2026-09-26'

# ------------------------------------------------------------------------------------------------------ sources
# read: 'full' = the page/document itself was read; 'snippet' = only search-engine extracts of it could be read (the
# page blocks automated access); 'secondary' = a secondary source citing an original we could not open.
S = {
    'som': dict(title='SOM project page: San Francisco International Airport - International Terminal', publisher='Skidmore, Owings & Merrill',
                url='https://www.som.com/projects/san-francisco-international-airport-international-terminal/', read='full',
                cache='refs/cache/buildings/itb/som_project.html', accessed=ACC),
    'som_sketch': dict(title='SOM project page, image "sfairport_1400x800_plan_01" (Craig Hartman concept sketches: west wall, roof segment, site diagram, roof elevation)',
                       publisher='SOM (image (c) SOM - reference only)', url='https://www.som.com/wp-content/uploads/2021/07/sfairport_1400x800_plan_01jpg.jpg',
                       read='full', cache='refs/cache/buildings/itb/sfairport_1400x800_plan_01jpg.jpg', accessed=ACC,
                       note='concept-stage sketch (competition 1993 / design 1995); handwritten dimensions are design intent, not as-built'),
    'som_section': dict(title='SOM project page, images "sfia_1575x900_som_02" (Section at ticket counter) and "_03" (perspective section of the hall)',
                        publisher='SOM (images (c) SOM - reference only)', url='https://www.som.com/wp-content/uploads/2021/07/sfia_1575x900_som_03.png', read='full',
                        cache='refs/cache/buildings/itb/sfia_1575x900_som_02.png, sfia_1575x900_som_03.png', accessed=ACC,
                        note='perspective drawings, not to scale; used for topology only (5 three-chord trusses in section, column under each truss)'),
    'sfom_sketch': dict(title='SFO Museum Collection 2000.086.009, "Architectural design drawing: SFO, SOM" (Craig Hartman roof plan sketch, 1995)',
                        publisher='SFO Museum', url='https://collection.sfomuseum.org/objects/1511910403/', read='full',
                        cache='refs/cache/buildings/itb/sfom_2000.086.009.jpg', accessed=ACC, note='developmental sketch: column grid letters B-J, skylights, 3-D trusses'),
    'msc2000': dict(title='R. E. Ferch, P. M. Hassett, "S.F. Airport Roof Truss Erection", Modern Steel Construction, February 2000 (AISC)', publisher='AISC',
                    url='https://www.aisc.org/globalassets/modern-steel/archives/2000/02/2000v02_sf_airport.pdf', read='snippet',
                    note='PDF behind a Cloudflare challenge (curl 403 / WebFetch 403; Scribd copy 373810186 also blocked); abstract text read via search-engine extracts only'),
    'seaonc': dict(title='Hensolt SEAONC Legacy Project: San Francisco Airport International Terminal Building', publisher='Structural Engineers Association of Northern California',
                   url='https://legacy.seaonc.org/structure/sfo-international-terminal/', read='snippet',
                   note='site returns an sgcaptcha challenge to curl and an empty page to WebFetch; text read via search-engine extracts only'),
    'smith_emery': dict(title='Smith-Emery project page: San Francisco International Airport Roof Truss System', publisher='Smith-Emery (inspection/testing)',
                        url='https://www.smithemery.com/staging/4272/projects/san-francisco-international-airport-roof-truss-system-san-francisco-california/', read='full', accessed=ACC),
    'sfgate2000': dict(title='D. Armstrong, "SFO terminal ready to take wing", San Francisco Examiner (SFGate), 2000-01-30', publisher='SF Examiner / SFGate',
                       url='https://www.sfgate.com/business/article/SFO-terminal-ready-to-take-wing-3077658.php', read='full', cache='refs/cache/buildings/itb/sfgate_3077658.html', accessed=ACC),
    'enclos': dict(title='Enclos project page: San Francisco International Airport: International Terminal', publisher='Enclos (curtain wall)',
                   url='https://enclos.com/project/san-francisco-international-airport-international-terminal/', read='full', accessed=ACC),
    'tutor_itb': dict(title='Tutor Perini project page: SFO International Terminal', publisher='Tutor Perini',
                      url='https://www.tutorperini.com/projects/aviation/sfo-international-terminal/', read='full', accessed=ACC),
    'tutor_bag': dict(title='Tutor Perini project page: SFO Boarding Area G', publisher='Tutor Perini',
                      url='https://www.tutorperini.com/projects/aviation/sfo-boarding-area-g/', read='full', accessed=ACC),
    'ags_baa': dict(title='AGS project page: SFO Boarding Area A Gate Enhancements', publisher='AGS Inc.', url='https://www.agsinc.com/projects/sfo-gate-enhancement', read='full', accessed=ACC),
    'airportworld25': dict(title="SFO's International Terminal celebrates 25th anniversary", publisher='Airport World',
                           url='https://airport-world.com/sfos-international-terminal-celebrates-25th-anniversary/', read='full', accessed=ACC),
    'webcor_roof': dict(title='Webcor: SFO International Terminal Building (ITB) Roof Upgrade Project', publisher='Webcor',
                        url='https://www.webcor.com/projects/sfo-international-terminal-building-itb-roof-upgrade-project', read='full', accessed=ACC),
    'webcor_ceremony': dict(title='Webcor: Ceremony Marks Start of Upgrade to Roof of 24-Year-Old Terminal Roof (2024-06-27)', publisher='Webcor',
                            url='https://www.webcor.com/webcor-articles/ceremony-marks-start-of-upgrade-to-roof-of-24-year-old-terminal-roof', read='full', accessed=ACC),
    'ftf_roof': dict(title='FTF Engineering: SFO Dianne Feinstein International Terminal - Building Envelope Upgrade & Solar Panel Installation', publisher='FTF Engineering',
                     url='https://ftfengineering.com/portfolio_page/international-terminal-building-roof-upgrade-sfo/', read='full', accessed=ACC),
    'ai_roof': dict(title='"SFO to upgrade terminal roof", Airports International', publisher='Airports International',
                    url='https://www.airportsinternational.com/article/sfo-upgrade-terminal-roof', read='snippet', note='HTTP 403 to WebFetch; read via search extracts'),
    'radp_nop': dict(title='SF Planning, Case 2017-007468ENV, SFO Recommended Airport Development Plan - Notice of Preparation of an EIR (May 2019)',
                     publisher='San Francisco Planning Department', url='https://sfmea.sfplanning.org/2017-007468ENV_SFO_RADP_NOP.pdf', read='full',
                     cache='refs/cache/buildings/itb/radp_nop_2017-007468ENV.pdf', accessed=ACC),
    'wiki_sfo': dict(title='Wikipedia: San Francisco International Airport (International Terminal section)', publisher='Wikipedia',
                     url='https://en.wikipedia.org/wiki/San_Francisco_International_Airport', read='secondary', cache='refs/cache/buildings/itb/wiki_sfo.html', accessed=ACC,
                     note='cites "Fact Sheet - International Terminal", flySFO.com, 2007-01-30 (archived PDF http://www.flysfo.com/web/export/sites/default/download/about/news/pressres/fact-sheet/pdf/International_Terminal_Fact_Sheet.pdf); the fact sheet itself could not be opened (web.archive.org refused by the proxy)'),
    'dof': dict(title='FAA Digital Obstacle File, DAILY_DOF_CSV.ZIP (DOF.CSV dated 2026-09-18)', publisher='FAA Aeronautical Information Services',
                url='https://aeronav.faa.gov/Obst_Data/DAILY_DOF_CSV.ZIP', read='full', cache='refs/cache/lighting/DAILY_DOF_CSV.ZIP; extract refs/cache/buildings/itb/dof_itb_area.json',
                note='accuracy code 1A = +-20 ft horizontal / +-3 ft vertical (DOF_README); horizontal datum WGS 84; heights AGL and AMSL in ft'),
    'naip': dict(title='USDA NAIP 2024 (flown 2024-05-20), world raster refs/cache/naip/naip_2024_world_0.5m (docs/research/imagery.md)', publisher='USDA FPAC-BC GEO',
                 url='https://apps.geo.fpac.usda.gov/geo-imagery/rest/services/naip/conus_naip/ImageServer', read='full', licence='US public domain (credit requested)',
                 note='measured by tools/buildings/itb_naip_measure.py -> itb_naip_measurements.json; relief displacement calibrated on DOF poles'),
    'sfom_data': dict(title='SFO Museum architecture data (footprints) as data/sfo_airport.json / data/sfo_buildings.json', publisher='SFO Museum', licence='CDLA-Permissive-1.0',
                      url='https://github.com/sfomuseum-data/sfomuseum-data-architecture', read='full'),
    'photo_dimi': dict(title='Wikimedia Commons File:San_Francisco_International.jpg (DimiCalifornia, 2005-07)', licence='Public domain',
                       url='https://commons.wikimedia.org/wiki/File:San_Francisco_International.jpg', read='full', cache='refs/cache/buildings/itb/photos/1975704.jpg',
                       note='measured by tools/buildings/itb_photo_skyline.py -> itb_photo_skyline.json (qualitative + pair means)'),
    'osm': dict(title='OpenStreetMap (Overpass extract 2026-09-24, refs/cache/osm/overpass_ksfo_latest.json)', licence='ODbL-1.0', url='https://www.openstreetmap.org/',
                read='full', note='cross-reference only (contributor values without cited sources); never used as a source value'),
}

# ------------------------------------------------------------------------------------------------------- items
I = []


def item(id_, group, name, value, unit, tag, src, conf, method=None, note=None, alt=None, status='verified', **kw):
    d = dict(id=id_, group=group, name=name, value=value, unit=unit, tag=tag, sources=src, confidence=conf, status=status)
    if unit == 'ft' and isinstance(value, (int, float)): d['value_m'] = round(value * FT, 2)
    if method: d['method'] = method
    if note: d['note'] = note
    if alt: d['conflicting_values'] = alt
    d.update(kw); I.append(d)


TP = M['true_planform']; EP = M['eave_profile']; SL = M['skylight_lines']; RF = M['roof_frame']; DOF = M['dof_objects']
k_itb = M['relief']['k_at_itb_roof']; km = M['relief']['model']
prof = {int(q['abs_u']): q for q in EP['profile']}
phf = PH['features']; pm = PH['pair_means_drop_m']

# --- identity / general ---------------------------------------------------------------------------------------
item('itb.name', 'general', 'Official name', 'Senator Dianne Feinstein International Terminal (renamed by Airport Commission resolution of 2024-01-16); departures main hall named after Mayor Ed Lee', None,
     'pub', ['airportworld25', 'wiki_sfo'], 'high')
item('itb.opened', 'general', 'Opened (ribbon cutting)', '2000-12-10', 'date', 'pub', ['airportworld25'], 'high',
     note='ground broken October 1995 (airportworld25; "late 1995" sfgate2000); SOM: design finish 1995, completion 2000')
item('itb.architect', 'general', 'Architect', 'Skidmore, Owings & Merrill (design partner Craig W. Hartman) in joint venture with Del Campo & Maru and Michael Willis & Associates', None,
     'pub', ['som', 'sfgate2000'], 'high')
item('itb.structure_engineer', 'general', 'Structural engineer', 'SOM ("SOM engineered the building ... base isolation")', None, 'pub', ['som'], 'high')
item('itb.contractor', 'general', 'General contractor', 'Tutor-Saliba / Perini / Buckley joint venture', None, 'pub', ['som', 'tutor_itb'], 'high')
item('itb.steel', 'general', 'Roof steel fabricator / erector', 'The Herrick Corporation (trusses assembled at Mare Island, shipped by barge in ~35 pieces)', None, 'pub', ['msc2000'], 'medium',
     note='from the article abstract / author line only (PDF not readable)')
item('itb.gross_area', 'general', 'Gross floor area, main terminal', 1800000, 'sq ft', 'pub', ['som', 'tutor_itb'], 'high',
     note='2.5 million sq ft including the two concourses (sfgate2000; webcor_roof)')
item('itb.site_area', 'general', 'Site area', 1000000, 'sq ft', 'pub', ['som'], 'medium')
item('itb.stories', 'general', 'Stories', 5, 'count', 'pub', ['som', 'sfgate2000'], 'high')
item('itb.levels', 'general', 'Level use', 'L1 services and baggage; L2 arrivals; L3 departures, ticketing, security; L4-L5 airline offices and lounges', None,
     'pub', ['sfgate2000', 'radp_nop'], 'high', note='RADP NOP: "levels two (arrivals) and three (departures) of the ITB"')
item('itb.height_som', 'general', 'Building height (as published by the architect)', 144, 'ft', 'pub', ['som', 'enclos'], 'medium', status='conflict',
     note='datum not stated (ground? lowest floor? MSL?). The FAA DOF roof tops are 131/132 ft AGL = 139/140 ft AMSL (ground ~8 ft AMSL); 144 ft matches neither exactly - do NOT use as roof height above ground',
     alt=[dict(value=131.5, unit='ft AGL', src='dof', note='mean of 06-035315 (131) and 06-035316 (132)'), dict(value=100, unit='ft', src='sfgate2000', note='"the soaring, 100-foot-high terminal roof" (height above the hall floor, rounded)')])
item('itb.isolators', 'general', 'Seismic base isolation', 267, 'friction pendulum isolators', 'pub', ['enclos'], 'high',
     note='"the largest building in the world constructed on base isolators" (airportworld25)')
item('itb.gates_2000', 'general', 'Gates at opening', 26, 'count', 'pub', ['seaonc'], 'low', status='unverified', note='SEAONC text via search extract only')
item('itb.cladding', 'facade', 'Metal and glass cladding, total', 382000, 'sq ft', 'pub', ['tutor_itb'], 'high')

# --- hall roof: published structure ---------------------------------------------------------------------------
item('roof.form', 'roof', 'Roof structure', 'five sets of steel balanced double-cantilever trusses with a central trussed span, linked into one continuous wing-like form; double-cantilevered trusses linked by bowstring trusses; three-chord "football" trusses', None,
     'pub', ['seaonc', 'msc2000', 'som', 'smith_emery'], 'high')
item('roof.length_pub', 'roof', 'Roof overall length (published)', 860, 'ft', 'pub', ['msc2000', 'seaonc', 'smith_emery'], 'medium', status='conflict',
     note='NAIP measures %.1f m (%.0f ft) tip to tip (roof.length_obs) - 9 m / 31 ft shorter. Unresolved: possibly measured along the curved top chord or to steel beyond the visible fascia. Concept sketch: 866 ft' % (TP['length_m'], TP['length_m'] / FT),
     alt=[dict(value=866, unit='ft', src='som_sketch', note='concept "Main roof: 866\' x 260\'"'), dict(value=round(TP['length_m'], 1), unit='m', src='naip')])
item('roof.span_centre', 'roof', 'Centre span (between the inner column lines)', 380, 'ft', 'pub', ['seaonc', 'msc2000', 'sfgate2000'], 'high')
item('roof.cantilever_end', 'roof', 'End cantilever (outer column line to roof tip)', 160, 'ft', 'pub', ['seaonc', 'msc2000'], 'high')
item('roof.truss_len', 'roof', 'Double-cantilever truss length', 'up to 320', 'ft', 'pub', ['msc2000'], 'medium')
item('roof.centre_section', 'roof', 'Central (suspended) section length', 180, 'ft', 'pub', ['msc2000'], 'medium', note='jacked up ~60 ft into place in two phases')
item('roof.truss_depth', 'roof', 'Truss depth, maximum (over the supports)', 29, 'ft', 'pub', ['seaonc', 'msc2000'], 'high')
item('roof.columns', 'roof', 'Roof columns', 20, 'count', 'pub', ['seaonc'], 'medium',
     note='"supported on 20 cantilevered columns rising from the third floor departures level" (search extract of SEAONC)')
item('roof.col_grid', 'roof', 'Column grid (concept)', "40 ft E/W grid by 80 ft N/S column bays", None, 'pub', ['som_sketch'], 'medium',
     note='truss-line spacing confirmed by NAIP (roof.truss_spacing_obs = %.2f m)' % SL['spacing_true_m'])
item('roof.height_above_floor', 'roof', 'Roof height above the ticketing hall floor', '60 to 90', 'ft', 'pub', ['smith_emery', 'msc2000'], 'medium',
     note='"soaring 60 to 90\' above the floor of a cavernous ticketing hall" - which surface (top / underside) is not stated')
item('hall.size_snippet', 'hall', 'Glass-enclosed great hall, length x width x height', '705 x 210 x up to 83', 'ft', 'pub', ['seaonc'], 'low', status='unverified',
     note='search engines attribute this sentence to the SEAONC page, which could not be opened. 83 ft is an INTERIOR hall height, not the roof height above ground (the current model js/live/terminals.js uses 83 ft as roof height above ground)')
item('hall.lobby_len', 'hall', 'Ticket lobby length', 700, 'ft', 'pub', ['sfgate2000'], 'high')
item('hall.bamboo', 'hall', 'Bamboo grove height', 55, 'ft', 'pub', ['sfgate2000'], 'high', note='"stretches 55 feet high between Levels 2 and 3" (interior)')

# --- hall roof: inferred rhythm ---------------------------------------------------------------------------------
item('roof.rhythm_inf', 'roof', 'Structural rhythm along the axis (tip -> tip)',
     '20 ft roof overhang | 140 ft outer truss cantilever | outer column | 80 ft | inner column | 100 ft inner cantilever | 180 ft centre section | 100 | col | 80 | col | 140 | 20', 'ft',
     'inf', ['seaonc', 'msc2000', 'som_sketch'], 'medium',
     method='the only split that satisfies all published numbers at once: 160 (end cantilever) + 80 (column bay) + 380 (centre span) + 80 + 160 = 860; truss 140 + 80 + 100 = 320; centre section 380 - 2 x 100 = 180',
     note='the 20 ft overhang beyond the truss ends is the inferred closure; if the as-built roof is 829 ft (NAIP) the cantilevers or the overhang are ~15 ft shorter each side')
item('roof.col_positions_inf', 'roof', 'Column lines from the roof centre along the axis', {'inner': [-190, 190], 'outer': [-270, 270]}, 'ft', 'inf', ['seaonc', 'msc2000', 'som_sketch'], 'medium',
     note='= +-57.9 m and +-82.3 m. 20 columns = 5 truss lines x 2 double-cantilever trusses x 2 columns (inf; the SOM perspective section shows a column under each truss line)')

# --- hall roof: NAIP observations -------------------------------------------------------------------------------
item('roof.axis_obs', 'roof', 'Roof axis heading (true north, towards Boarding Area A)', RF['axis_heading_deg'], 'deg', 'obs', ['naip'], 'high',
     method='glazed tip edges and the lens row are perpendicular to the axis; the straight west facade base line confirms it (sd %.2f m over %d rows)' % (EP['base_line_v_sd'], EP['n_points']),
     note='%.1f deg clockwise from the principal axis of the SFO Museum hall part used by the current model' % RF['rotation_vs_sfom_axis_deg'])
item('roof.centre_obs', 'roof', 'Roof centre (relief-corrected, world x/z)', TP['centre_xz'], 'm', 'obs', ['naip', 'dof'], 'medium',
     method='NAIP roof features moved back by k*h (k = %.3f at the ITB from DOF poles, h from the eave profile)' % k_itb['k'], note='+-1.5 m')
item('roof.corners_obs', 'roof', 'Main roof outline corners (relief-corrected, world x/z)', TP['corners'], 'm', 'obs', ['naip', 'dof'], 'medium',
     note='rectangle at the eaves; +-1.5 m. Check: DOF roof tops 06-035315/06-035316 fall %.1f / %.1f m inside the corrected west eave line' % (
         TP['dof_roof_points_uv']['06-035315'][1] - TP['west_eave_v_true'], TP['dof_roof_points_uv']['06-035316'][1] - TP['west_eave_v_true']))
item('roof.length_obs', 'roof', 'Roof length tip to tip (fascia to fascia)', TP['length_m'], 'm', 'obs', ['naip'], 'medium', status='conflict',
     method='NAIP 0.25 m resampled profile along the axis; imaged %.2f m, central-projection magnification of an elevated plane removed (H-h = %d m from the k(x) slope)' % (M['roof_length']['fascia_to_fascia_img_m'], km['H_minus_h_est_m']),
     note='+-1.5 m; conflicts with the published 860 ft (262.1 m)', alt=[dict(value=860, unit='ft', src='msc2000')])
item('roof.width_obs', 'roof', 'Roof width eave to eave', TP['width_m'], 'm', 'obs', ['naip'], 'medium',
     note='+-1.0 m (%.0f ft); concept sketch 260 ft; published enclosed hall width 210 ft (unverified)' % (TP['width_m'] / FT),
     alt=[dict(value=260, unit='ft', src='som_sketch', note='concept')])
item('roof.truss_lines_obs', 'roof', 'Truss / skylight lines', 5, 'count', 'obs', ['naip', 'som_sketch', 'seaonc'], 'high',
     note='5 straight glazed lines along the roof ("roof plane is opened with glass along major truss lines", SOM sketch)')
item('roof.truss_spacing_obs', 'roof', 'Truss-line spacing', SL['spacing_true_m'], 'm', 'obs', ['naip'], 'high',
     method='comb fit of 5 equally spaced lines (north half, %d rows) and the lens-skylight centres; both %.2f m imaged' % (SL['rows'], SL['spacing_img_m_lens_centres']),
     note='= %.1f ft (published grid 40 ft); outer lines %.1f m apart; outer line to eave ~8.4 m each side' % (SL['spacing_true_m'] / FT, SL['outer_line_to_line_true_m']))
lz = [q for q in M['lenses'] if q['u1'] - q['u0'] > 40]
item('roof.lenses_obs', 'roof', 'Centre-section skylights', dict(count=5, length_m=round(sum(q['u1'] - q['u0'] for q in lz) / len(lz), 1), max_width_m=round(sum(q['w_max'] for q in lz) / len(lz), 1),
     centred_on='the 5 truss lines'), 'm', 'obs', ['naip'], 'medium',
     note='lens-shaped (pointed ends) glazed skylights, one per truss line, occupying the central section (published 180 ft = 54.9 m); interior photos show them as glazed basket trusses; +-1 m')
item('roof.glazed_tips_obs', 'roof', 'Glazed canopy bands at the two roof tips (depth along the axis)', dict(north=M['glazed_tip_bands']['N_depth_m'], south=M['glazed_tip_bands']['S_depth_m']), 'm', 'obs', ['naip'], 'medium',
     note='bluish glazed grid across the full roof width at both cantilever tips; N/S difference (3 m) not explained; +-1 m')

# --- hall roof: heights -------------------------------------------------------------------------------------------
for o in ('06-035315', '06-035316'):
    d = DOF[o]
    item('roof.dof_%s' % o, 'roof', 'FAA DOF roof top %s' % o, d['agl_ft'], 'ft', 'pub', ['dof'], 'high',
         note='AGL %d ft / AMSL %d ft, accuracy 1A, verified, JDATE %s, %s %s -> world (%.1f, %.1f); lies at the west eave over the column pairs (u = %s m)' % (
             d['agl_ft'], d['amsl_ft'], d['jdate'], d['dmslat'], d['dmslon'], d['x'], d['z'], TP['dof_roof_points_uv'][o][0]))
item('roof.ground_amsl', 'site', 'Ground elevation at the ITB (from DOF AMSL - AGL)', 8, 'ft', 'inf', ['dof'], 'medium',
     note='139-131 = 140-132 = 8 ft AMSL (DOF rounding +-1 ft); SFO field elevation 13 ft')
H_top = round((DOF['06-035315']['agl_ft'] + DOF['06-035316']['agl_ft']) / 2 * FT, 2)
item('roof.profile', 'roof', 'Wing-roof height profile at the west eave (AGL), by distance |u| from the roof centre', {
    'hump (|u| 60-75 m, over the column pairs)': dict(h=H_top, tag='pub', src='dof'),
    'notch (|u| 25-31 m, where the wings meet the centre section)': dict(h=round(H_top - 0.5 * (prof[27]['drop_below_peak_m'] + pm['notch']), 1), tag='obs', src=['naip', 'photo_dimi'],
                                                                           naip_drop=prof[27]['drop_below_peak_m'], photo_drop=pm['notch']),
    'centre crown (u ~ 0, glazed centre section top)': dict(h=round(H_top - phf['crown']['drop_below_hump_mean_m'], 1), tag='obs', src=['photo_dimi'], note='photo only (NAIP cannot see it through the lens glass); +-2 m'),
    '|u| = 100 m': dict(h=prof[100]['h_agl_m'], tag='obs', src='naip'),
    'tip (|u| ~ 126 m)': dict(h=round(H_top - 0.5 * (prof[119]['drop_below_peak_m'] + pm['tip']), 1), tag='obs', src=['naip', 'photo_dimi'],
                              naip_drop_at_119=prof[119]['drop_below_peak_m'], photo_drop=pm['tip'])},
     'm AGL', 'obs', ['naip', 'photo_dimi', 'dof'], 'medium',
     method='NAIP: the imaged west eave wanders east by 0.955*k*h relative to the straight facade-base line (k = %.3f); even-polynomial fit, RMS %.2f m in plan; anchored at the peak to the DOF tops. Photo: public-domain frontal photograph, sky/roof silhouette, north/south pair means (perspective not modelled)' % (k_itb['k'], EP['fit_rms_m']),
     note='the humps are highest at |u| %.0f m, between the inferred inner (57.9 m) and outer (82.3 m) column lines; +-1.5 m below the anchor. The DOF value may belong to the skylight ridges rather than the eave (then all eave values drop by up to ~1-2 m) [unverified]' % EP['peak_abs_u_m'],
     full_curve=[dict(abs_u=q['abs_u'], h_agl_m=q['h_agl_m']) for q in EP['profile'][::4]])
item('level3.floor', 'hall', 'Departures level (level 3) floor above ground', 11.5, 'm', 'inf', ['dof', 'smith_emery', 'sfgate2000'], 'low', status='unverified',
     method='DOF roof top (40.1 m) minus "90 ft" (smith_emery, upper value) = 12.7 m, minus "100 ft" (sfgate2000) = 9.6 m; midpoint', note='+-1.5 m; no drawing or survey found - see open questions')

# --- facades --------------------------------------------------------------------------------------------------------
item('facade.west', 'facade', 'West (landside, front) wall', 'full-height glass wall, glass with three layers of ceramic frit ("like a scrim"); concept sketch: bands of translucent patterned frit, clear glass and translucent glass / metal brise-soleil', None,
     'pub', ['sfgate2000', 'som_sketch'], 'high', note='photos: lower band clear glazing at the curb with entrance vestibules and a canopy; upper wall light fritted panels; pairs of white columns at the column lines; roof trusses exposed above the wall')
item('facade.end_walls', 'facade', 'North and south end walls', 'custom unitized curtain walls spanning over 60 ft (vertical exterior end walls under the roof)', None, 'pub', ['enclos'], 'high')
item('facade.back_wall', 'facade', 'Hall back (east) wall, interior', 'cherry-wood clad high wall', None, 'pub', ['sfgate2000'], 'high')

# --- roof upgrade 2024-26 --------------------------------------------------------------------------------------------
item('roof.upgrade_2024', 'roof', 'Roof and envelope upgrade 2024-2026', 'new roof membrane and waterproofing, ~1,400 kW rooftop PV, expansion joints, window-washing (facade access) system, curtain-wall mullion caps, exposed-steel corrosion repair; west facade scaffolded in four phases; ceremony 2024-06-27, completion early/mid 2026', None,
     'pub', ['webcor_roof', 'webcor_ceremony', 'ftf_roof', 'ai_roof', 'airportworld25'], 'high',
     note='NAIP 2024 (2024-05-20) predates the works: the 2026 roof carries PV arrays whose layout is not documented in any open source found (open question)')

# --- relief / sun metadata ----------------------------------------------------------------------------------------------
item('naip.k_model', 'method', 'NAIP 2024 relief displacement factor near the ITB', km, None, 'obs', ['naip', 'dof'], 'high',
     note='5 DOF poles 153-157 ft AGL; scatter %.4f; k at ITB roof %.3f; predicts the tower cab lean (38-40 m) for 69-73 m height vs DOF top 74.7 m (245 ft incl. appurtenances)' % (km['scatter_sigma'], k_itb['k']))
item('naip.sun', 'method', 'Sun at the NAIP 2024 exposure near the ITB', M['sun']['picks'][0], None, 'obs', ['naip', 'dof'], 'medium',
     note='shadow of DOF pole 06-034826 (108 ft): azimuth ~187 deg, elevation ~72.4 deg (the local-noon maximum for 2024-05-20) - for later shadow checks')

# --- Boarding Area A ------------------------------------------------------------------------------------------------------
item('ba_a.architect', 'boarding_area_a', 'Architect / builder', 'Gerson/Overstreet Architects; built by Hensel Phelps Construction', None, 'pub', ['wiki_sfo'], 'medium', note='secondary (Wikipedia citing the 2007 flySFO fact sheet)')
item('ba_a.gates', 'boarding_area_a', 'Gates', 'A1-A15 (15)', None, 'pub', ['wiki_sfo', 'ags_baa'], 'high',
     note='AGS: 23 passenger boarding bridges at A1-A15 reconfigured (completed 2020); A6 retrofitted for a three-bridge A380 operation (AGS) - Wikipedia names A11 for three jetways (conflict, gate-level detail)')
item('ba_a.footprint', 'boarding_area_a', 'Footprint', 'SFO Museum polygon (data/sfo_airport.json "Boarding Area A"): 339 m along the pier axis incl. the connector; body width 38.7-38.8 m', 'm', 'obs', ['sfom_data'], 'medium',
     note='NAIP imaged roof (fascia to fascia) 36.5 m at three stations (by eye, +-1 m); the SFO Museum edge includes the oblique facade band')
item('ba_a.height_roof', 'boarding_area_a', 'Main pier roof height above apron', 17.0, 'm', 'obs', ['naip', 'sfom_data'], 'low',
     method='(a) NAIP west-side dark band (oblique WNW facade + shadow) 8.5-9 m wide = (0.873 k + 0.122) h with k = 0.42 -> 17.4-18.4 m (minus any roof overhang); (b) NAIP roof centre vs SFO Museum footprint centre 5.85 m = 0.873 k h -> 15.9 m',
     note='+-2.5 m. Consistent with a three-level pier (apron + two passenger levels) [inf]. OSM says 25 m (unsourced)', alt=[dict(value=25, unit='m', src='osm', note='unsourced')])
item('ba_a.pods', 'boarding_area_a', 'Raised roof pods', dict(count=3, plan='D-shaped, curved west edge', lengths_m=[70, 55, 55]), None, 'obs', ['naip'], 'low',
     note='by eye on NAIP (+-3 m); the first pod (nearest the ITB) top is FAA DOF 06-035352 = 85 ft AGL (25.9 m, 94 ft AMSL); its oblique rim band (2.5-3 m) gives ~7.5 m above the main roof, consistent with 17 + 7.5 = 24.5-26 m')
item('ba_a.dof_pod', 'boarding_area_a', 'FAA DOF 06-035352', DOF['06-035352']['agl_ft'], 'ft', 'pub', ['dof'], 'high',
     note='BLDG 85 ft AGL / 94 ft AMSL, 1A, %s %s -> world (%.1f, %.1f): west side of Boarding Area A pod 1 (pier frame u ~ -125 m)' % (DOF['06-035352']['dmslat'], DOF['06-035352']['dmslon'], DOF['06-035352']['x'], DOF['06-035352']['z']))

# --- Boarding Area G ------------------------------------------------------------------------------------------------------
item('ba_g.architect', 'boarding_area_g', 'Architect / builder', 'Robin Chiang & Company (Tutor Perini page); Wikipedia: Hellmuth, Obata + Kassabaum with Robin Chiang & Company and Robert B. Wong Architects; built by Tutor Perini; completed 1999; contract $95 M', None,
     'pub', ['tutor_bag', 'wiki_sfo'], 'high')
item('ba_g.area', 'boarding_area_g', 'Gross area', 380000, 'sq ft', 'pub', ['tutor_bag'], 'high')
item('ba_g.stories', 'boarding_area_g', 'Stories / levels', 'three-story: apron level (airline operations, storage, MEP); level 2 international arrivals, sterile corridor, clubs, in-transit lounge with gate-room access; level 3 departures concourse with retail', None,
     'pub', ['tutor_bag'], 'high')
item('ba_g.gaterooms', 'boarding_area_g', 'Gate rooms', 'six double-gated, two-level common-use gate rooms for twelve 747-400s', None, 'pub', ['tutor_bag'], 'high')
item('ba_g.gates', 'boarding_area_g', 'Gates', 'G1-G14 (14)', None, 'pub', ['wiki_sfo'], 'medium')
item('ba_g.facade', 'boarding_area_g', 'Exterior', 'metallic-finish composite aluminium panels and a tinted energy-efficient glazed curtain wall', None, 'pub', ['tutor_bag'], 'high')
item('ba_g.footprint', 'boarding_area_g', 'Footprint', 'SFO Museum polygon (data/sfo_airport.json "Boarding Area G"): body width 38.3-38.4 m, 47 m at the middle pod', 'm', 'obs', ['sfom_data'], 'medium',
     note='NAIP imaged roof width ~33.5 m by eye (edges ambiguous, low); the SFO Museum G outline is offset ~3-6 m NNE of the relief-corrected NAIP roof (imagery.md s.6 lists +4 m) - unresolved')
item('ba_g.height_roof', 'boarding_area_g', 'Main pier roof height above apron', 17.0, 'm', 'obs', ['naip'], 'low',
     method='NAIP: NNE shadow band + SSW oblique facade band = 4.5-5.5 m = 0.297 h (sun elevation 72.4 deg, azimuth 187 deg; k = 0.36)', note='+-3 m; three-story (pub) supports ~17-20 m [inf]')
item('ba_g.pods', 'boarding_area_g', 'Raised roof pods', dict(count=3, plan='lens / elliptical', lengths_m=[60, 55, 62]), None, 'obs', ['naip'], 'low',
     note='by eye on NAIP (+-3 m); heights not measured - no DOF entry on Boarding Area G')

# --- planned (RADP) -------------------------------------------------------------------------------------------------------
item('radp.itb', 'planned', 'RADP projects touching the ITB (2019 NOP)', 'Main Hall western expansion of levels 2-3 (~140,000 sq ft, 70,000 per level); Boarding Areas A (+10,800 sq ft) and G (+12,400 sq ft) "bump-outs"; ITB curbside expansion; Boarding Area H connected through the ITB', None,
     'pub', ['radp_nop'], 'high', status='unverified', note='planning-stage only; whether any was built by 2026 is not verified')

PHOTO_USE = {  # by eye, this session (refs/cache/buildings/itb/photos/<pageid>.jpg)
    '1975704': 'west (landside) elevation from the access road, near-frontal, long lens: roof silhouette measured (itb_photo_skyline.py)',
    '2690474': 'west elevation panorama from the garage/AirTrain level: wing humps, notches, glazed centre crown, column pairs, fritted wall',
    '51069944': 'west elevation from an elevated viewpoint (Highsmith, Library of Congress): departures and arrivals decks, column pairs, roof tips beyond the end walls',
    '51069959': 'wider west view incl. a 153-157 ft DOF high-mast pole and the Garage G side (Highsmith)',
    '61673925': 'departures curb (west facade) oblique: roof eave overhang, exposed trusses, column pair, canopy',
    '10615771': 'night, departures curb: eave overhang, trusses, notch between north wing and centre section',
    '53232672': 'approach road view of the whole ITB with garages A/G',
    '172433036': 'interior, main hall looking north: column pairs, three-chord trusses, lens "basket" trusses of the centre section, glazed truss lines',
    '54020895': 'interior panorama: check-in islands 8/9, cherry-wood back wall, trusses',
    '29357785': 'Boarding Area G apron side (2008, pre-2011 gate numbers 92/94): pier facade panels, bridges',
    '31878092': 'Boarding Area A interior (A6-A8), moving walkway',
    '31878106': 'Boarding Area interior (gate room glazing, tapered columns)',
    '54020936': 'interior, departures hall at night',
}
photos = []
for f, m in json.load(open(os.path.join(os.path.dirname(HERE), '..', 'refs', 'cache', 'buildings', 'itb', 'photos', 'manifest.json'))).items() if os.path.exists(
        os.path.join(os.path.dirname(HERE), '..', 'refs', 'cache', 'buildings', 'itb', 'photos', 'manifest.json')) else []:
    ok = os.path.exists(os.path.join(os.path.dirname(HERE), '..', 'refs', 'cache', 'buildings', 'itb', f)) and open(os.path.join(os.path.dirname(HERE), '..', 'refs', 'cache', 'buildings', 'itb', f), 'rb').read(3) == b'\xff\xd8\xff'
    import re
    pid = os.path.basename(f).split('.')[0]
    photos.append(dict(file='refs/cache/buildings/itb/' + f if ok else None, page=m['page'], title=m['title'], licence=m['licence'], use=PHOTO_USE.get(pid, 'not reviewed'),
                       author=re.sub(r'<[^>]+>', '', m.get('artist') or '').strip()[:80], date=re.sub(r'<[^>]+>', '', m.get('date') or '').strip()[:40], downloaded=ok))

# status: items whose sources were all read only as search-engine extracts (or only through a secondary source) are
# downgraded - the numbers agree across independent extracts, but the documents themselves were not read
for d in I:
    kinds = {S[x].get('read') for x in d['sources']}
    if d['status'] == 'verified' and kinds <= {'snippet', 'secondary'}:
        d['status'] = 'snippet-only' if 'snippet' in kinds else 'secondary-only'
photos.sort(key=lambda q: q['use'] == 'not reviewed')
spec = dict(
    schema='sfo3d building spec v1', building='International Terminal Building (ITB) - Senator Dianne Feinstein International Terminal, with Boarding Areas A and G',
    generated=datetime.date.today().isoformat(), generator='tools/buildings/build_spec_itb.py',
    frame=dict(id='ltp-nad83-2011', axes='world x east, z south, metres from the ARP; heights AGL (ground ~8 ft AMSL at the ITB) unless stated',
               roof_frame=dict(centre=TP['centre_xz'], axis=TP['axis_xz'], heading_deg=RF['axis_heading_deg'], u='along the axis, + towards Boarding Area A (SSE)', v='across, + towards ENE')),
    status=dict(verified='value read first-hand in at least one listed source (or measured by us)', conflict='sources disagree - see conflicting_values',
                unverified='no original could be read / no source exists - do not build on it without the owner',
                **{'snippet-only': 'all sources read only through search-engine extracts (site blocks automated access); the extracts of independent sources agree',
                   'secondary-only': 'known only through a secondary source (Wikipedia) citing an original we could not open'}),
    tags=dict(pub='published by an original source (architect, engineer, contractor, FAA, SF Planning, contemporary press) - see sources[].read',
              obs='measured by us on public imagery/data (NAIP 2024, FAA DOF geometry, a public-domain photo, SFO Museum footprints) with the stated method',
              inf='derived by stated arithmetic from pub/obs values'),
    sources=S, items=I, photos=photos,
    current_model_deviations=[
        'js/live/terminals.js greatHall(): roof top at 83 ft (25.3 m) above ground; the DOF roof tops are 131/132 ft AGL (40 m) - 83 ft is the (unverified) interior hall height',
        'greatHall(): roof length 380 + 2x160 + 2x12 ft ~ 237 m and width 210 ft + 18 m ~ 82 m; NAIP: %.1f m x %.1f m (published 860 ft long)' % (TP['length_m'], TP['width_m']),
        'greatHall(): placed on the SFO Museum hall part axis/centre; the roof axis is rotated %.1f deg (heading %.2f) and its centre is %s' % (RF['rotation_vs_sfom_axis_deg'], RF['axis_heading_deg'], TP['centre_xz']),
        'greatHall(): 20 columns as 2 x 10 along the long edges; published/inferred: 5 truss lines x 4 columns at +-190 / +-270 ft along the axis',
        'greatHall(): roof top profile highest over the column lines and lower at centre/tips - matches qualitatively, but the centre crown (glazed lens section) rises again to ~the hump height and the notches between wings and centre are ~5 m lower',
        'data/sfo_buildings.json: Boarding Areas A/G at 14.6 m; NAIP relief/shadow gives ~17 m (+-2.5/3 m) plus pods to ~26 m (A pod 1: DOF 85 ft)',
    ],
    unverified=[
        'flySFO "Fact Sheet - International Terminal" (2007) could not be retrieved (web.archive.org refused); its dimensions are only known through Wikipedia',
        'AISC Modern Steel Construction Feb 2000 article and the SEAONC Legacy page: only search-engine extracts could be read (bot challenges)',
        'the "705 x 210 x 83 ft" great-hall figures: attribution to SEAONC not confirmed first-hand',
        'datum of the architect\'s "144 ft" building height',
        'departures (level 3) floor elevation above ground (inferred 11.5 +-1.5 m)',
        'roof tip and centre-crown heights (NAIP + one photo, +-1.5-2 m); whether the DOF tops are the eave or skylight ridges',
        'as-built roof length: NAIP 252.7 m vs published 860 ft (262.1 m)',
        'pier roof heights (NAIP relief/shadow only), heights of pods other than A pod 1, G pod heights',
        'post-2024 roof: PV array layout, new membrane colour',
        'gate with the three-bridge A380 operation: A6 (AGS) vs A11 (Wikipedia)',
    ],
    open_questions=[
        'Owner: can we obtain SFO / SF Planning / SOM drawings (sections, elevations) of the ITB? e.g. SFO Bureau of Design and Construction record drawings, or the 1992 SFO Master Plan FEIR (the ITB EIR) - they would fix the level heights and the roof profile',
        'Which length to model: NAIP 252.7 m (as imaged) or the published 860 ft? Proposed: NAIP for the planform, published rhythm scaled to it, flagged on the drawing',
        'Roof appearance for 2026: new membrane + 1.4 MW PV - needs post-2024 imagery (NAIP 2026 when released, or owner photos); until then model the 2024 roof',
        'Pier heights: accept the NAIP-derived ~17 m (with pods ~26 m) or wait for an elevation source?',
        'Boarding Area G outline: SFO Museum polygon offset vs NAIP - retrace from NAIP ground-level edges?',
    ])
json.dump(spec, open(os.path.join(HERE, 'spec_itb.json'), 'w'), indent=1)
print('items', len(I), 'sources', len(S), 'photos', len(photos))
