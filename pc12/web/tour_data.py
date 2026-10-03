#!/usr/bin/env python3
"""Interior tour data for the viewer: web/viewer/tour_data.js, built from the approved interior tables.

    python3 web/tour_data.py            # (re)write web/viewer/tour_data.js
    python3 web/tour_data.py --check    # exit 1 if the committed file differs from the tables (test/viewer_test.py)

Every number comes from the source-tagged tables the L6 / L6B sheets draw and model/build.py builds from
(model/interior.py, model/fuselage_parts.py, model/build.py cockpit_camera); nothing is measured off the mesh:

  stops     the named viewpoints of the tour (MODEL axes: x = STA, y = BL + starboard, z = WL):
              pilot / copilot  the L6 design eye (interior.design_eye: the 50th-pct seated eye at the neutral seat),
                               looking where the viewer's cockpit camera looks (build.cockpit_camera)
              fd_cabin         standing in the divider opening (DIVIDER x_aft, open_bl), looking at the MFD
                               (interior.mfd_centre) between the crew seat backs
              cabin_fwd / _aft standing in the aisle at the baggage partition (BAGGAGE partition_x) / the divider,
                               crouched: the eye STAND_EYE above the floor (the cabin is 1.47 high, CABIN height)
              club             PAX 3's seated eye (interior.cabin_pose, 50th pct: seat_map 'PAX 3', the club four's
                               port forward-facing seat), looking forward across the club
              airstair         standing in the airstair door's clear opening (fuselage_parts.AIRSTAIR, DOOR_SILL_WL),
                               the door open, looking aft into the cabin
            `via`: points from the stop out to the aisle centre band (|BL| <= AISLE_BAND); a flight runs stop ->
            via -> along the aisle -> the other stop's via (reversed) -> stop.  `approach`: the exterior pose the
            camera flies to before it fades into the cabin from outside.
  regions   the walkable volume of the eye point: boxes (x, y, z ranges) whose union the first-person camera is
            projected onto after every move, the clearances (MARGIN) built in:
              flight_deck  between the crew seats, behind the pedestal, above the seats' armrests (CREW_SEAT bl,
                           width) up to the divider opening
              aisle        the cabin aisle between the executive seats (EXEC_SEAT bl, width), divider to the baggage
                           partition
              vestibule    the entry area abeam the airstair door (CLEAR_ZONES entry_bl: no furniture outboard of the
                           aisle there), divider to the LH cabinet (CABINETS lh x)
              doorway      the airstair door's clear opening (only while the door is open)
              seat_*       a pocket round each seated eye (crew: design_eye; cabin: cabin_pose at the 50th pct)
            regions marked `ceil` are also held MARGIN below the headliner / lining (`ceiling`).
  ceiling   the highest eye WL at (x, |y|) on a grid: the cabin headliner (interior.headliner_z: flat channel, soffit
            bands, curved side lining), the flight-deck lining crown (interior.lining_crown) with the overhead panel
            (OVERHEAD x, w, depth) hanging below it -- the lowest surface within MARGIN of the point, less MARGIN.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
sys.path.insert(0, str(ROOT))

from model import interior as I  # noqa: E402
from model import fuselage_parts as FP  # noqa: E402

OUT = WEB / "viewer" / "tour_data.js"

# interior.lining_section(x) is re-evaluated by every lining_crown / headliner_z call: cached per station here (the
# ceiling grid asks thousands of |BL| values at a few hundred stations)
_lining_section = I.lining_section


@functools.lru_cache(maxsize=None)
def _section_cached(x, n):
    return _lining_section(x, n)


I.lining_section = lambda x, n=1441: _section_cached(float(x), int(n))

MARGIN = 0.10          # eye-point clearance to the lining, headliner, seats and walls [E: a head ~0.10 round the eye]
AISLE_BAND = 0.06      # |BL| of the aisle centre band the flights run along [E]
STAND_EYE = 1.35       # standing eye above the cabin floor: crouched, under the 1.47 cabin height [E; CABIN height S]
STAND_EYE_FD = 1.25    # standing eye in the divider opening, over the crew seat backs at the flight deck [E]
CROUCH_MIN = 0.95      # lowest standing / crouching eye above the floor [E: a seated eye is ~0.75-0.80 above a cushion]
DOOR_EYE = 1.22        # eye above the airstair sill, standing (stooped) in the 1.35 m clear opening [E]
SEAT_POCKET = (0.08, 0.06, 0.12)   # seated-eye pocket: +/- along x, below / above the eye [E]
FOV_CREW, FOV_CABIN = 74.0, 70.0   # vertical field of view (deg), widened on narrow viewports by the viewer


def r3(v):
    return [round(float(a), 4) for a in v]


def floor_wl():
    return float(I.FLOOR["wl"])


def cockpit_target(side):
    """build.cockpit_camera's look point for either seat (mirrored for the right seat)."""
    from model import build as B
    t = np.array(B.cockpit_camera(-1)["target_model"], float)
    t[1] *= -side
    return t


