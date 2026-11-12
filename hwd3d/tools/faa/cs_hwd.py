#!/usr/bin/env python3
"""Transcribe the HWD entry of the FAA Chart Supplement (d-CS, Southwest volume) and cross-check docs/PLAN.md section 1.

New for hwd3d (task G3a, 2026-11-12); no sfo3d counterpart.

Inputs (all in refs/cache/faa/, US Government works, public domain; see SOURCES.json there):
  sw_174_29OCT2026.pdf                      the HWD entry, pages 174-175 "CALIFORNIA", cycle 29 OCT 2026 to 24 DEC 2026,
                                            found with the FAA d-CS search
                                            https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dafd/search/results/?cycle=2611&ident=HWD
  cs_sw_front_29oct2026_legend_p15-26.pdf   legend pages used to read the symbols (SW_front_29oct2026.pdf p. 15, 16, 18, 20,
                                            21, 22, 26). Its text layer uses a shifted font encoding (+29); decoded below.
  cs_sw_hotspot_29oct2026_p2.pdf            the SW hot spot list page that holds HWD HS 1-HS 5
Method: the text layer of the PDFs (pypdf), not OCR. Printed lines that wrap are joined into one logical line; runs of
spaces are collapsed; two text-layer artefacts are corrected to match the printed page, which was checked line by line
against a 300 dpi render (pdftoppm) on 2026-11-12: a missing space between a bold label and its value ("CON124.4" is
printed "CON 124.4", "DEL128.05" is "DEL 128.05") and the radar symbol printed in the left margin before "NORCAL"
("®NORCAL" -> "® NORCAL"). The right-hand column (charts) is kept apart in 'chart_refs'. Characters are those of the
text layer: º (U+00BA) for degrees, ´ (U+00B4) for feet/minutes, – en dash, — em dash, ‡, ®.
Checks (the script stops if one fails): every transcribed line occurs in the whitespace-free page text; every
'cs' quote of the cross-check occurs in the transcription; every legend quote occurs in the decoded legend text.

Output: refs/cache/faa/chart_supplement_HWD.json
usage: python3 -I hwd3d/tools/faa/cs_hwd.py
"""
import hashlib
import json
import os
import re
import sys

import pypdf

HERE = os.path.dirname(os.path.abspath(__file__))
HWD = os.path.normpath(os.path.join(HERE, '..', '..'))
FAA = os.path.join(HWD, 'refs', 'cache', 'faa')
ENTRY = os.path.join(FAA, 'sw_174_29OCT2026.pdf')
LEGEND = os.path.join(FAA, 'cs_sw_front_29oct2026_legend_p15-26.pdf')
HOT = os.path.join(FAA, 'cs_sw_hotspot_29oct2026_p2.pdf')
OUT = os.path.join(FAA, 'chart_supplement_HWD.json')

STARTS = re.compile(r'^(HAYWARD EXEC|52 B|RWY |SERVICE:|NOISE:|AIRPORT REMARKS:|AIRPORT MANAGER:|WEATHER DATA SOURCES:|'
                    r'COMMUNICATIONS:|®|TOWER |CLEARANCE DELIVERY PHONE:|AIRSPACE:|RADIO AIDS TO NAVIGATION:|OAKLAND|'
                    r'DME unusable:|VOR unusable:|\d{3}º–\d{3}º|LOC/DME)')
CHART_REFS = ['SAN FRANCISCO', 'H–3B, L–2F, 3B, A', 'IAP, AD']   # right-hand column of the HWD block (render)

# legend quotes: (legend PDF page as printed in the source file, text that must occur in the decoded legend)
LEGEND_QUOTES = {
    '‡': ('SW_front p.15 (printed 14), item 6 TIME CONVERSION',
          'indicates that during periods of Daylight Saving Time (DST) effective hours will be one hour earlier than shown'),
    '®': ('SW_front p.26 (printed 25), item 29 COMMUNICATIONS', 'APP CON³Approach Control. The symbol'),
    '® (meaning)': ('SW_front p.26 (printed 25)', 'indicates radar approach control'),
    '2 W': ('SW_front p.15 (printed 14), item 5 AIRPORT LOCATION',
            'Airport location is expressed as distance and direction from the center of the associated city in nautical miles'),
    'B': ('SW_front p.16, ROTATING LIGHT BEACON', 'B indicates rotating beacon is available. Rotating beacons operate sunset to sunrise unless otherwise indicated'),
    'TPA': ('SW_front p.16, TRAFFIC PATTERN ALTITUDE', 'The first figure shown is TPA above mean sea level. The second figure in parentheses is TPA above airport'),
    '2S': ('SW_front p.18, RUNWAY WEIGHT BEARING CAPACITY', 'ST=2S=Two single wheels in tandem type landing gear (C130)'),
    'strength units': ('SW_front p.18', 'Runway strength'),
    'gradient': ('SW_front p.20, RUNWAY GRADIENT', 'Runway slope will be shown only when it is 0.3 percent or greater'),
    'S4': ('SW_front p.21, SERVICE', 'S4:=Major airframe and major powerplant repairs.'),
    'OX 1, 3': ('SW_front p.22, OXYGEN', 'OX 1=High Pressure=OX 3=High Pressure³Replacement Bottles'),
}
# the legend uses a glyph the shift maps oddly for ‡ and ®; their own text is checked visually (render), the
# surrounding words above by text.

