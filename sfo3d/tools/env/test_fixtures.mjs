// Gate A-FIX (docs/research/environment_spec.md §11.3): the fixture loader (js/env/lighting/fixtures.js) yields the
// §5.2 counts and face colours (e.g. 28R edge faces W 96 / Y 20 / R 2) and every sprite carries prov.
// Expected numbers are transcribed from the spec's §5.2 tables (verifier-regenerated counts), plus the D1 REL arrays
// (28 labels on the FAA graphic, 2 retired F1 labels not expanded) and the D2/D3 text fixes.
// Run: node tools/env/test_fixtures.mjs   (exit 1 on failure)
import { LIGHTING_SPEC, LIGHTING_FIXTURES } from '../../data/sfo_lighting.js';
import { loadFixtures, provCounts } from '../../js/env/lighting/fixtures.js';

let fails = 0, n = 0;
const check = (name, got, want) => { n++; const ok = JSON.stringify(got) === JSON.stringify(want); if (!ok) fails++; console.log(`${ok ? 'PASS' : 'FAIL'} | ${name} | got ${JSON.stringify(got)}${ok ? '' : ' want ' + JSON.stringify(want)}`); };

const L = loadFixtures(LIGHTING_FIXTURES, LIGHTING_SPEC, { groundY: 3 });
const F = L.counts.faces;
const face = (sys, end, seen) => { const o = { ...(F[sys + '|' + end + '|' + seen] || {}) }; return Object.fromEntries(Object.entries(o).sort()); };
const fix = (sys, end) => LIGHTING_FIXTURES.groups.filter(g => g.system === sys && (end == null || g.end === end)).reduce((a, g) => a + g.n, 0);

// §5.2 edge lights: fixtures and faces
check('edge 10L/28R n', fix('runway_edge', '10L/28R'), 118);
check('edge 10L/28R faces seen by 10L', face('runway_edge', '10L/28R', '10L'), { W: 98, Y: 20 });
check('edge 10L/28R faces seen by 28R', face('runway_edge', '10L/28R', '28R'), { R: 2, W: 96, Y: 20 });
check('edge 10R/28L n', fix('runway_edge', '10R/28L'), 112);
check('edge 10R/28L faces 10R', face('runway_edge', '10R/28L', '10R'), { W: 92, Y: 20 });
check('edge 10R/28L faces 28L', face('runway_edge', '10R/28L', '28L'), { R: 2, W: 90, Y: 20 });
check('edge 1L/19R n', fix('runway_edge', '1L/19R'), 76);
check('edge 1L/19R faces 1L', face('runway_edge', '1L/19R', '1L'), { R: 6, W: 70 });
check('edge 1L/19R faces 19R', face('runway_edge', '1L/19R', '19R'), { W: 56, Y: 20 });
check('edge 1R/19L n', fix('runway_edge', '1R/19L'), 86);
check('edge 1R/19L faces 1R', face('runway_edge', '1R/19L', '1R'), { R: 4, W: 82 });
check('edge 1R/19L faces 19L', face('runway_edge', '1R/19L', '19L'), { W: 66, Y: 20 });
// §5.2 centreline lights
check('RCL 10L/28R n', fix('runway_centreline', '10L/28R'), 235);
check('RCL 10L/28R faces 10L', face('runway_centreline', '10L/28R', '10L'), { R: 39, W: 196 });
check('RCL 10L/28R faces 28R', face('runway_centreline', '10L/28R', '28R'), { '-': 5, R: 39, W: 191 });
check('RCL 10R/28L n', fix('runway_centreline', '10R/28L'), 226);
check('RCL 10R/28L faces 10R', face('runway_centreline', '10R/28L', '10R'), { R: 39, W: 187 });
check('RCL 10R/28L faces 28L', face('runway_centreline', '10R/28L', '28L'), { '-': 5, R: 39, W: 182 });
check('RCL 1L/19R n', fix('runway_centreline', '1L/19R'), 151);
check('RCL 1L/19R faces 1L', face('runway_centreline', '1L/19R', '1L'), { '-': 12, R: 39, W: 100 });
check('RCL 1L/19R faces 19R', face('runway_centreline', '1L/19R', '19R'), { R: 39, W: 112 });
check('RCL 1R/19L n', fix('runway_centreline', '1R/19L'), 171);
check('RCL 1R/19L faces 1R', face('runway_centreline', '1R/19L', '1R'), { '-': 10, R: 39, W: 122 });
check('RCL 1R/19L faces 19L', face('runway_centreline', '1R/19L', '19L'), { R: 39, W: 132 });
// §5.2 per-end systems
const als = (E) => ['als_centreline_bar', 'als_side_row', 'als_500ft_bar', 'als_1000ft_bar', 'als_threshold_bar', 'als_flasher'].map(s => fix(s, E));
check('ALS 28R ALSF-2 [CL bar, side row, 500, 1000, thr green, SFL]', als('28R'), [120, 54, 8, 16, 59, 15]);
check('ALS 28L MALSR [CL, -, -, 1000 crossbar, thr green, RAIL]', als('28L'), [35, 0, 0, 10, 23, 5]);
check('ALS 19L MALSF [CL, -, -, 1000 crossbar, thr green, SFL]', als('19L'), [35, 0, 0, 10, 23, 3]);
check('ALS totals 28R/28L/19L', ['28R', '28L', '19L'].map(E => als(E).reduce((a, b) => a + b, 0)), [272, 73, 71]);
check('TDZ 28R, 19L', [fix('tdz', '28R'), fix('tdz', '19L')], [180, 180]);
check('threshold/end per end (10L 10R 19L 19R)', ['10L', '10R', '19L', '19R'].map(E => fix('threshold_end', E)), [8, 8, 8, 8]);
check('red end bars at displaced ends (28R 28L 1L 1R)', ['28R', '28L', '1L', '1R'].map(E => fix('runway_end', E)), [8, 8, 8, 8]);
check('wing bars at displaced ends (28R 28L 1L 1R)', ['28R', '28L', '1L', '1R'].map(E => fix('threshold_wingbar', E)), [8, 8, 8, 8]);
check('threshold/end split faces (19L: G to 19L, R to 1R)', [face('threshold_end', '19L', '19L'), face('threshold_end', '19L', '1R')], [{ G: 8 }, { R: 8 }]);
check('PAPI per end (28R 28L 19L 19R 10L 10R)', ['28R', '28L', '19L', '19R', '10L', '10R'].map(E => fix('papi', E)), [4, 4, 4, 4, 4, 4]);
check('REIL (10L 1L 1R)', ['10L', '1L', '1R'].map(E => fix('reil', E)), [2, 2, 2]);
check('THL per end (10L 10R 28L 28R 1L 1R)', ['10L', '10R', '28L', '28R', '1L', '1R'].map(E => fix('rwsl_thl', E)), [32, 32, 32, 32, 32, 32]);
const T = LIGHTING_SPEC.fixture_counts;
const tot = (keys) => keys.reduce((a, k) => a + (T[k] || 0), 0);
check('§5.2 totals [edge, RCL, TDZ, thr/end/wing, ALS, PAPI, REIL, THL]',
  [T.runway_edge, T.runway_centreline, T.tdz, tot(['threshold_end', 'runway_end', 'threshold_wingbar']), tot(['als_centreline_bar', 'als_side_row', 'als_500ft_bar', 'als_1000ft_bar', 'als_threshold_bar', 'als_flasher']), T.papi, T.reil, T.rwsl_thl],
  [392, 783, 360, 96, 416, 24, 6, 192]);
