// Airfield-lighting sprites for both renderers (docs/research/environment_spec.md §5, §4.10, §9.1 item 4; step 2).
// Replaces js/anim/lights.js buildAirfieldLights' runway / approach / PAPI sprites (its arbitrary `i: 30 / 60 / 900`
// intensities, airfield §12 defects 1-8) with the 3,633 fixture faces of data/sfo_lighting.js (js/env/lighting/fixtures.js)
// switched by the JO 7110.65 controller (js/env/lighting/controller.js) and drawn at their photometric intensity:
//   I_view = cd(type, colour) × step % × B(θh, θv) × k_cd                       (spec §5.4; AC 150/5345-46F minima, V)
//   T = exp(−optical depth through the renderer's slabs: sky_model.js renderSlabs + slabTau, the scene fog's σ field),
//   E = I_view·T/d², v = visibility factor (E / E_T)   (§4.10)
//   sprite intensity i = lampUnits(I_view·T·v·G, s), phys: true                 (js/env/lighting/photometry.js)
// G = DAY_GAIN^(1 − w) (w = ASOS night weight): display gain by day (I). A 2-px sprite drawn at its physical energy cannot
// reach the eye's daylight contrast threshold on a display (spec §4.10 "Rendering the threshold on a display"): with the
// day exposure of js/three/renderer3.js (lit concrete at the display key) the just-visible energy of a 2.2-px sprite is
// ~30-40 × the eye's E_T = 4.12e-4 lx (estimate from the exposure and the sprite's solid angle, M on I); at night the
// physical rendering is within 2 × of the eye's threshold (E_T = 6.99e-7 lx), so G → 1. QA-tuned by the A-VIS render
// test (§11.3; step 3 adds the physical exposure). The visibility factor itself is physical (E vs E_T, A-VIS1).
// Choices and their tags (I unless stated):
//  - ALS steady lamps, ALS green threshold bars and the sequenced flashers have no FAA public photometry (NV, spec §5.4):
//    provisional cd = L-862 white 10,000 / red 2,000 / L-862E green 3,200 (spec §5.4 "Provisional: I = L-862 white × pct";
//    the same basis for red / green / flashers); records carry photometryNV and show red in ?qa=prov.
//  - ALS beams: ±10° in azimuth (NV), 12° vertical spread about the station's elevation setting (JO 6850.2C 206a,
//    Tables 2-1 / 2-2 via lighting_spec.json als_detail, V); flashers aimed 6° (fixture aim_up).
//  - SSALR mode of the 28R ALSF-2 (3-4-9; JO 6850.2C 200c via lighting_spec.json rules.ssalr, V): centreline bars at
//    200..1400 ft every 200 ft, the 1000-ft bar reduced to 70 ft (the inner lights within ±35 ft, I), no red side rows,
//    no 500-ft bar, RAIL = five flashers at 1600..2400 ft every 200 ft, sequenced among themselves (JO 6850.2C 200c, V);
//    the threshold bar stays (I).
//  - ALS positions: fixture station and lateral offset, placed on the structures by js/anim/lights.js alsPlacement
//    (NAIP-imaged stations over the water, inset on pavement, low mounts on land) so no light floats (owner rule).
//  - Taxiway edge lights: the app's outline-derived blue lights (spec §5.9 / Q4: kept, inf) at L-861T 2 cd (AC 150/5345-46F
//    Table 3-3 minimum, V) × the MITL 3-step output (AC 150/5340-30J 2.6.4.2: 100/30/10 %; the controller's taxiway
//    step >= 3 = full output, I), omnidirectional.
//  - PAPI: HG4 aiming (Q6 default), night 20 % / day 100 % from the PAPI photocell (EnvState photocell.papiNight).
//  - RWSL (3-4-19, automatic): REL arrays from the traffic (rwslFromTraffic, AIM 2-1-6); the 14 NV-flagged REL arrays
//    (runway assignment ambiguous) and the THLs stay dark (I).
//  - L-862 white also emits >= 50 cd omnidirectionally up to 15° elevation (46F Table 3-2 note (c), V), × step %.
//  - k_cd = 1 (46F allows the average up to 3× the minimum, §3.3: calibrate on owner night photos, Q7).
import { loadFixtures, COLOUR_NAME } from './fixtures.js';
import { controllerFromEnv, RUNWAY_OF, MITL_PCT } from './controller.js';
import { beamOf, beamFactor, papiWhite, papiCd, visibilityFactor, flashGain, lampUnits, aureole } from './photometry.js';
// one σ field for the scene fog and the lights (spec §4.10; review truth1-3 / look1-2): the renderer's slabs (BKN at its
// mean transmittance, the VV obscuration, the lowest slab's horizontal structure) and the same optical depth
import { renderSlabs, slabTau } from '../atmo/sky_model.js';

