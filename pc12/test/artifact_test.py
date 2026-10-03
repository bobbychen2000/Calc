#!/usr/bin/env python3
"""Headless check of the claude.ai Artifact bundle (web/package_artifact.py -> dist_artifact/).

Serves the folder over HTTP and opens its page file the way the Artifact host does: wrapped in a skeleton (doctype,
charset + viewport-fit=cover viewport, the host's small reset) with a strict Content-Security-Policy, in headless
Chromium (SwiftShader).  The wrappers are written into the folder as _host_*.html (never published: ARTIFACT.json
leaves them out).  Scenarios:

  nowasm   CSP without 'wasm-unsafe-eval': WebAssembly refused -> the gzip GLB (data/pc12_glb.gz.bin: the light tier),
           unpacked with DecompressionStream; the meshopt GLBs are never requested; the only console errors are the
           CSP's wasm refusals
  wasm     CSP with 'wasm-unsafe-eval' -> the meshopt GLB: data/pc12.glb on the desktop, the light tier
           data/pc12_low.glb on the phone (never the other one); the gzip copy is never requested

The GLBs and the studio HDRIs are published as base64 text parts (ARTIFACT.json 'base64'): each scenario checks that
every part of the file it loads is requested once, and that the studio HDRI (not the RoomEnvironment fallback) lit it.
  runtime  CSP with 'wasm-unsafe-eval', but WebAssembly.instantiate rejects at run time (the boot's compile test still
           passes): the meshopt GLB fails to decode and main.js falls back to the gzip copy

each at a phone (390x844, touch) and a desktop (1400x900) viewport, with screenshots in out/tmp/artifact/.  The first
desktop run also checks the host's theme choice (<html data-theme="dark|light"> over the OS setting: the panels and
the 3-D stage follow it; shot <mode>_desktop_dark.png).  Every run also enters the interior tour under the CSP (Go
inside -> the stop menu -> a cabin stop -> Exit; shot <mode>_<viewport>_tour.png).  The wrappers are removed afterwards.

usage: python3 test/artifact_test.py [--dir dist_artifact] [--port 8851] [--only nowasm,wasm] [--no-shots]
Exit code 0 = all checks pass.
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import json
import os
import socket
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # pc12/
OUT = ROOT / "out" / "tmp" / "artifact"
CHROMIUM = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "/opt/pw-browsers/chromium")
LAUNCH_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
CSP = ("script-src 'self' 'unsafe-inline'{wasm} https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
       "connect-src 'self'; worker-src 'self' blob:")
# the host's skeleton: charset, viewport, a small reset (light color-scheme on :root, :root padded top and bottom by
# the safe-area insets, no body margin, a 14px system font on an off-white ground, img max-width, [hidden] hidden);
# the page file goes inside <body>
SKELETON = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<style>:root{{color-scheme:light;padding:env(safe-area-inset-top,0px) 0 env(safe-area-inset-bottom,0px)}}body{{margin:0;font:14px system-ui,sans-serif;background:#faf9f7}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
{page}</body>
</html>
"""
VIEWPORTS = {"phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True),
             "desktop": dict(viewport={"width": 1400, "height": 900}, device_scale_factor=1)}
# 'runtime': WebAssembly compiles (the boot's test passes) but instantiation fails, as if refused later
BREAK_INSTANTIATE = """(() => { const E = WebAssembly.CompileError;
  WebAssembly.instantiate = () => Promise.reject(new E('WebAssembly.instantiate(): refused (artifact_test runtime scenario)')); })();"""
SCENARIOS = {"nowasm": "", "wasm": " 'wasm-unsafe-eval'", "runtime": " 'wasm-unsafe-eval'"}

results: list[tuple[str, bool, str]] = []
B64: dict[str, int] = {}                             # ARTIFACT.json 'base64': {file name: parts}


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    return ok


class Quiet(SimpleHTTPRequestHandler):
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


def free_port(want: int) -> int:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", want))
            return want
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


