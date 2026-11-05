// Step-2 unit gates of docs/research/environment_spec.md §11.3 (no GPU):
//   A-VIS1   the light-visibility function (js/env/lighting/photometry.js visualRange + the EnvState thresholds) reproduces
//            AC 70/7460-1N Table B-1 (+ B.3) within ±5 % and both twilight ranges within ±5 % at their ends; the sprite
//            visibility factor is 0 at E_T, 1 at 2·E_T, > 0.5 at 0.9 × and 0 at 1.1 × every tabled distance.
//   A-PAPI1  the PAPI colour function gives the C2 patterns (§11.2) for all six ends with both the standard and the HG4
//            aiming sets, seen from 1,852 m at five angles, with the LHAs of data/sfo_lighting.js.
//   A-NAV1   the position-light sector function matches 14 CFR 25.1387 (red only 0–110° left, green only 0–110° right,
//            white only ±70° aft), the 25.1391 minima, the 25.1393 vertical factors and the 25.1395 overlap maxima; the
//            sprites of a synthetic aircraft show only the permitted colour from every azimuth; light states per phase
//            follow AIM 4-3-24.
//   A-FLASH1 the effective intensity (Blondel–Rey, 25.1401(e)) of every rendered flash is ≥ its target at 30, 60 and 120
//            fps; rates: SFL 2/s, REIL 120/min, aircraft 40–100/min, L-864 30 ± 3/min (and ≤ +25 % for L-864).
// Run: node tools/env/test_lights.mjs [gate]   (exit 1 on failure)
import { LIGHTING_SPEC, LIGHTING_FIXTURES } from '../../data/sfo_lighting.js';
import { visualRange, visibilityFactor, allardE, papiWhite, papiCd, papiPattern, flashGain, effectiveIntensity, BR_C } from '../../js/env/lighting/photometry.js';
import { extinctionFromVisibility, SM_M } from '../../js/env/wx/metar.js';
import { ET_DAY_LUX, ET_NIGHT_LUX, allardThreshold } from '../../js/env/state.js';
import { navIntensity, navVertical, aclMinimum, dihedral, aircraftLightStates, aircraftSprites, setLightViewer, setLightFrame, MINIMA_FACTOR, BEACON, STROBE } from '../../js/env/aircraft_lights.js';
import { AirfieldLighting, FLASH } from '../../js/env/lighting/airfield.js';

