// Check js/env/wx/metar_zsss.js (the browser twin) against tools/wx/metar_zsss.py (the reference):
//  1. every decoded field of every report: built-in examples, data/sha_snapshot.js, and - when the local caches exist -
//     the AWC 30-day files and the IEM archive 2023-2026 (refs/cache/metar/, local);
//  2. both runway-direction rules stepped over the IEM sequence: the JS direction equals the Python direction after every
//     report, and the agreement with the RVR / wind-shear runway designators reproduces docs/phase1/sources_sim.md s.5.2
//     (146/169 chosen rule, 136/169 "into the wind");
//  3. the trend is never applied to the observation (BECMG / TEMPO cloud groups stay in trend[]);
//  4. runwayMode() / assignRunways() basics (segregated mode, night landing rule, closures).
// Usage: node sha3d/tools/wx/test_metar_zsss_js.mjs        (about 10 s with the IEM archive)
import fs from 'fs'; import path from 'path'; import os from 'os'; import { execFileSync } from 'child_process'; import { fileURLToPath } from 'url';
import { decode, RunwayDirection, RunwayDirectionIntoWind, runwayMode, assignRunways, windText } from '../../js/env/wx/metar_zsss.js';

const HERE = path.dirname(fileURLToPath(import.meta.url)); const ROOT = path.resolve(HERE, '..', '..');
let fails = 0; const fail = (m) => { fails++; if (fails < 25) console.log('FAIL', m); };
const ok = (c, m) => { if (!c) fail(m); };

// ---------------------------------------------------------------- report sets
const EXAMPLES = [
  'METAR ZSSS 140500Z 05002MPS 010V080 8000 -RA BKN020 19/17 Q1015 NOSIG',
  'METAR ZSSS 140200Z 01002MPS 340V040 4500 -RA BR BKN006 18/17 Q1017 BECMG TL0340 BKN011',
  'METAR ZSSS 132300Z 34003MPS 2500 -RA BR BKN004 18/17 Q1017 BECMG TL0010 3000 BKN005',
  'METAR ZSSS 202200Z VRB01MPS CAVOK 06/00 Q1028 NOSIG',
  'SPECI ZSSS 010712Z 33008G15MPS 1200 R36R/1300D R36L/P2000N +TSRA FEW012CB BKN020 25/23 Q1004 WS R36R TEMPO 0800 TSRA',
  'METAR ZSSS 050000Z 00000MPS 0400 R18L/0550U FG VV001 08/08 Q1030 BECMG FM0030 TL0130 1500 BR',
  'METAR ZSSS 050030Z 18004KT 3000 BR NSC M01/M03 A3012 RMK TEST',
  'METAR ZSSS 050100Z /////MPS //// NCD ///// Q////',
  'ZSSS 010030Z 19002MPS 5000 HZ NSC 06/01 Q1033 NOSIG',
];
const raws = [...EXAMPLES];
const SNAP = path.join(ROOT, 'data', 'sha_snapshot.js');
if (fs.existsSync(SNAP)) { const t = fs.readFileSync(SNAP, 'utf8'); const j = JSON.parse(t.slice(t.indexOf('{'), t.lastIndexOf('}') + 1)); for (const m of j.metars || []) raws.push(m.rawOb); }
const AWC = path.join(ROOT, 'refs', 'cache', 'metar', 'awc_30d');
if (fs.existsSync(AWC)) for (const f of fs.readdirSync(AWC).sort()) for (const l of fs.readFileSync(path.join(AWC, f), 'utf8').split('\n')) if (l.trim()) raws.push(l.trim());
const haveIem = fs.existsSync(path.join(ROOT, 'refs', 'cache', 'metar', 'iem_zsss'));

// ---------------------------------------------------------------- Python reference
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'metar_zsss_')); const inF = path.join(tmp, 'in.json'), outF = path.join(tmp, 'out.json');
fs.writeFileSync(inF, JSON.stringify(raws));
const PY = `
import json, sys, os
root = sys.argv[1]; sys.path.insert(0, os.path.join(root, 'tools', 'wx'))
sys.argv = sys.argv[:1] + [root]
import metar_zsss as M
raws = json.load(open(${JSON.stringify(inF)}))
out = {'decoded': [M.decode(r) for r in raws], 'iem': None}
if os.path.isdir(os.path.join(root, 'refs', 'cache', 'metar', 'iem_zsss')):
    import metar_stats as S
    reps = S.iem_reports()
    a, b = M.RunwayDirection('36'), M.RunwayDirectionIntoWind('36')
    out['iem'] = [{'raw': d['raw'], 'd': d, 'tail': a.step(d.get('wind'))[0], 'into': b.step(d.get('wind'))[0]} for t, d in reps]
json.dump(out, open(${JSON.stringify(outF)}, 'w'))
`;
execFileSync('python3', ['-I', '-c', PY, ROOT], { stdio: ['ignore', 'inherit', 'inherit'], maxBuffer: 1 << 30 });
const ref = JSON.parse(fs.readFileSync(outF, 'utf8')); fs.rmSync(tmp, { recursive: true, force: true });

