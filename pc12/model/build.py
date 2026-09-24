"""
PC-12 master build: runs every component builder, applies the livery, writes
  out/pc12.glb          glTF 2.0 assembly (quantised), hinge pivots in node extras
  out/pc12_meta.json    build steps, bill of materials, construction geometry, checks
and prints a dimensional verification against the official figures.
"""
from __future__ import annotations
import json
import sys
import time
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from cad.glb import to_gl
from model import fuselage as F
from model import fuselage_parts, wing, empennage, powerplant, gear, details, interior, livery
from model import wing as W, empennage as E
from model.assemble import write_glb
from model.lifting import cos_pts

STEPS = [
    ("datum", "Datum, stations & loft lines",
     "Everything is located from the weight-and-balance datum, 3.000 m (118 in) ahead of the firewall. "
     "The fuselage is lofted from four control lines (crown, keel, half-breadth and its water line) and a "
     "super-ellipse section law, the way mould-loft draftsmen defined hulls and fuselages."),
    ("structure", "Primary structure",
     "Frames, stringers, pressure bulkheads and the two-spar wing box go in first. The skins that follow "
     "hide them, so switch to X-ray to see this step again later."),
    ("fuselage_center", "Centre fuselage: pressure cabin",
     "The 1.69 x 1.83 m section around a 5.16 x 1.52 x 1.47 m cabin with a 1.30 m flat floor. "
     "Door and window openings are cut from the lofted skin with signed-distance trims."),
    ("fuselage_fwd", "Forward fuselage & flight deck",
     "The skin rises from the firewall (STA 3,000) to the roof, carrying the windshield and cockpit "
     "side-window openings and the nose-gear bay."),
    ("fuselage_aft", "Aft fuselage & tail cone",
     "Behind the aft pressure bulkhead (STA 9,850) the keel sweeps up for rotation clearance and the "
     "crown drops toward the fin."),
    ("glazing", "Glazing",
     "The windshield is two heated panes with a centre post. Each side has one fixed side window; the PRO "
     "deletes the pilot's direct-vision window. A dark surround trim (NGX/PRO) wraps the flight-deck "
     "glazing. The nine fixed cabin windows are rectangular, PC-24-style and 10 % larger than before. "
     "Every pane is trimmed from the lofted skin by signed-distance constraints and recessed 6 mm "
     "behind a black seal."),
    ("doors", "Doors & emergency exit",
     "The forward airstair door (0.61 x 1.35 m) opens downward. The aft cargo door (1.35 x 1.32 m) opens "
     "upward. The Type III over-wing exit is on the right. Each door is a solidified slab cut from the "
     "skin, with its hinge line stored for animation."),
    ("wing", "Wing",
     "The tapered wing has an unswept quarter-chord and sections from LS(1)-0417MOD at the root to "
     "LS(1)-0313 at the tip. The planform is solved from the official 16.28 m span and 25.81 m² "
     "area plus the POH aft CG limit (46 % MAC), which puts LEMAC at STA 5,318."),
    ("controls_wing", "Flaps & ailerons",
     "A single-piece Fowler flap covers 67 % of each trailing edge, running on three track fairings "
     "(0/15/30/40\u00b0). The short-span mass-balanced ailerons each carry a Flettner geared balance tab "
     "that moves opposite to the aileron; the left one doubles as electric trim. Coves and noses share "
     "the wing's own sections, so the gaps are exact."),
    ("winglets", "Winglets",
     "The blended winglets are lofted along a bend-then-straight path, canted 22° outboard and "
     "swept 42°. They set the 16.28 m overall span."),
    ("empennage_v", "Fin, dorsal fillet, rudder & strakes",
     "The swept fin carries an enlarged glass-fibre dorsal fillet and a mass-balanced rudder. Twin "
     "Kevlar ventral strakes sit under the tail cone."),
    ("empennage_h", "T-tail: tailplane & elevators",
     "The variable-incidence tailplane (5.20 m span) has raked tips and paired elevators, capped by the "
     "fin/tailplane bullet fairing at 4.26 m overall height."),
    ("powerplant", "Powerplant: PT6E-67XP",
     "The reverse-flow free-turbine engine is sized to its EASA type certificate: 1,870.9 mm long and "
     "481.8 mm in diameter. Air enters the rear inlet screen and passes a 4-axial + 1-centrifugal "
     "compressor, a folded annular combustor, a single-stage compressor turbine and a 2-stage power "
     "turbine. It exits through twin exhaust ducts ahead of the 2-stage planetary gearbox. FADEC-controlled, "
     "1,200 shp take-off."),
    ("cowling", "Cowlings, chin inlet & exhausts",
     "The carbon/Nomex upper and lower cowls split on the thrust line. The chin inlet feeds the "
     "rear-facing engine plenum, and twin stacks exhaust just behind the propeller."),
    ("propeller", "Propeller: Hartzell 5-blade composite",
     "The prop is 2.67 m (105 in) in diameter and turns 1,700 rpm, or 1,550 rpm in low-speed mode. It "
     "is full-feathering and reversing. Each blade is lofted through twisted cambered sections with a "
     "swept tip and pivots on its own pitch axis."),
    ("gear", "Landing gear",
     "Per the POH, electromechanical actuators drive the gear and over-centre two-piece folding struts "
     "lock it down. The trailing-link mains retract inward, with one door each attached to the leg; the "
     "tyres stay about 1 inch proud of the wells. The nose unit retracts aft and is fully enclosed by its "
     "doors. Track 4.53 m, wheelbase 3.48 m, prop clearance 0.32 m."),
    ("interior", "Flight deck & cabin",
     "The PC-12 PRO flight deck has Garmin G3000 PRIME: three 14-inch touchscreens and two touch "
     "controllers. The cabin shown is the six-seat executive layout, with baggage behind the "
     "cargo door."),
    ("details", "Systems & details",
     "The weather-radar pod on the right wing is standard; on the PRO its radome is enlarged for the "
     "12-inch GWX 8000 antenna. Also added: nav, strobe and beacon lights, VHF/GPS/XPDR/DME antennas, "
     "heated pitot-static probes and static dischargers."),
    ("paint", "Paint & roll-out",
     "The livery is an original scheme, not a real operator's. It is trimmed into the skins as exact "
     "geometry: white, a cool-grey belly, and a navy swoosh with a brass pinstripe."),
]


