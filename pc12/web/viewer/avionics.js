// The live G3000 PRIME pages: the five display glasses of the flight deck (one mesh, material 'display_page', UVs into
// one 2048 x 1296 atlas -- model/g3000_pages.py, GLB meta 'displays') show pages drawn in the browser from the simulated
// aircraft: the engine (engine.js, the same state the sound reads), the gear / flaps / trims / doors (kinematics.js) and
// the day of the Environment knobs (env.js).  The GLB's static atlas stays the fallback for other glTF viewers, ?avx=0,
// and an error here.
//
// Texture: one CanvasTexture (`g3000_live`) replaces the GLB atlas on the GLB material BEFORE new Model(), so every
// viewer material clone (interior, AO, cutaway, X-ray) inherits it (prepareLiveAtlas).  Each page draws into its own
// canvas at its atlas rectangle's size x the live scale; a changed page is copied into the master canvas (three
// re-uploads it after a context restore) and uploaded alone with renderer.copyTextureToTexture (texSubImage2D; the
// atlas' mips regenerate once per batch).
// Cadence: every animation frame update() builds the quantised view of each page (avx_pages.js view*) -- a page is
// redrawn only when its view changes, at most `hz` times a second (20 desktop, 10 phones; 2 for a page under 120 px on
// screen, none under 24 px or off screen), so a parked aircraft with nothing moving draws nothing and renders nothing.
// Picture: while a page changes the glass joins Stage.overlay (picture.js: the still image without it, the glass
// composed over it each frame -- a page change costs a compose, not a 2.7M-triangle render); it leaves AVX.hold s after
// the last upload (then the still passes supersample the pages again), and stays while the propeller's layered overlay
// is up anyway.
// URL: ?avx=0 the static atlas, ?avx=off black glass (master power off), ?avxres=1|2 the atlas scale, ?avxhz= the rate,
// ?avxclock=0 dashes for the UTC clock (tests), ?avxlabels=0 the words as abstract strokes (labels are on by
// default: owner 2026-10-24), ?avxovl=always|never.
import * as THREE from 'three';
import { drawPdu, drawMfd, drawSdu, keyPdu, keyMfd, keySdu, PFD_W } from './avx_pages.js';
import { AVX_LABELS, NUMERALS } from './avx_font.js';
import { OVERLAY_LAYER } from './picture.js';
import { WORLD } from './outside.js';

const Q = new URLSearchParams(typeof location !== 'undefined' ? location.search : '');
export const AVX = {
  on: !['0', 'false'].includes(Q.get('avx')), off: Q.get('avx') === 'off', res: +Q.get('avxres') || 0,
  hz: +Q.get('avxhz') || 0, clock: Q.get('avxclock') !== '0', hold: 1.5, ovl: Q.get('avxovl') || '',
};
AVX_LABELS.on = !['0', 'false'].includes(Q.get('avxlabels'));      // owner 2026-10-24: labels on by default

const ATLAS = { W: 2048, H: 1296,
  rects: { pfd_L: [0, 0, 1016, 633], mfd: [1032, 0, 2048, 633], pfd_R: [0, 649, 1016, 1282], sdu_L: [1032, 649, 1432, 1291],
    sdu_R: [1448, 649, 1848, 1291] } };
const PAGES = ['pfd_L', 'pfd_R', 'mfd', 'sdu_L', 'sdu_R'];
// widget rectangles (page mm) for rects() (tests): the MFD's engine strip, the PFD's tapes and boxes
const WIDGETS = {
  mfd: { eis: [0, 0, 59, 189.5], gauges: [0, 0, 59, 56], fuel: [0, 62, 58, 91], gear: [0, 92, 58, 135], bat: [0, 135, 58, 157],
    map: [61.5, 18.5, 303.5, 117.5] },
  pfd_L: { pfd: [0, 0, PFD_W, 189.5], alt: [134, 19, 176, 100], spd: [5, 19, 31, 88], hdg: [40, 103, 143, 176], bottom: [0, 176.5, PFD_W, 189.5],
    inboard: [PFD_W, 0, 305, 189.5] },
  pfd_R: { pfd: [305 - PFD_W, 0, 305, 189.5], inboard: [0, 0, 305 - PFD_W, 189.5] },
};

// the scale of the live atlas: 2 on desktops with large textures and a hardware renderer (close-ups), else 1
export function liveScale({ low, software, maxSize }) {
  if (AVX.res) return AVX.res >= 2 && maxSize >= 8192 ? 2 : AVX.res >= 1.5 && maxSize >= 4096 ? 1.5 : 1;
  return !low && !software && maxSize >= 8192 ? 2 : 1;
}

