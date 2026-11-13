// Forked from sfo3d/js/live/feed.js @ a967f9b. Kept: normalizeAircraft (readsb jv2 fields, position time from the relay's
// _pt or now - seen_pos), parsePayload, StreamFeed (relay SSE full + delta events, poll fallback), fetchMetar (relay JSON or
// raw lines). Changed: normalizeAircraft adds the hwd3d relay fields of fork map 2.1/2.7 - masked (_masked: D1),
// dbFlags (readsb README-json.md: PIA = dbFlags & 4, LADD = dbFlags & 8, quoted by P1 in docs/phase2_relay.md section 3),
// mx (_mx: Mictronics fill {r, t, d, op}), nacp (nac_p), nic, sil-free; fetchMetar defaults to KHWD on the relay
// (/api/metar?ids=KHWD&format=json); StreamFeed takes an optional ?history (P1: the relay replays the last S seconds first,
// so a display lookahead_s behind has fixes on both sides of a hole at once). Dropped: SOURCES + the direct-poll Feed (a
// browser polling adsb.lol itself would break the one-shared-poll rule of the relay and adsb.lol's 500 requests/day per IP,
// docs/phase2_relay.md section 3), Routes (no routes for GA), fetchGates / fetchTaf (SFO only; KHWD has no TAF).
// Node-pure except StreamFeed / fetchMetar (they need EventSource / fetch at call time only).
const num = (v) => (v === undefined || v === null || v === '' || v === 'N/A' || Number.isNaN(+v)) ? null : +v;
const str = (v) => (v === undefined || v === null || v === '' || v === 'N/A') ? null : String(v);

export function normalizeAircraft(a, nowMs) {
  const ground = a.alt_baro === 'ground' || a.ground === true;
  const pos = (a.lat != null && a.lon != null) ? a : a.lastPosition;
  const lat = num(pos && pos.lat), lon = num(pos && pos.lon);
  if (lat === null || lon === null) return null;
  if (!(a.lat != null) && a.lastPosition && num(a.lastPosition.seen_pos) > 60) return null; // stale position only
  const seenPos = num(pos.seen_pos) ?? num(a.seen) ?? 0;
  const mx = a._mx && typeof a._mx === 'object' ? { r: str(a._mx.r), t: str(a._mx.t), d: str(a._mx.d), op: str(a._mx.op) } : null;
  const dbFlags = num(a.dbFlags);
  return {
    hex: String(a.hex || '').toLowerCase(), flight: str(a.flight) ? String(a.flight).trim() || null : null,
    reg: str(a.r), icao: str(a.t), desc: str(a.desc), ownOp: str(a.ownOp), year: str(a.year), srcType: str(a.type),
    lat, lon, ground, altBaro: ground ? null : num(a.alt_baro), altGeom: ground ? null : num(a.alt_geom),
    gs: num(a.gs), track: num(a.track), trueHeading: num(a.true_heading), magHeading: num(a.mag_heading), trackRate: num(a.track_rate), roll: num(a.roll),
    baroRate: num(a.baro_rate), geomRate: num(a.geom_rate), squawk: str(a.squawk), category: str(a.category),
    emergency: a.emergency && a.emergency !== 'none' ? a.emergency : null, navAlt: num(a.nav_altitude_mcp), navQnh: num(a.nav_qnh),
    // position time: the relay's absolute _pt (s, relay clock) or provider now - seen_pos (readsb README-json.md)
    t: num(a._pt) != null && !(a.lat == null && a.lastPosition) ? num(a._pt) * 1000 : nowMs - seenPos * 1000, seen: num(a.seen) ?? 0,
    veh: a._veh === 1, src: str(a._src), prov: str(a._prov), // relay: sticky ground-vehicle flag, position provider, providers
    mlat: Array.isArray(a.mlat) ? a.mlat : null, tisb: Array.isArray(a.tisb) ? a.tisb : null,
    nacp: num(a.nac_p), nic: num(a.nic),
    // D1 (fork map 2.1): masked by the relay / pack builder, or flagged LADD (8) / PIA (4) and not yet masked (defence in depth)
    masked: !!a._masked || (dbFlags != null && (dbFlags & 12) !== 0) || /^x[0-9a-f]{8}$/.test(String(a.hex || '')),
    // why (fix round 1): 'd1' (flagged LADD / PIA), 'type-only' (a type-only relay / pack masks every aircraft), 'unknown'
    // (an older pack: _masked 1, or only the masked key form) - the UI claims LADD / PIA only for 'd1'
    maskWhy: (dbFlags != null && (dbFlags & 12) !== 0) || a._masked === 'd1' ? 'd1' : a._masked === 'type-only' ? 'type-only' : (a._masked || /^x[0-9a-f]{8}$/.test(String(a.hex || ''))) ? 'unknown' : null,
    dbFlags, mx,
  };
}

export function parsePayload(json, fallbackNow = Date.now()) {
  const list = json.ac || json.aircraft || [];
  const n = num(json.now), c = num(json.ctime);
  const now = n != null ? (n > 1e12 ? n : n * 1000) : c != null ? c : fallbackNow;
  // dataNow (ms): the relay's data clock (the recording's time in replay) for js/env/clock.js
  return { now, dataNow: num(json.dataNow), source: json._source || null, msg: json.msg || null, aircraft: list.map(a => normalizeAircraft(a, now)).filter(Boolean) };
}

