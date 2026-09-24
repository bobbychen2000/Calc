#!/usr/bin/env python3
"""METAR / SPECI (and basic TAF) decoder for KSFO, plus a METAR -> rendering-parameter mapping.

Purpose: research tool for docs/research/weather.md. It decodes every METAR group that matters for visuals and
maps the decoded report to physically based rendering inputs (extinction, cloud layers, precipitation, wetness,
windsock). The JS renderer should port `decode_metar()` and `render_params()`; this file is the reference and the
unit tests (tools/env/test_metar_decode.py) pin the behaviour on 58 real KSFO reports.

Standards (all quoted in docs/research/weather.md section 2; paragraph numbers below):
  [7900]  FAA Order JO 7900.5E w/ Chg 1, Surface Weather Observing (2020-01-15; Chg 1 2021-07-01; "Active"),
          https://www.faa.gov/documentLibrary/media/Order/JO_7900.5E_with_Change_1.pdf
          ch. 13 = coding (13.10 wind, 13.11 visibility + Table 13-3, 13.12 RVR, 13.13 present weather + Table 13-4,
          13.14 sky + Table 13-5/13-6, 13.15 temp, 13.16 altimeter, 13.21-13.58 remarks).
  [AIM]   FAA Aeronautical Information Manual, effective 2026-07-09 (Change 3): 7-1-7 flight categories,
          7-1-28 METAR/TAF key, 7-1-29 ICAO formats. https://www.faa.gov/air_traffic/publications/atpubs/aim_html/
  [FMH1]  FCM-H1-2005 (the 2019 edition's official PDF is in AWS "DEEP_ARCHIVE" and could not be fetched).
Physics (docs/research/weather.md section 3):
  [ASOS]  ASOS User's Guide (NOAA/DoD/FAA/USN, March 1998) https://www.weather.gov/media/asos/aum-toc.pdf :
          "For a given extinction coefficient, the day calculation will provide a visibility from 1/2 to 1/3 of that
          derived by the night equation."
  [R99]   Rasmussen et al. 1999, J. Appl. Meteor. 38:1542 (https://opensky.ucar.edu/system/files/2024-08/articles_15245.pdf):
          "The U.S. National Weather Service visibility algorithm for its ASOS systems uses Koschmieder's Eq. (21) with
          e = 0.055 to estimate day visibility, and the simplified Allard's law [(24)] with I0 = 25 candles and
          CDB = 0.084 mi-1 to estimate night visibility."  Eq. 24: Vn = (I0/CDB) exp(-s Vn).
  [WMO]   WMO OSCAR MOR definition (5 % of luminous flux, 2 700 K lamp) https://space.oscar.wmo.int/variables/view/meteorological_optical_range_mor_surface
  [GN07]  Garg & Nayar 2007, "Vision and Rain", IJCV (Marshall-Palmer N(a), terminal velocity v = 200 sqrt(a)).
  [AC27F] FAA AC 150/5345-27F (2021-12-15) 3.2.2: windsock "fully extend when exposed to a wind of 15 knots";
          3.5: moves freely at 3 knots or more.
Everything marked INFERRED in render_params() is a modelling choice, not a sourced fact.

Usage:
  python3 tools/env/metar_decode.py "METAR KSFO 241856Z 03006KT 10SM SCT200 22/16 A2989 RMK AO2 SLP120 T02170161"
  python3 tools/env/metar_decode.py --render --night "<metar>"
  python3 tools/env/metar_decode.py --fetch            # live KSFO METAR+TAF from aviationweather.gov (not from a browser: no CORS)
"""
import json, math, re, sys
from datetime import datetime, timezone

SM_M = 1609.344          # statute mile (exact)
FT_M = 0.3048            # foot (exact)
KT_MS = 1852.0 / 3600.0  # knot (exact)
INHG_HPA = 33.8639       # inch of mercury (0 degC) to hPa

# ---------------------------------------------------------------------------------------------------- vocabularies
# [7900] Table 13-4 (present weather).  Order of columns: intensity/proximity, descriptor, precip, obscuration, other.
DESCRIPTORS = ('MI', 'PR', 'BC', 'DR', 'BL', 'SH', 'TS', 'FZ')
PRECIP = ('DZ', 'RA', 'SN', 'SG', 'IC', 'PL', 'GR', 'GS', 'UP')
OBSCUR = ('BR', 'FG', 'FU', 'VA', 'DU', 'SA', 'HZ', 'PY')
OTHER = ('PO', 'SQ', 'FC', 'SS', 'DS')
PHEN = PRECIP + OBSCUR + OTHER
WX_NAMES = {'DZ': 'drizzle', 'RA': 'rain', 'SN': 'snow', 'SG': 'snow grains', 'IC': 'ice crystals', 'PL': 'ice pellets',
            'GR': 'hail', 'GS': 'snow pellets', 'UP': 'unknown precipitation', 'BR': 'mist', 'FG': 'fog', 'FU': 'smoke',
            'VA': 'volcanic ash', 'DU': 'widespread dust', 'SA': 'sand', 'HZ': 'haze', 'PY': 'spray',
            'PO': 'dust/sand whirls', 'SQ': 'squall', 'FC': 'funnel cloud', 'SS': 'sandstorm', 'DS': 'duststorm',
            'MI': 'shallow', 'PR': 'partial', 'BC': 'patches', 'DR': 'low drifting', 'BL': 'blowing',
            'SH': 'showers', 'TS': 'thunderstorm', 'FZ': 'freezing'}
_WX_RE = re.compile(r'^(?P<int>[+-]|VC)?(?P<desc>MI|PR|BC|DR|BL|SH|TS|FZ)?(?P<phen>(?:' + '|'.join(PHEN) + r')*)$')
# [7900] Table 13-5: summation amount in eighths (min, max).  FEW is ">0 - 2/8", SCT 3/8-4/8, BKN 5/8-7/8, OVC 8/8.
COVER_OKTAS = {'FEW': (0.5, 2), 'SCT': (3, 4), 'BKN': (5, 7), 'OVC': (8, 8), 'VV': (8, 8)}
COMPASS = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
_LOCWORDS = set(COMPASS) | {'OHD', 'VC', 'VCY', 'DSNT', 'ALQDS', 'AND', 'MOV', 'IN', 'GAP', 'BNK', 'BANK', 'AT', 'AP',
                            'OVR', 'THRU', 'UNKN', 'STNRY', 'BAY', 'RWY', 'DSIPTD', 'ONLY',
                            'MOVE', 'ALDQS', 'DNST'}            # typos observed in KSFO remarks 2016-2026


