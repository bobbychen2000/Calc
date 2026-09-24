"""docs/drawings/report.md: deviation and conflict tables (worst first) with sheet references, from
out/draw/{scene2d,deviations,audit,sheets,selftest,google_vs_naip,trace_audit}.json. Numbers only - no imagery pixels -
so the report is committable.

Guards: the scene must be in the current world frame (common.scene() refuses otherwise) and must describe the working
tree - every file the app loaded at extraction is re-hashed; if any differs the report is NOT written (set
ALLOW_STALE=1 to write it anyway, with a STALE banner). Every statement about the data is computed from the run's
numbers; nothing is carried over from earlier runs by hand."""
import json, math, os, collections, datetime, sys
import numpy as np
from common import scene, OUT, DOCS, ROOT, w2st, buildings, provenance, git_head, GF
from audit import scen_label
import measure

SEV = ['COLLISION', 'OFF-PAVEMENT', 'OBSTRUCTION', 'CLEARANCE', 'WARNING']


def f1(v, k=1):
    return '–' if v is None or (isinstance(v, float) and math.isnan(v)) else f'{v:.{k}f}'


def sheet_ref(sheets, x, z, want_detail=True):
    """vector sheets whose frame contains world point (x, z); detail sheets first"""
    hits = []
    for key, s in sheets.items():
        sid, var = key.split(':')
        if var != 'vector': continue
        b = s['box']
        if b[0] <= x <= b[2] and b[1] <= -z <= b[3]: hits.append(sid)
    hits.sort(key=lambda s: (s.startswith('00'), s))
    return ', '.join(f'[{h}]({h}.png)' for h in hits[:2]) if hits else '–'


def feature_loc(sample):
    p = np.array(sample['pts']); return (float(p[:, 0].mean()), float(p[:, 1].mean())) if len(p) else (0, 0)


def load(name, default=None):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else default


