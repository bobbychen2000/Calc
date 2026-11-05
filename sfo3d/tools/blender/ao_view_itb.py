# SPDX-License-Identifier: GPL-3.0-or-later
"""QA views of data/buildings3d/itb.glb (emission only, a few seconds):
  AO        every material shows its baked occlusionTexture (TEXCOORD_1); detail members without AO are pink
            -> out/buildings3d/itb_ao_<view>.png
  backface  (--backface) front faces grey, BACK faces red: the asset is single-sided (doubleSided false), so any red pixel
            is a face wound inwards or a hole through which an inner back face shows -> itb_bf_<view>.png + red pixel counts
    python3 tools/blender/ao_view_itb.py [--views i4,i3,baa,east,top] [--lod 0] [--backface]"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_itb as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--glb', default=os.path.join(R.ROOT, 'data', 'buildings3d', 'itb.glb'))
    ap.add_argument('--views', default='i4,i3,baa')
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--backface', action='store_true')
    args = ap.parse_args()
    R.setup(args.glb, 3, 4)
    for e in ('LOD0', 'LOD1', 'LOD2'):
        ob = bpy.data.objects.get(e)
        if ob:
            for c in ob.children_recursive: c.hide_render = (e != 'LOD%d' % args.lod)
    for m in bpy.data.materials:
        if not m.use_nodes: continue
        nt = m.node_tree
        img = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith('itb_ao')), None)
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        if args.backface:
            geo = nt.nodes.new('ShaderNodeNewGeometry'); mix = nt.nodes.new('ShaderNodeMixShader')
            e1 = nt.nodes.new('ShaderNodeEmission'); e1.inputs['Color'].default_value = (0.8, 0.8, 0.8, 1)
            e2 = nt.nodes.new('ShaderNodeEmission'); e2.inputs['Color'].default_value = (1, 0, 0, 1)
            nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac']); nt.links.new(e1.outputs[0], mix.inputs[1])
            nt.links.new(e2.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
            continue
        em = nt.nodes.new('ShaderNodeEmission')
        if img is not None:
            nt.links.new(img.outputs['Color'], em.inputs['Color'])
        else:
            em.inputs['Color'].default_value = (1.0, 0.25, 0.25, 1)      # no AO (detail members): pink
        nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    sc = bpy.context.scene
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.0
    for v in args.views.split(','):
        R.sun_sky(250, 38, exposure=0.0)
        sc.world.node_tree.nodes.clear()
        cam = {'i4': lambda: R.camera('c', R.W(4.0, -430.0, 20.0), R.W(4.0, 0.0, 24.0), lens=58.0, res=(960, 487)),
               'i3': lambda: R.camera('c', R.W(-95.0, -46.0, R.G.L3 + 1.7), R.W(-10.0, -24.0, 26.0), lens=24.0, res=(960, 540)),
               'baa': lambda: R.view_baa_cam(), 'a2g': lambda: R.a2g_cam(), 'bag': lambda: R.bag_cam(), 'under': lambda: R.camera('c', R.W(-118.0, -45.0, 14.0), R.W(-60.0, 0.0, 30.0), lens=28.0, res=(960, 540)),
               'east': lambda: R.camera('c', R.W(30.0, 300.0, 60.0), R.W(0.0, 0.0, 20.0), lens=35.0, res=(960, 540)),
               'top': lambda: R.camera('c', R.W(-60.0, -80.0, 150.0), R.W(0.0, 0.0, 30.0), lens=30.0, res=(960, 540))}[v]
        cam()
        sc.cycles.samples = 4; sc.cycles.use_denoising = False
        p = R.render(os.path.join(R.OUT, 'itb_%s_%s%s.png' % ('bf' if args.backface else 'ao', v, '' if args.lod == 0 else '_lod%d' % args.lod)))
        if args.backface:
            import numpy as np
            img = bpy.data.images.load(p); a = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)
            print('BACKFACE %s LOD%d: %d red px of %d' % (v, args.lod, int(((a[..., 0] > 0.6) & (a[..., 1] < 0.2)).sum()), a.shape[0] * a.shape[1]))


if __name__ == '__main__':
    main()