const DEG = Math.PI / 180, FT = 0.3048;
export const SIGMA_CLEAR_AIR = 3.3e-5;          // = js/env/state.js SIGMA_CLEAR (clear air of the sky model, spec §4.10, M)
export const DAY_GAIN = 30;                     // I (header)
export const K_CD = 1.0;                        // I (46F §3.3: average up to 3× the minimum)
export const ALS_PROVISIONAL_CD = { W: 10000, R: 2000, G: 3200 };   // I on NV (header)
export const ALS_BEAM_H = 10, ALS_V_SPREAD = 12;                    // NV / JO 6850.2C 206a (V)
export const TAXI_EDGE_CD = 2;                  // L-861T blue minimum (AC 150/5345-46F Table 3-3, V); MITL steps: controller.js MITL_PCT
export { MITL_PCT };
// Flashes (js/env/lighting/photometry.js flashGain): SFL each flasher 2 flashes/s, sequence outermost -> threshold
// (JO 6850.2C 200b, V), equal spacing in the 0.5 s cycle (I), effective intensity provisional (NV) = 10,000 cd × the
// flasher step %; REIL 120 fpm, both units in sync (AC 150/5345-51B 3.4.2, V; style E unidirectional, SFO style NV);
// L-864 30 fpm (27-33, AC 150/5345-43J 3.4.1.5, V), on for half the period (incandescent "1/2-2/3 period" / LED 100-1333
// ms, V range; 1.0 s chosen, I), 2,000 cd effective (V). Flash lamps: short (xenon / LED, duration NV): one frame.
export const FLASH = { SFL: { cd: 10000, P: 0.5, on: 0.002 }, REIL: { fpm: 120, on: 0.002 }, L864: { fpm: 30, on: 1.0, cd: 2000 } };
const SSALR_BAR_HALF_FT = 35;                   // 70-ft crossbar (rules.ssalr, V) -> inner lights (I)
// SSALR RAIL: five flashers at 1,600 / 1,800 / 2,000 / 2,200 / 2,400 ft (JO 6850.2C 200c, V)
export const SSALR_RAIL_FT = [1600, 1800, 2000, 2200, 2400];
const isSsalrRail = (q) => SSALR_RAIL_FT.includes(q.station);

/** Runway CL lines from LIGHTING_SPEC (runway_end world points): {runway: {a: [x, z], u: [ux, uz]}}. */
function runwayLines(SPEC) {
  const out = {};
  for (const R of SPEC.runways || []) {
    const K = Object.keys(R.ends || {}).filter(k => R.ends[k].runway_end && R.ends[k].runway_end.world);
    if (K.length < 2) continue;
    const E = K.map(k => R.ends[k].runway_end.world);
    const dx = E[1][0] - E[0][0], dz = E[1][1] - E[0][1], L = Math.hypot(dx, dz);
    out[R.id] = { a: E[0], u: [dx / L, dz / L], ends: K };     // u points from end K[0] toward end K[1]
  }
  return out;
}

