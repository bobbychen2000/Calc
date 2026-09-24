#!/usr/bin/env python3
"""Checks and test vectors behind docs/research/environment_spec.md (lighting, day/night and weather spec).

Research tool, stdlib only (plus `node` for tools/env/ephemeris.mjs). It writes nothing outside tools/env/fixtures/.

  python3 tools/env/env_spec_checks.py            # print the three checks
  python3 tools/env/env_spec_checks.py --json     # also write tools/env/fixtures/env_presets.json (test vectors)

1. Light visibility (spec s.4.10). Allard's law E = I exp(-sigma d) / d^2 [AC 70/7460-1N App. B cites it implicitly;
   formula: Rasmussen et al. 1999 eq. 22-24, weather.md s.3.1] fitted to the FAA's own calibration points:
   AC 70/7460-1N (2026-08-11) Table B-1 "Distance and Intensity" plus the B.3 sentence "When the visibility at night
   deteriorates to 1SM, the pilot's ability to see the lights of a structure using 2,000 candela is reduced to 1.2 SM"
   (refs/cache/lighting/2026-07-13_AC_70_7460-1N_..._FINAL_CLEAN.txt, lines ~10897-11060).
   sigma is taken three ways: Koschmieder 3.0/V (airfield_lighting.md s.10.3), 3.912/V (the app today) and the ASOS
   day/night inversion (weather.md s.3.1, tools/env/metar_decode.py extinction_from_visibility). One threshold E_T per
   period is fitted (geometric mean) and the distance error of every row is printed.
2. Real archived KSFO weather presets (spec s.10): each raw report decoded with metar_decode.render_params, with the
   Sun/Moon state from ephemeris.mjs skyState() and the natural illuminance with a cloud divisor (spec s.4.2).
3. Reference lighting controller (spec s.5.3): FAA JO 7110.65BB s.3-4 tables (online edition fetched 2026-09-24,
   refs/cache/lighting/jo7110_65_chap3_section_4.html) applied to each preset. The runway configuration is an INPUT
   (stated per preset); it is not derived from the weather.
Provenance tags used in the output: [V] quoted source, [M] computed here, [I] our modelling choice.
"""
import json, math, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from metar_decode import decode_metar, render_params, extinction_from_visibility, SM_M  # noqa: E402

# ------------------------------------------------------------------------------------------ 1. Table B-1 fit
# (period, meteorological visibility SM, distance SM, intensity cd)  [V] AC 70/7460-1N Table B-1 + B.3 text
TABLE_B1 = [('night', 3, 2.9, 1500), ('night', 3, 3.1, 2000), ('night', 3, 1.4, 32), ('night', 1, 1.2, 2000),
            ('day', 1, 1.5, 200000), ('day', 1, 1.4, 100000), ('day', 1, 1.0, 20000),
            ('day', 3, 3.0, 200000), ('day', 3, 2.7, 100000), ('day', 3, 1.8, 20000)]
# twilight rows: 20,000 cd, V = 1 SM -> 1.0 to 1.5 SM; V = 3 SM -> 1.8 to 4.2 SM  [V]
TWILIGHT_B1 = [(1, 1.0, 1.5, 20000), (3, 1.8, 4.2, 20000)]


def sigma_model(model, v_sm, period):
    vm = v_sm * SM_M
    if model == 'koschmieder_3.0':
        return 3.0 / vm
    if model == 'app_3.912':
        return 3.912 / vm
    return extinction_from_visibility(vm, night=(period == 'night'))   # 'asos'


def allard_range(I, sigma, et):
    lo, hi = 1.0, 1e6
    for _ in range(200):
        m = 0.5 * (lo + hi)
        if I * math.exp(-sigma * m) / (m * m) > et:
            lo = m
        else:
            hi = m
    return lo


