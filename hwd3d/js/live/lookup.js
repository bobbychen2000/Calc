// Identity of a GA track: registration, callsign, type, model and operator, with the LADD / PIA rule D1 (hwd3d Phase 2, P3).
// Replaces sfo3d/js/live/lookup.js @ a967f9b (airline / brand / livery tables, data/lookup.js, data/brands.js - not
// forked). Kept from it: nNumberFromHex (the FAA's fixed N-number order of the US Mode S block A00001-ADF7C7, verified by
// sfo3d against 392,062 of 392,213 US entries of the tar1090-db, its docs/research/liveries_impl.md) and isVehicle.
// Node-pure (fetchIdent needs fetch at call time only).
//
// D1 (docs/PLAN.md 6a, fork map 2.0 / 2.1): an aircraft flagged LADD (dbFlags & 8) or PIA (dbFlags & 4) - bit meanings
// quoted by P1 from readsb README-json.md @ 88877b9 (docs/phase2_relay.md section 3) - shows its TYPE ONLY: no
// registration, callsign, operator or address anywhere. The relay and the pack builder already mask such records
// (`_masked`, key 'x' + 8 hex, identity fields removed); this module masks again whenever a record says masked, carries
// those dbFlags bits, or has an 'x' key (defence in depth), and a masked identity never becomes unmasked for that track.
// A key is never used as a label (fork map 2.0: no UI text may contain a key).
//
//   identity(info, key, prev) -> { masked, label, reg, regSrc, callsign, operator, opSrc, icaoType, typeName, typeSrc,
//                                  category, src: {...} }
//   fetchIdent(key, {url}) -> relay /api/ident answer (cached 10 min per key; masked keys are not asked)
import { ACD } from '../aircraft/ga_acd.js';
import { HELI_TYPES } from '../aircraft/ga_dims.js';

const NCH = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const NSUF = 1 + 24 * 25, NB4 = 1 + 24 + 10, NB3 = 10 * NB4 + NSUF, NB2 = 10 * NB3 + NSUF, NB1 = 10 * NB2 + NSUF;
const nSuffix = (r) => { if (r === 0) return ''; r -= 1; const i = Math.floor(r / 25), j = r % 25; return NCH[i] + (j ? NCH[j - 1] : ''); };
export function nNumberFromHex(hex) {
  if (!/^[0-9a-f]{6}$/i.test(hex || '')) return null;
  const v = parseInt(hex, 16); if (!(v >= 0xA00001 && v <= 0xADF7C7)) return null;
  let r = v - 0xA00001; let out = 'N' + (Math.floor(r / NB1) + 1); r %= NB1;
  if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB2); r %= NB2; if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB3); r %= NB3; if (r < NSUF) return out + nSuffix(r); r -= NSUF;
  out += Math.floor(r / NB4); r %= NB4; if (r === 0) return out; return out + (r <= 24 ? NCH[r - 1] : String(r - 25));
}

export function isVehicle(info) {
  if (!info) return false;
  if (info === true || info.vehicle) return true;
  const cat = info.category || null, t = info.icao || info.type || null;
  return !!((cat && /^C[1-7]$/.test(cat)) || (t && ['SERV', 'GRND', 'TWR'].includes(t)));
}

export const isMaskedKey = (k) => /^x[0-9a-f]{8}$/.test(String(k || ''));
export const isMaskedRecord = (a) => !!(a && (a.masked || (a.dbFlags != null && (a.dbFlags & 12) !== 0) || isMaskedKey(a.hex)));

// a callsign worth showing: an ICAO-style flight id (3 letters + digits/letters) or an N-number; anything else (blank,
// squawk-like '0000', a registration of another state) is shown as is when it has letters
const ICAO_CS = /^[A-Z]{3}[0-9][0-9A-Z]{0,3}$/;
const N_NUM = /^N[1-9][0-9A-Z]{0,4}$/;

export function typeName(icao, desc, mxD) {
  if (desc) return { name: desc, src: 'adsb' };
  if (mxD) return { name: mxD, src: 'mictronics' };
  const a = icao && ACD[icao]; if (a) return { name: a[8], src: 'faa_acd' };
  if (icao && HELI_TYPES.has(icao)) return { name: `${icao} helicopter`, src: 'inf' };
  return { name: null, src: null };
}

// info: the merged per-track record of the newest reports (traffic.js setInfo): { flight, reg, icao, desc, ownOp, category,
// masked, mx }. prev: the previous identity of this track (masking is sticky).
export function identity(info, key, prev = null) {
  const masked = !!(info.masked || isMaskedKey(key) || (prev && prev.masked));
  const mx = info.mx || null;
  const icaoType = info.icao || (mx && mx.t) || null;
  const typeSrc = info.icao ? 'adsb' : mx && mx.t ? 'mictronics' : null;
  const tn = typeName(icaoType, info.desc, mx && mx.d);
  const category = info.category || null;
  if (masked) {
    return { masked: true, label: icaoType || 'Aircraft', reg: null, regSrc: null, callsign: null, operator: null, opSrc: null,
      icaoType, typeName: tn.name, typeSrc, category, src: { type: typeSrc, name: tn.src, d1: 'LADD/PIA: type only (D1)' } };
  }
  let reg = info.reg || (mx && mx.r) || null, regSrc = info.reg ? 'adsb' : mx && mx.r ? 'mictronics' : null;
  if (!reg) { const n = nNumberFromHex(key); if (n) { reg = n; regSrc = 'icao_address'; } }
  const cs = info.flight ? String(info.flight).trim().toUpperCase() : null;
  const callsign = cs && /[A-Z]/.test(cs) ? cs : null;
  const operator = info.ownOp || (mx && mx.op) || null, opSrc = info.ownOp ? 'adsb' : mx && mx.op ? 'mictronics' : null;
  // label: the callsign when it is an ICAO flight id or differs from the registration, else the registration, else the type
  const label = (callsign && (ICAO_CS.test(callsign) || !reg || callsign !== reg.replace(/-/g, ''))) ? callsign : reg || callsign || icaoType || 'Aircraft';
  return { masked: false, label, reg, regSrc, callsign, operator, opSrc, icaoType, typeName: tn.name, typeSrc, category,
    src: { type: typeSrc, name: tn.src, reg: regSrc, op: opSrc, callsign: callsign ? (ICAO_CS.test(callsign) ? 'adsb (ICAO flight id)' : N_NUM.test(callsign) ? 'adsb (registration as callsign)' : 'adsb') : null } };
}

// relay identity endpoint (P1: /api/ident?key=K answers only for aircraft in the relay's picture within 10 min; masked
// keys answer type only). Optional: the inline `_mx` already fills most fields. One request per key per 10 min at most.
const identCache = new Map();
export async function fetchIdent(key, { url = 'api/ident', now = Date.now() } = {}) {
  if (!key || isMaskedKey(key)) return null;
  const c = identCache.get(key); if (c && now - c.t < 600000) return c.v;
  identCache.set(key, { t: now, v: null });
  try {
    const r = await fetch(`${url}?key=${encodeURIComponent(key)}`, { cache: 'no-store' }); if (!r.ok) return null;
    const j = await r.json(); if (j && j.masked) { identCache.set(key, { t: now, v: { masked: true, t: j.t || null } }); return identCache.get(key).v; }
    const v = j ? { r: j.r || null, t: j.t || null, d: j.desc || null, op: j.op || null, flight: j.flight || null } : null;
    identCache.set(key, { t: now, v }); return v;
  } catch (e) { return null; }
}
