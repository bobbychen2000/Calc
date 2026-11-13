"""Rough type-mix ESTIMATE for SHA (no ADS-B near ZSSS: see docs/phase0/fleet.md).

Estimate A = sum over airlines of (airline's share of SHA airline-destination pairs) x (airline's passenger-fleet share per type
family). Inputs are hard-coded below with their sources; every number is from the cached sources listed in docs/phase0/fleet.md.
It ignores frequencies (the Beijing / Guangzhou / Shenzhen shuttles carry far more flights than a thin route) and assumes an
airline uses its whole fleet evenly at SHA, so it is only a first guess. Usage: python3 -I type_mix_estimate.py
"""
import collections

# airline: (route pairs at SHA from the Wikipedia SHA destination list rev 1385154959, {family: aircraft}, source of the fleet)
AL = {
    'China Eastern (MU)': (66, {'A320 family': 392, '737 family': 141, 'A330': 56, 'A350': 20, '777': 20, '787': 7, 'C909': 32, 'C919': 17}, 'WP mainline'),
    'Shanghai Airlines (FM)': (42, {'737 family': 78, '787': 10}, 'WP'),
    'Spring Airlines (9C)': (23, {'A320 family': 135}, 'WP'),
    'Juneyao Air (HO)': (22, {'A320 family': 93, '787': 10}, 'WP'),
    'XiamenAir (MF)': (10, {'A320 family': 22, '737 family': 142, '787': 12}, 'WP'),
    'China Southern (CZ)': (7, {'A320 family': 351, '737 family': 201, 'A330': 25, 'A350': 20, '777': 15, '787': 21, 'C909': 35, 'C919': 8}, 'WP mainline (777F excluded)'),
    'Air China (CA)': (6, {'A320 family': 225, '737 family': 143, 'A330': 43, 'A350': 30, '747': 9, '777': 28, '787': 14, 'C909': 35, 'C919': 9}, 'WP mainline'),
    'Shandong (SC)': (6, {'737 family': 135}, 'WP'),
    'Hainan (HU)': (4, {'A320 family': 12, 'A330': 29, '737 family': 158, '787': 38}, 'WP'),
    'Shenzhen (ZH)': (3, {'A320 family': 112, 'A330': 6, 'A350': 1, '737 family': 86}, 'WP'),
    'China United (KN)': (2, {'737 family': 60}, 'WP'),
    'Air Macau (NX)': (1, {'A320 family': 23}, 'WP'),
    'Chengdu Airlines (EU)': (1, {'A320 family': 51, 'C909': 30}, 'WP'),
    'Cathay Pacific (CX)': (1, {'A330': 1, 'A350': 1}, 'assumed wide-body on HKG (unverified)'),
    'China Airlines (CI)': (1, {'A330': 1}, 'Commons photo B-18361 A330 at SHA'),
    'EVA Air (BR)': (1, {'787': 1, 'A330': 1}, 'Commons photos B-17808 787-10, B-16333 A330 at SHA'),
    'Hong Kong Airlines (HX)': (1, {'A320 family': 1, 'A330': 1}, 'Commons photos B-LPU A320, B-LNP A330 at SHA'),
    'Japan Airlines (JL)': (1, {'767': 1}, 'assumed (unverified)'),
    'ANA (NH)': (1, {'787': 1}, 'assumed (unverified)'),
    'Korean Air (KE)': (1, {'A330': 1}, 'Commons photo HL7584 A330-300 at SHA'),
    'Asiana (OZ)': (1, {'A320 family': 1, 'A330': 1}, 'assumed (unverified)'),
    'Tianjin (GS)': (1, {'A320 family': 44, 'A330': 4, 'E-Jet': 55}, 'WP'),
    'Lucky Air (8L)': (1, {'A320 family': 14, 'A330': 4, '737 family': 33}, 'WP'),
    'Hebei (NS)': (1, {'737 family': 28}, 'WP'),
    'Xizang (TV)': (1, {'A330': 1}, 'Commons photo B-1046 A330-200 at SHA'),
}
tot_w = sum(w for w, _, _ in AL.values())
mix = collections.Counter()
for name, (w, fleet, _) in AL.items():
    n = sum(fleet.values())
    for fam, k in fleet.items():
        mix[fam] += w / tot_w * k / n
print('Estimate A (route-pair weights x fleet shares), %d airlines, %d airline-destination pairs:' % (len(AL), tot_w))
for fam, s in mix.most_common():
    print('   %-12s %5.1f %%' % (fam, 100 * s))
wb = sum(mix[f] for f in ('A330', 'A350', '777', '787', '747', '767'))
print('   wide-body total %.1f %%' % (100 * wb))
