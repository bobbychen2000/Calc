// Live ADS-B + METAR + route feeds. Response format: readsb "jv2" JSON as served by the adsb.lol API
// (github.com/adsblol/api) and the adsb.fi open data API (github.com/adsbfi/opendata): { ac: [...], now (ms), ... }.
export const SOURCES = [
  { name: 'adsb.lol', home: 'https://adsb.lol', url: (lat, lon, nm) => `https://api.adsb.lol/v2/point/${lat}/${lon}/${nm}` },
  { name: 'adsb.fi', home: 'https://adsb.fi', url: (lat, lon, nm) => `https://opendata.adsb.fi/api/v3/lat/${lat}/lon/${lon}/dist/${nm}` },
];
const num = (v) => (v === undefined || v === null || v === '' || v === 'N/A' || Number.isNaN(+v)) ? null : +v;
const str = (v) => (v === undefined || v === null || v === '' || v === 'N/A') ? null : String(v);

export function normalizeAircraft(a, nowMs) {
  const ground = a.alt_baro === 'ground' || a.ground === true;
  const pos = (a.lat != null && a.lon != null) ? a : a.lastPosition;
  const lat = num(pos && pos.lat), lon = num(pos && pos.lon);
  if (lat === null || lon === null) return null;
  if (!(a.lat != null) && a.lastPosition && num(a.lastPosition.seen_pos) > 60) return null; // stale position only
  const seenPos = num(pos.seen_pos) ?? num(a.seen) ?? 0;
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
    mlat: Array.isArray(a.mlat) ? a.mlat : null,
    // relay: the other provider's aircraft-database type when the two disagree (traffic.js resolveType)
    dbAlt: a._dbalt && a._dbalt.t ? { t: String(a._dbalt.t), desc: str(a._dbalt.desc), p: str(a._dbalt.p) } : null,
    // relay: the ICAO type of the model the FAA registry lists for this address (transport types; sfo_live_server.py FaaRegistry)
    faa: str(a._faa),
  };
}

export function parsePayload(json, fallbackNow = Date.now()) {
  const list = json.ac || json.aircraft || [];
  const n = num(json.now), c = num(json.ctime);
  const now = n != null ? (n > 1e12 ? n : n * 1000) : c != null ? c : fallbackNow;
  return { now, source: json._source || null, aircraft: list.map(a => normalizeAircraft(a, now)).filter(Boolean) };
}

export class Feed {
  constructor({ lat, lon, radiusNm = 30, intervalMs = 6000, sources = SOURCES, onData, onStatus }) {
    Object.assign(this, { lat, lon, radiusNm, intervalMs, sources, onData, onStatus });
    this.src = 0; this.fails = 0; this.timer = null; this.running = false; this.lastOk = 0; this.pause = 0;
  }
  start() { if (this.running) return; this.running = true; this.tick(); }
  stop() { this.running = false; clearTimeout(this.timer); }
  async tick() {
    if (!this.running) return;
    const s = this.sources[this.src];
    const ctl = new AbortController(); const to = setTimeout(() => ctl.abort(), 9000);
    let wait = this.intervalMs;
    try {
      const r = await fetch(s.url(this.lat.toFixed(4), this.lon.toFixed(4), this.radiusNm), { signal: ctl.signal, cache: 'no-store' });
      if (r.status === 429) { wait = 60000; throw new Error('rate limited (HTTP 429)'); }
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      const p = parsePayload(j);
      this.fails = 0; this.lastOk = Date.now();
      this.onStatus && this.onStatus({ ok: true, source: { ...s, name: p.source || s.name }, count: p.aircraft.length });
      this.onData && this.onData(p, s);
    } catch (e) {
      this.fails++;
      this.onStatus && this.onStatus({ ok: false, source: s, error: e.name === 'AbortError' ? 'timed out' : (e.message || 'blocked') });
      this.src = (this.src + 1) % this.sources.length; // rotate to the next provider
      if (wait < 60000) wait = Math.min(60000, 2000 * Math.pow(1.6, Math.min(this.fails, 8)));
    } finally { clearTimeout(to); }
    this.timer = setTimeout(() => this.tick(), document.hidden ? Math.max(wait, 30000) : wait);
  }
}

