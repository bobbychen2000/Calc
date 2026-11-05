# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Cycles reference renders of the EXPORTED ITB asset (data/buildings3d/itb.glb, imported back into an empty scene), for the
visual QA against the 2-D sheets and the reference photos (reference only, never textures):

    python3 tools/blender/render_itb.py [--glb data/buildings3d/itb.glb] [--views west,i4,baa] [--res 960] [--samples 48]

Views (out/buildings3d/itb_<view>.png; comparison sheets itb_cmp_<view>.png, local only - they contain photo pixels):
  west   orthographic WEST (landside) elevation looking ENE, the BI-02 view 1 frame (u to the right, height up); the
         comparison overlays the BI-02 lines computed by tools/buildings/draw_itb.py (roof_line, chord, glass head, canopy,
         level 3, the column and hanger stations) on the render, and the silhouette of the render is measured against
         roof_line(u) (out/buildings3d/itb_render_check.json)
  i4     perspective from the landside roadways approximating photo i4 (DimiCalifornia 2005, public domain)
  a2g    photo a2 (Pi.1415926535 2025, CC BY-SA 4.0, "Aerial view of San Francisco International Airport station") with its
         camera SOLVED (review r1): a2 looks SSW over the Boarding Area G NNE face (Garage G and the BART / AirTrain station
         roof behind it, Garage A and the Grand Hyatt further back, the ITB north tip at the left edge) - not Boarding Area A
         as round 0 assumed. Camera from 11 image <-> world correspondences (BA-G roof edge / base at the bump-outs, bump-out
         edges, pod ends, ITB NW roof corner, Garage G east end, Grand Hyatt): out/buildings3d/itb_a2_camera.json
  baa    aerial from the east-south-east over the apron at Boarding Area A (BI-04 view 2 face). NO reference photo of
         BA-A is cached (a2 shows BA-G; a Commons search 2026-11-05 found none identifiable): render only
  bag    aerial from the north-north-east at Boarding Area G with the pod-3 end box (photo d2 direction; BI-04 view 1)
Lighting: a sun lamp + Hosek-Wilkie sky (sun from the WSW in the afternoon for the landside views, as in i1 / i4); AgX;
OIDN denoise. LOD0 only. Renders are small (<= 960 px, <= 64 spp) on the shared CPUs.
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
sys.path.insert(0, HERE)
import itb_geom as G  # noqa: E402

ROOT = G.ROOT
OUT = os.path.join(ROOT, 'out', 'buildings3d')
GROUND_Y = 3.0
REF = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'review_likeness')
T0 = time.time()


def log(*a):
    print('[itb-render %6.1f s]' % (time.time() - T0), *a, flush=True)


def W(u, v, h):
    """roof frame (u, v, height AGL) -> Blender world (after import the root sits at (OX, -OZ, GROUND_Y))."""
    x, y, z = G.Buv(u, v, h)
    return Vector((x + G.OX, y - G.OZ, z + GROUND_Y))


def Wxz(x, z, h):
    return Vector((x, -z, h + GROUND_Y))


def setup(glb, threads, samples, lod=0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'FIXED'; sc.render.threads = threads
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass  # noqa: E701
    sc.cycles.max_bounces = 6; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 2
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast' if 'AgX - Medium High Contrast' in [l.name for l in []] else 'None'
    bpy.ops.import_scene.gltf(filepath=glb)
    for e in ('LOD0', 'LOD1', 'LOD2'):
        ob = bpy.data.objects.get(e)
        if ob and e != 'LOD%d' % lod:
            for c in ob.children_recursive: c.hide_render = True; c.hide_viewport = True
    # ground: neutral pavement grey (roads / apron), not an image
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(G.OX, -G.OZ, GROUND_Y - 0.01))
    gnd = bpy.context.object; gnd.name = 'ground'
    m = bpy.data.materials.new('ground'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.16, 0.16, 0.155, 1); b.inputs['Roughness'].default_value = 0.9
    gnd.data.materials.append(m)
    return sc


def sun_sky(az_deg, el_deg, exposure=None):
    """physical sky with its sun disc (Cycles 'MULTIPLE_SCATTERING' = Nishita-type model; sun_rotation measured clockwise
    from north, checked with an equirectangular probe); no extra lamp."""
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    w = sc.world or bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'; sky.sun_disc = True
    sky.sun_elevation = math.radians(el_deg); sky.sun_rotation = math.radians(az_deg)
    sky.altitude = 10.0; sky.air_density = 1.0; sky.aerosol_density = 1.5; sky.ozone_density = 1.0
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 1.0
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sc.view_settings.exposure = EXPOSURE if exposure is None else exposure


EXPOSURE = -4.0


