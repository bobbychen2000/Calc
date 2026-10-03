"""
loftkit.res -- the one tessellation-quality setting of the model (PC12_RES).

    PC12_RES=1   the builders' own grids, as the model was judged in review (the viewer's light tier for phones,
                 out/pc12_low.glb)
    PC12_RES=2   (default) the same grids refined where it shows (out/pc12.glb):
                   * round primitives (cad.mesh revolve, disk, circle2d / sweep_tube, superellipsoid, cylinder) take
                     up to RES x their segment count where their chords miss the circle by more than SEG_TOL
                     (seg(); polygons with fewer than SEG_MIN sides stay polygons) -- not the hidden engine modules
                     (coarse(): seen only through the cutaway / X-ray);
                   * builders whose own grids were coarse where it shows take finer ones (factor(): the seats'
                     rounded cushion rims and outline corners, the chin-inlet duct entry, the strakes' edges);
                   * before the livery is trimmed into a skin, the skin is refined along every paint boundary
                     (cad.refine field criterion, PAINT_LEVELS passes) so stroke and band edges are smooth curves;
                   * every part is then refined by curvature (cad.refine): an edge is split where its curve bows more
                     than TOL[class] from its chord (silhouettes: big radii keep their triangles -- a 30 mm skin grid
                     on a 0.7 m fuselage radius bows 0.16 mm and already shades smoothly) or where its end normals turn
                     more than TURN_DEG while it bows more than MIN_SAG (facets: tight radii, rims, grips, lips get
                     many triangles whatever their sagitta); hidden parts are not refined;
    PC12_RES>2   tighter still (tolerances ~ 1 / RES^2, one more pass per doubling).

Tessellation density is not a shape parameter: refinement never moves an original vertex, every new vertex lies on
the smooth surface the builder's vertex normals describe (between two samples of the analytic surface), and
creases, folds and flat faces are kept (cad.refine).

The GLB's normals are 16-bit in BOTH tiers (normal_bits(): 8-bit normals step by ~0.45 deg, which breaks the studio's
reflected streaks on the glossy paint and the cockpit side windows into stairs -- review round 1 RES1-02: that, not
the triangle count, was the visible part of the upgrade, and phones load the light tier).

Classes (part_class): 'exterior' parts are seen from ~1 m in the viewer, 'interior' (flight deck, cabin) from
~0.3-0.6 m, 'hidden' parts (engine modules under the cowls, firewall, mount) only through the cutaway / X-ray.
"""
from __future__ import annotations

import os

import numpy as np

RES = float(os.environ.get("PC12_RES", "2"))

SEG_MIN = 8                      # segment counts below this are polygons by design (hex nuts, square bars): kept
SEG_TOL = 0.04e-3                # a round primitive whose chords miss its circle by less than this keeps its count


def seg(n: int, r=None) -> int:
    """Segment count of a round primitive (cad.mesh revolve / disk / circle2d / superellipsoid) of radius r at this
    RES: up to RES x the builder's count -- exact samples of the analytic circle -- as many as the chord sagitta
    r (1 - cos(pi / n)) needs to drop below SEG_TOL; polygons (n < SEG_MIN) as drawn."""
    n = int(n)
    if not on() or n < SEG_MIN:
        return n
    n_max = int(round(n * RES))
    if r is None or r <= 0:
        return n_max
    if r * (1.0 - np.cos(np.pi / n)) <= SEG_TOL:
        return n
    need = int(np.ceil(np.pi / np.arccos(max(1.0 - SEG_TOL / r, -1.0))))
    return int(min(n_max, max(n, need)))


