// P3 test page: renders the traffic engine's drawn aircraft (GA placeholders) on P2's world, for visual checks of the
// placeholders, parking poses and ground positions. Reuses P2's renderer / world / env exactly as dev/world.js does.
import { initGL } from '../../js/gl.js';
import { Renderer } from '../../js/renderer.js';
import { Scene } from '../../js/scene.js';
import { buildSite } from '../../js/world/site.js';
import { buildHwdWorld } from '../../js/live/world.js';
import { AppEnv } from '../../js/env/app_env.js';
import { applyEnvToRenderer } from '../../js/env/render_env.js';
import { HWD_AIRPORT } from '../../data/hwd_airport.js';
import { TAXIGRAPH } from '../../data/hwd_taxigraph.js';
import { parsePayload } from '../../js/live/feed.js';
import { Traffic, phaseLabel } from '../../js/live/traffic.js';
import { ParkingModel } from '../../js/live/parking.js';
import { GroundPhysics } from '../../js/live/ground.js';
import { AircraftViews } from '../../js/live/aircraft.js';
import { GaAircraft } from '../../js/aircraft/placeholder.js';
import { gaDims } from '../../js/aircraft/ga_dims.js';

const q = new URLSearchParams(location.search), hud = document.getElementById('hud'), canvas = document.getElementById('c');
const W = Math.round(innerWidth * (+(q.get('scale') || 1))), H = Math.round(innerHeight * (+(q.get('scale') || 1))); canvas.width = W; canvas.height = H;
window.ANISO = 4;
initGL(canvas);
const R = new Renderer(W, H, { msaa: 2, shadowRes: 2048 });
const site = buildSite(HWD_AIRPORT);
const world = buildHwdWorld(R, HWD_AIRPORT, { site, quality: 'low', naip: true, log: () => {} });
const scene = new Scene(R, world); scene.staticLights.push(world.staticSprites);
const D2R = Math.PI / 180;
let post = { exposure: 0.45, shutter: 0, bloom: 0.01, vignette: 0.15, grain: 0.0, sat: 1.0 };
const parking = new ParkingModel({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site });
const traffic = new Traffic({ airport: HWD_AIRPORT, taxigraph: TAXIGRAPH, site, parking, persist: false });
const physics = new GroundPhysics({ site, net: traffic.net, parking });
const views = new AircraftViews(scene, { quality: 'high' });
const gy = (x, z) => site.groundY(x, z);
const cam = { target: [0, 12, 0], yaw: 30, pitch: 30, dist: 300, fov: 40 };
function camera() {
  const dir = [Math.sin(cam.yaw * D2R) * Math.cos(cam.pitch * D2R), -Math.sin(cam.pitch * D2R), -Math.cos(cam.yaw * D2R) * Math.cos(cam.pitch * D2R)];
  const pos = [cam.target[0] - dir[0] * cam.dist, cam.target[1] - dir[1] * cam.dist, cam.target[2] - dir[2] * cam.dist];
  return { pos, dir, up: [0, 1, 0], fov: cam.fov * D2R, near: Math.max(0.3, cam.dist * 0.004), split: Math.max(300, cam.dist * 3.5), far: 40000, shadowSplits: [Math.max(40, cam.dist * 0.8), Math.max(300, cam.dist * 2.5), 2500] };
}
function render(t = 1000) { const C = camera(); const fr = scene.frame(t, C.pos); R.render(fr, C, t / 1000, post); scene.commit(); R.present(canvas.width, canvas.height); }
async function shot(v) {
  if (v) Object.assign(cam, v);
  for (let i = 0; i < 2; i++) render(1000 + i * 16);
  const px = R.readPixels(); const c2 = document.createElement('canvas'); c2.width = R.W; c2.height = R.H;
  const cx = c2.getContext('2d'); const id = cx.createImageData(R.W, R.H);
  for (let y = 0; y < R.H; y++) id.data.set(px.subarray((R.H - 1 - y) * R.W * 4, (R.H - y) * R.W * 4), y * R.W * 4);
  cx.putImageData(id, 0, 0); return c2.toDataURL('image/png');
}
// a static line-up of every placeholder class on the Green Ramp (shape check, not traffic)
const lineup = [];
function showLineup(on) {
  for (const a of lineup) scene.remove(a); lineup.length = 0; if (!on) return;
  const types = [['C172', 'A1'], ['CH7A', 'A1'], ['P28A', 'A1'], ['BE55', 'A1'], ['PC12', 'A1'], ['SF50', 'A1'], ['C56X', 'A2'], ['GLF5', 'A3'], ['R44', 'A7'], ['EC45', 'A7']];
  const base = [-140, -390], along = [Math.sin(30 * D2R), -Math.cos(30 * D2R)], perp = [-along[1], along[0]];
  let s = 0;
  for (const [t, c] of types) { const T = gaDims(t, c); s += Math.max(T.span, T.rotor || 0) / 2 + 4;
    const x = base[0] + perp[0] * s, z = base[1] + perp[1] * s; const a = new GaAircraft(T); a.pos = [x, gy(x, z), z]; a.fwd = [along[0], 0, along[1]]; scene.add(a); lineup.push(a);
    s += Math.max(T.span, T.rotor || 0) / 2 + 4; }
  return { centre: [base[0] + perp[0] * s / 2, base[1] + perp[1] * s / 2], len: s, each: lineup.map((a, i) => ({ type: types[i][0], pos: a.pos, L: a.T.L, span: Math.max(a.T.span, a.T.rotor || 0) })) };
}
async function loadPack(url) {
  const r = await fetch(url); const buf = new Uint8Array(await r.arrayBuffer());
  const txt = buf[0] === 0x1f ? await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text() : new TextDecoder().decode(buf);
  return JSON.parse(txt);
}
// run the engine headless in the page up to `min` minutes into the replay window (display time = window start + min)
async function runTo(pack, min) {
  const st = {}; const expand = (p) => ({ now: p.now, dataNow: p.dataNow, ac: p.d.map(r => { const a = st[r[0]] || (st[r[0]] = { hex: r[0] }); for (const k in r[1]) a[k] = r[1][k]; if (r[2]) for (const k of r[2]) delete a[k]; return { ...a }; }) });
  const L = pack.lookahead_s; traffic.setLookahead(L);
  const t0 = pack.from + L, t1 = t0 + min * 60; let ei = 0;
  for (let t = t0; t <= t1; t += 0.1) {
    while (ei < pack.events.length && pack.events[ei].T <= t) { const rr = t === t0 ? t0 * 1000 : pack.events[ei].T * 1000; traffic.ingest(parsePayload(expand(pack.events[ei].p), rr), rr); ei++; }
    traffic.update(t * 1000, 0.1); physics.resolve(traffic, 0.1);
  }
  views.sync(traffic, t1 * 1000, { dt: 0.1 });
  return t1;
}
function tracks() { return [...traffic.tracks.values()].filter(tr => tr.disp.valid && tr.inView && !tr.hidden && tr.disp.alpha > 0.5).map(tr => ({ type: tr.info.icao, cls: tr.dims && tr.dims.cls, phase: tr.phase, label: phaseLabel(tr), x: +tr.disp.x.toFixed(1), y: +tr.disp.y.toFixed(1), z: +tr.disp.z.toFixed(1), hdg: +tr.disp.hdg.toFixed(0), ground: tr.disp.ground, gs: +tr.disp.gs.toFixed(1), spot: tr.park && tr.park.spotId })); }
const env = new AppEnv({ mode: 'live', search: '?t=2026-11-08T20:30:00Z', station: 'KHWD' });
env.setReports([{ rawOb: 'METAR KHWD 082054Z 29008KT 10SM FEW060 19/12 A2974', obsTime: Date.parse('2026-11-08T20:54:00Z') / 1000 }]);
function applyEnv(force) { const E = env.update(Date.now()); const r = applyEnvToRenderer(R, world, E, { quality: 'low', force }); post.exposure = r.exposure; }
applyEnv(true);
window.HWDT = { R, scene, world, site, traffic, views, cam, render, shot, loadPack, runTo, tracks, showLineup, gy };
world.ready.then(() => { window.__trafficReady = true; hud.textContent = ''; }).catch(e => { window.__trafficError = String(e); hud.textContent = 'error ' + e; });
