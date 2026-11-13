"""Extract ZSSS context features from an OSM API 0.6 XML download (ODbL data).

Usage: python3 -I osm_extract.py <relation_full.xml> <map.osm> <out.geojson>

Writes a GeoJSON FeatureCollection with: the aerodrome multipolygon (relation 21913346),
runway centrelines (aeroway=runway), railway / transport stations, waterways and water areas.
Prints a short summary (runway lengths / bearings on WGS-84 via pyproj.Geod).
OSM coordinates are WGS-84 (EPSG:4326); no GCJ-02 data is involved.
"""
import sys, json
import xml.etree.ElementTree as ET
from pyproj import Geod

G = Geod(ellps="WGS84")


def load(path):
    r = ET.parse(path).getroot()
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in r.findall("node")}
    ways, rels = {}, {}
    for w in r.findall("way"):
        ways[w.get("id")] = dict(nd=[x.get("ref") for x in w.findall("nd")],
                                 tags={t.get("k"): t.get("v") for t in w.findall("tag")},
                                 meta={k: w.get(k) for k in ("version", "timestamp")})
    for rel in r.findall("relation"):
        rels[rel.get("id")] = dict(members=[(m.get("type"), m.get("ref"), m.get("role")) for m in rel.findall("member")],
                                   tags={t.get("k"): t.get("v") for t in rel.findall("tag")},
                                   meta={k: rel.get(k) for k in ("version", "timestamp")})
    return nodes, ways, rels


def rings(way_ids, ways, nodes):
    """Join member ways into closed rings."""
    segs = [list(ways[w]["nd"]) for w in way_ids if w in ways]
    out = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        out.append([nodes[n] for n in cur if n in nodes])
    return out


def main():
    rel_path, map_path, out_path = sys.argv[1:4]
    n1, w1, r1 = load(rel_path)
    n2, w2, r2 = load(map_path)
    nodes = {**n2, **n1}
    ways = {**w2, **w1}
    feats = []
    rel = r1["21913346"]
    outer = [m[1] for m in rel["members"] if m[0] == "way" and m[2] == "outer"]
    rr = rings(outer, ways, nodes)
    feats.append(dict(type="Feature", properties=dict(kind="aerodrome", osm="relation/21913346", **{k: rel["tags"].get(k) for k in ("name", "name:en", "iata", "icao", "ele", "source")}, **rel["meta"]),
                      geometry=dict(type="MultiPolygon", coordinates=[[r] for r in rr])))
    area = sum(abs(G.polygon_area_perimeter([p[0] for p in r], [p[1] for p in r])[0]) for r in rr)
    print(f"aerodrome rings={len(rr)} area={area/1e6:.3f} km2 meta={rel['meta']}")
    for wid, w in ways.items():
        t = w["tags"]
        coords = [nodes[n] for n in w["nd"] if n in nodes]
        if len(coords) < 2:
            continue
        kind = None
        if t.get("aeroway") == "runway":
            kind = "runway"
            (lo0, la0), (lo1, la1) = coords[0], coords[-1]
            az, _, dist = G.inv(lo0, la0, lo1, la1)
            print(f"runway {t.get('ref')} way/{wid} v{w['meta']['version']} {w['meta']['timestamp']} nodes={len(coords)} "
                  f"len={dist:.1f} m az(true)={az % 360:.2f} width={t.get('width')} ends={coords[0]} {coords[-1]}")
        elif t.get("building") == "train_station" or t.get("railway") == "station" or t.get("public_transport") == "station":
            kind = "station"
        elif "waterway" in t:
            kind = "waterway"
        elif t.get("natural") == "water" or t.get("landuse") in ("reservoir", "basin"):
            kind = "water_area"
        elif t.get("aeroway") in ("terminal",):
            kind = "terminal"
        if not kind:
            continue
        closed = w["nd"][0] == w["nd"][-1] and len(coords) > 3
        geom = dict(type="Polygon", coordinates=[coords]) if closed and kind != "waterway" else dict(type="LineString", coordinates=coords)
        props = dict(kind=kind, osm=f"way/{wid}", **{k: v for k, v in t.items() if k in ("name", "name:en", "ref", "width", "waterway", "water", "railway", "station", "building", "public_transport", "aeroway", "surface")})
        feats.append(dict(type="Feature", properties=props, geometry=geom))
    with open(out_path, "w") as f:
        json.dump(dict(type="FeatureCollection", properties=dict(licence="ODbL 1.0, (c) OpenStreetMap contributors", source=[rel_path, map_path]), features=feats), f, ensure_ascii=False)
    from collections import Counter
    print(Counter(x["properties"]["kind"] for x in feats))
    for x in feats:
        if x["properties"]["kind"] in ("station", "terminal"):
            p = x["properties"]
            c = x["geometry"]["coordinates"]
            ring = c[0] if x["geometry"]["type"] == "Polygon" else c
            lo = sum(q[0] for q in ring) / len(ring)
            la = sum(q[1] for q in ring) / len(ring)
            print(p["kind"], p["osm"], p.get("name"), p.get("name:en"), f"centroid~{lo:.5f},{la:.5f}")


if __name__ == "__main__":
    main()
