"""docs/drawings/report.md: deviation and conflict tables (worst first) with sheet references, from
out/draw/{scene2d,deviations,audit,sheets}.json. Numbers only - no imagery pixels - so the report is committable."""
import json, math, os, collections, datetime
import numpy as np
from common import scene, OUT, DOCS, ROOT, w2st, buildings

SEV = ['COLLISION', 'OFF-PAVEMENT', 'CLEARANCE', 'WARNING']


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


def run():
    S = scene(); g = S['meta']['groundY']
    D = json.load(open(os.path.join(OUT, 'deviations.json'))) if os.path.exists(os.path.join(OUT, 'deviations.json')) else {}
    A = json.load(open(os.path.join(OUT, 'audit.json'))) if os.path.exists(os.path.join(OUT, 'audit.json')) else {'conflicts': [], 'meta': {}}
    SH = json.load(open(os.path.join(OUT, 'sheets.json'))) if os.path.exists(os.path.join(OUT, 'sheets.json')) else {}
    samples = {}
    for src in D:
        fp = os.path.join(OUT, f'dev_samples_{src}.json')
        if os.path.exists(fp): samples[src] = json.load(open(fp))['samples']
    L = []; w = L.append
    C = A['conflicts']
    w('# SFO Live 3D — 2-D drawing set: deviations and physical conflicts')
    w('')
    w(f'Generated {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")}Z by `tools/drawing/run_all.sh` (report: `tools/drawing/report.py`).')
    w(f'Scene extracted from the running app (`jobs/extract2d.mjs`, {S["meta"]["url"].split("/")[-1]}, git `{S["meta"].get("git")}`, {S["meta"]["generated"][:19]}Z, quality tier `{S["meta"]["quality"]["name"]}`).')
    w('Everything below is drawn/measured from the objects the 3-D app actually places (window.SFO world / gateSys / traffic / physics, and the app\'s own builder functions), not re-derived from the data files.')
    w('')
    # ------------------------------------------------------------------ headline
    w('## Headline')
    w('')
    for src, R in D.items():
        fs = R['features']; meas = [f for f in fs if f.get('measured')]
        cls_ok = [f for f in meas if f['cls'] != 'bridge-rotunda']
        w(f'- **Imagery `{src}`** ({R["source"]}; {"public" if R["public"] else "reference only, not redistributable"}): '
          f'{len(fs)} features sampled, **{len(cls_ok)} measured** (+{len(meas) - len(cls_ok)} jet-bridge rotunda candidates), '
          f'**{sum(f["flag"] for f in fs)} with median offset > 1.0 m**; {sum(1 for f in cls_ok if f.get("p90", 0) > 1.0)} with p90 > 1.0 m.')
    if 'naip' not in D: w('- **NAIP**: not present in `refs/cache/naip/` at run time - every measurement below used the Google screenshots only. Re-run `tools/drawing/run_all.sh` once the NAIP tiles and their world->pixel JSON are there; the NAIP columns/sheets are produced automatically.')
    cs = collections.Counter(c['severity'] for c in C)
    w(f'- **Physical audit**: {len(C)} distinct findings (one per pair of objects, merged across scenarios): '
      + ', '.join(f'**{cs.get(s, 0)} {s}**' for s in SEV) + '.')
    bys = collections.Counter((sc, c['severity']) for c in C for sc in c.get('scenarios', [c['scenario']]))
    scen = sorted({k[0] for k in bys})
    w('')
    w('| scenario | ' + ' | '.join(SEV) + ' |'); w('|---|' + '---|' * len(SEV))
    desc = {'LIVE': 'snapshot as displayed', 'REST': 'all stands empty, bridges parked', 'DOCK-REF': 'every stand with its reference type, bridges docked', 'DOCK-MAX': 'every stand with its largest type, bridges docked',
            'ENVELOPE': 'class envelopes (all accepted types) vs neighbours / parked bridges / buildings', 'OVERSIZE': '747 / A380 on EL-F stands vs blocking rule', 'KINEMATICS': 'bridge tunnel geometry rest vs docked', 'STATIC': 'buildings vs buildings'}
    for sc in scen: w(f'| {sc} ({desc.get(sc, "")}) | ' + ' | '.join(str(bys.get((sc, s), 0)) for s in SEV) + ' |')
    w('')
    # ------------------------------------------------------------------ key findings (plain language)
    w('## Key findings (worst first)')
    w('')
    kinds = collections.Counter(c['kind'] for c in C if c['severity'] == 'COLLISION')
    txt = {
        'aircraft-building': 'parked aircraft overlapping a terminal building in the LIVE snapshot - GroundPhysics never tested them (see the classification finding below); note also that its tests use 13 outline points of the TYPES planform, not the rendered model',
        'envelope-rest-bridge': 'parked (retracted) jet bridge inside the arrival envelope of its own stand: the cab parks min(15 m, reach - 2 m) from the rotunda towards the door, i.e. within ~2 m of the fuselage line on short-reach stands',
        'bridge-vdgs': 'VDGS / stand-sign box inside a bridge tunnel or stair (the VDGS is placed on the stand centreline at the attach-point depth, where tunnels also pass)',
        'bridge-aircraft': 'docked bridge (tunnel / rotunda / stair / drive column) intersecting its own or a neighbouring aircraft (wing, engine or fuselage) in 3-D',
        'bridge-bridge': 'two bridges intersecting in 3-D (mostly the L1 and L2 bridges of one wide-body stand at rest)',
        'aircraft-vdgs': 'aircraft intersecting a VDGS unit', 'bridge-building': 'bridge part inside a building / elevated walkway',
        'envelope-envelope': 'two neighbouring class envelopes overlap', 'oversize-not-blocked': 'oversize aircraft (747/A380) reaches a neighbour the blocking rule leaves available'}
    for k, n in kinds.most_common():
        w(f'- **{n} x {k}** - {txt.get(k, "")}.')
    # physics classification: stale ('parked') tracks that keep their last reported ground speed
    stuck = [a for a in S['aircraft'] if a['ground'] and a['valid'] and not a['gate'] and a['stale'] and (a['gs'] or 0) >= 0.8]
    live_bad = [c for c in C if c['scenario'] == 'LIVE' and c['severity'] in ('COLLISION', 'OFF-PAVEMENT')]
    bad = {c['a'].get('id') for c in live_bad} | {c['b'].get('id') for c in live_bad}
    if stuck:
        hit = [a for a in stuck if a['hex'] in bad]
        lst = ', '.join(f'{a["flight"] or a["hex"]} {a["gs"]:.1f} m/s' for a in stuck[:10])
        w(f'- **GroundPhysics never checks {len(stuck)} parked aircraft**: tracks with phase `parked` and a stale transponder that still carry their last reported ground speed ({lst}) fall into the *moving* branch of `ground.js resolve()` (`(D.gs || 0) < 0.8` fails), which only nudges aircraft apart and never tests buildings or pavement. {len(hit)} of them account for the LIVE building / VDGS / off-pavement conflicts below.')
    op = [c for c in C if c['severity'] == 'OFF-PAVEMENT']
    if op: w(f'- **{len(op)} aircraft with a gear leg off the paved raster** the app uses (ground.js physics / ground shader): ' + ', '.join(c['a']['elabel'] for c in op) + '.')
    kin = collections.Counter(c['kind'] for c in C if c['scenario'] == 'KINEMATICS')
    if kin: w(f'- **Bridge kinematics**: {kin.get("tunnel-stretch", 0)} bridges whose three tunnel sections change length between parked and docked (they scale instead of telescoping - visible "morphing"); {kin.get("tunnel-slope", 0)} docked tunnels steeper than 1:12.')
    bb = [c for c in C if c['kind'] == 'building-building']
    if bb: w(f'- **{len(bb)} overlapping building footprints** that are both extruded (coplanar roofs that z-fight, or walls that cut through each other), among them AirTrain stations listed twice under two names: ' + '; '.join(f'{c["a"]["elabel"]} / {c["b"]["elabel"]}' for c in bb if 'twice' in c['note'])[:600] + '.')
    mk = [c for c in C if c['kind'] == 'marker-no-body']
    if mk: w(f'- {len(mk)} aircraft on the ground drawn as a marker (no TYPES entry) - GroundPhysics treats it as no body at all.')
    w('')
    # ------------------------------------------------------------------ verified-by-eye findings
    w('## Visually verified on the overlay sheets')
    w('')
    w('- **28R / 28L displaced-threshold bar is on the wrong side of the threshold line (3.05 m)** - verified on NAIP 2024 (0.5 m, independently georeferenced) and on the Google screenshot 1a26bbeb: the modelled threshold stripes coincide with the imaged ones to about half a metre at both ends, but the imaged 10 ft bar lies on the landing side of the threshold (x = 0 .. +3.05 m, then a ~3 m gap to the stripes starting at +6.1 m), while `js/shaders/ground.js` endMarkings() draws it at x = -3.05 .. 0 (approach side, where the imagery shows the arrowheads). Candidate fix: `band(xt, 0.0, 3.05, fw)` instead of `band(xt, -3.05, 0.0, fw)`; re-check the arrowhead tips against the bar afterwards (AC 150/5340-1M Fig. A-7). The automatic bar number in the tables over-states the shift because the ridge detector locks onto the stripe block.')
    w('- **Threshold bar missing at the non-displaced ends (10L, 10R, 19L, 19R)** - the NAIP along-axis profiles in `refs/cache/naip/naip_faa_check_2022.json` / `_2024.json` (produced by the imagery research task) show a 3.4-3.7 m bright band from x = -0.9..0 to +2.7..3.5 m at all four ends, presumably the 10 ft bar blurred by the imagery; `endMarkings()` draws a bar only when the threshold is displaced. The same profiles confirm the rest of the model at those ends: stripes start at 5.3-6.3 m (model 6.1 m) and end at 51.3-52.2 m (model 51.8 m); EMAS beds start 10.5-11.1 m beyond the end (model setback 10.67 m).')
    w('- The EMAS "pavement end" at 1L/1R/19L/19R is not a visible edge (the 35 ft setback is paved); these ends are measured by the EMAS bed outline instead.')
    w('')
    # ------------------------------------------------------------------ data vs source (no imagery)
    w('## Data vs published source (no imagery)')
    w('')
    w('Runway ends of the RWY table the 3-D draws (`js/world/airfield.js`, s/t) against the FAA/AirNav end coordinates (`js/geo.js` RWY_ENDS):')
    w('')
    w('| end | along-axis diff (m) | lateral diff (m) | displacement model / FAA (m) |'); w('|---|---|---|---|')
    faa = {}
    for r in S['runwaysFAA']:
        faa[r['ends'][0]] = (np.array(r['a']), r['dispA']); faa[r['ends'][1]] = (np.array(r['b']), r['dispB'])
    for rw in S['runways']:
        for e in rw['ends']:
            if e['name'] not in faa: continue
            p, dfa = faa[e['name']]; d = np.array(e['end']) - p; inw = np.array(e['inward']); lat = np.array([-inw[1], inw[0]])
            a, b_ = d @ inw, d @ lat; B = lambda v: f'**{v:+.2f}**' if abs(v) > 1.0 else f'{v:+.2f}'
            w(f'| {e["name"]} | {B(a)} | {B(b_)} | {e["disp"]:.1f} / {dfa:.1f} |')
    w('')
    w('The RWY table stores every runway axis-aligned in the s/t grid (a single c per runway). The FAA ends of 1L/19R (s = -20.49 / -22.91) and 1R/19L (s = 207.96 / 205.28) show those runways are not exactly perpendicular to 10/28 (about 0.06 deg), so the modelled 1/19 centrelines are 1.1-1.4 m off at both ends (bold, opposite sides) and close to 0 at mid-length - a rotation, not a shift. NAIP agrees: along their whole length the 1/19 edge stripes measure within ~0.8 m of the model, and the NAIP-derived runway centrelines lie within 0.2-0.4 m of the FAA lines (refs/cache/naip/naip_faa_check_*.json). Fix: give 1L/19R and 1R/19L their own direction instead of the t axis.')
    w('')
    w('Rendered aircraft planform (real model scaled to TYPES length) against the TYPES published span - the audit uses the rendered geometry; GroundPhysics and standFits use TYPES:')
    w('')
    w('| type | model | TYPES span (m) | rendered span (m) | diff |'); w('|---|---|---|---|---|')
    from common import model_geom
    for k, tr in sorted(S['typeRender'].items()):
        if not tr.get('modelKey') or not tr.get('placement'): continue
        gm = model_geom(tr['modelKey'], json.dumps(tr['stretch'], sort_keys=True) if tr.get('stretch') else '', json.dumps(tr['placement']))
        sp = S['types'][k]['wing']['span']
        if abs(gm.span - sp) > 0.5: w(f'| {k} | {tr["modelKey"]} | {sp:.1f} | {gm.span:.1f} | {gm.span - sp:+.1f} |')
    w('')
    w('Several TYPES spans are not the published value of the type they name, and standFits() / GroundPhysics use TYPES: e.g. a332/a333 64.8 m is the A350 wing (A330-200/-300: 60.3 m), crj2 24.9 m is the CRJ900 value (CRJ200: 21.2 m). Rendered models are scaled by length only, so their spans differ from TYPES by up to ~5 m. Verify against the manufacturers\' airport-planning documents before changing js/aircraft/types.js.')
    w('')
    # ------------------------------------------------------------------ deviations
    stp = os.path.join(OUT, 'selftest.json')
    if os.path.exists(stp):
        ST = json.load(open(stp)); keys = [f'{math.hypot(*sh):.1f}' for sh in ST['shifts']]
        w('## How far to trust the automatic picks (self-test)')
        w('')
        w(f'`tools/drawing/selftest.py` resamples the Google imagery of {len(ST["regions"])} regions into synthetic georeferenced tiles whose content is displaced by a known vector ({", ".join(str(tuple(sh)) for sh in ST["shifts"])} m) and re-measures every feature there. `stable` = same pick on an undisplaced resampled tile (within 0.5 m); `recovered` = the measured offset changed by the known n . shift (within 0.5 m). Low recovery means the class\'s numbers are dominated by picking a neighbouring edge (parapet, shadow, shoulder, paint): use its overlay sheets, not its numbers.')
        w('')
        w('| class | samples in test regions | measured | stable | ' + ' | '.join(f'recovered @ {k} m' for k in keys) + ' |'); w('|---|---|---|---|' + '---|' * len(keys))
        for k, v in sorted(ST['classes'].items()):
            if not v.get('measured'): w(f'| {k} | {v["samples"]} | 0 | – | ' + ' | '.join('–' for _ in keys) + ' |'); continue
            w(f'| {k} | {v["samples"]} | {v["measured"]} | {v["stable_rate"]:.2f} | ' + ' | '.join(f'{v["recovery_" + kk]:.2f}' for kk in keys) + ' |')
        w('')
    for src, R in D.items():
        fs = R['features']; smp = samples.get(src, {})
        w(f'## Deviations from imagery - `{src}`')
        w('')
        w(f'Source: {R["source"]} ({R["licence"]}). Offsets are signed along the outward edge normal (+ = imaged edge outside / right of the model), in metres; `gsd` = ground resolution of the image the profile was read from; `alt` = the same samples read from the next-best image (registration check). Features flagged when the median |offset| > 1.0 m.')
        w('')
        by = collections.defaultdict(list)
        for f in fs: by[f['cls']].append(f)
        w('| class | features | measured | flagged (median > 1 m) | median of medians | median p90 | typical gsd | notes |'); w('|---|---|---|---|---|---|---|---|')
        notes = {'building': 'roof edge vs footprint: relief displacement (roofs lean away from nadir) + registration; see `shift`/`resid` columns',
                 'taxiway-centreline': '6 in paint: needs <= 0.35 m/px; the airfield screenshots are 0.5-1.6 m/px and JPEG chroma hides thin yellow lines',
                 'stand-leadin': 'lead-in paint not visible (worn / under the parked aircraft on obs stands)', 'hold-line': 'needs <= 0.6 m/px; most holds are on 0.9-1.6 m/px shots',
                 'bridge-rotunda': 'automatic disc search, low confidence - use the per-bridge crops', 'extra-pavement': 'derived from the same imagery (circular); checks the vectorisation',
                 'runway-edge-stripe': '0.91 m stripe; 1L/19R, 1R/19L only on coarse shots', 'runway-threshold': 'stripe start; needs <= 0.8 m/px'}
        for c in sorted(by):
            m = [f for f in by[c] if f.get('measured')]
            w(f'| {c} | {len(by[c])} | {len(m)} | {sum(f["flag"] for f in by[c])} | {f1(np.median([f["median"] for f in m]) if m else None, 2)} | {f1(np.median([f["p90"] for f in m]) if m else None, 2)} | {f1(np.median([f["gsd"] for f in m]) if m else None, 2)} | {notes.get(c, "")} |')
        w('')
        for c in ['runway-end', 'runway-threshold', 'runway-displaced-threshold', 'runway-edge-stripe', 'emas-bed', 'building', 'taxiway-edge', 'apron-edge', 'extra-pavement', 'bridge-walkway', 'bridge-rotunda']:
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
                w(f'| {f["name"]}{flag} | {f["measured"]}/{f["n"]} | {f1(f["median"], 2)} | {f1(f["p90"], 2)} | {f1(f["max"], 1)} | {f["bias"]:+.2f} | {f1(f["gsd"], 2)} | {", ".join(f["images"])[:40]} | '
                  + (f'{alt["bias"]:+.2f} ({alt["gsd"]:.2f})' if alt else '–') + ' |'
                  + (f' {f1(f.get("shiftLen"), 2)} | {f1(f.get("resid_median"), 2)} |' if extra else '') + f' {sheet_ref(SH, x, z)} |')
            w('')
    # ------------------------------------------------------------------ conflicts
    w('## Physical conflicts (worst first)')
    w('')
    w('One row per pair of objects (worst part pair shown; `parts` lists all intersecting part pairs), merged over the scenarios in which it occurs. `depth` = short side of the overlap region (m), `vgap` = smallest vertical gap over the overlap (negative = interpenetration). Crops: `crops/conflict_NNNN.png` (vector, committed for the first 60 collisions) and `out/draw/crops/` (over the imagery, local only).')
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
            w(f'| {num} | {",".join(c.get("scenarios", [c["scenario"]]))} | {c["kind"]} | {c["a"]["elabel"]}{types} | {c["b"]["elabel"]} | {"; ".join(c.get("parts", []))[:80]} | '
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
    tp = os.path.join(OUT, 'trace_audit.json')
    if os.path.exists(tp):
        TA = json.load(open(tp)); cc = collections.Counter(r['kind'] for r in TA['conflicts'])
        w('## Moving traffic (live mode, harness mock relay)')
        w('')
        w(f'`jobs/trace2d.mjs` ran the app in live mode for {TA["span_s"]:.0f} s ({TA["frames"]} samples) with the harness\'s mock relay (recorded snapshot, aircraft moved in straight lines along their track, taxiing aircraft at 0.35 x speed); `trace_audit.py` checked every sampled frame. The mock\'s straight-line motion takes taxiing aircraft off the pavement and through buildings by construction, so only the aircraft-aircraft rows test GroundPhysics.')
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
    w('Vector sheets (no imagery) are in this folder; the same sheets over the imagery (`*_overlay-google.*`, and `*_overlay-naip.*` when NAIP is present) are written to `out/draw/sheets/` only (Google pixels must not be committed).')
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
        '**Extraction** (`jobs/extract2d.mjs`): loads `live.html?mode=snapshot` in the harness, stops the page timers, lets traffic + GroundPhysics run until every track is displayable, freezes the render loop, then reads window.SFO and calls the app\'s own builders with a recording geometry sink (every jet-bridge box/cylinder/tube from `gates.js bridgeGeo()` in its current, parked and docked pose; VDGS from `standGeo()`; markings from `markings.js`; signs from `signs.js`; EMAS from `world.js buildEMAS()`; buildings from `buildLiveBuildings()`; pavement from `paintAirportMapReal()` - the raster the physics uses). Module-private values (REF_TYPE, CLASS_MAX, STRUCT_H, ...) are read by re-importing the module source with an extra export. Replicated by hand (listed in scene2d.json meta.replicated): the runway paint layout (GLSL), standFits(), and the GSE check rectangles.',
        '**Aircraft**: live aircraft use the rendered model (.sfom, stretched and placed exactly as `aircraft.js` does) or the procedural TYPES body; per-cell min/max heights make the bridge/wing/engine checks 3-D. Class envelopes = union of every non-oversize type the stand accepts (both the procedural TYPES body and the rendered model). Gear contact points: TYPES nose/main gear (the gear the app draws).',
        '**Deviation measurement** (`measure.py`): profiles along the edge normal (+-10 m; +-25 m along the runway axis for runway ends/thresholds), gradient peaks (steps) with feature-level polarity consensus against shadows, width-matched ridges for paint; nearest strong candidate to the model. Automatic picks can lock onto the wrong edge (shadow, shoulder, paint): always read a number together with its overlay sheet.',
        '**Imagery**: the owner\'s Google Maps screenshots (19, 0.17-3.2 m/px, similarity registrations in tools/sat/work/reg.json). Building-edge numbers are not independent of the building data: the screenshots were registered by chamfer matching against the SFO Museum outlines. Runway ends were checked independently against FAA coordinates (tools/sat/faacheck.py). NAIP (independent georeference) is supported but was not available for this run.',
        '**Heights**: SFO Museum footprints have no heights; building heights are the app\'s values (sfo_buildings parts, STRUCT_H tables), bridge heights come from the geometry.',
        '**Not covered**: aircraft in the air; buildings in the imagery that the app does not build (cargo sheds, hangars other than the Super Bay) are not detected automatically - compare the overlay sheets; taxiway centrelines, lead-ins and most hold lines are not measurable on the available resolution.',
    ]:
        w('- ' + t)
    w('')
    open(os.path.join(DOCS, 'report.md'), 'w').write('\n'.join(L))
    print('  report:', os.path.relpath(os.path.join(DOCS, 'report.md'), ROOT), len(L), 'lines')


if __name__ == '__main__':
    run()
