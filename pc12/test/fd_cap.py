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
    "pedestal": {"eye": [4.10, 0.00, 1.78], "target": [3.72, 0.00, 1.42], "fov": 40},
    "quadrant": {"eye": [4.02, 0.06, 1.68], "target": [3.82, 0.00, 1.40], "fov": 36},
    "panel_l": {"eye": [4.05, -0.38, 1.85], "target": [3.45, -0.38, 1.78], "fov": 40},
    "panel_r": {"eye": [4.05, 0.38, 1.85], "target": [3.45, 0.38, 1.78], "fov": 40},
    "yoke_l": {"eye": [3.85, -0.34, 1.92], "target": [3.55, -0.36, 1.84], "fov": 38},
    "hood": {"eye": [4.15, -0.30, 2.15], "target": [3.40, 0.05, 2.02], "fov": 50},
    "overhead": {"eye": [4.30, 0.00, 1.95], "target": [3.95, 0.00, 2.55], "fov": 50},
    "cb_left": {"eye": [4.05, -0.20, 1.95], "target": [3.95, -0.60, 1.55], "fov": 45},
    "seats_aft": {"eye": [5.10, 0.00, 2.05], "target": [4.20, 0.00, 1.55], "fov": 50},
    "post_l": {"eye": [4.15, -0.20, 2.05], "target": [3.55, -0.55, 2.25], "fov": 45},
    "footwell_l": {"eye": [3.95, -0.30, 1.75], "target": [3.35, -0.36, 1.35], "fov": 50},
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
        await pg.goto(q, wait_until="domcontentloaded", timeout=600000)
        await pg.wait_for_function("window.__ready === true", timeout=900000)
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
            # wait for the still refinement to finish
            await VT.js(pg, "for (let i = 0; i < 400; i++) { const st = window.viewer._internals.stage; "
                            "if (!st.picture || st.picture.a.done) break; await window.viewer.frames(1); }")
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
