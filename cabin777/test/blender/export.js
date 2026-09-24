// Export Builder geometry from the running page for the Blender Cycles review renderer (test/blender/render.py).
// Usage: node test/blender/export.js <outdir> <spec.json>
//   spec: { "w": 960, "h": 720, "shots": [
//     { "name": "roomPair", "unit": "roomPair", "opts": { "az": 2.35, "el": 0.42, "dist": 1.45 } },      // UNITS / STUDIO_UNITS
//     { "name": "econ_slice", "slice": { "z0": 47, "z1": 53, "parts": ["shell","upper","bins","seats","mono","ext"] },
//       "opts": { "eye": [0.4, 1.6, 53.5], "look": [-0.3, 1.1, 47], "fov": 60 } } ] }
// Writes <outdir>/<name>.json (meta + camera opts) + <name>.bin (baked, world-space arrays) and shared textures in
// <outdir>/tex/ (detail layers, photo swatches, canvas atlas). Page: $CABIN_PAGE or dist/test.html.
// Baking: every instance matrix of a mesh is applied (normals by the linear part, winding flipped for mirrors), the
// instance tint multiplies the linear vertex colour, and layer-13 seatback screens get their per-instance atlas row.
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const fs = require('fs'), path = require('path');
const out = process.argv[2];
const spec = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
fs.mkdirSync(path.join(out, 'tex'), { recursive: true });

// minimal RGBA8 PNG encoder (straight alpha)
function encodePNG(rgba, w, h) {
  const zlib = require('zlib');
  const crcT = new Int32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c; });
  const crc = (b) => { let c = -1; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) rgba.copy(raw, y * (w * 4 + 1) + 1, y * w * 4, (y + 1) * w * 4);
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}