// before new Model(): the GLB's display_page material gets the live canvas texture (initialised from the GLB atlas)
export function prepareLiveAtlas(gltf, { scale = 1 } = {}) {
  if (!AVX.on) return null;
  let src = null;
  gltf.scene.traverse((o) => { if (!src && o.isMesh && o.material && o.material.name === 'display_page') src = o.material; });
  const old = src && src.emissiveMap;
  if (!old || !old.image) return null;
  const W = Math.round(ATLAS.W * scale), H = Math.round(ATLAS.H * scale);
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const cx = cv.getContext('2d', { alpha: false });
  cx.drawImage(old.image, 0, 0, W, H);
  // the static atlas, kept for setEnabled(false) and the error fallback
  const saved = document.createElement('canvas');
  saved.width = W; saved.height = H;
  saved.getContext('2d', { alpha: false }).drawImage(cv, 0, 0);
  if (AVX.off) { cx.fillStyle = '#000'; cx.fillRect(0, 0, W, H); }
  const tex = new THREE.CanvasTexture(cv);
  tex.flipY = false;                              // the glTF UV convention (a CanvasTexture defaults to true)
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.name = 'g3000_live';
  src.emissiveMap = tex;
  try { if (old.image.close) old.image.close(); } catch (e) { /* not an ImageBitmap */ }
  old.dispose();
  return { tex, canvas: cv, ctx: cx, saved, scale, W, H, material: src };
}

const pad2 = (n) => String(n).padStart(2, '0');
function utcClock() { const d = new Date(); return `${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`; }

export class Avionics {
  constructor({ model, stage, kin, env, live, low = false }) {
    this.model = model; this.stage = stage; this.kin = kin; this.env = env; this.live = live;
    this.low = low;
    this.enabled = !!live && !AVX.off;
    this.hz = AVX.hz || (low ? 10 : 20);
    this.stats = { uploads: 0, full: 0, draws: 0, uploadMs: 0, errors: 0, frames: 0 };
    this.lastUpload = -1e9;
    this._prevUp = -1e9;
    this.clock = AVX.clock ? utcClock() : null;
    this.error = null;
    const mr = model.meshRecs.find((m) => m.base && m.base.name === 'display_page');
    this.glassRec = mr || null;
    this.glass = mr ? mr.mesh : null;
    let disp = null;
    model.root.traverse((o) => { if (!disp && o.userData && o.userData.displays) disp = o.userData.displays; });
    this.displays = disp || {};
    // the rest frame of the glass' parent: page quads (meta, model axes) follow the part's explode / fly-in offsets
    model.root.updateMatrixWorld(true);
    this.m0inv = this.glass ? this.glass.parent.matrixWorld.clone().invert() : new THREE.Matrix4();
    this.pages = {};
    if (!this.enabled) return;
    const k = live.scale;
    for (const id of PAGES) {
      const d = this.displays[id] || {};
      const r = d.page || ATLAS.rects[id];
      const mmW = d.size ? d.size[0] * 1000 : (id.startsWith('sdu') ? 94 : 305), mmH = d.size ? d.size[1] * 1000 : (id.startsWith('sdu') ? 151 : 189.5);
      const w = r[2] - r[0], h = r[3] - r[1];
      const cv = document.createElement('canvas');
      cv.width = Math.round(w * k); cv.height = Math.round(h * k);
      const ctx = cv.getContext('2d', { alpha: false });
      const P = {
        id, kind: id.slice(0, 3), side: id.endsWith('_R') ? 'R' : 'L', rect: r, mmW, mmH, canvas: cv, ctx, cache: {}, log: [],
        sx: k * (w - 1) / mmW, sy: k * (h - 1) / mmH, ox: 0.5 * k, oy: 0.5 * k, key: null, lastDraw: -1e9, draws: 0,
        texWrap: new THREE.Texture(cv), visPx: 0, layers: [],
      };
      P.pxPerMm = P.sx;
      P.layer = (fn, x, y, lw, lh) => this._layer(P, fn, x, y, lw, lh);
      P.blit = (Lr) => { const c = P.ctx; c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(Lr.cv, Lr.px0, Lr.py0); c.restore(); if (Lr.log) P.log.push(...Lr.log); };
      this.pages[id] = P;
    }
    // the atlas' gaps black, then every page drawn at once: the in-flight static pages are never seen when live
    live.ctx.fillStyle = '#040507';
    live.ctx.fillRect(0, 0, live.W, live.H);
    this._ovl = [this.glass];
    try {
      const S = this._snapshot();
      for (const id of PAGES) this._draw(this.pages[id], S);
      live.tex.needsUpdate = true;
    } catch (e) { this._fail(e); }
  }

