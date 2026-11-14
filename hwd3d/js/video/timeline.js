// Frame schedule of an OD3 video (hwd3d Phase 3, video). Pure ES module (no DOM): the driver (tools/video/render.mjs, Node)
// builds the table and hands it to the page (js/video/director.js), which steps the app frame by frame.
//
//   buildTimeline({ segments, fps = 30, maxSub = 1 / 30, rampS = 1.0 }) -> { fps, frames, t0, t1 }
//   segments: [{ from, to, speed, label?, skip? }] in DATA time (epoch ms of the recording, the instant the app displays),
//             contiguous; speed = app seconds per video second (1 = real time, 8 = time-lapse "8x"); skip: true = a cut in
//             data time: no frame shows it, the engine still runs through it (in sub-steps of the first frame after it), and
//             the speed changes at the cut without a ramp (the camera plan must cut there too: tools/video/render.mjs plan)
//   frames[i] = { t: data time displayed by frame i (ms), dt: app ms advanced INTO frame i, n: engine sub-steps,
//                 h: sub-step (s, <= maxSub), speed (ramped), seg, nominal (the segment's speed: the overlay label),
//                 cut (s of data skipped into this frame, only on the first frame after a skip segment) }
// Speed changes are ramped over rampS video seconds (a slow-down starts BEFORE the boundary, so the real-time segment
// begins at real time; a speed-up starts at the boundary). Frame i covers (t[i] - dt, t[i]]; the first frame's dt is one
// step of its own segment. Deterministic: the same segments give the same table, bit for bit.
export function buildTimeline({ segments, fps = 30, maxSub = 1 / 30, rampS = 1.0 }) {
  if (!segments || !segments.length) throw new Error('timeline: no segments');
  const S = segments.map((s, i) => ({ ...s, i }));
  if (S[0].skip || S[S.length - 1].skip) throw new Error('timeline: the first and the last segment cannot be skipped');
  for (let i = 1; i < S.length; i++) if (S[i].skip && S[i - 1].skip) throw new Error('timeline: two skip segments in a row');
  for (let i = 1; i < S.length; i++) if (Math.abs(S[i].from - S[i - 1].to) > 1) throw new Error(`timeline: segment ${i} does not start where ${i - 1} ends`);
  const t1 = S[S.length - 1].to; const frames = [];
  let t = S[0].from, s = S[0].speed, k = 0, lastTarget = s, rate = 0, latch = -1;
  const segAt = (tt) => { while (k < S.length - 1 && tt >= S[k].to - 1e-6) k++; return S[k]; };
  for (let guard = 0; guard < 1e6; guard++) {
    const g = segAt(t); const nx = S[g.i + 1];
    let target = g.speed;
    // slow-down ahead: start when the data time left before the boundary is what the ramp will cover
    // (latched once started: the coverage shrinks as the speed drops)
    if (nx && !nx.skip && (latch === g.i || (nx.speed < s && (g.to - t) <= 0.5 * (s + nx.speed) * rampS * 1000))) { target = nx.speed; latch = g.i; }
    if (target !== lastTarget) { rate = Math.abs(target - s) / Math.max(1, rampS * fps); lastTarget = target; }   // a linear ramp
    if (target > s) s = Math.min(target, s + rate); else if (target < s) s = Math.max(target, s - rate);
    const dtS = s / fps, n = Math.max(1, Math.ceil(dtS / maxSub - 1e-9)), dt = dtS * 1000;
    if (frames.length === 0) { frames.push({ t, dt, n, h: dtS / n, speed: s, seg: g.i, nominal: g.speed }); continue; }   // frame 0 shows the start
    t += dt; if (t > t1 + 1e-6) break;
    let gs = segAt(t);
    if (gs.skip) {   // a cut: jump to the end of the skipped segment; the speed of the next one applies at once
      const cut = gs.to - t; t = gs.to; gs = segAt(t); s = gs.speed; lastTarget = s; rate = 0; latch = -1;
      const dF = dt + cut, nF = Math.max(1, Math.ceil(dF / 1000 / maxSub - 1e-9));
      frames.push({ t, dt: dF, n: nF, h: dF / 1000 / nF, speed: s, seg: gs.i, nominal: gs.speed, cut: +(cut / 1000).toFixed(3) }); continue;
    }
    frames.push({ t, dt, n, h: dtS / n, speed: s, seg: gs.i, nominal: gs.speed });
  }
  return { fps, frames, t0: frames[0].t, t1: frames[frames.length - 1].t };
}
/** the speed label shown in the overlay ("8x") or null at (near) real time */
export const speedLabel = (s) => s >= 1.5 ? (Math.abs(s - Math.round(s)) < 0.05 ? Math.round(s) : s.toFixed(1)) + '×' : null;
