"""List OSM objects in a cached .osm extract whose tags the PRC Public Map Content Specification 2023 (items 20-21)
would bar from a public map of China (military landuse/usage, military=*, etc.). Read-only; stdlib only.
usage: python3 -I tools/law/osm_sensitive.py FILE.osm
Prints way/node id, tags, centroid and distance from the AIP ARP of ZSSS (N31 11.8 E121 20.1, aip.md fact 8)."""
import math, sys, xml.etree.ElementTree as ET
ARP = (31 + 11.8 / 60, 121 + 20.1 / 60)
root = ET.parse(sys.argv[1]).getroot()
nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.iter("node") if n.get("lat")}
def sens(tags):
    return (tags.get("landuse") == "military" or "military" in tags or tags.get("usage") == "military"
            or tags.get("aeroway") == "military" or tags.get("operator:type") == "military")
def dist(a, b):
    k = 111320.0
    return math.hypot((a[0] - b[0]) * k, (a[1] - b[1]) * k * math.cos(math.radians(a[0])))
for el in root:
    if el.tag not in ("node", "way", "relation"):
        continue
    tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
    if not sens(tags):
        continue
    pts = [nodes[nd.get("ref")] for nd in el.findall("nd") if nd.get("ref") in nodes] if el.tag == "way" else \
          ([nodes[el.get("id")]] if el.tag == "node" else [])
    c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
    d = f"{dist(c, ARP)/1000:.2f} km from ARP" if c else "no geometry"
    print(el.tag, el.get("id"), el.get("timestamp"), {k: v for k, v in tags.items() if k in
          ("name", "landuse", "military", "usage", "railway", "service", "operator")},
          f"centroid {c[0]:.4f},{c[1]:.4f}" if c else "", d)
