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

def _steps():
    """Build-step texts, generated from the parameters (stale literals were S3-15)."""
    from model import fuselage_parts as FP, cockpit_glazing as CG, gear as G, powerplant as PP, details as D
    n_fixed = sum(len(v) for v in FP.FIXED_WINDOWS.values())
    n_lines = len(F.CONTROL_LINES)
    cab = F.cabin_numbers()
    return [
        ("datum", "Datum, stations & loft lines",
         "Everything is located from the weight-and-balance datum, 3.000 m (118 in) ahead of the firewall. "
         f"The fuselage is lofted from {n_lines} control lines (crown, keel, half-breadth and its water line, plus "
         "the four section-law exponents) through a two-exponent super-ellipse section law, the way mould-loft "
         "draftsmen defined hulls and fuselages. The knots are fitted to the Pilatus NGX model drawing "
         f"(STA {F.STA['cowl_front'] * 1000:,.0f} to {F.STA['tail_end'] * 1000:,.0f})."),
        ("structure", "Primary structure",
         f"Frames at the Pilatus frame stations (FR10-FR40 and on to the tail closure), interrupted at the door and "
         "window cut-outs, stringers above and below the window belt, pressure bulkheads and the two-spar wing box "
         "go in first. The skins that follow hide them, so switch to X-ray to see this step again later."),
        ("fuselage_center", "Centre fuselage: pressure cabin",
         f"The {2 * cab['max_breadth'] / 2:.2f} x {cab['depth']:.2f} m section around a 5.16 x 1.52 x 1.47 m cabin "
         f"whose flat floor sits at WL {F.CABIN_FLOOR_WL * 1000:,.0f} ({F.cabin_floor_width():.2f} m inside the "
         "lining). Door and window openings are cut from the lofted skin with signed-distance trims."),
        ("fuselage_fwd", "Forward fuselage & flight deck",
         "The skin rises from the firewall (STA 3,000) to the roof, carrying the windshield and cockpit "
         "side-window openings and the nose-gear bay."),
        ("fuselage_aft", "Aft fuselage & tail cone",
         f"Behind the aft pressure bulkhead (STA {F.STA['aft_pressure_bulkhead'] * 1000:,.0f}) the keel sweeps up "
         "for rotation clearance and the crown drops toward the fin. The tail cone ends at the rudder leading edge, "
         "closed by a flat bulkhead fairing, so the full-height rudder can swing behind it."),
        ("glazing", "Glazing",
         "The windshield is two heated panes with a centre post. Each side has one fixed side window; the PRO "
         "deletes the pilot's direct-vision window. The dark PRO windshield mask wraps the flight-deck glazing. "
         f"{n_fixed} fixed cabin windows ({len(FP.FIXED_WINDOWS[-1])} left, {len(FP.FIXED_WINDOWS[1])} right) plus "
         "the windows in the cargo door and the emergency exit are rectangular, PC-24-style and 10 % larger than "
         "before. Every pane is trimmed from the lofted skin by signed-distance constraints and recessed 6 mm "
         "behind a black seal."),
        ("doors", "Doors & emergency exit",
         f"The forward airstair door ({2 * FP.AIRSTAIR['hx']:.2f} x {2 * FP.AIRSTAIR['hz']:.2f} m clear opening) "
         f"opens {FP.AIRSTAIR['open_deg']:.0f}° downward on integral steps. The aft cargo door "
         f"({2 * FP.CARGO['hx']:.2f} x {2 * FP.CARGO['hz']:.2f} m) opens {FP.CARGO['open_deg']:.0f}° upward. The "
         "plug-type over-wing emergency exit is on the right. Each door is a slab cut from the skin along its panel "
         "seam, with a door stop and jamb round the clear opening, and its hinge line stored for animation."),
        ("wing", "Wing",
         "The tapered wing has an almost unswept quarter-chord and sections from LS(1)-0417MOD at the root to "
         f"LS(1)-0313 at the tip, with {np.degrees(W.DIHEDRAL):.2f}° dihedral outboard of a flat centre section. "
         "The planform is taken from the Pilatus drawing and the root chord solved for the official 16.28 m span "
         f"and 25.81 m² projected area: MAC {W.MAC * 1000:,.0f} mm, LEMAC STA {W.LEMAC * 1000:,.0f}; the POH aft "
         f"CG limit STA {W.AFT_CG * 1000:,.0f} lies at {100 * (W.AFT_CG - W.LEMAC) / W.MAC:.0f} % MAC. A belly "
         "fairing encloses the carry-through, which stays under the cabin floor, and a concave root fillet runs "
         "from the fairing nose along the wing root, fading out ahead of the cargo door."),
        ("controls_wing", "Flaps & ailerons",
         "A single-piece Fowler flap covers 67 % of each trailing edge, stowed under a long shroud and running on "
         "three track fairings (0/15/30/40°). The constant-chord ailerons have a straight hinge line; each "
         "carries a Flettner geared balance tab that moves opposite to the aileron, the left one doubling as "
         "electric trim. Coves and noses share the wing's own sections, so the gaps are exact."),
        ("winglets", "Winglets",
         "The blended winglets are lofted along a bend-then-straight path "
         f"(bend radius {W.WL_BEND_R:.2f} m) canted {np.degrees(W.WL_CANT):.0f}° from the vertical, their trailing "
         "edge sweeping back toward the tip. They set the 16.28 m overall span."),
        ("empennage_v", "Fin, dorsal fillet, rudder & strakes",
         "The swept NACA 0018 fin stands on the tail cone behind a glass-fibre dorsal fin whose root fillet fairs "
         "into the tail cone. The single-piece rudder runs from the bullet down to the ventral edge behind the "
         "tail-cone closure; a thin ventral fairing and twin Kevlar ventral strakes sit under the tail cone."),
        ("empennage_h", "T-tail: tailplane & elevators",
         "The variable-incidence tailplane (5.20 m span) has raked tips and paired elevators with horn balances, "
         "capped by the fin/tailplane bullet fairing at 4.26 m overall height."),
        ("powerplant", "Powerplant: PT6E-67XP",
         "The reverse-flow free-turbine engine is sized to its EASA type certificate: 1,870.9 mm long and "
         "481.8 mm in diameter, installed on the thrust line (2° nose-down, 2° right). Air enters the rear inlet "
         "screen and passes a 4-axial + 1-centrifugal compressor, a folded annular combustor, a single-stage "
         "compressor turbine and a 2-stage power turbine. It exits through twin exhaust ducts ahead of the 2-stage "
         "planetary gearbox. FADEC-controlled, 1,200 shp take-off."),
        ("cowling", "Cowlings, chin inlet & exhausts",
         "The carbon/Nomex upper and lower cowls split on the thrust line. The chin inlet's polished lip rings the "
         "mouth cut into the keel step under the spinner, and its duct runs under the engine to the rear-facing "
         "plenum. Twin scarfed stacks with heat-tinted collars exhaust just behind the propeller."),
        ("propeller", "Propeller: Hartzell 5-blade composite",
         "The prop is 2.67 m (105 in) in diameter and turns 1,700 rpm, or 1,550 rpm in low-speed mode. It "
         "is full-feathering and reversing. The spinner meets the cowl front on the tilted, yawed thrust axis. "
         "Each blade is lofted through twisted cambered sections with a swept tip and pivots on its own pitch axis."),
        ("gear", "Landing gear",
         "Per the POH, electromechanical actuators drive the gear and over-centre two-piece folding struts "
         "lock it down. The trailing-link mains retract inward, with one door each attached to the leg; the "
         "tyres stay about 1 inch proud of the wells. The nose unit retracts aft into a tunnel under the centre "
         f"pedestal and is fully enclosed by its doors. Track {G.TRACK * 1000:,.0f} mm, wheelbase "
         f"{G.WHEELBASE * 1000:,.0f} mm, prop clearance {PP.prop_clearance() * 1000:.0f} mm."),
        ("interior", "Flight deck & cabin",
         "The PC-12 PRO flight deck has Garmin G3000 PRIME: three 14-inch touchscreens and two touch "
         "controllers. The cabin shown is the six-seat executive layout, clear of the airstair door, with "
         "baggage behind a net at the cargo door."),
        ("details", "Systems & details",
         "The weather-radar pod at the right wing tip is standard; on the PRO its radome is enlarged for the "
         "12-inch GWX 8000 antenna. Also added: nav and strobe lights in the winglets, red beacons on the tail "
         "bullet and the belly, VHF/GPS/XPDR/DME antennas, heated pitot-static probes and static dischargers."),
        ("paint", "Paint & roll-out",
         f"The livery is that of PC-12 PRO {__import__('model.livery', fromlist=['x']).MASK_SCHEME} (N81DW), the "
         "first PRO delivered, without lettering: deep metallic blue, a light-blue swoosh, white and navy "
         "calligraphic pinstripes, a white fin cap and bullet, silver tailplane, dark wing undersides and the PRO "
         "windshield mask, all trimmed into the skins as exact geometry."),
    ]


