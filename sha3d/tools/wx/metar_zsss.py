"""ICAO METAR / SPECI decoder for ZSSS (Shanghai Hongqiao), with the trend part kept apart, plus the runway-direction rule.

Stdlib only. Written for SHA Live 3D Phase 1 (task B2, docs/phase1/sources_sim.md); a JS twin is a Phase 2 job.

Why a new decoder: ZSSS reports are ICAO-style (wind in MPS, visibility in metres, Q-group QNH in hPa, half-hourly
routine reports) and almost every report ends in a trend forecast ("NOSIG", "BECMG TL0340 BKN011", "TEMPO ..."). The
sfo3d decoder (js/env/wx/metar.js, read only) cuts the report only at RMK, so the trend's cloud groups are added to the
observed sky ("BKN006 ... BECMG TL0340 BKN011" decodes as two observed layers, BKN006 and BKN011): measured with node in
task B2. Here the body ends at the first NOSIG / BECMG / TEMPO / RMK token and the trend is decoded separately.

Units: the report units are kept (m/s, metres, hPa) and knots are derived (1 kt = 1852/3600 m/s exactly).
Wind direction in METAR is degrees TRUE (ICAO Annex 3); runway headings below are TRUE too.

Usage:
    python3 -I tools/wx/metar_zsss.py "<raw METAR>" ...        # prints the decoded JSON
"""
import json, math, re, sys

KT_MS = 1852.0 / 3600.0

# Runway true headings from OSM way bearings / AIP AD 2.12 (mirror): 18L/36R 177.34 deg, 18R/36L 177.33 deg.
RWY_TRUE = {'18': 177.34, '36': 357.34}

WX_RE = re.compile(r'^(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)*)$')
TREND_START = ('NOSIG', 'BECMG', 'TEMPO')


def _wind(tok):
    m = re.fullmatch(r'(\d{3}|VRB|///)(\d{2,3}|//)(?:G(\d{2,3}))?(MPS|KT)', tok)
    if not m:
        return None
    to_ms = 1.0 if m.group(4) == 'MPS' else KT_MS
    spd = None if m.group(2) == '//' else int(m.group(2)) * to_ms
    w = {'raw': tok, 'unit': m.group(4), 'dir_true_deg': None if m.group(1) in ('VRB', '///') else int(m.group(1)),
         'variable': m.group(1) == 'VRB', 'speed_ms': spd, 'gust_ms': int(m.group(3)) * to_ms if m.group(3) else None}
    w['calm'] = spd == 0.0
    w['speed_kt'] = None if spd is None else round(spd / KT_MS, 1)
    return w


def _sky(tok):
    m = re.fullmatch(r'(FEW|SCT|BKN|OVC)(\d{3}|///)(CB|TCU|///)?', tok)
    if m:
        return {'cover': m.group(1), 'base_ft': None if m.group(2) == '///' else int(m.group(2)) * 100,
                'type': m.group(3) if m.group(3) not in (None, '///') else None}
    m = re.fullmatch(r'VV(\d{3}|///)', tok)
    if m:
        return {'cover': 'VV', 'base_ft': None if m.group(1) == '///' else int(m.group(1)) * 100, 'type': None}
    if tok in ('NSC', 'NCD', 'SKC', 'CLR'):
        return {'cover': tok, 'base_ft': None, 'type': None}
    return None


def _wx(tok):
    if tok == 'NSW':
        return {'raw': tok, 'nsw': True}
    m = WX_RE.fullmatch(tok)
    if not m or not (m.group(3) or m.group(2) == 'TS'):
        return None
    return {'raw': tok, 'intensity': {'-': 'light', '+': 'heavy', 'VC': 'vicinity'}.get(m.group(1), 'moderate'),
            'descriptor': m.group(2), 'phenomena': [m.group(3)[k:k + 2] for k in range(0, len(m.group(3)), 2)]}


