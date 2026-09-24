# Items from the PY worker

## To lighting + integration (`test/qa.js`)

1. **`q13_pyFront` cannot be rated** (py_r3 high issue): its camera sits in the J/PY bulkhead / curtain, so no PY seat
   front is visible. The monuments worker's `__rel('25C', 0.35, 1.75, -0.72, ...)` also works. The PY worker rated with
   a camera over the right aisle just aft of the bulkhead, looking aft toward the centre block. Its framing is closest to
   py_37302 (H/K pair and windows on the left, the centre block large on the right):
   `q13_pyFront: [\`__rel('25G', 0.52, 1.95, -0.35, Math.PI-0.35, -0.42)\`, ['py_37302'], 'PY cabin from the front']`
2. Optional: add a PY seat-back view (real photos ref/web/py san_05 / san_13 / alv_03):
   `q13b_pyBacks: [\`__rel('26H', 0.1, 1.45, 1.25, 0.05, -0.3)\`, ['py_37304'], 'PY seat backs, screens, pockets']`.

## To monuments (`src/10_mono.js`)

- Row 25 faces the J/PY bulkhead, which carries wall-mounted monitors and literature pockets (real photos ref/web/py
  alv_14 / alv_15 / san_03, and ANA py_37303). The monitors are already modelled (`monitor: true`); please check them
  against alv_14 (two monitors per seat pair at about eye height, with grey pockets below).
