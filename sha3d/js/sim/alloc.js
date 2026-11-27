// SHA Live 3D Phase 3 (package P3-A): stand allocation of the day plan (design s.2.4). Pure ES module (node + browser),
// integer times (ms), no imports. Interval scheduling over the stands of data/sha_stands.js (passed in, never imported).
//
//   fit       type span <= stand maxSpan and length <= maxLen, the gate objects' own limits (js/live/gates.js shaGates:
//             maxSpan = min(class_max span, span_max + 0.1), maxLen = min(class_max length, len_max + 0.1));
//   buffer    [on - 10 min, off + 10 min] free (params.bufferS) [inf]: the stored occupancies are the UNBUFFERED ground
//             visits and a candidate is tested with its buffered window, so consecutive occupants are at least 10 min apart
//             (verification fix round 1, F6; before, buffered windows were stored and tested: a 20 min gap); the 5
//             exclusive pairs (excl) are mutually exclusive with the same 10 min;
//             NOTAM-closed stands are skipped while closed (267, F4313/26);
//   order     wide-bodies first (most constrained), then the others; each pass in rotation order (on-block, tier 2
//             first); per visit the first free stand of: own side contact -> own side remote -> the other side's remote
//             stands -> the other side's contact stands (counted crossSide) -> unplaced (the caller removes the movements
//             and counts them); within a tier: smallest fitting class first ("keep E / EL for wide-bodies"), then the
//             stand that became free latest (best fit), then name;
//   nightCap  (opts) at most nightCap[side] night-stoppers (visits parked from t0) on a side's stands; the rest go to the
//             other side while that side is below its own cap (design s.2.2 step 7: 0.85 x usable(side)), counted
//             crossSide, then to their own side, then to the other side (both full);
//   business  generic business jets only on the business apron; airliners never there.
//   gateTimes (optional, package P3-E table): a contact stand takes a model only if the table has the stand x type key.
// Sides [inf, stands.md s.5]: T1 = T1 contact stands + the east apron north of T1 + the east remote apron along A;
// T2 = T2 apron 2 + the west and south-west remote aprons; BIZ = the business apron.

export const sideOfArea = (a) => /^(T1|east)/.test(a || '') ? 'T1' : /^business/.test(a || '') ? 'BIZ' : 'T2';
const WIDE_SPAN = 41.2;                     // a stand whose class span exceeds this is a wide-body stand (gates.js 'wide')

