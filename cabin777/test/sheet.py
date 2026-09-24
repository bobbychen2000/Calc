import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]; out = sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 2
files = sorted(glob.glob(os.path.join(d, 'q*.png')))
ims = [Image.open(f).convert('RGB') for f in files]
w, h = ims[0].size
sc = 0.5
tw, th = int(w * sc), int(h * sc)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (tw * cols, th * rows), 'white')
dr = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * tw, (i // cols) * th
    sheet.paste(im.resize((tw, th)), (x, y))
    dr.rectangle([x, y, x + 120, y + 16], fill=(15, 20, 30)); dr.text((x + 4, y + 3), os.path.basename(f)[:-4], fill=(255, 255, 255))
sheet.save(out); print(sheet.size)
