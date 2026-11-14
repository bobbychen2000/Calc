"""Sensitive-feature rule for OSM data around ZSSS (docs/PLAN.md s.6b Q3 default; law.md: PRC Public Map Content
Specification 2023 items 20-21 and the surveying secret catalogue). Features matching it are DROPPED from anything we
publish, never drawn and never labelled; reports give counts only, never ids, names or positions.

Classes (PLAN s.6b): military, armed police, police, prison / detention, GNSS / geodetic stations.

Library (stdlib only):
    sensitive_reason(tags) -> None or a class string ('military', 'armed_police', 'police', 'prison', 'gnss')
Rules:
  * tags: landuse=military; any military=*; usage=military; operator:type=military; building in (military, barracks,
    bunker); aeroway=military; amenity in (police, prison); office=police; any police=*; man_made=surveillance
    (cameras: public-security infrastructure, dropped conservatively and counted as police); building=prison;
    man_made=survey_point (all geodetic marks); man_made=monitoring_station with any monitoring:gnss* tag; any key
    starting with gnss.
  * names (name, name:*, official_name, alt_name, old_name, short_name, operator, brand), except on linear transport
    and water features (highway / railway / waterway / route / public_transport relations), whose names say nothing
    about a facility: Chinese terms for army units, armed police, police, detention and state security, GNSS reference
    stations; English whole words (police, prison, jail, military, army, armed police, detention, GNSS, CORS; "PLA"
    case-sensitive).
  Fire stations are civil since 2018 (Ministry of Emergency Management) and are kept.
CLI (local inspection only; prints ids, never commit its output):
    python3 -I tools/law/osm_sensitive.py FILE.osm [FILE2.osm ...]
"""
import re
import sys

_ZH = re.compile(r'部队|武警|公安|警察|派出所|警务|警署|监狱|看守所|拘留所|戒毒所|劳教|劳改|边防|国家安全|国安|军事|军营|军区|'
                 r'营区|解放军|军分区|武装部|基准站|参考站|卫星定位|北斗基站|CORS')
_EN = re.compile(r'\b(police|prison|jail|military|army|armed police|detention|gnss|cors)\b', re.I)
_PLA = re.compile(r'\bPLA\b')
_NAME_KEYS = ('name', 'official_name', 'alt_name', 'old_name', 'short_name', 'operator', 'brand')
_LINEAR = ('highway', 'railway', 'waterway')


def _named(tags):
    for k, v in tags.items():
        if not v or not (k in _NAME_KEYS or k.startswith('name:')):
            continue
        if _ZH.search(v) or _EN.search(v) or _PLA.search(v):
            return True
    return False


def sensitive_reason(tags):
    """None if the OSM tag dict is not sensitive, else the class."""
    t = tags
    if (t.get('landuse') == 'military' or 'military' in t or t.get('usage') == 'military'
            or t.get('operator:type') == 'military' or t.get('building') in ('military', 'barracks', 'bunker')
            or t.get('aeroway') == 'military'):
        name = ' '.join(v for k, v in t.items() if k.startswith('name') or k == 'operator')
        return 'armed_police' if '武警' in name or 'armed police' in name.lower() else 'military'
    if t.get('amenity') == 'police' or t.get('office') == 'police' or 'police' in t or t.get('man_made') == 'surveillance':
        return 'police'
    if t.get('amenity') == 'prison' or t.get('building') == 'prison':
        return 'prison'
    if t.get('man_made') == 'survey_point' or any(k.startswith('gnss') for k in t) or (
            t.get('man_made') == 'monitoring_station' and any(k.startswith('monitoring:gnss') for k in t)):
        return 'gnss'
    linear = any(k in t for k in _LINEAR) or t.get('type') in ('route', 'route_master', 'public_transport')
    if not linear and _named(t):
        s = ' '.join(v for k, v in t.items() if k in _NAME_KEYS or k.startswith('name:'))
        if '武警' in s or 'armed police' in s.lower():
            return 'armed_police'
        if re.search(r'公安|警察|派出所|警务|警署|police', s, re.I):
            return 'police'
        if re.search(r'监狱|看守所|拘留所|戒毒所|劳教|劳改|prison|jail|detention', s, re.I):
            return 'prison'
        if re.search(r'基准站|参考站|卫星定位|北斗基站|CORS|gnss', s, re.I):
            return 'gnss'
        return 'military'
    return None


if __name__ == '__main__':
    import math
    import xml.etree.ElementTree as ET
    ARP = (31.19784885, 121.3362899)   # scene origin (OD0)
    for path in sys.argv[1:]:
        root = ET.parse(path).getroot()
        nodes = {n.get('id'): (float(n.get('lat')), float(n.get('lon'))) for n in root.iter('node') if n.get('lat')}
        for el in root:
            if el.tag not in ('node', 'way', 'relation'):
                continue
            tags = {t.get('k'): t.get('v') for t in el.findall('tag')}
            why = sensitive_reason(tags)
            if not why:
                continue
            pts = ([nodes[nd.get('ref')] for nd in el.findall('nd') if nd.get('ref') in nodes] if el.tag == 'way'
                   else [nodes[el.get('id')]] if el.tag == 'node' else [])
            c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
            d = (math.hypot((c[0] - ARP[0]) * 110857, (c[1] - ARP[1]) * 95334) / 1000) if c else None
            print(why, el.tag, el.get('id'), f'{d:.2f} km from origin' if d is not None else 'no geometry')
