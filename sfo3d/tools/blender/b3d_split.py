"""Per-building files of the landside asset for the phone tier (integration review round 2, finding 4): data/buildings3d/
landside.glb (20-21 MB: LOD0 162k + 93k instanced, LOD1 81k + 66k, LOD2 16k triangles, 1,732 cars) was fetched and parsed
whole as soon as the camera came within the LOD2 switch distance of ANY of its 24 units - from every core camera on the
low tier (the tower cab, the gates, the ITB). Split here into one file per top-level building node, so js/three/
buildings3d.js loads only the units near the camera and releases them when far.

    python3 tools/blender/b3d_split.py           # also run by tools/blender/b3d_integrate.py (the index goes to integration.js)

  data/buildings3d/lsu_<unit>.glb    the building node with its LOD0 / LOD1 / LOD2 children, root node as in landside.glb
                                     (name, translation, extras), the accessors / buffer views / materials / samplers it uses
  data/buildings3d/lsu_img_<name>.png  the images, written once and referenced by URI from every unit file that uses them
                                     (the three AO atlases are shared by up to 24 units: embedding them would add ~35 MB);
                                     each texture is named 'lsu:<image>' so the loader keeps ONE GPU texture per image
Geometry, materials and extras are byte-for-byte those of landside.glb (no re-encoding); landside.glb itself is unchanged
and stays the source (the landside group's export) and what the checks read. No bpy."""
import json, os, struct, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
D3 = os.path.join(ROOT, 'data', 'buildings3d')
PREFIX, IMG = 'lsu_', 'lsu_img_'


def read_glb(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]; js = json.loads(b[20:20 + n]); off = 20 + n
    ln = struct.unpack_from('<I', b, off)[0]; return js, b[off + 8:off + 8 + ln]


def write_glb(path, js, bin_):
    while len(bin_) % 4: bin_ += b'\0'
    js['buffers'] = [dict(byteLength=len(bin_))]
    j = json.dumps(js, separators=(',', ':')).encode()
    while len(j) % 4: j += b' '
    with open(path + '.tmp', 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(bin_)))
        f.write(struct.pack('<II', len(j), 0x4E4F534A)); f.write(j)
        f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
    os.replace(path + '.tmp', path)


def tex_refs(o, out):
    """texture indices referenced anywhere in a material (textureInfo objects: {'index': i, ...})"""
    if isinstance(o, dict):
        for k, v in o.items():
            if k.endswith('Texture') and isinstance(v, dict) and isinstance(v.get('index'), int): out.add(v['index'])
            tex_refs(v, out)
    elif isinstance(o, list):
        for v in o: tex_refs(v, out)
    return out


def remap_tex(o, m):
    if isinstance(o, dict):
        for k, v in o.items():
            if k.endswith('Texture') and isinstance(v, dict) and isinstance(v.get('index'), int): v['index'] = m[v['index']]
            remap_tex(v, m)
    elif isinstance(o, list):
        for v in o: remap_tex(v, m)


