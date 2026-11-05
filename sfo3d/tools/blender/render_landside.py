# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Cycles reference renders of the EXPORTED landside asset (data/buildings3d/landside.glb imported back into an empty scene)
for the visual QA against the 2-D sheets BL-02 / BL-03 and the reference photos (reference only, never textures):

    flock out/.heavy.lock python3 tools/blender/render_landside.py [--views gar_a,hyatt,superbay,l4,l1,l5,a2,overview]
                                                                   [--res 960] [--samples 48] [--glb ...] [--itb]

Orthographic elevations in the BL-03 frames, with the sheet lines drawn over the render (red; computed by
tools/buildings/draw_landside.py, not from the mesh) and the measured render silhouette:
  gar_a      Garage A SSE face looking NNW (u from the WSW end to the right): drum ring / deck placeholder, the nine level
             lines, body end Lb, core cylinder and rooftop box tops (BL-03 row 1)
  hyatt      Grand Hyatt east face looking WNW (SSW on the left): parapet, podium / colonnade tops, the l4 face fractions
             (podium 0.47, colonnade 0.02-0.10, framed bay 0.615-0.842, penthouse 0.518-0.692 / 0.615-0.742) (BL-03 row 2)
  superbay   Superbay WNW door face looking ESE (NNE on the left): spine 41.15, root 39.65, folded tip edge 27.0 / 28.5, the
             door head, 138-m roof (BL-03 row 4)
Perspectives approximating the reference photos (camera positions estimated, not surveyed):
  l4  Grand Hyatt from the airfield (east), long lens        l1  Garage A east portal from the guideway (photo l1)
  l5  RCC west wall + station tower from the north (l5)      a2  aerial from the ESE over the ITB at Garage G / Hyatt (a2)
  overview  oblique aerial over the whole landside group