async def run_one(browser, base, mode, vp, shots, theme=False):
    ctx = await browser.new_context(reduced_motion="reduce", **VIEWPORTS[vp])
    if mode == "runtime":
        await ctx.add_init_script(BREAK_INSTANTIATE)
    page = await ctx.new_page()
    errors, warns, reqs, bad = [], [], [], []
    page.on("console", lambda m: (errors if m.type == "error" else warns if m.type == "warning" else []).append(
        m.text + (f" [{m.location.get('url')}]" if m.type == "error" and m.location.get("url") else "")))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("request", lambda r: reqs.append(r.url))
    page.on("requestfailed", lambda r: bad.append(f"{r.url} ({r.failure})") if "ERR_ABORTED" not in str(r.failure) else None)
    page.on("response", lambda r: bad.append(f"{r.url} HTTP {r.status}") if r.status >= 400 else None)
    t0 = time.time()
    await page.goto(f"{base}/_host_{'nowasm' if mode == 'nowasm' else 'wasm'}.html")
    # polled from here: page.wait_for_function evaluates its predicate with eval(), which the CSP refuses
    while not await page.evaluate("() => window.__ready === true"):
        if time.time() - t0 > 300:
            raise TimeoutError(f"{mode} {vp}: not ready after 300 s")
        await asyncio.sleep(0.5)
    dt = time.time() - t0
    st = await page.evaluate("""() => ({ err: window.__error || '', wasm: window.PC12_BOOT.wasm, gzip: !!window.PC12_BOOT.gzip,
      title: document.title, parts: window.viewer ? window.viewer.parts().length : 0,
      tris: window.viewer ? window.viewer.perf().info.triangles : 0,
      glbSpec: (document.getElementById('statsList') || {}).textContent || '',
      loading: getComputedStyle(document.getElementById('loading')).display,
      scrollW: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth), w: innerWidth })""")
    name = f"{mode} {vp}"
    # the tier: phones load the light tier (PC12_CONFIG.glbLow), desktops the full model -- never the other one
    tier, other = ("pc12_low.glb", "pc12.glb") if vp == "phone" else ("pc12.glb", "pc12_low.glb")
    glb = [u for u in reqs if f"/data/{tier}" in u]
    wrong = [u for u in reqs if f"/data/{other}" in u]
    gz = [u for u in reqs if "/data/pc12_glb.gz.bin" in u]
    want_gz = mode in ("nowasm", "runtime")
    n_glb, n_gz = B64.get(tier, 1), B64.get("pc12_glb.gz.bin", 1)
    hdr_name = "studio_small_09_512.hdr" if vp == "phone" else "studio_small_09_1k.hdr"
    hdr = sorted({u.rsplit("/", 1)[1] for u in reqs if "/assets/studio_small_09" in u})
    want_hdr = [f"{hdr_name}.b64.txt"] if B64.get(hdr_name) == 1 else [f"{hdr_name}.b64.{i}.txt" for i in range(B64.get(hdr_name, 0))] or [hdr_name]
    check(f"{name}: loads", not st["err"] and st["parts"] > 50 and st["loading"] == "none",
          st["err"].splitlines()[0] if st["err"] else f"{dt:.0f} s, {st['parts']} parts, {st['tris']} triangles drawn")
    check(f"{name}: aircraft drawn", st["tris"] > 100000, f"{st['tris']} triangles in the last frame")
    check(f"{name}: path", (st["wasm"] is False if mode == "nowasm" else st["wasm"] is True) and st["gzip"] == want_gz
          and len(gz) == len(set(gz)) == (n_gz if want_gz else 0) and len(glb) == len(set(glb)) == (0 if mode == "nowasm" else n_glb)
          and not wrong,
          f"wasm {st['wasm']}, gzip {st['gzip']}, requests: {tier} x{len(glb)} (of {n_glb} parts), gz x{len(gz)} (of {n_gz})"
          + (f", {other} x{len(wrong)}" if wrong else ""))
    check(f"{name}: studio HDRI", hdr == sorted(want_hdr) and not any("HDRI environment unavailable" in w for w in warns),
          f"requested {', '.join(hdr) or 'nothing'}")
    if want_gz:
        check(f"{name}: Specs panel names the gzip GLB", "gzip" in st["glbSpec"], st["glbSpec"][:120])
    # expected: the CSP's WebAssembly refusals (nowasm); runtime: the decoder's own rejected start-up may be logged
    # (/favicon.ico: this skeleton has no icon and Chromium ignores the page's data-URI icon link outside <head>)
    unexpected = [e for e in errors if "WebAssembly" not in e and not e.endswith("/favicon.ico]")]
    wasm_err = [e for e in errors if "WebAssembly" in e]
    check(f"{name}: no console errors but the expected WebAssembly refusal", not unexpected and (mode != "wasm" or not wasm_err),
          "; ".join((unexpected or wasm_err)[:3])[:300] or (f"expected: {wasm_err[0][:110]}" if wasm_err else "none"))
    if mode == "runtime":
        check(f"{name}: fallback announced", any("gzip copy" in w for w in warns), "; ".join(w[:100] for w in warns[:2]))
    check(f"{name}: no failed requests", not bad, "; ".join(bad[:3]))
    check(f"{name}: title, no horizontal scroll", st["title"] == "PC-12 PRO Parametric Model" and st["scrollW"] <= st["w"],
          f"{st['title']!r}, scrollWidth {st['scrollW']} / {st['w']}")
    if shots:
        OUT.mkdir(parents=True, exist_ok=True)
        await page.evaluate("window.viewer.frames(2)")
        p = OUT / f"{mode}_{vp}.png"
        await page.screenshot(path=str(p), timeout=240000)
        print(f"  shot {p.relative_to(ROOT)}")
    await check_tour(page, name, errors, shots)
    if theme:
        await check_theme(page, name, shots)
    await ctx.close()