def pl(a):
    """polyline -> gl-axes list rounded to mm."""
    return np.round(to_gl(np.asarray(a, float)), 3).tolist()


def construction():
    C = {k: [] for k, *_ in STEPS}
    # --- datum & loft lines
    xs = np.linspace(0.95, 14.36, 120)
    C["datum"].append({"kind": "datum", "pts": pl([[0, -1.2, 0], [0, 1.2, 0], [0, 1.2, 3.2], [0, -1.2, 3.2], [0, -1.2, 0]])})
    C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, 0 * xs, F.z_top(xs)], 1)), "label": "crown"})
    C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, 0 * xs, F.z_bot(xs)], 1)), "label": "keel"})
    for s in (1, -1):
        C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, s * F.half_w(xs), F.z_mw(xs)], 1)),
                           "label": "max breadth" if s > 0 else None})
    t = np.linspace(0, 1, 73)
    for x in list(np.arange(1.0, 14.3, 0.75)) + [14.3]:
        C["datum"].append({"kind": "section", "pts": pl(F.section(np.full_like(t, x), t))})
    for x in range(0, 15):
        C["datum"].append({"kind": "tick", "pts": pl([[x, -1.5, 0.002], [x, -1.9 if x % 5 == 0 else -1.7, 0.002]]),
                           "label": f"STA {x*1000:,}" if x % 5 == 0 or x == 3 else None})
    C["datum"].append({"kind": "line", "pts": pl([[0, -1.5, 0.002], [14.8, -1.5, 0.002]])})
    # fuselage steps: sections
    for key, a, b in (("fuselage_center", 4.36, 9.85), ("fuselage_fwd", 3.0, 4.36), ("fuselage_aft", 9.85, 14.36)):
        for x in np.linspace(a, b, max(3, int((b - a) / 0.5))):
            C[key].append({"kind": "section", "pts": pl(F.section(np.full_like(t, x), t))})
    # --- wing: planform, spars, MAC, sections
    ys = np.linspace(0, W.SEMI, 30)
    for s in (1, -1):
        le = np.array([W.section_at(y).le for y in ys]) * [1, s, 1]
        te = np.array([W.section_at(y).point(np.array(1.0), np.array(0.0)) for y in ys]) * [1, s, 1]
        C["wing"].append({"kind": "line", "pts": pl(le)})
        C["wing"].append({"kind": "line", "pts": pl(te)})
        for frac in (0.15, 0.66):
            sp = np.array([W.section_at(y).camber_pt(np.array(frac)) for y in ys]) * [1, s, 1]
            C["wing"].append({"kind": "spar", "pts": pl(sp)})
        qc = np.array([W.section_at(y).point(np.array(0.25), np.array(0.0)) for y in ys]) * [1, s, 1]
        C["wing"].append({"kind": "axis", "pts": pl(qc), "label": "c/4 unswept" if s > 0 else None})
        for y in (0.0, W.SEMI / 2, W.SEMI):
            sec = W.section_at(y)
            xx = cos_pts(40)
            loop = np.vstack([sec.lower(xx[::-1]), sec.upper(xx[1:])]) * [1, s, 1]
            C["wing"].append({"kind": "section", "pts": pl(loop)})
    m, ym, lemac = W.mac()
    sec = W.section_at(ym)
    C["wing"].append({"kind": "mac", "pts": pl([sec.le, sec.le + [m, 0, 0]]), "label": f"MAC {m*1000:.0f} mm"})
    # --- control hinge lines
    for s in (1, -1):
        for y0, y1, xc in ((W.Y_FLAP[0], W.Y_FLAP[1], 0.73), (W.Y_AIL[0], W.Y_AIL[1], W.AIL_XH)):
            a = W.section_at(y0).camber_pt(np.array(xc)) * [1, s, 1]
            b = W.section_at(y1).camber_pt(np.array(xc)) * [1, s, 1]
            C["controls_wing"].append({"kind": "axis", "pts": pl([a, b])})
    # --- winglet path
    arr, seg = W.winglet_path()
    for s in (1, -1):
        le0 = W.section_at(W.SEMI).le[0]
        C["winglets"].append({"kind": "axis", "pts": pl(np.stack([np.full(len(arr), le0 + 0.25 * W.C_TIP), s * arr[:, 0], arr[:, 1]], 1))})
    # --- empennage
    zs = np.linspace(E.FIN_Z0, E.FIN_Z1, 20)
    C["empennage_v"].append({"kind": "line", "pts": pl([E.fin_section(z).le for z in zs])})
    C["empennage_v"].append({"kind": "line", "pts": pl([E.fin_section(z).point(np.array(1.0), np.array(0.0)) for z in zs])})
    C["empennage_v"].append({"kind": "axis", "pts": pl([E.fin_section(z).point(np.array(E.RUD_XH), np.array(0.0)) for z in (E.RUD_Z[0], E.RUD_Z[1])])})
    ys = np.linspace(0, E.STAB_TIP_Y, 20)
    for s in (1, -1):
        C["empennage_h"].append({"kind": "line", "pts": pl(np.array([E.stab_section(y).le for y in ys]) * [1, s, 1])})
        C["empennage_h"].append({"kind": "line", "pts": pl(np.array([E.stab_section(y).point(np.array(1.0), np.array(0.0)) for y in ys]) * [1, s, 1])})
        C["empennage_h"].append({"kind": "axis", "pts": pl(np.array([E.stab_section(y).point(np.array(E.ELEV_XH), np.array(0.0)) for y in E.ELEV_Y]) * [1, s, 1])})
    # --- powerplant thrust line & prop disc
    C["powerplant"].append({"kind": "axis", "pts": pl([[0.2, 0, F.PROP_AXIS_Z], [3.2, 0, F.PROP_AXIS_Z]]), "label": "thrust line"})
    th = np.linspace(0, 2 * np.pi, 97)
    disc = np.stack([np.full_like(th, 0.80), 1.335 * np.cos(th), F.PROP_AXIS_Z + 1.335 * np.sin(th)], 1)
    C["propeller"].append({"kind": "circle", "pts": pl(disc), "label": "Ø 2,670"})
    # --- gear: retraction arcs and ground line
    from model import gear as G
    for s in (1, -1):
        T = G.MAIN_TRUNNION * [1, s, 1]
        A = G.MAIN_AXLE * [1, s, 1]
        r = A - T
        arc = []
        for a in np.linspace(0, np.radians(90), 20):
            ang = -s * a
            c, sn = np.cos(ang), np.sin(ang)
            arc.append(T + [r[0], r[1] * c - r[2] * sn, r[1] * sn + r[2] * c])
        C["gear"].append({"kind": "arc", "pts": pl(arc)})
    P, A = G.NOSE_PIVOT, G.NOSE_AXLE
    r = A - P
    arc = []
    for a in np.linspace(0, np.radians(95), 20):
        c, sn = np.cos(-a), np.sin(-a)
        arc.append(P + [r[0] * c + r[2] * sn, 0, -r[0] * sn + r[2] * c])
    C["gear"].append({"kind": "arc", "pts": pl(arc)})
    C["gear"].append({"kind": "dim", "pts": pl([[G.MAIN_AXLE[0], -G.TRACK / 2, 0.003], [G.MAIN_AXLE[0], G.TRACK / 2, 0.003]]), "label": "track 4,530"})
    C["gear"].append({"kind": "dim", "pts": pl([[G.NOSE_AXLE[0], 0, 0.003], [G.MAIN_AXLE[0], 0, 0.003]]), "label": "wheelbase 3,480"})
    return C