def _is_dir(tok):
    """Compass point, compass range (E-SE), or run of points (SE-SW)."""
    return all(p in COMPASS for p in tok.split('-'))


def _frac(s):
    """'1/2' -> 0.5, '3' -> 3.0, 'M1/4' -> (0.25, 'M'), 'P6' -> (6, 'P')."""
    pre = ''
    if s[:1] in 'MP' and len(s) > 1 and (s[1].isdigit()):
        pre, s = s[0], s[1:]
    if '/' in s:
        n, d = s.split('/')
        v = int(n) / int(d)
    else:
        v = float(s)
    return v, pre


def _vis_value(tokens, i):
    """Parse a statute-mile visibility starting at tokens[i]; supports '1 1/2SM', 'M1/4SM', 'P6SM', '10SM'.
    Returns (value_sm, prefix, n_tokens_consumed) or None.  [7900] 13.11: "A space is coded between whole numbers
    and fractions of reportable visibility values ... Only automated stations may use an 'M'"."""
    t = tokens[i]
    if re.fullmatch(r'\d{1,2}', t) and i + 1 < len(tokens) and re.fullmatch(r'\d/\d{1,2}SM', tokens[i + 1]):
        v2, _ = _frac(tokens[i + 1][:-2])
        return int(t) + v2, '', 2
    m = re.fullmatch(r'([MP]?\d{1,2}(?:/\d{1,2})?)SM', t)
    if m:
        v, pre = _frac(m.group(1))
        return v, pre, 1
    return None


def _vis_remark_value(tokens, i):
    """Remark visibility value without the SM suffix ('1 1/2', 'M1/4', '6', '3SM' seen at KSFO)."""
    if i >= len(tokens):
        return None
    t = tokens[i].removesuffix('SM')
    if re.fullmatch(r'\d{1,2}', t) and i + 1 < len(tokens) and re.fullmatch(r'\d/\d{1,2}(SM)?', tokens[i + 1]):
        return int(t) + _frac(tokens[i + 1].removesuffix('SM'))[0], '', 2
    if re.fullmatch(r'[MP]?\d{1,2}(/\d{1,2})?', t):
        v, pre = _frac(t)
        return v, pre, 1
    return None


def _temp(s):
    return -int(s[1:]) if s.startswith('M') else int(s)


def _tgroup(s):
    """[7900] 13.52: sign digit 1 = below 0 degC, then tenths."""
    return (-1 if s[0] == '1' else 1) * int(s[1:4]) / 10.0


def _slp(ppp, altim_hpa=None):
    """[7900] 13.40: SLP coded with tens, units and tenths of hPa ('SLP982' = 998.2).  The leading 9 or 10 is
    implicit: pick the candidate nearest the altimeter-derived QNH when available, else the usual <500 -> 10xx rule."""
    v = int(ppp) / 10.0
    cands = (900 + v, 1000 + v)
    if altim_hpa:
        return min(cands, key=lambda c: abs(c - altim_hpa))
    return cands[1] if int(ppp) < 500 else cands[0]


# ------------------------------------------------------------------------------------------------- body elements
def _parse_wx(tok):
    """Present-weather group -> dict, or None if tok is not a weather group.  [7900] 13.13 and Table 13-4."""
    if tok in ('NSW',):
        return {'raw': tok, 'nsw': True}
    m = _WX_RE.match(tok)
    if not m or (not m.group('phen') and m.group('desc') != 'TS' and not (m.group('int') == 'VC' and m.group('desc') == 'SH')):
        return None
    if not m.group('int') and not m.group('desc') and not m.group('phen'):
        return None
    ph = [m.group('phen')[k:k + 2] for k in range(0, len(m.group('phen')), 2)]
    inten = m.group('int') or ''
    return {'raw': tok, 'intensity': {'-': 'light', '+': 'heavy'}.get(inten, 'moderate' if inten != 'VC' else None),
            'vicinity': inten == 'VC', 'descriptor': m.group('desc'), 'phenomena': ph,
            'precip': [p for p in ph if p in PRECIP], 'obscuration': [p for p in ph if p in OBSCUR],
            'tornadic': tok == '+FC'}


def _parse_sky(tok):
    m = re.fullmatch(r'(FEW|SCT|BKN|OVC)(\d{3}|///)(CB|TCU|///)?', tok)
    if m:
        h = None if m.group(2) == '///' else int(m.group(2)) * 100
        return {'cover': m.group(1), 'height_ft': h, 'type': m.group(3) if m.group(3) != '///' else None}
    m = re.fullmatch(r'VV(\d{3}|///)', tok)
    if m:
        return {'cover': 'VV', 'height_ft': None if m.group(1) == '///' else int(m.group(1)) * 100, 'type': None}
    if tok in ('CLR', 'SKC', 'NSC', 'NCD'):
        return {'cover': tok, 'height_ft': None, 'type': None}
    return None


