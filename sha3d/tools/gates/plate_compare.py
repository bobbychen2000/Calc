"""Side-by-side of the Phase 1 stands plate (T2 north + middle piers panel: Umbra SAR + OSM stands) and the gates
package's top-down render of the same area (docs/phase2/gates_push_t2_plate_frame.png, jobs/gates.mjs push set).
Both north up at about 1 px/m; the crop is matched by eye (the plate panel carries no georeference), so this is a
visual comparison, not a measurement.
Usage: python3 -I sha3d/tools/gates/plate_compare.py sha3d
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'sha3d')
plate = Image.open(root / 'docs/phase1/stands_overlay.jpg').convert('RGB')
rend = Image.open(root / 'docs/phase2/gates_push_t2_plate_frame.png').convert('RGB')
# plate: the "T2 north + middle piers" panel (top right; 100 m = ~97 px)
P = plate.crop((1303, 30, 1908, 632))
# render: 1280 px = 2 * 700 m * tan(25 deg) * 16/9 = 1160 m -> 1.10 px/m; scaled to the plate's ~0.97 px/m
R = rend.crop((330, 0, 1010, 720)); R = R.resize((round(R.width * 0.88), round(R.height * 0.88)), Image.LANCZOS)
W = P.width + R.width + 30; H = max(P.height, R.height) + 110
out = Image.new('RGB', (W, H), (20, 20, 22)); d = ImageDraw.Draw(out)
try:
    f = ImageFont.truetype('DejaVuSans.ttf', 15); fs = ImageFont.truetype('DejaVuSans.ttf', 12)
except OSError:
    f = fs = ImageFont.load_default()
d.text((10, 8), 'Phase 1 stands plate (T2 north + middle piers)', fill=(235, 235, 235), font=f)
d.text((P.width + 20, 8), 'Phase 2c render, same area (?debug=push)', fill=(235, 235, 235), font=f)
out.paste(P, (10, 34)); out.paste(R, (P.width + 20, 34))
y = 34 + max(P.height, R.height) + 10
d.text((10, y), 'Left: docs/phase1/stands_overlay.jpg (crop). Contains Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0, modified; '
       '(c) OpenStreetMap contributors (ODbL).', fill=(200, 200, 200), font=fs)
d.text((10, y + 18), 'Right: docs/phase2/gates_push_t2_plate_frame.png (crop, scaled to ~1 px/m). Both north up; crops matched by eye, '
       'not georeferenced.', fill=(200, 200, 200), font=fs)
d.text((10, y + 36), 'Plate: magenta = bridge to the L1 door of the class reference, white = fixed link. Render: magenta dashes = '
       'push-back path, cyan = lead-in, bridges at rest.', fill=(200, 200, 200), font=fs)
dst = root / 'docs/phase2/gates_compare_plate_t2.png'; out.save(dst); print(dst, out.size)
