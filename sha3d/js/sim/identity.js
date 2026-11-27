// SHA Live 3D Phase 3 (package P3-A): the identity overlay contract and the label / card texts of every tier.
// Pure ES module (node + browser), no imports. Design: docs/phase3/design.md s.3 (identity data flow, OD4), s.6.1 (exact
// texts), s.7.1 (checkOverlay, labelFor; frozen interface: fields may be added, never renamed).
//
// OD4: real identities "observed elsewhere" come ONLY from the local overlay (relay GET /api/observed_elsewhere?day= or
// window.SHA_IDENTITY in the private artifact), never from a committed file. checkOverlay keeps the allow-listed fields
// and drops everything else; ?identity=0 means overlay = null (the public plan), never "hide the fields".

export const OVERLAY_FIELDS = Object.freeze(['uid', 'role', 'airline', 'cs', 'flight', 'reg', 'type', 'operator', 'far', 't_sha', 'sigma_s']);
const TYPE_RX = /^[A-Z][A-Z0-9]{1,3}$/;
const HEX24_RX = /^[0-9a-f]{6}$/;          // lowercase (the source's addresses); 'CAnnnn' is a flight number
const DAY_RX = /^\d{4}-\d{2}-\d{2}$/;
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** 'YYYY-MM-DD' -> '12 Nov 2026' */
export function fmtDay(day) {
  if (!DAY_RX.test(day || '')) return String(day);
  const [y, mo, d] = day.split('-');
  return `${+d} ${MON[+mo - 1]} ${y}`;
}

/**
 * checkOverlay(obj) -> Overlay | null. Accepts only {v: 1, tier: 'oe', day, records: [...]}; each record keeps the
 * allow-listed fields (OVERLAY_FIELDS) and is dropped when a field is malformed: role arr / dep, integer t_sha (epoch s),
 * integer sigma_s >= 0, type ~ ^[A-Z][A-Z0-9]{1,3}$, and NO value that looks like a 24-bit address (6 hex digits; the
 * source field 'icao' is the address and is never read, review M12). opts.day: the day it must be for.
 */
export function checkOverlay(obj, opts = {}) {
  if (!obj || typeof obj !== 'object' || obj.available === false) return null;
  if (obj.v !== 1 || obj.tier !== 'oe' || !DAY_RX.test(obj.day || '') || !Array.isArray(obj.records)) return null;
  if (opts.day && obj.day !== opts.day) return null;
  const records = [];
  let dropped = 0;
  const seen = new Set();
  for (const r of obj.records) {
    if (!r || typeof r !== 'object') { dropped++; continue; }
    const o = {};
    for (const k of OVERLAY_FIELDS) o[k] = r[k] ?? null;
    const strs = OVERLAY_FIELDS.filter(k => k !== 't_sha' && k !== 'sigma_s').map(k => o[k]).filter(v => v != null);
    const ok = typeof o.uid === 'string' && o.uid && !seen.has(o.uid) && (o.role === 'arr' || o.role === 'dep') &&
      Number.isInteger(o.t_sha) && Number.isInteger(o.sigma_s) && o.sigma_s >= 0 &&
      typeof o.type === 'string' && TYPE_RX.test(o.type) && typeof o.airline === 'string' && /^[A-Z]{3}$/.test(o.airline) &&
      strs.every(v => typeof v === 'string' && !HEX24_RX.test(v));
    if (!ok) { dropped++; continue; }
    seen.add(o.uid);
    records.push(Object.freeze(o));
  }
  return Object.freeze({
    v: 1, day: obj.day, tier: 'oe', note: String(obj.note || 'observed elsewhere, SHA time inferred'),
    licence: String(obj.licence || 'ODbL 1.0 (adsb.lol), VRS CC0, Mictronics ODC-By'),
    records: Object.freeze(records), dropped,
  });
}