def _parse_body(tokens, out, taf=False):
    """Decode body element tokens (from wind onwards) into `out`.  Unknown tokens go to out['unparsed']."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        m = re.fullmatch(r'(\d{3}|VRB|///)(\d{2,3}|//)(?:G(\d{2,3}))?(KT|MPS|KMH)', t)
        if m and 'wind' not in out:
            unit = {'KT': 1.0, 'MPS': 1 / KT_MS, 'KMH': 1 / 1.852}[m.group(4)]
            spd = None if m.group(2) == '//' else round(int(m.group(2)) * unit, 1)
            calm = t.startswith('00000')
            d = None if (m.group(1) in ('VRB', '///') or calm) else int(m.group(1))
            out['wind'] = {'dir_true_deg': d, 'speed_kt': spd, 'gust_kt': round(int(m.group(3)) * unit, 1) if m.group(3) else None,
                           'variable': m.group(1) == 'VRB', 'calm': calm, 'var_from': None, 'var_to': None}
            i += 1
            continue
        m = re.fullmatch(r'(\d{3})V(\d{3})', t)
        if m and 'wind' in out:
            out['wind']['var_from'], out['wind']['var_to'] = int(m.group(1)), int(m.group(2))
            i += 1
            continue
        if t == 'CAVOK':
            out['visibility'] = {'sm': 10000 / SM_M, 'prefix': 'P', 'm': 10000.0, 'raw': t}
            i += 1
            continue
        v = _vis_value(tokens, i)
        if v and 'visibility' not in out:
            val, pre, n = v
            out['visibility'] = {'sm': val, 'prefix': pre or None, 'm': val * SM_M, 'raw': ' '.join(tokens[i:i + n])}
            i += n
            continue
        if re.fullmatch(r'\d{4}', t) and 'visibility' not in out and 'wind' in out:    # ICAO metres (not used in the US)
            out['visibility'] = {'sm': (10000 if t == '9999' else int(t)) / SM_M, 'prefix': 'P' if t == '9999' else None,
                                 'm': 10000.0 if t == '9999' else float(t), 'raw': t}
            i += 1
            continue
        m = re.fullmatch(r'R(\d{2}[LRC]?)/([MP]?)(\d{4})(?:V([MP]?)(\d{4}))?(FT)?(?:/?([UDN]))?', t)
        if m:
            lo = int(m.group(3)); hi = int(m.group(5)) if m.group(5) else None
            out.setdefault('rvr', []).append({'runway': m.group(1), 'min_ft': lo, 'min_prefix': m.group(2) or None,
                                              'max_ft': hi, 'max_prefix': (m.group(4) or None) if hi else None,
                                              'unit': 'ft' if m.group(6) else 'm', 'tendency': m.group(7), 'raw': t})
            i += 1
            continue
        w = _parse_wx(t)
        if w:
            out.setdefault('weather', []).append(w)
            i += 1
            continue
        s = _parse_sky(t)
        if s:
            out.setdefault('sky', []).append(s)
            i += 1
            continue
        m = re.fullmatch(r'(M?\d{2})/(M?\d{2})?', t)
        if m and not taf:
            out['temp_c'] = _temp(m.group(1))
            out['dewpoint_c'] = _temp(m.group(2)) if m.group(2) else None
            i += 1
            continue
        m = re.fullmatch(r'A(\d{4})', t)
        if m:
            out['altimeter_inhg'] = int(m.group(1)) / 100.0
            out['qnh_hpa'] = round(out['altimeter_inhg'] * INHG_HPA, 1)
            i += 1
            continue
        m = re.fullmatch(r'Q(\d{4})', t)
        if m:
            out['qnh_hpa'] = float(m.group(1))
            i += 1
            continue
        m = re.fullmatch(r'WS(\d{3})/(\d{3})(\d{2,3})KT', t)
        if m and taf:
            out['wind_shear'] = {'height_ft': int(m.group(1)) * 100, 'dir': int(m.group(2)), 'speed_kt': int(m.group(3))}
            i += 1
            continue
        out.setdefault('unparsed', []).append(t)
        i += 1


# ------------------------------------------------------------------------------------------------------ remarks
def _parse_remarks(rt, out):
    """Decode the RMK section ([7900] 13.17-13.58).  Recognised groups go to out['rmk'][...]; free text that is not
    recognised is kept verbatim in out['rmk']['plain'] (e.g. 'FG IN GAP W', 'TS DSIPTD')."""
    r = out['rmk']
    toks = rt.split()
    altim_hpa = out.get('qnh_hpa')
    plain = []
    i = 0
    n = len(toks)

    def flush_plain():
        if plain:
            r.setdefault('plain', []).append(' '.join(plain))
            plain.clear()

    while i < n:
        t = toks[i]
        nxt = toks[i + 1] if i + 1 < n else ''
        # --- automated station type [7900] 13.21
        if t in ('AO1', 'AO2', 'AO1A', 'AO2A', 'A01', 'A02'):      # 'A02' (zero for O) occurs 76 times at KSFO 2016-26
            flush_plain(); r['station_type'] = t.replace('0', 'O', 1) if t[1] == '0' else t; i += 1; continue
        # --- peak wind 13.22: PK WND dddff(f)/(hh)mm
        if t == 'PK' and nxt == 'WND' and i + 2 < n:
            m = re.fullmatch(r'(\d{3})(\d{2,3})/(\d{2,4})', toks[i + 2])
            if m:
                flush_plain()
                r['peak_wind'] = {'dir_true_deg': int(m.group(1)), 'speed_kt': int(m.group(2)), 'time': m.group(3)}
                i += 3; continue
        # --- wind shift 13.23
        if t == 'WSHFT' and re.fullmatch(r'\d{2,4}', nxt):
            flush_plain()
            fropa = i + 2 < n and toks[i + 2] == 'FROPA'
            r['wind_shift'] = {'time': nxt, 'fropa': fropa}
            i += 3 if fropa else 2; continue
        # --- tower / surface visibility 13.24
        if t in ('TWR', 'SFC') and nxt == 'VIS':
            v = _vis_remark_value(toks, i + 2)
            if v:
                flush_plain(); r['tower_vis_sm' if t == 'TWR' else 'surface_vis_sm'] = v[0]; i += 2 + v[2]; continue
        # --- VIS remarks: variable 13.25, sector 13.26, second location 13.27
        if t in ('VIS', 'CIG') and nxt == 'LWR' and i + 2 < n and _is_dir(toks[i + 2]):
            flush_plain(); r.setdefault('lower_toward', []).append({'what': t, 'dir': toks[i + 2]}); i += 3; continue
        if t == 'VIS':
            whole = 0; k0 = 1
            if re.fullmatch(r'\d', nxt) and i + 2 < n and re.fullmatch(r'\d/\d{1,2}V.+', toks[i + 2]):
                whole = int(nxt); k0 = 2; nxt = toks[i + 2]                  # 'VIS 1 1/2V5' = 1 1/2 to 5
            m = re.fullmatch(r'([MP]?\d{1,2}(?:/\d{1,2})?)V([MP]?\d{1,2}(?:/\d{1,2})?)(SM)?', nxt)
            if m:
                flush_plain()
                lo = whole + _frac(m.group(1))[0]; hi = _frac(m.group(2))[0]; k = k0 + 1
                if '/' not in m.group(2) and i + k < n and re.fullmatch(r'\d/\d{1,2}', toks[i + k]):
                    hi += _frac(toks[i + k])[0]; k += 1         # 'VIS 1/2V2 1/2' = 1/2 to 2 1/2
                r['vis_variable_sm'] = (lo, hi); i += k; continue
            j = i + 1; dirs = []
            while j < n and _is_dir(toks[j]):
                dirs.append(toks[j]); j += 1
            v = _vis_remark_value(toks, j)
            if dirs and v:
                flush_plain(); r.setdefault('vis_sector', []).append({'dirs': dirs, 'sm': v[0], 'prefix': v[1] or None})
                i = j + v[2]; continue
            v = _vis_remark_value(toks, i + 1)
            if v:
                k = i + 1 + v[2]; loc = None
                if k < n and toks[k] == 'RWY' and k + 1 < n:
                    loc = 'RWY ' + toks[k + 1]; k += 2
                elif k < n and re.fullmatch(r'RWY\w+', toks[k]):
                    loc = toks[k]; k += 1
                flush_plain(); r.setdefault('vis_other', []).append({'sm': v[0], 'loc': loc}); i = k; continue
        # --- variable ceiling 13.34, ceiling at second location 13.38
        if t == 'CIG':
            m = re.fullmatch(r'(\d{3})V(\d{3})', nxt)
            if m:
                flush_plain(); r['cig_variable_ft'] = (int(m.group(1)) * 100, int(m.group(2)) * 100); i += 2; continue
            if re.fullmatch(r'\d{3}', nxt):
                k = i + 2; loc = None
                if k < n and toks[k] == 'RWY' and k + 1 < n:
                    loc = 'RWY ' + toks[k + 1]; k += 2
                elif k < n and re.fullmatch(r'RWY\w+', toks[k]):
                    loc = toks[k]; k += 1
                flush_plain(); r['cig_second_location'] = {'height_ft': int(nxt) * 100, 'loc': loc}; i = k; continue
        # --- obscuration 13.35: w'w' NsNsNshshshs  (e.g. 'FG BKN000', 'FU FEW004', 'FU BKN020')
        if re.fullmatch(r'(MI|PR|BC)?(' + '|'.join(OBSCUR) + ')', t) and re.fullmatch(r'(FEW|SCT|BKN|OVC)\d{3}', nxt):
            flush_plain()
            r.setdefault('obscuration_layers', []).append({'wx': t, 'cover': nxt[:3], 'height_ft': int(nxt[3:]) * 100})
            i += 2; continue
        # --- variable sky condition 13.36: 'BKN014 V OVC', 'SCT V BKN'
        if re.fullmatch(r'(FEW|SCT|BKN|OVC)(\d{3})?', t) and nxt == 'V' and i + 2 < n and toks[i + 2] in ('FEW', 'SCT', 'BKN', 'OVC'):
            flush_plain()
            r.setdefault('sky_variable', []).append({'from': t[:3], 'height_ft': int(t[3:]) * 100 if len(t) > 3 else None, 'to': toks[i + 2]})
            i += 3; continue
        # --- lightning 13.28: [OCNL|FRQ|CONS] LTG[IC][CC][CG][CA] [loc...]
        m = re.fullmatch(r'LTG((?:IC|CC|CG|CA)*)', t)
        if m or (t in ('OCNL', 'FRQ', 'CONS') and re.fullmatch(r'LTG(?:IC|CC|CG|CA)*', nxt)):
            flush_plain()
            freq = None
            if not m:
                freq = t; i += 1; t = toks[i]; m = re.fullmatch(r'LTG((?:IC|CC|CG|CA)*)', t)
            types = [m.group(1)[k:k + 2] for k in range(0, len(m.group(1)), 2)]
            j = i + 1; loc = []
            while j < n and (toks[j] in ('DSNT', 'VC', 'OHD', 'ALQDS', 'AND') or _is_dir(toks[j])):
                loc.append(toks[j]); j += 1
            r.setdefault('lightning', []).append({'frequency': freq, 'types': types, 'loc': ' '.join(loc) or None})
            i = j; continue
        # --- begin/end of precipitation 13.29 and thunderstorm 13.30: RAB05E30SNB20E55, TSB0159E30, GRB47E53
        if re.fullmatch(r'(?:[A-Z]{2,6}?(?:[BE](?:\d{4}|\d{2}|MM))+)+', t) and re.search(r'\d|[BE]MM', t):
            evs = []                                  # 'MM' = time missing (e.g. 'RAEMMB27', seen at KSFO)
            for mm in re.finditer(r'([A-Z]{2,6}?)((?:[BE](?:\d{4}|\d{2}|MM))+)', t):
                for e in re.finditer(r'([BE])(\d{4}|\d{2}|MM)', mm.group(2)):
                    evs.append({'wx': mm.group(1), 'event': 'begin' if e.group(1) == 'B' else 'end', 'time': e.group(2)})
            if evs and all(e['wx'] in ('TS',) or re.fullmatch(r'(SH|FZ)?(' + '|'.join(PRECIP) + ')+', e['wx']) for e in evs):
                flush_plain(); r.setdefault('wx_events', []).extend(evs); i += 1; continue
        # --- pressure rising/falling rapidly 13.39
        if t in ('PRESRR', 'PRESFR'):
            flush_plain(); r['pressure_rapid'] = 'rising' if t == 'PRESRR' else 'falling'; i += 1; continue
        # --- sea-level pressure 13.40
        m = re.fullmatch(r'SLP(\d{3})', t)
        if m:
            flush_plain(); r['slp_hpa'] = _slp(m.group(1), altim_hpa); i += 1; continue
        if t == 'SLPNO':
            flush_plain(); r['slp_hpa'] = None; r.setdefault('sensor_status', []).append('SLPNO'); i += 1; continue
        # --- hourly precipitation 13.46: Prrrr (hundredths of an inch since last METAR)
        m = re.fullmatch(r'P(\d{4}|////)', t)
        if m:
            flush_plain(); r['precip_hourly_in'] = None if '/' in m.group(1) else int(m.group(1)) / 100.0; i += 1; continue
        # --- ice accretion 13.47
        m = re.fullmatch(r'I([136])(\d{3}|///)', t)
        if m:
            flush_plain(); r['ice_accretion_%sh_in' % m.group(1)] = None if '/' in m.group(2) else int(m.group(2)) / 100.0; i += 1; continue
        # --- 3/6-hour precip 13.48 (6RRRR), 24-hour precip 13.49 (7RRRR)
        m = re.fullmatch(r'([67])(\d{4}|////)', t)
        if m:
            flush_plain()
            r['precip_3or6h_in' if m.group(1) == '6' else 'precip_24h_in'] = None if '/' in m.group(2) else int(m.group(2)) / 100.0
            i += 1; continue
        # --- snow depth 13.50 (4/sss), water equivalent 13.51 (933RRR)
        m = re.fullmatch(r'4/(\d{3})', t)
        if m:
            flush_plain(); r['snow_depth_in'] = int(m.group(1)); i += 1; continue
        m = re.fullmatch(r'933(\d{3})', t)
        if m:
            flush_plain(); r['snow_water_equiv_in'] = int(m.group(1)) / 10.0; i += 1; continue
        # --- hourly temperature/dew point 13.52: TsnT'T'T'snT'dT'dT'd
        m = re.fullmatch(r'T([01]\d{3})([01]\d{3})?', t)
        if m:
            flush_plain()
            r['temp_c_tenths'] = _tgroup(m.group(1))
            r['dewpoint_c_tenths'] = _tgroup(m.group(2)) if m.group(2) else None
            i += 1; continue
        # --- 6-h max/min 13.53/13.54, 24-h max/min 13.55, 3-h pressure tendency 13.56
        m = re.fullmatch(r'([12])([01]\d{3})', t)
        if m:
            flush_plain(); r['max_temp_6h_c' if m.group(1) == '1' else 'min_temp_6h_c'] = _tgroup(m.group(2)); i += 1; continue
        m = re.fullmatch(r'4([01]\d{3})([01]\d{3})', t)
        if m:
            flush_plain(); r['max_temp_24h_c'] = _tgroup(m.group(1)); r['min_temp_24h_c'] = _tgroup(m.group(2)); i += 1; continue
        m = re.fullmatch(r'5([0-8])(\d{3})', t)
        if m:
            flush_plain(); r['pressure_tendency'] = {'character': int(m.group(1)), 'change_hpa': int(m.group(2)) / 10.0}; i += 1; continue
        # --- sensor status 13.57 (VISNO/CHINO may carry a location, e.g. 'CHINO RWY L10')
        if t in ('PWINO', 'PNO', 'FZRANO', 'TSNO', 'RVRNO'):
            flush_plain(); r.setdefault('sensor_status', []).append(t); i += 1; continue
        if t in ('VISNO', 'CHINO'):
            flush_plain(); k = i + 1; loc = None
            if k < n and toks[k] == 'RWY' and k + 1 < n:
                loc = 'RWY ' + toks[k + 1]; k += 2
            elif k < n and re.fullmatch(r'RWY\w+', toks[k]):
                loc = toks[k]; k += 1
            r.setdefault('sensor_status', []).append(t + (' ' + loc if loc else '')); i = k; continue
        # --- breaks in overcast (plain-language contraction, FAA Order JO 7340 'BINOVC')
        if t == 'BINOVC':
            flush_plain(); r['breaks_in_overcast'] = True; i += 1; continue
        # --- maintenance indicator 13.58
        if t == '$':
            flush_plain(); r['maintenance'] = True; i += 1; continue
        # --- hailstone size 13.32
        if t == 'GR' and nxt and (nxt == 'LESS' or re.fullmatch(r'\d(/\d)?', nxt)):
            flush_plain()
            if nxt == 'LESS':
                r['hail_size_in'] = '<1/4'; i += 4; continue               # 'GR LESS THAN 1/4'
            v = _vis_remark_value(toks, i + 1)
            r['hail_size_in'] = v[0]; i += 1 + v[2]; continue
        # --- significant clouds 13.37, thunderstorm location 13.31, virga 13.33, distant/vicinity phenomena
        m = re.fullmatch(r'(CB|CBMAM|TCU|ACC|ACSL|SCSL|CCSL|VIRGA|TS|VCTS|FOG|' + r'(?:VC|MI|PR|BC)?(?:' + '|'.join(OBSCUR + PRECIP) + r')+|VCSH)', t)
        if m:
            flush_plain(); j = i + 1; loc = []
            while j < n and (toks[j] in _LOCWORDS or _is_dir(toks[j])):
                loc.append(toks[j]); j += 1
            entry = {'what': t, 'loc': ' '.join(loc) or None}
            key = 'significant_clouds' if t in ('CB', 'CBMAM', 'TCU', 'ACC', 'ACSL', 'SCSL', 'CCSL') else 'phenomena'
            r.setdefault(key, []).append(entry)
            if ('FG' in t or t == 'FOG') and any(w in ('BNK', 'BANK') for w in loc):
                r['fog_bank'] = entry['loc']          # plain language, not an FAA-coded remark (see weather.md 2.9)
            if ('FG' in t or t == 'FOG') and 'GAP' in loc:
                r['fog_in_gap'] = entry['loc']        # KSFO plain language 'FG/FOG IN GAP W' (San Bruno Gap), weather.md 4.3
            i = j; continue
        plain.append(t)
        i += 1
    flush_plain()


# ------------------------------------------------------------------------------------------------------- METAR
def decode_metar(raw, ref=None):
    """Decode one METAR/SPECI line.  `ref` (datetime, UTC) resolves the month/year of the DDhhmmZ group
    (the report is taken to be the latest date not after ref + 1 day).  Returns a plain dict (JSON-safe)."""
    text = ' '.join(raw.replace('=', ' ').split())
    out = {'raw': text, 'type': None, 'station': None, 'modifier': [], 'rmk': {}}
    body, _, rmk = text.partition(' RMK ')
    if text.startswith('RMK '):
        body, rmk = '', text[4:]
    toks = body.split()
    i = 0
    if toks and toks[0] in ('METAR', 'SPECI'):
        out['type'] = toks[0]; i += 1
    if i < len(toks) and re.fullmatch(r'[A-Z][A-Z0-9]{3}', toks[i]):
        out['station'] = toks[i]; i += 1
    if i < len(toks) and re.fullmatch(r'\d{6}Z', toks[i]):
        d, h, mi = int(toks[i][:2]), int(toks[i][2:4]), int(toks[i][4:6])
        out['time'] = {'day': d, 'hour': h, 'minute': mi}
        if ref is not None:
            out['time']['utc'] = _resolve_day(ref, d, h, mi).isoformat().replace('+00:00', 'Z')
        i += 1
    while i < len(toks) and toks[i] in ('AUTO', 'COR', 'RTD', 'NIL'):
        out['modifier'].append(toks[i]); i += 1
    _parse_body(toks[i:], out)
    if rmk:
        _parse_remarks(rmk, out)
    _derive(out)
    return out


def _resolve_day(ref, d, h, mi):
    ref = ref.astimezone(timezone.utc) if ref.tzinfo else ref.replace(tzinfo=timezone.utc)
    y, m = ref.year, ref.month
    for _ in range(3):
        try:
            cand = datetime(y, m, d, h, mi, tzinfo=timezone.utc)
            if (cand - ref).total_seconds() <= 86400:
                return cand
        except ValueError:
            pass
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return datetime(ref.year, ref.month, min(d, 28), h, mi, tzinfo=timezone.utc)


def _derive(out):
    """Ceiling, flight category, precise temperatures, relative humidity."""
    sky = out.get('sky', [])
    # [7900] 10.4a: ceiling = lowest non-surface-based layer reported BKN or OVC, or VV into a surface obscuration.
    ceil = None
    for s in sky:
        if s['cover'] in ('BKN', 'OVC', 'VV') and s['height_ft'] is not None:
            if s['cover'] != 'VV' and s['height_ft'] == 0:
                continue                          # 'BKN000' = surface-based partial obscuration, not a ceiling
            ceil = s['height_ft'] if ceil is None else min(ceil, s['height_ft'])
    out['ceiling_ft'] = ceil
    vis = out.get('visibility', {}).get('sm')
    # [AIM] 7-1-7 categorical ceiling and visibility.
    cat = None
    if vis is not None or ceil is not None:
        c = ceil if ceil is not None else 1e9
        v = vis if vis is not None else 1e9
        if c < 500 or v < 1:
            cat = 'LIFR'
        elif c < 1000 or v < 3:
            cat = 'IFR'
        elif c <= 3000 or v <= 5:
            cat = 'MVFR'
        else:
            cat = 'VFR'
    out['flight_category'] = cat
    r = out['rmk']
    t = r.get('temp_c_tenths', out.get('temp_c'))
    td = r.get('dewpoint_c_tenths', out.get('dewpoint_c'))
    out['temp_c_best'], out['dewpoint_c_best'] = t, td
    if t is not None and td is not None:
        # Magnus form, Alduchov & Eskridge (1996) coefficients over water: es = 6.1094 exp(17.625 T / (T + 243.04)).
        es = lambda x: 6.1094 * math.exp(17.625 * x / (x + 243.04))
        out['rel_humidity_pct'] = round(100.0 * es(td) / es(t), 1)
    else:
        out['rel_humidity_pct'] = None


# --------------------------------------------------------------------------------------------------------- TAF
def decode_taf(raw):
    """Split a TAF into its base and change groups (FM, TEMPO, BECMG, PROBnn) and decode each group's elements with
    the METAR body parser.  [AIM] 7-1-28 (TAF key).  Returns {'station','issued','valid','periods':[...]}."""
    text = ' '.join(raw.replace('=', ' ').split())
    toks = text.split()
    i = 0
    out = {'raw': text, 'modifier': [], 'periods': []}
    if toks and toks[0] == 'TAF':
        i += 1
    while i < len(toks) and toks[i] in ('AMD', 'COR', 'RTD'):
        out['modifier'].append(toks[i]); i += 1
    out['station'] = toks[i]; i += 1
    if re.fullmatch(r'\d{6}Z', toks[i]):
        out['issued'] = toks[i]; i += 1
    if re.fullmatch(r'\d{4}/\d{4}', toks[i]):
        out['valid'] = toks[i]; i += 1
    cur = {'change': 'BASE', 'from': out.get('valid', '').split('/')[0] or None, 'to': None, 'prob': None, 'tokens': []}
    chunks = [cur]
    while i < len(toks):
        t = toks[i]
        m = re.fullmatch(r'FM(\d{6})', t)
        if m:
            cur = {'change': 'FM', 'from': m.group(1), 'to': None, 'prob': None, 'tokens': []}; chunks.append(cur); i += 1; continue
        if t in ('TEMPO', 'BECMG') or re.fullmatch(r'PROB\d{2}', t):
            prob = int(t[4:]) if t.startswith('PROB') else None
            change = t if not prob else 'PROB'
            j = i + 1
            if prob and j < len(toks) and toks[j] == 'TEMPO':
                change = 'PROB TEMPO'; j += 1
            fr = to = None
            if j < len(toks) and re.fullmatch(r'\d{4}/\d{4}', toks[j]):
                fr, to = toks[j].split('/'); j += 1
            cur = {'change': change, 'from': fr, 'to': to, 'prob': prob, 'tokens': []}; chunks.append(cur); i = j; continue
        cur['tokens'].append(t); i += 1
    for c in chunks:
        p = {k: v for k, v in c.items() if k != 'tokens'}
        el = {'rmk': {}}
        _parse_body(c['tokens'], el, taf=True)
        el.pop('rmk')
        p.update(el)
        s = el.get('sky', [])
        p['ceiling_ft'] = min([x['height_ft'] for x in s if x['cover'] in ('BKN', 'OVC', 'VV') and x['height_ft']] or [None], key=lambda x: x or 1e9)
        out['periods'].append(p)
    return out


# ----------------------------------------------------------------------------------------- rendering parameters
ASOS_DAY_CONTRAST = 0.055          # [R99]
ASOS_NIGHT_I0_CD = 25.0            # [R99] candles
ASOS_NIGHT_CDB_PER_MI = 0.084      # [R99] mi^-1


def extinction_from_visibility(vis_m, night=False, contrast=ASOS_DAY_CONTRAST):
    """Invert the ASOS visibility algorithm: reported visibility -> path-averaged extinction coefficient (1/m).
    Day: Koschmieder, V = -ln(eps)/sigma with eps = 0.055 [R99].  Night: simplified Allard's law
    Vn = (I0/CDB) exp(-sigma Vn) with I0 = 25 cd, CDB = 0.084 mi^-1, V in miles [R99 eq. 24]."""
    if vis_m is None or vis_m <= 0:
        return None
    if not night:
        return -math.log(contrast) / vis_m
    v_mi = vis_m / SM_M
    sigma_per_mi = math.log(ASOS_NIGHT_I0_CD / (ASOS_NIGHT_CDB_PER_MI * v_mi)) / v_mi
    return max(sigma_per_mi, 1e-9) / SM_M


def _layer_coverages(sky):
    """[7900] 10.7 summation principle: each reported amount is the TOTAL sky cover at and below that layer.
    Convert to the fraction each layer adds under a random-overlap assumption (INFERRED):
    own_i = 1 - (1 - C_i) / (1 - C_{i-1}).  C uses the middle of the Table 13-5 okta range."""
    out = []
    prev = 0.0
    for s in sky:
        if s['cover'] not in COVER_OKTAS:
            continue
        lo, hi = COVER_OKTAS[s['cover']]
        tot = max(prev, (lo + hi) / 2 / 8.0)
        own = 1.0 if prev >= 1.0 else max(0.0, 1.0 - (1.0 - tot) / (1.0 - prev))
        out.append({**s, 'summation': round(tot, 3), 'own_fraction': round(own, 3)})
        prev = tot
    return out


def render_params(d, night=False, marine_layer_depth_ft=None, routine_minute=56):
    """Map a decoded METAR to renderer inputs.  Every value carries its basis in the docstring / weather.md s.3.
    night: True when the ASOS photocell would select the night equation (0.5-3 fc, [ASOS]); the caller decides it
           from the sun elevation (INFERRED mapping, weather.md 3.2).
    marine_layer_depth_ft: cloud thickness for low stratus when known (e.g. from the Oakland sounding); default
           1000 ft = the upper end of "usually less than 1000 feet" (MIT LL ATC-319 s.3.3.3)."""
    p = {'sources': {}}
    vis = d.get('visibility')
    vis_m = vis['m'] if vis else None
    lower_bound = bool(vis) and (vis['prefix'] == 'P' or vis['sm'] >= 10)
    beta = extinction_from_visibility(vis_m, night=night)
    p['visibility_m'] = vis_m
    p['visibility_is_lower_bound'] = lower_bound       # '10SM' means 10 or more ([ASOS] "10 miles or greater")
    p['extinction_per_m'] = beta                       # an UPPER bound when visibility_is_lower_bound
    p['sources']['extinction'] = 'ASOS inversion, %s equation [R99]' % ('night Allard' if night else 'day Koschmieder eps=0.055')
    wx = d.get('weather', [])
    phen = {ph for w in wx if not w.get('vicinity') for ph in w.get('phenomena', [])}
    desc = {w.get('descriptor') for w in wx}
    # ---- fog / mist / haze / smoke (obscurations in the body only when vis < 7 SM, [7900] 13.13a(2))
    fog = 'FG' in phen
    p['fog'] = None
    if fog or 'BR' in phen:
        vv = next((s['height_ft'] for s in d.get('sky', []) if s['cover'] == 'VV'), None)
        p['fog'] = {'kind': 'fog' if fog else 'mist',
                    'partial': bool(desc & {'BC', 'PR', 'MI'}),
                    'shallow': 'MI' in desc,
                    'vertical_visibility_ft': vv,
                    # INFERRED: a surface layer at least as deep as VV (the ceilometer sees VV into it); when no VV,
                    # mist fills the mixed layer up to the lowest cloud base.
                    'top_ft_min': vv if vv is not None else d.get('ceiling_ft')}
    p['aerosol'] = {'haze': 'HZ' in phen, 'smoke': 'FU' in phen,
                    'smoke_aloft': [o for o in d['rmk'].get('obscuration_layers', []) if o['wx'] == 'FU'],
                    'distant': [x for x in d['rmk'].get('phenomena', []) if x['what'] in ('FU', 'HZ', 'DU', 'SA')]}
    # ---- clouds
    layers = _layer_coverages(d.get('sky', []))
    depth_ft = marine_layer_depth_ft or 1000
    for L in layers:
        h = L['height_ft']
        # INFERRED thickness: low stratus = marine layer depth; otherwise unknown (renderer default).
        L['base_m'] = None if h is None else h * FT_M
        L['thickness_m_guess'] = (depth_ft * FT_M) if (h is not None and h < 3000 and L['cover'] in ('BKN', 'OVC', 'SCT')) else None
    p['cloud_layers'] = layers
    p['ceiling_m'] = None if d.get('ceiling_ft') is None else d['ceiling_ft'] * FT_M
    clear_frac = 1.0
    for L in layers:
        clear_frac *= (1.0 - L['own_fraction'])
    p['sun_visible_probability'] = round(clear_frac, 3)          # INFERRED (random overlap)
    n_oktas = 8.0 * (1.0 - clear_frac)
    # Kasten & Czeplak (1980) all-sky global irradiance ratio G(N)/G(0) = 1 - 0.75 (N/8)^3.4  [SECONDARY, weather.md 3.4]
    p['global_irradiance_ratio'] = round(1.0 - 0.75 * (n_oktas / 8.0) ** 3.4, 3)
    p['sky_automated_limit_note'] = 'CLR = no cloud detected at or below 12,000 ft [7900] Table 13-5 note 1' if any(
        s['cover'] == 'CLR' for s in d.get('sky', [])) else None
    # ---- precipitation
    pr = [w for w in wx if w.get('precip') and not w.get('vicinity')]
    p['precip'] = None
    if pr:
        w0 = pr[0]
        kind = 'drizzle' if w0['precip'] == ['DZ'] else ('hail' if 'GR' in w0['precip'] or 'GS' in w0['precip'] else 'rain')
        inten = w0['intensity']
        # [7900] Table 9-4 (rain rate classes, in/h -> mm/h); drizzle intensity is visibility-based (Table 9-5).
        rate_cls = {'light': (0.1, 2.54), 'moderate': (2.8, 7.62), 'heavy': (7.62, 25.0)}[inten or 'moderate']
        rate = None
        hp = d['rmk'].get('precip_hourly_in')
        if hp:
            # Prrrr = amount since the last METAR ([7900] 13.46). KSFO routine METARs are issued at hh:56 (observed in
            # every routine report 2016-2026), so a SPECI at hh:mm covers (mm - 56) mod 60 minutes.
            mins = 60
            if d.get('time') and d['time']['minute'] != routine_minute:
                mins = (d['time']['minute'] - routine_minute) % 60 or 60
            rate = hp * 25.4 * 60.0 / mins
        if rate is None:
            rate = math.sqrt(max(rate_cls[0], 0.1) * rate_cls[1]) if kind != 'drizzle' else 0.25   # INFERRED mid-class
        lam = 4.1 * rate ** -0.21            # Marshall-Palmer slope, per mm of diameter [GN07]: 8200 h^-0.21 per m of radius
        n0 = 8000.0                          # m^-3 mm^-1
        p['precip'] = {'kind': kind, 'intensity': inten, 'showery': w0['descriptor'] == 'SH',
                       'thunder': w0['descriptor'] == 'TS', 'rate_mm_h': round(rate, 2),
                       'rate_basis': 'Prrrr remark' if hp else 'intensity class midpoint (INFERRED)',
                       'drops_per_m3_gt_0p5mm': round(n0 / lam * math.exp(-lam * 0.5), 0) if kind == 'rain' else None,
                       'median_volume_diameter_mm': round(3.67 / lam, 2) if kind == 'rain' else 0.3,
                       'fall_speed_m_s': round(200.0 * math.sqrt(3.67 / lam / 2 / 1000.0), 2) if kind == 'rain' else 1.0}
    # ---- wetness (INFERRED state machine inputs; the renderer integrates over time)
    evs = d['rmk'].get('wx_events', [])
    p['surface'] = {'precip_now': bool(pr),
                    'precip_ended_this_hour': any(e['event'] == 'end' and e['wx'] != 'TS' for e in evs),
                    'precip_since_last_metar_in': d['rmk'].get('precip_hourly_in'),
                    'precip_3or6h_in': d['rmk'].get('precip_3or6h_in')}
    # ---- wind / windsock
    w = d.get('wind') or {}
    spd = w.get('speed_kt') or 0.0
    ext = 0.0 if spd < 3 else min(1.0, (spd - 3.0) / 12.0)       # INFERRED linear 3->15 kt; endpoints [AC27F]
    p['wind'] = {'from_true_deg': w.get('dir_true_deg'), 'speed_m_s': spd * KT_MS,
                 'gust_m_s': (w['gust_kt'] * KT_MS) if w.get('gust_kt') else None,
                 'variable': w.get('variable', False), 'range_deg': (w.get('var_from'), w.get('var_to')) if w.get('var_from') is not None else None,
                 'windsock_extension': round(ext, 3), 'windsock_full_at_kt': 15, 'windsock_moves_at_kt': 3,
                 'peak_since_last_metar_kt': d['rmk'].get('peak_wind', {}).get('speed_kt')}
    # ---- lightning ([7900] Table 13-7 frequency: OCNL < 1/min, FRQ 1-6/min, CONS > 6/min)
    lt = d['rmk'].get('lightning', [])
    ts_here = any(w.get('descriptor') == 'TS' and not w.get('vicinity') for w in wx)
    ts_vc = any(w.get('descriptor') == 'TS' and w.get('vicinity') for w in wx)
    rate_map = {'OCNL': 0.5, 'FRQ': 3.5, 'CONS': 8.0}
    p['lightning'] = {'at_station': ts_here, 'vicinity': ts_vc,
                      'flashes_per_min': max([rate_map.get(x['frequency'], 0.5) for x in lt] or [0.5 if (ts_here or ts_vc) else 0.0]),
                      'reports': lt}
    p['flight_category'] = d.get('flight_category')
    return p


# ----------------------------------------------------------------------------------------------------------- CLI
def _fetch():
    import urllib.request
    ua = 'sfo3d-weather-research/0.1 (tools/env/metar_decode.py)'
    res = {}
    for kind, url in (('metar', 'https://aviationweather.gov/api/data/metar?ids=KSFO&format=raw&hours=2'),
                      ('taf', 'https://aviationweather.gov/api/data/taf?ids=KSFO&format=raw')):
        req = urllib.request.Request(url, headers={'User-Agent': ua})
        with urllib.request.urlopen(req, timeout=20) as f:
            res[kind] = f.read().decode().strip()
    return res


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--fetch' in sys.argv:
        r = _fetch()
        line = r['metar'].splitlines()[0]
        print(line)
        print(json.dumps(decode_metar(line, datetime.now(timezone.utc)), indent=1))
        print(json.dumps(decode_taf(r['taf']), indent=1))
    for a in args:
        d = decode_metar(a, datetime.now(timezone.utc))
        print(json.dumps(render_params(d, night='--night' in sys.argv) if '--render' in sys.argv else d, indent=1, default=str))