TOUR_JS = """async () => {
  const V = window.viewer, q = (id) => document.getElementById(id);
  q('tourEnter').click(); await V.frames(1);
  const menu = !q('tourMenu').hidden && q('tourMenu').querySelectorAll('[data-stop]').length;
  q('tourMenu').querySelector('[data-stop="cabin_aft"]').click(); V.tour.finish(); await V.frames(2);
  const st = V.state;
  return { menu, active: st.tour.active, stop: st.tour.stop, inside: st.camInside, outside: st.tour.outside,
    exitVisible: !q('tourExit').hidden, tris: V.perf().info.triangles }; }"""


async def check_tour(page, name, errors, shots):
    """The interior tour under the host's CSP: the menu, a stop (camera inside, the cabin drawn), Exit."""
    n0 = len(errors)
    r = await page.evaluate(TOUR_JS)
    if shots:
        p = OUT / f"{name.replace(' ', '_')}_tour.png"
        await page.screenshot(path=str(p), timeout=240000)
        print(f"  shot {p.relative_to(ROOT)}")
    out = await page.evaluate("""async () => { document.getElementById('tourExit').click(); window.viewer.tour.finish();
      await window.viewer.frames(1); return [window.viewer.state.tour.active, window.viewer.state.cameraPreset]; }""")
    new = [e for e in errors[n0:] if not e.endswith("/favicon.ico]")]
    check(f"{name}: interior tour (Go inside -> menu -> cabin stop -> Exit)",
          r["menu"] == 7 and r["active"] and r["stop"] == "cabin_aft" and r["inside"] and r["outside"] < 1e-6 and r["exitVisible"]
          and r["tris"] > 100000 and out == [False, "three_quarter"] and not new,
          f"{r['menu']} stops, at {r['stop']} (inside {r['inside']}), {r['tris']} triangles drawn, exit {out}" + (f"; {new[:2]}" if new else ""))


THEME_JS = """async (t) => { const r = document.documentElement;
  if (t) r.setAttribute('data-theme', t); else r.removeAttribute('data-theme');
  await window.viewer.frames(2);
  return { bg: getComputedStyle(document.body).backgroundColor, dark: window.viewer.state.dark }; }"""
LIGHT_BG, DARK_BG = "rgb(233, 236, 239)", "rgb(20, 24, 28)"


async def check_theme(page, name, shots):
    """The host stamps data-theme on <html> for an explicit light / dark choice; none = the OS setting."""
    got = {}
    for os_scheme, t in (("light", "dark"), ("light", None), ("dark", "light"), ("dark", None)):
        await page.emulate_media(color_scheme=os_scheme)
        got[(os_scheme, t)] = r = await page.evaluate(THEME_JS, t)
        want_dark = t == "dark" or (t is None and os_scheme == "dark")
        check(f"{name}: theme OS {os_scheme}, data-theme {t or '-'}", r["dark"] == want_dark and r["bg"] == (DARK_BG if want_dark else LIGHT_BG),
              f"stage dark {r['dark']}, body {r['bg']}")
        if shots and (os_scheme, t) == ("light", "dark"):
            p = OUT / f"{name.replace(' ', '_')}_dark.png"
            await page.screenshot(path=str(p), timeout=240000)
            print(f"  shot {p.relative_to(ROOT)}")
    await page.emulate_media(color_scheme="light")
    await page.evaluate(THEME_JS, None)


async def run(args):
    from playwright.async_api import async_playwright
    d = (ROOT / args.dir).resolve()
    page = (d / "index.html").read_text(encoding="utf-8")
    B64.update(json.loads((d / "ARTIFACT.json").read_text()).get("base64") or {})
    hosts = []
    for name, wasm in (("nowasm", ""), ("wasm", " 'wasm-unsafe-eval'")):
        hosts.append(d / f"_host_{name}.html")
        hosts[-1].write_text(SKELETON.format(csp=CSP.format(wasm=wasm), page=page), encoding="utf-8")
    port = free_port(args.port)
    srv = Server(("127.0.0.1", port), functools.partial(Quiet, directory=str(d)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    print(f"serving {d} at {base}")
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path=CHROMIUM, args=LAUNCH_ARGS)
            theme = True
            for mode in args.only.split(","):
                for vp in VIEWPORTS:
                    await run_one(browser, base, mode, vp, not args.no_shots, theme and vp == "desktop")
                    theme = theme and vp != "desktop"
            await browser.close()
    finally:
        srv.shutdown()
        for h in hosts:
            h.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="dist_artifact", help="the bundle folder (relative to pc12/)")
    ap.add_argument("--port", type=int, default=8851, help="HTTP port (a free one if taken)")
    ap.add_argument("--only", default="nowasm,wasm,runtime", help="scenarios: nowasm, wasm, runtime")
    ap.add_argument("--no-shots", action="store_true")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("test harness", False, repr(e))
    w = max(len(n) for n, _, _ in results) if results else 10
    print("\n" + "-" * (w + 50))
    for n, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {n:{w}s}  {detail}")
    fails = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{len(results) - fails}/{len(results)} passed")
    sys.exit(1 if fails or not results else 0)


if __name__ == "__main__":
    main()
