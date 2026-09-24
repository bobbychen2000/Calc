#!/usr/bin/env python3
"""Debug view of the livery-atlas part classification of a model: fuselage light grey, fin red, tailplane green,
nacelles blue, pylons yellow, wing tips magenta, gear doors cyan; everything else keeps its own texture.
Usage: python3 tools/liveries/partsview.py <atlased model.sfom> <out.png> [type]"""
import sys
import paint, preview
S = sys.argv
c = paint.Canvas(S[1], S[3] if len(S) > 3 else None, 1024)
for p, h in {'fus': '#EEEEEE', 'fin': '#FF0000', 'hstab': '#00FF00', 'eng': '#0000FF', 'pylon': '#FFFF00', 'tip': '#FF00FF', 'gdoor': '#00FFFF'}.items():
    c.paint((c.part == p).astype(float), h)
img = c.finish()
m, P = preview.load_for(S[1], S[3] if len(S) > 3 else None)
preview.sheet(m, P, ['side', '34', 'bottom', 'front'], img, 800, 380).save(S[2])