def run():
    S = scene(); PV = provenance(S)
    if PV['stale'] and os.environ.get('ALLOW_STALE') != '1':
        raise SystemExit('report.py: out/draw/scene2d.json is STALE - these files the app loaded changed since the extraction: ' + ', '.join(PV['stale'][:12])
                         + (' ...' if len(PV['stale']) > 12 else '') + '. Re-run tools/drawing/run_all.sh (or ALLOW_STALE=1 to write a report marked stale).')
    D = load('deviations.json', {}); A = load('audit.json', {'conflicts': [], 'meta': {}}); SH = load('sheets.json', {})
    ST = load('selftest.json'); GN = load('google_vs_naip.json'); TA = load('trace_audit.json')
    for src, R in D.items():
        if R.get('rules') != measure.RULES_VERSION: raise SystemExit(f'report.py: deviations.json ({src}) was measured with rules {R.get("rules")!r}, measure.py is {measure.RULES_VERSION!r}: re-run measure.py')
    samples = {}
    for src in D:
        fp = os.path.join(OUT, f'dev_samples_{src}.json')
        if os.path.exists(fp): samples[src] = json.load(open(fp))['samples']
    L = []; w = L.append
    C = A['conflicts']
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
    w('# SFO Live 3D — 2-D drawing set: deviations and physical conflicts')
    w('')
    if PV['stale']: w(f'> **STALE (ALLOW_STALE=1): {len(PV["stale"])} file(s) the app loaded changed after the extraction** ({", ".join(PV["stale"][:8])}). The numbers below describe the extracted state, not the working tree.')
    w(f'Generated {now}Z by `tools/drawing/run_all.sh` (report: `tools/drawing/report.py`).')
    w(f'Scene extracted from the running app (`jobs/extract2d.mjs`, {S["meta"]["url"].split("/")[-1]}) at {PV["generated"][:19]}Z: **world frame `{PV["frame"]}`**, git `{PV["git"]}` (HEAD now `{git_head()}`), '
      f'{PV["nInputs"]} input files hashed (inputs `{PV["inputsHash"]}`, TYPES `{PV["typesHash"]}`) - '
      + ('**all unchanged in the working tree at report time**' if PV['stale'] == [] else 'staleness unknown' if PV['stale'] is None else '**stale**') + f', quality tier `{S["meta"]["quality"]["name"]}`.')
    if S['meta'].get('gitDirty'): w(f'Uncommitted app files at extraction (their content is what the hashes pin): {", ".join(S["meta"]["gitDirty"][:10])}' + (' ...' if len(S["meta"]["gitDirty"]) > 10 else '') + '.')
    if PV['changedDuring']: w(f'**Changed while the extraction ran** (the scene may mix both versions): {", ".join(PV["changedDuring"])}.')
    w('Everything below is drawn/measured from the objects the 3-D app actually places (window.SFO world / gateSys / traffic / physics, and the app\'s own builder functions), not re-derived from the data files.')
    w('')
    # ------------------------------------------------------------------ headline
    w('## Headline')
    w('')
    for src, R in D.items():
        fs = R['features']; meas = [f for f in fs if f.get('measured')]
        cls_ok = [f for f in meas if f['cls'] != 'bridge-rotunda']
        w(f'- **Imagery `{src}`** ({R["source"]}; {"public, primary" if R["public"] else "reference only, not redistributable"}): '
          f'{len(fs)} features sampled, **{len(cls_ok)} measured** (+{len(meas) - len(cls_ok)} jet-bridge rotundas found), '
          f'**{sum(f["flag"] for f in fs)} with median offset > 1.0 m**; {sum(1 for f in cls_ok if f.get("p90", 0) > 1.0)} with p90 > 1.0 m.')
    for src, R in D.items():
        by = collections.defaultdict(list)
        for f in R['features']:
            if f.get('measured'): by[f['cls']].append(f)
        rel = ['runway-edge-stripe', 'runway-end', 'runway-threshold', 'runway-threshold-bar', 'emas-bed', 'approach-light-pier']
        w(f'  - `{src}` by class (flagged / measured): ' + '; '.join(f'{c} {sum(f["flag"] for f in by[c])}/{len(by[c])}' for c in rel + ['taxiway-edge', 'extra-pavement', 'apron-edge', 'building', 'bridge-walkway', 'hold-line'] if by.get(c)) + '.')
    w('  - How far each class can be trusted is in the self-test section; building and pavement-edge classes recover a known shift less reliably than runway markings, so read their numbers with the overlay sheets.')
    if 'naip' not in D: w('- **NAIP** was not present in `refs/cache/naip/` at run time: every measurement used the Google screenshots only.')
    cs = collections.Counter(c['severity'] for c in C)
    w(f'- **Physical audit**: {len(C)} distinct findings (one per pair of objects, merged across scenarios, worst severity kept): ' + ', '.join(f'**{cs.get(s, 0)} {s}**' for s in SEV) + '.')
    ps = A['meta'].get('per_scenario') or {}
    scen = sorted({k.split('|')[0] for k in ps})
    w('')
    w('Per scenario (each scenario counted at its own severity - a pair that collides in DOCK-MAX but only warns in LIVE counts as a LIVE warning):')
    w('')
    w('| scenario | ' + ' | '.join(SEV) + ' |'); w('|---|' + '---|' * len(SEV))
    desc = {'LIVE': 'snapshot as displayed', 'REST': 'all stands empty, bridges parked', 'DOCK-REF': 'every stand with its reference type, bridges docked', 'DOCK-MAX': 'every stand with its largest type, bridges docked',
            'ENVELOPE': 'class envelopes (all accepted types) vs neighbours / parked bridges / buildings', 'OVERSIZE': '747 / A380 on EL-F stands vs blocking rule', 'KINEMATICS': 'bridge tunnel geometry rest vs docked',
            'STATIC': 'buildings vs buildings; piers / signs vs movement surfaces'}
    for sc in scen: w(f'| {sc} ({desc.get(sc, "")}) | ' + ' | '.join(str(ps.get(f'{sc}|{s}', 0)) for s in SEV) + ' |')
    w('')
    # ------------------------------------------------------------------ key findings (plain language, computed)
    w('## Key findings (worst first)')
    w('')
    txt = {
        'aircraft-building': 'aircraft overlapping a terminal building (3-D)',
        'envelope-rest-bridge': 'parked (retracted) jet bridge inside the arrival envelope of a stand: an arriving aircraft of an accepted type would hit it',
        'bridge-vdgs': 'VDGS / stand-sign box inside a bridge tunnel, cab or stair',
        'bridge-aircraft': 'docked bridge part (tunnel / rotunda / stair / drive column) intersecting an aircraft in 3-D',
        'bridge-bridge': 'two bridges intersecting in 3-D',
        'aircraft-vdgs': 'aircraft intersecting a VDGS unit', 'bridge-building': 'bridge part inside a building / elevated walkway',
        'envelope-envelope': 'two neighbouring class envelopes overlap', 'oversize-not-blocked': 'oversize aircraft (747/A380) reaches a neighbour the blocking rule leaves available',
        'aircraft-aircraft': 'two aircraft overlapping in 3-D', 'aircraft-pier': 'aircraft intersecting an approach-light pier', 'aircraft-mast': 'aircraft intersecting a floodlight mast',
        'bridge-mast': 'bridge intersecting a floodlight mast', 'bridge-cab-own-aircraft': 'docked cab penetrating its own aircraft beyond the bellows',
        'gse-aircraft': 'ground vehicle inside an aircraft', 'gse-bridge': 'ground vehicle inside a bridge', 'gse-gse': 'two ground vehicles overlapping', 'gse-building': 'ground vehicle in a building / mast / sign',
        'oversize-rest-bridge': 'oversize aircraft hits a neighbour\'s parked bridge', 'oversize-building': 'oversize aircraft hits a building',
        'pier-on-movement-surface': 'approach-light pier or post standing on a runway / displaced-threshold area / blast pad / EMAS bed / taxiway',
        'sign-on-movement-surface': 'airfield sign standing on a runway / taxiway / blast pad / EMAS surface',
        'gear-off-pavement': 'rendered gear on unpaved ground (visual view: rendered paved raster)',
        'gear-off-physics-pavement': 'GroundPhysics gear point neither on the paved raster nor on the OSM taxi net (physics view)'}
    by_kind = collections.defaultdict(list)
    for c in C: by_kind[(c['severity'], c['kind'])].append(c)
    for (sev, k), rows in sorted(by_kind.items(), key=lambda kv: (SEV.index(kv[0][0]), -len(kv[1]))):
        if sev in ('CLEARANCE', 'WARNING'): continue
        sc = collections.Counter(s for r in rows for s, v in (r.get('scenarios') or {}).items() if v == sev)
        w(f'- **{len(rows)} {sev} x {k}** - {txt.get(k, "")} (' + ', '.join(f'{s} {n}' for s, n in sorted(sc.items())) + ').')
    live_bad = [c for c in C if (c.get('scenarios') or {}).get('LIVE') in ('COLLISION', 'OFF-PAVEMENT')]
    if live_bad:
        ids = {}
        for c in live_bad:
            for o in (c['a'], c['b']):
                if o.get('cat') == 'aircraft': ids[o.get('id')] = o.get('elabel')
        acs = {a['hex']: a for a in S['aircraft']}
        lst = [f'{lab} (phase {acs[h]["phase"]}, gs {acs[h]["gs"] or 0:.1f} m/s{", stale" if acs[h]["stale"] else ""}{", at " + acs[h]["gate"] if acs[h]["gate"] else ""})' for h, lab in ids.items() if h in acs]
        if lst: w(f'- LIVE aircraft involved in a collision / off-pavement finding ({len(lst)}): ' + '; '.join(lst[:14]) + (' ...' if len(lst) > 14 else '') + '.')
    kin = collections.Counter(c['kind'] for c in C if c['scenario'] == 'KINEMATICS')
    if kin: w(f'- **Bridge kinematics**: {kin.get("tunnel-stretch", 0)} bridges whose three tunnel sections change length between parked and docked (they scale instead of telescoping); {kin.get("tunnel-slope", 0)} docked tunnels steeper than 1:12.')
    bb = [c for c in C if c['kind'] == 'building-building']
    if bb: w(f'- **{len(bb)} overlapping building footprints** that are both extruded (coplanar roofs that z-fight, or walls that cut through each other)' + ((', among them stations listed twice under two names: ' + '; '.join(f'{c["a"]["elabel"]} / {c["b"]["elabel"]}' for c in bb if 'twice' in c['note'])[:500]) if any('twice' in c['note'] for c in bb) else '') + '.')
    sw = [c for c in C if c['kind'] == 'sign-on-physics-pavement']; pw = [c for c in C if c['kind'] == 'pier-on-physics-pavement']
    if sw: w(f'- {len(sw)} signs stand more than 1 m inside the paved raster that GroundPhysics treats as legal aircraft ground (deepest {max(c["depth"] or 0 for c in sw):.1f} m) - GroundPhysics does not know about signs, so a relocated aircraft can end up on one (WARNING).')
    if pw: w(f'- {len(pw)} approach-light piers / posts inside the paved raster outside the runway / taxiway / end-zone polygons (WARNING).')
    mk = [c for c in C if c['kind'] == 'marker-no-body']
    if mk: w(f'- {len(mk)} aircraft on the ground drawn as a marker (no TYPES entry) - GroundPhysics treats it as no body at all.')
    nc = A['meta'].get('netcheck')
    if nc: w(f'- The OSM taxi-net pavement test the physics view uses is re-implemented from the exported net; it agrees with the page\'s own `TaxiNet.paved` at {nc["agree"] * 100:.2f} % of {nc["n"]} random points.')
    w('')
    # ------------------------------------------------------------------ runway markings measured on NAIP
    prim = 'naip' if 'naip' in D else next(iter(D), None)
    if prim:
        R = {f['id']: f for f in D[prim]['features']}
        w(f'## Runway markings and ends measured on `{prim}`')
        w('')
        w('Along-axis numbers in metres from the threshold line (+ = landing side). `stripe start`: offset of the imaged start of the threshold-stripe block from the model\'s 6.1 m (stripe-start rule, module doc of measure.py). `threshold bar`: imaged centre of the 10 ft bar vs the model (`js/shaders/ground.js` endMarkings() draws a bar only at displaced thresholds, centred 1.525 m on the approach side).')
        w('')
        w('| end | stripe start offset (n) | imaged bar centre | model bar centre | bar verdict | pavement end offset | EMAS bed median |'); w('|---|---|---|---|---|---|---|')
        for rw in S['runways']:
            for e in rw['ends']:
                n = e['name']; th = R.get(f'rwy-thr:{n}') or {}; br = R.get(f'rwy-bar:{n}') or {}; en = R.get(f'rwy-end:{n}') or {}; em = R.get(f'emas:{n}') or {}
                ic, mc = br.get('imaged_centre'), br.get('model_centre')
                if ic is None: verdict = 'not measured'
                elif mc is None: verdict = f'**bar imaged, model draws none**' if br.get('flag') else 'model draws none; weak / partial bar'
                else: verdict = '**wrong side of the threshold**' if (ic > 0) != (mc > 0) and abs(ic - mc) > 1.5 else 'agrees' if abs(ic - mc) <= 1.0 else f'{ic - mc:+.1f} m'
                w(f'| {n} | {f1(th.get("bias"), 2)} ({th.get("measured", 0)}/{th.get("n", 0)}) | {f1(ic, 2)} ({br.get("measured", 0)}/{br.get("n", 0)}) | {f1(mc, 2) if mc is not None else "none"} | {verdict} | '
                  f'{f1(en.get("bias"), 2) if en else "(EMAS end)"} | {f1(em.get("median"), 2) if em else "–"} |')
        w('')
        w('The EMAS "pavement end" at 1L/1R/19L/19R is not a visible edge (the 35 ft setback is paved); those ends are checked by the EMAS bed outline.')
        w('')
        als = [f for f in D[prim]['features'] if f['cls'] == 'approach-light-pier']
        if als:
            w('Approach-light piers over water (`js/anim/lights.js`): along-axis position of each imaged crossbar relative to the modelled pier (read on both crossbar arms), and the imaged crossbar half-length against the widest part of the modelled pier.')
            w('')
            w('| system | samples measured | along-axis offset median / bias (m) | imaged crossbar half-length (m) | model half-length (m) |'); w('|---|---|---|---|---|')
            for f in als: w(f'| {f["name"]} | {f.get("measured", 0)}/{f["n"]} | {f1(f.get("median"), 2)} / {f1(f.get("bias"), 2)} | {f1(f.get("xbar_imaged"), 1)} | {f1(f.get("xbar_model"), 1)} |')
            w('')
        prs = S.get('piers') or []
        if prs:
            land = [q for q in prs if not q['water']]; ob = [c for c in C if c['kind'] == 'pier-on-movement-surface']
            w(f'The app builds {len(prs)} approach-light structures ({len(prs) - len(land)} piers over water, {len(land)} posts on land); {len(ob)} of them stand on a runway, displaced-threshold area, blast pad, EMAS bed or taxiway (OBSTRUCTION rows below).')
            w('')
    # ------------------------------------------------------------------ data vs source (no imagery)
    w('## Data vs published source (no imagery)')
    w('')
    w(f'Runway ends of the RWY table the 3-D draws (`js/world/airfield.js`, s/t) against the FAA/AirNav end coordinates (`js/geo.js` RWY_ENDS), both in the scene\'s frame `{PV["frame"]}`:')
    w('')
    w('| end | along-axis diff (m) | lateral diff (m) | displacement model / FAA (m) |'); w('|---|---|---|---|')
    faa = {}
    for r in S['runwaysFAA']:
        faa[r['ends'][0]] = (np.array(r['a']), r['dispA']); faa[r['ends'][1]] = (np.array(r['b']), r['dispB'])
    diffs = []
    for rw in S['runways']:
        for e in rw['ends']:
            if e['name'] not in faa: continue
            p, dfa = faa[e['name']]; d = np.array(e['end']) - p; inw = np.array(e['inward']); lat = np.array([-inw[1], inw[0]])
            a, b_ = d @ inw, d @ lat; diffs.append((e['name'], a, b_, e['disp'] - dfa)); B = lambda v: f'**{v:+.2f}**' if abs(v) > 1.0 else f'{v:+.2f}'
            w(f'| {e["name"]} | {B(a)} | {B(b_)} | {e["disp"]:.1f} / {dfa:.1f} |')
    w('')
    if diffs:
        mx = max(diffs, key=lambda q: max(abs(q[1]), abs(q[2])))
        w(f'Largest difference: {mx[0]} ({mx[1]:+.2f} m along, {mx[2]:+.2f} m across). ' + ('All eight ends agree with the FAA coordinates to better than 1 m.' if all(max(abs(q[1]), abs(q[2])) < 1.0 for q in diffs) else 'Ends beyond 1 m are in bold.')
          + (' Displacements match.' if all(abs(q[3]) < 0.05 for q in diffs) else ' Displacement differences: ' + ', '.join(f'{q[0]} {q[3]:+.1f} m' for q in diffs if abs(q[3]) >= 0.05) + '.'))
        w('')
    rows = []
    from common import model_geom
    for k, tr in sorted(S['typeRender'].items()):
        if not tr.get('modelKey') or not tr.get('placement'): continue
        gm = model_geom(tr['modelKey'], json.dumps(tr['stretch'], sort_keys=True) if tr.get('stretch') else '', json.dumps(tr['placement']))
        sp = S['types'][k]['wing']['span']; rows.append((k, tr['modelKey'], sp, gm.span))
    big = [r for r in rows if abs(r[3] - r[2]) > 0.5]
    w(f'Rendered aircraft planform (the model after `fit.js` scaling, plugs, span and fin fits, as `models.js` applies them - re-implemented in `common.py _stretch` and checked below) against the TYPES span that GroundPhysics and standFits use: {len(rows)} model-rendered types, '
      + (f'{len(big)} differ by more than 0.5 m:' if big else 'all within 0.5 m.'))
    w('')
    if big:
        w('| type | model | TYPES span (m) | rendered span (m) | diff |'); w('|---|---|---|---|---|')
        for k, mk, sp, rs in big: w(f'| {k} | {mk} | {sp:.2f} | {rs:.2f} | {rs - sp:+.2f} |')
        w('')
    # the Python re-implementation of the model fit against the page's own dims
    chk = []
    for k, tr in sorted(S['typeRender'].items()):
        if not tr.get('modelKey') or not tr.get('placement') or not tr.get('dims'): continue
        gm = model_geom(tr['modelKey'], json.dumps(tr['stretch'], sort_keys=True) if tr.get('stretch') else '', json.dumps(tr['placement']))
        md = getattr(gm, 'model_dims', {}); pd = tr['dims']
        err = max(abs(md.get(q, 0) - pd.get(q, 0)) for q in ('L', 'span', 'H') if q in pd and q in md) if md else None
        chk.append((k, err))
    if chk:
        bad = [c for c in chk if c[1] is None or c[1] > 0.02]
        w(f'Check of the re-implemented model fit: model dims (L, span, H in model units) after `_stretch` equal the page\'s `model.dims` for {len(chk) - len(bad)} of {len(chk)} types' + (': mismatches ' + ', '.join(f'{k} {f1(e, 3)}' for k, e in bad) if bad else ' (to 2 cm).'))
        w('')
    # ------------------------------------------------------------------ imagery + georeference
    w('## Imagery and georeference')
    w('')
    for src, R in D.items():
        pv = R.get('provenance') or {}
        if src == 'naip':
            for p in pv.get('parts', []): w(f'- `naip`: `{p.get("file")}` (sha256 `{p.get("sha")}`, {p.get("bytes") or 0:,} bytes, {p.get("res"):.2f} m/px), transform {p.get("frame_note") or p.get("frame")}' + (f', sidecar `{p["sidecar"]}`' if p.get('sidecar') else '') + '.')
        else: w(f'- `{src}`: {pv.get("images")} screenshots, registrations `{pv.get("registrations")}` (sha256 `{pv.get("reg_sha")}`, frame(s) {", ".join(pv.get("reg_frames", []))} mapped exactly into `{pv.get("frame")}` by tools/sat/common.py sim_from_reg); NAIP residual correction: {pv.get("naip_correction")}.')
    w('')
    if GN:
        w(f'Residual translation of each Google screenshot against NAIP (`imreg.py`, {GN.get("generated")}; ground-level colour gradients, buildings masked, +-{GN.get("search_m")} m search). `shift` = where a ground feature shows in the screenshot as registered, relative to NAIP (x east, z south); applied when `use`.')
        w('')
        w('| screenshot | m/px | patches ok / tested | shift x, z (m) | MAD (m) | NCC | used | note |'); w('|---|---|---|---|---|---|---|---|')
        for k, r in sorted(GN['images'].items(), key=lambda kv: -math.hypot(*(kv[1].get('shift') or [0, 0]))):
            sh = r.get('shift'); w(f'| {k} | {r["gsd"]:.2f} | {r["accepted"]} / {r["tested"]} | {f"{sh[0]:+.2f}, {sh[1]:+.2f}" if sh else "–"} | {f1(r.get("mad"), 2)} | {f1(r.get("ncc"), 2)} | {"yes" if r["use"] else "no"} | {r.get("note", "")} |')
        w('')
    if 'naip' in D and 'google' in D:
        g = {f['id']: f for f in D['google']['features'] if f.get('measured')}; n_ = {f['id']: f for f in D['naip']['features'] if f.get('measured')}
        byc = collections.defaultdict(list)
        for fid in set(g) & set(n_):
            if g[fid]['cls'] == 'bridge-rotunda': continue
            byc[g[fid]['cls']].append(g[fid]['bias'] - n_[fid]['bias'])
        if byc:
            w('Cross-source check after the correction: median over features of (Google bias - NAIP bias) along the outward normal, per class (a residual georeference difference would show as a common non-zero value):')
            w('')
            w('| class | features on both | median difference (m) | median absolute difference (m) |'); w('|---|---|---|---|')
            for c, v in sorted(byc.items(), key=lambda kv: -len(kv[1])): w(f'| {c} | {len(v)} | {np.median(v):+.2f} | {np.median(np.abs(v)):.2f} |')
            w('')
    # ------------------------------------------------------------------ self-test
    if ST and ST.get('rules') == measure.RULES_VERSION:
        keys = [f'{math.hypot(*sh):.1f}' for sh in ST['shifts']]
        w('## How far to trust the automatic picks (self-test)')
        w('')
        w(f'`tools/drawing/selftest.py` (rules `{ST["rules"]}`) resamples each source over {len(ST["regions"])} regions (terminal, airfield, and a box at every threshold) into synthetic tiles whose content is displaced by a known vector ({", ".join(str(tuple(sh)) for sh in ST["shifts"])} m) and re-measures every feature there. `stable` = same pick on an undisplaced resampled tile (within 0.5 m); `recovered` = the measured offset changed by the known n . shift (within 0.5 m). Low recovery means the class\'s numbers are dominated by picking a neighbouring edge.')
        w('')
        for src, cls in ST['sources'].items():
            w(f'**`{src}`**')
            w('')
            w('| class | samples in test regions | measured | stable | ' + ' | '.join(f'recovered @ {k} m' for k in keys) + ' |'); w('|---|---|---|---|' + '---|' * len(keys))
            for k, v in sorted(cls.items()):
                if not v.get('measured'): w(f'| {k} | {v["samples"]} | 0 | – | ' + ' | '.join('–' for _ in keys) + ' |'); continue
                w(f'| {k} | {v["samples"]} | {v["measured"]} | {v["stable_rate"]:.2f} | ' + ' | '.join(f'{v["recovery_" + kk]:.2f}' for kk in keys) + ' |')
            w('')
    elif ST: w(f'(The self-test in out/draw/selftest.json was made with rules `{ST.get("rules")}`, not the current `{measure.RULES_VERSION}` - not shown; re-run selftest.py.)\n')
    # ------------------------------------------------------------------ deviations
    for src, R in D.items():
        fs = R['features']; smp = samples.get(src, {})
        w(f'## Deviations from imagery - `{src}`')
        w('')
        w(f'Source: {R["source"]} ({R["licence"]}). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (NAIP: the other year; Google: another screenshot). Features flagged when the median |offset| > 1.0 m.')
        w('')
        by = collections.defaultdict(list)
        for f in fs: by[f['cls']].append(f)
        w('| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |'); w('|---|---|---|---|---|---|---|---|')
        notes = {'building': 'roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns. One feature per building; edges shared with the ramp-level complex belong to the part',
                 'taxiway-centreline': '6 in paint: needs <= 0.35 m/px', 'stand-leadin': 'lead-in paint: needs <= 0.35 m/px; often under parked aircraft',
                 'bridge-rotunda': 'automatic disc search (6 m radius; picks at the boundary count as not found), low confidence - read with the sheets', 'extra-pavement': 'derived from the Google imagery (circular on `google`); checks the vectorisation',
                 'runway-edge-stripe': '0.91 m stripe', 'runway-threshold': 'start of the stripe block (stripe-start rule)',
                 'runway-threshold-bar': 'imaged 10 ft bar vs the model bar (see the runway table above)', 'hold-line': 'needs <= 0.6 m/px',
                 'approach-light-pier': 'along-axis position of each imaged pier crossbar over water'}
        for c in sorted(by):
            m = [f for f in by[c] if f.get('measured')]
            w(f'| {c} | {len(by[c])} | {len(m)} | {sum(f["flag"] for f in by[c])} | {f1(np.median([f["median"] for f in m]) if m else None, 2)} | {f1(np.median([f["p90"] for f in m]) if m else None, 2)} | {f1(np.median([f["gsd"] for f in m]) if m else None, 2)} | {notes.get(c, "")} |')
        w('')
        for c in ['runway-end', 'runway-threshold', 'runway-threshold-bar', 'runway-edge-stripe', 'emas-bed', 'approach-light-pier', 'building', 'taxiway-edge', 'apron-edge', 'extra-pavement', 'bridge-walkway', 'bridge-rotunda']:
            m = sorted([f for f in by.get(c, []) if f.get('measured')], key=lambda f: -f['median'])
            if not m: continue
            lim = 40 if c in ('building', 'taxiway-edge', 'extra-pavement', 'bridge-rotunda') else 999
            w(f'### {c} ({len(m)} measured, worst first' + (f', top {lim}' if len(m) > lim else '') + ')')
            w('')
            extra = c == 'building'
            w('| feature | n | median | p90 | max | bias | gsd | image(s) | alt bias (gsd) |' + (' fit shift | resid median |' if extra else '') + ' sheet |')
            w('|---|---|---|---|---|---|---|---|---|' + ('---|---|' if extra else '') + '---|')
            for f in m[:lim]:
                x, z = feature_loc(smp[f['id']]) if f['id'] in smp else (0, 0)
                alt = f.get('alt'); flag = ' **>1 m**' if f['flag'] else ''
                imgs = ', '.join(i.split('/')[-1][:24] for i in f['images'])[:48]
                w(f'| {f["name"]}{flag} | {f["measured"]}/{f["n"]} | {f1(f["median"], 2)} | {f1(f["p90"], 2)} | {f1(f["max"], 1)} | {f["bias"]:+.2f} | {f1(f["gsd"], 2)} | {imgs} | '
                  + (f'{alt["bias"]:+.2f} ({alt["gsd"]:.2f})' if alt else '–') + ' |'
                  + (f' {f1(f.get("shiftLen"), 2)} | {f1(f.get("resid_median"), 2)} |' if extra else '') + f' {sheet_ref(SH, x, z)} |')
            w('')
    # ------------------------------------------------------------------ conflicts
    w('## Physical conflicts (worst first)')
    w('')
    w('One row per pair of objects (worst part pair shown; `parts` lists all intersecting part pairs), merged over scenarios; `scenarios` lists those at the row\'s severity, others with their own severity initial in brackets. `depth` = short side of the overlap region (m), `vgap` = smallest vertical gap over the overlap, evaluated point by point (negative = interpenetration). Crops: `crops/conflict_NNNN.png` (vector, committed for the first 60) and `out/draw/crops/` (over the imagery, local only).')
    w('')
    crops = set(os.listdir(os.path.join(DOCS, 'crops'))) if os.path.isdir(os.path.join(DOCS, 'crops')) else set()
    for sev in SEV:
        rows = [c for c in C if c['severity'] == sev and c['scenario'] != 'KINEMATICS']
        if not rows: continue
        w(f'### {sev} ({len(rows)})')
        w('')
        w('| # | scenarios | kind | object A | object B | parts | depth / area | dist | vgap | note | x, z / s, t | sheet |'); w('|---|---|---|---|---|---|---|---|---|---|---|---|')
        for c in rows[:200]:
            loc = c.get('loc') or [0, 0]; s_, t_ = w2st(loc[0], loc[1])
            cr = f'conflict_{c["n"]:04d}.png'
            num = f'[{c["n"]}](crops/{cr})' if cr in crops else str(c['n'])
            types = (' (' + ', '.join(c['types'][:6]) + (' ...' if len(c['types']) > 6 else '') + ')') if c.get('types') and c['kind'].startswith('envelope') else ''
            w(f'| {num} | {scen_label(c)} | {c["kind"]} | {c["a"]["elabel"]}{types} | {c["b"]["elabel"]} | {"; ".join(c.get("parts", []))[:80]} | '
              f'{f1(c.get("depth"), 2)} / {f1(c.get("area"), 1)} | {f1(c.get("dist"), 2)} | {f1(c.get("vgap"), 2)} | {(c.get("note") or "")[:110]} | {loc[0]:.0f}, {loc[1]:.0f} / {float(s_):.0f}, {float(t_):.0f} | {sheet_ref(SH, loc[0], loc[1])} |')
        if len(rows) > 200: w(f'| ... | {len(rows) - 200} more in out/draw/audit.json |')
        w('')
    kin = [c for c in C if c['scenario'] == 'KINEMATICS']
    if kin:
        w(f'### Bridge kinematics ({len(kin)})')
        w('')
        w('| # | kind | bridge | note |'); w('|---|---|---|---|')
        for c in kin[:80]: w(f'| {c["n"]} | {c["kind"]} | {c["a"]["elabel"]} | {c["note"]} |')
        if len(kin) > 80: w(f'| ... | | | {len(kin) - 80} more in out/draw/audit.json |')
        w('')
    # ------------------------------------------------------------------ moving traffic
    if TA:
        cc = collections.Counter(r['kind'] for r in TA['conflicts'])
        w('## Moving traffic (live mode, harness mock relay)')
        w('')
        tpv = TA.get('provenance') or {}
        w(f'`jobs/trace2d.mjs` ran the app in live mode for {TA["span_s"]:.0f} s ({TA["frames"]} samples, git `{TA.get("traceGit")}`, {str(TA.get("traceGenerated"))[:16]}Z) with the harness\'s mock relay (recorded snapshot, aircraft moved in straight lines along their track, taxiing aircraft at 0.35 x speed); `trace_audit.py` checked every sampled frame. The mock\'s straight-line motion takes taxiing aircraft off the pavement and through buildings by construction, so only the aircraft-aircraft rows test GroundPhysics.')
        w('')
        w(f'Pairs in conflict: ' + (', '.join(f'**{v} {k}**' for k, v in cc.most_common()) if cc else 'none') + '.')
        w('')
        if TA['conflicts']:
            w('| kind | object A | object B | frames in conflict | first - last (s) | worst depth (m) | state |'); w('|---|---|---|---|---|---|---|')
            for r in TA['conflicts'][:40]: w(f'| {r["kind"]} | {r["a"]} | {r["b"]} | {r["frames"]} / {TA["frames"]} | {r["first"]:.0f} - {r["last"]:.0f} | {r["depth"]:.1f} | {r["note"]} |')
            w('')
    # ------------------------------------------------------------------ sheets
    w('## Sheet index')
    w('')
    w('Vector sheets (no imagery) are in this folder; the same sheets over the imagery (`*_overlay-naip.*`, `*_overlay-google.*`) are written to `out/draw/sheets/` only (Google pixels must not be committed). Deviation dots on the vector sheets are the NAIP measurements.')
    w('')
    w('| sheet | scale | paper | features (flagged) | conflicts on sheet |'); w('|---|---|---|---|---|')
    for key, s in sorted(SH.items()):
        sid, var = key.split(':')
        if var != 'vector': continue
        w(f'| [{sid}]({sid}.png) ([svg]({sid}.svg)) | 1:{s["scale"]} | {s["paper"]} | {s["features"]} ({s["flagged"]}) | {", ".join(f"{k} {v}" for k, v in sorted(s["conflicts"].items())) or "–"} |')
    w('')
    # ------------------------------------------------------------------ method
    w('## Method, sources and limits')
    w('')
    for t in [
        '**Extraction** (`jobs/extract2d.mjs`): loads `live.html?mode=snapshot` in the harness, stops the page timers, lets traffic + GroundPhysics run until every track is displayable, freezes the render loop, then reads window.SFO and calls the app\'s own builders with a recording geometry sink (every jet-bridge box/cylinder/tube from `gates.js bridgeGeo()` in its current, parked and docked pose; VDGS from `standGeo()`; floodlight masts from `items.js buildMasts()`; approach-light piers from `js/anim/lights.js buildPierGeometry()`; light sprites and PAPIs from `buildLiveLights()`; markings from `markings.js`; signs from `signs.js`; EMAS from `world.js buildEMAS()`; buildings from `buildLiveBuildings()`; pavement from `paintAirportMapReal()`; the OSM taxi net from `traffic.net`). Boxes and tubes are recorded as exact parallelepipeds, so heights are evaluated point by point. Module-private values are read by re-importing the module source with an extra export. Replicated by hand (listed in scene2d.json meta.replicated): the runway paint layout (GLSL; meta.paintCheck confirms each constant is still in the shader), standFits(), the GSE check rectangles, the TaxiNet test and the GroundPhysics gear points. The world frame id, git state and a hash of every loaded file are recorded; all tools refuse a scene in another frame, and this report refuses a stale one.',
        '**Aircraft**: live aircraft use the rendered model (.sfom, with the `fit.js` plugs / span / fin fits applied exactly as `models.js` does) or the procedural TYPES body; per-cell min/max heights make the bridge/wing/engine checks 3-D. Class envelopes = union of every non-oversize type the stand accepts (both the procedural TYPES body and the rendered model). Gear on pavement is tested twice: rendered gear on the rendered raster (visual), GroundPhysics gear points on raster OR taxi net (physics).',
        '**Deviation measurement** (`measure.py`, rules `' + measure.RULES_VERSION + '`): profiles along the edge normal (+-10 m; +-25 m along the runway axis for runway ends/thresholds), gradient peaks (steps) with feature-level polarity consensus against shadows, width-matched ridges for paint and bars, the stripe-start rule for thresholds. Automatic picks can lock onto the wrong edge (shadow, shoulder, paint): read a number together with its overlay sheet.',
        '**Imagery**: NAIP (USDA, public domain, independently georeferenced; primary) - the 2024 mosaic resampled into the world frame, plus the 2022 GeoTIFF mapped world -> NAD83(2011) lat/lon -> UTM 10N; the owner\'s Google Maps screenshots (reference only; frame-aware registrations, re-registered to NAIP per screenshot where `imreg.py` finds a reliable shift). Google building-edge numbers are not independent of the building data: the screenshots were first registered by chamfer matching against the SFO Museum outlines.',
        '**Heights**: SFO Museum footprints have no heights; building heights are the app\'s values (sfo_buildings parts, STRUCT_H tables), bridge / mast / pier heights come from the recorded geometry.',
        '**Not covered**: aircraft in the air; light fixtures other than the approach-light piers are sprites without bodies (runway / taxiway edge lights, PAPI boxes are drawn as points / boxes on the runway sheets but not audited as solids); buildings in the imagery that the app does not build are not detected automatically - compare the overlay sheets; taxiway centrelines and lead-ins need <= 0.35 m/px imagery.',
    ]:
        w('- ' + t)
    w('')
    open(os.path.join(DOCS, 'report.md'), 'w').write('\n'.join(L))
    print('  report:', os.path.relpath(os.path.join(DOCS, 'report.md'), ROOT), len(L), 'lines')


if __name__ == '__main__':
    run()