(async () => {
  const t0 = Date.now();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 320, height: 240 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('pageerror', e.message));
  await page.addInitScript(() => { window.__TEST__ = true; });
  await page.goto('file://' + (process.env.CABIN_PAGE || path.resolve(__dirname, '../../dist/test.html')));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 240000 });
  await page.evaluate(() => { __app.loop = () => {}; });
  console.log('page ready', ((Date.now() - t0) / 1000).toFixed(1) + 's');

  // ---- shared textures: detail layers (RGBA = normal xy, albedo, roughness), photo swatches, atlas ----
  const tex = await page.evaluate(() => {
    // raw RGBA (a canvas round trip would premultiply the roughness-in-alpha channel)
    const S = 256;
    const png = (rgba) => { const u8 = new Uint8Array(rgba.buffer, rgba.byteOffset, S * S * 4); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
    const det = buildDetailLayers(S), res = { detail: {}, photo: {} };
    det.forEach((d, k) => { if (k > 0 && d) res.detail[k] = png(d); });
    if (PHOTO_PIX) for (const [k, name] of Object.entries(PHOTO_LAYERS)) if (PHOTO_PIX[name]) res.photo[k] = png(PHOTO_PIX[name]);
    res.atlas = ATL.canvas.toDataURL('image/png');
    res.params = LAYER_PARAMS; res.screenStep = ATL.screenStep;
    res.photoLayers = PHOTO_LAYERS; res.nLayers = N_LAYERS;
    return res;
  });
  const save = (rel, url) => { fs.writeFileSync(path.join(out, rel), Buffer.from(url.split(',')[1], 'base64')); return rel; };
  const saveRaw = (rel, b64) => { fs.writeFileSync(path.join(out, rel), encodePNG(Buffer.from(b64, 'base64'), 256, 256)); return rel; };
  const texMeta = { detail: {}, photo: {}, params: tex.params, photoLayers: tex.photoLayers, nLayers: tex.nLayers };
  for (const [k, u] of Object.entries(tex.detail)) texMeta.detail[k] = saveRaw(`tex/detail_${k}.png`, u);
  for (const [k, u] of Object.entries(tex.photo)) texMeta.photo[k] = saveRaw(`tex/photo_${k}.png`, u);
  texMeta.atlas = save('tex/atlas.png', tex.atlas);

  for (const shot of spec.shots) {
    const t1 = Date.now();
    const r = await page.evaluate((s) => {
      // ---- gather meshes (geo + instances) ----
      const recs = [];
      if (s.unit) {
        const f = (typeof UNITS !== 'undefined' && UNITS[s.unit]) || STUDIO_UNITS[s.unit];
        if (!f) throw new Error('unknown unit ' + s.unit);
        recs.push({ name: s.unit, geo: f(), inst: [M4.ident()], tints: null });
      } else {
        const sl = s.slice, parts = new Set(sl.parts || ['shell', 'upper', 'bins', 'seats', 'mono']);
        const fake = { mesh(geo, o = {}) { const m = { name: o.name || '', geo, inst: o.instances || [M4.ident()], tints: o.tints || null }; recs.push(m); return m; }, setInstances() {}, setInstancesRaw() {} };
        const L = buildLayout();
        const tag = (p) => { const n0 = recs.length; return () => { for (let i = n0; i < recs.length; i++) recs[i].part = p; }; };
        let done;
        if (parts.has('shell') || parts.has('upper')) { done = tag('shell'); buildShell(fake, L); done(); }
        if (parts.has('bins')) { done = tag('bins'); buildBins(fake, L); done(); }
        if (parts.has('seats')) { done = tag('seats'); buildSeats(fake, L); done(); }
        if (parts.has('mono')) { done = tag('mono'); buildMonuments(fake, L); done(); }
        if (parts.has('ext')) { done = tag('ext'); buildExterior(fake); done(); }
        for (const m of recs) if (m.part === 'shell' && m.name === 'upper' && !parts.has('upper')) m.skip = true;
        for (const m of recs) if (m.part === 'shell' && m.name === 'shell' && !parts.has('shell')) m.skip = true;
      }
      // ---- bake ----
      const z0 = s.slice ? s.slice.z0 : -1e9, z1 = s.slice ? s.slice.z1 : 1e9;
      const x0 = s.slice && s.slice.x0 != null ? s.slice.x0 : -1e9, x1 = s.slice && s.slice.x1 != null ? s.slice.x1 : 1e9;
      const P = [], N = [], C = [], M = [], U = [], I = [], F = [];
      const toLin = (c) => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
      const lut = new Float32Array(256); for (let i = 0; i < 256; i++) lut[i] = toLin(i / 255);
      const stats = {};
      let nv = 0;
      for (const m of recs) {
        if (m.skip || !m.inst.length) continue;
        const g = m.geo, gp = g.pos, gn = g.nrm, gu = g.uv, gc = g.col, gm = g.mat, gi = g.idx, n = gp.length / 3;
        const glass = /^glass/.test(m.name);
        const [bmn, bmx] = g.bounds || [[-1e9, -1e9, -1e9], [1e9, 1e9, 1e9]];
        const big = m.inst.length === 1 && (bmx[2] - bmn[2]) > 4;   // whole-cabin meshes: clip per triangle
        m.inst.forEach((xf, ii) => {
          // instance culling: centre of the transformed bounds inside the slice
          if (!big) {
            const c = M4.point(xf, [(bmn[0] + bmx[0]) / 2, (bmn[1] + bmx[1]) / 2, (bmn[2] + bmx[2]) / 2]);
            if (c[2] < z0 || c[2] > z1 || c[0] < x0 || c[0] > x1) return;
          }
          const t = m.tints && m.tints[ii] ? m.tints[ii] : [1, 1, 1, 0];
          const scr = Math.floor(t[3] + 0.001) * ATL.screenStep;
          const det = xf[0] * (xf[5] * xf[10] - xf[9] * xf[6]) - xf[4] * (xf[1] * xf[10] - xf[9] * xf[2]) + xf[8] * (xf[1] * xf[6] - xf[5] * xf[2]);
          const flip = det < 0;
          const wp = new Float32Array(n * 3);
          for (let k = 0; k < n; k++) {
            const x = gp[k * 3], y = gp[k * 3 + 1], z = gp[k * 3 + 2];
            wp[k * 3] = xf[0] * x + xf[4] * y + xf[8] * z + xf[12];
            wp[k * 3 + 1] = xf[1] * x + xf[5] * y + xf[9] * z + xf[13];
            wp[k * 3 + 2] = xf[2] * x + xf[6] * y + xf[10] * z + xf[14];
          }
          const remap = new Int32Array(n).fill(-1);
          const vert = (k) => {
            if (remap[k] >= 0) return remap[k];
            remap[k] = nv++;
            P.push(wp[k * 3], wp[k * 3 + 1], wp[k * 3 + 2]);
            const a = gn[k * 3], b = gn[k * 3 + 1], c = gn[k * 3 + 2];
            let nx = xf[0] * a + xf[4] * b + xf[8] * c, ny = xf[1] * a + xf[5] * b + xf[9] * c, nz = xf[2] * a + xf[6] * b + xf[10] * c;
            const l = Math.hypot(nx, ny, nz) || 1; N.push(nx / l, ny / l, nz / l);
            C.push(lut[gc[k * 4]] * t[0], lut[gc[k * 4 + 1]] * t[1], lut[gc[k * 4 + 2]] * t[2], 1);
            M.push(gm[k * 4] / 255, gm[k * 4 + 1] / 255, gm[k * 4 + 3] / 255);
            return remap[k];
          };
          let tris = 0;
          for (let q = 0; q < gi.length; q += 3) {
            const a = gi[q], b = flip ? gi[q + 2] : gi[q + 1], c = flip ? gi[q + 1] : gi[q + 2];
            if (big) {
              const cz = (wp[a * 3 + 2] + wp[b * 3 + 2] + wp[c * 3 + 2]) / 3, cx = (wp[a * 3] + wp[b * 3] + wp[c * 3]) / 3;
              if (cz < z0 || cz > z1 || cx < x0 || cx > x1) continue;
            }
            const layer = gm[a * 4 + 2];
            I.push(vert(a), vert(b), vert(c));
            for (const v of [a, b, c]) U.push(gu ? gu[v * 2] : 0, (gu ? gu[v * 2 + 1] : 0) + (layer === 13 ? scr : 0));
            F.push(glass ? 25 : layer);
            tris++;
          }
          if (tris) stats[m.name] = (stats[m.name] || 0) + tris;
        });
      }
      const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
      for (let k = 0; k < P.length; k += 3) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], P[k + a]); mx[a] = Math.max(mx[a], P[k + a]); }
      // transfer as base64 blocks (page.evaluate returns JSON)
      const b64 = (ta) => { const u8 = new Uint8Array(ta.buffer); let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
      return {
        nv, nt: I.length / 3, bounds: [mn, mx], stats,
        blocks: { pos: b64(new Float32Array(P)), nrm: b64(new Float32Array(N)), col: b64(new Float32Array(C)), mat: b64(new Float32Array(M)),
          uv: b64(new Float32Array(U)), idx: b64(new Uint32Array(I)), fmat: b64(new Uint8Array(F)) },
      };
    }, shot);
    // ---- write <name>.bin + <name>.json ----
    const bufs = [], layout = {};
    let off = 0;
    for (const [k, v] of Object.entries(r.blocks)) {
      const b = Buffer.from(v, 'base64');
      layout[k] = { offset: off, bytes: b.length };
      bufs.push(b); off += b.length;
      const pad = (4 - (off % 4)) % 4; if (pad) { bufs.push(Buffer.alloc(pad)); off += pad; }
    }
    fs.writeFileSync(path.join(out, shot.name + '.bin'), Buffer.concat(bufs));
    const meta = {
      name: shot.name, unit: shot.unit || null, slice: shot.slice || null, opts: shot.opts || {},
      w: shot.w || spec.w || 960, h: shot.h || spec.h || 720,
      nv: r.nv, nt: r.nt, bounds: r.bounds, stats: r.stats, bin: shot.name + '.bin', layout,
      axes: 'engine: x right, y up, z aft (metres); render.py maps to Blender (x, -z, y)',
      tex: texMeta,
    };
    fs.writeFileSync(path.join(out, shot.name + '.json'), JSON.stringify(meta, null, 1));
    console.log('export', shot.name, r.nv, 'verts', r.nt, 'tris', ((Date.now() - t1) / 1000).toFixed(1) + 's');
  }
  await browser.close();
})().catch((e) => { console.error('ERR', e); process.exit(1); });