def split(src=os.path.join(D3, 'landside.glb'), log=print):
    t0 = time.time(); js, bin_ = read_glb(src)
    root_i = js['scenes'][js.get('scene', 0)]['nodes'][0]; root = js['nodes'][root_i]
    # the images once, as files (their own bytes, by name)
    img_file = {}
    for i, im in enumerate(js.get('images', [])):
        bv = js['bufferViews'][im['bufferView']]; data = bin_[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        ext = {'image/png': '.png', 'image/jpeg': '.jpg'}[im.get('mimeType', 'image/png')]
        fn = IMG + (im.get('name') or 'img%d' % i) + ext
        p = os.path.join(D3, fn)
        if not os.path.exists(p) or open(p, 'rb').read() != data:
            open(p + '.tmp', 'wb').write(data); os.replace(p + '.tmp', p)
        img_file[i] = fn
    index = []
    for ci in root.get('children', []):
        unit = js['nodes'][ci].get('name')
        # subtree (every node: LOD0 / LOD1 / LOD2 and their descendants)
        nodes, st = [], [ci]
        while st:
            i = st.pop(); nodes.append(i); st += js['nodes'][i].get('children', [])
        nmap = {old: k + 1 for k, old in enumerate(nodes)}          # 0 = the new root
        meshes = sorted({js['nodes'][i]['mesh'] for i in nodes if 'mesh' in js['nodes'][i]}); mmap = {m: k for k, m in enumerate(meshes)}
        mats, accs = set(), set()
        for m in meshes:
            for pr in js['meshes'][m]['primitives']:
                if 'material' in pr: mats.add(pr['material'])
                accs |= set(pr['attributes'].values()); accs |= {pr['indices']} if 'indices' in pr else set()
                for t in pr.get('targets', []): accs |= set(t.values())
        for i in nodes:
            for e in js['nodes'][i].get('extensions', {}).values():
                accs |= set(e.get('attributes', {}).values())
        mats = sorted(mats); matmap = {m: k for k, m in enumerate(mats)}
        texs = sorted(set().union(*[tex_refs(js['materials'][m], set()) for m in mats])) if mats else []; tmap = {t: k for k, t in enumerate(texs)}
        imgs = sorted({js['textures'][t]['source'] for t in texs}); imap = {s: k for k, s in enumerate(imgs)}
        smps = sorted({js['textures'][t]['sampler'] for t in texs if 'sampler' in js['textures'][t]}); smap = {s: k for k, s in enumerate(smps)}
        accs = sorted(accs); amap = {a: k for k, a in enumerate(accs)}
        bvs = sorted({js['accessors'][a]['bufferView'] for a in accs if 'bufferView' in js['accessors'][a]}); bmap = {b: k for k, b in enumerate(bvs)}
        nb = bytearray(); new_bv = []
        for b in bvs:
            v = dict(js['bufferViews'][b]); data = bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
            while len(nb) % 4: nb.append(0)
            v['byteOffset'] = len(nb); v['buffer'] = 0; nb += data; new_bv.append(v)
        out = dict(asset=dict(js['asset'], generator=js['asset'].get('generator', '') + ' + tools/blender/b3d_split.py'), scene=0, scenes=[dict(nodes=[0])])
        r = {k: v for k, v in root.items() if k != 'children'}; r['children'] = [nmap[ci]]; out['nodes'] = [r]
        for i in nodes:
            nd = json.loads(json.dumps(js['nodes'][i]))
            if 'children' in nd: nd['children'] = [nmap[c] for c in nd['children']]
            if 'mesh' in nd: nd['mesh'] = mmap[nd['mesh']]
            for e in nd.get('extensions', {}).values():
                if 'attributes' in e: e['attributes'] = {k: amap[a] for k, a in e['attributes'].items()}
            out['nodes'].append(nd)
        out['meshes'] = []
        for m in meshes:
            me = json.loads(json.dumps(js['meshes'][m]))
            for pr in me['primitives']:
                pr['attributes'] = {k: amap[a] for k, a in pr['attributes'].items()}
                if 'indices' in pr: pr['indices'] = amap[pr['indices']]
                if 'material' in pr: pr['material'] = matmap[pr['material']]
                if 'targets' in pr: pr['targets'] = [{k: amap[a] for k, a in t.items()} for t in pr['targets']]
            out['meshes'].append(me)
        out['materials'] = []
        for m in mats:
            ma = json.loads(json.dumps(js['materials'][m])); remap_tex(ma, tmap); out['materials'].append(ma)
        out['accessors'] = []
        for a in accs:
            ac = dict(js['accessors'][a])
            if 'bufferView' in ac: ac['bufferView'] = bmap[ac['bufferView']]
            out['accessors'].append(ac)
        out['bufferViews'] = new_bv
        if texs:
            out['textures'] = []
            for t in texs:
                tx = dict(js['textures'][t]); si = tx['source']; tx['source'] = imap[si]
                if 'sampler' in tx: tx['sampler'] = smap[tx['sampler']]
                tx['name'] = 'lsu:' + (js['images'][si].get('name') or str(si)); out['textures'].append(tx)
            out['images'] = [dict(uri=img_file[s], name=js['images'][s].get('name'), mimeType=js['images'][s].get('mimeType', 'image/png')) for s in imgs]
            if smps: out['samplers'] = [js['samplers'][s] for s in smps]
        used = set()
        for ma in out['materials']: used |= set(ma.get('extensions', {}).keys())
        for nd in out['nodes']: used |= set(nd.get('extensions', {}).keys())
        if used: out['extensionsUsed'] = sorted(used)
        req = [e for e in js.get('extensionsRequired', []) if e in used]
        if req: out['extensionsRequired'] = req
        fn = PREFIX + unit + '.glb'; write_glb(os.path.join(D3, fn), out, bytes(nb))
        sw = {}
        for c in js['nodes'][ci].get('children', []):
            ex = js['nodes'][c].get('extras', {})
            if isinstance(ex.get('lod'), int): sw[ex['lod']] = ex.get('switch_m')
        index.append(dict(unit=unit, file=PREFIX + unit, bytes=os.path.getsize(os.path.join(D3, fn)), switch1_m=sw.get(1), switch2_m=sw.get(2), images=[img_file[s] for s in imgs]))
    # stale unit files of units no longer in landside.glb
    keep = {e['file'] + '.glb' for e in index} | set(img_file.values())
    for f in os.listdir(D3):
        if (f.startswith(PREFIX) and f.endswith('.glb') or f.startswith(IMG)) and f not in keep and not f.endswith('.tmp'): os.remove(os.path.join(D3, f))
    log('landside split: %d unit files, %.1f MB (+ %d shared images %.1f MB) from %s (%.1f MB) in %.1f s'
        % (len(index), sum(e['bytes'] for e in index) / 1e6, len(img_file), sum(os.path.getsize(os.path.join(D3, f)) for f in img_file.values()) / 1e6, os.path.basename(src), os.path.getsize(src) / 1e6, time.time() - t0))
    return index


if __name__ == '__main__':
    idx = split()
    for e in idx: print('%-24s %8.2f MB  LOD2 at %s m' % (e['unit'], e['bytes'] / 1e6, e['switch2_m']))