// ---------------------------------------------------------------- deep compare (numbers to 1e-9)
function same(a, b, p = '') {
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a)) ? null : `${p}: ${a} != ${b}`;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return a === b ? null : `${p}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
  if (Array.isArray(a) !== Array.isArray(b)) return `${p}: array mismatch`;
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  if (ka.join() !== kb.join()) return `${p}: keys ${ka} != ${kb}`;
  for (const k of ka) { const r = same(a[k], b[k], p + '.' + k); if (r) return r; }
  return null;
}
let n = 0;
raws.forEach((r, i) => { const e = same(decode(r), ref.decoded[i], r); n++; if (e) fail(e); });
console.log(`decode: ${n} reports (examples ${EXAMPLES.length}, snapshot + AWC 30 d ${raws.length - EXAMPLES.length}) compared with metar_zsss.py`);

// ---------------------------------------------------------------- trend never applied
{ const d = decode(EXAMPLES[1]);
  ok(d.sky.length === 1 && d.sky[0].cover === 'BKN' && d.sky[0].base_ft === 600, 'BECMG BKN011 must not be an observed layer');
  ok(d.trend[0].kind === 'BECMG' && d.trend[0].tl === '0340' && d.trend[0].elements.sky[0].base_ft === 1100, 'trend decoded apart');
  const s = decode(EXAMPLES[4]);
  ok(s.wind.speed_ms === 8 && s.wind.gust_ms === 15 && s.vis_m === 1200 && s.qnh_hpa === 1004, 'MPS / metres / hPa kept');
  ok(s.trend[0].kind === 'TEMPO' && s.trend[0].elements.vis_m === 800 && s.vis_m === 1200, 'TEMPO visibility not applied');
  ok(decode(EXAMPLES[0]).vis_m === 8000 && decode(EXAMPLES[3]).cavok === true && decode(EXAMPLES[3]).vis_m === 10000, 'visibility metres / CAVOK');
  ok(windText(s.wind) === '330° 8 m/s G15', 'windText ' + windText(s.wind));
}

// ---------------------------------------------------------------- the rules over the IEM archive
if (ref.iem) {
  const a = new RunwayDirection('36'), b = new RunwayDirectionIntoWind('36');
  const hint = (raw) => { const ds = new Set([...raw.matchAll(/ R(\d{2}[LR])\/[PM]?\d{4}/g)].map(m => m[1].slice(0, 2)).concat([...raw.matchAll(/WS R(\d{2}[LR])/g)].map(m => m[1].slice(0, 2))));
    return ds.size === 1 ? [...ds][0] : null; };
  let k = 0, agreeA = 0, agreeB = 0, nh = 0, diffDec = 0;
  for (const r of ref.iem) {
    const d = decode(r.raw); if (same(d, r.d)) { diffDec++; if (diffDec < 5) fail('IEM decode ' + same(d, r.d)); }
    const da = a.step(d.wind || null)[0], db = b.step(d.wind || null)[0];
    if (da !== r.tail) fail(`tail rule differs at ${r.raw}`); if (db !== r.into) fail(`into-wind rule differs at ${r.raw}`);
    const h = hint(r.raw); if (h) { nh++; if (h === da) agreeA++; if (h === db) agreeB++; }
    k++;
  }
  console.log(`IEM: ${k} reports; decode differences ${diffDec}; rule directions equal to Python after every report`);
  console.log(`hints ${nh}: tail-wind rule ${agreeA}/${nh} = ${(100 * agreeA / nh).toFixed(1)} %, into the wind ${agreeB}/${nh} = ${(100 * agreeB / nh).toFixed(1)} %`);
  ok(nh === 169 && agreeA === 146 && agreeB === 136, 'agreement must reproduce sources_sim.md s.5.2 (146/169, 136/169)');
} else console.log('IEM archive not present (refs/cache/metar/iem_zsss is local): rule check on the archive skipped');

// ---------------------------------------------------------------- runwayMode / assignRunways
{ // south wind 4.5 m/s on north flow: one report > 4.0 m/s turns to 18
  const m = runwayMode([{ rawOb: 'METAR ZSSS 140000Z 18005MPS 9999 FEW030 20/10 Q1015 NOSIG', obsTime: 1794614400 }]);
  ok(m.dir === '18' && m.arr[0] === '18L' && m.dep[0] === '18R' && m.flow === 'south' && m.tag === 'inf', 'runwayMode south ' + JSON.stringify(m));
  const m2 = runwayMode(['METAR ZSSS 140000Z 18002MPS 9999 FEW030 20/10 Q1015 NOSIG']);
  ok(m2.dir === '36', 'one report of 2 m/s tail wind keeps 36');
  const m3 = runwayMode(['METAR ZSSS 140000Z 18002MPS 9999 FEW030 20/10 Q1015 NOSIG', 'METAR ZSSS 140030Z 18002MPS 9999 FEW030 20/10 Q1015 NOSIG'].map((r, i) => ({ rawOb: r, obsTime: 1794614400 + i * 1800 })));
  ok(m3.dir === '18', 'two reports of 2 m/s tail wind turn to 18');
  ok(runwayMode(['METAR ZSSS 140000Z 18002MPS 9999 FEW030 20/10 Q1015 NOSIG'], { rule: 'intowind' }).dir === '18', 'into the wind turns at once');
  const n1 = assignRunways('36', Date.UTC(2026, 10, 20, 18), ['18L/36R']); ok(n1.arr.length === 0 && n1.dep[0] === '36L', 'night closure: no landings on 36L');
  const n2 = assignRunways('36', Date.UTC(2026, 10, 20, 6), ['18L/36R']); ok(n2.arr[0] === '36L' && n2.dep[0] === '36L', 'day closure: single runway');
}
console.log(fails ? `${fails} FAILURES` : 'all passed');
process.exitCode = fails ? 1 : 0;
