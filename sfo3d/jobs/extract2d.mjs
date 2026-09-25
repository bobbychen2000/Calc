// 2-D extraction of everything the live 3-D app places on the ground plane, for the drawing / deviation / clearance
// tools in tools/drawing/.   Run:  SOFTGL=1 node livetest.mjs jobs/extract2d.mjs
// Output: out/draw/scene2d.json (+ out/draw/meshes.bin, out/draw/pave_*.png)
//
// Everything is taken from the running app (window.SFO: world, gateSys, scene, traffic, physics) or produced by calling
// the app's own builder functions with a recording geometry sink. Where a value lives in a module-private constant or
// function (REF_TYPE, doorOf, CLASS_MAX, STRUCT_H*, Ribbons, centerlineBack, the sign builder class, buildEMAS,
// RUNWAY_SIGNS, buildVehicleMeshes' Geo), the module source is re-imported as a blob with an extra `export {…}` line
// (relative imports rewritten to the same absolute URLs, so the shared modules are the very instances the app uses).
// Nothing is re-typed by hand except where noted in meta.replicated.
//
// World frame: x east, z south, y up (m), origin ARP; ground at GROUND_Y. Airport grid s/t via js/geo.js.
import fs from 'fs'; import path from 'path'; import crypto from 'crypto'; import { execSync } from 'child_process';