def seats():
    m = {r["id"]: r for r in I.seat_map()}
    return m


def seated_eye(rec):
    """(x, y, z) of the 50th-pct seated eye in a cabin seat record (interior.cabin_pose)."""
    p = I.cabin_pose(rec, scale=float(I.P50_SCALE))
    return np.array([float(p["eye"][0]), float(rec["srp"][1]), float(p["eye"][1])])


# --------------------------------------------------------------------------------------------------- ceiling
def surface_wl(x, a):
    """WL of the surface over the eye at station x, |BL| a: the flight-deck lining crown (overhead panel below it)
    forward of the divider, the cabin headliner aft of it, the lower of both inside the divider wall."""
    xa = float(I.DIVIDER["x_aft"])
    xf = xa - float(I.DIVIDER["t"])
    ox0, ox1 = (float(v) for v in I.OVERHEAD["x"])
    fd = I.lining_crown(x, a)
    if ox0 <= x <= ox1 and a <= 0.5 * float(I.OVERHEAD["w"]):
        fd -= float(I.OVERHEAD["depth"])
    if x <= xf:
        return fd
    cab = I.headliner_z(x, a)
    return cab if x >= xa else min(fd, cab)


def ceiling_grid(x0=3.80, x1=9.35, dx=0.025, a1=0.80, da=0.025, fine=0.025):
    """ztop[i][j] at x0 + i dx, |BL| j da: the lowest surface within MARGIN (in x and |BL|) of the point, less
    MARGIN."""
    xs = np.arange(x0, x1 + 1e-9, dx)
    as_ = np.arange(0.0, a1 + 1e-9, da)
    xf = np.arange(x0 - MARGIN, x1 + MARGIN + 1e-9, fine)
    af = np.arange(0.0, a1 + MARGIN + 1e-9, fine)
    S = np.array([[surface_wl(float(x), float(a)) for a in af] for x in xf])
    Z = np.empty((len(xs), len(as_)))
    for i, x in enumerate(xs):
        mi = np.abs(xf - x) <= MARGIN + 1e-9
        for j, a in enumerate(as_):
            mj = np.abs(af - a) <= MARGIN + 1e-9
            Z[i, j] = S[np.ix_(mi, mj)].min() - MARGIN
    return dict(x0=x0, dx=dx, nx=len(xs), da=da, na=len(as_), z=[[round(float(v), 4) for v in row] for row in Z])


def ceil_at(C, x, a):
    """Bilinear lookup of the ceiling grid (the viewer's tour.js does the same)."""
    fx = min(max((x - C["x0"]) / C["dx"], 0.0), C["nx"] - 1.000001)
    fa = min(max(a / C["da"], 0.0), C["na"] - 1.000001)
    i, j = int(fx), int(fa)
    u, v = fx - i, fa - j
    z = C["z"]
    return ((z[i][j] * (1 - v) + z[i][j + 1] * v) * (1 - u) + (z[i + 1][j] * (1 - v) + z[i + 1][j + 1] * v) * u)


