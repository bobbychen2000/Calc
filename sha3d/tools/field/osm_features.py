"""List airport-relevant OSM features (ways/nodes/relations) with tags and a centroid.

usage: python3 -I tools/field/osm_features.py MAP.osm
Stdlib only; the .osm file is untrusted input. Prints TSV: type id lat lon key-tags name.
Selects: aeroway=* (except taxiway/runway/parking_position/holding_position/gate/taxilane),
building=hangar|control_tower|terminal|cargo, man_made=tower with tower:type=*,
and any feature whose name mentions 东航/东方航空/上海航空/春秋/吉祥/公务机/货运/机务/维修/塔台/航站楼/Hawker/Jet Aviation.
"""
import re
import sys
import xml.etree.ElementTree as ET

KEYS = re.compile(r"东航|东方航空|上海航空|春秋|吉祥|公务|货运|货站|机务|维修|塔台|航站楼|机库|Hawker|Jet Aviation|Eastern|Cargo|Hangar|FBO",
                  re.I)
SKIP_AEROWAY = {"taxiway", "runway", "parking_position", "holding_position", "gate", "taxilane",
                "stopway", "windsock", "navigationaid"}


def main(path):
    nodes = {}
    ways = []
    for ev, el in ET.iterparse(path, events=("end",)):
        if el.tag == "node":
            nodes[el.get("id")] = (float(el.get("lat")), float(el.get("lon")))
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            if tags:
                ways.append(("node", el.get("id"), [el.get("id")], tags))
            el.clear()
        elif el.tag == "way":
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            refs = [n.get("ref") for n in el.findall("nd")]
            ways.append(("way", el.get("id"), refs, tags))
            el.clear()
    for kind, oid, refs, tags in ways:
        name = " / ".join(v for k, v in tags.items() if k.startswith("name") or k in ("operator", "description"))
        aw = tags.get("aeroway", "")
        bld = tags.get("building", "")
        sel = (aw and aw not in SKIP_AEROWAY) or bld in ("hangar", "control_tower", "terminal", "cargo") \
            or tags.get("man_made") == "tower" or (name and KEYS.search(name))
        if not sel:
            continue
        pts = [nodes[r] for r in refs if r in nodes]
        if not pts:
            continue
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        keytags = ",".join(f"{k}={v}" for k, v in tags.items()
                           if k in ("aeroway", "building", "man_made", "tower:type", "height",
                                    "building:levels", "operator", "start_date", "ref"))
        print(f"{kind}\t{oid}\t{lat:.6f}\t{lon:.6f}\t{keytags}\t{name}")


if __name__ == "__main__":
    main(sys.argv[1])