# Cross-check of every row of docs/PLAN.md section 1 (as committed in 254e7f7). verdict: agree | differs | partial |
# not_in_cs. 'cs' = quote that must occur in the transcription.
XCHECK = [
    ('Identity', 'LID HWD, ICAO KHWD, "HAYWARD EXEC", Hayward, Alameda County, CA; public use, City of Hayward; 1947/05',
     'HAYWARD EXEC (HWD)(KHWD) 2 W', 'partial',
     'Name, LID and ICAO agree. The CS gives the location as 2 NM W of the city (legend: nautical miles; NASR '
     'DIST_CITY_TO_AIRPORT 2, W). County, ownership and activation date are not in the CS entry.'),
    ('ARP', '37.65893166 N, -122.12173888 E', 'N37º39.54´ W122º07.30´', 'agree',
     'NASR 37-39-32.154 N = 39.536´ and 122-07-18.26 W = 07.304´ round to the CS values (0.01´ = 18 m).'),
    ('Field elevation', '52.1 ft (diagram 52)', '52 B TPA—See Remarks', 'agree', 'CS 52 ft.'),
    ('Magnetic variation', '15° E (epoch 2005)', None, 'not_in_cs',
     'The airport entry has no variation. "13/17E" on the OAKLAND VOR/DME line is that NAVAID\'s elevation and '
     'variation, not the airport\'s.'),
    ('Runway 10R/28L', '5,694 x 150 ft, asphalt, grooved, MIRL, S-30 / D-75, PIR marking, true 120°/300°',
     'RWY 10R–28L: H5694X150 (ASPH–GRVD) S–30, D–75, 2S–95 MIRL 0.4% up E', 'partial',
     'Length, width, surface, grooving, MIRL, S-30 and D-75 agree. The CS adds 2S-95 (two single wheels in tandem, '
     '95,000 lb; absent from the NASR extract and from the PLAN) and the gradient 0.4% up E. Marking type and true '
     'alignment are not in the CS.'),
    ('10R end', 'displaced threshold 826 ft; VASI V4R 3.0°, TCH 25 ft; REIL; coordinates, elev 27.7',
     'RWY 10R: REIL. VASI(V4R)—GA 3.0º TCH 25´. Thld dsplcd 826´. Tree. Rgt tfc.', 'agree',
     'All stated items agree; the CS adds the controlling obstacle "Tree" (NASR OBSTN_TYPE TREE). Coordinates and '
     'elevations are not in the CS.'),
    ('28L end', 'displaced threshold 676 ft; VASI V4L 4.0°, TCH 35 ft; LOC/DME; REIL',
     'RWY 28L: REIL. VASI(V4L)—GA 4.0º TCH 35´. Thld dsplcd 676´.', 'agree',
     'LOC/DME confirmed on the NAVAID line: "LOC/DME 111.5 I–HWD Chan 52 Rwy 28L. Localizer offset angle 3.00 deg. '
     'LOC unmonitored when ATCT clsd."'),
    ('Runway 10L/28R', '3,108 x 75 ft, asphalt, MIRL, S-13, NPI marking', 'RWY 10L–28R: H3108X75 (ASPH) S–13 MIRL 0.3% up SE',
     'partial', 'All stated items agree except the marking, which the CS does not give. The CS adds the gradient 0.3% up SE.'),
    ('10L end', 'PAPI P4L 3.0°, TCH 29 ft; left-hand traffic', 'RWY 10L: PAPI(P4L)—GA 3.0º TCH 29´. Tree.', 'agree',
     'No "Rgt tfc" on the 10L line, so the pattern is left-hand. The CS adds "Tree".'),
    ('28R end', 'PAPI P4L 3.0°, TCH 44 ft; right-hand traffic', 'RWY 28R: PAPI(P4L)—GA 3.0º TCH 44´. Rgt tfc.', 'agree', ''),
    ('Traffic pattern', '10R RH; 10L and 28L LH; 28R RH. TPA 600 ft AGL, 800 ft AGL for 10L/28R',
     'TPA—652(600) Rwy 10R–28L, 852(800) Rwy 10L–28R.', 'agree',
     'TPA 652 ft MSL (600 AGL) and 852 ft MSL (800 AGL); "Rgt tfc" only on 10R and 28R.'),
    ('Tower', 'FAA ATCT, call HAYWARD, hours 0700-2100 local; tower closed: 10L/28R closed, CTAF 120.2, MIRL 10R/28L preset low',
     'TOWER 120.2 118.9 (1500–0500Z‡)', 'agree',
     '1500-0500Z = 0700-2100 PST (UTC-8); with ‡ (legend: one hour earlier during DST) 1400-0400Z = 0700-2100 PDT. '
     'So 0700-2100 local all year. Also confirmed: "When tower clsd Rwy 10L–28R CLOSED", "CTAF 120.2", "When twr clsd '
     'MIRL Rwy 10R–28L preset low ints, to increase ints ACTIVATE—CTAF". The PLAN omits that, with the tower closed, '
     'VASI 10R/28L run sunset to sunrise and PAPI 10L, PAPI 28R and REIL 10R/28L are unavailable, and the LOC is '
     'unmonitored. Operator (FAA) and call sign are not stated in the CS.'),
    ('Frequencies', 'TWR 120.2 (P, CTAF) and 118.9 (S; "NASR only, not on the diagram"), 257.8 UHF; GND 121.4; CD 128.05; '
     'ATIS 126.7 (24 h, 510-786-3988); UNICOM 122.95; NorCal 124.4 (P), 125.35, 134.5',
     'COMMUNICATIONS: CTAF 120.2 ATIS 126.7 510–786–3988 UNICOM 122.95', 'differs',
     'VHF agree: TOWER 120.2 118.9, GND CON 121.4, CLNC DEL 128.05, NORCAL APP CON 124.4 125.35 134.5 (® = radar '
     'approach control), NORCAL DEP CON 124.4. Differences: (1) 118.9 is printed in the CS, so "NASR only" in the '
     'PLAN is wrong - it is missing only from the diagram; (2) the UHF 257.8 (NASR LCL/P) is not in the CS; '
     '(3) ATIS hours are not in the CS (NASR ATIS_HRS 24).'),
    ('Surface ADS-B', 'SAID in use ...', 'SAID in use. Operate transponders with altitude reporting mode and ADS–B (if '
     'equipped) enabled on all airport surfaces.', 'agree', 'Same text in the CS airport remarks.'),
    ('Taxiways on diagram', 'A, A1, B, C, D, E, F, Z, Z1; Z1 > 94 ft and A1 > 100 ft wingspan closed; Twy A not visible '
     'from ATCT between B and C', 'Twy A not visible from twr between Twy B and Twy C. Twy A1 clsd to acft with wingspan '
     'greater than 100´. Twy Z1 clsd to acft with wingspan greater than 94´.', 'agree',
     'Restrictions agree. The full taxiway list is a diagram fact (AL-5015), not in the CS entry.'),
    ('Hot spots', 'HS 1-HS 5 on the diagram', None, 'not_in_cs',
     'Not in the airport entry; the SW hot spot list (cs_sw_hotspot_29oct2026_p2.pdf) has HWD HS 1-HS 5 with '
     'descriptions, transcribed in "hot_spots" below.'),
    ('Named areas', 'West/East Hangars, FBO ramps, GA Transient Ramp, Terminal/Admin, TWR, Fire Station, 28L Run-up', None,
     'not_in_cs', 'Diagram facts. The CS only names the "green ramp" and the tower (helicopter remark).'),
    ('Helicopters', 'Transient helicopter TFC use helipads west of Green Ramp lctd at base of ATCT',
     'Transient helicopter tfc use helipads west of green ramp located at base of twr.', 'agree', ''),
    ('Other remarks', 'lighted distance-remaining signs 10R north, 28L south; 155-ft stack 1.5 NM SW, no overflight below '
     '1,000 MSL; noise abatement; beacon WG SS-SR; segmented circle, lighted windsock',
     'Rwy 10R has ldg distance remaining signs (lgtd) north side of rwy. Rwy 28L has ldg distance remaining signs (lgtd) '
     'south side of rwy.', 'partial',
     'Signs, stack ("155´ energy complex exhaust stack 1.5 NM southwest of arpt. Do not overfly energy complex facility '
     'below 1,000´ MSL.") and noise ("Noise abatement procedures in effect ctc arpt for noise rules 510–293–8669.") '
     'agree; the CS says *landing* distance remaining signs. Beacon: the CS shows "B" (rotating beacon, legend: '
     'operates sunset to sunrise) but not its colours. Segmented circle and windsock are not in the CS.'),
    ('Fuel and services', '100LL, Jet A, UL94 (self-serve island); major airframe and powerplant repair; charter, '
     'instruction, rental; transient tie-downs', 'SERVICE: S4 FUEL 100LL, JET A, UL94 OX 1, 3', 'partial',
     'Fuel agrees ("UL94 fuel avbl at self–serve island"). S4 = major airframe and major powerplant repairs (legend) '
     'agrees with NASR MAJOR/MAJOR. The CS adds oxygen OX 1, 3 (high pressure; high-pressure replacement bottles). '
     'Charter/instruction/rental and transient tie-downs are not in the CS.'),
    ('ADS-B recordings cover HWD', 'rec_pack within 25 nm of SFO', None, 'not_in_cs', 'Not an FAA fact.'),
]
CS_ONLY = [   # facts in the CS entry that docs/PLAN.md section 1 does not have
    ('Attended 1600–0100Z‡', 'airport attended 0800-1700 local all year (NASR APT_ATT 0800-1700 agrees)'),
    ('AIRSPACE: CLASS D svc 1500–0500Z‡; other times CLASS E.', 'Class D with the tower hours, Class E otherwise'),
    ('CLEARANCE DELIVERY PHONE: For CD when ATCT is clsd ctc NorCal Apch at 916-361-0516.', ''),
    ('Flocks of birds feeding along the shoreline, creek areas and at the golf course to the north', 'bird remark'),
    ('WEATHER DATA SOURCES: ASOS (510) 786–3052', 'ASOS on field'),
    ('AIRPORT MANAGER: (510) 293-8678', ''),
    ('OAKLAND (VH) (DH) VORW/DME 116.8 OAK Chan 115 N37º43.56´ W122º13.42´ 113º 6.3 NM to fld.', 'OAK VOR/DME 6.3 NM'),
    ('UTC–8(–7DT)', 'time zone'),
    ('NOTAM FILE HWD', ''),
]


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def squash(s):
    return re.sub(r'\s+', '', s)