# --------------------------------------------------------------------------------------------------- regions
def regions():
    fl = floor_wl()
    S = seats()
    cs, es = I.CREW_SEAT, I.EXEC_SEAT
    xa = float(I.DIVIDER["x_aft"])
    ob0, ob1 = (float(v) for v in I.DIVIDER["open_bl"])
    # crew seats: headrests inboard edge at bl - head w / 2 (the eye passes between them), armrests far below the eye
    crew_in = float(cs["bl"]) - 0.5 * float(cs["head_hwt"][1])
    fd_hw = min(crew_in, -ob0, ob1) - MARGIN - 0.035                      # = 0.10
    # cabin: the executive seats' aisle-side edge (CL - width / 2)
    aisle_hw = float(es["bl"]) - 0.5 * float(es["width"]) - 0.05         # = 0.10 (seat edge 0.15, the arm's 50 mm pad)
    ped_x1 = float(I.PEDESTAL["x"][1])
    ox0 = float(I.OVERHEAD["x"][0])
    A = FP.AIRSTAIR
    sill = float(FP.DOOR_SILL_WL)
    lh_x0 = float(I.CABINETS["lh"]["x"][0])
    out = [
        dict(id="flight_deck", label="flight deck", x=[ox0 - 0.05, xa + 0.05], y=[-fd_hw, fd_hw],
             z=[fl + CROUCH_MIN, fl + 2.0], ceil=True,
             src="CREW_SEAT bl / head_hwt, DIVIDER open_bl; forward to the overhead panel (OVERHEAD x), over the "
                 f"pedestal (aft end {ped_x1:.3f}, top {float(I.PEDESTAL['top_h']):.2f} above the floor)"),
        dict(id="aisle", label="aisle", x=[xa - 0.04, float(I.BAGGAGE["partition_x"]) - 0.12], y=[-aisle_hw, aisle_hw],
             z=[fl + CROUCH_MIN, fl + 2.0], ceil=True,
             src="EXEC_SEAT bl / width; DIVIDER x_aft .. BAGGAGE partition_x (curtain)"),
        dict(id="vestibule", label="entry vestibule", x=[xa + MARGIN, lh_x0 - 0.08], y=[-0.45, 0.0],
             z=[fl + CROUCH_MIN, fl + 2.0], ceil=True,
             src="CLEAR_ZONES entry_bl (no furniture abeam the airstair door), DIVIDER x_aft .. CABINETS lh x0"),
        dict(id="doorway", label="airstair doorway", when="door_airstair",
             x=[A["cx"] - A["hx"] + MARGIN, A["cx"] + A["hx"] - MARGIN], y=[-0.70, -0.30],
             z=[sill + CROUCH_MIN, sill + 2 * A["hz"] - 0.08], ceil=False,
             src="fuselage_parts.AIRSTAIR clear opening (cx, hx, hz), DOOR_SILL_WL; open door only"),
    ]
    dx, dzl, dzu = SEAT_POCKET
    for sid, key in (("PILOT", "pilot"), ("CO-PILOT", "copilot")):
        r = S[sid]
        e = I.design_eye(r["side"])
        y0, y1 = sorted((r["side"] * (float(cs["bl"]) + 0.05), r["side"] * (fd_hw - 0.04)))
        out.append(dict(id="seat_" + key, label=sid.lower(), x=[e[0] - dx, e[0] + dx + 0.02], y=[y0, y1],
                        z=[e[2] - dzl - 0.02, e[2] + dzu], ceil=True, src="interior.design_eye, CREW_SEAT bl"))
    for k in range(1, 7):
        r = S[f"PAX {k}"]
        e = seated_eye(r)
        y0, y1 = sorted((r["side"] * (float(es["bl"]) + 0.04), r["side"] * (aisle_hw - 0.04)))
        out.append(dict(id=f"seat_pax{k}", label=f"PAX {k}", x=[e[0] - dx, e[0] + dx], y=[y0, y1],
                        z=[e[2] - dzl, e[2] + dzu], ceil=True, src=f"seat_map 'PAX {k}', cabin_pose (50th pct)"))
    for R in out:
        R["x"], R["y"], R["z"] = r3(R["x"]), r3(R["y"]), r3(R["z"])
    return out