# sagitta tolerance (m) at RES 2 per viewing class (silhouettes; review round 1 RES1-01: 0.10 / 0.15 mm split every
# big skin uniformly -- fuselage 84k -> 300k triangles -- and left the coarse small radii as they were)
TOL = {"exterior": 0.30e-3, "interior": 0.35e-3, "hidden": 1.0e-3}
# facets: an edge whose end normals turn more than TURN_DEG (a face whose vertex normals stray ~10 deg from it) is split
# while it bows more than MIN_SAG (m)
TURN_DEG = {"exterior": 20.0, "interior": 20.0, "hidden": None}
MIN_SAG = {"exterior": 0.03e-3, "interior": 0.02e-3, "hidden": 1.0e-3}
# cad.refine bow_max: larger bows -> kept straight (RES1-01: 1 mm left exactly the exterior's large-bow rims straight; the
# face guards of cad.refine -- deviation, lean, bend, S -- keep flat panels flat.  Interior 1 mm: at 4 mm the short
# flat bottom of a crew seat's base plate between two arcs bowed 1.4 mm into the floor; the seats' rims are fine
# enough by their own grids now, seats._rounds)
BOW_MAX = {"exterior": 6.0e-3, "interior": 1.0e-3, "hidden": 1.0e-3}
LEVELS = 3                       # curvature passes at RES 2
PAINT_LEVELS = 1                 # paint-boundary passes before the livery is trimmed (RES 2; 2 passes cost the fuselage
#                                  ~100k triangles for stroke edges the review could not tell apart)
PAINT_NEAR = 0.25                # ... also where a paint region passes between an edge's ends (cad.refine field_near)

HIDDEN = ("eng_", "firewall", "engine_mount", "inlet_duct")
BUDGET_SCALE = 1.75             # triangle budgets set at PC12_RES=1 grow in proportion with the whole model at RES 2
#                                 (1.53M -> ~2.1M triangles); see budget()


def budget(n: int, scale: float = BUDGET_SCALE) -> int:
    """A triangle budget written for the builders' own grids (PC12_RES=1), at this RES (in proportion to the model;
    scale: a piece whose own grid is refined more, the seats' rims)."""
    return int(n) if not on() else int(round(n * scale * max(1.0, RES / 2.0) ** 2))


def normal_bits() -> int:
    """Bits of the GLB's quantised normals (cad.glb): 16 in both tiers -- 8-bit normals broke the reflected streaks on
    the clear-coated paint and the side windows into stairs (+4 bytes a vertex)."""
    return 16


def on() -> bool:
    return RES > 1.0 and not _COARSE[0]


_COARSE = [False]


class coarse:
    """with res.coarse(): ... builds at the builders' own grids (the hidden engine modules: no finer round primitives,
    no factor()): RES1-05, seen only through the cutaway / X-ray."""
    def __enter__(self):
        self._was = _COARSE[0]
        _COARSE[0] = True
        return self

    def __exit__(self, *a):
        _COARSE[0] = self._was
        return False


def factor() -> float:
    """Sample-count factor for builders whose own grids are coarse where it shows (1 at PC12_RES=1, RES above)."""
    return RES if on() else 1.0


def _scale():
    return (2.0 / RES) ** 2


def levels(base=LEVELS) -> int:
    import math
    return 0 if not on() else base + max(0, int(math.ceil(math.log2(RES / 2.0))))


def part_class(pid: str, part) -> str:
    if pid.startswith(HIDDEN):
        return "hidden"
    return "interior" if getattr(part, "step", "") == "interior" else "exterior"


def _kw(cls):
    return dict(tol=TOL[cls] * _scale(), levels=levels(), bow_max=BOW_MAX[cls], turn_deg=TURN_DEG[cls],
                min_sag=MIN_SAG[cls] * _scale())


def refine_part(pid: str, part):
    """Refine a built part in place (all its meshes together: shared paint / patch boundaries stay watertight); hidden
    parts (engine modules, firewall, mount, duct) are left as built."""
    if not on() or not part.meshes:
        return part
    cls = part_class(pid, part)
    if cls == "hidden":
        return part
    from cad.refine import refine
    ms = refine([m for m, _ in part.meshes], **_kw(cls))
    part.meshes = [(m, mat) for m, (_, mat) in zip(ms, part.meshes)]
    return part


def refine_for_trim(mesh, field, cls="exterior"):
    """Refine a skin along the zero sets of field(V) -> (n, k) (and by curvature) before it is trimmed along them.  Its
    open boundary is kept as built (it is shared with meshes refined later, with the whole part: refine_part)."""
    if not on() or mesh.nf == 0:
        return mesh
    from cad.refine import refine
    return refine([mesh], field=field, field_levels=levels(PAINT_LEVELS), field_near=PAINT_NEAR, keep_boundary=True,
                  **_kw(cls))[0]