--itb also imports data/buildings3d/itb.glb (context for a2). Sun + physical sky, AgX, OIDN; <= 960 px, <= 64 spp.
"""
import argparse
import json
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
import draw_data as D  # noqa: E402
import draw_landside as DL  # noqa: E402
from draw_lib import FT, hdg_vec  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'buildings3d')
REF = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'review_likeness')
GROUND_Y = 3.0
LB = D.LANDM['buildings']
T0 = time.time()
EXPOSURE = -4.0


def log(*a):
    print('[landside-render %6.1f s]' % (time.time() - T0), *a, flush=True)


def Wxz(x, z, h):
    return Vector((float(x), -float(z), float(h) + GROUND_Y))


def setup(glbs, threads, samples, lod=0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = threads
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass  # noqa: E701
    sc.cycles.max_bounces = 5; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
    sc.view_settings.view_transform = 'AgX'
    for g in glbs:
        bpy.ops.import_scene.gltf(filepath=g)
    for ob in list(bpy.data.objects):
        if ob.name.startswith('LOD') and ob.name[3:4].isdigit() and int(ob.name[3]) != lod:
            for c in ob.children_recursive: c.hide_render = True; c.hide_viewport = True
    bpy.ops.mesh.primitive_plane_add(size=9000, location=(-1200, 700, GROUND_Y - 0.02))
    gnd = bpy.context.object; gnd.name = 'ground'
    m = bpy.data.materials.new('ground'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.15, 0.15, 0.145, 1); b.inputs['Roughness'].default_value = 0.9
    gnd.data.materials.append(m)
    return sc


def sun_sky(az_deg, el_deg, exposure=None):
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'; sky.sun_disc = True
    sky.sun_elevation = math.radians(el_deg); sky.sun_rotation = math.radians(az_deg)
    sky.altitude = 10.0; sky.air_density = 1.0; sky.aerosol_density = 1.5; sky.ozone_density = 1.0
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sc.view_settings.exposure = EXPOSURE if exposure is None else exposure


def camera(name, loc, target, lens=None, ortho=None, res=(960, 540)):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens; cd.sensor_width = 36.0
    cd.sensor_fit = 'HORIZONTAL'; cd.clip_start = 1.0; cd.clip_end = 12000
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    return co


def render(path, transparent=False):
    sc = bpy.context.scene
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log(f'{os.path.basename(path)} {sc.render.resolution_x}x{sc.render.resolution_y} {sc.cycles.samples} spp in {time.time() - t:.1f} s')
    return path


def only(prefixes):
    """hide every imported building node except those whose name starts with one of the prefixes (+ the ground)."""
    root = bpy.data.objects.get('landside')
    if not root: return
    for b in root.children:
        vis = any(b.name.startswith(p) for p in prefixes)
        for c in b.children_recursive:
            if c.name.startswith('LOD') or c.type != 'EMPTY':
                if not vis: c.hide_render = True
    return


def elev(name, c, a, b, H_c, scale, res, face_dist=700.0):
    """orthographic camera looking along +b (from c - b * dist), image right = +a; returns px(u_along_a, h) mapper."""
    loc = Wxz(*(c - b * face_dist), H_c); tgt = Wxz(*c, H_c)
    co = camera(name, loc, tgt, ortho=scale, res=res)
    k = res[0] / scale

    def px(u, h):
        return (res[0] / 2 + u * k, res[1] / 2 - (h - H_c) * k)
    return co, px, k


def overlay(p_rgb, p_alpha, lines, name, px, k, u_range, top_fn=None, H_c=0.0):
    """sheet lines over the render + the silhouette (topmost opaque pixel) vs top_fn(u)."""
    from PIL import Image, ImageDraw
    im = Image.open(p_rgb).convert('RGB'); dr = ImageDraw.Draw(im)
    for pts, col, w in lines:
        dr.line([px(u, h) for u, h in pts], fill=col, width=w)
    out_p = os.path.join(OUT, f'landside_cmp_{name}.png'); im.save(out_p)
    res = None
    if top_fn is not None and p_alpha:
        A = np.array(Image.open(p_alpha))[..., 3].astype(float) / 255.0
        Hd, Wd = A.shape
        rows = []
        for col in range(Wd):
            u = (col + 0.5 - Wd / 2) / k
            if not (u_range[0] + 1 < u < u_range[1] - 1): continue
            r = np.where(A[:, col] > 0.5)[0]
            if not len(r): continue
            h = H_c + (Hd / 2 - (r[0] + 1 - A[r[0], col])) / k
            t = top_fn(u)
            if t is None: continue
            rows.append((u, h, t))
        R = np.array(rows)
        if len(R):
            d = R[:, 1] - R[:, 2]
            res = dict(n=len(R), px_m=round(1 / k, 3), max_abs_dev_m=round(float(np.abs(d).max()), 3), p95_abs_dev_m=round(float(np.percentile(np.abs(d), 95)), 3),
                       mean_dev_m=round(float(d.mean()), 3), stations=[dict(u=round(float(u), 1), render=round(float(h), 2), drawing=round(float(t), 2)) for u, h, t in R[::max(1, len(R) // 12)]])
    return out_p, res


def silhouette(path):
    gnd = bpy.data.objects['ground']; gnd.hide_render = True
    s = bpy.context.scene.cycles.samples; bpy.context.scene.cycles.samples = 4
    pa = render(path, transparent=True)
    bpy.context.scene.cycles.samples = s; gnd.hide_render = False
    return pa


# ------------------------------------------------------------------------------------------------ views
def view_gar_a(args):
    k = 'garage_a'; g = DL.GAR[k]; G = DL.ggeom(k)
    a, b, L, Lb, hd = G['a'], G['b'], G['L'], G['Lb'], float(g['drum'])
    c = G['c']
    sun_sky(200.0, 50.0)
    res = (960, 300); scale = 320.0; Hc = 22.0
    co, px0, kk = elev('cam_gar_a', c, a, b, Hc, scale, res)
    px = lambda u, h: px0(u - L / 2, h)
    p = render(os.path.join(OUT, 'landside_gar_a.png'))
    pa = silhouette(os.path.join(OUT, 'landside_gar_a_alpha.png'))
    lines = [([(0, hd), (Lb, hd)], (230, 40, 40), 1), ([(Lb, 0), (Lb, hd)], (230, 40, 40), 1)]
    for i in range(1, 9):
        lines.append(([(0, hd * i / 9), (Lb, hd * i / 9)], (255, 150, 0), 1))
    uc, R = G['uc'], G['R']; r = DL.GAR_CORE_D / 2
    lines.append(([(uc - r, hd + 4), (uc + r, hd + 4)], (230, 40, 40), 1))
    if G['box']:
        lines.append(([(G['box'][0], hd + 3.5), (G['box'][1], hd + 3.5)], (230, 40, 40), 1))
    import landside_airtrain as AT
    lines.append(([(0, AT.NET_LEVEL), (L, AT.NET_LEVEL)], (0, 160, 255), 1))
    lines.append(([(0, hd * 6 / 8), (Lb, hd * 6 / 8)], (200, 0, 200), 1))

    def top(u):
        if 2 < u < Lb - 2 and not (abs(u - uc) < r + 1) and not (G['box'] and G['box'][0] - 1 < u < G['box'][1] + 1):
            return hd
        return None
    cmp_p, chk = overlay(p, pa, lines, 'gar_a', px, kk, (-L / 2 + 0, -L / 2 + Lb), lambda u: top(u + L / 2), Hc)
    return dict(render=p, compare=cmp_p, silhouette_vs_sheet=chk)


def view_hyatt(args):
    k = 'grand_hyatt'; mr = LB[k]['footprint']['min_rect']
    ax = hdg_vec(mr['long_side_heading_deg']); east = np.array([-ax[1], ax[0]])
    east = np.array([ax[1], -ax[0]]) if np.array([ax[1], -ax[0]])[0] > 0 else -np.array([ax[1], -ax[0]])
    c = np.array(mr['centre']); W = mr['length_m']; p = DL.GH_P; H = 13.2 * p
    sun_sky(110.0, 40.0)
    res = (960, 520); scale = 130.0; Hc = 24.0
    co, px0, kk = elev('cam_hyatt', c, ax, -east, Hc, scale, res)
    px = lambda f, h: px0(f * W - W / 2, h)
    only(['grand_hyatt'])
    pr = render(os.path.join(OUT, 'landside_hyatt.png'))
    pa = silhouette(os.path.join(OUT, 'landside_hyatt_alpha.png'))
    hp, hc = DL.GH_POD * p, (DL.GH_POD + DL.GH_COL) * p
    red, org = (230, 40, 40), (255, 150, 0)
    lines = [([(0, H), (1, H)], red, 1), ([(0, hp), (0.47, hp)], red, 1), ([(0.47, 0), (0.47, hp)], red, 1),
             ([(0.02, hc), (0.10, hc)], org, 1), ([(0.02, hp), (0.02, hc)], org, 1), ([(0.10, hp), (0.10, hc)], org, 1),
             ([(0.615, 0), (0.615, H - p), (0.842, H - p), (0.842, 0)], org, 1),
             ([(0.518, H), (0.518, H + 1.4 * p), (0.692, H + 1.4 * p), (0.692, H)], red, 1),
             ([(0.615, H + 0.65 * p), (0.742, H + 0.65 * p), (0.742, H)], red, 1)]
    for fm in (-0.008, 0.027, 0.905, 0.961):
        lines.append(([(fm, H), (fm, H + 0.8 * p)], (0, 160, 255), 1))

    def top(fu):
        f = fu / W + 0.5
        if 0.03 < f < 0.50 or 0.76 < f < 0.89 or 0.97 < f < 0.99: return H
        return None
    cmp_p, chk = overlay(pr, pa, lines, 'hyatt', lambda f, h: px(f, h), kk, (-W / 2, W / 2), top, Hc)
    return dict(render=pr, compare=cmp_p, silhouette_vs_sheet=chk)


def view_superbay(args):
    k = 'superbay'; c = np.array(LB[k]['footprint']['min_rect']['centre'])
    sv, tv = hdg_vec(117.83), hdg_vec(27.83)
    hs = 135 * FT; root = hs - 1.5; ht = DL.SB_TIP
    sun_sky(285.0, 35.0)
    res = (960, 400); scale = 170.0; Hc = 22.0
    cc = c + sv * (-80.5)
    co, px0, kk = elev('cam_sb', cc, -tv, sv, Hc, scale, res)      # looking ESE (+sv), image right = SSW (-tv)
    px = lambda t, h: px0(-t, h)                                     # t (NNE +) -> image left
    only(['superbay'])
    pr = render(os.path.join(OUT, 'landside_superbay.png'))
    pa = silhouette(os.path.join(OUT, 'landside_superbay_alpha.png'))
    red, org = (230, 40, 40), (255, 150, 0)
    edge = [(-69 + 8.625 * i, ht + (DL.SB_FOLD if i % 2 else 0.0)) for i in range(17)]
    lines = [(edge, red, 1), ([(69, ht + DL.SB_FOLD), (69 - DL.SB_HIP['nne'], root), (-69 + DL.SB_HIP['ssw'], root), (-69, ht + DL.SB_FOLD)], org, 1),
             ([(-69, hs), (69, hs)], (0, 160, 255), 1), ([(-67.0, ht - DL.SB_DOOR_GAP), (67.0, ht - DL.SB_DOOR_GAP)], org, 1)]

    def top(u):
        t = -u
        if abs(t) < 69 - DL.SB_HIP['nne'] - 1: return hs
        return None
    cmp_p, chk = overlay(pr, pa, lines, 'superbay', px, kk, (-69, 69), top, Hc)
    return dict(render=pr, compare=cmp_p, silhouette_vs_sheet=chk)


def persp(name, cam_xz, cam_h, tgt_xz, tgt_h, lens, res, sun, photo=None):
    sun_sky(*sun)
    camera('cam_' + name, Wxz(*cam_xz, cam_h), Wxz(*tgt_xz, tgt_h), lens=lens, res=res)
    pr = render(os.path.join(OUT, f'landside_{name}.png'))
    cmp_p = side_by_side(pr, os.path.join(REF, photo + '.jpg'), f'landside_cmp_{name}.png') if photo else None
    return dict(render=pr, compare=cmp_p)


def view_l4(args):
    """Grand Hyatt east face from the airfield (photo l4 = 7391, long lens ~243 mm equivalent, from the east)."""
    mr = LB['grand_hyatt']['footprint']['min_rect']; c = np.array(mr['centre'])
    ax = hdg_vec(mr['long_side_heading_deg']); e = np.array([ax[1], -ax[0]]); e = e if e[0] > 0 else -e
    return persp('l4', c + e * 620 + ax * 10, 6.0, c + ax * 5, 22.0, 220.0, (960, 640), (160.0, 55.0), 'l4')


def view_l1(args):
    """Garage A east portal from the guideway walkway, looking west (photo l1)."""
    G = DL.ggeom('garage_a'); a, b, L, Lb = G['a'], G['b'], G['L'], G['Lb']
    import landside_airtrain as AT
    p0 = G['c'] + a * (Lb - L / 2 + 38) - b * 14.5
    return persp('l1', p0, AT.NET_LEVEL + 1.7, G['c'] + a * (Lb - L / 2 - 20) - b * 14.0, AT.NET_LEVEL + 6.0, 24.0, (960, 720), (150.0, 50.0), 'l1')


def view_l5(args):
    """RCC west wall and the station tower from the guideway north of the station, looking south (photo l5)."""
    import landside_airtrain as AT
    tk = AT.RCC_TOWER['world']
    return persp('l5', (tk[0] + 3.0, tk[1] - 75.0), AT.RCC_PLATFORM + 2.5, (tk[0] + 2.0, tk[1] + 10.0), AT.RCC_PLATFORM + 6.0, 26.0, (960, 720), (140.0, 55.0), 'l5')


def view_a2(args):
    """aerial from the ESE over the ITB at Garage G / Grand Hyatt (photo a2 direction)."""
    Gg = DL.ggeom('garage_g')
    tgt = Gg['c'] + np.array([20.0, 60.0])
    d = np.array([math.sin(math.radians(32.0)), -math.cos(math.radians(32.0))])     # camera NNE of the target, looking SSW [est.]
    return persp('a2', tgt + d * 1000.0, 420.0, tgt, 10.0, 62.0, (960, 640), (200.0, 55.0), 'a2')


def view_overview(args):
    return persp('overview', (-600.0, 900.0), 900.0, (-1500.0, -600.0), 0.0, 32.0, (960, 640), (200.0, 55.0), None)


def side_by_side(render_p, photo, out_name):
    from PIL import Image
    if not os.path.exists(photo): return None
    a = Image.open(render_p).convert('RGB'); b = Image.open(photo).convert('RGB')
    b = b.resize((a.width, int(b.height * a.width / b.width)))
    im = Image.new('RGB', (a.width, a.height + b.height + 6), (255, 255, 255))
    im.paste(b, (0, 0)); im.paste(a, (0, b.height + 6))
    p = os.path.join(OUT, out_name); im.save(p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(ROOT, 'data', 'buildings3d', 'landside.glb'))
    ap.add_argument('--views', default='gar_a,hyatt,superbay')
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--itb', action='store_true')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    glbs = [args.glb] + ([os.path.join(ROOT, 'data', 'buildings3d', 'itb.glb')] if args.itb else [])
    done = {}
    for v in args.views.split(','):
        setup(glbs, args.threads, args.samples, args.lod)      # fresh scene per view (views hide buildings)
        done[v] = globals()['view_' + v](args)
        log(v, json.dumps(done[v], default=str)[:600])
    pj = os.path.join(OUT, 'landside_render.json')
    old = json.load(open(pj)) if os.path.exists(pj) else {}
    old.update(done)
    json.dump(old, open(pj, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
