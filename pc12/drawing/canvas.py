"""
Minimal vector canvas in millimetres (y down) that renders the same primitive list
to SVG (viewBox in mm, 2-decimal coordinates) and to a vector PDF (reportlab).

Primitives: polyline/polygon paths (stroked, optionally dashed / filled), circles,
text (label or mono font, anchor, rotation). Consecutive paths with identical style
are merged into one SVG <path> to keep the file small.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from reportlab.pdfbase.pdfmetrics import stringWidth

LABEL_FONT_SVG = "'Barlow Condensed','Arial Narrow',sans-serif"
MONO_FONT_SVG = "'IBM Plex Mono',ui-monospace,monospace"
MM2PT = 72.0 / 25.4

# PDF fonts: embedded DejaVu Sans Condensed / Sans Mono (full glyph coverage: ² Ø ° · — ℄);
# fall back to the standard Helvetica / Courier if the TrueType files are missing.
_TTF = {"PC12-Label": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "PC12-Label-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "PC12-Mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "PC12-Mono-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"}


def _register_fonts():
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if all(os.path.exists(f) for f in _TTF.values()):
        try:
            for name, f in _TTF.items():
                pdfmetrics.registerFont(TTFont(name, f))
            return {("label", 400): "PC12-Label", ("label", 600): "PC12-Label-Bold",
                    ("mono", 400): "PC12-Mono", ("mono", 600): "PC12-Mono-Bold"}
        except Exception:
            pass
    return {("label", 400): "Helvetica", ("label", 600): "Helvetica-Bold",
            ("mono", 400): "Courier", ("mono", 600): "Courier-Bold"}


PDF_FONTS = _register_fonts()
# layout safety factor: the SVG may fall back to a wider generic sans-serif than the PDF font
_SAFETY = {"label": 1.12, "mono": 1.0}


def pdf_font(font, weight):
    return PDF_FONTS[(font, 600 if weight >= 600 else 400)]


def text_width(s, size, font="label", weight=400):
    """Conservative width (mm) of a string for layout decisions."""
    return stringWidth(s, pdf_font(font, weight), 1000.0) / 1000.0 * size * _SAFETY[font]


def fmt(v):
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


@dataclass
class Item:
    kind: str
    data: dict = field(default_factory=dict)


class Canvas:
    def __init__(self, W, H, bg="#FCFCFA", ink="#1B2429"):
        self.W, self.H, self.bg, self.ink = W, H, bg, ink
        self.items = []

    # ------------------------------------------------------------------ primitives
    def path(self, pts, w=0.13, dash=None, closed=False, fill=None, stroke=True, color=None):
        pts = [(float(x), float(y)) for x, y in pts]
        if len(pts) < 2:
            return
        self.items.append(Item("path", dict(pts=pts, w=w, dash=tuple(dash) if dash else None, closed=closed,
                                            fill=fill, stroke=stroke, color=color)))

    def line(self, p, q, w=0.13, dash=None, color=None):
        self.path([p, q], w, dash, color=color)

    def polygon(self, pts, fill=None, w=0.0, stroke=False, color=None):
        self.path(pts, w, None, closed=True, fill=fill or self.ink, stroke=stroke, color=color)

    def rect(self, x, y, w, h, lw=0.25, fill=None, stroke=True, color=None):
        self.path([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], lw, None, closed=True, fill=fill, stroke=stroke,
                  color=color)

    def circle(self, cx, cy, r, w=0.25, fill=None, stroke=True):
        self.items.append(Item("circle", dict(cx=float(cx), cy=float(cy), r=float(r), w=w, fill=fill, stroke=stroke)))

    def text(self, x, y, s, size=3.5, font="label", anchor="start", rot=0.0, weight=400, fill=None,
             spacing=0.0, vcenter=False):
        """(x, y) is the baseline point; vcenter=True puts the cap-height centre at y instead."""
        if vcenter:
            dy = 0.35 * size
            a = math.radians(rot)
            x, y = x - dy * math.sin(a), y + dy * math.cos(a)
        self.items.append(Item("text", dict(x=float(x), y=float(y), s=str(s), size=size, font=font, anchor=anchor,
                                            rot=rot, weight=weight, fill=fill, spacing=spacing)))

    # ------------------------------------------------------------------ SVG
    def to_svg(self, title="", desc="", font_import=None):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(self.W)} {fmt(self.H)}" '
               f'width="{fmt(self.W)}mm" height="{fmt(self.H)}mm">']
        if title:
            out.append(f"<title>{esc(title)}</title>")
        if desc:
            out.append(f"<desc>{esc(desc)}</desc>")
        if font_import:
            out.append(f"<defs><style><![CDATA[@import url('{font_import}');]]></style></defs>")
        out.append(f'<rect width="{fmt(self.W)}" height="{fmt(self.H)}" fill="{self.bg}"/>')
        out.append(f'<g fill="none" stroke="{self.ink}" stroke-linecap="round" stroke-linejoin="round">')
        cur_key, cur_d = None, []

        def flush():
            nonlocal cur_key, cur_d
            if cur_key is not None and cur_d:
                w, dash, fill, stroke, color = cur_key
                attrs = []
                if stroke:
                    attrs.append(f'stroke-width="{fmt(w)}"')
                    if color:
                        attrs.append(f'stroke="{color}"')
                else:
                    attrs.append('stroke="none"')
                if dash:
                    attrs.append(f'stroke-dasharray="{" ".join(fmt(d) for d in dash)}"')
                    attrs.append('stroke-linecap="butt"')
                if fill:
                    attrs.append(f'fill="{fill}"')
                out.append(f'<path {" ".join(attrs)} d="{"".join(cur_d)}"/>')
            cur_key, cur_d = None, []

        for it in self.items:
            if it.kind == "path":
                d = it.data
                key = (d["w"], d["dash"], d["fill"], d["stroke"], d["color"])
                if key != cur_key:
                    flush()
                    cur_key = key
                cur_d.append(svg_path_d(d["pts"], d["closed"]))
                continue
            flush()
            if it.kind == "circle":
                d = it.data
                attrs = [f'cx="{fmt(d["cx"])}" cy="{fmt(d["cy"])}" r="{fmt(d["r"])}"']
                if d["stroke"]:
                    attrs.append(f'stroke-width="{fmt(d["w"])}"')
                else:
                    attrs.append('stroke="none"')
                if d["fill"]:
                    attrs.append(f'fill="{d["fill"]}"')
                out.append(f'<circle {" ".join(attrs)}/>')
            elif it.kind == "text":
                d = it.data
                fam = LABEL_FONT_SVG if d["font"] == "label" else MONO_FONT_SVG
                anchor = {"start": "start", "middle": "middle", "end": "end"}[d["anchor"]]
                attrs = [f'x="{fmt(d["x"])}" y="{fmt(d["y"])}"', f'font-family="{fam}"',
                         f'font-size="{fmt(d["size"])}"', 'stroke="none"', f'fill="{d["fill"] or self.ink}"']
                if anchor != "start":
                    attrs.append(f'text-anchor="{anchor}"')
                if d["weight"] != 400:
                    attrs.append(f'font-weight="{d["weight"]}"')
                if d["spacing"]:
                    attrs.append(f'letter-spacing="{fmt(d["spacing"])}"')
                if d["rot"]:
                    attrs.append(f'transform="rotate({fmt(d["rot"])} {fmt(d["x"])} {fmt(d["y"])})"')
                out.append(f'<text {" ".join(attrs)}>{esc(d["s"])}</text>')
        flush()
        out.append("</g></svg>")
        return "\n".join(out)

    # ------------------------------------------------------------------ PDF
    def to_pdf(self, path, title="", author="", subject=""):
        from reportlab.pdfgen import canvas as rl
        from reportlab.lib.colors import HexColor
        W, H = self.W * MM2PT, self.H * MM2PT
        c = rl.Canvas(path, pagesize=(W, H), pageCompression=1)
        c.setTitle(title)
        c.setAuthor(author)
        c.setSubject(subject)
        ink = HexColor(self.ink)
        c.setFillColor(HexColor(self.bg))
        c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setLineCap(1)
        c.setLineJoin(1)

        def P(x, y):
            return x * MM2PT, (self.H - y) * MM2PT

        for it in self.items:
            d = it.data
            if it.kind == "path":
                col = HexColor(d["color"]) if d["color"] else ink
                c.setStrokeColor(col)
                c.setLineWidth(max(d["w"], 0.0) * MM2PT)
                if d["dash"]:
                    c.setDash([v * MM2PT for v in d["dash"]], 0)
                    c.setLineCap(0)
                else:
                    c.setDash([], 0)
                    c.setLineCap(1)
                p = c.beginPath()
                x0, y0 = P(*d["pts"][0])
                p.moveTo(x0, y0)
                for q in d["pts"][1:]:
                    p.lineTo(*P(*q))
                if d["closed"]:
                    p.close()
                if d["fill"]:
                    c.setFillColor(HexColor(d["fill"]))
                c.drawPath(p, stroke=1 if d["stroke"] else 0, fill=1 if d["fill"] else 0)
            elif it.kind == "circle":
                c.setDash([], 0)
                c.setStrokeColor(ink)
                c.setLineWidth(d["w"] * MM2PT)
                if d["fill"]:
                    c.setFillColor(HexColor(d["fill"]))
                cx, cy = P(d["cx"], d["cy"])
                c.circle(cx, cy, d["r"] * MM2PT, stroke=1 if d["stroke"] else 0, fill=1 if d["fill"] else 0)
            elif it.kind == "text":
                font = pdf_font(d["font"], d["weight"])
                size = d["size"] * MM2PT
                c.setFillColor(HexColor(d["fill"]) if d["fill"] else ink)
                c.saveState()
                x, y = P(d["x"], d["y"])
                c.translate(x, y)
                if d["rot"]:
                    c.rotate(-d["rot"])
                t = c.beginText()
                t.setFont(font, size)
                if d["spacing"]:
                    t.setCharSpace(d["spacing"] * MM2PT)
                wdt = stringWidth(d["s"], font, size) + (d["spacing"] * MM2PT * max(len(d["s"]) - 1, 0))
                dx = {"start": 0.0, "middle": -wdt / 2, "end": -wdt}[d["anchor"]]
                t.setTextOrigin(dx, 0)
                t.textOut(d["s"])
                c.drawText(t)
                c.restoreState()
        c.showPage()
        c.save()


def svg_path_d(pts, closed=False):
    """Absolute first point, then relative 'l' segments (2 decimals) -> compact path data."""
    x0, y0 = round(pts[0][0], 2), round(pts[0][1], 2)
    parts = [f"M{fmt(x0)} {fmt(y0)}"]
    px, py = x0, y0
    rel = []
    for x, y in pts[1:]:
        xr, yr = round(x, 2), round(y, 2)
        dx, dy = round(xr - px, 2), round(yr - py, 2)
        if dx == 0 and dy == 0:
            continue
        rel.append(f"{fmt(dx)} {fmt(dy)}".replace(" -", "-"))
        px, py = xr, yr
    if rel:
        parts.append("l" + " ".join(rel).replace(" -", "-"))
    elif not closed:
        parts.append("l0 0")
    if closed:
        parts.append("z")
    return "".join(parts)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
