export const meta = {
  name: 'sfo-followup-r7',
  description: 'Round 7 (owner: "go ahead and address the points"; Full version only, usage-guarded): fix every open residual from the round-5/6 verifiers -> independent verify',
  phases: [{ title: 'Fix' }, { title: 'Verify' }],
}
const SP = '/tmp/claude-0/-home-user-Calc/3fd08d73-28ea-592f-8f33-69ede4de867b/scratchpad'
const METER = `python3 ${SP}/usage/usage_meter.py --calib 687.7 80`
const BASE = `Project "SFO Live 3D", /home/user/Calc/sfo3d (read CLAUDE.md, docs/HANDOFF.md, and your track's docs/requests/*_closeout.md). SP = ${SP}.
This is follow-up ROUND 7 (started 9 Nov 2026 ~16:45Z; owner: "go ahead and address the points"). Inputs: the round-6 independent verifiers' reports (${SP}/c6_r6verify_<track>.json), the round-6 fixers' reports (${SP}/c6_r6fix_<track>.json) and work logs (${SP}/c6/<track>/NOTES.md); round-5 reports ${SP}/c5_*.json where cited. FIVE chains run IN PARALLEL with DISJOINT file ownership: realtime, runtime (bridges + env), aircraft, buildings, static. Edit ONLY the files your track owns (listed below); if a fix needs another track's file, write the exact request (file, line, change, why) into your closeout doc and your report's open_questions. Do not kill processes you did not start.
OWNER DIRECTIVES (9 Nov): the LITE artifact is FROZEN -- no lite-only work, but keep every existing lite line intact; improve the FULL version incl. its LOD2 far files. The lead rebuilds/publishes the Full artifact after this round: do not touch out/phone_artifact*.
USAGE BUDGET (binding; the owner pauses all work at 85 % of the weekly limit; it was 80 % at 16:43Z): be economical -- the smallest evidence that proves each fix (windowed replays of the minutes that show the defect, at most ~4 replays per agent; renders only if essential, at most 1-2 small ones). Run \`${METER}\` at your start and before every long job or every ~30 min; if the estimate it prints is >= 83.5 %, STOP: leave the repo consistent (finish or revert the edit in hand), write your NOTES, and return the StructuredOutput report right away with what is done / not done.
Machine: 4 CPUs / 15 GB shared. (a) jobs that can exceed ~3 GB RSS or saturate CPU for long (Blender builds / AO bakes, paint_pave_naip, livery re-bakes) run ONE AT A TIME under \`flock /home/user/Calc/sfo3d/out/.heavy.lock nice -n 10 <cmd>\`; (b) node replays (tools/live harness, <= ~1.5 GB) without the lock, \`nice -n 10\`, <= 2 at a time per track, only while out/memlog.txt shows >= 3 GB available; (c) Chromium renders under \`flock /home/user/Calc/sfo3d/out/.heavy2.lock\`. Python 3.11; bpy 5.0.1 pins numpy 1.26.4 (never upgrade numpy); NEVER run npm ci / npm i / npm install in the repo root. The live relay sfo_live_server.py (pid in refs/cache/rec/relay_record.pid) serves the owner and records ADS-B: NEVER stop or restart it. Keep the lead's js/live/models.js keyBytes() fetch cache intact.
EVIDENCE RULE: never compare before/after numbers from different harness versions; every replay number carries the md5 of tools/live/invariants.mjs and tools/live/build_stream.py and the frozen root it ran on; before and after arms run on the SAME harness copy (freeze one under SP/c7/<track>/).
Owner rules (binding): never make unverified key assumptions (coordinates, dimensions, sources, licences -- verify against the original source or mark needs_owner); keep observed vs inferred tagged; Google imagery is reference only, never a texture (NAIP is public domain and may be measured); physical plausibility (no clipping, gaps or collisions; aircraft only on pavement).
Do NOT git commit (the lead commits). Keep a running log in SP/c7/<track>/NOTES.md (changes, every job with pid / marker / log, before/after numbers with md5s) so a restarted agent can continue; write 'done' markers for background jobs. Add a 'Round 7' section to your track's closeout doc(s) with before/after numbers and dispositions; update data/buildings3d/manifest.json entries under its flock if you rebuild an asset.`
const TRACKS = {
  realtime: { doc: 'docs/requests/realtime_closeout.md',
    own: 'js/live/traffic.js, js/live/ground.js, js/live/app.js (realtime logic only; keep the lite pickQuality line), tools/live/** (invariants.mjs, build_stream.py, hooks), docs/requests/realtime_closeout.md. Not the relay process.',
    focus: `All 5 residuals in ${SP}/c6_r6verify_realtime.json, at their root causes:
(1) repos hold: cancelled whenever the aircraft is heard again even standing still at the same spot, and the 20-min clock only runs while silent -> a tow that keeps transmitting never gets parked; keep the hold (and run the clock) while it stays within a few m and below taxi speed, drop it only when it actually moves away.
(2) the veto + 'lead' path removes the ghost while its bridge is still docked -> the bridge then retracts from an empty stand (bridge.orphan rises); make the retraction start with the ghost removal (or keep the ghost until its bridge clears) without re-introducing ghost/arrival contacts.
(3) noPush re-signal: a late departure whose SFO estimated off-block has already passed (no actual block-out yet) never re-signals; allow it (estimate passed, no block-out) while keeping the round-6 near-push gate.
(4) placement margin: after its move LXJ569 still stands 1.46 m from N453FD, below the 3 m code-B stand clearance clear.stand requires; use the ICAO wingtip clearance of the larger code for stationary off-stand placements (3 m A/B, 4.5 m C, 7.5 m D-F) where a valid pose exists.
(5) the 1-3-frame ground overlaps of 'waiting' ghosts (removed via window/alloc, still drawn while their bridge retracts) touched by the arriving body.
Same-harness before/after on the windows that show each (D, A-w, G6 / F16 windows from round 6; scripts in SP/c6/realtime/scripts). Do NOT enable --record-sfo-gates.` },
  runtime: { doc: 'docs/requests/bridges_closeout.md and docs/requests/env_closeout.md',
    own: 'js/live/gates.js, js/world/gates.js, js/env/**, js/shaders/sprites.js, js/scene.js (only if needed), docs/requests/bridges_closeout.md, docs/requests/env_closeout.md.',
    focus: `(1) ${SP}/c6_r6verify_runtime.json: at the steepest up-slope docks the flat corridor roof ends inside tunnel A's end frame but stands up to 12 mm above the frame's sloped top face -- close it.
(2) Rest poses per occupant (static verifier R6.2, 24 'accepted, parked while the bridge rests' WARNs in tools/sat/check.py / check_stands, e.g. G12 L2 1.0 m from a B736, G13 L2 3.8 m from a B752, A6/A9/A10 L2 1.1-1.4 m): in gates.js choose each bridge's rest pose per actual occupant (retract / swing an L2 clear of the occupant's wing, engine and tailplane by its ICAO code clearance, checked against the pushback tail swing), keeping the mapped rest when no aircraft is there. Show the at-rest contact numbers before/after (bridge suite + the round-5 static replay numbers DAL672 C9 L1 14 fr, SWA375 D3 L1 8 fr if cheap) and that plans stay 3,331 / 78 refused or explain each change.
(3) The pre-existing G12 L1 drum-edge 5-cm sliver noted in round 6, if cheap.` },
  aircraft: { doc: 'docs/requests/aircraft_closeout.md',
    own: 'js/aircraft/**, tools/models/** (incl. model_features.py, skin_check), data/models/** (features.json, manifest.js, *.sfom via the tools), tools/liveries/** and data/liveries/** (re-bakes allowed this round, under the heavy lock), docs/requests/aircraft_closeout.md.',
    focus: `All 5 residuals in ${SP}/c6_r6verify_aircraft.json:
(1) correct the hwl_guard robustness claim (comment + closeout) to the measured safe range;
(2) the three table-row wording slips;
(3) the pre-existing wide-body under-read ahead of 0.45 L (A350-900 X22.5-32.5 reads ~2.45 m vs mesh ~2.98 m at keel + 1.4 m; LO_FWD cap 1.0 where sec has no hwf rows) -- fix at the root, skin_check per-row before/after, consumers unchanged;
(4) the cowl-top / pylon sawtooth on the dark-engine A350 and MD-11 bakes: paint the over-cowl junction by angle around the nacelle axis (eng_angle ~ +-10 deg) in paint.py, re-bake the affected models' bakes (hi/mid/lo) one at a time under the heavy lock, label-diff + before/after crops (one small render), manifests;
(5) the Full phone artifact staleness is the lead's (ignore).` },
  buildings: { doc: 'docs/requests/buildings_closeout.md and docs/requests/integration_closeout.md',
    own: 'tools/blender/**, tools/buildings/**, data/buildings3d/** (glb, lod2, integration.{json,js}, manifest.json under its flock), docs/requests/buildings_closeout.md, docs/requests/integration_closeout.md.',
    focus: `All 5 residuals in ${SP}/c6_r6verify_buildings.json, plus request C5.1:
(1) Grand Hyatt: the new gh_bridge is a 5-m stub that ends 0.15 m short of the guideway and lands ~9 m above the model's own 4th floor. Connect it to the HYATT station platform / deck (clipped by the keep-out and vehicle envelope) and reconcile the hotel's floor heights with the [pub] fact that the AirTrain connects at the 4th floor (spec_landside.json gh_lobby_level, landside_airtrain STATIONS['HYATT']): re-derive the storey heights only from sourced data (tag inferred what is not), all LODs.
(2) the CG LOD2 deck-box residual (311 m2, 0.69 m): same root cause as round-6 item (b) -- apply the plinth-top fix at LOD2 too.
(3) LOD1 fold gate: make it fail the build (gfail) above its ceiling and read the manifest flag.
(4) b3d_integrate: a dump with zero bridges (or a bridge count below the scene's) must be a CONFLICT 'input stale'.
(5) the remaining wording / record items.
(6) request C5.1 (realtime): provenance and height band of integration.js physics.rings[82] (UAL1757 wing / CFJNX 5 frames, bbox x -1594.7..-1323.0, z 243.8..356.1) and of the SFO Museum 'Garage A' outline in the building grid near (-1328, 535) (AMX664); if a ring is an elevated walkway / canopy above wing height, give it its height band so ground aircraft do not collide with it.
Rebuild only what you change (one at a time under the heavy lock); re-run verify_landside / verify_itb / verify_domestic / b3d_integrate / lod2 check / tools/sat/check.py as relevant.` },
  static: { doc: 'docs/requests/static_closeout.md',
    own: 'data/sfo_stands.*, tools/stands/**, data/sfo_pavement.*, data/sfo_paint.*, tools/sat/** (incl. paint_pave_naip.py, check.py, check_stands), tools/imagery/**, tools/build_landside.py + data/sfo_landside.*, docs/requests/static_closeout.md.',
    focus: `The residuals in ${SP}/c5_r5verify1_static.json (findings 1-5; finding 6 F16 is fixed) plus request C5.3:
(1) P13 stop_open: store each aircraft's still duration and fix count; require a minimum duration (60-180 s, as P9) or label short groups 'last still report before the signal ended'; redo the F19/F20 evidence text.
(2) correct R6.1.3 / R5.1.4 (the app clamps parked noses to between 25 m short of the drawn stop and the stop).
(3) landside w_src wording for kept runs inside pieces that are then not drawn; rerun build_landside (md5-reproducible).
(4) the P10 comment / closeout: add the current-code numbers (the static verifier's).
(5) C5.3: the rendered pavement mask does not cover 37.6250 N -122.3991 W (west maintenance area) where ASA503 B39M stood 11 h per ADS-B; extend the apron mask there, checked against NAIP (public domain), keeping provenance tags; paint_pave_naip under the heavy lock, md5-reproducible; re-run check.py / check_stands.
(6) rest poses per occupant are the runtime track's this round (gates.js) -- coordinate only via requests.` },
}
const RES = { type: 'object', properties: {
  dispositions: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, status: { type: 'string', enum: ['fixed', 'partly', 'deferred', 'rejected', 'needs_owner'] }, evidence: { type: 'string' } }, required: ['id', 'status', 'evidence'] } },
  files: { type: 'array', items: { type: 'string' } }, metrics: { type: 'string' }, renders: { type: 'array', items: { type: 'string' } },
  open_questions: { type: 'array', items: { type: 'string' } }, usage_at_end: { type: 'string' }, summary: { type: 'string' } }, required: ['dispositions', 'files', 'summary'] }