const airlineInfo = (inputs, a) => (inputs && inputs.airlines && inputs.airlines[a]) || null;
const airlineShort = (inputs, a) => a ? ((airlineInfo(inputs, a) || {}).short || a) : 'Business jet';

/** the 3-D model note for stand-ins (design s.2.3) or null */
export function modelNote(m, inputs) {
  if (!m) return null;
  const si = inputs && inputs.params && inputs.params.standIns && inputs.params.standIns[m.icao];
  if (si) return si.note;
  if (m.tier === 'inf' && m.side === 'BIZ') return '3D model: generic business jet (scaled CRJ200 shape)';
  if (m.model && m.model !== m.icao) return `3D model: ${m.model} stand-in`;
  return null;
}

function partnerOe(m, plan) {
  if (!plan || !plan.movements) return null;
  const by = plan._byId || new Map(plan.movements.map(x => [x.id, x]));
  for (const id of [m.next, m.prev]) {
    const p = id && by.get(id);
    if (p && p.tier === 'oe') return p;
  }
  return null;
}

/**
 * labelFor(movement, overlay, opts) -> {title, label, sub, chips, lines, row, modelNote, src}
 *   title: card title; label / sub: the 3-D label lines; chips: list chips; lines: card source line + rows;
 *   row: the list row text. opts: {inputs, plan, day}. Texts exactly as design s.6.1.
 */
export function labelFor(m, overlay, opts = {}) {
  const I = opts.inputs || null;
  const type = m.icao;
  const base = { modelNote: modelNote(m, I), src: 'inf' };
  const inf = () => ({
    ...base, title: `${airlineShort(I, m.airline)} · ${type}`, label: `${m.airline || 'BIZ'} · ${type}`, sub: null, chips: ['inf'],
    row: `${airlineShort(I, m.airline)} · ${type}`,
    lines: [m.side === 'BIZ'
      ? 'Simulated flight (inferred): a generic business jet on the business apron. No flight number or registration is known for it.'
      : 'Simulated flight (inferred): airline and type follow the Hongqiao mix. No flight number or registration is known for it.'],
  });
  if (m.tier === 'oe') {
    const rec = overlay && overlay.records ? overlay.records.find(r => r.uid === m.ident) : null;
    if (!rec) return inf();                      // no overlay (identity off): never an identity
    const id = rec.flight || rec.cs;
    const sig = Math.round((rec.sigma_s || 0) / 60);
    return {
      ...base, title: id, label: id, sub: rec.type, chips: ['obs elsewhere', 'inf'], row: `${id} · ${rec.type}`,
      lines: [`Identity observed elsewhere: open ADS-B saw this flight outside the Shanghai coverage gap on ${fmtDay(overlay.day)}. ` +
        `Its time at Hongqiao is inferred (±${sig} min, 1σ). Stand, taxi route, runway and position are simulated.`,
        `Callsign ${rec.cs || '-'}`, `Registration ${rec.reg || '-'}`, `Operator ${rec.operator || '-'}`, `Type ${rec.type}`],
    };
  }
  if (m.tier === 'pub' && m.flight) {
    const hk = m.far === 'HKG';
    const date = fmtDay(m.farDate || opts.day || '');
    const typeKnown = !!m.typePublished;
    const src = hk
      ? `Flight number from the published Hong Kong airport schedule of ${date} (Airport Authority Hong Kong, via DATA.GOV.HK). ` +
        'Its time at Hongqiao is inferred from it; type and registration are not published.'
      : `Flight number from the published Taipei Songshan Airport schedule of ${date} (CAA Taiwan, OGDL v1.0). ` +
        (typeKnown ? 'Its time at Hongqiao is inferred from it; the type is as published, the registration is not published.'
          : 'Its time at Hongqiao is inferred from it; type and registration are not published.');
    return { ...base, title: m.flight, label: m.flight, sub: type, chips: ['published', 'inf'], row: `${m.flight} · ${type}`, lines: [src] };
  }
  if (m.tier === 'rep' && m.flight) {
    return {
      ...base, title: m.flight + '*', label: m.flight + '*', sub: type, chips: ['seen other days', 'inf'], row: `${m.flight}* · ${type}`,
      lines: ['Flight number seen at about this time on 10 and 12 Nov 2026 (observed elsewhere, open ADS-B outside the Shanghai ' +
        'coverage gap). It was not observed today: today\'s flight, time and aircraft are simulated.'],
    };
  }
  if (m.tier === 'cont') {
    const p = partnerOe(m, opts.plan);
    const rec = p && overlay && overlay.records ? overlay.records.find(r => r.uid === p.ident) : null;
    const pid = rec ? (rec.flight || rec.cs) : null;
    const pRole = p ? (p.role === 'arr' ? 'arrival' : 'departure') : (m.role === 'arr' ? 'departure' : 'arrival');
    const me = m.role === 'arr' ? 'arrival' : 'departure';
    return {
      ...base, title: `${airlineShort(I, m.airline)} · ${type}`, label: `${m.airline} · ${type}`, sub: null, chips: ['inf'],
      row: `${airlineShort(I, m.airline)} · ${type}`,
      lines: [pid
        ? `Same aircraft as the observed ${pRole} ${pid} (${fmtDay(overlay.day)}), parked here by inference. This ${me} was not observed: no flight number or registration is shown.`
        : `Same aircraft as an observed ${pRole}, parked here by inference. This ${me} was not observed: no flight number or registration is shown.`],
    };
  }
  return inf();
}

