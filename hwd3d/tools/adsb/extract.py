"""Step 1 of the HWD ADS-B ground analysis: read the pinned adsb.lol hours once and keep, per aircraft, every distinct
position fix near HWD -> refs/cache/local/adsb/hwd_tracks.pkl (gitignored: it holds ICAO addresses, default D1).

New file. The fix de-duplication by position time (t - seen_pos) is the method of sfo3d/tools/stands/adsb_parked.py
LolTracks @ a967f9b (there: tpos = record t - seen_pos rounded to 0.1 s, one fix per (hex, tpos)); changed: the position time
uses the server clock d.now (the record 't' is the client's request time), a fix is a new fix only when its position time is
> 0.25 s after the aircraft's previous one, the region is HWD (R_KEEP of the HWD ARP, below ALT_KEEP ft or 'ground').

Kept per fix: tpos, x, z (hwd_frame.wgs84_to_world), ground flag (alt_baro == 'ground'), alt_baro (ft, None on the
ground), alt_geom (ft), gs (kt), track, true_heading, baro_rate, NACp, source class, seen_pos, category, type.
Also kept: the server times of all HTTP-200 polls (coverage: an event in a polling hole is 'unobserved', not 'absent').
usage: python3 -I hwd3d/tools/adsb/extract.py
"""
import lzma, json, math, os, pickle, sys, time
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C                                              # noqa: E402

R_KEEP = 12000.0      # m from the ARP: pattern legs (~1.5-3 km) and final approaches (~5 km) fit easily
ALT_KEEP = 5000       # ft pressure altitude: HWD pattern 600-800 ft AGL (NASR); OAK/SFO arrivals above are dropped later
MAX_SEEN_POS = 60.0   # s: older positions are not fixes of this poll


def main():
    t0 = time.time()
    fix = defaultdict(list)          # hex -> list of tuples
    last_tp = {}
    polls = []; n_rec = 0; n_code = Counter(); per_hour = {}
    burst = Counter()                # polls per burst (consecutive 200s separated by < 5 s)
    for h in C.HOURS:
        fn = os.path.join(C.PACK, 'adsblol_%s.jsonl.xz' % h)
        if not os.path.exists(fn):
            print('missing hour', h); per_hour[h] = None; continue
        n_ok = 0; bl = 0; prev = None
        try:
            fh = lzma.open(fn, 'rt')
            for line in fh:
                try: r = json.loads(line)
                except ValueError: continue
                n_rec += 1; n_code[r.get('code')] += 1
                if r.get('code') != 200: continue
                d = r.get('d') or {}
                now = (d.get('now') / 1000.0) if d.get('now') else r['t']
                polls.append(now); n_ok += 1
                if prev is not None and now - prev < 5: bl += 1
                else:
                    if bl: burst[bl] += 1
                    bl = 1
                prev = now
                for a in d.get('ac') or []:
                    if 'lat' not in a or not a.get('hex'): continue
                    sp = a.get('seen_pos') or 0.0
                    if sp > MAX_SEEN_POS: continue
                    alt = a.get('alt_baro'); g = alt == 'ground'
                    if not g and not (isinstance(alt, (int, float)) and alt <= ALT_KEEP): continue
                    x, z = C.F.wgs84_to_world(a['lat'], a['lon'])
                    if math.hypot(x, z) > R_KEEP: continue
                    hx = a['hex']; tp = now - sp
                    if tp <= last_tp.get(hx, -1e18) + 0.25: continue
                    last_tp[hx] = tp
                    fix[hx].append((tp, x, z, g, None if g else float(alt),
                                    a.get('alt_geom'), a.get('gs'), a.get('track'), a.get('true_heading'),
                                    a.get('baro_rate'), a.get('nac_p'), C.src_class(a.get('type')), sp,
                                    a.get('category'), a.get('t'), a.get('type')))
            if bl: burst[bl] += 1
        except (EOFError, lzma.LZMAError) as e:
            print('read error', h, e)
        per_hour[h] = n_ok
    polls = np.array(sorted(polls))
    gaps = np.diff(polls)
    tracks = {}
    for hx, L in fix.items():
        L.sort(key=lambda q: q[0])
        cols = list(zip(*L))
        ty = Counter(q for q in cols[14] if q); ca = Counter(q for q in cols[13] if q)
        t = ty.most_common(1)[0][0] if ty else None; cat = ca.most_common(1)[0][0] if ca else None
        cls, cls_src = C.type_class(t, cat)
        tracks[hx] = dict(type=t, cat=cat, cls=cls, cls_src=cls_src,
                          t=np.array(cols[0]), x=np.array(cols[1]), z=np.array(cols[2]), g=np.array(cols[3], bool),
                          alt=np.array([np.nan if v is None else v for v in cols[4]]),
                          altg=np.array([np.nan if v is None else v for v in cols[5]], float),
                          gs=np.array([np.nan if v is None else v for v in cols[6]], float),
                          trk=np.array([np.nan if v is None else v for v in cols[7]], float),
                          hdg=np.array([np.nan if v is None else v for v in cols[8]], float),
                          vr=np.array([np.nan if v is None else v for v in cols[9]], float),
                          nacp=np.array([-1 if v is None else v for v in cols[10]], int),
                          src=np.array(cols[11]), seen=np.array(cols[12]), rawsrc=np.array([v or '' for v in cols[15]]))
    pattern = {'records': n_rec, 'http_codes': {str(k): v for k, v in n_code.most_common()},
               'ok_polls': int(len(polls)), 'span_s': [float(polls[0]), float(polls[-1])],
               'poll_gap_s_pct': {p: round(float(np.percentile(gaps, p)), 2) for p in (5, 25, 50, 75, 90, 95, 99)},
               'polls_per_burst': dict(sorted((int(k), v) for k, v in burst.items())),
               'gaps_over_60s': int((gaps > 60).sum()), 'gaps_over_600s': int((gaps > 600).sum()),
               'hours_ok_polls': {h: v for h, v in per_hour.items()}}
    pickle.dump({'tracks': tracks, 'polls': polls, 'pattern': pattern, 'hours': C.HOURS, 'R_KEEP': R_KEEP,
                 'ALT_KEEP': ALT_KEEP}, open(C.TRACKS, 'wb'), protocol=4)
    nf = sum(len(v['t']) for v in tracks.values())
    print('%d records, %d ok polls, %d aircraft, %d fixes -> %s (%.0f s)' % (n_rec, len(polls), len(tracks), nf,
          os.path.relpath(C.TRACKS, C.HWD), time.time() - t0))
    print(json.dumps({k: v for k, v in pattern.items() if k != 'hours_ok_polls'}))


if __name__ == '__main__':
    main()