def fit_table_b1(model):
    out = {}
    for period in ('night', 'day'):
        rows = [r for r in TABLE_B1 if r[0] == period]
        ets = [I * math.exp(-sigma_model(model, v, period) * d * SM_M) / (d * SM_M) ** 2 for _, v, d, I in rows]
        et = math.exp(sum(math.log(e) for e in ets) / len(ets))
        res = []
        for (_, v, d, I) in rows:
            dd = allard_range(I, sigma_model(model, v, period), et) / SM_M
            res.append({'vis_sm': v, 'table_sm': d, 'cd': I, 'model_sm': round(dd, 3), 'err_pct': round(100 * (dd - d) / d, 1)})
        out[period] = {'E_T_lux': float('%.3g' % et), 'rows': res, 'max_abs_err_pct': max(abs(r['err_pct']) for r in res)}
    return out


# ------------------------------------------------------------------------------------------ 2. presets
# Real KSFO reports. Sources: IEM ASOS archive (public domain; tools/env/fixtures/ksfo_archive_wx.txt) and the
# aviationweather.gov Data API (US Government work; refs/cache/weather/metar_json_120h.json, fetched 2026-09-24).
# `rwy` = runway configuration used as controller INPUT: arrivals {end: approach type}, departures [ends].
WEST = {'arr': {'28L': 'visual', '28R': 'visual'}, 'dep': ['28L', '28R'],
        'note': 'West Plan arrivals (flysfo.com [V]); departures 28L/28R because D-ATIS 23-24 Sep 2026 said "RY 1L, 1R CLSD" [M, third party]'}
WEST_IFR = {'arr': {'28L': 'ILS', '28R': 'ILS'}, 'dep': ['1L', '1R'],
            'note': 'West Plan (flysfo.com [V]); ILS because below the charted visual-approach minima 2500 ft / 5 SM [V]; assumed [I]'}
SOUTH = {'arr': {'19L': 'ILS', '19R': 'RNAV'}, 'dep': ['10L', '10R'],
         'note': 'Southeast Plan (flysfo.com [V]) chosen by the JO 7110.65 3-5-1 fallback (wind most nearly aligned with 19) [I]; not observed'}
PRESETS = [
    ('dawn', '2026-09-24T13:40:00Z', 'METAR KSFO 241256Z 23003KT 10SM FEW200 16/11 A2986 RMK AO2 SLP111 T01560111', 'awc', WEST),
    ('noon', '2026-09-24T20:02:00Z', 'METAR KSFO 241956Z 35008KT 10SM SCT200 23/15 A2988 RMK AO2 SLP116 T02330150 $', 'awc', WEST),
    ('dusk', '2026-09-24T02:30:00Z', 'METAR KSFO 240156Z 29013KT 10SM FEW200 20/12 A2985 RMK AO2 SLP108 T02000117', 'awc', WEST),
    ('night_clear', '2026-09-24T06:56:00Z', 'METAR KSFO 240656Z 29005KT 10SM CLR 16/12 A2986 RMK AO2 SLP111 T01610122', 'awc', WEST),
    ('snapshot', '2026-09-23T17:51:00Z', 'SPECI KSFO 231722Z 09004KT 10SM FEW004 SCT008 16/13 A2996 RMK AO2 T01610133', 'awc', WEST),
    ('marine_layer', '2026-09-23T15:56:00Z', 'METAR KSFO 231556Z 14005KT 10SM FEW003 OVC005 14/13 A2995 RMK AO2 SLP143 T01440133', 'awc', dict(WEST_IFR, dep=['28L', '28R'])),
    ('low_ceiling_night', '2026-09-23T04:56:00Z', 'METAR KSFO 230456Z 30008KT 10SM FEW006 BKN010 14/12 A2995 RMK AO2 SLP141 T01440122', 'awc', dict(WEST_IFR, dep=['28L', '28R'])),
    ('predawn_fog', '2025-11-08T13:56:00Z', 'KSFO 081356Z 20003KT M1/4SM R28R/1000V1400FT FG VV002 14/14 A3001 RMK AO2 SLP161 T01440139', 'iem', WEST_IFR),
    ('night_fog', '2025-01-07T09:39:00Z', 'KSFO 070939Z 00000KT M1/4SM R28R/1600V3000FT FG BKN000 10/10 A3019 RMK AO2 FG BKN000 T01000100 $', 'iem', WEST_IFR),
    ('ifr_mist_day', '2025-11-08T17:03:00Z', 'KSFO 081703Z 03005KT 3/4SM R28R/3500VP6000FT BR BKN002 OVC004 14/14 A3004 RMK AO2 T01440144', 'iem', WEST_IFR),
    ('rain_day', '2026-04-10T19:15:00Z', 'KSFO 101915Z 18005KT 3/4SM R28R/2200VP6000FT +RA BR FEW006 BKN015 OVC048 15/13 A2988 RMK AO2 SFC VIS 1 P0010 T01500128 $', 'iem', SOUTH),
    ('squall_night', '2025-12-25T10:56:00Z', 'KSFO 251056Z 22036G63KT 2SM R28R/3500VP6000FT +RA BR SQ FEW020 SCT029 OVC039 13/11 A2961 RMK AO2 PK WND 23063/1053 SLP026 P0016 T01280106 $', 'iem', SOUTH),
    ('ts_evening', '2026-02-18T03:20:00Z', 'KSFO 180320Z COR 28012G23KT 8SM -TSRA SCT029 BKN044CB OVC080 07/04 A2970 RMK AO2 FRQ LTGICCCCG SE VCTS MOV N WSHFT 0303 RAB02 TSB20 P0001 T00720044', 'iem', WEST_IFR),
    ('drizzle_night', '2026-05-26T10:21:00Z', 'KSFO 261021Z 25008KT 2 1/2SM -DZ BR FEW005 BKN016 OVC027 13/12 A2988 RMK AO2 P0000 T01280117 $', 'iem', WEST_IFR),
]
SRC = {'iem': 'IEM ASOS archive (public domain), tools/env/fixtures/ksfo_archive_wx.txt',
       'awc': 'aviationweather.gov Data API (US Gov work), refs/cache/weather/metar_json_120h.json fetched 2026-09-24'}


