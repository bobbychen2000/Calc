#!/usr/bin/env python3
"""Download the reference photographs listed in refs/photos.json into refs/cache/photos/.

The photos are third-party material (Pilatus press/web images, Wikimedia Commons
files under CC licences) and are NOT committed to this public repository; only the
manifest (refs/photos.json) and the observations (refs/photo_notes.md) are tracked.

    python3 refs/fetch_photos.py              # fetch missing files
    python3 refs/fetch_photos.py --force      # re-download everything
    python3 refs/fetch_photos.py --only pro3010_rfds_port_pilatus ngx2243_hbfxk_stbd
    python3 refs/fetch_photos.py --dest /tmp/photos   # alternative target directory

Politeness: one request at a time, a short pause between requests, an identifying
User-Agent, and exponential back-off on HTTP 429/5xx (Wikimedia rate-limits scripted
downloads; the manifest therefore points at standard-size Commons thumbnails, not at
originals).  Standard library only; Pillow is used for a sanity check if installed.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "photos.json")
DEFAULT_DEST = os.path.join(HERE, "cache", "photos")
USER_AGENT = ("pc12-refs/1.0 (+https://github.com/bobbychen2000/Calc; "
              "reference-photo fetcher for a PC-12 CAD model) python-urllib")
PAUSE_S = 1.5


def fetch(url, tries=6):
    delay = 10.0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                wait = float(e.headers.get("Retry-After") or delay)
                print(f"    HTTP {e.code}, retrying in {wait:.0f} s", flush=True)
                time.sleep(wait)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < tries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def check_image(path, want_w, want_h):
    try:
        from PIL import Image
    except ImportError:
        return "unchecked (Pillow not installed)"
    with Image.open(path) as im:
        w, h = im.size
    if (w, h) != (want_w, want_h):
        return f"WARNING: size {w}x{h}, manifest says {want_w}x{want_h} (source may have changed)"
    return f"{w}x{h} ok"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    ap.add_argument("--only", nargs="*", help="photo ids to fetch (default: all)")
    ap.add_argument("--dest", default=DEFAULT_DEST, help="target directory (default: refs/cache/photos)")
    a = ap.parse_args()

    with open(MANIFEST, encoding="utf-8") as f:
        photos = json.load(f)
    if a.only:
        unknown = set(a.only) - {p["id"] for p in photos}
        if unknown:
            sys.exit(f"unknown id(s): {', '.join(sorted(unknown))}")
        photos = [p for p in photos if p["id"] in a.only]
    os.makedirs(a.dest, exist_ok=True)

    failed = []
    for p in photos:
        path = os.path.join(a.dest, p["file"])
        if os.path.exists(path) and os.path.getsize(path) > 0 and not a.force:
            print(f"skip  {p['id']} (exists)")
            continue
        print(f"get   {p['id']}  <- {p['url']}", flush=True)
        try:
            data = fetch(p["url"])
        except Exception as e:  # keep going; report at the end
            print(f"    FAILED: {e}")
            failed.append(p["id"])
            continue
        tmp = path + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        print(f"    {len(data) / 1e6:.2f} MB, {check_image(path, p['width'], p['height'])}")
        time.sleep(PAUSE_S)

    if failed:
        print(f"\n{len(failed)} failed: {', '.join(failed)} (re-run later; Wikimedia may be rate-limiting)")
        sys.exit(1)
    print(f"\ndone: {len(photos)} photo(s) in {a.dest}")


if __name__ == "__main__":
    main()
