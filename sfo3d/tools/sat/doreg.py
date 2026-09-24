import sys, json
from manual import *
from register import refine2
from overlay import overlay
def run(name, th, s, wpt, ipt, bottom=2200, crop=None, fix_th=True, truncs=(16, 8, 4)):
    sim0 = sim_from(th, s, wpt, ipt)
    sim, c = refine2(name, sim0, bottom, fix_th=fix_th, truncs=truncs)
    save(name, sim, c, f'init th={th} s={s} w={wpt} i={ipt}')
    print(name, 's', round(sim.s, 4), 'th', round(sim.th, 3), 'cost', round(c, 4))
    overlay(name, out=SP + f'ov_{name}.png', scale=0.5)
    if crop: overlay(name, out=SP + f'ovc_{name}.png', scale=1.0, crop=crop)
if __name__ == '__main__':
    a = sys.argv
    run(a[1], float(a[2]), float(a[3]), (float(a[4]), float(a[5])), (float(a[6]), float(a[7])), int(a[8]) if len(a) > 8 else 2200)
