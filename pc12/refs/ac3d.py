"""Minimal AC3D (.ac) reader -> list of (name, V (n,3), tris (m,3)) in world coords."""
import numpy as np


def read_ac(path):
    lines = open(path, encoding="latin-1").read().splitlines()
    i = 0
    out = []

    def parse_object(i, parent_M):
        assert lines[i].startswith("OBJECT"), lines[i]
        i += 1
        name, loc, rot = "", np.zeros(3), np.eye(3)
        V, tris, kids = None, [], 0
        while i < len(lines):
            L = lines[i].strip()
            if L.startswith("name"):
                name = L.split('"')[1] if '"' in L else L.split()[1]
            elif L.startswith("loc"):
                loc = np.array(list(map(float, L.split()[1:4])))
            elif L.startswith("rot"):
                rot = np.array(list(map(float, L.split()[1:10]))).reshape(3, 3)
            elif L.startswith("numvert"):
                n = int(L.split()[1])
                V = np.array([list(map(float, lines[i + 1 + k].split()[:3])) for k in range(n)])
                i += n
            elif L.startswith("numsurf"):
                ns = int(L.split()[1])
                i += 1
                for _ in range(ns):
                    # SURF / mat / refs
                    while not lines[i].strip().startswith("refs"):
                        i += 1
                    nr = int(lines[i].split()[1])
                    idx = [int(lines[i + 1 + k].split()[0]) for k in range(nr)]
                    i += nr + 1
                    for k in range(1, nr - 1):
                        tris.append((idx[0], idx[k], idx[k + 1]))
                continue
            elif L.startswith("kids"):
                kids = int(L.split()[1])
                i += 1
                break
            i += 1
        M = parent_M.copy()
        T = np.eye(4)
        T[:3, :3] = rot
        T[:3, 3] = loc
        M = parent_M @ T
        if V is not None and len(tris):
            Vw = V @ M[:3, :3].T + M[:3, 3]
            out.append((name, Vw, np.array(tris)))
        for _ in range(kids):
            i = parse_object(i, M)
        return i

    while i < len(lines) and not lines[i].startswith("OBJECT"):
        i += 1
    parse_object(i, np.eye(4))
    return out


if __name__ == "__main__":
    import sys
    objs = read_ac(sys.argv[1])
    allV = np.vstack([v for _, v, _ in objs])
    print("objects", len(objs), "bounds", allV.min(0).round(3), allV.max(0).round(3))
    for n, v, t in objs:
        print(f"  {n:14s} verts {len(v):5d} tris {len(t):5d}  min {v.min(0).round(2)} max {v.max(0).round(2)}")