check('§5.2 total without REL', Object.entries(T).filter(([k]) => k !== 'rwsl_rel').reduce((a, [, v]) => a + v, 0), 2269);
// D1: 28 REL labels; arrays expanded per AC 150/5340-30J App. G
const R = LIGHTING_SPEC.rwsl;
check('D1 REL labels (FAA graphic)', R.rel.length, 28);
check('D1 taxiway N on 10R/28L present + snapped', R.rel.filter(e => e.taxiway === 'N' && e.runway === '10R/28L').map(e => !!e.hold), [true]);
check('D1 REL arrays expanded / not expanded (retired F1 crossing)', [R.rel_arrays.filter(a => a.n > 0).length, R.rel_arrays.filter(a => a.n === 0).map(a => a.taxiway)], [26, ['F1', 'F1']]);
check('D1 every expanded array >= 6 lights, spacing 12.5-50 ft', R.rel_arrays.filter(a => a.n > 0).every(a => a.n >= 6 && a.spacing_ft >= 12.5 && a.spacing_ft <= 50), true);
check('D1 ambiguous between-runway labels flagged NV (taxiways)', R.rel.filter(e => e.runway_nv).map(e => e.taxiway).sort(), ['F1', 'G', 'H']);
check('D1 REL fixture count = sum of arrays', fix('rwsl_rel'), R.rel_arrays.reduce((a, b) => a + b.n, 0));
// D2 / D3
const e28R = LIGHTING_SPEC.runways.find(r => r.id === '10L/28R').ends['28R'];
check('D2 28R pier far end note (~2650 ft NAIP edge, caps to ~2600 ft)', /2650 ft/.test(e28R.als_detail.piers_observed.far_end_ft) && /2600 ft/.test(e28R.als_detail.piers_observed.far_end_ft), true);
const twr = LIGHTING_SPEC.obstructions.find(o => o.type === 'CTRL TWR');
check('D3 tower obstruction lights cite AC 70/7460-1N 5.6 (>= 3 L-864 + mid-level steady red)', [/5\.6\.2\.2/.test(twr.fixture_inferred), !/5\.5/.test(twr.fixture_inferred), twr.fixture_inferred_levels.map(l => l.type)], [true, true, ['L-864', 'L-810']]);
// every sprite carries prov; colours are EB 67D lin sRGB
check('every record carries prov + provClass', L.records.every(r => typeof r.prov === 'string' && r.prov.length > 0 && ['pub', 'std', 'inf', 'NV'].includes(r.provClass)), true);
check('record count = emitting faces', L.records.length, L.records.filter(r => r.colour && r.colour !== '-').length);
check('edge white colour = EB 67D centroid lin sRGB', L.records.find(r => r.system === 'runway_edge' && r.colour === 'W').c, LIGHTING_SPEC.colours.white.lin_srgb);
check('ALS on the light plane (28R thr 12.9 ft vs field 13.1 ft: y within 0.1 m of ground)', Math.abs(L.records.find(r => r.system === 'als_centreline_bar' && r.end === '28R').p[1] - 3) < 0.1, true);
const pc = provCounts(L.records);
console.log('INFO | records', L.records.length, '| prov classes', JSON.stringify(pc));
console.log(`\n${fails ? 'FAILED' : 'ALL PASSED'} (${n - fails}/${n})`);
process.exit(fails ? 1 : 0);
