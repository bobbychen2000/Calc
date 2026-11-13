#!/usr/bin/env python3
"""List every file under refs/cache/ with size and SHA-256 in refs/MANIFEST.json, and whether it is committed
(redistributable, staged with git add -f) or kept local. Mirrors sfo3d's tools/cache/sync.py idea: after a container
loss the manifest says what to re-fetch (each directory's SOURCES.json has the URL) and lets a re-fetch be checked.
Usage (from sha3d/): python3 -I tools/cache_manifest.py"""
import hashlib, json, os, subprocess
root = "refs/cache"; out = {}
tracked = set(subprocess.run(["git", "ls-files", root], capture_output=True, text=True).stdout.split())
for d, _, fs in os.walk(root):
    for f in sorted(fs):
        p = os.path.join(d, f)
        if "/live/" in p + "/": continue  # raw live recordings (adsb.fi / OpenSky terms): local only, not listed
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        out[p] = {"bytes": os.path.getsize(p), "sha256": h, "committed": p in tracked}
json.dump({"note": "refs/cache inventory; see SOURCES.json in each directory for URL, licence and redistribution",
           "files": dict(sorted(out.items()))}, open("refs/MANIFEST.json", "w"), indent=0)
print(len(out), "files,", sum(v["bytes"] for v in out.values()) // 1_000_000, "MB,", sum(v["committed"] for v in out.values()), "committed")
