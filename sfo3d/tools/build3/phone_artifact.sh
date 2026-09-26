#!/bin/sh
# Build the phone-test artifact (claude.ai artifact, snapshot mode) from a commit, in a clean copy.
#   sh tools/build3/phone_artifact.sh [commit=HEAD] [outdir=out/phone_artifact]
# Output: <outdir>/pub/sfo_phone_test.html (app bundle inlined, live.css inlined, test card) + supporting files:
#   assets/ (MSDF sign atlas), data/models/*.wasm (the .sfom models renamed: artifacts serve only standard web types,
#   and the app fetches the bytes with SFO_MODEL_EXT='.wasm'), data/liveries/*/*-lo.webp (low-resolution livery set).
# Publish with the Artifact tool: file_path=<outdir>/pub/sfo_phone_test.html, root=<outdir>/pub, files=every other file.
# First published 26 Sep 2026 as https://claude.ai/artifact/2ekxFtAwbF4vVMKSxTrkEY (private).
set -e
C=${1:-HEAD}; OUT=${2:-out/phone_artifact}; ROOT=$(cd "$(dirname "$0")/../.." && pwd)
rm -rf "$OUT/src" "$OUT/pub"; mkdir -p "$OUT/src"
git -C "$ROOT" archive "$C" . | tar -x -C "$OUT/src"
ln -s "$ROOT/node_modules" "$OUT/src/node_modules"
(cd "$OUT/src" && node tools/build3/build.mjs --app)
python3 "$ROOT/tools/build3/phone_artifact_page.py" "$OUT/src" "$OUT/pub"
