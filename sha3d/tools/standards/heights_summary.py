"""B3: combine the building-height evidence (OSM tags, AIP obstacles, GLO-30 DSM, Umbra layover, photo ratios) into
data/meas/b3_building_heights.json. Each entry: proposed height above ground (m), +-, src (inf), method, evidence.

usage: python3 -I sha3d/tools/standards/heights_summary.py sha3d
"""
import json, os, sys
root = sys.argv[1]; M = os.path.join(root, 'data', 'meas')
dem = {b['id']: b for b in json.load(open(os.path.join(M, 'b3_dem_building_samples.json')))['buildings']}
lay = json.load(open(os.path.join(M, 'b3_umbra_layover.json')))['results']
L = {(r['id'], r['wall']): r for r in lay}
def d(bid):
    b = dem.get(bid) or {}; e = b.get('excess_m') or {}
    i = b.get('inside') or {}
    return dict(excess_med=None if not e else round(e['med'], 1), excess_p90=None if not e else round(e['p90'], 1),
                excess_max=None if not e else round(e['max'], 1), n_px=i.get('n'), edm=i.get('edm'), flm=i.get('flm'))
def l(bid, w, verdict):
    r = L[(bid, w)]
    return dict(wall=w, wall_mid_xz=r['wall_mid_xz'], wall_len_m=r['wall_len_m'], layover_m=round(r['foot_m'] - r['onset_m'], 1) if r['onset_m'] is not None else None,
                height_m=r['height_m'], unc_m=r['height_unc_m'], contrast=r['contrast'], verdict=verdict)
B = [
 dict(id='osm:way/327613444', name='China Eastern hangar', proposed_m=33.5, unc_m=3.0, rule_m=32,
      method='Umbra layover: clean box profile (sharp onset, plateau, drop at the OSM wall foot)', dsm=d('osm:way/327613444'),
      layover=[l('osm:way/327613444', 0, 'accepted (best case)')],
      note='DSM unusable: airport-edited plane (EDM 5/6). AIP (mirror): hangar for two B747-400 + two narrow-bodies (B747-400 tail 19.4 m: consistent).'),
 dict(id='osm:way/327473856', name='big hangar (east)', proposed_m=28.5, unc_m=5.0, rule_m=32,
      method='Umbra layover, moderate (noisy plateau)', dsm=d('osm:way/327473856'), layover=[l('osm:way/327473856', 0, 'accepted, moderate')],
      note='DSM unusable (EDM 6/5).'),
 dict(id='osm:way/327473860', name='hangar (east, small)', proposed_m=22, unc_m=6, rule_m=22, method='rule kept (A1)', dsm=d('osm:way/327473860'),
      layover=[l('osm:way/327473860', 0, 'rejected: the big hangar and apron clutter overlap the profile')]),
 dict(id='osm:way/328013621', name='hangar north-east, near the 18L end (way 328013621)', proposed_m=16, unc_m=4, rule_m=22,
      method='Umbra layover, moderate; DSM small excess (+3 to +4 m, 2 px only)', dsm=d('osm:way/328013621'), layover=[l('osm:way/328013621', 0, 'accepted, moderate')]),
 dict(id='osm:way/1257868692', name='building south of the China Eastern hangar', proposed_m=19, unc_m=4, rule_m=12,
      method='Umbra layover, moderate', dsm=d('osm:way/1257868692'), layover=[l('osm:way/1257868692', 0, 'accepted, moderate')]),
 dict(id='osm:way/93184730', name='T1 (central hall roof / airside concourse)', proposed_m=26, unc_m=4, rule_m=25,
      method='photo ratio to the east tower in Commons 202309_Terminal_1 (CC BY-SA 4.0): hall roof 65 px vs tower 125 px at 570 / 500 m '
             '(OSM distances; tower 44.5 m) -> 26 m; airside concourse roof 27 px at 465 m -> 9 m',
      concourse_m=9, concourse_unc_m=2, dsm=d('osm:way/93184730'),
      layover=[l('osm:way/93184730', 1, 'rejected: no clean plateau (canopies, roads, mixed heights)')],
      note='DSM from TanDEM-X 2010-2015 shows the pre-renovation T1 (renovated 2014-2018), so its 7-16 m excess is outdated.'),
 dict(id='osm:relation/21913345', name='T2 main hall', proposed_m=22, unc_m=4, rule_m=25,
      method='Umbra layover on the west wall at x -1140, z 307-490 (21.4 +- 3.3 m) agrees with the DSM p90 excess (22.2 m)',
      piers_m=None, dsm=d('osm:relation/21913345'),
      layover=[l('osm:relation/21913345', 2, 'accepted (main hall)'), l('osm:relation/21913345', 0, 'south block, 29 m: accepted with low confidence (foot 15 m off OSM)'),
               l('osm:relation/21913345', 5, 'west end (transport centre side), 24 m: low confidence'),
               l('osm:relation/21913345', 9, 'rejected: clutter')],
      note='126 of 168 DSM pixels are infill (FLM: 91 SRTM30, 35 ASTER), so the DSM is low confidence here. A T2 lounge is named "21米贵宾厅" '
           '(Commons file titles): a 21 m level is plausible but not verified. Piers: no measurement (rule).'),
 dict(id='osm:way/469610770', name='business aviation terminal (FBO)', proposed_m=12, unc_m=4, rule_m=12,
      method='rule kept; DSM +3.8 / +5.7 / +6.2 m (2 px); layover not clean (6 +- 5 m)', dsm=d('osm:way/469610770'),
      layover=[l('osm:way/469610770', 0, 'rejected: profile too short and peaked')]),
 dict(id='osm:node/3342630333', name='control tower (east)', proposed_m=44.5, unc_m=1.5, rule_m=44.5,
      method='AIP (mirror) obstacle elevation 47 m - ground 2.5 m (A1); the photo scale is consistent: 125 px at f = 1386 px gives 494 m '
             'for 44.5 m, the expected distance from RWY 18L/36R', layover=[], dsm=None,
      note='form from the 2023 photo: pale concrete shaft with a dark vertical slot, flared two-level head with small windows, cab with dark inclined glazing and a flat roof.'),
 dict(id='osm:way/1576039982', name='SW tower 1 (untyped)', proposed_m=35, unc_m=10, rule_m=35, method='rule kept: no measurement (Umbra clutter, A1)', layover=[], dsm=d('osm:way/1576039982')),
]
rej = [dict(id='osm:way/861029093', note='layover 83 m (65 m) is implausible for a 17 m wide block: neighbouring structures merge into the profile; rule kept'),
       dict(id='osm:relation/21913196', note='China Eastern office: no clean profile; DSM +3 / +6 / +8 m (11 px, mostly smoothed); rule 20 m kept'),
       dict(id='osm:way/1576050065', note='hotel by T2 (context): ramp-shaped layover to 78 m (~64 m) suggests a tall block; not used (context building, ramp not a box)')]