  // a static layer of a page (the SVT, the map relief, a page's frame): drawn once into its own canvas at the page's
  // device pixels (blit() puts it back pixel for pixel)
  _layer(P, fn, x, y, w, h) {
    const T = P.ctx.getTransform();
    const px0 = Math.floor(T.e + x * T.a), py0 = Math.floor(T.f + y * T.d);
    const cv = document.createElement('canvas');
    cv.width = Math.max(1, Math.ceil(w * T.a) + 2); cv.height = Math.max(1, Math.ceil(h * T.d) + 2);
    const lc = cv.getContext('2d');
    lc.setTransform(T.a, 0, 0, T.d, T.e - px0, T.f - py0);
    const keep = P.ctx, log = P.log;
    P.ctx = lc; P.log = [];
    let staticLog;
    try { fn(); } finally { staticLog = P.log; P.ctx = keep; P.log = log; }
    return { cv, px0, py0, log: staticLog };
  }

  // the state every page reads (quantised by the page views)
  _snapshot() {
    const k = this.kin, e = k.eng.state, ev = this.env.get(), atm = k.atm;
    return {
      eng: e, adc: e.adc, rpmT: k.t.rpm, pitch: k.c.pitch, toMode: !!k.toMode,
      gear: { pos: k.gear.pos, door: k.gear.door, target: k.gear.target },
      flaps: k.c.flaps, flapsT: k.t.flaps, trims: { stab: k.c.stabTrim, ail: k.c.ailTrim, rud: k.c.rudTrim },
      doors: { airstair: k.c.door_airstair, cargo: k.c.door_cargo },
      env: ev, atm, hdg: ev.hdg, baroMode: ev.baro, qnhUnit: ev.qnhUnit, clock: this.clock,
    };
  }
  _key(P, S) {
    return P.kind === 'pfd' ? keyPdu(S, P.side) : P.kind === 'mfd' ? keyMfd(S) : keySdu(S, P.side);
  }
  _draw(P, S) {
    const ctx = P.ctx;
    P.log = [];
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#040507';
    ctx.fillRect(0, 0, P.canvas.width, P.canvas.height);
    ctx.setTransform(P.sx, 0, 0, P.sy, P.ox, P.oy);
    ctx.lineCap = 'butt'; ctx.lineJoin = 'miter';
    if (P.kind === 'pfd') drawPdu(P, S, WORLD);
    else if (P.kind === 'mfd') drawMfd(P, S);
    else drawSdu(P, S);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    P.key = this._key(P, S);
    P.draws++;
    this.stats.draws++;
    // into the master canvas (the context-restore source)
    const k = this.live.scale;
    this.live.ctx.drawImage(P.canvas, Math.round(P.rect[0] * k), Math.round(P.rect[1] * k));
  }
  _upload(list) {
    const R = this.stage.renderer, tex = this.live.tex, k = this.live.scale, t0 = performance.now();
    // a texture three has not created yet, or one with a full upload pending (the constructor, a context restore,
    // filterTextures): upload the master canvas whole -- it holds every page just drawn.  copyTextureToTexture would
    // run that upload inside its first copy with generateMipmaps off, and three keys its GPU texture on generateMipmaps:
    // a new single-level WebGL texture (no trilinear mips until the next full upload)
    const p = R.properties.get(tex);
    if (!p.__webglTexture || p.__version !== tex.version) {
      tex.generateMipmaps = true;
      R.initTexture(tex);
      this.stats.uploads += list.length; this.stats.full++;
      this.stats.uploadMs += performance.now() - t0; this.lastUpload = performance.now();
      return;
    }
    // three r160's state.bindTexture skips gl.activeTexture when its cache already has the texture on that unit, so
    // copyTextureToTexture's texSubImage2D / generateMipmap would act on whichever unit the last draw left active
    // ('no texture bound to target', or another texture written): make unit 0 -- the one it binds to -- active first
    const gl = R.getContext();
    try {
      list.forEach((P, i) => {
        tex.generateMipmaps = i === list.length - 1;
        R.state.activeTexture(gl.TEXTURE0);
        R.copyTextureToTexture(new THREE.Vector2(Math.round(P.rect[0] * k), Math.round(P.rect[1] * k)), P.texWrap, tex);
      });
    } catch (e) {
      tex.needsUpdate = true;                    // a full re-upload of the master canvas instead
    }
    tex.generateMipmaps = true;
    this.stats.uploads += list.length;
    this.stats.uploadMs += performance.now() - t0;
    this.lastUpload = performance.now();
  }
  _fail(e) {
    this.stats.errors++;
    if (!this.error) { this.error = String(e && e.stack || e); console.warn('avionics: live pages off,', e); }
    this.setEnabled(false);
  }