STEPS = _steps()


def pl(a):
    """polyline -> gl-axes list rounded to mm."""
    return np.round(to_gl(np.asarray(a, float)), 3).tolist()


def construction():
    C = {k: [] for k, *_ in STEPS}
    # --- datum & loft lines
    x0, x1 = F.STA["cowl_front"], F.STA["tail_end"]
    xs = np.linspace(x0, x1, 120)
    C["datum"].append({"kind": "datum", "pts": pl([[0, -1.2, 0], [0, 1.2, 0], [0, 1.2, 3.2], [0, -1.2, 3.2], [0, -1.2, 0]])})
    C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, 0 * xs, F.z_top(xs)], 1)), "label": "crown"})
    C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, 0 * xs, F.z_bot(xs)], 1)), "label": "keel"})
    for s in (1, -1):
        C["datum"].append({"kind": "line", "pts": pl(np.stack([xs, s * F.half_w(xs), F.z_mw(xs)], 1)),
                           "label": "max breadth" if s > 0 else None})
    t = np.linspace(0, 1, 73)
    for x in list(np.arange(1.25, x1, 0.75)) + [x1]:
        C["datum"].append({"kind": "section", "pts": pl(F.section(np.full_like(t, x), t))})
    for x in range(0, 15):
        C["datum"].append({"kind": "tick", "pts": pl([[x, -1.5, 0.002], [x, -1.9 if x % 5 == 0 else -1.7, 0.002]]),
                           "label": f"STA {x*1000:,}" if x % 5 == 0 or x == 3 else None})
    C["datum"].append({"kind": "line", "pts": pl([[0, -1.5, 0.002], [14.8, -1.5, 0.002]])})
    # fuselage steps: sections
    from model.fuselage_parts import SPLIT_FWD, SPLIT_AFT
    x_tc = float(E.tail_cut_x(F.z_bot(12.7)))
    for key, a, b in (("fuselage_center", SPLIT_FWD, SPLIT_AFT), ("fuselage_fwd", F.STA["firewall"], SPLIT_FWD),
                      ("fuselage_aft", SPLIT_AFT, x_tc)):
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
    # --- control hinge lines: the flap from its pivot data, the aileron from the straight hinge W.AIL_HINGE
    for s in (1, -1):
        a = W.section_at(W.Y_FLAP[0]).camber_pt(np.array(0.73)) * [1, s, 1]
        b = W.section_at(W.Y_FLAP[1]).camber_pt(np.array(0.73)) * [1, s, 1]
        C["controls_wing"].append({"kind": "axis", "pts": pl([a, b]), "label": "flap hinge" if s > 0 else None})
        ends = []
        for y in W.Y_AIL:
            xh = float(W.ail_xh(y))
            ends.append(W.section_at(y).camber_pt(np.array(xh)) * [1, s, 1])
        C["controls_wing"].append({"kind": "axis", "pts": pl(ends), "label": "aileron hinge" if s > 0 else None})
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
    from model import powerplant as PP
    C["powerplant"].append({"kind": "axis", "pts": pl(PP.axis_point(np.array([0.2, 3.2]))), "label": "thrust line"})
    th = np.linspace(0, 2 * np.pi, 97)
    R = PP.thrust_rotation()
    disc = PP.prop_hub() + (np.stack([np.zeros_like(th), PP.PROP_R * np.cos(th), PP.PROP_R * np.sin(th)], 1) @ R.T)
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
    for a in np.linspace(0, np.radians(abs(G.NOSE_RETRACT_DEG)), 20):
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
    from model import powerplant as PP
    # propeller diameter / clearance: blade tips measured in the (tilted) disc; clearance = lowest blade point
    ax = PP.thrust_dir()
    w = Bv - PP.prop_hub()
    r = np.linalg.norm(w - np.outer(w @ ax, ax), axis=1).max()
    checks = [
        ("Overall length (spinner tip -> aft-most)", 14.40, V[:, 0].max() - V[:, 0].min(), "eq"),
        ("Wing span (over winglets)", 16.28, V[:, 1].max() - V[:, 1].min(), "eq"),
        ("Overall height (static)", 4.26, V[:, 2].max(), "eq"),
        ("Tailplane span", 5.20, 2 * max(E.STAB_TIP_Y, 0), "eq"),
        # D5: the published area is the TOTAL projected plan area (both halves through the fuselage, aileron kink and
        # the winglets' plan projection): wing.planform_area()
        ("Wing area, total projected (m^2)", 25.81, W.planform_area(), "eq"),
        ("Propeller diameter", 2.67, 2 * r, "eq"),
        ("Propeller ground clearance (blade down)", 0.32, PP.prop_hub()[2] - r * np.sqrt(1.0 - ax[2] ** 2), "eq"),
        ("Wheel track", 4.53, 2 * G.MAIN_AXLE[1], "eq"),
        ("Wheelbase", 3.48, G.MAIN_AXLE[0] - G.NOSE_AXLE[0], "eq"),
        (f"Cabin floor width at WL {F.CABIN_FLOOR_WL * 1000:.0f} (OML - {F.CABIN_LINING * 1000:.0f} mm lining)",
         1.30, F.cabin_floor_width(6.0), "min"),
    ]
    out = []
    for name, target, got, kind in checks:
        area = "m^2" in name
        d = float(got) - target
        ok = (d >= -0.002) if kind == "min" else (abs(d) <= (0.005 if area else 0.002))
        out.append({"check": name, "official": target, "model": round(float(got), 3), "kind": kind,
                    "delta_mm": None if area else round(1000 * d, 1), "delta": round(d, 4), "ok": bool(ok)})
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
        dl = f"{c['delta']:+7.3f} m2" if c["delta_mm"] is None else f"{c['delta_mm']:+7.1f} mm"
        rel = ">=" if c["kind"] == "min" else "  "
        print(f"  {c['check']:52s} official {rel}{c['official']:7.3f}  model {c['model']:7.3f}  delta {dl}  "
              f"{'OK' if c['ok'] else 'FAIL'}")
    return parts


if __name__ == "__main__":
    main()
