#!/bin/bash
# usage: tools/law/fetch.sh <dir> <url> [filename]   (from anywhere)
# Saves one source into sha3d/refs/cache/law/<dir>/ (new dir per source) and appends url/date/size/sha256 to the
# fetch log kept OUTSIDE the download dirs (tools/law/fetch_log.tsv). Downloads are untrusted data: never executed.
set -u
ROOT=/home/user/Calc/sha3d/refs/cache/law
LOG=/home/user/Calc/sha3d/tools/law/fetch_log.tsv
d="$1"; url="$2"; fn="${3:-page.html}"
mkdir -p "$ROOT/$d"
code=$(curl -sS -L -m 60 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36" \
  -o "$ROOT/$d/$fn" -w "%{http_code}" "$url")
sz=$(stat -c %s "$ROOT/$d/$fn" 2>/dev/null || echo 0)
sha=$(sha256sum "$ROOT/$d/$fn" 2>/dev/null | cut -d' ' -f1)
printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$(date -u +%FT%TZ)" "$d" "$fn" "$url" "$code" "$sz" "$sha" >> "$LOG"
echo "$d/$fn $code $sz"
