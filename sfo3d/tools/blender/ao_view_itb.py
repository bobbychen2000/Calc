# SPDX-License-Identifier: GPL-3.0-or-later
"""QA view of the BAKED ambient occlusion of data/buildings3d/itb.glb: every material is replaced by an emission shader showing
its occlusionTexture (TEXCOORD_1), rendered from the render_itb.py cameras -> out/buildings3d/itb_ao_<view>.png.
    python3 tools/blender/ao_view_itb.py [--views i4,i3,baa] [--lod 0]"""
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
               'baa': lambda: R.view_baa_cam(), 'under': lambda: R.camera('c', R.W(-118.0, -45.0, 14.0), R.W(-60.0, 0.0, 30.0), lens=28.0, res=(960, 540))}[v]
        cam()
        sc.cycles.samples = 4; sc.cycles.use_denoising = False
        R.render(os.path.join(R.OUT, 'itb_ao_%s%s.png' % (v, '' if args.lod == 0 else '_lod%d' % args.lod)))


if __name__ == '__main__':
    main()
