# SPDX-License-Identifier: GPL-3.0-or-later
# (imports bpy: Blender's licence asks scripts that use its API to be GPL-compatible if published, docs/research/engine.md 7.3)
"""Cycles reference renders of the EXPORTED domestic asset (data/buildings3d/domestic.glb or the WIP build, imported back
into an empty scene), for the visual QA against the 2-D sheets BD-01..03 and the reference photos (reference only, never
textures):

    flock out/.heavy.lock python3 tools/blender/render_domestic.py [--glb ...] [--views a1,d1,bab,plan] [--res 960] [--samples 48]

Views (out/buildings3d/domestic_<view>.png; comparison sheets domestic_cmp_<view>.png stay local: they hold photo pixels):
  a1    perspective approximating photo a1 (aerial from a departing flight, Sept 2025, CC BY-SA 4.0): BA-D head on the left,
        the tower behind, BA-E with its raised PV roof and glazed end wall on the right. Camera solved from three imaged
        points (tower cab rim, BA-D north drum top, BA-E end-wall top) at an assumed 60 m altitude: world (-529, 60, -384),
        heading 204 deg, pitch -4.1 deg, 36.5 mm on 36 mm [inf: estimated, not surveyed]
  d1    T1 Center landside face from the AirTrain / garage side (photo d1, Famartin 2025-08-12, CC BY-SA 4.0; BD-03 view 1):
        the west run with the curb canopy, the two-tier green fritted wall and the sign [camera estimated]
  bab   orthographic Boarding Area B cross-section, looking NNE along the pier axis (+t) from beyond its tip, far clip at
        t = -946 (the straight pier only): the BD-02 view 1 frame (s to the right, height up). The comparison draws the BD-02
        lines (outer roof edges s -383.73 / -438.04 at 13.14 m, raised band s -391.0 / -423.4 at 19.04 m) and the
        silhouette of the render is measured against them (out/buildings3d/domestic_render_check.json)
  plan  orthographic roof plan, north up (BD-01 frame), LOD0
Lighting: Nishita-type sky with its sun disc (Cycles MULTIPLE_SCATTERING), AgX, OIDN. Renders are small (<= 960 px,
<= 64 spp) on the shared CPUs.
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
sys.path.insert(0, os.path.join(ROOT, 'tools', 'buildings'))
from draw_lib import st2w  # noqa: E402

OUT = os.path.join(ROOT, 'out', 'buildings3d')
GROUND_Y = 3.0
REF = os.path.join(ROOT, 'refs', 'cache', 'buildings', 'review_likeness')
OX, OZ = -896.5, 336.5           # dom_geom.OX / OZ (asset root)
T0 = time.time()
EXPOSURE = -4.0
# BD-02 view 1 (BA-B typical section) [draw_domestic.bab_band / BAB_OUTER_S, spec bab.h_roof / bab.h_roof_central]
BAB = dict(outer=(-383.73, -438.04), band=(-391.0, -423.4), h_outer=13.14, h_band=19.04, t_far=-946.0, t_cam=-1700.0)


def log(*a):
    print('[dom-render %6.1f s]' % (time.time() - T0), *a, flush=True)


def Wxz(x, z, h):
    """app world (x east, z south, height above grade) -> Blender world after the glTF import (root at (OX, -OZ, GROUND_Y))."""
    return Vector((x, -z, h + GROUND_Y))


def setup(glb, threads, samples, lod=0, context=()):
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
    bpy.ops.import_scene.gltf(filepath=glb)
    for e in ('LOD0', 'LOD1', 'LOD2'):
        ob = bpy.data.objects.get(e)
        if ob and e != 'LOD%d' % lod:
            for c in ob.children_recursive: c.hide_render = True; c.hide_viewport = True
    if context:
        # neighbouring assets for orientation in the photo comparisons (their LOD0 only): the 2016 tower and the ITB
        for f in context:
            if not os.path.exists(f): continue
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=f)
            new = [o for o in bpy.data.objects if o not in before]
            for o in new:
                if o.name.split('.')[0] in ('LOD1', 'LOD2'):
                    for c in o.children_recursive: c.hide_render = True; c.hide_viewport = True
    # ground: neutral apron grey (not an image)
    bpy.ops.mesh.primitive_plane_add(size=8000, location=(OX, -OZ, GROUND_Y - 0.01))
    gnd = bpy.context.object; gnd.name = 'ground'
    m = bpy.data.materials.new('ground'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.16, 0.16, 0.155, 1); b.inputs['Roughness'].default_value = 0.9
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


def camera(name, loc, target, lens=None, ortho=None, res=(960, 540), clip=(1.0, 9000.0)):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens; cd.sensor_width = 36.0
    cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start, cd.clip_end = clip
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


def heading_target(cam, yaw, pitch, dist=1000.0):
    """target point at heading yaw (deg from north, clockwise), pitched down by pitch (deg) from a world camera (x, h, z)."""
    x, h, z = cam
    a, p = math.radians(yaw), math.radians(pitch)
    return (x + dist * math.sin(a) * math.cos(p), h - dist * math.sin(p), z - dist * math.cos(a) * math.cos(p))


# ------------------------------------------------------------------------------------------------ views
def view_a1(args):
    sun_sky(205.0, 48.0)
    cam = (-529.3, 60.0, -384.2)
    tx, th, tz = heading_target(cam, 203.8, 4.1)
    camera('cam_a1', Wxz(cam[0], cam[2], cam[1]), Wxz(tx, tz, th), lens=36.5, res=(args.res, int(args.res * 2 / 3)))
    return render(os.path.join(OUT, 'domestic_a1%s.png' % args.suffix)),


def view_d1(args):
    sun_sky(200.0, 55.0)
    # facade of the west run (longest landside edge -940.4,463.5 -> -978.8,455.3), seen from ~68 m in front, ~20 m up
    c = np.array([-959.6, 459.4]); d = np.array([-38.4, -8.2]); d /= np.hypot(*d)
    n = np.array([-d[1], d[0]])
    if n[1] > 0: n = -n                               # towards the garage (north)
    cam = c + n * 68.0 + d * -6.0
    camera('cam_d1', Wxz(cam[0], cam[1], 21.0), Wxz(c[0] - d[0] * 6.0, c[1] - d[1] * 6.0, 11.0), lens=50.0,
           res=(args.res, int(args.res * 0.75)))
    return render(os.path.join(OUT, 'domestic_d1%s.png' % args.suffix)),


BAB_SCALE, BAB_HC = 96.0, 12.0


def view_bab(args):
    """orthographic section along BA-B, s to the right (looking +t = NNE), far clip at t_far."""
    sun_sky(117.83 + 180 - 40, 40.0)                       # light from behind-left: faces readable
    sc_ = 0.5 * (BAB['outer'][0] + BAB['outer'][1])
    x0, z0 = st2w(sc_, BAB['t_cam']); x1, z1 = st2w(sc_, BAB['t_far'])
    dist = BAB['t_far'] - BAB['t_cam']
    res = (args.res, int(args.res * 0.3125))
    camera('cam_bab', Wxz(x0, z0, BAB_HC), Wxz(x1, z1, BAB_HC), ortho=BAB_SCALE, res=res, clip=(1.0, dist))
    p = render(os.path.join(OUT, 'domestic_bab%s.png' % args.suffix))
    gnd = bpy.data.objects['ground']; gnd.hide_render = True
    s = bpy.context.scene.cycles.samples; bpy.context.scene.cycles.samples = 4
    pa = render(os.path.join(OUT, 'domestic_bab_alpha%s.png' % args.suffix), transparent=True)
    bpy.context.scene.cycles.samples = s; gnd.hide_render = False
    return p, pa


def view_bclose(args):
    """close aerial over the middle of BA-B from the ESE (raised band, wells, PV, bridge doors) - for the AO / back-face QA."""
    sun_sky(205.0, 50.0)
    x0, z0 = st2w(-300.0, -1150.0); x1, z1 = st2w(-405.0, -1100.0)
    camera('cam_bclose', Wxz(x0, z0, 70.0), Wxz(x1, z1, 8.0), lens=35.0, res=(args.res, int(args.res * 0.5625)))
    return render(os.path.join(OUT, 'domestic_bclose%s.png' % args.suffix)),


def view_eclose(args):
    """close aerial at the BA-E tip from the NE (raised PV plate, tapered edge, glazed end wall) - photo a1 detail."""
    sun_sky(205.0, 50.0)
    camera('cam_eclose', Wxz(-640.0, -190.0, 75.0), Wxz(-780.0, -40.0, 8.0), lens=35.0, res=(args.res, int(args.res * 0.5625)))
    return render(os.path.join(OUT, 'domestic_eclose%s.png' % args.suffix)),


def qa_override(mode):
    """AO view (every material shows its baked occlusion; detail members without AO pink) or back-face view (front grey, BACK
    faces red: the asset is single-sided, so a red pixel is a face wound inwards or a hole showing an inner back face)."""
    for m in bpy.data.materials:
        if not m.use_nodes or m.name == 'ground': continue
        nt = m.node_tree
        img = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith('dom_ao')), None)
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if out is None: continue
        if mode == 'backface':
            geo = nt.nodes.new('ShaderNodeNewGeometry'); mix = nt.nodes.new('ShaderNodeMixShader')
            e1 = nt.nodes.new('ShaderNodeEmission'); e1.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
            e2 = nt.nodes.new('ShaderNodeEmission'); e2.inputs['Color'].default_value = (1, 0, 0, 1)
            nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac']); nt.links.new(e1.outputs[0], mix.inputs[1])
            nt.links.new(e2.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
        else:
            em = nt.nodes.new('ShaderNodeEmission')
            if img is not None: nt.links.new(img.outputs['Color'], em.inputs['Color'])
            else: em.inputs['Color'].default_value = (1.0, 0.25, 0.25, 1)
            nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'
    gnd = bpy.data.objects.get('ground')
    if gnd is not None: gnd.hide_render = True


def view_plan(args):
    sun_sky(187.0, 72.4)          # NAIP 2024-05-20 local noon: sun az ~187, el 72.4 (as the ITB plan)
    c = Wxz(OX, OZ, 0)
    co = camera('cam_plan', Vector((c.x, c.y, 600.0)), Vector((c.x, c.y, 0.0)), ortho=1400.0, res=(args.res, args.res))
    co.rotation_euler = (0.0, 0.0, 0.0)
    return render(os.path.join(OUT, 'domestic_plan%s.png' % args.suffix)),


# ------------------------------------------------------------------------------------------------ comparisons
def bab_overlay(p_rgb, p_alpha, suffix=''):
    """BD-02 view 1 lines on the orthographic section + the measured silhouette (topmost opaque pixel per column)."""
    from PIL import Image, ImageDraw
    im = Image.open(p_rgb).convert('RGB'); Wd, Hd = im.size
    k = Wd / BAB_SCALE
    sc_ = 0.5 * (BAB['outer'][0] + BAB['outer'][1])

    def px(s, h):
        return (Wd / 2 + (s - sc_) * k, Hd / 2 - (h - BAB_HC) * k)
    dr = ImageDraw.Draw(im)
    o0, o1 = BAB['outer']; b0, b1 = BAB['band']
    red, blue = (230, 40, 40), (0, 120, 255)
    dr.line([px(o1, 0), px(o1, BAB['h_outer']), px(b1, BAB['h_outer']), px(b1, BAB['h_band']), px(b0, BAB['h_band']),
             px(b0, BAB['h_outer']), px(o0, BAB['h_outer']), px(o0, 0)], fill=red, width=1)
    dr.line([px(o1 - 5, 0), px(o0 + 5, 0)], fill=blue, width=1)
    im.save(os.path.join(OUT, 'domestic_cmp_bab%s.png' % suffix))
    A = np.array(Image.open(p_alpha))[..., 3].astype(float) / 255.0
    prof = []
    for col in range(Wd):
        s = sc_ + (col + 0.5 - Wd / 2) / k
        rows = np.where(A[:, col] > 0.5)[0]
        if not len(rows): continue
        r = rows[0]
        h = BAB_HC + (Hd / 2 - (r + 1 - A[r, col])) / k
        prof.append((s, h))
    P = np.array(prof)
    hi = P[P[:, 1] > 0.5 * (BAB['h_outer'] + BAB['h_band'])]
    lo = P[P[:, 1] > BAB['h_outer'] - 2.0]           # above the elevated walkways (10.5 m) beside the pier
    meas = dict(band_wnw_s=float(hi[:, 0].min()), band_ese_s=float(hi[:, 0].max()), outer_wnw_s=float(lo[:, 0].min()), outer_ese_s=float(lo[:, 0].max()),
                band_top=float(np.median(hi[:, 1])),
                outer_top_ese=float(np.median(P[(P[:, 0] > b0 + 1) & (P[:, 0] < o0 - 1), 1])),
                outer_top_wnw=float(np.median(P[(P[:, 0] > o1 + 1) & (P[:, 0] < b1 - 1), 1])))
    draw = dict(band_wnw_s=b1, band_ese_s=b0, outer_wnw_s=o1, outer_ese_s=o0, band_top=BAB['h_band'], outer_top_ese=BAB['h_outer'],
                outer_top_wnw=BAB['h_outer'])
    out = dict(px_per_m=round(k, 3), m_per_px=round(1 / k, 3), view='orthographic along +t (NNE) from t %.0f, far clip t %.0f' % (BAB['t_cam'], BAB['t_far']),
               rows=[dict(item=key, render=round(meas[key], 2), drawing=draw[key], dev=round(meas[key] - draw[key], 2)) for key in meas],
               note='silhouette = topmost opaque pixel per column of the alpha pass (LOD0); the parapet / coping top is the measured roof edge')
    json.dump(out, open(os.path.join(OUT, 'domestic_render_check%s.json' % suffix), 'w'), indent=1)
    log('BA-B section silhouette vs BD-02:', [(r['item'], r['dev']) for r in out['rows']])
    return out


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
    ap.add_argument('--glb', default=os.path.join(ROOT, 'data', 'buildings3d', 'domestic.glb'))
    ap.add_argument('--views', default='a1,d1,bab')
    ap.add_argument('--res', type=int, default=960)
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--suffix', default='')
    ap.add_argument('--qa', default='', choices=['', 'ao', 'backface'])
    ap.add_argument('--context', type=int, default=1, help='also import the tower and ITB assets (orientation in the photo views)')
    args = ap.parse_args()
    args.res = min(args.res, 960); args.samples = min(args.samples, 64)
    os.makedirs(OUT, exist_ok=True)
    ctx = [os.path.join(ROOT, 'data', 'buildings3d', f) for f in ('tower.glb', 'itb.glb')] if args.context and not args.qa else []
    setup(args.glb, args.threads, args.samples, args.lod, ctx)
    done = {}
    if args.qa:
        qa_override(args.qa)
        args.suffix = args.suffix + '_' + args.qa + ('' if args.lod == 0 else '_lod%d' % args.lod)
    for v in args.views.split(','):
        r = globals()['view_' + v](args)
        if args.qa:
            sc = bpy.context.scene; sc.view_settings.exposure = 0.0
            if sc.world: sc.world.node_tree.nodes.clear()
            r = (render(r[0]),)
            if args.qa == 'backface':
                img = bpy.data.images.load(r[0]); a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
                n_red = int(((a[..., 0] > 0.6) & (a[..., 1] < 0.2) & (a[..., 2] < 0.2)).sum())
                done[v + '_red_px'] = n_red
                log('BACKFACE %s LOD%d: %d red px of %d' % (v, args.lod, n_red, a.shape[0] * a.shape[1]))
            done[v] = [os.path.relpath(p, ROOT) for p in r]
            continue
        done[v] = [os.path.relpath(p, ROOT) for p in r]
        if v == 'bab':
            done['bab_check'] = bab_overlay(*r, suffix=args.suffix)
        elif v == 'a1':
            side_by_side(r[0], os.path.join(REF, 'a1.jpg'), 'domestic_cmp_a1%s.png' % args.suffix)
        elif v == 'd1':
            side_by_side(r[0], os.path.join(REF, 'd1.jpg'), 'domestic_cmp_d1%s.png' % args.suffix)
    done['args'] = dict(glb=os.path.relpath(args.glb, ROOT), res=args.res, samples=args.samples, lod=args.lod)
    json.dump(done, open(os.path.join(OUT, 'domestic_render%s.json' % args.suffix), 'w'), indent=1, default=str)
    if os.path.abspath(args.glb) == os.path.abspath(os.path.join(ROOT, 'data', 'buildings3d', 'domestic.glb')) and not args.suffix and not args.qa:
        sys.path.insert(0, HERE)
        import dom_manifest
        dom_manifest.add_renders(json.loads(json.dumps(done, default=str)), done['args'])
        log('manifest renders updated')


if __name__ == '__main__':
    main()