const CACHE = new WeakMap();
/** stand table derived once per stands object */
export function standTable(stands) {
  if (CACHE.has(stands)) return CACHE.get(stands);
  const CM = stands.class_max || {};
  const L = [];
  for (const s of stands.stands || []) {
    const cm = CM[s.cls] || CM.C || [36.5, 45];
    const maxSpan = s.span_max ? Math.min(cm[0], s.span_max + 0.1) : cm[0];
    const maxLen = s.len_max ? Math.min(cm[1], s.len_max + 0.1) : cm[1];
    L.push({ name: s.name, side: sideOfArea(s.area), area: s.area, contact: !!s.contact, cls: s.cls, maxSpan, maxLen,
      wide: cm[0] > WIDE_SPAN, excl: (s.excl || []).slice(), bridges: (s.bridges || []).length,
      shares: s.bridge_status === 'shared' && (s.alt_group || []).length ? s.alt_group[0] : null });
  }
  L.sort((a, b) => (a.maxSpan - b.maxSpan) || (a.maxLen - b.maxLen) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
  const byName = new Map(L.map(s => [s.name, s]));
  // usable at once per side: stands minus one of each exclusive pair (non-B only for the airliner capacity)
  const cap = {};
  for (const sd of ['T1', 'T2', 'BIZ']) {
    const S = L.filter(s => s.side === sd);
    const pairs = new Set();
    for (const s of S) for (const e of s.excl) if (byName.has(e)) pairs.add([s.name, e].sort().join('|'));
    const nonB = S.filter(s => s.cls !== 'B');
    const pairsNonB = [...pairs].filter(p => p.split('|').every(n => byName.get(n).cls !== 'B')).length;
    const fitsN = (span, len) => {
      const F = S.filter(s => span <= s.maxSpan && len <= s.maxLen);
      const fp = [...pairs].filter(p => p.split('|').every(n => F.includes(byName.get(n)))).length;
      return F.length - fp;
    };
    cap[sd] = { stands: S.length, contact: S.filter(s => s.contact).length, nonB: nonB.length, usable: nonB.length - pairsNonB,
      all: S.length - pairs.size, excelPairs: pairs.size,
      wide: fitsN(60.3, 63.7), el: fitsN(64.8, 73.9), narrow: fitsN(35.8, 44.5) };
  }
  const T = { list: L, byName, cap };
  CACHE.set(stands, T);
  return T;
}

/** closure windows per stand from NOTAM records: Map(name -> [[a, b], ...]) */
export function closureWindows(notams) {
  const m = new Map();
  for (const n of notams || []) {
    if (n.kind !== 'stand_closed' || !n.target || !n.target.stand) continue;
    const k = String(n.target.stand);
    if (!m.has(k)) m.set(k, []);
    for (const w of n.windows || []) m.get(k).push([w[0], w[1]]);
  }
  return m;
}

const overlaps = (iv, a, b) => { for (const x of iv) if (x[0] < b && x[1] > a) return true; return false; };

/**
 * allocate(visits, stands, opts) -> {assign: Map(visitId -> {stand, contact, side, crossSide}), unplaced: [visitId],
 *   occ: Map(stand -> [[from, to, visitId]] unbuffered), stats}
 *   visit: {id, side, from, to, spanM, lenM, wide, biz, typeKey, tierRank, prefer, t0Edge, t1Edge}
 *   opts: {t0, t1, bufferS = 600, closures: Map, gateTimes, notams}
 */
export function allocate(visits, stands, opts = {}) {
  const T = standTable(stands);
  const buf = (opts.bufferS ?? 600) * 1000;
  const closures = opts.closures || closureWindows(opts.notams);
  const GT = opts.gateTimes && opts.gateTimes.stands ? opts.gateTimes.stands : null;
  const occ = new Map(T.list.map(s => [s.name, []]));
  const lastEnd = new Map(T.list.map(s => [s.name, -Infinity]));
  // most constrained first: wide-bodies (they fit only the E / EL / D stands), then the rest; each pass in rotation order
  // (night-stoppers, all from t0: the earliest departure first, so that a side's night-stop cap keeps the early leavers)
  const order = visits.slice().sort((a, b) => ((b.wide ? 1 : 0) - (a.wide ? 1 : 0)) || (a.from - b.from) ||
    ((a.t0Edge && b.t0Edge) ? a.to - b.to : 0) || ((a.tierRank || 9) - (b.tierRank || 9)) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const nightCap = opts.nightCap || null, nightOn = { T1: 0, T2: 0, BIZ: 0 };
  const assign = new Map(), unplaced = [];
  const free = (s, a, b) => {
    if (overlaps(occ.get(s.name), a, b)) return false;
    for (const e of s.excl) if (occ.has(e) && overlaps(occ.get(e), a, b)) return false;
    const c = closures.get(s.name);
    if (c && overlaps(c, a, b)) return false;
    return true;
  };
  const fits = (s, v) => v.spanM <= s.maxSpan && v.lenM <= s.maxLen && (!GT || !s.contact || !s.bridges || !v.typeKey || !!(GT[s.name] && GT[s.name][v.typeKey]));
  const pick = (cands, a, b) => {
    let best = null;
    for (const s of cands) {
      if (!free(s, a, b)) continue;
      if (!best) { best = s; continue; }
      if (s.maxSpan > best.maxSpan + 1e-9) continue;        // smallest fitting class first (list is sorted by span)
      if (lastEnd.get(s.name) > lastEnd.get(best.name)) best = s;
    }
    return best;
  };
  const stats = { crossSide: 0, unplaced: 0, preferred: 0, byTier: {} };
  for (const v of order) {
    const a = v.t0Edge ? v.from : v.from - buf, b = v.t1Edge ? v.to : v.to + buf;
    const own = v.biz ? 'BIZ' : v.side;
    const other = own === 'T1' ? 'T2' : own === 'T2' ? 'T1' : null;
    const F = T.list.filter(s => fits(s, v) && (v.biz ? s.side === 'BIZ' : s.side !== 'BIZ'));
    let s = null, cross = false;
    if (v.prefer) {
      const p = T.byName.get(v.prefer);
      if (p && F.includes(p) && p.side === own && free(p, a, b)) { s = p; stats.preferred++; }
    }
    const tiers = [];
    const capped = v.t0Edge && nightCap && nightCap[own] != null && nightOn[own] >= nightCap[own];
    // a capped night-stopper goes to the other side only while that side is below ITS cap (verification fix round 1: the
    // T2 excess filled the T1 side to the last stand); then its own side; then the other side again (physically full)
    const otherRoom = capped && other && (nightCap[other] == null || nightOn[other] < nightCap[other]);
    const ownT = v.remoteFirst ? [F.filter(x => x.side === own && !x.contact), F.filter(x => x.side === own && x.contact)]
      : [F.filter(x => x.side === own && x.contact), F.filter(x => x.side === own && !x.contact)];
    const otherT = other ? [F.filter(x => x.side === other && !x.contact), F.filter(x => x.side === other && x.contact)] : [];
    if (v.biz) tiers.push(F);
    else if (!capped) tiers.push(...ownT, ...otherT);
    else if (otherRoom) tiers.push(...otherT, ...ownT);
    else tiers.push(...ownT, ...otherT);
    for (let i = 0; !s && i < tiers.length; i++) {
      s = pick(tiers[i], a, b);
      if (s && s.side !== own) cross = true;
    }
    if (!s) { unplaced.push(v.id); stats.unplaced++; continue; }
    occ.get(s.name).push([v.from, v.to, v.id]);       // unbuffered: the next candidate's own buffer keeps the 10 min gap
    if (v.t0Edge) nightOn[s.side]++;
    if (v.to > lastEnd.get(s.name)) lastEnd.set(s.name, v.to);
    if (cross) stats.crossSide++;
    assign.set(v.id, { stand: s.name, contact: s.contact, side: s.side, crossSide: cross });
  }
  for (const L of occ.values()) L.sort((x, y) => x[0] - y[0]);
  return { assign, unplaced, occ, stats, table: T };
}