json.dump(dict(what='Airport building heights from open sources (B3), all src inf', method_notes=dict(
    osm='no height / building:levels tags on any airport building (A1)',
    aip='AIP (mirror) obstacles match only the tower among airport buildings (A1)',
    dsm='Copernicus GLO-30 DSM minus the median of a 30-90 m ring; 30 m pixels; TanDEM-X Dec 2010 - Jan 2015; hangars on airport-edited planes',
    sar='Umbra GEC 2024-06-02, incidence 38.08 deg, sensor azimuth 275.5 deg: h = layover / cot(38.08 deg) = layover / 1.2763 between the SAR wall foot and the layover onset',
    photo='height ratio to the 44.5 m east tower in a 2023 Commons photo, distances from OSM'),
    buildings=B, rejected=rej, licences='Copernicus WorldDEM-30 notice; Umbra CC BY 4.0; OSM ODbL; Commons photo CC BY-SA 4.0 (MNXANL)',
    attribution=('produced using Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH '
                 '2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved; Umbra Lab, Inc., '
                 'Umbra SAR Open Data, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), modified; '
                 '(c) OpenStreetMap contributors (ODbL 1.0); photo ratio: Wikimedia Commons photo by MNXANL, CC BY-SA 4.0 '
                 '(docs/phase1/photos_credits.md); AIP (mirror) obstacle match: short cited fact')),
    open(os.path.join(M, 'b3_building_heights.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for b in B: print(f"{b['name'][:42]:42s} {b['proposed_m']:5.1f} +- {b['unc_m']:4.1f}  (rule {b['rule_m']})")
