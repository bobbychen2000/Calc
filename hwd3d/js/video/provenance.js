// Provenance of the hero's current sample, and the per-frame caption state of the OD3 videos (hwd3d Phase 3, video).
// Pure ES module (no DOM): js/video/director.js classifies each frame's sample from the track's own fixes (sampleSrc, page
// side, recorded in the scout trace); tools/video/render.mjs `plan` turns the trace into the caption state of every frame
// (captionTrack, Node side), stored in cams.json and handed to the overlay frame by frame - so the pill and the phase line
// are the same in a split, resumed or picked render as in one straight run.
//
// Classes (the pill colour, js/video/overlay.js):
//   obs  between two fixes <= HOLE_S apart                                   "Recorded ADS-B position"
//   inf  a recorder hole (HOLE_S < gap <= NOSIG_S), no start / stop / take-off / landing inside, or after the newest fix
//                                                                            "Interpolated between ADS-B fixes · recorder gap of N s"
//   rec  a ground <-> air transition inside a hole (the roll and lift-off / touchdown have no fix at all), or a hole in
//        which the aircraft starts or stops moving (when it does is the engine's guess)
//                                                                            "Reconstructed (no ADS-B fix) · ..."
//   nos  a gap far longer than the recorder's duty-cycle hole (> NOSIG_S): the transponder itself was silent
//                                                                            "No ADS-B signal for N s · position inferred"
export const HOLE_S = 8;          // s: js/live/classifier.js HOLE_S (a gap longer than this is a recorder hole)
export const NOSIG_S = 90;        // s: the recorder saw ~14 s of every minute (holes ~46 s); a gap this long is a silence
export const STILL_KT = 1, MOVING_KT = 3;
/** the fixes `F` (tr.fx: {t, g|ground, gs (kt), x, z}) around display time t -> { src, gapS, kind } */
export function sampleSrc(F, t, stale = false) {
  const n = F ? F.length : 0; if (!n) return { src: 'inf', gapS: null, kind: 'nofix' };
  if (stale) return { src: 'inf', gapS: null, kind: 'stale' };
  if (t >= F[n - 1].t) return { src: 'inf', gapS: null, kind: 'after' };
  if (t <= F[0].t) return { src: 'inf', gapS: null, kind: 'before' };
  let i = n - 1; while (i > 0 && F[i - 1].t > t) i--;
  const a = F[i - 1], b = F[i], gap = (b.t - a.t) / 1000;
  if (gap <= HOLE_S) return { src: 'obs', gapS: +gap.toFixed(1), kind: 'fix' };
  const ga = a.ground ?? a.g, gb = b.ground ?? b.g, G = Math.round(gap);
  if (ga !== gb) return { src: 'rec', gapS: G, kind: ga ? 'takeoff' : 'landing' };
  if (ga && gb) {
    const sa = a.gs ?? 0, sb = b.gs ?? 0;
    if (sa < STILL_KT && sb > MOVING_KT) return { src: 'rec', gapS: G, kind: 'start' };
    if (sa > MOVING_KT && sb < STILL_KT) return { src: 'rec', gapS: G, kind: 'stop' };
  }
  if (gap > NOSIG_S) return { src: 'nos', gapS: G, kind: 'silent' };
  return { src: 'inf', gapS: G, kind: 'hole' };
}
/** pill text of a classified sample */
export function pillText(p) {
  const g = p.gapS;
  switch (p.src) {
    case 'obs': return ['Recorded ADS-B position', ''];
    case 'rec':
      if (p.kind === 'takeoff') return ['Reconstructed (no ADS-B fix)', `${g} s between the last ground and the first airborne fix`];
      if (p.kind === 'landing') return ['Reconstructed (no ADS-B fix)', `${g} s between the last airborne and the first ground fix`];
      if (p.kind === 'start') return ['Reconstructed (no ADS-B fix)', `no fix for ${g} s: when it starts to move is inferred`];
      if (p.kind === 'stop') return ['Reconstructed (no ADS-B fix)', `no fix for ${g} s: when it stops is inferred`];
      return ['Reconstructed (no ADS-B fix)', g ? `no fix for ${g} s` : ''];
    case 'nos': return [`No ADS-B signal for ${g} s`, 'position inferred'];
    default:
      if (p.kind === 'hole') return ['Interpolated between ADS-B fixes', `recorder gap of ${g} s`];
      if (p.kind === 'after' || p.kind === 'stale') return ['Extrapolated after the last ADS-B fix', ''];
      return ['Inferred (no ADS-B fix yet)', ''];
  }
}
/** a state shown for fewer than `minFrames` frames is not shown: those frames keep the state on screen before them (the
 *  first run of the video or of a shot - `cuts`, the frames where a shot starts - takes the state after it). One forward
 *  pass, so the result of frame f depends on the trace and the cuts only, never on where a render starts. `key(i)` names
 *  frame i's state; returns the frame -> source-frame index map. */
export function holdRuns(n, key, minFrames, cuts = []) {
  const idx = new Array(n), runs = [], cut = new Set(cuts);
  for (let i = 0; i < n;) { let j = i; const k = key(i); while (j < n && key(j) === k && (j === i || !cut.has(j))) j++; runs.push([i, j]); i = j; }
  let shown = null;                    // source frame of the state on screen
  for (let r = 0; r < runs.length; r++) {
    const [i, j] = runs[r]; if (cut.has(i)) shown = null;
    const nx = runs[r + 1], nxSameShot = nx && !cut.has(nx[0]);
    if (j - i >= minFrames || (shown == null && !nxSameShot)) { for (let q = i; q < j; q++) idx[q] = q; shown = j - 1; continue; }
    const src = shown != null ? shown : nx[0];
    for (let q = i; q < j; q++) idx[q] = src;
    if (shown == null) shown = src;
  }
  return idx;
}
/** the caption state of every frame from the scout trace: { phase, cls, text, sub }.
 *  - the phase line is the app's own label ("(provisional)" dropped) except that a hero standing still on the ground
 *    (gs < 0.5 kt for >= stillS s of data time) that the app still calls "Taxiing" is shown as "Stopped" [inf: a video rule,
 *    the classifier item in docs/phase3_video.md section 8];
 *  - pill and phase line hold every state for at least minS s of VIDEO (time-lapse: a 14-s observed window passes in a few
 *    frames at 24x) */
export function captionTrack(trace, { fps = 30, minS = 0.5, stillS = 2, cuts = [] } = {}) {
  const n = trace.length, minF = Math.max(1, Math.round(minS * fps));
  const phase = new Array(n), still = new Array(n).fill(0);
  let since = null;
  for (let f = 0; f < n; f++) {
    const p = trace[f] || {};
    const st = p.found !== false && p.valid && p.ground && (p.gs ?? 99) < 0.5;
    since = st ? (since ?? p.t) : null; still[f] = st ? (p.t - since) / 1000 : 0;
    let L = p.label || '';
    if (L === 'Taxiing' && st && still[f] >= stillS) L = 'Stopped';
    phase[f] = L;
  }
  const pill = trace.map(p => { const [t, s] = pillText(p || {}); return { cls: (p && p.src) || 'inf', text: t, sub: s }; });
  const pk = (i) => pill[i].cls + '|' + pill[i].text + '|' + pill[i].sub;
  const ip = holdRuns(n, pk, minF, cuts), il = holdRuns(n, (i) => phase[i], minF, cuts);
  const out = new Array(n);
  for (let f = 0; f < n; f++) out[f] = { phase: phase[il[f]], ...pill[ip[f]], held: ip[f] !== f || il[f] !== f ? 1 : 0 };
  return out;
}