def camera(name, loc, target, lens=None, ortho=None, res=(960, 540)):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens; cd.sensor_width = 36.0
    cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start = 1.0; cd.clip_end = 8000
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


# ------------------------------------------------------------------------------------------------ views
WEST_SCALE, WEST_RES, WEST_HC = 272.0, (960, 288), 26.0


def view_west(args):
    """orthographic west elevation; u to the right (looking ENE), same as BI-02 V1."""
    sun_sky(250.0, 38.0)
    loc = W(0, -600, WEST_HC); tgt = W(0, 0, WEST_HC)
    camera('cam_west', loc, tgt, ortho=WEST_SCALE, res=WEST_RES)
    p = render(os.path.join(OUT, 'itb_west.png'))
    # silhouette pass (alpha): no ground
    gnd = bpy.data.objects['ground']; gnd.hide_render = True
    s = bpy.context.scene.cycles.samples; bpy.context.scene.cycles.samples = 4
    pa = render(os.path.join(OUT, 'itb_west_alpha.png'), transparent=True)
    bpy.context.scene.cycles.samples = s; gnd.hide_render = False
    return p, pa


def view_i4(args):
    """perspective from the landside roadways (photo i4: frontal, elevated, long lens; the 252.9-m roof spans ~88 % of the
    frame width; camera position estimated, not surveyed)."""
    sun_sky(255.0, 32.0)
    loc = W(4.0, -430.0, 20.0); tgt = W(4.0, 0.0, 24.0)
    camera('cam_i4', loc, tgt, lens=58.0, res=(960, 487))
    return render(os.path.join(OUT, 'itb_i4.png')),


def view_i3(args):
    """close-up from the departures curb island looking SSE along the facade (photo i3, Elizabeth K. Joseph 2017,
    CC BY 2.0; camera estimated): columns with their fans, the exposed truss, soffit outriggers, canopy and hangers.
    Review r2: lit as in the photo - the west facade in shade (no column shadows on the glass, soft shadows on the sidewalk:
    sun behind the building, az 100 / el 35 [est.]); round 1 lit it with a WSW sun, so the frit could not be compared."""
    sun_sky(100.0, 35.0)
    loc = W(-95.0, -46.0, G.L3 + 1.7); tgt = W(-10.0, -24.0, 26.0)
    camera('cam_i3', loc, tgt, lens=24.0, res=(960, 540))
    return render(os.path.join(OUT, 'itb_i3.png')),


def view_baa_cam():
    P = G.PIERS['A']; c = np.array(P['centre_xz']); t = np.array(P['t_axis']); s = np.array(P['s_axis'])
    cam = c + t * 240 - s * 70
    return camera('cam_baa', Wxz(cam[0], cam[1], 95.0), Wxz(c[0] - s[0] * 60, c[1] - s[1] * 60, 14.0), lens=45.0, res=(960, 600))


def view_baa(args):
    """aerial over the apron ESE of Boarding Area A, looking WNW at its apron face and pods (no reference photo of BA-A)."""
    sun_sky(200.0, 55.0)
    view_baa_cam()
    return render(os.path.join(OUT, 'itb_baa.png')),


# photo a2 camera (1920 x 1280) from tools/blender/itb_a2_solve.py (review r1, 2026-11-05: plan bearings of 5 features, then a
# soft-L1 fit on 10 picks; residuals <= ~20 px, the pod ends are the loosest picks; the ITB NW roof corner and the Garage G
# east end, not used, land within 25 / 40 px). x, z (south), h in the app frame; az from north clockwise; el; roll; f px.
A2_CAM = dict(x=-1059.7, z=-614.2, h=163.4, az=203.22, el=-8.51, roll=1.03, f_px=6780.0, w=1920, h_px=1280)


def a2g_cam():
    from mathutils import Quaternion
    c = A2_CAM; a, e = math.radians(c['az']), math.radians(c['el'])
    loc = Wxz(c['x'], c['z'], c['h'])
    fwd = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    co = camera('cam_a2g', loc, loc + fwd * 1000.0, lens=c['f_px'] / c['w'] * 36.0, res=(960, 640))
    co.rotation_mode = 'QUATERNION'
    co.rotation_quaternion = co.rotation_euler.to_quaternion() @ Quaternion((0.0, 0.0, 1.0), math.radians(c['roll']))
    return co


