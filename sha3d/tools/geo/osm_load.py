"""Merge OSM API 0.6 /map tiles into one in-memory dataset (nodes, ways, relations).

Usage (run with python3 -I, data dir passed as an argument):
    python3 -I sha3d/tools/geo/osm_load.py sha3d/refs/cache/osm  out.json

Writes a compact JSON: {"nodes": {id: [lat, lon, tags, meta]}, "ways": {...}, "relations": {...}}
meta = [version, timestamp, user, uid, changeset].
"""
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET


def meta(e):
    return [int(e.get("version", 0)), e.get("timestamp"), e.get("user"), e.get("uid"), e.get("changeset")]


def tags(e):
    return {t.get("k"): t.get("v") for t in e.findall("tag")}


def load(paths):
    nodes, ways, rels = {}, {}, {}
    for p in paths:
        root = ET.parse(p).getroot()
        for e in root:
            if e.tag == "node":
                nodes[e.get("id")] = [float(e.get("lat")), float(e.get("lon")), tags(e), meta(e)]
            elif e.tag == "way":
                ways[e.get("id")] = [[nd.get("ref") for nd in e.findall("nd")], tags(e), meta(e)]
            elif e.tag == "relation":
                rels[e.get("id")] = [[(m.get("type"), m.get("ref"), m.get("role")) for m in e.findall("member")],
                                     tags(e), meta(e)]
    return nodes, ways, rels


if __name__ == "__main__":
    d, out = sys.argv[1], sys.argv[2]
    paths = sorted(glob.glob(os.path.join(d, "map_*.osm"))) + sorted(glob.glob(os.path.join(d, "*_full.xml")))
    n, w, r = load(paths)
    with open(out, "w") as f:
        json.dump({"nodes": n, "ways": w, "relations": r}, f)
    print(len(n), "nodes", len(w), "ways", len(r), "relations")
