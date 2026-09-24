#!/usr/bin/env bash
# Bring a fresh machine / cloud container up to a working state for the PC-12 project.
#   ./setup.sh            python deps + three.js r160 (web/three_local) + reference PDF
#   ./setup.sh --blender  also Blender 5.0 as a Python module in /opt/venv-blender (~375 MB)
#   ./setup.sh --photos   also re-download the reference photos listed in refs/photos.json
# Idempotent: skips whatever is already present.
set -euo pipefail
cd "$(dirname "$0")"

want_blender=0; want_photos=0
for a in "$@"; do
  case "$a" in
    --blender) want_blender=1 ;;
    --photos)  want_photos=1 ;;
    *) echo "unknown option $a" >&2; exit 2 ;;
  esac
done

# numpy 2.x: the model build is byte-reproducible with it (numpy 1.26 changes float rounding)
python3 -c "import numpy, scipy, matplotlib, PIL, reportlab, playwright, pymupdf" 2>/dev/null || \
  pip install -q "numpy>=2" scipy matplotlib pillow reportlab playwright lxml pymupdf

# three.js r160 for the dev harness and offline viewer tests (?three=local); not committed
if [ ! -f web/three_local/build/three.module.js ]; then
  tmp=$(mktemp -d)
  (cd "$tmp" && npm pack three@0.160.0 --silent >/dev/null && tar xzf three-0.160.0.tgz)
  mkdir -p web/three_local
  cp -r "$tmp/package/build" "$tmp/package/examples" web/three_local/
  rm -rf "$tmp"
fi

# Pilatus PC-12 NGX Model Building Plan (reference drawing; gitignored cache, never committed)
mkdir -p refs/cache out/tmp
pdf=refs/cache/PC-12-NGX-Model-Building-Plan.pdf
[ -f "$pdf" ] || curl -sSfL -A "Mozilla/5.0" -o "$pdf" \
  "https://www.pilatus-aircraft.com/assets/files/Model-Building-Plans/PC-12-NGX-Model-Building-Plan.pdf"

if [ "$want_blender" = 1 ] && [ ! -x /opt/venv-blender/bin/python ]; then
  # separate venv: the bpy wheel pins numpy 1.x, which must not leak into the model environment
  python3 -m venv /opt/venv-blender
  /opt/venv-blender/bin/pip install -q bpy pillow
fi

if [ "$want_photos" = 1 ] && [ -f refs/fetch_photos.py ]; then
  python3 refs/fetch_photos.py
fi

echo "setup ok: $(python3 -c 'import numpy; print("numpy", numpy.__version__)')," \
     "three.js $( [ -f web/three_local/build/three.module.js ] && echo r160 || echo missing )," \
     "blender $( [ -x /opt/venv-blender/bin/python ] && echo yes || echo no )"