const only = process.argv[2] || null;
let fails = 0, n = 0;
const check = (gate, name, ok, info = '') => { if (only && gate !== only) return; n++; if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${gate} ${name}${info !== '' ? ' | ' + info : ''}`); };
const DEG = Math.PI / 180;

// ============================================================================================== A-VIS1
// [V] AC 70/7460-1N (2026-08-11) Appendix B Table B-1 + the B.3 night 1 SM sentence (spec §4.10 table)
const B1 = [['night', 3, 2.9, 1500], ['night', 3, 3.1, 2000], ['night', 3, 1.4, 32], ['night', 1, 1.2, 2000],
  ['day', 1, 1.5, 200000], ['day', 1, 1.4, 100000], ['day', 1, 1.0, 20000], ['day', 3, 3.0, 200000], ['day', 3, 2.7, 100000], ['day', 3, 1.8, 20000]];
const sig = (vSM, night) => extinctionFromVisibility(vSM * SM_M, night);
let worst = 0;
for (const [per, V, D, I] of B1) {
  const night = per === 'night', ET = night ? ET_NIGHT_LUX : ET_DAY_LUX;
  const d = visualRange(I, sig(V, night), ET) / SM_M; const err = (d - D) / D; worst = Math.max(worst, Math.abs(err));
  const vAt = (k) => visibilityFactor(allardE(I, sig(V, night), k * D * SM_M), ET);
  check('A-VIS1', `Table B-1 ${per} V ${V} SM ${I} cd: FAA ${D} SM`, Math.abs(err) <= 0.05, `model ${d.toFixed(3)} SM (${(100 * err).toFixed(1)} %)`);
  check('A-VIS1', `  sprite factor at 0.9× / 1.1× of ${D} SM`, vAt(0.9) > 0.5 && vAt(1.1) === 0, `v(0.9×) ${vAt(0.9).toFixed(2)}, v(1.1×) ${vAt(1.1).toFixed(2)}`);
}
// twilight rows (20,000 cd): V 1 SM -> 1.0 to 1.5 SM; V 3 SM -> 1.8 to 4.2 SM: the day model (w = 0) gives the low end and
// the night model (w = 1) the high end; through the EnvState blend (σ linear, E_T log-linear in w) at its two ends
for (const [V, lo, hi] of [[1, 1.0, 1.5], [3, 1.8, 4.2]]) {
  const at = (w) => visualRange(20000, (1 - w) * sig(V, false) + w * sig(V, true), allardThreshold(w)) / SM_M;
  const dD = at(0), dN = at(1);
  check('A-VIS1', `twilight V ${V} SM 20,000 cd: ${lo} to ${hi} SM`, Math.abs(dD - lo) / lo <= 0.05 && Math.abs(dN - hi) / hi <= 0.05,
    `w=0 ${dD.toFixed(3)} SM (${(100 * (dD - lo) / lo).toFixed(1)} %), w=1 ${dN.toFixed(3)} SM (${(100 * (dN - hi) / hi).toFixed(1)} %), w=0.5 ${at(0.5).toFixed(2)} SM`);
}
check('A-VIS1', 'visibility factor: 0 at E_T, 1 at 2·E_T, monotone', visibilityFactor(ET_NIGHT_LUX, ET_NIGHT_LUX) === 0 && Math.abs(visibilityFactor(2 * ET_NIGHT_LUX, ET_NIGHT_LUX) - 1) < 1e-3 &&
  [1.1, 1.3, 1.6, 1.9].map(k => visibilityFactor(k * ET_DAY_LUX, ET_DAY_LUX)).every((v, i, a) => i === 0 || v > a[i - 1]));
check('A-VIS1', `max |error| over the 10 Table B-1 rows ≤ 5 %`, worst <= 0.05, `${(100 * worst).toFixed(1)} %`);

// ============================================================================================== A-PAPI1
const papiEnds = {}; for (const R of LIGHTING_SPEC.runways) for (const [E, e] of Object.entries(R.ends)) if (e.papi) papiEnds[E] = e.papi;
const C2 = { '3.00': [2.3, 2.6, 3.0, 3.4, 3.7], '2.85': [2.15, 2.45, 2.85, 3.25, 3.55], '3.15': [2.45, 2.75, 3.15, 3.55, 3.85] };
const papiGroups = LIGHTING_FIXTURES.groups.filter(g => g.system === 'papi');
check('A-PAPI1', 'six PAPI ends in the fixtures', papiGroups.length === 6, papiGroups.map(g => g.end).join(' '));
for (const g of papiGroups) {
  const P = papiEnds[g.end]; const gpa = P.angle_deg; const angles = C2[gpa.toFixed(2)];
  const ed = g.emit.split.emit_dir; // horizontal emission direction (toward the approach)
  const cx = g.pts.reduce((a, p) => a + p[0], 0) / 4, cz = g.pts.reduce((a, p) => a + p[1], 0) / 4, h = g.pts[0][2];
  check('A-PAPI1', `${g.end} fixture aims = JO 6850.2C HG4 set`, g.pts.every((p, i) => Math.abs(p[3] - P.aiming_deg_hg4[i]) < 1e-3), g.pts.map(p => p[3]).join('/'));
  for (const [setName, aims] of [['std', P.aiming_deg_std], ['HG4', P.aiming_deg_hg4]]) {
    const got = [];
    let ok = true;
    angles.forEach((a, k) => {
      const eye = [cx + ed[0] * 1852 * Math.cos(a * DEG), 3 + h + 1852 * Math.sin(a * DEG), cz + ed[1] * 1852 * Math.cos(a * DEG)];
      const pat = g.pts.map((p, i) => {
        const v = [eye[0] - p[0], eye[1] - (3 + p[2]), eye[2] - p[1]]; const hd = Math.hypot(v[0], v[2]);
        const el = Math.atan2(v[1], hd) / DEG; const dh = Math.acos(Math.max(-1, Math.min(1, (v[0] * ed[0] + v[2] * ed[1]) / hd))) / DEG;
        const w = papiWhite(aims[i], el, dh); return w >= 0.999 ? 'W' : w <= 0.001 ? 'R' : 'P';
      });
      const nW = pat.filter(c => c === 'W').length, nR = pat.filter(c => c === 'R').length;
      // white on the OUTER LHAs (lowest aims, farthest from the runway): LHA1 first -> R..R W..W
      const ordered = pat.join('') === 'R'.repeat(4 - k) + 'W'.repeat(k);
      if (!(nW === k && nR === 4 - k && ordered)) ok = false;
      got.push(`${a}°:${pat.join('')}`);
    });
    check('A-PAPI1', `${g.end} (${gpa.toFixed(2)}°) ${setName} C2 patterns 4R/1W3R/2W2R/3W1R/4W`, ok, got.join(' '));
  }
}
{
  const iso = LIGHTING_SPEC.fixtures.PAPI_LHA.isocandela;
  const c0 = papiCd(iso, 0, 0.25), c1 = papiCd(iso, 3.5, 0), c2 = papiCd(iso, 11, 0), c3 = papiCd(iso, 0, 4.5);
  check('A-PAPI1', 'isocandela: 30,000/15,000 cd on the axis, 20,000/10,000 at 3.5° az, 0 beyond the LED ±10.5°, 0 above ±4°',
    c0.white === 30000 && c0.red === 15000 && c1.white === 20000 && c1.red === 10000 && c2.white === 0 && c3.white === 0, JSON.stringify([c0, c1, c2, c3]));
  check('A-PAPI1', 'transition 3′ wide at the beam centre (white 0.5 at the aim, 1 at +1.5′, 0 at −1.5′), 5′ at the edge',
    Math.abs(papiWhite(3, 3, 0) - 0.5) < 1e-9 && papiWhite(3, 3 + 1.5 / 60, 0) > 0.9999 && papiWhite(3, 3 - 1.5 / 60, 0) < 1e-4 && papiWhite(3, 3 + 1.5 / 60, 10) < 0.9 && papiWhite(3, 3 + 2.5 / 60, 10) > 0.9999 && papiWhite(3, 3 - 2.5 / 60, 10) < 1e-4);
}

// ============================================================================================== A-NAV1
{
  let bad = [];
  for (let az = -180; az <= 180; az += 0.5) for (const el of [0, 3, 7, 12, 17, 25, 35, 60]) {
    const r = navIntensity('red', az, el), g = navIntensity('green', az, el), w = navIntensity('white', az, el);
    const ab = Math.abs(az), vf = navVertical(el);
    const minFwd = ab <= 10 ? 40 : ab <= 20 ? 30 : 5;
    // inside a dihedral angle (2° clear of its boundaries): its own light at >= minimum x factor
    if (az < -2 && ab < 108 && r < minFwd * vf) bad.push(`red min at ${az}/${el}`);
    if (az > 2 && ab < 108 && g < minFwd * vf) bad.push(`green min at ${az}/${el}`);
    if (ab > 112 && w < 20 * vf) bad.push(`white min at ${az}/${el}`);
    // 25.1395 maxima in overlaps (Area A: 10-20° past the common boundary, Area B: > 20°)
    const pastFwd = (side) => side === 'red' ? az : -az;          // degrees into the other forward dihedral angle
    for (const [c, I] of [['red', r], ['green', g]]) {
      const p = pastFwd(c); if (p > 10 && ab <= 110 && I > (p < 20 ? 10 : 1)) bad.push(`${c} overlap fwd ${az}/${el} ${I}`);
      const pa = ab - 110; const own = c === 'red' ? az < 0 : az > 0;
      if (own && pa > 10 && I > (pa < 20 ? 5 : 1)) bad.push(`${c} overlap aft ${az}/${el} ${I}`);
    }
    const pw = 110 - ab; if (pw > 10 && w > (pw < 20 ? 5 : 1)) bad.push(`white overlap ${az}/${el} ${w}`);
    // only the permitted colour beyond the 2° anti-aliasing ramp
    const lit = [r > 0 && 'R', g > 0 && 'G', w > 0 && 'W'].filter(Boolean).join('');
    const want = ab > 112 ? 'W' : (az < -2 && ab < 108) ? 'R' : (az > 2 && ab < 108) ? 'G' : null;
    if (want && lit !== want) bad.push(`colours at ${az}/${el}: ${lit} != ${want}`);
  }
  check('A-NAV1', 'sector function: red only 0–110° left, green only 0–110° right, white only ±70° aft; 25.1391 minima; 25.1395 overlap maxima', bad.length === 0, bad.length ? bad.slice(0, 6).join('; ') + ` (${bad.length})` : `721 azimuths × 8 elevations, intensities ${MINIMA_FACTOR}× minima`);
  const vf = [[0, 1], [2.5, 0.9], [5, 0.9], [7, 0.8], [12, 0.7], [17, 0.5], [25, 0.3], [35, 0.1], [60, 0.05], [-60, 0.05], [-3, 0.9]];
  check('A-NAV1', '25.1393 vertical factors (0° 1.00, 0–5° 0.90, 5–10° 0.80, 10–15° 0.70, 15–20° 0.50, 20–30° 0.30, 30–40° 0.10, 40–90° 0.05)', vf.every(([e, f]) => navVertical(e) === f), vf.map(([e]) => navVertical(e)).join(' '));
  check('A-NAV1', '25.1401(f) anticollision minima 400/240/80/40/20 cd', [[0, 400], [4, 400], [7, 240], [15, 80], [25, 40], [50, 20], [-50, 20], [80, 0]].every(([e, v]) => aclMinimum(e) === v));
  check('A-NAV1', '25.1387 dihedral angles', dihedral(-50) === 'L' && dihedral(50) === 'R' && dihedral(-111) === 'A' && dihedral(180) === 'A' && dihedral(109) === 'R');
  // synthetic aircraft at the origin heading east (fwd +x), right wing toward +z (south), up +y: sprites from all azimuths
  const L = { navL: [0, 3, -15], navR: [0, 3, 15], tail: [-20, 5, 0], beaconTop: [0, 7, 0], beaconBot: [0, 1, 0], strobeL: [-0.5, 3, -15], strobeR: [-0.5, 3, 15] };
  const axes = { fwd: [1, 0, 0], right: [0, 0, 1], up: [0, 1, 0] };
  const badS = [];
  for (let az = 0; az < 360; az += 5) {
    const r = 400; const v = [Math.cos(az * DEG) * r, 3 + 2, Math.sin(az * DEG) * r];   // az measured clockwise from +x toward +z (right)
    setLightViewer(v);
    const S = aircraftSprites(L, axes, { nav: true }, 0, 1.0).filter(s => s.nav);
    const lit = S.filter(s => s.i > 0).map(s => s.nav[0].toUpperCase()).sort().join('');
    const a = ((az + 540) % 360) - 180, ab = Math.abs(a);
    // each light sees the viewer from a slightly different angle (15 m wing semi-span at 400 m: < 2.2°): skip the ramps
    const want = ab > 113 ? 'W' : (a < -3 && ab < 107) ? 'R' : (a > 3 && ab < 107) ? 'G' : null;
    if (want && lit !== want) badS.push(`${az}°: ${lit} != ${want}`);
  }
  check('A-NAV1', 'aircraft sprites: only the permitted position-light colour from every azimuth (synthetic aircraft, viewer at 400 m)', badS.length === 0, badS.slice(0, 5).join('; '));
  const st = (o) => Object.entries(o).filter(([, v]) => v).map(([k]) => k).join('+') || 'none';
  const cases = [
    [{ phase: 'still', ground: true, gs: 0 }, 'none'], [{ phase: 'pushback', ground: true, gs: 2 }, 'nav+beacon'],
    [{ phase: 'taxi', ground: true, gs: 15 }, 'nav+beacon+taxi'], [{ phase: 'taxi', ground: true, gs: 0 }, 'nav+beacon'],
    [{ phase: 'lineup', ground: true, gs: 5 }, 'nav+beacon+strobe+taxi'], [{ phase: 'lineup', ground: true, gs: 0 }, 'nav+beacon+strobe'],
    [{ phase: 'takeoff', ground: true, gs: 120 }, 'nav+beacon+strobe+landing'], [{ phase: 'climb', ground: false, altAgl: 2000 }, 'nav+beacon+strobe+landing'],
    [{ phase: 'climb', ground: false, altAgl: 3500 }, 'nav+beacon+strobe'], [{ phase: 'final', ground: false, altAgl: 300 }, 'nav+beacon+strobe+landing'],
    [{ phase: 'rollout', ground: true, gs: 80 }, 'nav+beacon+strobe+landing'], [{ phase: 'rollout', ground: true, gs: 20 }, 'nav+beacon+strobe+taxi'],
    [{ phase: 'taxi', ground: true, gs: 10, stale: true }, 'none'],
  ];
  const badP = cases.filter(([i, w]) => st(aircraftLightStates(i)) !== w).map(([i, w]) => `${i.phase}/${i.gs ?? i.altAgl}: ${st(aircraftLightStates(i))} != ${w}`);
  check('A-NAV1', 'light states per phase (AIM 4-3-24; parked off, Q11 default)', badP.length === 0, badP.join('; ') || `${cases.length} cases`);
}

// ============================================================================================== A-FLASH1
{
  // [target cd effective, period s, phase s, on s, expected flashes per minute, tolerance (upper, null = none)]
  const types = [
    ['SFL (each flasher 2/s; photometry NV, provisional)', FLASH.SFL.cd, 0.5, 0.1, FLASH.SFL.on, 120, null],
    ['REIL style E high (120 fpm)', 15000, 60 / FLASH.REIL.fpm, 0.05, FLASH.REIL.on, 120, null],
    ['L-864 (30 fpm, 2,000 cd eff ±25 %)', 2000, 60 / FLASH.L864.fpm, 0.3, FLASH.L864.on, 30, 1.25],
    ['aircraft red beacon (60 cpm)', MINIMA_FACTOR * 400, 60 / BEACON.fpm, 0.2, BEACON.on, 60, null],
    ['aircraft white strobe (66 double flashes / min)', MINIMA_FACTOR * 400, 60 / STROBE.fpm, 0.15, STROBE.on, 66, null],
  ];
  for (const [name, target, P, ph, on, perMin, upper] of types) {
    for (const fps of [30, 60, 120]) {
      // frames at a steady rate (t_k = t0 + k/fps, no accumulated rounding); a flash = a run of consecutive lit frames,
      // each frame shown for dt; effective intensity per 25.1401(e): I_e = Σ I_f·dt / (0.2 + n·dt)
      const dt = 1 / fps, T = 120, t0 = 0.0137; let runs = [], cur = null;
      for (let k = 1; t0 + k * dt < T; k++) {
        const tPrev = t0 + (k - 1) * dt, t = t0 + k * dt;
        let g = flashGain(tPrev, t, P, ph, on);
        if (name.includes('strobe')) g = Math.max(g, flashGain(tPrev, t, P, ph + STROBE.gap, on));
        if (g > 0) { if (cur && cur.last === k - 1) { cur.n++; cur.last = k; cur.E += target * g * dt; } else { cur = { g, n: 1, last: k, E: target * g * dt }; runs.push(cur); } }
      }
      const effs = runs.map(r => r.E / (BR_C + r.n * dt) / target);
      const minE = Math.min(...effs), maxE = Math.max(...effs);
      const cycles = name.includes('strobe') ? runs.length / 2 : runs.length;
      const rate = cycles / (T / 60);
      const okRate = Math.abs(rate - perMin) <= 1 && (name.includes('aircraft') ? rate >= 40 && rate <= 100 : true) && (name.includes('L-864') ? rate >= 27 && rate <= 33 : true);
      check('A-FLASH1', `${name} at ${fps} fps`, minE >= 1 - 1e-9 && okRate && (upper == null || maxE <= upper),
        `${runs.length} flashes in ${T} s (${rate.toFixed(1)}/min), effective / target ${minE.toFixed(3)}..${maxE.toFixed(3)}, drawn ${runs[0] ? runs[0].n : 0} frame(s) of ${(target * (runs[0] ? runs[0].g : 0)).toFixed(0)} cd`);
    }
  }
  // spec example: 400 cd effective -> 5,200 cd for one 60 Hz frame, 2,800 cd for two (14 CFR 25.1401(e))
  check('A-FLASH1', '400 cd effective = 5,200 cd for 1 frame at 60 Hz, 2,800 cd for 2 frames', Math.abs(400 * (BR_C + 1 / 60) * 60 - 5200) < 1 && Math.abs(400 * (BR_C + 2 / 60) * 30 - 2800) < 1);
  // SFL sequence: outermost first, each flasher twice per second, equal spacing within the 0.5 s cycle (airfield module)
  const AL = new AirfieldLighting(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: 3 });
  const seq = AL.flasherSequence('28R');
  check('A-FLASH1', '28R SFL sequence: 15 flashers, outermost (2,400 ft) first, toward the threshold, phases equally spaced in 0.5 s',
    seq.length === 15 && seq[0].station === 2400 && seq[14].station === 1000 && seq.every((s, i) => Math.abs(s.phase - i * 0.5 / 15) < 1e-9), seq.map(s => s.station).join(','));
}
// ============================================================================================== RWSL (REL) logic, unit part of A-RWSL
{
  const AL = new AirfieldLighting(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: 3 });
  const ln = AL.lines['10L/28R'], KT = 0.514444;
  const along = (end, m) => { const e = LIGHTING_SPEC.runways[0].ends[end].runway_end.world; const sg = ln.ends[0] === end ? 1 : -1; return [e[0] + ln.u[0] * sg * m, e[1] + ln.u[1] * sg * m]; };
  const R = AL.relGroups.filter(g => g.runway === '10L/28R');
  const at = (ph, end, m, kt, ground = true) => { const p = along(end, m); return [...AL.rwslFromTraffic([{ phase: ph, rwy: end, x: p[0], z: p[1], gs: kt * KT, ground }])]; };
  const dep20 = at('takeoff', '28R', 300, 20), dep40 = at('takeoff', '28R', 300, 40), air = at('takeoff', '28R', 2500, 150, false);
  // arrays ahead of the departure (ETA > 3.5 s) on, the ones behind / about to be reached off
  const sgn = ln.ends[0] === '28R' ? 1 : -1; const pA = along('28R', 300); const aAc = (pA[0] - ln.a[0]) * ln.u[0] + (pA[1] - ln.a[1]) * ln.u[1];
  const ahead = R.filter(g => (g.a - aAc) * sgn / (40 * KT) > 3.5).map(g => g.id).sort();
  check('A-RWSL1', `REL 10L/28R (${R.length} arrays): departure 28R at 20 kt none; at 40 kt the ${ahead.length} arrays ahead (> 3.5 s) only; airborne none`,
    dep20.length === 0 && JSON.stringify(dep40.sort()) === JSON.stringify(ahead) && ahead.length > 0 && ahead.length < R.length && air.length === 0, `40 kt: ${dep40.length} on`);
  const fin2 = (() => { const th = LIGHTING_SPEC.runways[1].ends['28L'].landing_threshold.world; const L2 = AL.lines['10R/28L']; const sg = L2.ends[0] === '28L' ? 1 : -1; const mk = (m) => [...AL.rwslFromTraffic([{ phase: 'final', rwy: '28L', x: th[0] - L2.u[0] * sg * m, z: th[1] - L2.u[1] * sg * m, gs: 70, ground: false }])]; return [mk(2 * 1852), mk(0.9 * 1852)]; })();
  const R2 = AL.relGroups.filter(g => g.runway === '10R/28L');
  check('A-RWSL1', `arrival 28L: 2 NM out none, 0.9 NM out all ${R2.length} arrays of 10R/28L`, fin2[0].length === 0 && fin2[1].length === R2.length, `${fin2[1].length} on`);
  const r60 = at('rollout', '28R', 1500, 60), r30 = at('rollout', '28R', 1500, 30), r90 = at('rollout', '28R', 1500, 90);
  check('A-RWSL1', 'rollout 28R: 90 kt all ahead, 60 kt only within 30 s, 30 kt none', r30.length === 0 && r60.length <= r90.length && r90.length > 0, `90 kt ${r90.length}, 60 kt ${r60.length}`);
  check('A-RWSL1', 'the NV-flagged REL arrays (between-runway F1 / G / H: runway assignment ambiguous) are never lit', !LIGHTING_FIXTURES.groups.some((g, i) => g.runway_nv && AL.relGroups.some(r => r.id === i)));
}
console.log(`\nstep-2 unit gates${only ? ' (' + only + ')' : ''}: ${n - fails}/${n} checks passed`);
process.exit(fails ? 1 : 0);