def project(p, regs, C, doors=("door_airstair",)):
    """Nearest point of the walkable union (tour.js project(), the same rule)."""
    best, bd, who = None, math.inf, None
    for R in regs:
        if R.get("when") and R["when"] not in doors:
            continue
        x = min(max(p[0], R["x"][0]), R["x"][1])
        y = min(max(p[1], R["y"][0]), R["y"][1])
        zhi = R["z"][1]
        if R["ceil"]:
            zhi = min(zhi, ceil_at(C, x, abs(y)))
        if zhi < R["z"][0]:
            continue
        z = min(max(p[2], R["z"][0]), zhi)
        d = (x - p[0]) ** 2 + (y - p[1]) ** 2 + (z - p[2]) ** 2
        if d < bd:
            best, bd, who = (x, y, z), d, R["id"]
    return best, math.sqrt(bd), who


# --------------------------------------------------------------------------------------------------- stops
def stops():
    fl = floor_wl()
    S = seats()
    xa = float(I.DIVIDER["x_aft"])
    xb = float(I.BAGGAGE["partition_x"])
    A = FP.AIRSTAIR
    sill = float(FP.DOOR_SILL_WL)
    out = []
    for key, sid, label in (("pilot", "PILOT", "Pilot seat"), ("copilot", "CO-PILOT", "Co-pilot seat")):
        side = S[sid]["side"]
        e = I.design_eye(side)
        out.append(dict(
            id=key, label=label, fov=FOV_CREW,
            note=("Left" if side < 0 else "Right") + " seat at the design eye (sheet L6)",
            eye=e, target=cockpit_target(side),
            via=[np.array([e[0] + 0.16, side * (AISLE_BAND - 0.01), e[2] + 0.08])],
            approach="nose",
            src="interior.design_eye (50th-pct seated eye, neutral seat); build.cockpit_camera look point"))
    e = np.array([xa + 0.05, 0.0, fl + STAND_EYE_FD])
    out.append(dict(id="fd_cabin", label="Flight deck from the cabin", fov=FOV_CABIN,
                    note="In the divider opening, between the crew seats", eye=e, target=I.mfd_centre(), via=[],
                    approach="door", src="DIVIDER x_aft / open_bl, interior.mfd_centre"))
    e = np.array([xb - 0.20, 0.0, fl + STAND_EYE])
    out.append(dict(id="cabin_fwd", label="Cabin, looking forward", fov=FOV_CABIN,
                    note="Aft end of the aisle, toward the flight deck", eye=e,
                    target=np.array([xa - 0.60, 0.0, fl + CROUCH_MIN]), via=[], approach="door",
                    src="BAGGAGE partition_x, DIVIDER x_aft, CABIN height"))
    e = np.array([xa + 0.22, 0.0, fl + STAND_EYE])
    out.append(dict(id="cabin_aft", label="Cabin, looking aft", fov=FOV_CABIN,
                    note="From the divider, down the aisle", eye=e,
                    target=np.array([xb, 0.0, fl + 0.85]), via=[], approach="door",
                    src="DIVIDER x_aft, BAGGAGE partition_x / bar_h"))
    p3, p2 = S["PAX 3"], S["PAX 2"]
    e = seated_eye(p3)
    out.append(dict(id="club", label="Club seats", fov=FOV_CABIN,
                    note="PAX 3's seat in the club four, facing forward", eye=e,
                    target=np.array([p2["x0"] + 0.25, 0.25 * p2["bl"], fl + 0.90]),
                    via=[np.array([e[0], -(AISLE_BAND - 0.01), e[2] + 0.10])], approach="door",
                    src="seat_map 'PAX 3' / 'PAX 2', cabin_pose (50th pct)"))
    e = np.array([A["cx"] - 0.04, -0.55, sill + DOOR_EYE])
    out.append(dict(id="airstair", label="Airstair entry", fov=FOV_CABIN, doors={"door_airstair": 1},
                    note="Standing in the open airstair door", eye=e,
                    target=np.array([float(p3["x0"]), 0.30, fl + 0.95]),
                    via=[np.array([A["cx"], -0.33, sill + DOOR_EYE]),
                         np.array([A["cx"] + 0.10, -(AISLE_BAND - 0.01), fl + STAND_EYE - 0.05])],
                    approach="door", src="fuselage_parts.AIRSTAIR (cx, hz), DOOR_SILL_WL"))
    for s in out:
        s["eye"], s["target"] = r3(s["eye"]), r3(s["target"])
        s["via"] = [r3(v) for v in s["via"]]
    return out