def _elements(tokens, out):
    """Decode wind / visibility / RVR / weather / sky / T/Td / QNH groups (shared by the body and trend groups)."""
    i = 0
    while i < len(tokens):
        t = tokens[i]
        w = _wind(t)
        if w and 'wind' not in out:
            out['wind'] = w; i += 1; continue
        m = re.fullmatch(r'(\d{3})V(\d{3})', t)
        if m and 'wind' in out:
            out['wind']['var_from'], out['wind']['var_to'] = int(m.group(1)), int(m.group(2)); i += 1; continue
        if t == 'CAVOK':
            out['cavok'] = True; out['vis_m'] = 10000; out['vis_ge'] = True; i += 1; continue
        m = re.fullmatch(r'(\d{4})(NDV)?', t)
        if m and 'vis_m' not in out:
            v = int(m.group(1)); out['vis_m'] = v; out['vis_ge'] = v == 9999
            if v == 9999: out['vis_m'] = 10000
            i += 1; continue
        m = re.fullmatch(r'(\d{4})(N|NE|E|SE|S|SW|W|NW)', t)
        if m and 'vis_m' in out:
            out.setdefault('vis_min', []).append({'m': int(m.group(1)), 'dir': m.group(2)}); i += 1; continue
        m = re.fullmatch(r'R(\d{2}[LRC]?)/([PM]?\d{4})(?:V([PM]?\d{4}))?([UDN])?', t)
        if m:
            out.setdefault('rvr', []).append({'rwy': m.group(1), 'm': m.group(2), 'var': m.group(3), 'tend': m.group(4)})
            i += 1; continue
        m = re.fullmatch(r'(M?\d{2})/(M?\d{2})?', t)
        if m and 'temp_c' not in out:
            c = lambda s: None if s is None else (-int(s[1:]) if s.startswith('M') else int(s))
            out['temp_c'], out['dew_c'] = c(m.group(1)), c(m.group(2)); i += 1; continue
        m = re.fullmatch(r'Q(\d{4})', t)
        if m:
            out['qnh_hpa'] = int(m.group(1)); i += 1; continue
        m = re.fullmatch(r'A(\d{4})', t)
        if m:
            out['qnh_hpa'] = round(int(m.group(1)) / 100 * 33.8639, 1); out['qnh_from_inhg'] = True; i += 1; continue
        s = _sky(t)
        if s:
            out.setdefault('sky', []).append(s); i += 1; continue
        x = _wx(t)
        if x:
            out.setdefault('wx', []).append(x); i += 1; continue
        if t.startswith('RE'):
            out.setdefault('recent_wx', []).append(t[2:]); i += 1; continue
        if t == 'WS' and i + 1 < len(tokens):
            out.setdefault('windshear', []).append(' '.join(tokens[i:i + 3])); i += 3; continue
        out.setdefault('unparsed', []).append(t); i += 1
    return out


def split_report(raw):
    """-> (head+body tokens, trend tokens, rmk text). Body ends at the first NOSIG/BECMG/TEMPO or RMK."""
    toks = raw.replace('=', ' ').split()
    rmk = ''
    if 'RMK' in toks:
        k = toks.index('RMK'); rmk = ' '.join(toks[k + 1:]); toks = toks[:k]
    for k, t in enumerate(toks):
        if t in TREND_START:
            return toks[:k], toks[k:], rmk
    return toks, [], rmk


def decode(raw):
    body, trend, rmk = split_report(raw.strip())
    out = {'raw': raw.strip()}
    i = 0
    if body and body[0] in ('METAR', 'SPECI'):
        out['type'] = body[0]; i = 1
    else:
        out['type'] = 'METAR'
    if i < len(body) and body[i] == 'COR':
        out['cor'] = True; i += 1
    out['station'] = body[i]; i += 1
    m = re.fullmatch(r'(\d{2})(\d{2})(\d{2})Z', body[i]) if i < len(body) else None
    if m:
        out['day'], out['hour'], out['minute'] = int(m.group(1)), int(m.group(2)), int(m.group(3)); i += 1
    if i < len(body) and body[i] in ('AUTO', 'NIL'):
        out[body[i].lower()] = True; i += 1
    _elements(body[i:], out)
    out['trend'] = decode_trend(trend)
    if rmk:
        out['rmk'] = rmk
    return out


