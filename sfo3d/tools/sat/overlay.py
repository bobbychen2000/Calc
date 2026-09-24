import sys, json
from common import *
from refmap import render
from PIL import Image
U = open(SP + 'uniq.txt').read().split()
def overlay(name, sim=None, out=None, scale=0.5, crop=None):
    reg = json.load(open(SP + 'reg.json'))
    r = reg[name]; sim = sim or Sim(r['s'], r['th'], r['tx'], r['ty'])
    f = [u for u in U if name in u][0]
    bg = Image.open(f).convert('RGB')
    im = render(sim, bg.size[0], bg.size[1], bg=bg, labels=True, width=3)
    if crop: im = im.crop(crop)
    im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    im.save(out or SP + f'ov_{name}.png')
if __name__ == '__main__':
    overlay(sys.argv[1], scale=float(sys.argv[2]) if len(sys.argv) > 2 else 0.5)
