#!/usr/bin/env python3
"""Reference photographs of the current liveries, for the render check of the baked liveries (tools/liveries/
render_blender.py) and for measuring layouts and colours where no official side view or brand guide is reachable.

REFERENCE ONLY: the photographs are downloaded to refs/cache/livref/ (gitignored) and never shipped, traced or used as
textures. Source: Wikimedia Commons (recent photographs of the aircraft type we render, in the livery we render; the
airlines' own media hosts block this sandbox). Each download records the file page, author and licence in
refs/cache/livref/index.json; tools/liveries/liveries.py cites the photos it was checked or measured against by file name
(provenance 'photo': measured on a photograph, not an official colour value).

Usage: python3 tools/liveries/ref_photos.py [BRAND ...] [--width 1600]
"""
import argparse, json, os, subprocess, sys, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'refs', 'cache', 'livref')
UA = 'sfo3d-research/1.0 (non-commercial livery reference check)'

# brand -> Commons file titles (the rendered type where a photo exists; newest first)
REFS = {
    'UAL': ['United Airlines Boeing 737-9 MAX N37545 departing Boston August 2025.jpg', 'Boeing 737 MAX 9 - United Airlines - N37440.jpg'],
    'DAL-C': ['N242SY Delta Connection Embraer ERJ-175LR (ERJ-170-200 LR) SkyWest s-n 17000588 (38880321374).jpg', 'Delta Connection E175LR N310SY IND.jpg'],
    'AAL': ['American Airlines Airbus A321 N907AA departing Boston August 2025.jpg', 'American Airbus A321 N913US BWI MD1.jpg'],
    'AAL-E': ['N515SY (55106011269).jpg', 'N521SY (53540289498).jpg'],
    'ASA': ['Alaska Airlines Boeing 737-900ER N464AS departing Boston June 2025.jpg', 'Alaska Airlines Boeing 737-900ER (N288AK) (54590451699).jpg'],
    'JBU': ['JetBlue Airways Airbus A321 N954JB departing Boston December 2025.jpg', 'N982JB JFK Taxiing To Active 22R B6 A321 231 A Defining MoMint Small (52979273471).png'],
    'WJA': ['C-FNWD - Boeing 737 MAX 8 - WestJet LIR 260225.jpg', 'C-GPFT Boeing 737 Max 8 Westjet LGW 20.5.24 (53734026042).jpg'],
    'AMX': ['Aeroméxico Boeing 737-8 MAX XA-DAE on final approach to Boston July 2025.jpg', 'Aeromexico Boeing 737-8 MAX (XA-SRA) at GDL.jpg'],
    'AVA': ['Avianca Airbus A320neo N962AV departing Boston June 2025 1.jpg', 'Avianca Airbus A320neo HK-5366 departing Boston Feb 2025 1.jpg'],
    'CMP': ['HP-9924CMP @ BOS, 2024-09-11.jpg', 'HP-9902CMP @ LAX, 2023-12-11.jpg'],
    'VOI': ['N531VL Volaris Airbus A320-271N s-n 7626 (38892933654).jpg'],
    'FLE': ['C-FLKA at YYZ 20260701.jpg', 'C-FLUJ @ LAX, 2023-09-12.jpg'],
    'CPA': ['(AUS-Victoria) Cathay Pacific Airbus A350-941 B-LRA @ YMML 2025-12-06.jpg', 'Cathay Pacific (B-LRU) Airbus A350-941 at Sydney Airport.jpg'],
    'SIA': ['(SGP-Singapore) Singapore Airlines Airbus A350-941 9V-SHL @ WSSS 2025-11-19.jpg', 'Singapore Airlines Airbus A350 9V-SMK Singapore 2025 (01).jpg'],
    'EVA': ['EVA Air Boeing 787-9 B-17887 at Munich May 2025.jpg', 'Eva Air Boeing 787-9 B-17881 (50314419768).jpg'],
    'CAL': ['(GBR-London) China Airlines Airbus A350-941 B-18906 @ EGLL 2025-06-17.jpg', 'B-18919 - Airbus A350-941 - China Airlines SIN 220325.jpg'],
    'KAL': ['Korean Air 787-10 HL8571.jpg', 'Korean Air - Boeing 787-9 Dreamliner - HL8392 (54867525416).jpg'],
    'ANA': ['ANA Boeing 787 (JA896A) taking off from NRT.jpg', 'JA895A HND 2025-03-20.jpg'],
    'JAL': ['(AUS-Victoria) Japan Airlines Boeing 787-9 JA864J @ YMML 2025-12-06.jpg', 'Japan Airlines Boeing 787-9 JA867J after departing Runway 33L Boston Feb 2025 1.jpg'],
    'QFA': ['20250407 Boeing 787-9 of Qantas (VH-ZNG) taxiing at SYD.jpg', 'Qantas - VH-ZNF - Boeing 787-9 Dreamliner - Sydney Kingsford Smith International Airport (1).jpg'],
    'PAL': ['Philippine Airlines, RP-C3501, Airbus A350-941 (52016591900).jpg', 'Philippines Airlines Airbus A350-941 RP-C3506.jpg'],
    'AFR': ['Air France, F-HTYS, Airbus A350-941 (54008313536).jpg', 'Air France, F-HUVE, Airbus A350-941 (54008539633).jpg'],
    'BAW': ['(GBR-London) British Airways Airbus A380-841 G-XLEH @ EGLL 2025-06-17.jpg', 'British Airways, G-XLEA, Airbus A380-841 (52437091298).jpg'],
    'DLH': ['Lufthansa Boeing 747-8 D-ABYI IAD VA1.jpg', 'Lufthansa Boeing 747-8 D-ABYK MD1.jpg'],
    'UAE': ['(GBR-London) Emirates Airbus A380-861 A6-EUH @ EGLL 2025-06-18.jpg', '20250402 Airbus A380-861 of Emirates (A6-EOE) taxiing at SYD.jpg'],
    'THY': ['Turkish Airlines (TC-LHD) Airbus A350-941 taxiing at Sydney Airport.jpg', 'Turkish Airlines, TC-LGZ, Airbus A350-941 (54076337726).jpg'],
    'VIR': ['Better Virgin Atlantic Boeing 787-9 Dreamliner G-VOWS arriving SFO ref L1180157.jpg', 'G-VZIG B787 VIRGIN ATLANTIC (54770862678).jpg'],
    'ANZ': ['Air New Zealand Boeing 787 ZK-NZG, PER September 2025.jpg', 'Air New Zealand 787-9 ZK-NZK (1).jpg'],
    'KLM': ['KLM 787-10 PH-BKG MD1.jpg', 'KLM Boeing 787 PH-BHI Jakarta 2025 (01).jpg'],
    'AAR': ['(GBR-London) Asiana Airlines Airbus A350-941 HL8362 @ EGLL 2025-06-17.jpg', 'Asiana Airlines, HL8360, Airbus A350-941 (53213646688).jpg'],
    'SJX': ['Starlux A350-941 B-58509 - TPE RCTP - 11-JAN-2026.jpg', 'Starlux Airlines Airbus A350-941 B-58501 (52488542894).jpg'],
    'TZP': ['ZIPAIR Boeing 787-8 JA824J at Vancouver June 2025.jpg', 'ZIPAIR, Boeing 787-8, JA825J, Narita, 20221210.jpg'],
    'EIN': ['Aer Lingus EI-EIK A333.jpg', 'EI-GCF - Airbus A330-302 - Aer Lingus (45508328212).jpg'],
    'QTR': ['(SGP-Singapore) Qatar Airways Airbus A350-941 A7-AMI @ WSSS 2025-12-05.jpg', 'Qatar Airways, A7-AMG, Airbus A350-941 (53212715944).jpg'],
    'FBU': ['French bee A350-900 F-HREY @ LAX.jpg', 'French bee, F-HREU, Airbus A350-941 (54011783844).jpg'],
    'SAS': ['Scandinavian Airlines Airbus A350-900 SE-RSF departing SFO, 4-20-2026.jpg', 'SAS, SE-RSF, Airbus A350-941.jpg'],
    'TAP': ['Airbus A330-941 ‘CS-TUL’ TAP Air Portugal (53762510261).jpg', 'Airbus A330-941 ‘CS-TUC’ TAP Air Portugal (53698538866).jpg'],
    'APZ': ['(JPN-Chiba) Air Premia Boeing 787-9 HL8703 @ RJAA 2026-06-12.jpg', 'HL8388 Air Premia Boeing 787-9 Dreamliner Departing Los Angeles International, August 2023.jpg'],
    'ITY': ['ITA Airways EI-IFF at LAX, May 2, 2026.jpg', 'ITA Airways EI-IFF Airbus A350-941, FCO, 23022023.jpg'],
    'CSN': ['(SGP-Singapore) China Southern Airlines Boeing 787-9 B-20C6 @ WSSS 2025-11-26.jpg', 'B-1128 China Southern Boeing 787-9 Dreamliner YMML.jpg'],
    'HVN': ['(VNM-Ho Chi Minh City) Vietnam Airlines Airbus A350-941 VN-A898 @ VVTS 2025-10-08.jpg', 'Vietnam Airlines A350-941 VN-A898 (51082039571).jpg'],
    'FJI': ['Fiji Airways (DQ-FAI) Airbus A350-941 taxiing at SYD, Jan 2026 01.jpg', '20230811 Airbus A350-941 of Fiji Airways (DQ-FAJ) at SYD 01.jpg'],
    'IBE': ['Iberia, EC-MJA, Airbus A330-202 (51006997442).jpg', 'Iberia Airbus A330-202 EC-MKI.jpg'],
    'LOT': ['LOT, SP-LSE, Boeing 787-9 Dreamliner (51956838524).jpg', 'LOT, SP-LSG, Boeing 787-9 Dreamliner (51855177489).jpg'],
    'SWA': ['Southwest Airlines Boeing 737-700 N273WN departing Boston June 2025.jpg', 'Southwest Boeing 737-700 N947WN BWI MD1.jpg'],
    'FFT': ['Frontier Airbus A320neo N354FR BWI MD1.jpg', 'Frontier Airbus A320neo N384FR BWI MD1.jpg'],
    'UAL-X': ['United Express Embraer 175 N206SY landing at San Francisco January 2026.jpg', 'United Express Embraer 175 N86371 landing at San Francisco January 2026.jpg'],
    'DAL': ['Delta Boeing 737-900ER N884DN departing Boston February 2025.jpg', 'Delta Boeing 737-900ER N837DN BWI MD1.jpg'],
    'ACA': ['C-GELQ at YUL 20260629.jpg', 'Air Canada and United 737 MAX at Vancouver June 2025.jpg'],
    'ACA-X': ['C-FNJZ taking off from LAX.jpg', 'C-FJJZ.jpg'],
    'HAL': ['Hawaiian Airlines Airbus A321neo N226HA.jpg', 'N228HA @ LAX, 2019-12-31.jpg'],
    'SCX': ['Sun Country Airlines B737-800.jpg', 'Sun Country Airlines 737-800 (417812906).jpg'],
    'MXY': ['N204BZ @ LAX, 2024-12-09.jpg', 'Airbus A220-300 - Breeze Airways - N256BZ.jpg'],
    'FDX': ['MD-11F N591FE FedEx Express London Stansted Airport.jpg', 'FedEx Express McDonnell Douglas MD-11F N602FE (35239861795).jpg'],
    'CFG': ['16-NOV-2023 - DE2032 FRA-SEA (D-ANRA - A330-900neo) (01).jpg', '18-NOV-2023 - DE2033 SEA-FRA (D-ANRJ - A330-900neo) (04).jpg'],
    'UPS': ['UPS, N618UP, Boeing 747-8F (52016277689).jpg', 'UPS N627UP run 5X61(Hong Kong International Airport to Taiwan Taipei Taoyuan International Airport) 11-02-2025.jpg'],
}