  // the glass' screen footprint (CSS px): the page quad from meta 'displays' through the part's current transform
  _quad(id, mm = null) {
    const d = this.displays[id];
    if (!d || !d.centre) return null;
    const cam = this.stage.camera, el = this.stage.renderer.domElement;
    const M = this.glass ? this._m.multiplyMatrices(this.glass.parent.matrixWorld, this.m0inv) : null;
    const W = d.size[0], H = d.size[1], P = this.pages[id];
    const box = mm || [0, 0, P ? P.mmW : W * 1000, P ? P.mmH : H * 1000];
    const out = [];
    for (const [mx, my] of [[box[0], box[3]], [box[2], box[3]], [box[2], box[1]], [box[0], box[1]]]) {
      const s = mx / (W * 1000) - 0.5, t = 0.5 - my / (H * 1000);
      const p = [0, 1, 2].map((i) => d.centre[i] + s * W * d.u[i] + t * H * d.v[i]);
      const v = this._v.set(p[1], p[2], p[0]);
      if (M) v.applyMatrix4(M);
      v.project(cam);
      if (v.z > 1 || v.z < -1) return null;
      out.push([(v.x + 1) / 2 * el.clientWidth, (1 - v.y) / 2 * el.clientHeight]);
    }
    return out;
  }
  _shown() {
    let o = this.glass;
    if (!o || !this.glassRec || o.material !== this.glassRec.base) return false;     // X-ray / cutaway swaps: not live
    while (o) { if (!o.visible) return false; o = o.parent; }
    return true;
  }

  // every animation frame (main.js frame()): returns true when a page was uploaded
  update(dt, now = performance.now()) {
    if (!this.enabled || !this.glass) return false;
    this.stats.frames++;
    try {
      const S = this._snapshot();
      const running = S.eng.phase !== 'off';
      if (AVX.clock && running) { const c = utcClock(); if (c !== this.clock) this.clock = S.clock = c; }
      const dirty = PAGES.map((id) => this.pages[id]).filter((P) => this._key(P, S) !== P.key);
      if (!dirty.length) return false;
      if (AVX.clock && !running) {
        // the clock moves only together with other redraws when parked (no per-minute frames)
        const c = utcClock();
        if (c !== this.clock) { this.clock = S.clock = c; for (const id of ['pfd_L', 'pfd_R']) if (!dirty.includes(this.pages[id])) dirty.push(this.pages[id]); }
      }
      const shown = this._shown(), due = [];
      for (const P of dirty) {
        let hz = this.hz, px = 0;
        if (shown) {
          const qd = this._quad(P.id);
          if (qd) {
            const xs = qd.map((p) => p[0]), ys = qd.map((p) => p[1]);
            const el = this.stage.renderer.domElement;
            const x0 = Math.max(0, Math.min(...xs)), x1 = Math.min(el.clientWidth, Math.max(...xs));
            const y0 = Math.max(0, Math.min(...ys)), y1 = Math.min(el.clientHeight, Math.max(...ys));
            px = x1 > x0 && y1 > y0 ? Math.max(...xs) - Math.min(...xs) : 0;
          }
        }
        P.visPx = px;
        if (px < 24) continue;                    // off screen / too small: stays dirty
        if (px < 120) hz = Math.min(hz, 2);
        if (now - P.lastDraw < 1000 / hz - 2) continue;
        due.push(P);
      }
      if (!due.length) return false;
      for (const P of due) { this._draw(P, S); P.lastDraw = now; }
      this._upload(due);
      // over a settled still image (or the spinning propeller's), or when pages keep changing (another upload within
      // AVX.hold), the glass joins the overlay: composed frames, not re-renders.  A lone redraw while the still is not
      // settled (the camera just moved or a refinement running; without refinement: within 8 frames of a move) keeps
      // the glass in the scene and restarts the still with the new page: entering and leaving the layered path would
      // each restart the refinement (twice the passes after a tour stop)
      const pic = this.stage.picture, a = pic && pic.a, prev = this._prevUp;
      this._prevUp = now;
      const settled = a && (pic.N > 0 ? a.valid && a.done : pic.frame - pic.lastMove >= 8);
      if (this._inOvl || this._prop || settled || now - prev < AVX.hold * 1000) return true;
      this.lastUpload = -1e9;
      if (pic) pic.invalidate();
      this.stage.needsRender = true;
      return false;
    } catch (e) { this._fail(e); return false; }
  }

