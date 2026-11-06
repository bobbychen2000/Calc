#!/usr/bin/env bash
# Rebuild what a recreated container lost (refs/cache is gitignored; tools/cache/sync.py commits what it may).
#   1. ADS-B: the committed trimmed adsb.lol hours (refs/cache/rec_pack/) back into refs/cache/rec/ where an hour is missing
#   2. NAIP 2024 (USDA, public domain): tools/imagery/naip_fetch.py --source usda + naip_world.py, checked against the
#      SHA-256 in refs/MANIFEST.json (a mismatch is reported, not fatal: USDA may re-serve the tiles)
#   2b. npm tool packages under refs/cache/*/node (gltf-validator, gltf-transform, meshoptimizer, sharp): reinstalled from
#      their committed package-lock.json with npm ci --prefix <dir> (a separate prefix: the repo-root playwright pin is untouched)
#   3. workflow journals: .wf/journals/<run>.jsonl -> the session's subagents/workflows/<run>/journal.jsonl (pass the
#      session's transcript directory as $1 to enable Workflow resumeFromRunId after a container loss)
# Dependencies: pip install numpy scipy shapely opencv-python-headless pillow matplotlib pyproj rasterio;
#               npm ci, then (when the preinstalled Chromium is newer) npm i --no-save playwright@<its version>.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p refs/cache/rec
for f in refs/cache/rec_pack/adsblol_*.jsonl.xz; do       # xz packs -> the recorder's gzip format (tools/live/recio.py)
  [ -e "$f" ] || continue
  b=$(basename "$f" .xz).gz; [ -e "refs/cache/rec/$b" ] || python3 -c 'import gzip,lzma,shutil,sys; shutil.copyfileobj(lzma.open(sys.argv[1]), gzip.open(sys.argv[2], "wb", 6))' "$f" "refs/cache/rec/$b"
done
if [ ! -e refs/cache/naip/naip_2024_world_0.5m.png ]; then
  python3 tools/imagery/naip_fetch.py --source usda
  python3 tools/imagery/naip_world.py --year 2024 --res 0.5
fi
python3 - <<'PY'
import hashlib, json, os
m = json.load(open('refs/MANIFEST.json'))['files'] if os.path.exists('refs/MANIFEST.json') else {}
for rel in ('naip/naip_2024_sfo_utm10n.tif', 'naip/naip_2024_world_0.5m.png'):
    p = os.path.join('refs/cache', rel)
    if rel in m and os.path.exists(p):
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        print(rel, 'sha256 OK' if h == m[rel]['sha256'] else f'sha256 DIFFERS from the manifest ({h[:12]} vs {m[rel]["sha256"][:12]})')
PY
for d in refs/cache/*/node; do                            # 2b: npm tool packages (not committed)
  [ -f "$d/package-lock.json" ] && [ ! -d "$d/node_modules" ] && npm ci --prefix "$d" --no-audit --no-fund || true
done
if [ -n "${1:-}" ]; then
  for j in .wf/journals/wf_*.jsonl; do
    [ -e "$j" ] || continue
    run=$(basename "$j" .jsonl); mkdir -p "$1/subagents/workflows/$run"
    [ -e "$1/subagents/workflows/$run/journal.jsonl" ] || cp "$j" "$1/subagents/workflows/$run/journal.jsonl"
  done
fi
echo "restore done"