def decode_trend(tokens):
    """ICAO Annex 3 trend: NOSIG, or one or more BECMG/TEMPO groups with FMhhmm / TLhhmm / AThhmm and elements."""
    groups, cur = [], None
    for t in tokens:
        if t == 'NOSIG':
            groups.append({'kind': 'NOSIG'}); cur = None; continue
        if t in ('BECMG', 'TEMPO'):
            cur = {'kind': t, 'elements_raw': []}; groups.append(cur); continue
        if cur is None:
            continue
        m = re.fullmatch(r'(FM|TL|AT)(\d{4})', t)
        if m:
            cur[m.group(1).lower()] = m.group(2); continue
        cur['elements_raw'].append(t)
    for g in groups:
        if g['kind'] != 'NOSIG':
            g['elements'] = _elements(g.pop('elements_raw'), {})
    return groups


def components(wind, rwy):
    """Head- (+) and cross-wind (+ from the right) components in m/s on runway direction '18' or '36'.
    Variable / missing direction -> None."""
    if not wind or wind.get('dir_true_deg') is None or wind.get('speed_ms') is None:
        return None
    a = math.radians(wind['dir_true_deg'] - RWY_TRUE[rwy])
    spd = wind['speed_ms']
    return spd * math.cos(a), spd * math.sin(a)


class RunwayDirection:
    """Inferred runway-direction rule for ZSSS (both runways always run the same way; close parallels).

    AIP (mirror) AD 2.20 2.1.2: "During changing the direction of RWY in use, if downwind speed is more than 3m/s and
    not exceeding 5m/s, ATC may instruct aircraft downwind take-off or downwind landing for short time." That is the
    tolerance DURING a change, not the trigger for one.
    Model [inf]: keep the current direction while its tailwind component (gusts included) is <= TAIL_KEEP_MS; when it
    exceeds TAIL_KEEP_MS in two consecutive reports, or exceeds TAIL_MAX_MS once, turn round. Calm or VRB keeps the
    current direction. Defaults 1.5 / 4.0 m/s were calibrated in task B2 against the only observed hint of the runway
    in use, the runway designators of RVR and windshear groups in ZSSS METARs 2023-2026 (169 reports on 60 days;
    tools/wx/rule_check_rvr.py, rule stepped on every METAR and SPECI): 86.4 % agreement, against 65.1 % for a
    3 / 5 m/s reading of the AIP text and 80.5 % for "always into the wind". The starting direction is a parameter (default '36'; no preferred direction is
    published).
    """
    TAIL_KEEP_MS = 1.5
    TAIL_MAX_MS = 4.0

    def __init__(self, start='36'):
        self.dir = start
        self.pending = 0

    def step(self, wind):
        c = components(wind, self.dir)
        if c is None:
            self.pending = 0
            return self.dir, 'keep (calm/VRB/missing)'
        head = c[0]
        if wind.get('gust_ms'):
            head = min(head, wind['gust_ms'] * math.cos(math.radians(wind['dir_true_deg'] - RWY_TRUE[self.dir])))
        tail = -head
        if tail > self.TAIL_MAX_MS or (tail > self.TAIL_KEEP_MS and self.pending >= 1):
            self.dir = '18' if self.dir == '36' else '36'
            self.pending = 0
            return self.dir, f'change (tailwind {tail:.1f} m/s)'
        if tail > self.TAIL_KEEP_MS:
            self.pending += 1
            return self.dir, f'keep, tailwind {tail:.1f} m/s (1st report > {self.TAIL_KEEP_MS})'
        self.pending = 0
        return self.dir, 'keep'


if __name__ == '__main__':
    for r in sys.argv[1:]:
        print(json.dumps(decode(r), ensure_ascii=False))