def logical_lines(raw):
    out = []
    for ln in raw.split('\n'):
        ln = re.sub(r'\s+', ' ', ln).strip()
        if not ln:
            continue
        if STARTS.match(ln) or not out:
            out.append(ln)
        else:
            out[-1] += ' ' + ln
    fix = lambda s: re.sub(r'^® ?', '® ', re.sub(r'\b(CON|DEL)(\d)', r'\1 \2', s))
    return [fix(s) for s in out]


def main():
    pages = [p.extract_text() for p in pypdf.PdfReader(ENTRY).pages]
    assert len(pages) == 2 and pages[0].startswith('174 CALIFORNIA'), pages[0][:40]
    p1, p2 = pages
    a = p1.index('HAYWARD EXEC (HWD)(KHWD)')
    b = p1.index('CONTINUED ON NEXT PAGE', a)
    c = p2.index('AIRSPACE:')
    d = p2.index('LOC unmonitored when ATCT clsd.') + len('LOC unmonitored when ATCT clsd.')
    lines = logical_lines(p1[a:b]) + logical_lines(p2[c:d])
    flat = squash(p1 + p2)
    for ln in lines:
        assert squash(ln) in flat, ln
    for r in CHART_REFS:
        assert r in p1.split('\n') or r in [x.strip() for x in p1.split('\n')], r
    text = '\n'.join(lines)
    norm = lambda s: re.sub(r'\s+', ' ', s)
    for row in XCHECK:
        if row[2]:
            assert norm(row[2]) in norm(text), row[2]
    for q, _ in CS_ONLY:
        assert norm(q) in norm(text), q
    # legend
    dec = lambda t: ''.join(chr(ord(ch) + 29) if 3 <= ord(ch) <= 93 else ch for ch in t)
    leg = ' '.join(dec(p.extract_text() or '') for p in pypdf.PdfReader(LEGEND).pages)
    leg = re.sub(r"\s*'\s*", ' ', leg)   # the decoded layer marks line ends with "'"
    legend = {}
    for k, (where, q) in LEGEND_QUOTES.items():
        assert norm(q) in norm(leg), (k, q)
        legend[k] = {'where': where, 'quote_decoded_text_layer': q}
    legend['‡']['meaning'] = 'during Daylight Saving Time the effective hours are one hour earlier than shown (glyph checked on the render)'
    legend['®']['meaning'] = 'radar approach control (glyph checked on the render: "APP CON—Approach Control. The symbol ® indicates radar approach control.")'
    # hot spots
    ht = pypdf.PdfReader(HOT).pages[0].extract_text()
    i, j = ht.index('HAYWARD EXEC (HWD)'), ht.index('LA VERNE')
    hs = re.split(r'\s(?=HS \d )', re.sub(r'\s+', ' ', ht[i + len('HAYWARD EXEC (HWD)'):j]).strip())
    hot = {h.split(' ', 2)[0] + ' ' + h.split(' ', 2)[1]: h.split(' ', 2)[2] for h in hs}
    assert sorted(hot) == ['HS 1', 'HS 2', 'HS 3', 'HS 4', 'HS 5'], hot
    out = {
        'source': {
            'publication': 'FAA Chart Supplement, Southwest U.S. (digital Chart Supplement, d-CS)',
            'cycle': 'SW, 29 OCT 2026 to 24 DEC 2026 (effective 0901Z 29 Oct 2026; current on 2026-11-12)',
            'index': 'https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dafd/ (current edition Oct 29 2026, next Dec 24 2026)',
            'search': 'https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dafd/search/results/?cycle=2611&ident=HWD',
            'file': {'name': os.path.basename(ENTRY), 'url': 'https://aeronav.faa.gov/afd/29oct2026/sw_174_29OCT2026.pdf',
                     'sha256': sha256(ENTRY), 'pages': 'CALIFORNIA 174-175 (HWD entry starts on 174, continues on 175)'},
            'licence': 'US Government work (FAA, 17 U.S.C. 105), public domain',
            'fetched': '2026-11-12'},
        'method': __doc__.split('Method: ')[1].split('Checks')[0].strip().replace('\n', ' '),
        'entry': {'lines': lines, 'chart_refs': CHART_REFS},
        'hot_spots': {'source': {'file': os.path.basename(HOT), 'sha256': sha256(HOT),
                                 'url': 'https://aeronav.faa.gov/afd/29oct2026/SW_hotspot.pdf (page 2 of 7)'},
                      'HWD': hot},
        'legend': {'file': os.path.basename(LEGEND), 'sha256': sha256(LEGEND),
                   'url': 'https://aeronav.faa.gov/afd/29oct2026/SW_front_29oct2026.pdf (pages 15, 16, 18, 20, 21, 22, 26)',
                   'items': legend},
        'derived': {
            'tower_hours_local': '0700-2100 all year (1500-0500Z in PST; 1400-0400Z in PDT per ‡)',
            'class_d_hours_local': '0700-2100 all year; other times Class E',
            'attended_local': '0800-1700 all year (1600-0100Z‡)',
            'tpa_ft_msl': {'10R/28L': 652, '10L/28R': 852}, 'tpa_ft_agl': {'10R/28L': 600, '10L/28R': 800},
            'right_traffic': ['10R', '28R'], 'left_traffic': ['28L', '10L'],
            'gradient': {'10R/28L': '0.4% up E', '10L/28R': '0.3% up SE'},
            'strength_klb': {'10R/28L': {'S': 30, 'D': 75, '2S': 95}, '10L/28R': {'S': 13}},
        },
        'crosscheck_plan_section1': {
            'plan': 'hwd3d/docs/PLAN.md section 1 (commit 254e7f7)',
            'rows': [{'plan_row': r[0], 'plan_value': r[1], 'cs': r[2], 'verdict': r[3], 'note': r[4]} for r in XCHECK],
            'cs_facts_not_in_plan': [{'cs': q, 'note': n} for q, n in CS_ONLY],
        },
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    v = {}
    for r in XCHECK:
        v[r[3]] = v.get(r[3], 0) + 1
    print('wrote %s: %d lines, %d hot spots, cross-check %s' % (OUT, len(lines), len(hot), v))


if __name__ == '__main__':
    sys.exit(main())
