export const meta = {
  name: 'sfo-static-fixup',
  description: 'Compact fix pass on the static-data findings left after review round 4 (stand stops/axes, T centreline, footprints, classes, landside, attribution), one review',
  phases: [{ title: 'Fix' }, { title: 'Review' }, { title: 'Fix2' }],
}
const CTX = `Project "SFO Live 3D", /home/user/Calc/sfo3d (read CLAUDE.md, docs/research/stands_rebuild.md). The static-geometry workflow finished with open findings (below). You own the static data and its generators: data/sfo_*.json|js (regenerate, never hand-edit), tools/stands/**, tools/build_*.py, tools/sat/**, tools/imagery/**, tools/xcheck/**, js/geo.js, js/live/airport.js (standGates, landside), docs/ATTRIBUTION.md, docs/research/stands_rebuild.md. NOT yours: js/live/gates.js (the bridges workflow is replacing the app's own rotunda/walkway/rest-pose derivation with the data's rotundaW/walkW/stowW right now), js/anim/lights.js and PAPI placement (the environment workflow will implement docs/research/environment_spec.md), js/live/traffic.js and tools/live/** (real-time workflow; write docs/requests/static_fixup.md for them). Owner's rules: never make unverified key assumptions; evidence from NAIP (public domain), OSM (ODbL), ADS-B recordings (refs/cache/rec) and SFO names; Google screenshots reference only. The owner asked to conserve rate limits: be efficient, fix what the evidence supports, flag the rest honestly. Do NOT git commit. Other workflows run in parallel; tools/drawing extraction may break on their uncommitted edits — use a git archive of HEAD if needed.`
const FINDINGS = `OPEN FINDINGS (static review round 4):
- data stands[].nose: 16 stop points > 1.5 m along-axis from the aircraft imaged in NAIP are flagged (conflict_along) but not corrected; correct them where NAIP + ADS-B agree (per-type stop offsets), keep provenance.
- G1 axis laterally offset/rotated vs imaged aircraft and ADS-B; G12 axis: imaged wide body left of axis, 1.9-2.1 m ahead.
- D3/D4 headings 12-27 deg off, D9 ~11 deg / 5 m off, D8 8.5 m lateral, per the builder's own ADS-B evidence.
- D5 class E rests on one AODB plan that never happened; largest actually parked is B752 -> CL.
- E10/E12 types_ok whitelists exclude Airbus narrow-bodies SFO does allocate (A319/A320 stop ~8 m further forward) — model per-family stop points instead of excluding.
- F17/F19/F21 L1 bridge data rest poses physically impossible (folded 163 deg onto their own walkway; overlaps) and rest/docked tunnels needing rotunda swing beyond the datasheet 175 deg total; rest poses 1.0-4.5 m from wings/engines of types really parked (ICAO 4.5 m C / 7.5 m D-F from fixed objects) — fix the stow data; F5 L1 reach infeasible, A1/A2 L2 and G7 L1 reach — decide from evidence (manufacturer range), document.
- Alternative positions B5S/B11S/B16S/C9V have no bridges and the base stand's rest pose lies inside a wide body parked on the alternative — give the data what the app needs (which bridge serves the alternative, a rest pose clear of it) and document for the bridges workflow.
- sfo_details centerlines[16] taxiway T west end leaves the painted centreline, crosses the edge marking and shoulder, ends on the runway edge — fix from OSM+NAIP paint.
- T1, T3 and BA D footprints > 3 m off where roof lean cannot explain it (T1/T3 over the curbside roadways) — correct with NAIP ground-contact evidence or OSM building outlines (ODbL), document.
- js/live/airport.js landside(): hand-drawn, unsourced roads/lots painted into the ground (236 m circle, bands, rectangles) — replace with OSM highway/parking areas (ODbL) or remove.
- Aircraft-aircraft clearances below ICAO Doc 9157 Pt 2 §3.4.4 at the pairs in stands_rebuild.md §5 — state the evidence that SFO really operates them that way (ADS-B simultaneous occupancy) or restrict (excl).
- docs/ATTRIBUTION.md understates what comes from flysfo (AODB aircraft types drive classes) — make it accurate; if a field has no licence basis, say so plainly for the owner's decision.
- tools/live/gatecheck.py still uses the legacy projection — request to the real-time owner.`
const RES = { type: 'object', properties: { changed: { type: 'array', items: { type: 'string' } }, verification: { type: 'string' }, doubts: { type: 'array', items: { type: 'string' } } }, required: ['changed', 'verification'] }
const FIND = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['critical', 'major', 'minor'] }, where: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' } }, required: ['severity', 'where', 'problem', 'evidence'] } } }, required: ['findings'] }
phase('Fix')
const fix = await agent(`${CTX}\n\n${FINDINGS}\n\nFix them at the source, regenerate the data, run tools/stands/check_stands.py, tools/sat/check.py, check_bridges.py, tools/imagery/check_markings.py. Return what changed and the check results.`, { label: 'fix', phase: 'Fix', schema: RES })
phase('Review')
const rv = await agent(`${CTX}\n\nADVERSARIAL REVIEWER. The fixer addressed:\n${FINDINGS}\nResult: ${JSON.stringify(fix).slice(0, 4000)}\n\nVerify each item independently against NAIP / OSM / ADS-B (numbers, crops in out/review/fixup/). Report what is still wrong or newly broken. Do not fix.`, { label: 'review', phase: 'Review', schema: FIND })
const serious = rv ? rv.findings.filter(f => f.severity !== 'minor') : []
log(`${serious.length} critical/major after the fix`)
let fix2 = null
if (serious.length) { phase('Fix2'); fix2 = await agent(`${CTX}\n\nReviewer findings after your fix:\n${JSON.stringify(rv.findings, null, 1).slice(0, 20000)}\n\nFix the valid ones, regenerate, re-run the checks; list any you leave open with the evidence.`, { label: 'fix2', phase: 'Fix2', schema: RES }) }
return { fix, review: rv, fix2 }