const FIND = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['critical', 'major', 'minor'] }, where: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'where', 'problem', 'evidence', 'fix'] } },
  metrics: { type: 'string' }, renders: { type: 'array', items: { type: 'string' } }, usage_at_end: { type: 'string' }, summary: { type: 'string' } }, required: ['findings', 'summary'] }
const J = o => JSON.stringify(o, null, 1)
const fix = t => agent(`${BASE}\n\nTRACK: ${t} (round 7 fix). You OWN: ${TRACKS[t].own}\nFocus:\n${TRACKS[t].focus}\n\nFix each item at its root cause; re-run the track's checks with numbers before / after (same harness / script on both arms); give evidence for anything you reject or defer; needs_owner items: do not guess, document. Work log: SP/c7/${t}/NOTES.md. Closeout doc(s): ${TRACKS[t].doc}. Finish with the StructuredOutput report (dispositions per item, files changed, metrics, renders, open questions, usage_at_end, summary).`, { label: `r7fix:${t}`, phase: 'Fix', schema: RES })
const verify = (tracks, fxs) => agent(`${BASE}\n\nINDEPENDENT VERIFIER (round 7) for track(s): ${tracks.join(' + ')}. Do not trust the fixer(s); read-only except your own scratch files under SP/c7/${tracks.join('_')}_ver/ (no edits to the repo). Focus list(s) the fixer(s) worked on:\n${tracks.map(t => `[${t}] ${TRACKS[t].focus}`).join('\n\n')}\n\nThe fixer report(s), in full:\n${J(fxs)}\n\nCheck EVERY item on the current files: fixed (re-run the check yourself, same harness / script on both arms; economical), partly, or not fixed. Then hunt briefly for regressions the fix introduced (same family of defect elsewhere, other LODs of the Full version, neighbouring tracks' files that depend on what changed). Report every residual or new problem with severity, where, problem, evidence and the fix you suggest. Finish with the StructuredOutput report (usage_at_end = the usage_meter estimate when you finished).`, { label: `r7verify:${tracks.join('+')}`, phase: 'Verify', schema: FIND })
const chain = async (tracks) => {
  const fxs = {}
  for (const t of tracks) { fxs[t] = await fix(t) }
  if (!Object.values(fxs).some(Boolean)) return { fxs, vf: null }
  const vf = await verify(tracks, fxs)
  if (vf) log(`${tracks.join('+')}: ${vf.findings.length} residual (${vf.findings.filter(f => f.severity !== 'minor').length} critical/major)`)
  return { fxs, vf }
}
const GROUPS = [['realtime'], ['aircraft'], ['buildings'], ['runtime', 'static']]
const out = await parallel(GROUPS.map(g => () => chain(g)))
return Object.fromEntries(GROUPS.map((g, i) => [g.join('+'), out[i]]))