def approaches():
    """Exterior poses (eye, target) the camera flies to before it fades into the cabin."""
    fl = floor_wl()
    A = FP.AIRSTAIR
    e = I.design_eye(-1)
    return dict(
        nose=dict(eye=r3([e[0] - 2.3, 0.0, e[2] + 0.30]), target=r3([e[0], 0.0, e[2] - 0.05]),
                  note="ahead of the windshield (both crew seats)"),
        door=dict(eye=r3([A["cx"] + 0.20, -2.9, fl + 1.15]), target=r3([A["cx"], -0.80, fl + 0.85]),
                  note="abeam the airstair door, port side"),
    )


def build_data():
    C = ceiling_grid()
    regs = regions()
    sts = stops()
    fl = floor_wl()
    # self-checks: every stop and via point inside the walkable union, headroom in every ceiling region
    errs = []
    for s in sts:
        for k, p in [("eye", s["eye"])] + [(f"via{i}", v) for i, v in enumerate(s["via"])]:
            q, d, who = project(p, regs, C)
            if d > 1e-6:
                errs.append(f"{s['id']} {k} {p} is {d * 1000:.1f} mm outside the walkable volume (nearest {who})")
    for R in regs:
        if not R["ceil"]:
            continue
        lo = min(ceil_at(C, x, abs(y)) for x in np.linspace(*R["x"], 25) for y in np.linspace(*R["y"], 9))
        if lo < R["z"][0] + 0.02:
            errs.append(f"region {R['id']}: ceiling {lo:.3f} leaves no headroom over z0 {R['z'][0]:.3f}")
    if errs:
        raise SystemExit("tour_data: " + "; ".join(errs))
    return dict(
        source="web/tour_data.py from model/interior.py + fuselage_parts.py (sheets L6 / L6B tables)",
        axes="model: x = STA (m aft of the datum), y = BL (+ starboard), z = WL",
        floor=round(fl, 4), cabin_height=float(I.CABIN["height"]), margin=MARGIN, aisle_band=AISLE_BAND,
        stand_eye=round(fl + STAND_EYE, 4), crouch_min=round(fl + CROUCH_MIN, 4),
        stops=[{k: (v if not isinstance(v, np.ndarray) else r3(v)) for k, v in s.items()} for s in sts],
        approach=approaches(), regions=regs, ceiling=C,
    )


def render(data) -> str:
    """The JS module: one line per stop / region / ceiling row."""
    d = dict(data)
    C = d.pop("ceiling")
    one = lambda o: json.dumps(o, separators=(", ", ": "))   # noqa: E731
    lines = []
    for k, v in d.items():
        if k in ("stops", "regions"):
            lines.append(f'  "{k}": [\n' + ",\n".join("    " + one(o) for o in v) + "\n  ]")
        elif k == "approach":
            lines.append(f'  "{k}": {{\n' + ",\n".join(f'    "{a}": ' + one(o) for a, o in v.items()) + "\n  }")
        else:
            lines.append(f'  "{k}": ' + one(v))
    grid = ",\n".join("    [" + ",".join(f"{v:.4f}".rstrip("0").rstrip(".") for v in row) + "]" for row in C["z"])
    lines.append(f'  "ceiling": {{"x0": {C["x0"]}, "dx": {C["dx"]}, "nx": {C["nx"]}, "da": {C["da"]}, "na": {C["na"]}, '
                 '"z": [\n' + grid + "\n  ]}")
    head = ("// GENERATED by web/tour_data.py from the interior tables (model/interior.py, model/fuselage_parts.py,\n"
            "// model/build.py cockpit_camera): do not edit -- run `python3 web/tour_data.py`.\n"
            "// MODEL axes (x = STA, y = BL + starboard, z = WL); tour.js converts to glTF (X = y, Y = z, Z = x).\n")
    return head + "export const TOUR = {\n" + ",\n".join(lines) + "\n};\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare with the committed file instead of writing it")
    a = ap.parse_args()
    text = render(build_data())
    if a.check:
        cur = OUT.read_text() if OUT.exists() else ""
        if cur != text:
            print(f"{OUT.relative_to(ROOT)} is stale: run python3 web/tour_data.py")
            sys.exit(1)
        print(f"{OUT.relative_to(ROOT)} matches the interior tables")
        return
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