export default async ({ page, base }) => {
  const OUTD = path.resolve(process.env.DRAW_OUT || 'out/draw');
  fs.mkdirSync(OUTD, { recursive: true });
  await page.goto(base + 'live.html?mode=snapshot');
  // a module that 404s while another process rewrites the tree leaves the page waiting forever: name it, time out
  page.on('response', r => { if (r.status() >= 400 && r.url().startsWith(base)) console.log('HTTP', r.status(), r.url()); });
  await page.waitForFunction(() => window.__sfoReady || window.__sfoError, null, { timeout: +(process.env.LOAD_TIMEOUT_MS || 1500000) });
  const err = await page.evaluate(() => window.__sfoError); if (err) throw new Error(err);
  const tLoad = Date.now();
  // every file the app loaded (performance resource entries), hashed on disk now and again at the end: the drawing
  // tools compare these hashes with the working tree (tools/drawing/common.py stale_inputs) and refuse stale scenes
  const ROOTD = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');   // repo root (this file is jobs/extract2d.mjs)
  const sha = (f) => { try { return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 16); } catch (e) { return null; } };
  const loaded = async () => (await page.evaluate(() => performance.getEntriesByType('resource').map(e => e.name).concat([location.href])))
    .filter(u => u.startsWith(base)).map(u => decodeURIComponent(new URL(u).pathname.slice(1)).split('?')[0]).filter(p => p && !p.startsWith('api/'));
  const hashInputs = (list) => Object.fromEntries([...new Set(list)].sort().map(p => [p, sha(path.join(ROOTD, p))]));
  const inputs0 = hashInputs(await loaded());
  // let traffic + ground physics run a few frames, then freeze the render loop (a static, consistent state; llvmpipe
  // frames would otherwise starve the extraction of GPU time)
  await page.evaluate(async () => {
    await Promise.all(SFO.scene.aircraft.map(a => a.ready));
    // stop every timer (the snapshot re-ingest every 90 s, UI refresh), then let a few frames of traffic.update() +
    // physics.resolve() run on the final state
    const hi = setTimeout(() => { }, 0); for (let i = 1; i <= hi; i++) { clearInterval(i); clearTimeout(i); }
    // wait: >= 15 frames and >= 12 s (traffic.js displays positions DELAY_MS = 7 s behind the reports) and every
    // track with reports displayable (disp.valid), max 240 s
    const f0 = SFO.physics.frame; const t0 = performance.now();
    const ready = () => SFO.physics.frame >= f0 + 15 && performance.now() - t0 > 12000 && [...SFO.traffic.tracks.values()].every(t => !t.fixes.length || t.disp.valid);
    while (!ready() && performance.now() - t0 < 240000) await new Promise(r => setTimeout(r, 250));
    console.log('valid tracks', [...SFO.traffic.tracks.values()].filter(t => t.disp.valid).length, 'of', SFO.traffic.tracks.size, 'after', ((performance.now() - t0) / 1000).toFixed(1), 's');
    window.requestAnimationFrame = () => 0; await new Promise(r => setTimeout(r, 1500));
    console.log('frozen after', SFO.physics.frame, 'physics frames');
  });
  let git = null, gitHead = null, gitDirty = null; try { gitHead = execSync('git rev-parse --short HEAD', { cwd: ROOTD }).toString().trim(); gitDirty = execSync('git status --porcelain js data live.html', { cwd: ROOTD }).toString().split('\n').filter(l => l.trim()).map(l => l.slice(3)); git = gitHead + (gitDirty.length ? '+dirty' : ''); } catch (e) { }

  const res = await page.evaluate(async () => {
    const abs = (p) => new URL(p, location.href).href; const T00 = performance.now(); const say = (m) => console.log('[extract] ' + m + ' @' + ((performance.now() - T00) / 1000).toFixed(1) + 's');
    // ------------------------------------------------ module access (shared instances) and private internals
    const mod = async (p) => import(abs(p));
    const internals = async (p, names, patches = []) => {
      const url = abs(p); let src = await (await fetch(url)).text();
      src = src.replace(/(\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)(['"])(\.{1,2}\/[^'"]+)\2/g, (m, a, q, s) => a + q + new URL(s, url).href + q);
      for (const [re, rep] of patches) { const before = src; src = src.replace(re, rep); if (src === before) throw new Error('patch did not apply in ' + p + ': ' + re); }
      // names the module already exports (e.g. gates.js doorOf) must not be exported twice
      const extra = names.filter(n => !new RegExp('export\\s+(const|let|var|function|class|async\\s+function)\\s+' + n + '\\b|export\\s*\\{[^}]*\\b' + n + '\\b').test(src));
      if (extra.length) src += '\nexport { ' + extra.join(', ') + ' };\n';
      return import(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
    };
    const geo = await mod('js/geo.js'), airportM = await mod('js/live/airport.js'), airfield = await mod('js/world/airfield.js');
    const typesM = await mod('js/aircraft/types.js'), gatesM = await mod('js/live/gates.js'), trafficM = await mod('js/live/traffic.js');
    const geomM = await mod('js/geom.js'), mathM = await mod('js/math.js'), itemsM = await mod('js/live/items.js'), terminalsM = await mod('js/live/terminals.js');
    const acM = await mod('js/live/aircraft.js'), modelM = await mod('js/aircraft/model.js'), manifest = await mod('data/models/manifest.js');
    const D = { AIRPORT: (await mod('data/sfo_airport.js')).AIRPORT, DETAILS: (await mod('data/sfo_details.js')).DETAILS, BUILDINGS: (await mod('data/sfo_buildings.js')).BUILDINGS,
      STANDS: (await mod('data/sfo_stands.js')).STANDS, PAINT: (await mod('data/sfo_paint.js')).PAINT, PAVEMENT: (await mod('data/sfo_pavement.js')).PAVEMENT };
    const gatesI = await internals('js/live/gates.js', ['REF_TYPE', 'doorOf', 'stW', 'stD']);
    const airportI = await internals('js/live/airport.js', ['CLASS_MAX', 'HALL_H', 'STRUCT_H', 'STRUCT_H_BY_NAME']);
    const markI = await internals('js/live/markings.js', ['Ribbons', 'centerlineBack']);
    const signI = await internals('js/live/signs.js', ['G', 'locName']);
    const worldI = await internals('js/live/world.js', ['buildEMAS', 'gateWorld']);
    const appI = await internals('js/live/app.js', ['RUNWAY_SIGNS', 'QUALITY', 'pickQuality']);
    // vehicle meshes: keep the CPU geometry (Mesh stubbed in the copy)
    const vehI = await internals('js/world/gates.js', [], [[/import \{ Mesh \} from '[^']+';/, 'const Mesh = class { constructor(d) { this.data = d; } };']]);
    const terminalsI = await internals('js/live/terminals.js', ['greatHall']);
    // builders that make their own Geo: patched copies that build with the recording sink (globalThis.__RecGeo)
    const recPatch = [[/const g = new Geo\(\);/, 'const g = new (globalThis.__RecGeo || Geo)(); globalThis.__lastGeo = g;']];
    const itemsI = await internals('js/live/items.js', ['buildMasts'], recPatch);
    const lightsI = await internals('js/anim/lights.js', ['buildAirfieldLights', 'buildPierGeometry'], recPatch);
    const animTrafficM = await mod('js/anim/traffic.js'), liveLightsM = await mod('js/live/lights.js');
    say('modules loaded'); const { Geo } = geomM; const { m4 } = mathM; const G = geo.GROUND_Y;
    const SFO = window.SFO; const world = SFO.world, gateSys = SFO.gateSys, traffic = SFO.traffic;

    // ------------------------------------------------ binary mesh pack (Float32 xyz + Uint32 idx per entry)
    const bin = []; let binLen = 0;
    const pack = (pos, idx) => { const p = new Float32Array(pos), i = new Uint32Array(idx); const e = { off: binLen, nv: p.length / 3, ni: i.length }; bin.push(new Uint8Array(p.buffer.slice(0)), new Uint8Array(i.buffer.slice(0))); binLen += p.byteLength + i.byteLength; return e; };
    const b64 = (u8) => { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };

    // ------------------------------------------------ recording geometry sink: every box / cylinder / lathe call and
    // every loose vertex run becomes a primitive with its world vertices (for exact plan hulls and height ranges)
    class RecGeo extends Geo {
      constructor() { super(); this.prims = []; this.cur = null; }
      open(kind, info) { const p = { kind, ...info, v: [] }; this.prims.push(p); return p; }
      vert(p, n, c, e, uv) {
        let P = this.cur; if (!P) { const last = this.prims[this.prims.length - 1]; P = last && last.kind === 'loose' && last.open ? last : this.open('loose', { open: true, col: c }); }
        P.v.push(p[0], p[1], p[2]); return super.vert(p, n, c, e, uv);
      }
      _wrap(kind, info, fn) { const lastL = this.prims[this.prims.length - 1]; if (lastL && lastL.kind === 'loose') lastL.open = false; if (this.cur) return fn(); this.cur = this.open(kind, info); try { return fn(); } finally { this.cur = null; } }
      box(min, max, c, e, M, faces) {
        // exact solid: parallelepiped o + a e1 + b e2 + c e3 (a, b, c in [0, 1]) -> per-point vertical extent in audit.py
        const X = (p) => M ? mathM.m4.xform(M, p) : p; const o = X([min[0], min[1], min[2]]);
        const d = (p) => { const q = X(p); return [q[0] - o[0], q[1] - o[1], q[2] - o[2]]; };
        const pp = { o, E: [d([max[0], min[1], min[2]]), d([min[0], max[1], min[2]]), d([min[0], min[1], max[2]])] };
        return this._wrap('box', { min, max, col: c, pp }, () => super.box(min, max, c, e, M, faces));
      }
      cylinder(r, h, seg, c, e, M, caps) { return this._wrap('cyl', { r, h, col: c }, () => super.cylinder(r, h, seg, c, e, M, caps)); }
      lathe(profile, seg, c, e, M, capTop) { return this._wrap('lathe', { rmax: Math.max(...profile.map(q => q[0])), col: c }, () => super.lathe(profile, seg, c, e, M, capTop)); }
    }
    const hull2 = (v) => { // plan convex hull of xyz vertex list
      const P = []; for (let i = 0; i < v.length; i += 3) P.push([v[i], v[i + 2]]);
      P.sort((a, b) => a[0] - b[0] || a[1] - b[1]); if (P.length < 3) return P;
      const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
      const lo = [], up = []; for (const p of P) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 1e-9) lo.pop(); lo.push(p); }
      for (let i = P.length - 1; i >= 0; i--) { const p = P[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 1e-9) up.pop(); up.push(p); }
      return lo.slice(0, -1).concat(up.slice(0, -1)).map(q => [+q[0].toFixed(3), +q[1].toFixed(3)]);
    };
    const yr = (v) => { let a = 1e9, b = -1e9; for (let i = 1; i < v.length; i += 3) { a = Math.min(a, v[i]); b = Math.max(b, v[i]); } return [+a.toFixed(3), +b.toFixed(3)]; };
    const ppOut = (pp) => pp ? { o: rnd(pp.o, 4), E: rnd(pp.E, 5) } : null;
    const primOut = (p, name) => ({ part: name, kind: p.kind, hull: hull2(p.v), y: yr(p.v), r: p.r ?? p.rmax, col: Array.isArray(p.col) ? p.col.slice(0, 3).map(x => +x.toFixed(3)) : null, pp: p.pp ? [ppOut(p.pp)] : null });
    // gates.js tube(): loose sides P(0,hw,0) P(L,hw,0) P(L,hw,h) P(0,hw,h), P(0,-hw,0) ... -> the tube's parallelepiped
    const tubePP = (v) => { if (v.length < 24) return null; const V = (i) => [v[i * 3], v[i * 3 + 1], v[i * 3 + 2]]; const s = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
      const v0 = V(0), v1 = V(1), v3 = V(3), v4 = V(4); return { o: v4, E: [s(v1, v0), s(v0, v4), s(v3, v0)] }; };
    const rnd = (a, k = 3) => Array.isArray(a) ? a.map(x => rnd(x, k)) : (typeof a === 'number' ? +a.toFixed(k) : a);
    const W2 = (p) => [+p[0].toFixed(3), +p[2].toFixed(3)];
    const stWorld = (st) => { const w = geo.stToWorld(st[0], st[1], 0); return [+w[0].toFixed(3), +w[2].toFixed(3)]; };
    const stRing = (pts) => pts.map(stWorld);
    const same = (a, b) => a.length === b.length && a.every((x, i) => Math.abs(x[0] - b[i][0]) < 1e-6 && Math.abs(x[1] - b[i][1]) < 1e-6);
    const replicated = [];

    // ------------------------------------------------ meta
    const Q = appI.pickQuality('auto');
    const meta = {
      generated: new Date().toISOString(), url: location.href, userAgent: navigator.userAgent, deviceMemory: navigator.deviceMemory,
      quality: Q, groundY: G, frame: 'world x east, z south, y up (m), origin = ARP (js/geo.js); airport grid s/t: s = x*V[0] - z*V[1] ... see stBasis',
      frameId: geo.FRAME_ID || 'equirect-v1', datum: geo.DATUM || null, mPerDeg: { lat: geo.M_PER_DEG_LAT ?? null, lon: geo.M_PER_DEG_LON ?? null },
      probe: { arpWorld: geo.llToWorld(geo.ARP.lat, geo.ARP.lon), end10L: (() => { const e = geo.RWY_ENDS['10L']; return geo.llToWorld(e.lat, e.lon); })(), end28R: (() => { const e = geo.RWY_ENDS['28R']; return geo.llToWorld(e.lat, e.lon); })() },
      stBasis: { V: geo.V, U: geo.U, note: 'e = s*V0 + t*U0, n = s*V1 + t*U1, x = e, z = -n' },
      aptRect: airfield.APT_RECT, ARP: geo.ARP, runwayWidth: airfield.RWY_W,
    };

    // ------------------------------------------------ types / classes (runtime values: seatType() may have changed Hc)
    const types = {}; for (const k in typesM.TYPES) { if (k === 'narrow' || k === 'wide' || k === 'mid') continue; types[k] = JSON.parse(JSON.stringify(typesM.TYPES[k])); }
    const classMax = airportI.CLASS_MAX, refType = gatesI.REF_TYPE;

    // ------------------------------------------------ buildings (as built) + footprints with heights
    const Bm = airportM.buildLiveBuildings(D.AIRPORT, D.BUILDINGS);
    const buildingMesh = pack(Bm.geo.pos, Bm.geo.idx);
    const buildings = [];
    const BP = D.BUILDINGS; const itbPart = BP.parts.filter(p => p.kind === 'hall' && /International/.test(p.name)).sort((a, b) => b.area - a.area)[0];
    BP.complex.forEach((r, i) => buildings.push({ id: 'complex' + i, kind: 'apron-level', name: 'Terminal complex ramp level', rings: [r], y0: G, y1: G + 5.0, src: 'sfo_buildings.complex (terminals.js buildTerminals: walls G..G+5)' }));
    BP.parts.forEach((p, i) => {
      if (p.kind === 'walkway') buildings.push({ id: 'part' + i, kind: 'walkway', name: p.name, rings: p.rings, y0: G + (p.y0 || 6), y1: G + p.h, src: 'sfo_buildings.parts (elevated walkway)' });
      else buildings.push({ id: 'part' + i, kind: p.kind, name: p.name, rings: p.rings, y0: G, y1: (p === itbPart ? G + 16 : G + p.h) + 0.6, roofY: p === itbPart ? G + 16 : G + p.h, src: 'sfo_buildings.parts (' + p.kind + '; +0.6 m parapet)' });
    });
    const tower = D.AIRPORT.structures.find(s => s.kind === 'atc'); const seen = new Set();
    D.AIRPORT.structures.forEach((s, i) => {
      if (s.kind === 'atc') return;
      if (s.kind === 'rail') { for (const poly of s.polys) buildings.push({ id: 'struct' + i, kind: 'rail', name: s.name, rings: poly, y0: G + 9.0, y1: G + 10.6, src: 'AirTrain guideway deck (airport.js)' }); return; }
      const key = s.name.replace(/\s+/g, ' ').toLowerCase().replace(/garaga/, 'garage');
      let dup = false; if (s.kind === 'airtrain') { if (seen.has(key)) dup = true; seen.add(key); }
      const h = airportI.STRUCT_H_BY_NAME[s.name] || airportI.STRUCT_H[s.kind] || 12;
      for (const poly of s.polys) buildings.push({ id: 'struct' + i, kind: s.kind, name: s.name, rings: poly, y0: s.kind === 'airtrain' ? G : G, y1: G + h, notBuilt: dup, src: 'sfo_airport.structures (airport.js STRUCT_H' + (airportI.STRUCT_H_BY_NAME[s.name] ? '_BY_NAME' : '') + ')' });
    });
    // control tower: base building + lathe shaft/cab, recorded
    let towerOut = null;
    if (tower) { const g = new RecGeo(); const T = terminalsM.buildTower(g, tower.polys[0][0]); towerOut = { footprint: tower.polys[0], cab: rnd(T.cab), top: +T.top.toFixed(2), prims: g.prims.map((p, i) => primOut(p, 'tower' + i)).filter(p => p.hull.length >= 3) }; buildings.push({ id: 'tower', kind: 'atc', name: tower.name, rings: tower.polys[0], y0: G, y1: G + 14, src: 'tower base (terminals.js buildTower)' }); }
    // ITB great hall roof (wing roof overhang), recorded from terminals.js greatHall
    let itbRoof = null;
    if (itbPart) { const g = new RecGeo(); terminalsI.greatHall(g, itbPart); const v = g.prims.flatMap(p => p.v); itbRoof = { hull: hull2(v), y: yr(v), note: 'terminals.js greatHall(): roof + hall + columns (convex hull of all vertices)' }; }

    say('buildings'); // ------------------------------------------------ runways, thresholds, end zones
    const RW = airfield.RWY.map((r, i) => {
      const hw = airfield.RWY_W / 2;
      const P = (u, v) => stWorld(r.axis === 0 ? [u, r.c + v] : [r.c + v, u]);
      const dirW = (() => { const a = P(r.a0, 0), b = P(r.a1, 0); const l = Math.hypot(b[0] - a[0], b[1] - a[1]); return [(b[0] - a[0]) / l, (b[1] - a[1]) / l]; })();
      return { i, name: r.name, axis: r.axis, c: r.c, a0: r.a0, a1: r.a1, disp0: r.disp0, disp1: r.disp1, width: airfield.RWY_W,
        corners: [P(r.a0, -hw), P(r.a1, -hw), P(r.a1, hw), P(r.a0, hw)], centre: [P(r.a0, 0), P(r.a1, 0)], dir: rnd(dirW, 6),
        ends: [{ name: r.name[0], end: P(r.a0, 0), thr: P(r.a0 + r.disp0, 0), disp: r.disp0, inward: rnd(dirW, 6) }, { name: r.name[1], end: P(r.a1, 0), thr: P(r.a1 - r.disp1, 0), disp: r.disp1, inward: rnd([-dirW[0], -dirW[1]], 6) }],
        shoulderPaved: { hw: hw + 7.5, u0: r.a0 - 60, u1: r.axis === 0 ? r.a1 : r.a1 + 60, poly: r.axis === 0 ? [P(r.a0 - 60, -hw - 7.5), P(r.a1, -hw - 7.5), P(r.a1, hw + 7.5), P(r.a0 - 60, hw + 7.5)] : [P(r.a0 - 60, -hw - 7.5), P(r.a1 + 60, -hw - 7.5), P(r.a1 + 60, hw + 7.5), P(r.a0 - 60, hw + 7.5)] },
        paint: { edgeStripe: [29.27, 30.18], thrStripes: { x0: 6.1, x1: 51.8, lat0: 1.75, pitch: 3.5, width: 1.75, n: 8 }, dispBar: [-3.05, 0], centreline: { start: 120, dash: 36.58, period: 60.96, hw: 0.45 }, aiming: { x0: 310.9, x1: 356.6, y0: 11.0, y1: 20.1 }, src: 'js/shaders/ground.js endMarkings()/runwayAt() constants (replicated)' } };
    });
    replicated.push('runway paint geometry (edge stripes, threshold stripes, displaced-threshold bar, centreline dashes) copied from js/shaders/ground.js (GLSL, not callable); meta.paintCheck = the GLSL still contains each copied constant');
    { const glsl = await (await fetch(abs('js/shaders/ground.js'))).text();
      meta.paintCheck = Object.fromEntries(['band(abs(dv), 29.27, 30.18', 'band(xt, 6.1, 51.8', 'band(f, 0.0, 1.75', '(ay - 1.75) / 3.5', 'band(xt, -3.05, 0.0', 'band(xt, 310.9, 356.6, fw) * band(ay, 11.0, 20.1', 'band(fract(xc / 60.96) * 60.96, 0.0, 36.58', '120.0 + info.x'].map(k => [k, glsl.includes(k)])); }
    const faa = geo.RUNWAYS.map(r => ({ ends: r.ends, a: [r.a[0], -r.a[1]], b: [r.b[0], -r.b[1]], width: r.width, length: r.length, dispA: r.dispA, dispB: r.dispB }));
    const endZones = airportM.endZoneRects().map(z => ({ ...z, rectW: stRing(z.rect), kind: z.type === 2 ? 'EMAS' : 'blastpad', end: airfield.RWY[z.rw].name[z.end] }));
    // EMAS beds: one hull per bed (the bed faces are emitted as quads; group vertices by nearest end zone)
    const emasBeds = []; { const E = worldI.buildEMAS(); const pos = E.pos; const beds = endZones.filter(z => z.type === 2).map(z => ({ end: z.end, v: [] }));
      const cent = endZones.filter(z => z.type === 2).map(z => { const r = z.rectW; return [(r[0][0] + r[2][0]) / 2, (r[0][1] + r[2][1]) / 2]; });
      for (let i = 0; i < pos.length; i += 3) { let bi = 0, bd = 1e9; cent.forEach((c, k) => { const d = Math.hypot(pos[i] - c[0], pos[i + 2] - c[1]); if (d < bd) { bd = d; bi = k; } }); beds[bi].v.push(pos[i], pos[i + 1], pos[i + 2]); }
      for (const b of beds) emasBeds.push({ end: b.end, hull: hull2(b.v), y: yr(b.v) }); }

    // ------------------------------------------------ pavement (vector sources + the exact raster the app uses)
    const gatesW = world.gates;
    const pave = {}; const rasterOut = {}; const mapPaved = {};
    for (const res of [1.0, Q.mapRes, 1.6].filter((v, i, a) => a.indexOf(v) === i)) {
      const M = airportM.paintAirportMapReal(D.AIRPORT, gatesW, res, D.DETAILS, { paint: D.PAINT, pavement: D.PAVEMENT, endZones: airportM.endZoneRects() }); mapPaved[res] = M.paved;
      const cv = document.createElement('canvas'); cv.width = M.w; cv.height = M.h; const cx = cv.getContext('2d'); const im = cx.createImageData(M.w, M.h);
      for (let i = 0; i < M.w * M.h; i++) { im.data[i * 4] = M.data[i * 4]; im.data[i * 4 + 1] = M.data[i * 4 + 1]; im.data[i * 4 + 2] = M.paint ? M.paint[i * 4] : 0; im.data[i * 4 + 3] = 255; }
      cx.putImageData(im, 0, 0); rasterOut['pave_' + res.toFixed(2)] = { png: cv.toDataURL('image/png'), w: M.w, h: M.h, res, channels: 'R = paved (physics + ground shader), G = concrete, B = green paint', mapping: 'pixel column i, row j <-> s = s0 + (i + 0.5) res, t = t0 + h - (j + 0.5) res' };
      cv.width = cv.height = 1;
    }
    say('pavement rasters'); pave.apron = D.DETAILS.apron; pave.patches = D.DETAILS.patches; pave.extra = D.PAVEMENT.polys; pave.extraConc = D.PAVEMENT.conc; pave.paint = D.PAINT.polys;
    pave.taxiways = D.AIRPORT.taxiways; pave.runwayPolys = D.AIRPORT.runways; pave.terminalComplex = D.AIRPORT.terminalComplex;
    pave.landside = airfield.landside().map(l => ({ kind: l.kind, w: l.w, pts: stRing(l.pts) }));
    pave.standEnvelopes = gatesW.filter(g => g.bridge).map(g => ({ stand: g.name, poly: stRing(airportM.standEnvelopeST(g, 6, 6, 14)) }));
    pave.remoteDiscs = gatesW.filter(g => g.remote).map(g => ({ stand: g.name, c: [g.world.x, g.world.z], r: 40 }));

    // ------------------------------------------------ markings: record every ribbon the app builds
    const rec = []; let tag = null;
    markI.Ribbons.prototype.line = function (pts, hw, color, alpha = 1, offset = 0, dash = null) { rec.push({ fn: tag, pts: pts.map(p => rnd(p, 3)), hw, color: rnd(color), alpha, offset: +offset.toFixed(4), dash }); };
    markI.Ribbons.prototype.mesh = function () { return null; };
    tag = 'buildMarkings'; markI.buildMarkings(D.DETAILS);
    tag = 'buildStandMarks'; const gw = [geo.V[0], -geo.V[1]]; markI.buildStandMarks(gatesW.map(g => ({ ...g, w: worldI.gateWorld(g) })), D.STANDS.redBoxes || [], gw);
    const IN = 0.0254, FT = 0.3048; const eq = (a, b) => Math.abs(a - b) < 1e-6;
    const clsMark = (r) => {
      const yel = r.color[0] > 0.8 && r.color[2] < 0.1, red = r.color[0] < 0.6 && r.color[1] < 0.1, wht = r.color[2] > 0.8;
      if (r.fn === 'buildStandMarks') { if (red) return 'redbox'; if (eq(r.hw, 3 * IN)) return 'leadin'; return 'stopbar'; }
      if (wht) return r.dash ? 'road-centre' : 'road-edge';
      if (eq(r.hw, 6 * IN)) return r.dash ? 'hold-dashed' : 'hold-solid';
      if (r.dash) return 'enhanced-centreline';
      if (Math.abs(Math.abs(r.offset) - 4.5 * IN) < 1e-6) return 'taxiway-edge';
      return 'taxiway-centreline';
    };
    for (const r of rec) r.kind = clsMark(r);
    const markings = { ribbons: rec, holds: D.DETAILS.holds, roads: D.DETAILS.roads, note: 'ribbons recorded from markings.js buildMarkings()/buildStandMarks() (pts = polyline, drawn offset `offset` m to the right of travel, half width hw; dash = [period, on])' };

    say('markings'); // ------------------------------------------------ signs (hold signs, location signs, distance remaining): recorded boxes
    const signBoxes = []; let signQuads = 0;
    signI.G.prototype.box = function (c, u, w, h, d, y0) { signBoxes.push({ c: rnd(c), u: rnd(u, 5), w: +w.toFixed(3), h: +h.toFixed(3), d: +d.toFixed(3), y0: +y0.toFixed(3) }); };
    signI.G.prototype.quad = function () { signQuads++; };
    signI.G.prototype.mesh = function () { return null; };
    signI.buildSigns(D.DETAILS, appI.RUNWAY_SIGNS());
    const signs = signBoxes.filter(b => b.w > 0.2).map(b => ({ ...b, kind: b.h > 0.9 ? 'distance-remaining' : 'hold/location' }));
    const signLegs = signBoxes.filter(b => b.w <= 0.2).length;

    // ------------------------------------------------ masts (world.js keeps masts outside stand envelopes)
    const mastsAll = D.DETAILS.masts || [];
    globalThis.__RecGeo = RecGeo;
    const masts = mastsAll.map(([x, z], i) => {
      const removed = !!airportM.inStandEnvelope(gatesW, x, z, 4); const m = { x, z, removed, r: 0.85, headHalf: 2.1, h: itemsM.MAST_H };
      // the geometry items.js buildMasts() emits for this mast (base, pole, platform ring, head bar, luminaires), recorded
      if (!removed) { itemsI.buildMasts([[x, z]]); const names = ['base', 'pole', 'platform', 'head-bar']; m.prims = globalThis.__lastGeo.prims.filter(p => p.v.length).map((p, k) => primOut(p, names[k] || 'luminaire')); }
      return m;
    });

    say('masts'); // ------------------------------------------------ airfield lighting (js/anim/lights.js via js/live/lights.js)
    // approach-light piers: app.js buildPierGeometry(lsys.piers) -> world.items; each pier's boxes recorded separately
    const LS = lightsI.buildAirfieldLights(1.0, { taxiways: false });
    const alsEnds = geo.APPROACH_LIGHTS.map(A => ({ ...A, F: animTrafficM.runwayFrame(A.end) }));
    const piers = LS.piers.map((P, i) => {
      lightsI.buildPierGeometry([P]); const prims = globalThis.__lastGeo.prims.filter(p => p.v.length);
      let sys = null, best = 1e9;
      for (const A of alsEnds) { const F = A.F; const dx = P.base[0] - F.thr[0], dz = P.base[2] - F.thr[2]; const along = -(dx * F.dir[0] + dz * F.dir[2]), lat = dx * F.right[0] + dz * F.right[2];
        if (along > 0 && Math.abs(lat) < best) { best = Math.abs(lat); sys = { end: A.end, type: A.type, fromThr: +along.toFixed(2), lateral: +lat.toFixed(3) }; } }
      const F = sys && alsEnds.find(A => A.end === sys.end).F;
      return { i, ...sys, fromEnd: F ? +(sys.fromThr - Math.hypot(F.thr[0] - F.start[0], F.thr[2] - F.start[2])).toFixed(2) : null, base: W2(P.base), right: rnd([P.right[0], P.right[2]], 5), water: !!P.water, h: P.h,
        prims: prims.map((p, k) => primOut(p, P.water ? ['leg', 'leg', 'cap', 'catwalk', 'rail', 'rail'][k] || 'pier' : 'post')) };
    });
    replicated.push('approach-light pier system/end labels: nearest APPROACH_LIGHTS end on the extended centreline (piers carry no label in js/anim/lights.js)');
    // all light sprites as the app builds them (app.js: buildLiveLights(cfg.airport, world.paved) - world.paved is the
    // pavement raster at quality mapRes, rebuilt here with the same inputs)
    const LL = liveLightsM.buildLiveLights(D.AIRPORT, mapPaved[Q.mapRes] || null);
    const lightCol = (c) => c[2] > 0.9 && c[0] < 0.3 ? 'blue' : c[1] > 0.9 && c[0] < 0.3 ? 'green' : c[1] < 0.1 ? 'red' : c[1] > 0.7 && c[2] < 0.3 ? 'yellow' : 'white';
    const lights = { taxiEdgeCount: LL.taxiCount, points: LL.L.map(l => [+l.p[0].toFixed(2), +l.p[1].toFixed(2), +l.p[2].toFixed(2), lightCol(l.c)]), flashers: LS.flashers.map(f => ({ p: rnd(f.p, 2), end: f.end })),
      papis: LS.papis.map(q => ({ p: rnd(q.p, 2), angle: +q.angle.toFixed(3), dir: rnd([q.dir[0], q.dir[2]], 5) })), note: 'js/anim/lights.js buildAirfieldLights(1, {taxiways:false}) sprites (no solid bodies except the piers); js/live/lights.js adds blue taxiway edge lights along the taxiway outlines' };

    // ------------------------------------------------ stands + jet bridges
    const TY = typesM.TYPES;
    const fits = (g, T) => { if (!T || g.remote || !g.maxSpan) return true; const span = T.wing ? T.wing.span : 36; if (span <= g.maxSpan + 0.6 && T.L <= g.maxLen + 2) return true; return g.maxSpan >= 64 && span <= 80; };
    replicated.push('standFits() (traffic.js, module-private) copied to pick class-max types; oversize = span > maxSpan + 0.5 (traffic.js occupy())');
    const typeKeys = Object.keys(types).filter(k => !k.startsWith('biz_'));
    const classTypes = {};
    for (const cls in classMax) {
      const g0 = { maxSpan: classMax[cls].span, maxLen: classMax[cls].len };
      const fit = typeKeys.filter(k => fits(g0, TY[k])); const nonOver = fit.filter(k => TY[k].wing.span <= g0.maxSpan + 0.5);
      const byArea = (a, b) => (TY[b].wing.span - TY[a].wing.span) || (TY[b].L - TY[a].L);
      classTypes[cls] = { fit, nonOversize: nonOver, oversize: fit.filter(k => !nonOver.includes(k)), maxType: nonOver.slice().sort(byArea)[0], maxLenType: nonOver.slice().sort((a, b) => TY[b].L - TY[a].L)[0], refType: refType[cls] };
    }
    const bridgeParts = (gp, b, k) => {
      const rg = new RecGeo(); const saveSpr = gateSys.sprites; gateSys.sprites = [];
      const P = gateSys.bridgeGeo(gp, b, k, rg, null); gateSys.sprites = saveSpr;
      // label primitives in bridgeGeo() emission order
      const out = []; let loose = 0, cyl = 0, boxAfterCab = false; const prims = rg.prims;
      let i = 0; const nxt = () => prims[i++];
      const isCol = (p, c) => p.col && Math.abs(p.col[0] - c[0]) < 1e-3 && Math.abs(p.col[1] - c[1]) < 1e-3 && Math.abs(p.col[2] - c[2]) < 1e-3;
      let tubeN = 0;
      while (i < prims.length) {
        const p = nxt();
        if (p.kind === 'loose') { // a tube: loose sides followed by its two end frames
          const f1 = prims[i], f2 = prims[i + 1]; i += 2; const v = p.v.concat(f1.v, f2.v);
          out.push({ part: tubeN === 0 ? 'walkway' : 'tunnel' + tubeN, kind: 'tube', hull: hull2(v), y: yr(v), pp: [ppOut(tubePP(p.v)), ppOut(f1.pp), ppOut(f2.pp)].filter(Boolean) }); tubeN++; continue;
        }
        let name = 'misc';
        if (p.kind === 'cyl' || p.kind === 'lathe') { const r = p.r ?? p.rmax; name = Math.abs(r - 0.35) < 1e-6 ? 'column' : Math.abs(r - 0.6) < 1e-6 ? 'pedestal' : Math.abs(r - 2.45) < 1e-6 ? 'rotunda' : Math.abs(r - 0.48) < 1e-6 ? 'wheel' : Math.abs(r - 0.14) < 1e-6 ? 'beacon' : 'cyl'; }
        else if (p.kind === 'box') {
          const C = { steel: [0.46, 0.47, 0.49], cab: [0.8, 0.81, 0.82], dark: [0.07, 0.07, 0.08], yellow: [0.9, 0.7, 0.08], unit: [0.74, 0.75, 0.76], lamp: [1, 0.93, 0.82] };
          if (isCol(p, C.cab)) { name = 'cab'; boxAfterCab = true; }
          else if (boxAfterCab && (isCol(p, C.steel) && p.max[1] > 3.1 && p.min[1] >= 3.1)) name = 'cab-roof';
          else if (boxAfterCab && isCol(p, C.dark) && p.min[0] >= 1.49 && p.max[1] > 2.9) name = 'bellows';
          else if (boxAfterCab && (isCol(p, C.dark) || isCol(p, C.lamp))) name = 'floodlight';
          else if (boxAfterCab) name = 'stair';
          else if (isCol(p, C.unit)) name = 'pca-unit';
          else if (isCol(p, C.yellow) && p.min[1] < -1.9) name = 'pca-hose';
          else if (isCol(p, C.yellow)) name = 'drive-control';
          else if (isCol(p, C.steel) && Math.abs(p.max[2] - 1.55) < 1e-6) name = 'drive-beam';
          else if (isCol(p, C.steel) && Math.abs(p.max[0] - 0.16) < 1e-6) name = 'drive-leg';
          else name = 'box';
        }
        out.push(primOut(p, name));
      }
      return { P, parts: out, nPrims: prims.length };
    };
    const poseOut = (P) => ({ attach: W2(P.attach), u: rnd([P.u[0], P.u[2]], 5), rc: W2(P.rc), floorY: +P.floorY.toFixed(3), cab: rnd(P.cab), facing: rnd([P.facing[0], P.facing[2]], 5), door: rnd(P.door), kk: +P.kk.toFixed(4), type: P.T && P.T.key });
    const stands = [], bridges = [];
    for (const g of gatesW) {
      const n = geo.stToWorld(g.nose[0], g.nose[1], 0), fW = gatesI.stD(g.dir);
      const S = { name: g.name, alias: g.alias || [], letter: g.letter, cls: g.cls, src: g.src || null, remote: !!g.remote, bridge: !!g.bridge, nose: [+n[0].toFixed(3), +n[2].toFixed(3)], noseST: rnd(g.nose), dirST: rnd(g.dir, 6), dir: rnd([fW[0], fW[2]], 6), hdg: g.hdg ?? null,
        maxSpan: g.maxSpan, maxLen: g.maxLen, wide: g.wide, acType: g.acType, dockType: g.dockType || null, dock: g.dock ? { nose: stWorld(g.dock.nose), dirST: rnd(g.dock.dir, 6) } : null, occupant: g.occupant || null, oversize: !!g.oversize,
        envelope: g.bridge ? stRing(airportM.standEnvelopeST(g, 0, 0, 0)) : null, classTypes: classTypes[g.cls] || null, bridges: [] };
      if (g.bridge) {
        // stand sign + VDGS (gates.js standGeo): recorded boxes
        const rg = new RecGeo(); const sg = { pos: [], nrm: [], uv: [], ext: [], idx: [] }; gateSys.standGeo(g, rg, sg);
        const post = rg.prims.length > 3, names = post ? ['vdgs-post', 'vdgs-post-base', 'vdgs-display', 'vdgs-display-base', 'stand-sign-back'] : ['vdgs-display', 'vdgs-display-base'];
        S.vdgs = rg.prims.filter(p => p.v.length).map((p, i) => primOut(p, names[i] || 'vdgs')); S.vdgsPost = post;
        const anim = gateSys.anims.get(g.id); const kNow = anim ? anim.k : null;
        for (const b of g.bridges) {
          const B = { stand: g.name, gate: b.gate, door: b.door, attachData: rnd(b.attachW), attach: W2(b.attachW), u: rnd([b.u[0], b.u[2]], 6), fixedLen: +b.fixedLen.toFixed(3), rc: W2(b.rc), parkDir: rnd([b.parkDir[0], b.parkDir[2]], 6), reach: +b.reach.toFixed(3), poses: {} };
          const docksNow = g.acType && gateSys.docks(g, b);
          const kCur = anim ? (gateSys.docks(g, b) ? kNow : 0) : (docksNow ? 1 : 0);
          const cur = bridgeParts(g, b, kCur); B.poses.current = { k: kCur, occupiedBy: g.acType, pose: poseOut(cur.P), parts: cur.parts };
          const gp0 = { ...g, dock: null, acType: null, _lastType: null };
          const rest = bridgeParts(gp0, b, 0); B.poses.rest = { k: 0, pose: poseOut(rest.P), parts: rest.parts };
          for (const [key, tk] of [['dockRef', refType[g.cls]], ['dockMax', classTypes[g.cls] && classTypes[g.cls].maxType]]) {
            if (!tk) continue; const gp = { ...g, dock: null, acType: tk, _lastType: tk }; const d = gateSys.docks(gp, b);
            const r = bridgeParts(gp, b, d ? 1 : 0); B.poses[key] = { k: d ? 1 : 0, type: tk, docks: d, pose: poseOut(r.P), parts: r.parts };
          }
          bridges.push(B); S.bridges.push(bridges.length - 1);
        }
      }
      stands.push(S);
    }

    say('stands + bridges'); // ------------------------------------------------ ground service equipment (instances as placed, footprints from the vehicle meshes)
    const VM = vehI.buildVehicleMeshes(); const vehFoot = {};
    for (const k in VM) { const v = VM[k].data.pos; vehFoot[k] = { hull: hull2(v), y: yr(v) }; }
    const gse = [];
    for (const k in gateSys.vehicleBuckets || {}) for (const e of gateSys.vehicleBuckets[k]) {
      // inst(): rows of the 3x4 matrix; local x -> e[0],e[4],e[8]; translation e[3],e[7],e[11]
      const ax = [e[0], e[4], e[8]], az = [e[2], e[6], e[10]], t = [e[3], e[7], e[11]];
      const hull = vehFoot[k].hull.map(([lx, lz]) => [+(t[0] + ax[0] * lx + az[0] * lz).toFixed(3), +(t[2] + ax[2] * lx + az[2] * lz).toFixed(3)]);
      gse.push({ kind: k, pos: [+t[0].toFixed(3), +t[2].toFixed(3)], dir: rnd([ax[0], ax[2]], 5), hull, y: [G + vehFoot[k].y[0], G + vehFoot[k].y[1]] });
    }
    // the collision-check rectangles used by placeVehicles (len x wid centred on the placement point) for comparison
    const gseCheckDims = { beltLoader: [8.5, 2.2, 1.4], tug: [3, 1.8, 2.1], cart: [3.2, 1.8, 1.5], catering: [8.2, 2.4, 6.3], fuel: [8.2, 2.5, 2.9], gpu: [2.5, 1.5, 1.6], cone: [0.4, 0.4, 0.8] };
    replicated.push('GSE collision-check rectangle sizes copied from gates.js placeVehicles() put() calls (for comparison with the real vehicle mesh footprints)');

    // ------------------------------------------------ aircraft (as displayed): pose, model placement, procedural bodies
    const aircraft = []; const bodies = {};
    const needBody = new Set(typeKeys);
    for (const tr of traffic.tracks.values()) {
      const D2 = tr.disp; const ac = SFO.scene.aircraft.find(a => a.id === tr.hex) || null; const T = tr.model && TY[tr.model.t];
      const A = { hex: tr.hex, flight: tr.info.flight || null, reg: tr.info.reg || null, icao: tr.info.icao || null, typeKey: tr.model ? tr.model.t : null, modelKey: tr.model ? tr.model.m : null, generic: tr.model ? tr.model.generic || null : null,
        phase: tr.phase, ground: !!D2.ground, valid: !!D2.valid, stale: !!tr.stale, gate: tr.gate ? tr.gate.name : null, gs: D2.gs, pos: [D2.x, D2.y, D2.z], hdg: D2.hdg,
        nose: T ? [D2.x + Math.sin(D2.hdg) * trafficM.ANT * T.L, D2.z - Math.cos(D2.hdg) * trafficM.ANT * T.L] : null,
        phys: tr.phys ? { off: tr.phys.off || null, cur: tr.phys.cur || null, ok: tr.phys.ok ?? null } : null, rendered: ac ? (ac.model ? 'model' : 'procedural') : 'marker' };
      if (ac) { A.W = Array.from(ac.matrix()); A.modelLoaded = !!ac.model; A.modelKeyUsed = ac.modelKey || null; A.stretch = ac.stretch || null; A.placement = ac.model ? Array.from(ac.placement()) : null; A.modelDims = ac.model ? ac.model.dims : null; if (!ac.model) needBody.add(ac.type); }
      if (A.typeKey && TY[A.typeKey]) needBody.add(A.typeKey);
      aircraft.push(A);
    }
    for (const k of needBody) { if (!TY[k]) continue; const B = modelM.buildAircraft(k, 0); const pos = [], idx = [];
      const add = (d) => { const base = pos.length / 3; for (const x of d.pos) pos.push(x); for (const i of d.idx) idx.push(i + base); };
      add(B.body); for (const f of B.flaps) add(f.data); for (const s of B.spoilers) add(s.data); for (const gg of B.gear) add(gg.data);
      bodies[k] = { ...pack(pos, idx), frame: 'buildAircraft(): local x = xMain - (distance from nose) (forward +), y up (0 = ground), z = right; world = aircraft.W * local', Hc: TY[k].Hc, xMain: TY[k].xMain, L: TY[k].L };
    }

    // rendered geometry of every type as the app would draw it when parked: a LiveAircraft per TYPES key (not added to
    // the scene) gives the model key, plug stretch and model placement exactly as for a live aircraft
    const typeRender = {};
    for (const k of typeKeys) {
      const icao = Object.keys(acM.TYPE_MODELS).find(c => acM.TYPE_MODELS[c].t === k && acM.TYPE_MODELS[c].m) || null;
      const mk = icao ? acM.TYPE_MODELS[icao].m : null;
      if (!mk) { typeRender[k] = { modelKey: null, icao: Object.keys(acM.TYPE_MODELS).find(c => acM.TYPE_MODELS[c].t === k) || null }; continue; }
      const la = new acM.LiveAircraft(k, mk, 0, { id: 'probe-' + k }); await la.ready;
      typeRender[k] = { icao, modelKey: mk, stretch: la.stretch || null, placement: la.model ? Array.from(la.placement()) : null, dims: la.model ? la.model.dims : null, Hc: typesM.TYPES[k].Hc };
    }
    say('aircraft'); // ------------------------------------------------ physics view of the world (what GroundPhysics / traffic use)
    const physics = { stats: SFO.physics.stats || null, buildingGridSources: 'airport.terminalComplex + boardingAreas + structures except rail and hangar (ground.js buildingGrid, 2 m cells)', paved: 'ground.js pavedUnion(world.paved, traffic.net): paintAirportMapReal raster at quality mapRes (' + Q.mapRes + ' m) OR TaxiNet.paved(round(x), round(z))', mapRes: Q.mapRes };
    // the OSM taxi net GroundPhysics adds to the raster (traffic.js TaxiNet.paved: within hw of an edge, 30.5 m of a
    // runway edge, or inside an apron ring), exported so tools/drawing can test gear points the way the physics does
    const net = traffic.net && traffic.net.ok ? { hw: traffic.net.hw, rwHw: 30.5, edges: traffic.net.E.map(e => [+e.x0.toFixed(2), +e.z0.toFixed(2), +e.x1.toFixed(2), +e.z1.toFixed(2), e.rw ? 1 : 0]), aprons: traffic.net.aprons.map(a => a.r.map(q => [+q[0].toFixed(2), +q[1].toFixed(2)])) } : null;
    replicated.push('TaxiNet.paved() test (traffic.js) re-implemented in tools/drawing/common.py net_paved(); checked against physics.samples (the page\'s own SFO.physics.paved at random points)');
    if (net) { const smp = []; let seed = 12345; const rnd01 = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
      for (let i = 0; i < 20000; i++) { const x = -2600 + rnd01() * 4400, z = -2300 + rnd01() * 4100; smp.push([+x.toFixed(2), +z.toFixed(2), SFO.physics.paved(x, z) ? 1 : 0, traffic.net.paved(Math.round(x), Math.round(z)) ? 1 : 0]); }
      physics.samples = smp; }

    // ------------------------------------------------ assemble
    const u8 = new Uint8Array(binLen); { let o = 0; for (const b of bin) { u8.set(b, o); o += b.length; } }
    return {
      json: {
        meta: { ...meta, replicated, snapshotLabel: document.querySelector('#status') ? document.querySelector('#status').textContent : null },
        types, typeRender, typeModels: acM.TYPE_MODELS, modelDims: manifest.MODEL_DIMS, modelBase: acM.MODEL_BASE, classMax, refType, classTypes, gseCheckDims,
        buildings, buildingMesh, tower: towerOut, itbRoof, runways: RW, runwaysFAA: faa, endZones, emasBeds, pave, markings, signs, signLegs, masts,
        stands, bridges, gse, vehicleFootprints: vehFoot, aircraft, bodies, physics, net, piers, lights,
      },
      bin: b64(u8), rasters: rasterOut,
    };
  });
  // write outputs
  for (const [k, r] of Object.entries(res.rasters)) { fs.writeFileSync(path.join(OUTD, k + '.png'), Buffer.from(r.png.split(',')[1], 'base64')); r.file = k + '.png'; delete r.png; }
  res.json.rasters = res.rasters; res.json.meta.git = git; res.json.meta.gitHead = gitHead; res.json.meta.gitDirty = gitDirty; res.json.meta.secondsAfterLoad = (Date.now() - tLoad) / 1000; res.json.meshBin = 'meshes.bin';
  res.json.meta.typesHash = crypto.createHash('sha256').update(JSON.stringify(res.json.types)).digest('hex').slice(0, 16);
  const inputs1 = hashInputs(await loaded());
  res.json.meta.inputs = inputs1; res.json.meta.inputsChangedDuringExtraction = Object.keys(inputs1).filter(k => k in inputs0 && inputs0[k] !== inputs1[k]);
  res.json.meta.inputsHash = crypto.createHash('sha256').update(JSON.stringify(inputs1)).digest('hex').slice(0, 16);
  fs.writeFileSync(path.join(OUTD, 'meshes.bin'), Buffer.from(res.bin, 'base64'));
  fs.writeFileSync(path.join(OUTD, 'scene2d.json'), JSON.stringify(res.json));
  const J = res.json;
  console.log('scene2d.json:', (fs.statSync(path.join(OUTD, 'scene2d.json')).size / 1e6).toFixed(1), 'MB;', J.buildings.length, 'building footprints,', J.stands.length, 'stands,', J.bridges.length, 'bridges,', J.gse.length, 'GSE,', J.aircraft.length, 'aircraft,', J.markings.ribbons.length, 'ribbons,', J.signs.length, 'signs,', J.piers.length, 'approach-light piers,', J.lights.points.length, 'lights; frame', J.meta.frameId, 'git', J.meta.git, 'inputs', Object.keys(J.meta.inputs).length, 'changed during extraction', J.meta.inputsChangedDuringExtraction.length);
};