def view_a2g(args):
    """photo a2 view (solved camera): the BA-G NNE face, its gate-room curtain walls, low bridge-head boxes and pods."""
    sun_sky(215.0, 50.0)      # a2: overcast-bright, soft shadows falling towards the camera side (sun behind the pier) [est.]
    co = a2g_cam()
    # projection check of the photo picks (pixel coordinates of a2 at 1920 x 1280)
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    P = G.PIERS['G']; cc = np.array(P['centre_xz']); sa = np.array(P['s_axis']); ta = np.array(P['t_axis'])
    picks = [((-69.6, -0.7, 17.0), (372, 864)), ((73.2, -0.7, 17.0), (1593, 923)), ((-69.6, -0.7, 0.0), (372, 1012)),
             ((-53.8, -9.4, 6.5), (507, 955)), ((88.9, -9.4, 6.5), (1735, 1003))]
    err = []
    for (s_, t_, h_), (px, py) in picks:
        q = cc + sa * s_ + ta * t_
        v = world_to_camera_view(bpy.context.scene, co, Wxz(q[0], q[1], h_))
        X, Y = v.x * 1920, (1 - v.y) * 1280
        err.append(math.hypot(X - px, Y - py))
        log('a2 pick s %.1f t %.1f h %.1f: photo (%d, %d) render (%.0f, %.0f)' % (s_, t_, h_, px, py, X, Y))
    log('a2 picks: mean error %.1f px (1920 px frame)' % (sum(err) / len(err)))
    return render(os.path.join(OUT, 'itb_a2g.png')),


def view_plan(args):
    """orthographic roof plan of the hall, north up (BI-01 view 2 frame, rotated north-up)."""
    sun_sky(190.0, 72.4)          # NAIP 2024-05-20 local noon: sun az ~187, el 72.4 (spec naip.sun)
    c = W(0, 0, 0)
    co = camera('cam_plan', Vector((c.x, c.y, 400.0)), Vector((c.x, c.y, 0.0)), ortho=300.0, res=(720, 960))
    co.rotation_euler = (0.0, 0.0, 0.0)           # looking down, image up = north
    return render(os.path.join(OUT, 'itb_plan.png')),


def bag_cam():
    P = G.PIERS['G']; c = np.array(P['centre_xz']); t = np.array(P['t_axis']); s = np.array(P['s_axis'])
    bx = np.mean(np.asarray(G.POD['G3-box']['ring_true_xz']), 0)
    cam = bx - t * 260 + s * 40       # t_axis of G points SSW, the apron face looked at is NNE: camera on -t
    return camera('cam_bag', Wxz(cam[0], cam[1], 95.0), Wxz(bx[0] - s[0] * 90, bx[1] - s[1] * 90, 15.0), lens=40.0, res=(960, 600))


def view_bag(args):
    sun_sky(200.0, 55.0)
    bag_cam()
    return render(os.path.join(OUT, 'itb_bag.png')),


def view_bar(args):
    """review r2: the ITB core north bar as an elevated connector over the domestic departures viaduct and the at-grade roads,
    seen from the ESE at 25 m, with the integration group's roadways.glb (LOD0) imported as context when it exists."""
    rw = os.path.join(ROOT, 'data', 'buildings3d', 'roadways.glb')
    if os.path.exists(rw) and not bpy.data.objects.get('roadways_ctx'):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=rw)
        new_objs = [o for o in bpy.data.objects if o not in before]
        for o in new_objs:
            if o.name.startswith(('LOD1', 'LOD2')):
                for c in o.children_recursive: c.hide_render = True
        m = bpy.data.objects.new('roadways_ctx', None); bpy.context.scene.collection.objects.link(m)
    sun_sky(220.0, 45.0)
    camera('cam_bar', Wxz(-1022.0, 262.0, 26.0), Wxz(-1100.0, 190.0, 8.0), lens=30.0, res=(960, 600))
    return render(os.path.join(OUT, 'itb_bar.png')),


def view_curb(args):
    """review r2: the departures curb from the roadway side at eye height on the deck (L3 - 0.15 + 1.6): kerb, bollards, canopy
    posts on the sidewalk, wall-head brackets and the truss above (no photo match; i3 is the reference for the furniture)."""
    sun_sky(240.0, 40.0)
    camera('cam_curb', W(-40.0, G.KERB_V - 9.0, G.L3 + 1.45), W(-10.0, G.KERB_V + 2.0, G.L3 + 6.0), lens=24.0, res=(960, 540))
    return render(os.path.join(OUT, 'itb_curb.png')),