// Relay stream: Server-Sent Events from hwd_live_server.py /api/stream?delta=1 (full 'adsb' events, 'delta' events with
// changed records and gone keys). Keeps the full aircraft list and hands it to onData after every event. Falls back to
// polling /api/adsb when EventSource fails. (sfo3d design; the replay shim fakes both endpoints.)
export class StreamFeed {
  constructor({ url = 'api/stream?delta=1', pollUrl = 'api/adsb', onData, onStatus, onForget = null, pollMs = 2000, history = 0 } = {}) {
    if (history > 0 && !/history=/.test(url)) url += (url.includes('?') ? '&' : '?') + 'history=' + Math.min(120, Math.round(history));
    Object.assign(this, { url, pollUrl, onData, onStatus, onForget, pollMs });
    this.map = new Map(); this.seq = 0; this.es = null; this.mode = null; this.lastOk = 0; this.fails = 0; this.timer = null; this.running = false; this.head = null;
  }
  start() { if (this.running) return; this.running = true; if (typeof EventSource !== 'undefined') this.sse(); else this.poll(); }
  stop() { this.running = false; if (this.es) this.es.close(); this.es = null; clearTimeout(this.timer); }
  emit(head) {
    this.lastOk = Date.now(); this.fails = 0; this.head = head;
    const json = { ac: [...this.map.values()], now: head.now, dataNow: head.dataNow, _source: head._source, msg: head.msg };
    const p = parsePayload(json);
    this.onStatus && this.onStatus({ ok: true, source: { name: head._source || 'local relay' }, count: p.aircraft.length, mode: this.mode });
    this.onData && this.onData(p, { name: 'local relay' });
  }
  sse() {
    this.mode = 'stream'; const es = this.es = new EventSource(this.url);
    es.addEventListener('adsb', (ev) => { try { const j = JSON.parse(ev.data); this.map.clear(); for (const a of j.ac || []) this.map.set(a.hex, a); this.seq = j.seq; this.emit(j); } catch (e) { } });
    // D1 late flag (fix round 1): the relay names keys it published unmasked before a LADD/PIA flag arrived (open streams, and
    // since fix round 2 the poll answers too); the app drops their identity at once (traffic.forget)
    es.addEventListener('forget', (ev) => { try { const j = JSON.parse(ev.data); for (const k of j.forget || []) this.map.delete(k); this.onForget && this.onForget(j.forget || []); } catch (e) { } });
    es.addEventListener('delta', (ev) => { try { const j = JSON.parse(ev.data); for (const a of j.ac || []) this.map.set(a.hex, a); for (const k of j.gone || []) this.map.delete(k); this.seq = j.seq; this.emit(j); } catch (e) { } });
    es.onerror = () => {
      this.fails++; this.onStatus && this.onStatus({ ok: false, source: { name: 'local relay' }, error: 'stream interrupted' });
      if (this.fails >= 3 && !this.lastOk) { es.close(); this.es = null; this.poll(); } // no stream at all: poll instead
    };
  }
  async poll() {
    this.mode = 'poll'; if (!this.running) return;
    let wait = this.pollMs;
    try {
      // ?since=<seq of the last answer>: the relay adds 'forget' (D1 late flags) for keys this client was shown (fix round 2:
      // the forget event used to reach SSE streams only)
      const u = this.seq ? this.pollUrl + (this.pollUrl.includes('?') ? '&' : '?') + 'since=' + encodeURIComponent(this.seq) : this.pollUrl;
      const r = await fetch(u, { cache: 'no-store' }); if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      if (Array.isArray(j.forget) && j.forget.length) { for (const k of j.forget) this.map.delete(k); this.onForget && this.onForget(j.forget); }
      this.map.clear(); for (const a of j.ac || []) this.map.set(a.hex, a); if (j.seq != null) this.seq = j.seq; this.emit(j);
    } catch (e) { this.fails++; wait = Math.min(15000, 1000 * Math.pow(1.6, Math.min(this.fails, 8))); this.onStatus && this.onStatus({ ok: false, source: { name: 'local relay' }, error: e.message || 'failed' }); }
    this.timer = setTimeout(() => this.poll(), wait);
  }
}

// METAR through the relay only (aviationweather.gov sends no CORS header). -> the relay's JSON list [{obsTime (s), rawOb,
// ...}] newest first (last 3 h), raw lines -> [{rawOb}], or null. In replay the relay / shim returns only reports observed
// at or before the replay time (502 otherwise -> null).
export async function fetchMetar(station = 'KHWD', url = null) {
  url = url || `api/metar?ids=${encodeURIComponent(station)}&format=json`;
  try {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) return null; const t = (await r.text()).trim(); if (!t) return null;
    if (t[0] === '[') { const j = JSON.parse(t); return Array.isArray(j) ? j : null; }
    return t.split(/\r?\n/).map(l => l.trim()).filter(Boolean).map(rawOb => ({ rawOb }));
  } catch (e) { return null; }
}
