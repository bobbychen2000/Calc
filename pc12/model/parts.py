"""Part records shared by all component builders."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from cad.mesh import Mesh


@dataclass
class Part:
    id: str
    name: str
    step: str                       # build-step key
    meshes: list = field(default_factory=list)   # [(Mesh, material_name)]
    parent: Optional[str] = None    # parent part id (for nested kinematics)
    pivot: Optional[dict] = None    # {"origin": xyz, "axis": xyz, "kind": str, ...}
    explode: tuple = (0.0, 0.0, 0.0)  # exploded-view offset (model axes, m)
    group: str = ""
    qty: int = 1
    material_note: str = ""
    info: dict = field(default_factory=dict)
    construction: list = field(default_factory=list)  # polylines (list of (n,3) arrays)

    def add(self, mesh: Mesh, material: str):
        if mesh is not None and len(mesh.F):
            self.meshes.append((mesh, material))
        return self

    def tri_count(self):
        return sum(m.nf for m, _ in self.meshes)

    def bounds(self):
        V = np.vstack([m.V for m, _ in self.meshes])
        return V.min(0), V.max(0)
