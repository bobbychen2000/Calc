// Gate A-WX (docs/research/environment_spec.md §11.3): the JS METAR decoder (js/env/wx/metar.js) reproduces
// tools/env/metar_decode.py on all 58 fixtures and the 38 test cases (deep-equal output).
// Golden vectors: tools/env/fixtures/metar_golden.json, written by tools/env/build_metar_golden.py, which runs the 38
// Python unit tests with the decoder's public functions wrapped (every call + result recorded) and adds, for each of the
// 58 fixture reports and the 14 presets, decode_metar with / without a reference date and render_params by day / night.
// Equality: same keys, same types, strings / booleans / null identical, numbers equal within 1e-9 relative (Python
// tuples = JS arrays). Also checks that the old regex parseMetar is gone from js/.
// Run: node tools/env/test_metar_js.mjs   (exit 1 on failure)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { decodeMetar, decodeTaf, renderParams, extinctionFromVisibility } from '../../js/env/wx/metar.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const G = JSON.parse(fs.readFileSync(path.join(HERE, 'fixtures', 'metar_golden.json'), 'utf8'));
const unser = (v) => (v && typeof v === 'object' && v.__datetime__ ? new Date(v.__datetime__) : v);
const FN = {
  decode_metar: (a, k) => decodeMetar(a[0], unser(a[1] ?? k.ref ?? null)),
  decode_taf: (a) => decodeTaf(a[0]),
  render_params: (a, k) => renderParams(a[0], a[1] ?? k.night ?? false, a[2] ?? k.marine_layer_depth_ft ?? null, a[3] ?? k.routine_minute ?? 56),
  extinction_from_visibility: (a, k) => extinctionFromVisibility(a[0], a[1] ?? k.night ?? false, a[2] ?? k.contrast ?? 0.055),
};
let maxRel = 0;
function diff(a, b, p = '$') {
  if (typeof a === 'number' && typeof b === 'number') {
    if (a === b) return null;
    const rel = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b), 1e-300);
    maxRel = Math.max(maxRel, rel);
    return rel <= 1e-9 ? null : `${p}: ${a} != ${b}`;
  }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return a === b ? null : `${p}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`;
  if (Array.isArray(a) !== Array.isArray(b)) return `${p}: array vs object`;
  if (Array.isArray(a)) {
    if (a.length !== b.length) return `${p}: length ${a.length} != ${b.length}`;
    for (let i = 0; i < a.length; i++) { const d = diff(a[i], b[i], `${p}[${i}]`); if (d) return d; }
    return null;
  }
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  if (JSON.stringify(ka) !== JSON.stringify(kb)) return `${p}: keys ${JSON.stringify(ka.filter(k => !kb.includes(k)))} extra, ${JSON.stringify(kb.filter(k => !ka.includes(k)))} missing`;
  for (const k of ka) { const d = diff(a[k], b[k], `${p}.${k}`); if (d) return d; }
  return null;
}
const stats = {};
let fails = 0;
for (const c of G.calls) {
  const key = c.fn + ' (' + c.from + ')';
  stats[key] ||= { n: 0, ok: 0 };
  stats[key].n++;
  let got, err = null;
  try { got = FN[c.fn](JSON.parse(JSON.stringify(c.args)), c.kwargs || {}); } catch (e) { err = String(e && e.stack || e); }
  const d = err || diff(JSON.parse(JSON.stringify(got === undefined ? null : got)), c.result);
  if (d) { fails++; if (fails <= 15) console.log('FAIL |', c.fn, JSON.stringify(c.args[0]).slice(0, 120), '|', d); } else stats[key].ok++;
}
for (const [k, v] of Object.entries(stats)) console.log(`${v.ok === v.n ? 'PASS' : 'FAIL'} | ${k} | ${v.ok}/${v.n} deep-equal`);
// distinct reports covered
const rep = new Set(G.calls.filter(c => c.fn === 'decode_metar').map(c => c.args[0]));
console.log(`INFO | python tests run ${G.tests_run} (all passed when the golden was written); fixture reports ${G.fixture_reports}, presets ${G.preset_reports}; distinct METAR strings decoded ${rep.size}; max relative number difference ${maxRel.toExponential(2)}`);
// the old regex parser must be gone (spec A-WX: "parseMetar is deleted")
const offenders = [];
const walk = (dir) => { for (const f of fs.readdirSync(dir, { withFileTypes: true })) { const p = path.join(dir, f.name); if (f.isDirectory()) walk(p); else if (/\.(m?js|html)$/.test(f.name) && /function parseMetar\b|parseMetar\s*\(/.test(fs.readFileSync(p, 'utf8'))) offenders.push(path.relative(path.join(HERE, '..', '..'), p)); } };
walk(path.join(HERE, '..', '..', 'js'));
console.log(`${offenders.length ? 'FAIL' : 'PASS'} | old regex parseMetar removed from js/ | ${offenders.length ? offenders.join(', ') : 'none left'}`);
if (offenders.length) fails++;
console.log(`\n${fails ? 'FAILED (' + fails + ')' : 'ALL PASSED'} (${G.calls.length} recorded calls)`);
process.exit(fails ? 1 : 0);