export class AirfieldLighting {
  /** opts: {groundY, alsPlace: {end: place(stationFt, latM) -> {p, kind}} (js/anim/lights.js alsPlacement),
   *  taxiEdges: [{p}] (blue edge light positions), dayGain} */
  constructor(FIX, SPEC, opts = {}) {
    this.spec = SPEC; this.dayGain = opts.dayGain ?? DAY_GAIN;
    const L = loadFixtures(FIX, SPEC, { groundY: opts.groundY ?? 3 });
    this.loaded = L;
    const lines = runwayLines(SPEC); this.lines = lines;
    const thr = {}, alsAim = {};
    // REL arrays (RWSL, AIM 2-1-6): fixture group per light (by position), crossing point on the runway axis
    const relKey = (x, z) => x.toFixed(2) + ',' + z.toFixed(2);
    const relOf = new Map(); this.relGroups = [];
    FIX.groups.forEach((g, gi) => {
      if (g.system !== 'rwsl_rel' || g.runway_nv) return;
      const ln = lines[g.end]; if (!ln) return;
      let best = null; for (const p of g.pts) { const lat = Math.abs(-(p[0] - ln.a[0]) * ln.u[1] + (p[1] - ln.a[1]) * ln.u[0]); if (!best || lat < best.lat) best = { lat, a: (p[0] - ln.a[0]) * ln.u[0] + (p[1] - ln.a[1]) * ln.u[1] }; }
      this.relGroups.push({ id: gi, runway: g.end, a: best.a, n: g.n });
      for (const p of g.pts) relOf.set(relKey(p[0], p[1]), gi);
    });
    for (const R of SPEC.runways || []) for (const [E, e] of Object.entries(R.ends || {})) {
      if (e.landing_threshold && e.landing_threshold.world) thr[E] = e.landing_threshold.world;
      if (e.als_detail && e.als_detail.elevation_setting_deg) alsAim[E] = e.als_detail.elevation_setting_deg;
    }
    this.iso = SPEC.fixtures.PAPI_LHA && SPEC.fixtures.PAPI_LHA.isocandela;
    const recs = [];
    this.alsKinds = {};
    for (const r of L.records) {
      if (r.system === 'papi' && r.colour === 'R') continue;          // PAPI: one record per LHA (white / red split below)
      const q = { ...r, p: r.p.slice() };
      const cname = COLOUR_NAME[r.colour];
      q.cname = cname;
      q.h2 = r.dir ? (() => { const l = Math.hypot(r.dir[0], r.dir[2]) || 1; return [r.dir[0] / l, r.dir[2] / l]; })() : null;
      q.aimUp = r.aimUp || 0;
      const sys = r.system;
      if (sys === 'runway_edge' || sys === 'runway_centreline') q.sys = 'HIRL ' + r.end;
      else if (sys === 'threshold_end' || sys === 'runway_end' || sys === 'threshold_wingbar') q.sys = 'HIRL ' + RUNWAY_OF[r.end];
      else if (sys === 'tdz') q.sys = 'TDZ ' + r.end;
      else if (/^als_/.test(sys)) q.sys = 'ALS ' + r.end;
      else if (sys === 'reil') q.sys = 'REIL ' + r.end;
      else if (sys === 'papi') q.sys = 'PAPI';
      else if (/^rwsl/.test(sys)) { q.sys = 'RWSL'; if (sys === 'rwsl_rel') q.grp = relOf.get(relKey(r.p[0], r.p[2])); }
      else continue;
      // toe-in side: horizontal unit vector toward the runway centreline (edge, threshold / end, TDZ lights; 46F beams
      // are given for the toed side), or away from it for the REIL toe-out
      const rwy = sys === 'runway_edge' || sys === 'runway_centreline' ? r.end : RUNWAY_OF[r.end];
      const ln = lines[rwy];
      if (ln) {
        const n = [-ln.u[1], ln.u[0]]; const side = (r.p[0] - ln.a[0]) * n[0] + (r.p[2] - ln.a[1]) * n[1];
        q.toCL = side > 0 ? [-n[0], -n[1]] : [n[0], n[1]];
      }
      // beam
      if (/^als_/.test(sys)) {
        const tw = thr[r.end]; const u = q.h2;
        const rel = [r.p[0] - tw[0], r.p[2] - tw[1]];
        q.lat = rel[0] * (-u[1]) + rel[1] * u[0];                      // m right of the OUTWARD axis (cross(u, up))
        const st = r.station ?? Math.round((rel[0] * u[0] + rel[1] * u[1]) / FT);
        q.station = st;
        const place = opts.alsPlace && opts.alsPlace[r.end];
        if (place) { const P = place(st, q.lat); q.p = P.p; q.place = P.kind; this.alsKinds[P.kind] = (this.alsKinds[P.kind] || 0) + 1; }
        const tab = alsAim[r.end] || {};
        const keys = Object.keys(tab).filter(k => /^\d+$/.test(k)).map(Number);
        const near = keys.length ? keys.reduce((a, b) => Math.abs(b - st) < Math.abs(a - st) ? b : a) : null;
        const aim = sys === 'als_flasher' ? (r.aimUp || 6) : near != null ? tab[String(near)] : 6;
        q.beam = { main: { h: [-ALS_BEAM_H, ALS_BEAM_H], v: [aim - ALS_V_SPREAD / 2, aim + ALS_V_SPREAD / 2] }, ten: null };
        q.cd = sys === 'als_flasher' ? FLASH.SFL.cd : ALS_PROVISIONAL_CD[r.colour] ?? ALS_PROVISIONAL_CD.W;
        q.provisional = true;
      } else if (sys === 'reil') {
        q.beam = { main: { h: [-15, 15], v: [-5, 5] }, ten: null };   // 30° × 10° about the aim (51B style E; I)
        q.toeOut = r.toeOut || 15;
      } else if (sys !== 'papi') {
        q.beam = beamOf(this.spec.fixtures[r.ftype], cname);
        if (q.cd == null) q.cd = 0;
      }
      recs.push(q);
    }
    // sequenced flashers: per end, outermost first, phase j × 0.5 s / N
    this.seq = {};
    // (SSALR mode of the 28R ALSF-2: the RAIL is five flashers, 1,600-2,400 ft every 200 ft, sequenced among themselves:
    // JO 6850.2C 200c "five sequenced flashers ... the first being located 200 feet beyond the approach end of the last
    // steady-burning light bar with successive flasher units at each 200-foot interval out to 2,400 feet", V; review
    // finding truth1-8: all 9 ALSF-2 flashers >= 1,600 ft were kept, at 100-ft spacing)
    this.seqS = {};
    for (const e of new Set(recs.filter(q => q.system === 'als_flasher').map(q => q.end))) {
      const F = recs.filter(q => q.system === 'als_flasher' && q.end === e).sort((a, b) => b.station - a.station);
      F.forEach((q, j) => { q.phase = j * FLASH.SFL.P / F.length; });
      this.seq[e] = F;
      const FS = F.filter(isSsalrRail); FS.forEach((q, j) => { q.phaseS = j * FLASH.SFL.P / FS.length; }); this.seqS[e] = FS;
    }
    // taxiway edge lights (inf): omnidirectional blue
    const blue = (SPEC.colours.blue && SPEC.colours.blue.lin_srgb) || [0, 0.16, 1];
    for (const t of opts.taxiEdges || []) recs.push({ p: t.p.slice(), c: blue, colour: 'B', cname: 'blue', s: 0.2, sys: 'TWY', cd: TAXI_EDGE_CD, beam: null, h2: null, system: 'taxiway_edge', prov: 'inf', provClass: 'inf' });
    this.recs = recs; this.out = []; this.pool = []; this.env = null; this.state = null; this.tPrev = null; this.rwsl = null;
  }
  /** The 28R / 28L / 19L flasher sequence (QA, test): [{station, phase}], outermost first. */
  flasherSequence(end, mode) { return mode === 'SSALR' ? (this.seqS[end] || []).map(q => ({ station: q.station, phase: q.phaseS })) : (this.seq[end] || []).map(q => ({ station: q.station, phase: q.phase })); }
  /** Mount groups for js/anim/lights.js buildMountGeometry: the ALS lights placed on land ('land') or over the water
   *  without an imaged structure ('water'), grouped per end, station and lateral cluster (6 m buckets): one post under the
   *  group's centre and a bar under its lights; plus a lamp housing behind each PAPI LHA (box). `right` is passed as the LEFT of the outward axis because the geometry's
   *  local z is cross(cross(right, up), up) = −right (js/math.js m4.basis), so local z = metres right of the outward axis. */
  mountGroups() {
    const G = new Map();
    for (const r of this.recs) {
      if (!r.place || (r.place !== 'land' && r.place !== 'water')) continue;
      const k = r.end + '|' + r.station + '|' + Math.round(r.lat / 6);
      let g = G.get(k); if (!g) G.set(k, g = { pts: [], lats: [], u: r.h2, y: r.p[1], water: r.place === 'water' });
      g.pts.push(r.p); g.lats.push(r.lat); g.y = Math.min(g.y, r.p[1]);
    }
    const out = [];
    for (const r of this.recs) if (r.sys === 'PAPI' && r.h2) out.push({ x: r.p[0], z: r.p[2], yTop: r.p[1], box: true, right: [r.h2[1], 0, -r.h2[0]] });
    for (const g of G.values()) {
      const n = g.pts.length; const mx = g.pts.reduce((a, p) => a + p[0], 0) / n, mz = g.pts.reduce((a, p) => a + p[2], 0) / n;
      const ml = g.lats.reduce((a, b) => a + b, 0) / n;
      out.push({ x: mx, z: mz, yTop: g.y, lo: Math.min(...g.lats) - ml, hi: Math.max(...g.lats) - ml, right: [g.u[1], 0, -g.u[0]], water: g.water, n });
    }
    return out;
  }
  /** RWSL activation: a Set of REL fixture-group ids to light, or null (all dark). THLs stay dark (their rule needs a
   *  second aircraft on the runway ahead: not implemented, I). */
  setRwsl(set) { this.rwsl = set; }
  /** REL arrays lit by the traffic (AIM 2-1-6, V via spec §5.3): on a runway with a departure past ~30 kt or an arrival
   *  within ~1 mile of the landing threshold; each array goes out ~3-4 s before the aircraft reaches it (3.5 s, I); an
   *  arrival below ~80 kt keeps only the arrays within 30 s of its forward path, below ~34 kt none; an airborne departure
   *  none. tracks: iterable of {phase, rwy (end name, e.g. '28L'), x, z, gs (m/s), ground}. Returns the Set (also set).
   *  phase: the internal classifier names (takeoff / final / flare / rollout) or the DISPLAY names js/live/app.js passes
   *  (js/live/traffic.js displayPhase: the landing roll is 'landing', the flare 'final'; review finding truth1-2: with
   *  the display names the arrival arrays went dark at touchdown). */
  rwslFromTraffic(tracks) {
    const KT = 0.514444, on = new Set();
    for (const t of tracks) {
      let ph = t.phase === 'landing' ? 'rollout' : t.phase;
      if ((ph === 'final' || ph === 'flare') && t.ground) ph = 'rollout';
      if (!t.rwy || !['takeoff', 'final', 'flare', 'rollout'].includes(ph)) continue;
      const rid = RUNWAY_OF[t.rwy]; const ln = this.lines[rid]; if (!ln) continue;
      const sgn = ln.ends[0] === t.rwy ? 1 : -1;                         // motion along u from the end t.rwy
      const aAc = (t.x - ln.a[0]) * ln.u[0] + (t.z - ln.a[1]) * ln.u[1];
      const v = Math.max(1, t.gs || 0);
      let maxEta = Infinity;
      if (ph === 'takeoff') { if (!t.ground || v < 30 * KT) continue; }
      else if (ph === 'final' || ph === 'flare') {
        const th = this.spec.runways.find(R => R.id === rid).ends[t.rwy].landing_threshold.world;
        const aTh = (th[0] - ln.a[0]) * ln.u[0] + (th[1] - ln.a[1]) * ln.u[1];
        if ((aTh - aAc) * sgn > 1852) continue;                           // farther than ~1 mile from the threshold
      } else { if (v < 34 * KT) continue; if (v < 80 * KT) maxEta = 30; }   // rollout
      for (const g of this.relGroups) {
        if (g.runway !== rid) continue;
        const eta = (g.a - aAc) * sgn / v;
        if (eta > 3.5 && eta <= maxEta) on.add(g.id);
      }
    }
    this.rwsl = on; return on;
  }
  _prepare(env) {
    const ctl = env.lighting || controllerFromEnv(env); const o = ctl.out; const S = {};
    for (const [k, v] of Object.entries(o)) {
      if (k.startsWith('HIRL ') || k.startsWith('TDZ ')) S[k] = { pct: v.pct };
      else if (k.startsWith('ALS ')) S[k] = v.on ? { pct: v.pct, mode: v.mode, sfl: v.SFL, sflPct: v.SFL_pct } : { pct: 0 };
      else if (k.startsWith('REIL ')) S[k] = { pct: 100, cdEff: v.cd_eff };
    }
    S.PAPI = { pct: ctl.papi.pct };
    S.TWY = { pct: ctl.taxiwayDrawn ? ctl.taxiwayDrawn.pct : o.taxiway.step > 0 ? MITL_PCT[o.taxiway.step] : 0 };   // = the HUD's drawn MITL % (truth1-15)
    S.RWSL = { pct: 100 };
    this.ctl = ctl; this.state = S; this.env = env;
    const w = env.photocell ? env.photocell.asosNightW : 1;
    this.gain = Math.pow(this.dayGain, 1 - w);
    this.ET = env.lightVis ? env.lightVis.ET : 6.99e-7;
    this.slabs = env.atm ? renderSlabs(env) : null;
    // fog aureoles only with droplets in the air (the lowest slab denser than clean air, σ > 1e-4 m⁻¹: mist / fog / haze,
    // I); clear-air scattering (Rayleigh + fine aerosol) is not forward-peaked and makes no aureole
    this.fogAur = !!(this.slabs && this.slabs[0] && this.slabs[0].sigma > 1e-4);
  }
  /** Sprite records for this frame: env = EnvState, cam = camera position [x, y, z], t = time (s). */
  update(env, cam, t) {
    if (!env || !cam) return [];
    if (env !== this.env) this._prepare(env);
    const tPrev = this.tPrev != null && t > this.tPrev && t - this.tPrev < 0.5 ? this.tPrev : t - 1 / 60; this.tPrev = t;
    const S = this.state, out = this.out; out.length = 0; let n = 0;
    const reilG = flashGain(tPrev, t, 60 / FLASH.REIL.fpm, 0, FLASH.REIL.on);
    this.stats = { lit: 0, aureoles: 0, drawn: 0, culled: 0, invisible: 0 };   // lit = core visible; drawn = records (incl. aureole-only)
    for (let k = 0; k < this.recs.length; k++) {
      const r = this.recs[k]; const st = S[r.sys]; if (!st || !(st.pct > 0)) continue;
      let cd = r.cd, pct = st.pct;
      if (r.sys.startsWith('ALS ')) {
        const sys = r.system;
        if (st.mode === 'SSALR') {
          if (sys === 'als_side_row' || sys === 'als_500ft_bar') continue;
          if (sys === 'als_centreline_bar' && (r.station > 1400 || r.station % 200 !== 0)) continue;
          if (sys === 'als_1000ft_bar' && Math.abs(r.lat) > SSALR_BAR_HALF_FT * FT + 0.3) continue;
          if (sys === 'als_flasher' && !isSsalrRail(r)) continue;
        }
        if (sys === 'als_flasher') { if (!st.sfl) continue; const g = flashGain(tPrev, t, FLASH.SFL.P, st.mode === 'SSALR' ? r.phaseS : r.phase, FLASH.SFL.on); if (!g) continue; pct = st.sflPct * g; }
      } else if (r.sys.startsWith('REIL ')) { if (!reilG) continue; cd = st.cdEff * reilG; pct = 100; }
      else if (r.sys === 'RWSL') { if (r.system !== 'rwsl_rel' || !this.rwsl || !this.rwsl.has(r.grp)) continue; }
      const p = r.p; const vx = cam[0] - p[0], vy = cam[1] - p[1], vz = cam[2] - p[2];
      const hd = Math.hypot(vx, vz), d = Math.hypot(hd, vy);
      if (d < 0.5 || d > 30000) { this.stats.culled++; continue; }
      const dv = Math.atan2(vy, hd) / DEG;
      let dh = 0;
      if (r.h2 && hd > 1e-6) {
        const c = (vx * r.h2[0] + vz * r.h2[1]) / hd; dh = Math.acos(Math.max(-1, Math.min(1, c))) / DEG;
        if (r.toCL) dh *= ((vx * r.toCL[0] + vz * r.toCL[1]) >= 0 ? 1 : -1);
      }
      let I, col = r.c;
      if (r.sys === 'PAPI') {
        const fw = papiWhite(r.aim, dv, dh); const iso = papiCd(this.iso, dh, dv - r.aim);
        const Iw = iso.white * fw, Ir = iso.red * (1 - fw); I = (Iw + Ir) * pct / 100 * K_CD; if (!(I > 0)) continue;
        const W = this.spec.colours.white.lin_srgb, R = this.spec.colours.red.lin_srgb; const a = Iw / (Iw + Ir);
        col = [W[0] * a + R[0] * (1 - a), W[1] * a + R[1] * (1 - a), W[2] * a + R[2] * (1 - a)];
      } else {
        let B;
        if (r.sys.startsWith('REIL ')) B = beamFactor(r.beam, -dh - r.toeOut, dv - r.aimUp);   // dh toward the CL -> away = −dh
        else if (r.h2 && Math.abs(dh) > 90 && r.beam) B = 0;                                    // behind a unidirectional face
        else B = beamFactor(r.beam, dh, dv);
        I = cd * pct / 100 * B * K_CD;
        // 46F T3-2 note (c): >= 50 cd white omnidirectionally to 15°; counted once per fixture (the face whose hemisphere
        // the viewer is in, so a bidirectional light does not get it twice)
        if (r.ftype === 'L-862' && r.colour === 'W' && dv >= 0 && dv <= 15 && Math.abs(dh) <= 90) I = Math.max(I, 50 * pct / 100);
        if (!(I > 0)) continue;
      }
      const T = this.slabs ? Math.exp(-slabTau(this.slabs, cam, p)) : Math.exp(-SIGMA_CLEAR_AIR * d);
      const E = I * T / (d * d); const v = visibilityFactor(E, this.ET);
      // fog aureole (photometry.js aureole; review look1-1): drawn while its energy at the eye reaches E_T, also when the
      // direct core is below threshold (in dense fog the glow is seen before the point)
      const A = this.fogAur ? aureole(T) : null; const aurOn = A && I * A.f / (d * d) >= this.ET;
      if (!(v > 0) && !aurOn) { this.stats.invisible++; continue; }
      let o = this.pool[n]; if (!o) o = this.pool[n] = { p: null, c: null, i: 0, s: 0.3, phys: true };
      o.p = p; o.c = col; o.s = r.s || 0.3; o.i = v > 0 ? lampUnits(I * T * v * this.gain, o.s) : 0; o.sys = r.system; o.code = r.colour; o.cd = I * T; o.v = v;
      o.aur = aurOn ? lampUnits(I * A.f * this.gain, o.s) : 0; o.aurR = aurOn ? A.theta : 0;
      if (aurOn) this.stats.aureoles++; if (v > 0) this.stats.lit++;
      out.push(o); n++;
    }
    this.stats.drawn = n;
    return out;
  }
}
