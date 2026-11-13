#!/usr/bin/env python3
"""Rank the hours of the committed adsb.lol rec_pack (sfo3d/refs/cache/rec_pack, ODbL 1.0) by HWD activity, to choose
replay-pack windows. Counts only (no address, registration or callsign is printed or written).

Per UTC hour:
  ok / http429      recorder responses (200 / 429)
  ground            distinct aircraft reporting alt_baro 'ground' within 1.5 km of the HWD ARP (on the field)
  transitions       ground -> airborne changes within 2.5 km of the ARP (take-offs, touch-and-goes; one aircraft can
                    make several), from consecutive fixes of the same aircraft
  area              distinct aircraft within 8 NM of the ARP at <= 5,000 ft (alt_baro) or on the ground (the relay /
                    pack window)
Local time = PST (UTC-8; no DST in November 2026).

  python3 tools/live/rank_hours.py [--out out/replay/hours_rank.json]
"""
import argparse, datetime as dt, glob, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import recio  # noqa: E402
import hwd_live_server as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=os.path.join(ROOT, 'out', 'replay', 'hours_rank.json'))
    a = ap.parse_args()
    rows = []
    for p in sorted(glob.glob(os.path.join(S.REC_PACK, 'adsblol_*.jsonl.xz'))):
        hour = re.search(r'_(\d{8}_\d{2})\.jsonl', p).group(1)
        ok = n429 = 0; ground, area, last, trans = set(), set(), {}, 0
        for r in recio.lines(p):
            if r.get('code') == 429:
                n429 += 1
            d = r.get('d')
            if not isinstance(d, dict):
                continue
            ok += 1
            for x in d.get('ac') or []:
                hx = x.get('hex'); lat, lon = x.get('lat'), x.get('lon')
                if not hx or lat is None or lon is None:
                    continue
                m = S.hav_m(S.ARP[0], S.ARP[1], lat, lon); alt = x.get('alt_baro')
                gnd = alt == 'ground'
                if m <= 8 * S.NM and (gnd or (isinstance(alt, (int, float)) and alt <= 5000)):
                    area.add(hx)
                if gnd and m <= 1500:
                    ground.add(hx)
                if m <= 2500 and (gnd or isinstance(alt, (int, float))):
                    if last.get(hx) is True and not gnd:
                        trans += 1
                    last[hx] = gnd
        t = dt.datetime.strptime(hour, '%Y%m%d_%H').replace(tzinfo=dt.timezone.utc)
        loc = t - dt.timedelta(hours=8)
        rows.append({'hour_utc': hour, 'local': loc.strftime('%a %d %b %H:00 PST'), 'weekend': loc.weekday() >= 5,
                     'ok': ok, 'http429': n429, 'ground': len(ground), 'transitions': trans, 'area': len(area)})
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({'about': 'tools/live/rank_hours.py: HWD activity per rec_pack hour (counts only)', 'hours': rows},
              open(a.out, 'w'), indent=0)
    key = lambda r: (r['ground'] + r['transitions'], r['area'])
    for wk in (True, False):
        print('weekend' if wk else 'weekday', 'top 6 by ground + transitions:')
        for r in sorted((r for r in rows if r['weekend'] == wk and r['ok']), key=key, reverse=True)[:6]:
            print('  ', r)
    print(len(rows), 'hours,', sum(1 for r in rows if not r['ok']), 'without an OK poll ->', a.out)


if __name__ == '__main__':
    main()
