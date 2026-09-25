// TRAA disocclusion check (review round 1): the Engine pipeline (reversed depth, GTAO, TRAA) on a simple scene — a
// white tower in front of a dark ground with a bright checker wall behind — while the camera orbits the tower
// 3 deg per frame. After 12 moving frames the TRAA output is read back; then the camera holds that pose for 24 frames
// and the output is read again. Mean |moving - settled| over the pixels where they differ most measures the trails
// left where the background is revealed (history that should have been rejected by the disocclusion test).
// Page: js/three/dev/ghosttest.html (vendored three) — a copy with an import map pointing the vendor module at an
// unpatched build gives the "before". Result in window.__probe.
import { THREE } from '../lib.js';
import { Engine, QUALITY3 } from '../engine.js';
const q = new URLSearchParams(location.search); const out = { variant: q.get('v') || 'current' };
try {
  const c = document.createElement('canvas'); document.body.appendChild(c);
  const E = await new Engine(document.body, { ...QUALITY3.high, bloom: false }, { canvas: c }).init(); E.resize(innerWidth, innerHeight, 1);
  const S = E.scene; S.background = new THREE.Color(0.02, 0.02, 0.03); S.add(new THREE.HemisphereLight(0xffffff, 0x222222, 2.5));
  const g = new THREE.Mesh(new THREE.PlaneGeometry(800, 800), new THREE.MeshStandardNodeMaterial({ color: 0x151515, roughness: 1 })); g.rotation.x = -Math.PI / 2; S.add(g);
  const cv = document.createElement('canvas'); cv.width = cv.height = 256; const cx = cv.getContext('2d'); for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) { cx.fillStyle = (x + y) % 2 ? '#ffffff' : '#202020'; cx.fillRect(x * 32, y * 32, 32, 32); }
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(400, 120), new THREE.MeshStandardNodeMaterial({ map: tex, roughness: 1, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0.6 })); wall.position.set(0, 60, -150); S.add(wall);
  const tower = new THREE.Mesh(new THREE.BoxGeometry(6, 30, 6), new THREE.MeshStandardNodeMaterial({ color: 0xf2f2f2, roughness: 0.5 })); tower.position.set(0, 15, 0); S.add(tower);
  E.setSun([0.4, 0.8, 0.3], [4, 4, 4]); E.expo.value = 0.6;
  const cam = (a) => ({ pos: [Math.sin(a) * 60, 14, Math.cos(a) * 60], target: [0, 14, 0], fov: 45 * Math.PI / 180, near: 0.5, far: 5000, shadowSplits: [80, 300, 1200] });
  const read = async () => { const rt = E.traaNode._resolveRenderTarget; const px = await E.renderer.readRenderTargetPixelsAsync(rt, 0, 0, rt.width, rt.height); (out.read = out.read || []).push([px.length, rt.width, rt.height, E.renderer.info.render.calls]); const f = new Float32Array(px.length); for (let i = 0; i < px.length; i++) f[i] = THREE.DataUtils.fromHalfFloat(px[i]); return f; };
  // one render per animation frame: three runs the passes' FRAME-type updates (pass renders, TRAA) once per frame id,
  // which its animation loop advances
  const frame = async (c) => { E.setCamera(c, innerWidth, innerHeight); E.render(); await new Promise(r => requestAnimationFrame(r)); };
  const a0 = 0.35; for (let i = 0; i < 16; i++) await frame(cam(a0));
  let a = a0; for (let i = 0; i < 12; i++) { a += 3 * Math.PI / 180; await frame(cam(a)); }
  const moving = await read();
  for (let i = 0; i < 24; i++) await frame(cam(a));
  const settled = await read();
  const d = []; for (let i = 0; i < moving.length; i += 4) d.push((Math.abs(moving[i] - settled[i]) + Math.abs(moving[i + 1] - settled[i + 1]) + Math.abs(moving[i + 2] - settled[i + 2])) / 3);
  d.sort((x, y) => y - x); const top = d.slice(0, Math.max(1, Math.round(d.length * 0.01)));
  out.meanTop1pct = +(top.reduce((s, v) => s + v, 0) / top.length).toFixed(4); out.meanAll = +(d.reduce((s, v) => s + v, 0) / d.length).toFixed(5); out.px = d.length;
  out.pxOver0_05 = d.filter(v => v > 0.05).length; out.backend = E.backend; out.reversed = E.reversed;
  out.rt = [E.traaNode._resolveRenderTarget.width, E.traaNode._resolveRenderTarget.height, E.traaNode._historyRenderTarget.width]; out.scene = E.scenePass.renderTarget ? [E.scenePass.renderTarget.width, E.scenePass.renderTarget.height] : null; out.draw = E.renderer.getDrawingBufferSize(new THREE.Vector2()).toArray();
  out.ok = true;
} catch (e) { out.err = String(e && e.stack || e); }
window.__probe = out;
