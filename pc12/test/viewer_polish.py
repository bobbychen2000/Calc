#!/usr/bin/env python3
"""Look-development screenshots + load timings of the three.js viewer (headless Chromium, SwiftShader).

Serves pc12/ (or a packaged bundle, --dist) on a free port and renders the review set into
out/tmp/viewer_polish/ (or --out):
  hero_3q        default front-port 3/4 view, panel closed (compare: Blender out/renders/hero.png)
  cockpit_glass  close-up of the windshield / PRO mask from outside (lining behind the glazing)
  side           port side (compare: side_port_ortho.png)
  top            plan view (compare: top.png)
  phone          390 x 844, touch, DPR 3 (capped by the viewer), bottom sheet
  dark_hero      prefers-color-scheme: dark, 3/4 view
  + desktop_panel (the default page as a visitor sees it) and a few mode checks (cutaway, x-ray, primer)
and prints window.viewer.perf(): navigation -> meta / glb / env / init / compiled / first frame / ready (ms),
first-render ms, renderer.info, the quality tier and the material upgrade list.

usage: python3 test/viewer_polish.py [--dist DIR] [--three local|cdn] [--only name,..] [--out DIR] [--query k=v&..]
       python3 test/viewer_polish.py --cam "pos;target;fov" --name x   (ad-hoc view, glTF axes)
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # pc12/
sys.path.insert(0, str(ROOT / "test"))
from viewer_test import launch  # noqa: E402  (same Chromium fallback logic)

ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


class Server(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def serve(directory: Path):
    srv = Server(("127.0.0.1", 0), functools.partial(Handler, directory=str(directory)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# network / CPU profiles for the phone load measurement (Chrome DevTools Protocol emulation)
NET = {
    "4g": {"latency": 60, "down_mbit": 12, "up_mbit": 3, "cpu": 4},      # typical LTE, mid-range phone CPU
    "3g": {"latency": 150, "down_mbit": 1.6, "up_mbit": 0.75, "cpu": 4},
}


async def open_page(browser, url, *, viewport, scheme="light", mobile=False, dpr=1, cdn=False, errs=None, net=None):
    ctx = await browser.new_context(viewport=viewport, device_scale_factor=dpr, is_mobile=mobile, has_touch=mobile,
                                    color_scheme=scheme, reduced_motion="reduce", ignore_https_errors=cdn)
    page = await ctx.new_page()
    if net:
        n = NET[net]
        cdp = await ctx.new_cdp_session(page)
        await cdp.send("Network.enable")
        await cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": n["latency"],
                       "downloadThroughput": n["down_mbit"] * 1e6 / 8, "uploadThroughput": n["up_mbit"] * 1e6 / 8})
        await cdp.send("Emulation.setCPUThrottlingRate", {"rate": n["cpu"]})
    if errs is not None:
        page.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        page.on("requestfailed", lambda r: errs.append(f"requestfailed: {r.url} {r.failure}") if "pc12.glb" not in r.url else None)
    # the CDN is reached through this sandbox's outbound proxy, where Chromium intermittently gives up on a
    # module fetch (net::ERR_TOO_MANY_RETRIES): retry the page load a couple of times in CDN mode
    for attempt in range(3 if cdn else 1):
        t0 = time.time()
        await page.goto(url)
        await page.wait_for_function("window.__ready === true", timeout=240000)
        wall = time.time() - t0
        err = await page.evaluate("window.__error || ''")
        if not err:
            return ctx, page, wall
        if not (cdn and ("viewer scripts" in err or "CDN" in err)):
            break
        print(f"  CDN load failed (attempt {attempt + 1}), retrying")
    raise RuntimeError(err + ("\n" + "\n".join(errs[-8:]) if errs else ""))


async def js(page, body):
    return await page.evaluate("async () => { " + body + " }")


async def snap(page, out: Path, name, setup="", frames=3):
    if setup:
        await js(page, setup)
    await js(page, f"await window.viewer.frames({frames});")
    p = out / f"{name}.png"
    # SwiftShader rasterises ~5-10 s per frame at these sizes: allow queued frames to drain
    await page.screenshot(path=str(p), timeout=240000)
    print("  shot", p)
    return p


def perf_line(tag, wall, perf):
    m = perf["marks"]
    keys = ["script", "meta", "glb", "env", "init", "compiled", "firstFrame", "ready"]
    marks = "  ".join(f"{k} {m[k]}" for k in keys if k in m)
    info = perf.get("info") or {}
    q = perf.get("quality") or {}
    return (f"[{tag}] wall {wall:.1f} s | ms since navigation: {marks} | first render {perf.get('firstRenderMs')} ms"
            f" | {info.get('calls')} calls, {info.get('triangles')} tris, {info.get('programs')} programs"
            f" | dpr {q.get('dpr')} (max {q.get('dprMax')}), shadow {q.get('shadowMap')}, contact {q.get('contactMap')}, env {perf.get('env')}")


HIDE_PANEL = "window.viewer.panel(false); await window.viewer.frames(2);"


async def run(a):
    from playwright.async_api import async_playwright
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(a.dist) if a.dist else ROOT
    srv = serve(root)
    port = srv.server_address[1]
    page_path = "index.html" if a.dist else "web/index.html"
    cdn = a.three == "cdn" or bool(a.dist)
    qs = "" if a.dist else f"?three={a.three}"
    base = f"http://127.0.0.1:{port}/{page_path}{qs}"
    if a.query:
        base += ("&" if "?" in base else "?") + a.query.lstrip("?&")
    sep = "&" if "?" in base else "?"
    only = set(a.only.split(",")) if a.only else None
    want = lambda n: only is None or n in only  # noqa: E731
    report = {}
    try:
        async with async_playwright() as pw:
            browser = await launch(pw)
            errs: list[str] = []
            desk = {"width": a.width, "height": a.height}
            if a.cam:
                ctx, page, wall = await open_page(browser, base, viewport=desk, cdn=cdn, errs=errs, scheme=a.scheme)
                p, t, f = a.cam.split(";")
                await js(page, HIDE_PANEL + f"window.viewer.setCamera({{pos: [{p}], target: [{t}], fov: {f}}}, {{instant: true}});" + (a.setup or ""))
                await snap(page, out, a.name or "adhoc")
                await ctx.close()
            else:
                ctx, page, wall = await open_page(browser, base, viewport=desk, cdn=cdn, errs=errs)
                perf = await js(page, "return window.viewer.perf();")
                print(perf_line("desktop 1280x800", wall, perf))
                report["desktop"] = {"wall_s": round(wall, 2), **perf}
                if want("desktop_panel"):
                    await snap(page, out, "00_desktop_panel")
                await js(page, HIDE_PANEL)
                if want("hero_3q"):
                    await snap(page, out, "01_hero_3q", "window.viewer.setCamera('three_quarter', {instant: true});")
                if want("cockpit_glass"):
                    await snap(page, out, "02_cockpit_glass",
                               "window.viewer.setCamera({pos: [-2.35, 2.55, 1.45], target: [-0.1, 2.0, 3.75], fov: 38}, {instant: true});")
                if want("cockpit_glass"):
                    await snap(page, out, "02b_cockpit_glass_stbd",
                               "window.viewer.setCamera({pos: [2.2, 2.3, 2.2], target: [0.0, 2.05, 3.9], fov: 40}, {instant: true});")
                if want("side"):
                    await snap(page, out, "03_side", "window.viewer.setCamera('side', {instant: true});")
                if want("top"):
                    await snap(page, out, "04_top", "window.viewer.setCamera('top', {instant: true});")
                if want("modes"):
                    await snap(page, out, "07_cutaway", "window.viewer.setCamera('three_quarter', {instant: true}); window.viewer.setCutaway(true);")
                    await snap(page, out, "08_xray", "window.viewer.setCutaway(false); window.viewer.setXray(true);")
                    await snap(page, out, "09_primer", "window.viewer.setXray(false); window.viewer.setPaint(false, {instant: true});")
                    await snap(page, out, "10_cockpit_inside", "window.viewer.setPaint(true, {instant: true}); window.viewer.setCamera('cockpit', {instant: true});")
                    await js(page, "window.viewer.setCamera('three_quarter', {instant: true});")
                if want("bench"):
                    b = await js(page, "return window.viewer.bench(4);")
                    bc = await js(page, "return window.viewer.bench(2, {contact: true});")
                    print(f"  bench (SwiftShader, CPU): frame {b['mean']:.0f} ms mean, with shadow+contact re-render {bc['mean']:.0f} ms")
                    report["bench"] = {"frame_ms": round(b["mean"]), "frame_shadows_ms": round(bc["mean"])}
                await ctx.close()

                if want("phone"):
                    ctx, page, wall = await open_page(browser, base, viewport={"width": 390, "height": 844}, mobile=True, dpr=3, cdn=cdn, errs=errs)
                    perf = await js(page, "return window.viewer.perf();")
                    print(perf_line("phone 390x844 dpr3", wall, perf))
                    report["phone"] = {"wall_s": round(wall, 2), **perf}
                    if a.net:
                        await ctx.close()
                        ctx, page, wall = await open_page(browser, base, viewport={"width": 390, "height": 844}, mobile=True, dpr=3,
                                                          cdn=cdn, errs=errs, net=a.net)
                        perf = await js(page, "return window.viewer.perf();")
                        n = NET[a.net]
                        print(perf_line(f"phone {a.net} ({n['down_mbit']} Mbit/s, {n['latency']} ms, CPU x{n['cpu']}, no gzip)", wall, perf))
                        report["phone_" + a.net] = {"wall_s": round(wall, 2), **perf}
                    await snap(page, out, "05_phone")
                    await snap(page, out, "05b_phone_sheet_closed", "window.viewer.panel(false);")
                    await ctx.close()
                if want("dark"):
                    ctx, page, wall = await open_page(browser, base, viewport=desk, scheme="dark", cdn=cdn, errs=errs)
                    await snap(page, out, "06_dark_hero", HIDE_PANEL + "window.viewer.setCamera('three_quarter', {instant: true});")
                    await snap(page, out, "06b_dark_panel", "window.viewer.panel(true); await window.viewer.frames(2);")
                    await ctx.close()
            await browser.close()
            if errs:
                print("console:", *errs[:12], sep="\n  ")
            report["console"] = errs
    finally:
        srv.shutdown()
    (out / "perf.json").write_text(json.dumps(report, indent=1, default=str))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dist", help="serve this packaged bundle (web/package.py: index.html at its root, three.js vendored in three/)")
    ap.add_argument("--three", default="local", choices=["local", "cdn"])
    ap.add_argument("--out", default=str(ROOT / "out" / "tmp" / "viewer_polish"))
    ap.add_argument("--only", help="comma list: desktop_panel,hero_3q,cockpit_glass,side,top,modes,bench,phone,dark")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--scheme", default="light")
    ap.add_argument("--cam", help="ad-hoc view 'x,y,z;x,y,z;fov' (glTF axes)")
    ap.add_argument("--setup", help="extra JS run before the ad-hoc shot")
    ap.add_argument("--name")
    ap.add_argument("--net", choices=sorted(NET), help="also load the phone page under this network / CPU throttling profile")
    ap.add_argument("--query", help="extra URL query (look tuning: exposure=, look=, envrot=, floor=, walls=, top=, lift=, key=)")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
