// Import the PC-12 model from pc12/ into the hwd3d runtime (hwd3d Phase 3, M2).
//   node tools/models/pc12/import_pc12.mjs [--variant=out/pc12_fr3] [--sources-only]
// Default: copies pc12/out/pc12.glb unchanged (refuses an uncommitted pc12/out).
// --variant=<dir> (review fix round 2): imports a build of pc12's own builders with the documented parameter override set
//   of tools/models/pc12/build_pc12_variant.py (window / door layout, dihedral; outputs in hwd3d/out, gitignored). It
//   refuses a variant whose recorded pc12 sources were dirty, whose pc12 source tree hash differs from the files on disk
//   now, or whose builder hash differs from the script on disk, so the import can always be rebuilt bit-for-bit from the
//   working tree: `python3 -B tools/models/pc12/build_pc12_variant.py --set=fr3` (2 s; writes out/pc12_fr3).
// Writes js/aircraft/models/pc12.glb (the GLB unchanged), js/aircraft/models/pc12_meta.json (the parts of the build's meta
// the runtime and the docs use: BOM, dimension checks, wing data, build stats, plus provenance and the frame measured by
// js/aircraft/glb.js) and the pc12 entries of js/aircraft/models/SOURCES.json (other entries are kept; the entries of the
// other registered models - SF50 - are refreshed from their meta _provenance, with the file hash recomputed;
// --sources-only does only that).
// Read-only on pc12/ (it never writes there and runs no Python).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { convertGLB } from '../../../js/aircraft/glb.js';
import { MODELS, MODEL_LOAD_OPTS } from '../../../js/aircraft/models.js';

const HWD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..'), REPO = path.resolve(HWD, '..');
const VARIANT = (process.argv.find(a => a.startsWith('--variant=')) || '').slice(10) || null;
const SRC_DIR = VARIANT ? path.resolve(HWD, VARIANT) : path.join(REPO, 'pc12/out');
const SRC_GLB = path.join(SRC_DIR, 'pc12.glb'), SRC_META = path.join(SRC_DIR, 'pc12_meta.json');
const OUT = path.join(HWD, 'js/aircraft/models'); fs.mkdirSync(OUT, { recursive: true });
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const git = (...a) => execFileSync('git', ['-C', REPO, ...a], { encoding: 'utf8' }).trim();
let commit, date, variant = null;
if (!VARIANT) {
  commit = git('log', '-1', '--format=%H', '--', 'pc12/out/pc12.glb'); date = git('log', '-1', '--format=%cI', '--', 'pc12/out/pc12.glb');
  const dirty = git('status', '--porcelain', '--', 'pc12/out/pc12.glb', 'pc12/out/pc12_meta.json');
  if (dirty) throw new Error('pc12/out has uncommitted changes; import only a committed model:\n' + dirty);
} else {
  const M0 = JSON.parse(fs.readFileSync(SRC_META, 'utf8')); variant = M0._variant;
  if (!variant) throw new Error(SRC_META + ': no _variant record (not written by build_pc12_variant.py)');
  if (variant.pc12_sources_dirty) throw new Error('the variant was built from uncommitted pc12 sources');
  // the pc12 sources on disk must still be the ones the variant was built from, and the builder the one on disk
  const tree = crypto.createHash('sha256'); const now = {};
  for (const f of Object.keys(variant.pc12_sources).sort()) { const h = sha(path.join(REPO, f)); now[f] = h; tree.update(`${f} ${h}\n`); }
  const changed = Object.keys(now).filter(f => now[f] !== variant.pc12_sources[f]);
  if (changed.length || tree.digest('hex') !== variant.pc12_sources_tree_sha256) throw new Error('pc12 sources changed since the variant build: ' + changed.join(', '));
  const bsha = sha(path.join(REPO, variant.builder)); if (bsha !== variant.builder_sha256) throw new Error(`${variant.builder} changed since the variant build (rebuild)`);
  commit = variant.pc12_commit; date = git('log', '-1', '--format=%cI', commit);
}

