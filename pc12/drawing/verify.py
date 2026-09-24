"""
Independent check of the generated GA sheet: parses out/pc12_ga.svg (not the generator's
internal state), measures the drawn extents of the object lines in each view and compares
them with the dimension values at 1:50; also checks that everything lies inside the frame.

    cd <project root> && python3 -m drawing.verify [--png]

--png additionally renders out/pc12_ga_check.png with Playwright Chromium (2.5 px/mm).
"""
from __future__ import annotations

import re
import sys

import numpy as np

SVG = str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out/pc12_ga.svg"
SCALE = 50.0
FRAME = (20.0, 10.0, 831.0, 584.0)


def parse_paths(svg):
    """Yield (stroke_width, [points]) for every <path> (absolute M + relative l data)."""
    for m in re.finditer(r'<path ([^>]*?)d="([^"]+)"', svg):
        attrs, d = m.group(1), m.group(2)
        w = re.search(r'stroke-width="([\d.]+)"', attrs)
        w = float(w.group(1)) if w else None
        for sub in re.finditer(r"M([-\d.]+) ([-\d.]+)(?:l([^Mz]*))?", d):
            x, y = float(sub.group(1)), float(sub.group(2))
            pts = [(x, y)]
            if sub.group(3):
                nums = [float(v) for v in re.findall(r"-?\d*\.?\d+", sub.group(3))]
                for dx, dy in zip(nums[0::2], nums[1::2]):
                    x, y = x + dx, y + dy
                    pts.append((x, y))
            yield w, pts


def extents(paths, box, widths=(0.35,)):
    x0, y0, x1, y1 = box
    P = np.array([p for w, pts in paths if w in widths for p in pts])
    m = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1)
    Q = P[m]
    return Q[:, 0].min(), Q[:, 0].max(), Q[:, 1].min(), Q[:, 1].max()


def main():
    svg = open(SVG).read()
    paths = list(parse_paths(svg))
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
    from drawing import sheet as S
    from model import wing as W, empennage as E

    K = 1000.0 / SCALE
    rows = []
    # side view: object lines between the length dimension and the ground line
    sx0, sx1, sy0, sy1 = extents(paths, (S.X0 + 0.39 * K - 1, S.YG - 4.4 * K, S.X0 + 14.8 * K + 1, S.YG + 1.0))
    rows.append(("side: overall length", 14400, (sx1 - sx0) * SCALE))
    rows.append(("side: overall height (ground -> top)", 4260, (S.YG - sy0) * SCALE))
    # plan view
    px0, px1, py0, py1 = extents(paths, (S.X0 + 0.3 * K, S.YC - 8.3 * K, S.X0 + 14.9 * K, S.YC + 8.3 * K))
    rows.append(("plan: span over winglets", W.SPAN_TOTAL * 1000, (py1 - py0) * SCALE))
    rows.append(("plan: overall length", 14400, (px1 - px0) * SCALE))
    tx0, tx1, ty0, ty1 = extents(paths, (S.X0 + 12.5 * K, S.YC - 2.8 * K, S.X0 + 14.9 * K, S.YC + 2.8 * K))
    rows.append(("plan: tailplane span", 2 * E.STAB_TIP_Y * 1000, (ty1 - ty0) * SCALE))
    # front view
    fx0, fx1, fy0, fy1 = extents(paths, (S.XF - 8.3 * K, S.YG - 4.4 * K, S.XF + 8.3 * K, S.YG + 1.0))
    rows.append(("front: span over winglets", W.SPAN_TOTAL * 1000, (fx1 - fx0) * SCALE))
    rows.append(("front: height", 4260, (S.YG - fy0) * SCALE))
    ok = True
    print(f"{'measured on the sheet (x50)':42s} {'dimension':>10s} {'drawn':>10s} {'diff mm':>8s}")
    for name, want, got in rows:
        diff = got - want
        flag = "" if abs(diff) <= 25 else "   <-- CHECK"      # 25 mm real = 0.5 mm on paper
        ok &= not flag
        print(f"{name:42s} {want:10.0f} {got:10.1f} {diff:8.1f}{flag}")
    # everything (except zone marks / centring marks / zone labels) inside the frame
    X0, Y0, X1, Y1 = FRAME
    outside = 0
    for w, pts in paths:
        for x, y in pts:
            if not (X0 - 0.01 <= x <= X1 + 0.01 and Y0 - 0.01 <= y <= Y1 + 0.01):
                if w not in (0.18, 0.5):          # zone ticks (0.18) and centring marks (0.5) live in the margin
                    outside += 1
    texts = re.findall(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*>([^<]*)</text>', svg)
    t_out = [t for x, y, t in texts if not (X0 <= float(x) <= X1 and Y0 <= float(y) <= Y1)
             and not re.fullmatch(r"\d{1,2}|[A-M]", t)]
    print(f"path points outside the frame (excluding margin marks): {outside}")
    print(f"text outside the frame (excluding zone labels): {t_out if t_out else 0}")
    print(f"SVG size: {len(svg.encode()) / 1e6:.2f} MB, {len(paths)} sub-paths")
    if "--png" in sys.argv:
        render_png(SVG, str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out/pc12_ga_check.png", 2.5)
    return ok and outside == 0 and not t_out


def render_png(svg_path, out, pxmm):
    from playwright.sync_api import sync_playwright
    svg = open(svg_path).read()
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    W, H = float(m.group(1)), float(m.group(2))
    pw, ph = int(W * pxmm), int(H * pxmm)
    svg = re.sub(r'width="[\d.]+mm" height="[\d.]+mm"', f'width="{pw}" height="{ph}"', svg, count=1)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width": pw, "height": ph})
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
        pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>", wait_until="load")
        pg.screenshot(path=out, full_page=True)
        b.close()
    print("rendered", out)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