/** the day line of the note (design s.6.1) */
export function dayLine(plan, overlay, inputs) {
  const n = plan && plan.tiers ? plan.tiers.oe : 0;
  if (overlay && n > 0) return `Identities: ${n} flights observed elsewhere on this day (local data)`;
  const days = ((inputs && inputs.params && inputs.params.observedDays) || ['2026-11-10', '2026-11-12']).map(fmtDay);
  const list = days.length === 2 ? `${days[0].split(' ')[0]} and ${days[1]}` : days.join(', ');
  return `No real identities for this day: flights observed elsewhere exist for ${list} only.`;
}

/**
 * repCandidates(overlays, inputs) -> [{flight, role, airline, minLocal, type}] (owner question Q1: OFF by default; LOCAL
 * only: needs the overlay of every observed day): a flight number observed on EVERY given day within +-20 min of the same
 * local time, same airline and role; type only if identical on every day; never a registration.
 */
export function repCandidates(overlays, inputs, tolMin = 20) {
  const L = (overlays || []).filter(Boolean);
  if (L.length < 2) return [];
  const off = ((inputs && inputs.params && inputs.params.utcOffsetH) ?? 8) * 60;
  const minLocal = (t) => (((Math.floor(t / 60) + off) % 1440) + 1440) % 1440;
  const keyed = L.map(o => {
    const m = new Map();
    for (const r of o.records) if (r.flight) { const k = r.flight + '|' + r.role; if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    return m;
  });
  const out = [];
  for (const [k, rs] of [...keyed[0].entries()].sort((a, b) => a[0] < b[0] ? -1 : 1)) {
    for (const r of rs) {
      const t0 = minLocal(r.t_sha);
      let ok = true; const types = new Set([r.type]); const mins = [t0];
      for (const M of keyed.slice(1)) {
        const c = (M.get(k) || []).find(x => x.airline === r.airline && Math.min(Math.abs(minLocal(x.t_sha) - t0), 1440 - Math.abs(minLocal(x.t_sha) - t0)) <= tolMin);
        if (!c) { ok = false; break; }
        types.add(c.type); mins.push(minLocal(c.t_sha));
      }
      if (ok) out.push({ flight: r.flight, role: r.role, airline: r.airline, minLocal: Math.round(mins.reduce((s, x) => s + x, 0) / mins.length), type: types.size === 1 ? r.type : null });
    }
  }
  return out;
}
