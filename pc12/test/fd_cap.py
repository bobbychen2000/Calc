"""Flight-deck capture harness (track: first-principles flight deck): renders the standard flight-deck views of the
viewer -- the crew / fd_cabin tour stops, the Cockpit preset, the photo-fitted panel_408b, and close-ups -- for
before / after comparisons and the judges.

    python3 test/fd_cap.py OUTDIR [--glb ../out/x.glb] [--query '&fp=1'] [--views pilot,panel_408b,...] [--size 1200x900]

Headless Chromium + SwiftShader through test/viewer_test.py's server / launcher; High quality, 4 still passes."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test"))
import viewer_test as VT  # noqa: E402

# close-up poses (model axes: x STA aft, y BL starboard, z WL); eye / target / vertical fov
CLOSE = {
    "pedestal": {"eye": [4.25, 0.00, 2.05], "target": [3.75, 0.00, 1.62], "fov": 45},
    "quadrant": {"eye": [4.12, 0.10, 1.98], "target": [3.90, 0.00, 1.57], "fov": 40},
    "panel_l": {"eye": [4.00, -0.38, 2.05], "target": [3.50, -0.38, 1.80], "fov": 45},
    "panel_r": {"eye": [4.00, 0.38, 2.05], "target": [3.50, 0.38, 1.80], "fov": 45},
    "yoke_l": {"eye": [3.95, -0.37, 2.10], "target": [3.55, -0.37, 1.88], "fov": 40},
    "hood": {"eye": [4.15, -0.30, 2.40], "target": [3.45, 0.05, 2.12], "fov": 50},
    "overhead": {"eye": [4.30, 0.00, 2.20], "target": [3.95, 0.00, 2.62], "fov": 55},
    "cb_left": {"eye": [4.05, -0.15, 2.20], "target": [3.90, -0.60, 1.85], "fov": 50},
    "seats_aft": {"eye": [5.00, 0.00, 2.15], "target": [4.25, 0.00, 1.75], "fov": 50},
    "post_l": {"eye": [4.10, -0.25, 2.30], "target": [3.55, -0.50, 2.40], "fov": 45},
    "footwell_l": {"eye": [3.95, -0.30, 1.95], "target": [3.40, -0.36, 1.40], "fov": 50},
}
DEFAULT = ["pilot", "copilot", "fd_cabin", "panel_408b", "pedestal", "quadrant", "panel_l", "yoke_l", "hood",
           "overhead", "cb_left", "seats_aft", "post_l", "footwell_l"]


async def main(a):
    from playwright.async_api import async_playwright
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    srv = VT.start_server()
    port = srv.server_address[1]
    W, H = map(int, a.size.split("x"))
    q = f"http://127.0.0.1:{port}/web/index.html?three=local&quality=high&ssframes={a.ss}" + a.query
    if a.glb:
        q += f"&glb={a.glb}"
    views = a.views.split(",") if a.views else DEFAULT
    async with async_playwright() as pw:
        b = await VT.launch(pw)
        ctx = await b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1, reduced_motion="reduce")
        pg = await ctx.new_page()
        pg.set_default_timeout(1800000)
        import time as _t
        t0 = _t.time()
        await pg.goto(q, wait_until="domcontentloaded", timeout=600000)
        await pg.wait_for_function("window.__ready === true", timeout=900000)
        print(f"ready {_t.time() - t0:.0f}s", flush=True)
        await pg.evaluate(VT.JS_HELPERS)
        V = "const V = window.viewer, T = V.tour; "
        await VT.js(pg, V + "window.T.neutral(); V.setStep('paint', {instant: true}); V.panel(false);"
                            "await new Promise(r => setTimeout(r, 300));")
        for v in views:
            if v in ("pilot", "copilot", "fd_cabin"):
                await VT.js(pg, V + "T.enter(arg, {motion: false}); T.finish(); V.advance(0.5);", v)
            elif v == "cockpit":
                await VT.js(pg, V + "V.setCamera('cockpit', {instant: true}); V.advance(0.5);")
            else:
                cam = VT.photo_cam(v) if v in VT.PHOTO_CAMS else CLOSE[v]
                await VT.js(pg, V + "if (!T.inside) { T.enter('pilot', {motion: false}); T.finish(); } "
                                    "T.place(arg, {clamp: false}); V.advance(0.5);", cam)
            await VT.js(pg, "await window.viewer.frames(6);")
            print(f"  posed {v} {_t.time() - t0:.0f}s", flush=True)
            # wait for the still refinement to finish
            await VT.js(pg, "const h = document.getElementById('tourHint'); if (h) h.style.visibility = 'hidden';")
            await VT.js(pg, f"await window.viewer.frames({int(a.ss) + 2});")
            p = out / f"{v}.png"
            await pg.screenshot(path=str(p), timeout=1800000)
            print("shot", p, flush=True)
            if v in ("pilot", "copilot", "fd_cabin"):
                await VT.js(pg, V + "T.exit({motion: false}); await V.frames(1);")
        await b.close()
    srv.shutdown()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--glb", default="")
    ap.add_argument("--query", default="")
    ap.add_argument("--views", default="")
    ap.add_argument("--size", default="1200x900")
    ap.add_argument("--ss", default="4")
    asyncio.run(main(ap.parse_args()))