def verify(parts):
    ext = [p for k, p in parts.items() if p.step not in ("interior", "structure") and p.id not in ("firewall",)]
    V = np.vstack([m.V for p in ext for m, _ in p.meshes])
    # propeller with one blade down: lowest point at prop radius
    blades = [m.V for k, p in parts.items() if k.startswith("blade_") for m, _ in p.meshes]
    Bv = np.vstack(blades)
    r = np.sqrt(Bv[:, 1] ** 2 + (Bv[:, 2] - F.PROP_AXIS_Z) ** 2).max()
    from model import gear as G
    checks = [
        ("Overall length (spinner tip -> aft-most)", 14.40, V[:, 0].max() - V[:, 0].min()),
        ("Wing span (over winglets)", 16.28, V[:, 1].max() - V[:, 1].min()),
        ("Overall height (static)", 4.26, V[:, 2].max()),
        ("Tailplane span", 5.20, 2 * max(E.STAB_TIP_Y, 0)),
        ("Wing reference area (m^2)", 25.81, 2 * W.SEMI * (W.C_ROOT + W.C_TIP) / 2),
        ("Propeller diameter", 2.67, 2 * r),
        ("Propeller ground clearance (blade down)", 0.32, F.PROP_AXIS_Z - r),
        ("Wheel track", 4.53, 2 * G.MAIN_AXLE[1]),
        ("Wheelbase", 3.48, G.MAIN_AXLE[0] - G.NOSE_AXLE[0]),
        ("Cabin floor width (OML - lining)", 1.30, 2 * float(F.side_y(6.0, 1.12)) - 2 * 0.045),
    ]
    out = []
    for name, target, got in checks:
        out.append({"check": name, "official": target, "model": round(float(got), 3),
                    "delta_mm": round(1000 * (float(got) - target), 1)})
    return out