const SOURCES_ONLY = process.argv.includes('--sources-only');
// what each override set of build_pc12_variant.py changes (the values and their basis are in the builder and in the meta)
const OVERRIDE_TEXT = {
  fr2: 'cabin window / door / exit layout from Pilatus drawing 190.10.40.432 + MBP p.5 livery (stations measured), wing dihedral 6.2 deg about BL 2.265 (fitted to the drawing front view)',
  fr3: 'fr2 + fuselage loft aft of the nose (crown, keel, half-breadth, max-breadth WL, section exponents), cockpit glazing, window / door water lines, wing and main-gear trunnion height, nose-gear housing, belly fairing covering the wing, dorsal fin, fin leading edge, ventral strakes and winglet, all fitted to Pilatus drawing 190.10.40.432 (review fix round 3); iteration 2: flat cabin floor at the sourced 1.30 m width and a cabin layout clear of the doors, nose-gear housing with rounded edges and a strut slot, belly fairing section blended into the wing, belly antennas on the skin [inf: layout / shapes]',
};
// SOURCES.json entries of the other registered models (SF50: tools/models/sf50, M1), from their meta _provenance; the
// file hash is recomputed and compared with the hash the builder recorded
function otherSources(S) {
  for (const [type, e] of Object.entries(MODELS)) {
    if (type === 'PC12') continue;
    const glb = fileURLToPath(e.url), meta = fileURLToPath(e.meta); if (!fs.existsSync(glb) || !fs.existsSync(meta)) continue;
    const M = JSON.parse(fs.readFileSync(meta, 'utf8')), pv = M._provenance || {}, h = sha(glb);
    const name = path.basename(glb), mname = path.basename(meta);
    // fix round 2: the builder is untracked (tools/models), so 'repo @ HEAD' alone does not identify it: name the working
    // tree state and the sha256 of the builder sources recorded at build time
    const src = pv.sources_tree_sha256 ? `${pv.made_by || 'unknown builder'}, ${pv.builder_state || 'state not recorded'}, sources tree sha256 ${pv.sources_tree_sha256} (per-file hashes in ${mname} _provenance.sources_sha256; git HEAD at build ${pv.repo_rev || '?'}), built ${pv.built || '?'}`
      : `${pv.made_by || 'unknown builder'} @ ${pv.repo_rev || '?'}, built ${pv.built || '?'}`;
    S[name] = { url: null, source: src, sha256: h, builder_state: pv.builder_state || null, sources_tree_sha256: pv.sources_tree_sha256 || null, rebuild: pv.rebuild || null,
      sha256_recorded_by_builder: pv.glb_sha256 || null, sha256_match: pv.glb_sha256 ? pv.glb_sha256 === h : null, licence: pv.licence || null,
      facts: pv.facts || null, doc: pv.doc || null, note: `${type} detailed model (registry js/aircraft/models.js); provenance as recorded by its builder in ${mname} _provenance` };
    // fix round 3 (finding V1): the meta entry names its maker and carries a note like every SOURCES entry
    S[mname] = { url: null, source: `${pv.made_by || 'unknown builder'}, ${pv.builder_state || '@ ' + (pv.repo_rev || '?')}`, sha256: sha(meta), licence: pv.licence || null,
      made_by: pv.made_by || null, note: `${type} model metadata written by its builder with the GLB (parts, pivots, light anchors, checks, frame, _provenance); facts and their sources: ${pv.facts || '?'}` };
    console.log(`${type}: ${name} sha256 ${h.slice(0, 12)}… ${pv.glb_sha256 ? (pv.glb_sha256 === h ? '= builder record' : '!= builder record ' + pv.glb_sha256.slice(0, 12)) : '(no builder record)'}`);
  }
}
if (SOURCES_ONLY) { const SF = path.join(OUT, 'SOURCES.json'); const S = fs.existsSync(SF) ? JSON.parse(fs.readFileSync(SF, 'utf8')) : {}; otherSources(S); fs.writeFileSync(SF, JSON.stringify(S, null, 1) + '\n'); process.exit(0); }
fs.copyFileSync(SRC_GLB, path.join(OUT, 'pc12.glb'));
const meta = JSON.parse(fs.readFileSync(SRC_META, 'utf8'));
// the runtime's own conversion options (ground plane = pc12's ground, registry light anchors), so the recorded frame is the app's
const m = convertGLB(fs.readFileSync(SRC_GLB), MODEL_LOAD_OPTS('PC12'));
const r3 = (v) => Math.round(v * 1000) / 1000;
const out = {
  _provenance: {
    source: VARIANT ? `pc12's own builders (pc12/model, pc12/cad @ ${commit}, unchanged files) run by ${variant.builder} with the override set '${variant.set}' (docs/phase3_models.md section 4), output ${path.relative(HWD, SRC_DIR)}/ (gitignored, rebuilt bit-for-bit by: python3 -B ${path.relative(REPO, path.join(REPO, variant.builder)).replace(/^hwd3d\//, '')} --set=${variant.set})`
      : 'pc12/out/pc12.glb + pc12/out/pc12_meta.json (this repository: the from-scratch parametric PC-12 PRO model, pc12/CLAUDE.md)',
    commit, commit_date: date, glb_sha256: sha(SRC_GLB), meta_sha256: sha(SRC_META), licence: 'own work (this repository)',
    variant: variant ? { set: variant.set, overrides: variant.overrides, builder: variant.builder, builder_sha256: variant.builder_sha256, pc12_sources_tree_sha256: variant.pc12_sources_tree_sha256, pc12_sources_dirty: variant.pc12_sources_dirty, pc12_sources: variant.pc12_sources, built: variant.built } : null,
    imported_by: 'hwd3d/tools/models/pc12/import_pc12.mjs', imported: new Date().toISOString().slice(0, 10),
    facts: 'dimensions and configuration facts with their sources: pc12/CLAUDE.md "Sourced facts" (Pilatus, POH NGX, EASA TCDS, Jane\'s); contours, airfoils, interior and livery are estimated / reconstructed ("Estimated / reconstructed" there)',
    livery: 'original neutral scheme (pc12/model/livery.py: white, cool-grey belly, navy swoosh, brass pinstripe); no registration, no logo',
  },
  frame: {
    note: 'hwd3d aircraft local frame (+x forward, +y up, +z starboard, origin = main-gear ground contact on pc12\'s own ground plane; the tyres sit 14.5 mm (mains) / 10.5 mm (nose) into it, pc12\'s static deflection), measured by js/aircraft/glb.js convertGLB with js/aircraft/models.js MODEL_LOAD_OPTS',
    origin_gl: m.originGl.map(r3), contacts: Object.fromEntries(Object.entries(m.contacts).filter(([k]) => k !== 'parts').map(([k, v]) => [k, v && v.map(r3)])),
    wheelbase_m: r3(m.wheelbase), track_m: r3(m.track), bbox_local: m.bbox.map(r3),
    length_m: r3(m.bbox[3] - m.bbox[0]), span_m: r3(m.bbox[5] - m.bbox[2]), height_m: r3(m.bbox[4]), nose_to_main_m: r3(m.bbox[3]),
    // fix round 3 (finding V1): a 'src' field holds only obs / inf (tools/check_airport.py); the anchor's evidence text goes to
    // 'basis'. An anchor is a model position: inf unless its text says [obs] and nothing inferred
    lights: Object.fromEntries(Object.entries(m.lights).map(([k, v]) => [k, v && { p: v.p.map(r3), part: v.part >= 0 ? m.parts[v.part].id : null,
      src: /\[obs/.test(v.src || '') && !/inf/.test(v.src || '') ? 'obs' : 'inf', basis: v.src || null }])),
    excluded_parts: m.stats.excluded, tris_drawn: m.stats.tris,
  },
  checks: meta.checks, wing: meta.wing, stats: meta.stats,
  parts: meta.bom.map(b => ({ id: b.id, name: b.name, group: b.group, qty: b.qty, note: b.note, tris: b.tris, materials: b.materials, info: b.info || null })),
  pivots: m.parts.filter(p => p.pivot).map(p => ({ id: p.id, kind: p.pivot.kind, ...Object.fromEntries(Object.entries(p.pivot.raw).filter(([k]) => !['origin', 'axis', 'A', 'B0', 'K0', 'bend', 'travel'].includes(k))) })),
};
fs.writeFileSync(path.join(OUT, 'pc12_meta.json'), JSON.stringify(out, null, 1) + '\n');
const SF = path.join(OUT, 'SOURCES.json'); const S = fs.existsSync(SF) ? JSON.parse(fs.readFileSync(SF, 'utf8')) : {};
S['pc12.glb'] = { url: null, source: VARIANT ? `pc12 builders @ ${commit} (pc12 sources unchanged, tree sha256 ${variant.pc12_sources_tree_sha256.slice(0, 16)}…) + override set '${variant.set}' of ${variant.builder} (sha256 ${variant.builder_sha256.slice(0, 16)}…, working tree), this repository` : `pc12/out/pc12.glb @ ${commit} (${date}), this repository`,
  sha256: sha(path.join(OUT, 'pc12.glb')), licence: 'own work (this repository); no third-party geometry or texture',
  made_by: VARIANT ? `pc12/model + pc12/cad builders run by ${variant.builder} --set=${variant.set}; copied unchanged by hwd3d/tools/models/pc12/import_pc12.mjs --variant` : 'pc12/model/build.py (loftkit, plain Python + numpy); copied unchanged by hwd3d/tools/models/pc12/import_pc12.mjs',
  overrides: VARIANT ? (OVERRIDE_TEXT[variant.set] || `override set ${variant.set}`) + '; docs/phase3_models.md section 4' : null,
  note: `Pilatus PC-12 PRO (NGX) parametric model, ${meta.stats.parts} parts (as built), pivots in node extras.` + ' Sourced dimensions in pc12/CLAUDE.md; reconstructed contours marked there. Original neutral livery, no registration or logo (D1).' };
S['pc12_meta.json'] = { url: null, source: `subset of ${VARIANT ? path.relative(HWD, SRC_META) + ' (variant ' + variant.set + ', pc12 builders @ ' + commit + ')' : 'pc12/out/pc12_meta.json @ ' + commit} + the frame measured by js/aircraft/glb.js`, sha256: sha(path.join(OUT, 'pc12_meta.json')), licence: 'own work (this repository)', made_by: 'hwd3d/tools/models/pc12/import_pc12.mjs' };
otherSources(S);
fs.writeFileSync(SF, JSON.stringify(S, null, 1) + '\n');
console.log(`pc12 @ ${commit.slice(0, 7)}${VARIANT ? ' variant ' + variant.set : ''}: ${m.stats.tris} tris drawn, origin_gl ${out.frame.origin_gl}, wheelbase ${out.frame.wheelbase_m}, track ${out.frame.track_m}, L ${out.frame.length_m} span ${out.frame.span_m} H ${out.frame.height_m}`);
