"""
loftkit.res -- the one tessellation-quality setting of the model (PC12_RES).

    PC12_RES=1   the builders' own grids, as the model was judged in review (the viewer's light tier for phones,
                 out/pc12_low.glb)
    PC12_RES=2   (default) the same grids refined where it shows (out/pc12.glb):
                   * round primitives (cad.mesh revolve, disk, circle2d / sweep_tube, superellipsoid, cylinder) take
                     up to RES x their segment count where their chords miss the circle by more than SEG_TOL
                     (seg(); polygons with fewer than SEG_MIN sides stay polygons);
                   * before the livery is trimmed into a skin, the skin is refined along every paint boundary
                     (cad.refine field criterion, PAINT_LEVELS passes: the 30 mm skin grid cuts its strokes with
                     ~8 mm segments) and by curvature, so stroke and band edges are smooth curves;
                   * every part is then refined by curvature (cad.refine: split where the edge curve bows more
                     than TOL[class] from its chord) -- tight radii, leading edges, tubes and cushions get many
                     triangles, flat panels keep theirs;
    PC12_RES>2   tighter still (tolerances ~ 1 / RES^2, one more pass per doubling).

Tessellation density is not a shape parameter: refinement never moves an original vertex, every new vertex lies on
the smooth surface the builder's vertex normals describe (between two samples of the analytic surface), and
creases, folds and flat faces are kept (cad.refine).

The GLB's normals are 16-bit at RES > 1 (normal_bits(): 8-bit normals step by ~0.45 deg, which breaks the studio's
reflected streaks on the glossy paint into stairs), 8-bit at RES 1.

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
    if RES <= 1.0 or n < SEG_MIN:
        return n
    n_max = int(round(n * RES))
    if r is None or r <= 0:
        return n_max
    if r * (1.0 - np.cos(np.pi / n)) <= SEG_TOL:
        return n
    need = int(np.ceil(np.pi / np.arccos(max(1.0 - SEG_TOL / r, -1.0))))
    return int(min(n_max, max(n, need)))


# sagitta tolerance (m) at RES 2 per viewing class
TOL = {"exterior": 0.10e-3, "interior": 0.15e-3, "hidden": 1.0e-3}
BOW_MAX = {"exterior": 1.0e-3, "interior": 0.5e-3, "hidden": 1.0e-3}   # cad.refine bow_max: larger bows -> kept straight
LEVELS = 3                       # curvature passes at RES 2
PAINT_LEVELS = 2                 # paint-boundary passes before the livery is trimmed (RES 2)
PAINT_NEAR = 0.25                # ... also where a paint region passes between an edge's ends (cad.refine field_near)

HIDDEN = ("eng_", "firewall", "engine_mount", "inlet_duct")
BUDGET_SCALE = 1.75             # triangle budgets set at PC12_RES=1 grow in proportion with the whole model at RES 2
#                                 (1.53M -> ~2.6M triangles); see budget()


def budget(n: int) -> int:
    """A triangle budget written for the builders' own grids (PC12_RES=1), at this RES (in proportion to the model)."""
    return int(n) if not on() else int(round(n * BUDGET_SCALE * max(1.0, RES / 2.0) ** 2))


def normal_bits() -> int:
    """Bits of the GLB's quantised normals (cad.glb): 16 for the refined model (smooth reflections on the clear-coated
    paint), 8 at PC12_RES=1 (the light tier, as it was judged; half the normal data for phones)."""
    return 16 if on() else 8


def on() -> bool:
    return RES > 1.0


def _scale():
    return (2.0 / RES) ** 2


def levels(base=LEVELS) -> int:
    import math
    return 0 if not on() else base + max(0, int(math.ceil(math.log2(RES / 2.0))))


def part_class(pid: str, part) -> str:
    if pid.startswith(HIDDEN):
        return "hidden"
    return "interior" if getattr(part, "step", "") == "interior" else "exterior"


def refine_part(pid: str, part):
    """Refine a built part in place (all its meshes together: shared paint / patch boundaries stay watertight)."""
    if not on() or not part.meshes:
        return part
    from cad.refine import refine
    cls = part_class(pid, part)
    ms = refine([m for m, _ in part.meshes], tol=TOL[cls] * _scale(), levels=levels(), bow_max=BOW_MAX[cls])
    part.meshes = [(m, mat) for m, (_, mat) in zip(ms, part.meshes)]
    return part


def refine_for_trim(mesh, field, cls="exterior"):
    """Refine a skin along the zero sets of field(V) -> (n, k) (and by curvature) before it is trimmed along them.  Its
    open boundary is kept as built (it is shared with meshes refined later, with the whole part: refine_part)."""
    if not on() or mesh.nf == 0:
        return mesh
    from cad.refine import refine
    return refine([mesh], tol=TOL[cls] * _scale(), levels=levels(), field=field, field_levels=levels(PAINT_LEVELS),
                  field_near=PAINT_NEAR, keep_boundary=True, bow_max=BOW_MAX[cls])[0]
