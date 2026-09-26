#!/usr/bin/env python3
"""Recover a Boeing CAD 3-view whose DWG -> DXF conversion is incomplete (747-8: LibreDWG 0.13.3 dwg2dxf stops at the
BLOCK_HEADER table, "Invalid type 0x13, expected 0x31 BLOCK_HEADER", and writes a 40 KB DXF with no model-space entities,
which ezdxf rejects with "missing EOF tag"). `dwgread -O JSON` still decodes every entity of the file; this script writes
the drawing entities of that JSON dump (LINE, LWPOLYLINE with bulges, CIRCLE, ARC) into a new DXF in the same drawing
units, for tools/liveries/windows_ref.py. No geometry is changed; texts, dimensions and hatches are left out (windows_ref
ignores them anyway).

Usage:
  LD_LIBRARY_PATH=<libredwg>/lib <libredwg>/bin/dwgread -O JSON -o 7478p3vue.json refs/cache/boeing3v/7478p/7478p3vue.dwg
  python3 tools/liveries/dwg_json2dxf.py 7478p3vue.json refs/cache/boeing3v/7478p/7478p3vue_recovered.dxf
"""
import json, math, sys


def convert(src, dst):
    import ezdxf
    d = json.load(open(src))
    doc = ezdxf.new(); ms = doc.modelspace(); n = {}
    for o in d['OBJECTS']:
        e = o.get('entity')
        if e == 'LINE':
            ms.add_line(o['start'][:2], o['end'][:2])
        elif e == 'LWPOLYLINE':
            pts = [p[:2] for p in o['points']]; bl = o.get('bulges') or []
            closed = bool(o.get('flag', 0) & 1)
            if bl and any(bl): ms.add_lwpolyline([(p[0], p[1], 0, 0, b) for p, b in zip(pts, bl)], format='xyseb', close=closed)
            else: ms.add_lwpolyline(pts, close=closed)
        elif e == 'CIRCLE':
            ms.add_circle(o['center'][:2], o['radius'])
        elif e == 'ARC':
            ms.add_arc(o['center'][:2], o['radius'], math.degrees(o['start_angle']), math.degrees(o['end_angle']))
        else:
            continue
        n[e] = n.get(e, 0) + 1
    doc.saveas(dst)
    return n


if __name__ == '__main__':
    print(convert(sys.argv[1], sys.argv[2]))