  // the glass in Stage.overlay (picture.js layered path) while pages change or the propeller's overlay is up -- always
  // while the propeller's is (the still under a spinning propeller is never re-rendered for a page change, so a glass
  // left in it would show the page it had when that still was made; the glass and the disc join / leave together, and
  // the layered flag's change restarts the still)
  overlayFor(propOverlay, now = performance.now()) {
    this._prop = !!propOverlay;
    const on = this.enabled && this.glass && !this.stage.contextLost && this._shown() && AVX.ovl !== 'never'
      && (AVX.ovl === 'always' || !!propOverlay || now - this.lastUpload < AVX.hold * 1000);
    if (!on) { if (this.glass && this._inOvl) { this.glass.layers.disable(OVERLAY_LAYER); this._inOvl = false; } return null; }
    this._inOvl = true;
    return this._ovl;
  }

  // ---- tests / hooks
  flush() {
    if (!this.enabled) return this.state();
    try {
      const S = this._snapshot();
      if (AVX.clock && S.eng.phase !== 'off') S.clock = this.clock = utcClock();
      const due = PAGES.map((id) => this.pages[id]).filter((P) => this._key(P, S) !== P.key);
      const now = performance.now();
      for (const P of due) { this._draw(P, S); P.lastDraw = now; }
      if (due.length) this._upload(due);
    } catch (e) { this._fail(e); }
    return this.state();
  }
  // a close-up camera on a page (glTF {pos, target, fov}): `dist` m in front of the glass along its normal (tests, judges)
  closeup(id, dist = 0.45, fov = 30) {
    const d = this.displays[id];
    if (!d || !d.centre) return null;
    const u = d.u, v = d.v;
    let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const l = Math.hypot(...n) || 1;
    n = n.map((x) => x / l * (n[0] >= 0 ? 1 : -1));          // toward the crew (aft: + station)
    const p = d.centre.map((c, i) => c + n[i] * dist), gl = (a) => [a[1], a[2], a[0]];
    return { pos: gl(p), target: gl(d.centre), fov };
  }
  // labels as text (default) or abstract strokes (?avxlabels=0): tests, and a page that wants them off at run time
  setLabels(on) {
    AVX_LABELS.on = !!on;
    for (const id of PAGES) if (this.pages[id]) this.pages[id].cache = {};      // the static layers carry legends too
    this.redrawAll();
    return AVX_LABELS.on;
  }
  // the overlay policy at run time (tests: ?avxovl=): '' (auto), 'always', 'never'
  setOverlay(mode) { AVX.ovl = mode || ''; this.stage.needsRender = true; return AVX.ovl; }
  redrawAll() {
    if (!this.enabled) return;
    for (const id of PAGES) this.pages[id].key = null;
    this.flush();
  }
  state() {
    const pages = {};
    for (const id of PAGES) {
      const P = this.pages[id];
      if (!P) continue;
      pages[id] = { draws: P.draws, last: P.lastDraw, key: P.key, visPx: Math.round(P.visPx), text: P.log.map((t) => ({ w: t.w, s: t.s, label: !!t.label })),
        numeralsOnly: P.log.every((t) => t.label || NUMERALS.test(t.s)) };
    }
    const t = this.live && this.live.tex;
    return { live: this.enabled, scale: this.live ? this.live.scale : 0, hz: this.hz, ...this.stats, overlay: !!this._inOvl,
      labels: AVX_LABELS.on, error: this.error,
      texture: t ? { type: t.isCanvasTexture ? 'CanvasTexture' : t.type, w: t.image.width, h: t.image.height, flipY: t.flipY,
        colorSpace: t.colorSpace, mipmaps: t.generateMipmaps, anisotropy: t.anisotropy, name: t.name } : null, pages };
  }
  // the GPU's copy of each page against its canvas (tests: 'uploads not stale'): the live texture's level 0 (and level 1,
  // the mip the crew stops sample) read back through a framebuffer; mean absolute difference per channel (0-255) and
  // the share of pixels more than 24 off.  Level 1 is compared with a 2 x 2 box of the canvas (sRGB-encoded averages:
  // the GPU filters in linear light, so a few levels are expected on edges).
  verify() {
    const R = this.stage.renderer, gl = R.getContext(), tex = this.live && this.live.tex;
    if (!this.enabled || !tex || !gl.createFramebuffer) return null;
    const p = R.properties.get(tex), wt = p && p.__webglTexture;
    if (!wt) return null;
    const k = this.live.scale, out = {}, fb = gl.createFramebuffer();
    const prev = gl.getParameter(gl.FRAMEBUFFER_BINDING);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    try {
      for (const id of PAGES) {
        const P = this.pages[id];
        const x = Math.round(P.rect[0] * k), y = Math.round(P.rect[1] * k), w = P.canvas.width, h = P.canvas.height;
        const ref = P.ctx.getImageData(0, 0, w, h).data, row = {};
        for (const lev of [0, 1]) {
          gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, wt, lev);
          if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) { row['l' + lev] = null; continue; }
          const s = 1 << lev, lw = Math.floor(w / s), lh = Math.floor(h / s), buf = new Uint8Array(lw * lh * 4);
          gl.readPixels(Math.ceil(x / s), Math.ceil(y / s), lw, lh, gl.RGBA, gl.UNSIGNED_BYTE, buf);
          let sum = 0, bad = 0, n = 0;
          const ox = Math.ceil(x / s) * s - x, oy = Math.ceil(y / s) * s - y;
          for (let j = 1; j < lh - 1; j++) for (let i = 1; i < lw - 1; i++) {
            const q = (j * lw + i) * 4;
            let d = 0;
            for (let c = 0; c < 3; c++) {
              let r = 0;
              for (let b = 0; b < s; b++) for (let a = 0; a < s; a++) r += ref[((j * s + oy + b) * w + (i * s + ox + a)) * 4 + c];
              d += Math.abs(buf[q + c] - r / (s * s));
            }
            d /= 3; sum += d; n++; if (d > 24) bad++;
          }
          row['l' + lev] = { mad: +(sum / Math.max(n, 1)).toFixed(2), bad: +(bad / Math.max(n, 1)).toFixed(4) };
        }
        out[id] = row;
      }
    } finally {
      gl.bindFramebuffer(gl.FRAMEBUFFER, prev);
      gl.deleteFramebuffer(fb);
    }
    return out;
  }
  rects(page, widget = null) {
    const mm = widget && WIDGETS[page] && WIDGETS[page][widget] ? WIDGETS[page][widget] : null;
    return this._quad(page, mm);
  }
  snapshot(page) { const P = this.pages[page]; return P ? P.canvas.toDataURL('image/png') : null; }
  // the GLB's static page (the atlas the live pages replace): tests compare the pages' mean luminance
  staticSnapshot(page) {
    const P = this.pages[page], L = this.live;
    if (!P || !L) return null;
    const cv = document.createElement('canvas');
    cv.width = P.canvas.width; cv.height = P.canvas.height;
    cv.getContext('2d').drawImage(L.saved, -Math.round(P.rect[0] * L.scale), -Math.round(P.rect[1] * L.scale));
    return cv.toDataURL('image/png');
  }
  setEnabled(on) {
    if (!this.live) return false;
    if (!on) {
      this.enabled = false;
      try {
        this.live.ctx.drawImage(this.live.saved, 0, 0);
        this.live.tex.needsUpdate = true;
      } catch (e) { /* nothing more to do */ }
      if (this.glass) this.glass.layers.disable(OVERLAY_LAYER);
      this._inOvl = false;
    } else if (!this.error) {
      this.enabled = true;
      this.redrawAll();
      this.live.tex.needsUpdate = true;
    }
    this.stage.needsRender = true;
    return this.enabled;
  }
  // after a WebGL context restore: the master canvas is current (three re-uploads it); redraw anything stale
  contextRestored() {
    if (!this.live) return;
    this.live.tex.needsUpdate = true;
    for (const id of PAGES) if (this.pages[id]) this.pages[id].key = null;
  }
}
Avionics.prototype._m = new THREE.Matrix4();
Avionics.prototype._v = new THREE.Vector3();