def sky_states(times):
    """Sun/Moon/illuminance from ephemeris.mjs (clear sky and Brown divisors 2, 3, 4, 10)."""
    js = ("import('" + os.path.join(HERE, 'ephemeris.mjs') + "').then(m=>{const T=" + json.dumps(times) + ";"
          "const out=T.map(t=>{const d=new Date(t);const s=m.skyState(d);const E=D=>m.naturalIlluminanceAt(d,undefined,D).total;"
          "return {t, sunEl:s.sun.el, sunElTrue:s.sun.elTrue, sunAz:s.sun.az, phase:s.phase, moonEl:s.moon.el, moonLit:s.moon.illuminatedFraction,"
          "E1:E(1),E2:E(2),E3:E(3),E4:E(4),E10:E(10)}});console.log(JSON.stringify(out))})")
    r = subprocess.run(['node', '--input-type=module', '-e', js], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


# night weight from the ASOS photocell ("between 0.5 and 3 foot candles", ASOS User's Guide s.4.2 [V]), applied to the
# C171 horizontal illuminance [I]: 0 at >= 3 fc (32.3 lx), 1 at <= 0.5 fc (5.38 lx), log-linear in between.
FC = 10.7639


def night_weight(E):
    a, b = math.log(3 * FC), math.log(0.5 * FC)
    return min(1.0, max(0.0, (a - math.log(max(E, 1e-9))) / (a - b)))


def cloud_divisor(p, d):
    """[I] Brown's divisors (C171 App. B [V]) chosen from the METAR: 10 for TS/CB (C171 'dark stratus ... RARE'),
    else 1 / Kasten-Czeplak ratio [2nd] (OVC -> 4, close to Brown's 'average cloud' 3)."""
    wx = d.get('weather', [])
    if any(w.get('descriptor') == 'TS' and not w.get('vicinity') for w in wx) or any(s.get('type') == 'CB' for s in d.get('sky', [])):
        return 10.0
    return 1.0 / max(0.25, p['global_irradiance_ratio'])


# ------------------------------------------------------------------------------------------ 3. reference controller
HIRL_PCT = {5: 100, 4: 25, 3: 5, 2: 1.2, 1: 0.15}           # ac30j 2.6.4.1 [V]
ALSF2_PCT = {5: 100, 4: 20, 3: 4, 2: 0.8, 1: 0.16}          # JO 6850.2C T2-3 [V]
MALS_PCT = {3: 100, 2: 20, 1: 4}                            # JO 6850.2C T2-3 [V]
ALSF2_SFL = {5: 100, 4: 100, 3: 20, 2: 2.3, 1: 2.3}         # T2-3: steady 4-5 high, 3 medium, 1-2 low [V]
MALS_SFL = {3: 100, 2: 10, 1: 2.3}                          # T2-3 MALS* flashers 100/10/2.3 [V]; 1:1 step mapping [I]
REIL_CD = {3: 15000, 2: 1500, 1: 300}                       # AC 150/5345-51B Table 1 style E [V]; SFO style NV
ALS_OF = {'28R': 'ALSF2', '28L': 'MALSR', '19L': 'MALSF'}    # NASR [V]
REIL_ENDS = ('10L', '1L', '1R')                             # NASR RWY_END_LGTS_FLAG [V]
TDZ_ENDS = ('28R', '19L')                                   # NASR [V]
RUNWAY_OF = {'10L': '10L/28R', '28R': '10L/28R', '10R': '10R/28L', '28L': '10R/28L', '1L': '1L/19R', '19R': '1L/19R', '1R': '1R/19L', '19L': '1R/19L'}


def lt(v, x):
    """v < x for a visibility with an 'M' (less than) prefix handled by the caller (v is already reduced)."""
    return v < x


def controller(night, vis, rvr28r, ceil, rwy):
    """JO 7110.65BB s.3-4 [V tables]; choices marked [I]. vis: prevailing SM (M-prefixed values reduced by 1 %),
    rvr28r: lowest reported 28R RVR ft or None, ceil: ceiling ft or None, rwy: {'arr': {end: type}, 'dep': [ends]}."""
    out = {}
    in_use = {RUNWAY_OF[e] for e in list(rwy['arr']) + list(rwy['dep'])}
    # HIRL / RCL / TDZL: TBL 3-4-8, on sunset-sunrise for runways in use, by day when vis < 2 SM (3-4-10)
    for r in sorted(in_use):
        if night:
            st = 4 if vis < 1 else 3 if vis < 3 else 2 if vis <= 5 else 1
        elif vis < 2:
            st = 5 if vis < 1 else 4
        else:
            st = 0
        out['HIRL ' + r] = {'step': st, 'pct': HIRL_PCT.get(st, 0)}
    for e in TDZ_ENDS:
        r = RUNWAY_OF[e]
        if r in in_use:
            out['TDZ ' + e] = dict(out['HIRL ' + r])
    # ALS: 3-4-5 on; TBL 3-4-5 (ALSF-2 5-step) / TBL 3-4-7 (MALS 3-step); 3-4-9 ALSF-2 vs SSALR; 3-4-7 SFL
    for e, typ in ALS_OF.items():
        if e not in rwy['arr']:
            continue
        on = night or (ceil is not None and ceil < 1000) or vis <= 5
        if not on:
            out['ALS ' + e] = {'on': False}
            continue
        rv = rvr28r if e == '28R' else None
        if typ == 'ALSF2':
            if night:
                st = 3 if (vis < 1 or (rv is not None and rv <= 6000)) else 2 if vis <= 3 else 1
            else:
                st = 5 if (vis < 1 or (rv is not None and rv <= 6000)) else 4 if vis < 3 else 3 if vis < 5 else 2  # >=5: step 2 per the table NOTE [I]
            mode = 'ALSF-2' if (vis <= 0.75 or (rv is not None and rv <= 4000)) else 'SSALR'
            sfl = vis < 3 and rwy['arr'][e] == 'ILS'
            out['ALS ' + e] = {'on': True, 'mode': mode, 'step': st, 'pct': ALSF2_PCT[st], 'SFL': sfl, 'SFL_pct': ALSF2_SFL[st] if sfl else 0}
        else:
            if night:
                st = 3 if vis < 1 else 2 if vis < 3 else 1
            else:
                st = 3 if vis < 2 else 2                     # day >5 SM with ceiling < 1000: step 2 [I]
            sfl = vis < 3 and rwy['arr'][e] == 'ILS'
            out['ALS ' + e] = {'on': True, 'mode': typ, 'step': st, 'pct': MALS_PCT[st], 'SFL': sfl, 'SFL_pct': MALS_SFL[st] if sfl else 0,
                               'note': 'TBL 3-4-7 (separate MALSR controls); TBL 3-4-9 if slaved to the HIRL - SFO wiring NV'}
    # REIL: 3-4-2 "When the associated runway lights are lighted"; TBL 3-4-1; only ends in use [I]
    for e in REIL_ENDS:
        r = RUNWAY_OF[e]
        if (e in rwy['arr'] or e in rwy['dep']) and out.get('HIRL ' + r, {}).get('step', 0) > 0:
            st = (3 if vis < 1 else 2 if vis < 3 else 1) if night else (3 if vis < 2 else 2)
            out['REIL ' + e] = {'step': st, 'cd_eff': REIL_CD[st]}
    # PAPI: continuous photo-electric (AC 150/5345-28H 3.3.6) - day 100 %, night 20 % default of the 5/20 % choice [I]
    out['PAPI (all 6)'] = {'mode': 'night' if night else 'day', 'pct': 20 if night else 100}
    # taxiway lights: TBL 3-4-12 (5-step)
    out['taxiway'] = {'step': (4 if vis < 1 else 3) if night else (5 if vis < 1 else 0)}
    out['taxiway']['pct'] = HIRL_PCT.get(out['taxiway']['step'], 0)
    # beacon (not drawn: position unpublished): 3-4-18; basic VFR = ceiling >= 1000 ft and visibility >= 3 SM (14 CFR 91.155(c),(d)(1)) [V]
    out['beacon'] = {'on': night or vis < 3 or (ceil is not None and ceil < 1000)}
    out['obstruction'] = {'on': night, 'note': 'photocell 60->35 fc north sky (AC 70/7460-1N 5.3); tower rule sunset-sunrise (3-4-17)'}
    out['RWSL'] = {'on': 'automatic, continuous (3-4-19); activation from traffic'}
    return out


def main(write_json=False):
    print('=== 1. Allard fit to AC 70/7460-1N Table B-1 (+ B.3 night 1 SM row) ===')
    fits = {m: fit_table_b1(m) for m in ('koschmieder_3.0', 'app_3.912', 'asos')}
    for m, f in fits.items():
        print(f"{m:16s} night E_T {f['night']['E_T_lux']:.3g} lx (max err {f['night']['max_abs_err_pct']} %)   day E_T {f['day']['E_T_lux']:.3g} lx (max err {f['day']['max_abs_err_pct']} %)")
    for per in ('night', 'day'):
        for r in fits['asos'][per]['rows']:
            print(f"   asos {per:5s} V {r['vis_sm']} SM  {r['cd']:>7} cd  table {r['table_sm']} SM  model {r['model_sm']} SM  ({r['err_pct']:+.1f} %)")
    etn, etd = fits['asos']['night']['E_T_lux'], fits['asos']['day']['E_T_lux']
    for v, d0, d1, I in TWILIGHT_B1:
        dd = allard_range(I, sigma_model('asos', v, 'day'), etd) / SM_M
        dn = allard_range(I, sigma_model('asos', v, 'night'), etn) / SM_M
        print(f"   twilight V {v} SM {I} cd: table {d0}-{d1} SM; day model {dd:.2f} SM, night model {dn:.2f} SM")

    print('\n=== 2./3. Presets: decoded weather, sky state, reference controller ===')
    sk = {s['t']: s for s in sky_states([p[1] for p in PRESETS])}
    vectors = []
    for pid, t, raw, src, rwy in PRESETS:
        s = sk[t]
        night_tower = s['sunElTrue'] <= -50 / 60           # sunset..sunrise, USNO -50' (JO 7110.65 "sunset to sunrise") [V]
        d = decode_metar(raw if raw.startswith(('METAR', 'SPECI')) else 'METAR ' + raw)
        p0 = render_params(d, night=False)
        D = cloud_divisor(p0, d)
        E = s['E1'] / D
        w = night_weight(E)
        vis = d['visibility']
        vis_m = vis['m'] if vis else None
        sd = extinction_from_visibility(vis_m, night=False) if vis_m else None
        sn = extinction_from_visibility(vis_m, night=True) if vis_m else None
        sig = (1 - w) * sd + w * sn if sd else None
        v_sm = (vis['sm'] * (0.99 if vis.get('prefix') == 'M' else 1.0)) if vis else 10.0
        rv = [r for r in d.get('rvr', []) if r['runway'] == '28R']
        rvr = rv[0]['min_ft'] if rv else None
        ctl = controller(night_tower, v_sm, rvr, d.get('ceiling_ft'), rwy)
        pr = render_params(d, night=w >= 0.5)
        if pr['precip'] and pr['precip']['kind'] == 'rain':
            # spec s.4.6 / X9 [I]: Prrrr is an average since the last report, the coded intensity is the rate at the
            # observation (JO 7900.5E Table 9-4) -> clamp the Prrrr rate into the coded class
            lo, hi = {'light': (0.0, 2.54), 'moderate': (2.8, 7.62), 'heavy': (7.62, 1e9)}[pr['precip']['intensity'] or 'moderate']
            pr['precip']['rate_mm_h_spec'] = round(min(max(pr['precip']['rate_mm_h'], lo), hi), 2)
        ev = math.log2(0.18 * E / math.pi * 100 / 12.5)
        rec = {'id': pid, 'time_utc': t, 'metar': raw, 'source': SRC[src], 'runway_config_input': rwy,
               'sun_el_deg': round(s['sunEl'], 2), 'sun_az_deg': round(s['sunAz'], 1), 'phase': s['phase'], 'tower_night': night_tower,
               'moon_el_deg': round(s['moonEl'], 1), 'moon_lit': round(s['moonLit'], 2),
               'E_clear_lux': float('%.3g' % s['E1']), 'cloud_divisor': round(D, 2), 'E_lux': float('%.3g' % E), 'EV100_natural': round(ev, 1),
               'night_weight_asos': round(w, 2), 'sigma_day': sd and float('%.3g' % sd), 'sigma_night': sn and float('%.3g' % sn),
               'sigma_blend': sig and float('%.3g' % sig), 'visibility_lower_bound': pr['visibility_is_lower_bound'],
               'flight_category': d.get('flight_category'), 'ceiling_ft': d.get('ceiling_ft'), 'rvr28r_min_ft': rvr,
               'cloud_layers': [{k: L[k] for k in ('cover', 'height_ft', 'summation', 'own_fraction')} for L in pr['cloud_layers']],
               'sun_visible_probability': pr['sun_visible_probability'], 'kc_ratio': pr['global_irradiance_ratio'],
               'fog': pr['fog'], 'precip': pr['precip'], 'wind': pr['wind'], 'lightning': pr['lightning'], 'lights': ctl}
        vectors.append(rec)
        print(f"{pid:18s} {t} sun {s['sunEl']:6.2f} {s['phase']:12s} night={night_tower!s:5s} E {E:.3g} lx (D {D:.2f}) EV {ev:5.1f} w {w:.2f} "
              f"sigma {('%.3g' % sig) if sig else '-':>8s} {d.get('flight_category')}")
        for k, v in ctl.items():
            if k in ('RWSL', 'obstruction'):
                continue
            print(f"      {k:14s} {json.dumps(v)}")
    if write_json:
        path = os.path.join(HERE, 'fixtures', 'env_presets.json')
        with open(path, 'w') as f:
            json.dump({'schema': 'sfo3d.env_presets.v1', 'spec': 'docs/research/environment_spec.md',
                       'generator': 'tools/env/env_spec_checks.py', 'table_b1_fit': fits, 'presets': vectors}, f, indent=1)
        print('wrote', path)


if __name__ == '__main__':
    main('--json' in sys.argv)