// Relay stream: Server-Sent Events from sfo_live_server.py /api/stream?delta=1 (one merged update per provider
// snapshot, ~1 Hz; docs/research/realtime_impl.md s.1). Keeps the full aircraft list (full + delta events) and hands it
// to onData after every event. Falls back to polling /api/adsb every second when EventSource fails.
export class StreamFeed {
  constructor({ url = 'api/stream?delta=1', pollUrl = 'api/adsb', onData, onStatus, pollMs = 1000 } = {}) {
    Object.assign(this, { url, pollUrl, onData, onStatus, pollMs });
    this.map = new Map(); this.seq = 0; this.es = null; this.mode = null; this.lastOk = 0; this.fails = 0; this.timer = null; this.running = false; this.head = null;
  }
  start() { if (this.running) return; this.running = true; if (typeof EventSource !== 'undefined') this.sse(); else this.poll(); }
  stop() { this.running = false; if (this.es) this.es.close(); this.es = null; clearTimeout(this.timer); }
  emit(head) {
    this.lastOk = Date.now(); this.fails = 0; this.head = head;
    const json = { ac: [...this.map.values()], now: head.now, _source: head._source };
    const p = parsePayload(json);
    this.onStatus && this.onStatus({ ok: true, source: { name: head._source || 'local relay' }, count: p.aircraft.length, mode: this.mode });
    this.onData && this.onData(p, { name: 'local relay' });
  }
  sse() {
    this.mode = 'stream'; const es = this.es = new EventSource(this.url);
    es.addEventListener('adsb', (ev) => { try { const j = JSON.parse(ev.data); this.map.clear(); for (const a of j.ac || []) this.map.set(a.hex, a); this.seq = j.seq; this.emit(j); } catch (e) { } });
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
      const r = await fetch(this.pollUrl, { cache: 'no-store' }); if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json(); this.map.clear(); for (const a of j.ac || []) this.map.set(a.hex, a); this.emit(j);
    } catch (e) { this.fails++; wait = Math.min(15000, 1000 * Math.pow(1.6, Math.min(this.fails, 8))); this.onStatus && this.onStatus({ ok: false, source: { name: 'local relay' }, error: e.message || 'failed' }); }
    this.timer = setTimeout(() => this.poll(), wait);
  }
}

// SFO's own stand allocation through the relay (/api/gates: flysfo.com flight-status, fetched upstream at most every
// 10 min; docs/research/gate_truth.md). Optional: the relay may run with --no-sfo-gates.
export async function fetchGates(url = 'api/gates') {
  try { const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) return null; const j = await r.json(); return j && j.byCallsign ? j : null; } catch (e) { return null; }
}

// Route lookup (origin/destination by callsign, Virtual Radar Server standing data via adsb.lol), batched.
// Only definite answers are cached: an error, an empty body (the adsb.lol routeset API answered HTTP 201 with no body
// on 24 Sep 2026, traffic_audit F5) or bad JSON leaves the callsigns uncached and pauses lookups for 30 s.
export class Routes {
  constructor({ url = 'https://api.adsb.lol/api/0/routeset' } = {}) { this.url = url; this.cache = new Map(); this.pending = new Set(); this.busy = false; this.retryAt = 0; }
  get(cs) { return this.cache.get(cs); }
  async request(list) { // list: [{callsign, lat, lng}]
    if (this.busy || Date.now() < this.retryAt) return; const todo = list.filter(p => p.callsign && !this.cache.has(p.callsign) && !this.pending.has(p.callsign)).slice(0, 100);
    if (!todo.length) return;
    this.busy = true; todo.forEach(p => this.pending.add(p.callsign));
    let ok = false;
    try {
      const r = await fetch(this.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ planes: todo }) });
      const txt = r.ok ? await r.text() : '';
      const arr = txt.trim() ? JSON.parse(txt) : null;
      if (Array.isArray(arr)) {
        for (const x of arr) {
          if (!x || !x.callsign) continue;
          const codes = (x._airport_codes_iata && x._airport_codes_iata !== 'unknown') ? x._airport_codes_iata.split('-') : null;
          this.cache.set(x.callsign, codes ? { codes, airports: (x._airports || []).map(a => ({ iata: a.iata, icao: a.icao, name: a.name, city: a.location, country: a.countryiso2, lat: a.lat ?? null, lon: a.lon ?? null })), plausible: !!x.plausible, sfo: x._sfo || null, src: x._src || null } : null);
        }
        ok = true;
      }
    } catch (e) { /* routes are optional */ }
    todo.forEach(p => { this.pending.delete(p.callsign); if (ok && !this.cache.has(p.callsign)) this.cache.set(p.callsign, null); });
    if (!ok) this.retryAt = Date.now() + 30000;
    this.busy = false;
  }
}

export async function fetchMetar(station = 'KSFO', url = null) {
  try {
    const r = await fetch(url || `https://aviationweather.gov/api/data/metar?ids=${station}&format=raw&hours=2`, { cache: 'no-store' });
    if (!r.ok) return null; const t = (await r.text()).trim(); return t ? t.split('\n')[0].trim() : null;
  } catch (e) { return null; }
}