def build_parts():
    """Build every component (no files written). Returns the ordered parts dict."""
    parts = {}
    interior.build_structure(parts)
    fuselage_parts.build(parts)
    wing.build(parts)
    empennage.build(parts)
    powerplant.build(parts)
    gear.build(parts)
    interior.build_flightdeck(parts)
    interior.build_cabin(parts)
    details.build(parts)
    livery.apply(parts)
    order = {k: i for i, (k, *_) in enumerate(STEPS)}
    ids = sorted(parts.keys(), key=lambda k: order.get(parts[k].step, 99))
    return {k: parts[k] for k in ids}


def main():
    t0 = time.time()
    parts = build_parts()
    ids = list(parts.keys())
    checks = verify(parts)
    size, stats = write_glb(parts, str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out/pc12.glb",
                            meta={"model": "Pilatus PC-12 PRO", "units": "m", "datum": "STA 0 = 3.000 m fwd of firewall"})
    bom = []
    for k, p in parts.items():
        bom.append({"id": k, "name": p.name, "step": p.step, "group": p.group, "qty": p.qty,
                    "note": p.material_note, "tris": p.tri_count(), "info": p.info,
                    "materials": sorted(set(m for _, m in p.meshes))})
    meta = {
        "steps": [{"key": k, "title": t, "text": d, "parts": [p for p in ids if parts[p].step == k]} for k, t, d in STEPS],
        "bom": bom,
        "construction": construction(),
        "checks": checks,
        "stats": {"triangles": stats["triangles"], "vertices": stats["vertices"], "glb_bytes": size,
                  "parts": len(parts)},
        "wing": {"semi_span": W.SEMI, "root_chord": W.C_ROOT, "tip_chord": W.C_TIP, "mac": W.MAC,
                 "lemac": W.LEMAC, "x_qc": W.X_QC},
    }
    with open(str(__import__("pathlib").Path(__file__).resolve().parents[1]) + "/out/pc12_meta.json", "w") as f:
        json.dump(meta, f, separators=(",", ":"))
    print(f"parts {len(parts)}  triangles {stats['triangles']:,}  GLB {size/1e6:.2f} MB  ({time.time()-t0:.1f}s)")
    for c in checks:
        print(f"  {c['check']:44s} official {c['official']:7.3f}  model {c['model']:7.3f}  delta {c['delta_mm']:+7.1f} mm")
    return parts


if __name__ == "__main__":
    main()
