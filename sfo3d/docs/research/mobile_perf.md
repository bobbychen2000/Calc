# Mobile performance — status (deferred by the owner, 26 Sep 2026; revisit at the end)

## Measured on the owner's phone (phone-test artifact https://claude.ai/artifact/2ekxFtAwbF4vVMKSxTrkEY, commit 4ea28df)

Device: iPhone, iOS 18.7, inside the Claude app (UA `... Mobile/15E148 Claude/1.260916.19`), GPU "Apple GPU".

| Run | Backend | Tier | fps (10 s) | frame p50 / p95 | load | canvas |
|---|---|---|---|---|---|---|
| 1 | WebGPU (reversed depth) | low | 16.8 | 33 / 89 ms | 6.7 s | 516x1048 @ dpr 3 |
| 2 | WebGPU (reversed depth) | low | 16.7 | 34 / 128 ms | 2.7 s (cached) | 860x1746 @ dpr 3 |

Reading: WebGPU works in the Claude app on iOS 18.7. The frame rate did not change when the canvas grew 2.8x in pixels
(run 2), which suggests the cost is per-frame work (passes, draw calls, JS, stalls) rather than fill rate alone; the
p95 (89-128 ms) shows regular long frames. Target when revisited: >= 30 fps sustained, p95 <= 40 ms.

## Work started, then stopped (owner deprioritised it)

- `js/three/perf.js`: runtime flags (window.SFO_PERF) and per-frame timing; `js/three/engine.js` has two inert hooks
  (`Q.ao === 'none'` = one scene pass without GTAO; `Q.aa === 'fxaa'` = FXAA instead of TRAA) that no shipped tier uses.
- `tools/build3/phone_bench_prof*.{mjs,js}`: start of a profiling harness.
- Plan when resumed: a benchmark-sweep build of the phone artifact (AO / TRAA / bloom / cascades / render scale isolated,
  CPU split per frame, draw calls, GPU time where timestamp-query exists), then a 'phone' tier with dynamic resolution
  targeting 30 fps. The workflow script is kept locally in .wf/sfo-mobile-perf-*.js.
