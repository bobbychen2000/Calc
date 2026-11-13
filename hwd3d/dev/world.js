// Dev page script: renders only the HWD world (P2, Phase 2) with named views, a simple orbit camera (drag / wheel /
// pinch) and a shot hook for the headless renders (dev/shoot.mjs). Not the app: P4 owns js/live/app.js.
import { initGL } from '../js/gl.js';
import { Renderer } from '../js/renderer.js';
import { Scene } from '../js/scene.js';
import { buildSite } from '../js/world/site.js';
import { buildHwdWorld } from '../js/live/world.js';
import { AppEnv } from '../js/env/app_env.js';
import { applyEnvToRenderer } from '../js/env/render_env.js';
import { HWD_AIRPORT } from '../data/hwd_airport.js';
import { thrWorld, endWorld } from '../js/geo.js';

const q = new URLSearchParams(location.search);
const SHOT = q.has('shot'); if (SHOT) document.body.classList.add('shot');
const hud = document.getElementById('hud');
const log = (s) => { console.log(s); };
const canvas = document.getElementById('c');
const scale = +(q.get('scale') || Math.min(window.devicePixelRatio || 1, 1.5));
const quality = q.get('q') || (Math.min(innerWidth, innerHeight) < 600 ? 'low' : 'high');
function size() { return [Math.max(64, Math.round(innerWidth * scale)), Math.max(64, Math.round(innerHeight * scale))]; }
let [W, H] = size(); canvas.width = W; canvas.height = H;
window.ANISO = 8;
const gl = initGL(canvas);
const R = new Renderer(W, H, { msaa: quality === 'low' ? 2 : 4, shadowRes: quality === 'low' ? 2048 : 4096 });
R.onFatal = (h) => { hud.innerHTML = h; };
const site = buildSite(HWD_AIRPORT);
const world = buildHwdWorld(R, HWD_AIRPORT, { site, quality, naip: q.get('ground') !== 'procedural', log });
const scene = new Scene(R, world); scene.staticLights.push(world.staticSprites);
// environment: a fixed instant (default 2026-11-13 12:30 PST) and a KHWD-format report unless given
const T = q.get('t') || '2026-11-13T20:30:00Z';
const env = new AppEnv({ mode: 'live', search: '?t=' + T + (q.get('metar') ? '&metar=' + encodeURIComponent(q.get('metar')) : ''), station: 'KHWD' });
const defMetar = 'METAR KHWD ' + new Date(Date.parse(T) - 36 * 60e3).toISOString().slice(8, 10) + new Date(Date.parse(T) - 36 * 60e3).toISOString().slice(11, 13) + '54Z 29008KT 10SM FEW060 19/12 A2974';
if (!q.get('metar')) env.setReports([{ rawOb: defMetar, obsTime: (Date.parse(T) - 36 * 60e3) / 1000 }]);
let post = { exposure: 0.45, shutter: 0, bloom: 0.012, vignette: 0.2, grain: 0.008, sat: 1.0 };
function applyEnv(force) { const E = env.update(Date.now()); const r = applyEnvToRenderer(R, world, E, { quality, force }); post.exposure = r.exposure; return E; }
applyEnv(true);
// ---------------------------------------------------------------- camera
const D2R = Math.PI / 180;
const cam = { target: [40, 12, 30], yaw: 25, pitch: 28, dist: 2600, fov: 45, eye: null };
const gy = (x, z) => site.groundY(x, z);
const P = (p) => [p[0], gy(p[0], p[1]), p[1]];
const thr = (e) => { const t = thrWorld(e); return [t[0], t[2]]; };
const tw = site.anchors.tower;
export const VIEWS = {
  overview: { target: P([40, 30]), yaw: 22, pitch: 30, dist: 2700, fov: 45 },
  thr10R: { target: P(thr('10R')), yaw: 119.85, pitch: 11, dist: 330, fov: 50 },
  thr28L: { target: P(thr('28L')), yaw: 299.86, pitch: 11, dist: 330, fov: 50 },
  green: { target: P([-50, -335]), yaw: 30, pitch: 38, dist: 230, fov: 50 },
  west: { target: P([-235, -615]), yaw: 335, pitch: 32, dist: 430, fov: 50 },
  tower: { eye: [tw.x, tw.eyeY, tw.z], yaw: 165, pitch: 7, fov: 62 },
  // top-down (north up) views for the NAIP comparison: width covered = 2 * dist * tan(fov / 2) * aspect
  top_10R: { target: P(thr('10R')), yaw: 0, pitch: 89.95, dist: 700, fov: 14 },
  top_28L: { target: P(thr('28L')), yaw: 0, pitch: 89.95, dist: 700, fov: 14 },
  top_green: { target: P([-60, -350]), yaw: 0, pitch: 89.95, dist: 900, fov: 14 },
  top_west: { target: P([-250, -600]), yaw: 0, pitch: 89.95, dist: 1300, fov: 14 },
  top_tower: { target: P([20, -380]), yaw: 0, pitch: 89.95, dist: 700, fov: 14 },
  top_wsock: { target: P([-26.98, -59.42]), yaw: 0, pitch: 89.95, dist: 250, fov: 14 },
  top_field: { target: P([40, 0]), yaw: 0, pitch: 89.95, dist: 7000, fov: 14 },
};
function setView(name) { const v = VIEWS[name]; if (!v) throw new Error('no view ' + name); Object.assign(cam, { eye: null, target: v.target || cam.target, dist: v.dist || 1 }, v); cam.name = name; }
function camera() {
  const dir = [Math.sin(cam.yaw * D2R) * Math.cos(cam.pitch * D2R), -Math.sin(cam.pitch * D2R), -Math.cos(cam.yaw * D2R) * Math.cos(cam.pitch * D2R)];
  const pos = cam.eye ? cam.eye : [cam.target[0] - dir[0] * cam.dist, cam.target[1] - dir[1] * cam.dist, cam.target[2] - dir[2] * cam.dist];
  const hAbove = Math.max(1, pos[1] - gy(pos[0], pos[2]));
  const d = cam.eye ? 200 : cam.dist;
  const near = Math.min(5, Math.max(0.2, Math.min(d * 0.004, hAbove * 0.3)));
  const split = Math.min(5000, Math.max(300, d * 3.5));
  const up = Math.abs(dir[1]) > 0.999 ? [0, 0, -1] : [0, 1, 0];
  return { pos, dir, up, fov: cam.fov * D2R, near, split, far: 40000, shadowSplits: [Math.max(60, d * 0.6), Math.max(400, d * 2.2), Math.max(2500, d * 4.5)] };
}
// ---------------------------------------------------------------- render
let frames = 0;
function render(t = performance.now()) {
  const C = camera();
  const fr = scene.frame(t, C.pos);
  R.render(fr, C, t / 1000, post);
  scene.commit();
  R.present(canvas.width, canvas.height);
  frames++;
}
function hudText() {
  const s = world.stats; const E = R.envState;
  hud.textContent = `HWD world (dev) · view ${cam.name || '-'} · ground ${world.groundMode} · q ${quality} · ${W}x${H}\n` +
    `sun az ${E.sun.az.toFixed(0)}° el ${E.sun.el.toFixed(1)}° · ${E.wx.raw || 'no METAR'}\n` +
    `terrain ${s.terrain.tris} tris · paint ${s.paint.tris} · buildings ${s.buildings.tris} · map ${s.map.w}x${s.map.h} @ ${s.map.res} m`;
}
// shot: render n frames and return the final image as a PNG data URL (independent of canvas compositing)
async function shot(name, n = 2) {
  if (name) setView(name);
  for (let i = 0; i < n; i++) render(1000 + i * 16);
  const px = R.readPixels(); const c2 = document.createElement('canvas'); c2.width = R.W; c2.height = R.H;
  const cx = c2.getContext('2d'); const id = cx.createImageData(R.W, R.H);
  for (let y = 0; y < R.H; y++) id.data.set(px.subarray((R.H - 1 - y) * R.W * 4, (R.H - y) * R.W * 4), y * R.W * 4);
  cx.putImageData(id, 0, 0); return c2.toDataURL('image/png');
}
// ---------------------------------------------------------------- controls (drag = orbit, wheel / pinch = zoom)
const ptrs = new Map(); let pinch0 = null;
canvas.addEventListener('pointerdown', e => { canvas.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); if (ptrs.size === 2) { const [a, b] = [...ptrs.values()]; pinch0 = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), dist: cam.dist }; } });
canvas.addEventListener('pointermove', e => {
  const p = ptrs.get(e.pointerId); if (!p) return;
  if (ptrs.size === 1) { if (cam.eye) { cam.yaw -= (e.clientX - p[0]) * 0.2; cam.pitch = Math.max(-30, Math.min(89, cam.pitch + (e.clientY - p[1]) * 0.2)); } else { cam.yaw -= (e.clientX - p[0]) * 0.25; cam.pitch = Math.max(2, Math.min(89.9, cam.pitch + (e.clientY - p[1]) * 0.25)); } }
  ptrs.set(e.pointerId, [e.clientX, e.clientY]);
  if (ptrs.size === 2 && pinch0) { const [a, b] = [...ptrs.values()]; const d = Math.hypot(a[0] - b[0], a[1] - b[1]); cam.dist = Math.max(15, Math.min(20000, pinch0.dist * pinch0.d / Math.max(1, d))); }
});
const up = e => { ptrs.delete(e.pointerId); if (ptrs.size < 2) pinch0 = null; };
canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
canvas.addEventListener('wheel', e => { e.preventDefault(); cam.dist = Math.max(15, Math.min(20000, cam.dist * Math.exp(e.deltaY * 0.001))); }, { passive: false });
addEventListener('resize', () => { [W, H] = size(); canvas.width = W; canvas.height = H; R.resize(W, H); });
const vb = document.getElementById('views');
for (const k of Object.keys(VIEWS)) { const b = document.createElement('button'); b.textContent = k; b.onclick = () => setView(k); vb.appendChild(b); }
setView(VIEWS[q.get('view')] ? q.get('view') : 'overview');
// ---------------------------------------------------------------- go
window.HWDW = { R, scene, world, site, env, cam, VIEWS, setView, render, shot, applyEnv, stats: () => world.stats, inventory: () => world.inventory,
  setGround: (m) => { world.setGroundMode(m); } };
world.ready.then(() => {
  if (q.get('ground') === 'procedural') world.setGroundMode('procedural');
  window.__worldReady = true; hudText();
  if (!SHOT) { const loop = () => { render(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); setInterval(() => { applyEnv(false); hudText(); }, 30000); }
}).catch(e => { window.__worldError = String(e); hud.textContent = 'error: ' + e; });
