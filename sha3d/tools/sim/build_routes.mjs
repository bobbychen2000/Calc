// sha3d Phase 3 (P3-B): build the precomputed route table data/sha_routes.json / .js (window.SHA_ROUTES) with the same router
// the browser runs (js/sim/router.js). Deterministic: no clock, no randomness, fixed iteration orders; `md5sum` of two runs is
// identical (tools/sim/test_router.mjs checks it).
//
//   node tools/sim/build_routes.mjs            # from sha3d/ (or any cwd): writes data/sha_routes.json, .js, data/SOURCES_routes.json
//   node tools/sim/build_routes.mjs --out DIR   # write elsewhere (the determinism test)
//
// Contents (design §4.1, §7.1): departures 164 stands x 4 take-off ends (full length) + the intersection entries 18R via H2 /
// 36L via H6; arrivals per landing end x named rapid exit (the exit model's first and second per side, plus the third as its
// fallback) x stand on the exit's side, per span class (n < 36 m; w 36-65 m and x >= 65 m only where they differ); the
// F4552 closure variant for the routes of the 18R/36L ends that use a closed link (18L/36R itself is closed by F4551 in the
// same window). Link sequences are stored as tries (shared prefixes / suffixes); the integer geometry (pieces, blocks, holds)
// is rebuilt from them by js/sim/router.js + js/sim/path.js without trigonometry, and the per-route lengths stored here let
// the browser verify that its rebuild matches node's.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { makeRouter, closedLinksFor, graphFingerprint, END_IDS, ROUTER } from '../../js/sim/router.js';
import { runwayGeom } from '../../js/sim/traj.js';
import { PATH } from '../../js/sim/path.js';
import { PERF } from '../../js/sim/perf.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const args = process.argv.slice(2);
const OUT = args.includes('--out') ? path.resolve(args[args.indexOf('--out') + 1]) : path.join(ROOT, 'data');
const QUIET = args.includes('--quiet');
const log = (...a) => { if (!QUIET) console.log(...a); };

const read = (f) => fs.readFileSync(path.join(ROOT, 'data', f));
const sha16 = (buf) => crypto.createHash('sha256').update(buf).digest('hex').slice(0, 16);
const rawG = read('sha_taxigraph.json'), rawS = read('sha_stands.json'), rawA = read('sha_airport.json');
const G = JSON.parse(rawG), S = JSON.parse(rawS), A = JSON.parse(rawA);

