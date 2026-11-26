"""Print the EXIF tags that survived in the listing photos (lens / exposure data helps the camera fits)."""
import glob
import os
import sys

from PIL import ExifTags, Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in sorted(glob.glob(os.path.join(HERE, 'refs', 'cache', 'photos', '*.jpg'))):
    im = Image.open(f)
    ex = im.getexif()
    d = {ExifTags.TAGS.get(k, k): v for k, v in ex.items()}
    try:
        sub = ex.get_ifd(0x8769)
        d.update({ExifTags.TAGS.get(k, k): v for k, v in sub.items()})
    except Exception:
        pass
    d = {k: (v if not isinstance(v, bytes) else '<%d bytes>' % len(v)) for k, v in d.items() if k != 'ExifOffset'}
    print(os.path.basename(f), im.size, d)