def api(params):
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(params, format='json', maxlag=5))
    for k in range(8):
        r = subprocess.run(['curl', '-sS', '-m', '40', '-A', UA, url], capture_output=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(20 + 20 * k)          # HTTP 429: back off (Wikimedia API rate limits)
    raise RuntimeError('Commons API unreachable: ' + url)


def info(titles, width):
    """imageinfo of up to 40 files per request (one request instead of one per file: the API rate limit)"""
    out = {}
    for i in range(0, len(titles), 40):
        d = api(dict(action='query', titles='|'.join('File:' + t for t in titles[i:i + 40]), prop='imageinfo',
                     iiprop='url|extmetadata', iiurlwidth=width))
        norm = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        for pg in d['query']['pages'].values():
            t = norm.get(pg['title'], pg['title'])[5:]
            if 'imageinfo' in pg: out[t] = pg['imageinfo'][0]
        time.sleep(3)
    return out


def fetch_all(brands, width, index):
    os.makedirs(OUT, exist_ok=True)
    todo = [(b, i, t) for b in brands for i, t in enumerate(REFS[b]) if f'{b}_{i + 1}' not in index]
    II = info(sorted({t for _, _, t in todo}), width)
    for b, i, t in todo:
        ii = II.get(t)
        if not ii: print(f'  {b}: missing {t}'); continue
        md = ii.get('extmetadata', {}); src = ii.get('thumburl') or ii['url']
        fn = os.path.join(OUT, f'{b}_{i + 1}.jpg')
        for k in range(6):
            r = subprocess.run(['curl', '-sS', '-L', '-m', '60', '-A', UA, '-o', fn, '-w', '%{http_code}', src], capture_output=True, text=True)
            if r.stdout.strip() == '200' and os.path.getsize(fn) > 20000: break
            time.sleep(15 + 15 * k)
        else:
            print(f'  {b}_{i + 1}: download failed ({r.stdout.strip()})')
            if os.path.exists(fn): os.remove(fn)
            continue
        g = lambda k: (md.get(k) or {}).get('value', '')
        index[f'{b}_{i + 1}'] = dict(file=os.path.relpath(fn, ROOT), title=t, page=ii.get('descriptionurl'), author=g('Artist'),
                                     licence=g('LicenseShortName'), date=g('DateTimeOriginal'))
        print(f'  {b}_{i + 1}: {t} ({g("LicenseShortName")})', flush=True)
        json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=1, ensure_ascii=False)
        time.sleep(2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('brands', nargs='*'); ap.add_argument('--width', type=int, default=1600)
    a = ap.parse_args()
    ip = os.path.join(OUT, 'index.json')
    index = json.load(open(ip)) if os.path.exists(ip) else {}
    fetch_all(a.brands or list(REFS), a.width, index)