# ------------------------------------------------------------------------------------------------ comparisons
def west_overlay(p_rgb, p_alpha):
    """BI-02 V1 lines on the orthographic render + the measured silhouette vs roof_line(u)."""
    from PIL import Image, ImageDraw
    I = G.I
    im = Image.open(p_rgb).convert('RGB'); Wd, Hd = im.size
    k = Wd / WEST_SCALE

    def px(u, h):
        return (Wd / 2 + u * k, Hd / 2 - (h - WEST_HC) * k)
    dr = ImageDraw.Draw(im)
    us = np.linspace(-G.HL, G.HL, 600)
    dr.line([px(u, I.roof_line(u)) for u in us], fill=(230, 40, 40), width=1)
    dr.line([px(u, I.chord(u)) for u in us], fill=(255, 150, 0), width=1)
    for h, col in ((I.L3, (255, 0, 255)), (I.CANOPY, (0, 200, 255)), (I.WH, (0, 160, 0))):
        dr.line([px(-I.HALL_HL, h), px(I.HALL_HL, h)], fill=col, width=1)
    for cu in I.COL_U:
        for s in (-1, 1):
            dr.line([px(s * cu, I.L3), px(s * cu, I.L3 - 3)], fill=(0, 0, 255), width=2)
    for uh in I.HANGER_U:
        dr.line([px(uh, I.L3 - 1), px(uh, I.L3 - 2.5)], fill=(0, 120, 255), width=1)
    im.save(os.path.join(OUT, 'itb_cmp_west.png'))
    # silhouette: topmost pixel with alpha > 0.5 per column, converted to height, against roof_line
    A = np.array(Image.open(p_alpha))[..., 3].astype(float) / 255.0
    res = []
    for col in range(Wd):
        u = (col + 0.5 - Wd / 2) / k
        if abs(u) > G.HL - 0.5: continue
        rows = np.where(A[:, col] > 0.5)[0]
        if not len(rows): continue
        r = rows[0]
        # sub-pixel: alpha of the first row
        h = WEST_HC + (Hd / 2 - (r + 1 - A[r, col])) / k
        res.append((u, h, float(I.roof_line(u))))
    R = np.array(res)
    d = R[:, 1] - R[:, 2]
    wing = np.abs(R[:, 0]) > I.UN + 1
    out = dict(px_per_m=round(k, 3), n=len(R), wing_max_abs_dev_m=round(float(np.abs(d[wing]).max()), 3),
               wing_mean_dev_m=round(float(d[wing].mean()), 3), centre_max_abs_dev_m=round(float(np.abs(d[~wing]).max()), 3),
               note='silhouette = topmost opaque pixel of the orthographic west render (LOD0, alpha pass) vs BI-02 roof_line(u); '
                    'resolution 1 px = %.2f m; in the centre the lens glass / arch form the top' % (1 / k),
               stations=[dict(u=round(float(u), 1), render=round(float(h), 2), drawing=round(float(r), 2)) for u, h, r in R[::40]])
    json.dump(out, open(os.path.join(OUT, 'itb_render_check.json'), 'w'), indent=1)
    log('west silhouette vs roof_line:', {k_: out[k_] for k_ in ('wing_max_abs_dev_m', 'wing_mean_dev_m', 'centre_max_abs_dev_m')})
    return out


def side_by_side(render_p, photo, out_name, crop=None):
    from PIL import Image
    if not os.path.exists(photo): return None
    a = Image.open(render_p).convert('RGB'); b = Image.open(photo).convert('RGB')
    if crop: b = b.crop(crop)
    b = b.resize((a.width, int(b.height * a.width / b.width)))
    im = Image.new('RGB', (a.width, a.height + b.height + 6), (255, 255, 255))
    im.paste(b, (0, 0)); im.paste(a, (0, b.height + 6))
    p = os.path.join(OUT, out_name); im.save(p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(ROOT, 'data', 'buildings3d', 'itb.glb'))
    ap.add_argument('--views', default='west,i4,baa')
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--suffix', default='')
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    setup(args.glb, args.threads, args.samples, args.lod)
    if args.suffix:
        global render
        _r = render
        render = lambda path, transparent=False: _r(path.replace('.png', args.suffix + '.png'), transparent)  # noqa: E731
    done = {}
    for v in args.views.split(','):
        r = globals()['view_' + v](args)
        done[v] = r
        if v == 'west':
            done['west_check'] = west_overlay(*r)
        elif v == 'i4':
            side_by_side(r[0], os.path.join(REF, 'i4.jpg'), 'itb_cmp_i4.png')
        elif v == 'i3':
            side_by_side(r[0], os.path.join(REF, 'i3.jpg'), 'itb_cmp_i3.png')
        elif v == 'a2g':
            side_by_side(r[0], os.path.join(REF, 'a2.jpg'), 'itb_cmp_a2g.png')
        elif v == 'bag':
            side_by_side(r[0], os.path.join(REF, 'd2.jpg'), 'itb_cmp_bag.png')
    json.dump({k: v for k, v in done.items()}, open(os.path.join(OUT, 'itb_render.json'), 'w'), indent=1, default=str)
    if os.path.abspath(args.glb) == os.path.abspath(os.path.join(ROOT, 'data', 'buildings3d', 'itb.glb')):
        import build_itb_manifest_merge as MM
        MM.add_renders(done, args)


if __name__ == '__main__':
    main()