// ---------------------------------------------------------------------------------------- the F4552 effect record
// Derived effect record (ids, window, targets only; sources_sim.md §4.2 "Committed form"; OD3 short facts): the taxiway
// targets of NOTAM F4552/26 as listed in the eAIP NOTAM Summary in force 2026-11-02 07:06Z, paraphrased as targets.
export const F4552 = {
  id: 'F4552/26', window: { from: '2026-11-10T17:00Z', to: '2026-11-29T22:00Z', daily: ['17:00', '22:00'] },
  targets: [
    { twy: ['A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'T6', 'K2', 'K4', 'K5', 'K6', 'K7'] },
    { twy: ['A', 'B'], between: ['H4', 'H7'] },
    { twy: ['H2', 'H3', 'H5', 'H6'], between: ['18R/36L', 'B'] },
    { twy: ['A'], between: ['A2', 'H4'] },
    { twy: ['B'], between: ['H1', 'H4'] },
    { twy: ['H1'], between: ['18L/36R', '18R/36L'] },
  ],
  crossOnly: { '18L/36R': ['H4', 'H7'] },   // F4551/26 (same window): cross 18L/36R only via H4 / H7
  src: 'obs', notice: 'derived NOTAM effect record (targets only), eAIP NOTAM Summary in force 2026-11-02 07:06Z; later NOTAMs not known',
};

function main() {
  const t0 = Date.now();
  const R = makeRouter(G, { stands: S, live: true });
  const stands = R.graph.standNames.slice();   // node order of the taxi graph (deterministic)
  const info = new Map(S.stands.map(s => [s.name, s]));
  const runwayEnds = runwayGeom(A);
  const closed = closedLinksFor(G, F4552.targets);
  log('F4552 closed links', closed.ids.length, JSON.stringify(closed.report));
  // cross-check against the local NOTAM extraction if it is present (counts only; refs/cache is never read in a public checkout)
  const local = path.join(ROOT, 'refs/cache/notam/zsss_notams_2026-11.json');
  let localCheck = 'local NOTAM extraction not present';
  if (fs.existsSync(local)) {
    try { const N = JSON.parse(fs.readFileSync(local)); const n = (N.notams || []).find(x => x.id === F4552.id);
      const refsHere = new Set(F4552.targets.flatMap(t => t.twy.concat(t.between || []))); const txt = n ? String(n.E || '') : '';
      const refsThere = new Set((txt.match(/\b[A-Z]\d?\b/g) || []).filter(r => /^[A-Z]\d?$/.test(r) && !['TWY', 'CLSD', 'BTN', 'AND', 'FLW', 'RWY'].includes(r)));
      const missing = [...refsThere].filter(r => !refsHere.has(r) && G.links.some(l => l.ref === r));
      localCheck = n ? (missing.length ? 'local extraction names taxiways not in the record: ' + missing.length : 'record agrees with the local extraction (taxiway names)') : 'F4552 not in the local extraction';
    } catch (e) { localCheck = 'local extraction unreadable'; }
  }
  log('F4552 vs local NOTAM extraction:', localCheck);
  const RV = makeRouter(G, { stands: S, live: true, closedLinks: closed.ids, crossOnly: F4552.crossOnly });
  const closedSet = new Set(closed.ids); const nodeOf = new Map(G.nodes.map(n => [n.id, n]));
  // a base route needs the variant when it uses a closed link or crosses a runway outside F4551's crossing list
  const needsVariant = (sq) => !!sq && (sq.some(([id]) => closedSet.has(id)) || sq.some(([id, from], i) => { if (i === 0) return false; const n = nodeOf.get(from); const l = G.links[id], p = G.links[sq[i - 1][0]];
    return n && n.kind === 'rwy' && F4552.crossOnly[n.runway] && l.use !== 'runway' && p.use !== 'runway' && !F4552.crossOnly[n.runway].includes(l.ref); }));

  // ---------------------------------------------------------------------------------------- option A
  const optionA = {};
  for (const s of stands) { const r = R.optionA(s); if (r) optionA[s] = { run: r.run, runFrom: r.runFrom, node: r.node, swing: r.swing, turnDeg: r.turnDeg, runCm: r.runCm }; }
  log('option A stands', Object.keys(optionA).length);

  // ---------------------------------------------------------------------------------------- tries
  const groups = {};
  const counts = { dep: 0, arr: 0, depNull: 0, arrNull: 0, variantRoutes: 0, variantNull: 0 };
  function trieOf(seqs, rev) {   // seqs: [stand index -> array of link ids | null | undefined]
    const t = [], idx = new Map(); const leaf = new Array(stands.length).fill(-1);
    for (let i = 0; i < stands.length; i++) {
      const sq = seqs[i]; if (sq === undefined) continue; if (sq === null) { leaf[i] = -2; continue; }
      const ids = rev ? sq.slice().reverse() : sq; let p = -1;
      for (const id of ids) { const k = p + ':' + id; let n = idx.get(k); if (n === undefined) { n = t.length / 2; t.push(id, p); idx.set(k, n); } p = n; }
      leaf[i] = p;
    }
    return { t, leaf };
  }
  const lenOf = (r) => (r ? r.lenCm : -1);
  // departures
  const depEntries = []; for (const e of END_IDS) { depEntries.push([e, 'full']); if (ROUTER.intersection[e]) depEntries.push([e, ROUTER.intersection[e]]); }
  for (const [end, entry] of depEntries) {
    for (const variant of ['base', 'F4552']) {
      if (variant === 'F4552' && !(end === '18R' || end === '36L')) continue;
      const RR = variant === 'base' ? R : RV; const seqs = [], lenN = [], lenW = [], pn = [], sw = [], td = [];
      for (let i = 0; i < stands.length; i++) {
        const s = stands[i];
        const baseRec = R._search.depSeq(s, end, entry), base = baseRec && baseRec.seq;
        const rec = RR._search.depSeq(s, end, entry); const sq = rec && rec.seq;
        pn.push(rec ? rec.nPush : -1); sw.push(rec && rec.swing != null ? rec.swing : -1); td.push(rec && rec.turnDeg != null ? rec.turnDeg : -1);
        if (rec && rec.fallback) counts.pushFallback = (counts.pushFallback || 0) + 1;
        if (variant === 'F4552') { const usesClosed = needsVariant(base); if (!usesClosed) { seqs.push(undefined); lenN.push(-1); lenW.push(-1); continue; } counts.variantRoutes++; if (!sq) counts.variantNull++; }
        if (!sq) { seqs.push(null); lenN.push(-1); lenW.push(-1); if (variant === 'base') counts.depNull++; continue; }
        seqs.push(sq.map(([id]) => id)); if (variant === 'base') counts.dep++;
        lenN.push(lenOf(RR.departure(s, end, { entry, geom: 'narrow' }))); lenW.push(lenOf(RR.departure(s, end, { entry, geom: 'wide' })));
      }
      const tr = trieOf(seqs, true);
      groups['dep|' + end + '|' + entry + '|' + variant] = { rev: true, t: tr.t, leaf: tr.leaf, lenN, lenW, pn, sw, td };
    }
  }
  // arrivals
  const exitsOut = {};
  for (const end of END_IDS) {
    const ex = R.exits(end, true); exitsOut[end] = ex.map(e => ({ id: e.id, ref: e.ref, side: e.side, rank: e.rank, link: e.link, node: e.node, sCm: e.sCm, startCm: e.startCm }));
    for (const e of ex) {
      const rw = R.graph.ENDS[end].rw;
      const sideStands = stands.map(s => R.standSide(s, rw) === e.side);
      for (const variant of ['base', 'F4552']) {
        if (variant === 'F4552' && !(end === '18R' || end === '36L')) continue;
        const RR = variant === 'base' ? R : RV;
        for (const cls of ['n', 'w', 'x']) {
          const spanCm = cls === 'n' ? 0 : cls === 'w' ? ROUTER.spanNarrowCm : ROUTER.spanEaMaxCm;
          const seqs = [], lenN = [], lenW = []; let any = false;
          for (let i = 0; i < stands.length; i++) {
            const s = stands[i];
            if (!sideStands[i]) { seqs.push(undefined); lenN.push(-1); lenW.push(-1); continue; }
            const st = info.get(s); const maxSpan = st && st.span_max ? Math.round(st.span_max * 100) : 9e9;
            if (cls !== 'n' && maxSpan < spanCm) { seqs.push(undefined); lenN.push(-1); lenW.push(-1); continue; }   // the stand takes no such span
            const baseN = R._search.arrSeq(e.id, s, 'n'), baseC = cls === 'n' ? baseN : R._search.arrSeq(e.id, s, cls);
            let sq = RR._search.arrSeq(e.id, s, cls);
            if (variant === 'F4552') { const usesClosed = needsVariant(baseC); if (!usesClosed) { seqs.push(undefined); lenN.push(-1); lenW.push(-1); continue; } counts.variantRoutes++; if (!sq) counts.variantNull++; }
            else if (cls !== 'n') { const same = sq && baseN && sq.length === baseN.length && sq.every(([id], k) => id === baseN[k][0]); if (same) { seqs.push(undefined); lenN.push(-1); lenW.push(-1); continue; } }
            if (!sq) { seqs.push(null); lenN.push(-1); lenW.push(-1); if (variant === 'base' && cls === 'n') counts.arrNull++; any = true; continue; }
            seqs.push(sq.map(([id]) => id)); any = true; if (variant === 'base') counts.arr++;
            lenN.push(lenOf(RR.arrival(e.id, s, { spanCm, geom: 'narrow' }))); lenW.push(lenOf(RR.arrival(e.id, s, { spanCm, geom: 'wide' })));
          }
          if (!any) continue;
          const tr = trieOf(seqs, false);
          groups['arr|' + e.id + '|' + cls + '|' + variant] = { rev: false, t: tr.t, leaf: tr.leaf, lenN, lenW };
        }
      }
    }
  }
  const nNodes = Object.values(groups).reduce((a, g) => a + g.t.length / 2, 0);
  log('routes: departures', counts.dep, '(none', counts.depNull + ')', 'arrivals', counts.arr, '(none', counts.arrNull + ')', 'F4552 variant', counts.variantRoutes, '(none', counts.variantNull + ')', 'groups', Object.keys(groups).length, 'trie nodes', nNodes);

  const table = {
    v: 1,
    what: 'ZSSS precomputed taxi routes for the Phase 3 simulator (P3-B): link sequences of every departure (stand x take-off end x entry) and arrival (rapid exit x stand x span class), option A pushes, the F4552 closure variant and the integer runway-end geometry; rebuilt into integer pieces by js/sim/router.js',
    licence: 'ODbL 1.0 - Derivative Database of OpenStreetMap ((c) OpenStreetMap contributors) through data/sha_taxigraph.json (https://opendatacommons.org/licenses/odbl/1-0/). The runwayEnds declared distances, PAPI distances and displaced thresholds and the F4552 effect record are short cited facts (AIP (mirror), eAIP NOTAM Summary), not covered by the ODbL.',
    attribution: ['(c) OpenStreetMap contributors (ODbL 1.0) - https://www.openstreetmap.org/copyright', 'Short facts: AIP China AD 2 ZSSS (CAAC), EFF 2026-07-08, read in an unofficial mirror ("AIP (mirror)"); NOTAM effect record from the CAAC eAIP NOTAM Summary (in force 2026-11-02 07:06Z)'],
    generator: 'tools/sim/build_routes.mjs (js/sim/router.js, js/sim/path.js, js/sim/traj.js runwayGeom)',
    src: 'inf', src_note: 'routes are inferred (shortest allowed paths under the AIP (mirror) rules); geometry from OSM via the taxi graph',
    inputs_sha256_16: { taxigraph: sha16(rawG), stands: sha16(rawS), airport: sha16(rawA) },
    graph_fp: graphFingerprint(G),
    params: { router: ROUTER, path: PATH, perf: { vExitCms: PERF.vExitCms } },
    stands, exits: exitsOut, optionA, runwayEnds,
    variants: { F4552: { id: F4552.id, window: F4552.window, closedLinks: closed.ids, crossOnly: F4552.crossOnly, ends: ['18R', '36L'], note: 'routes of the 18R / 36L ends that use a closed link; 18L/36R is closed by F4551 in the same window', targets: F4552.targets, src: F4552.src, notice: F4552.notice } },
    groups,
    counts: { ...counts, groups: Object.keys(groups).length, trieNodes: nNodes, turnRule: { base: R.info().turnRule, F4552: RV.info().turnRule } },
    format: 'groups[key = dep|<end>|<entry>|<variant> or arr|<end>:<exit>|<n|w|x>|<variant>] = {rev, t: [linkId, parent, ...], leaf: [per stand: trie node | -1 not stored (use base / class n) | -2 no route], lenN / lenW: route length cm (narrow / wide geometry) | -1; dep only: pn = pushed links (push link + tail-first run), sw = swing link, td = push-turn deg}; a route = the links from leaf to root (reversed when !rev); fromNode of the first link = the stand node (dep) or the exit node (arr)',
  };
  const json = JSON.stringify(table);
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'sha_routes.json'), json);
  const header = '// generated by tools/sim/build_routes.mjs. ODbL 1.0: contains information from OpenStreetMap (c) OpenStreetMap contributors (through data/sha_taxigraph.json); runwayEnds / F4552: AIP (mirror) and NOTAM short facts, not covered by ODbL.\n';
  fs.writeFileSync(path.join(OUT, 'sha_routes.js'), header + 'window.SHA_ROUTES = ' + json + ';\n');
  const sources = {
    what: 'sources of data/sha_routes.json / .js (P3-B routing and kinematics)',
    generator: 'tools/sim/build_routes.mjs',
    inputs: {
      taxigraph: { file: 'data/sha_taxigraph.json', sha256_16: sha16(rawG), licence: 'ODbL 1.0 (OSM derivative; AIP (mirror) rules block not covered)', made_by: 'tools/airport/build_taxigraph.py' },
      stands: { file: 'data/sha_stands.json', sha256_16: sha16(rawS), licence: 'ODbL 1.0 (OSM derivative)', used: 'stand names, span_max (which span classes a stand needs)' },
      airport: { file: 'data/sha_airport.json', sha256_16: sha16(rawA), licence: 'ODbL 1.0 + AIP (mirror) short facts', used: 'runway ends, displaced thresholds, PAPI distances, declared distances, runway profile, extent ring (runwayEnds)' },
      notam: { record: F4552.id + ' (+ F4551/26 crossing restriction)', what: 'derived effect record: taxiway targets and window only, no NOTAM text', source: 'CAAC eAIP NOTAM Summary, in force 2026-11-02 07:06Z (docs/phase1/sources_sim.md §4.2)', licence: 'no terms published; short facts (owner decision OD3)', local_check: localCheck },
    },
    output: { file: 'data/sha_routes.json', sha256_16: sha16(Buffer.from(json)), bytes: Buffer.byteLength(json), licence: 'ODbL 1.0 (derivative database of OSM through the taxi graph); runwayEnds / variants.F4552: short cited facts, not covered by ODbL' },
    rules: 'AIP (mirror) AD 2.20 2.1.4.2, 2.1.7, 2.2.5, 2.3.1, 2.3.2, 2.3.3, 3.1.5, 3.2.2.2 through sha_taxigraph.json rules.facts / routing.turns; design.md §4.1-4.2',
    parameters: 'js/sim/router.js ROUTER, js/sim/path.js PATH, js/sim/perf.js PERF: every value src inf with its basis in the module (docs/phase3/movement.md §3)',
    deterministic: 'no clock or randomness; two runs give the same bytes (tools/sim/test_router.mjs)',
  };
  fs.writeFileSync(path.join(OUT, 'SOURCES_routes.json'), JSON.stringify(sources, null, 1) + '\n');
  log('wrote', path.join(OUT, 'sha_routes.json'), (Buffer.byteLength(json) / 1024).toFixed(1), 'kB in', ((Date.now() - t0) / 1000).toFixed(1), 's', '; path-level turn rule', JSON.stringify(table.counts.turnRule));
}
main();
