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
    hex: String(a.hex || '').toLowerCase().replace(/^~/, ''), flight: str(a.flight) ? String(a.flight).trim() || null : null,
    reg: str(a.r), icao: str(a.t), desc: str(a.desc), ownOp: str(a.ownOp), year: str(a.year), srcType: str(a.type),
    lat, lon, ground, altBaro: ground ? null : num(a.alt_baro), altGeom: ground ? null : num(a.alt_geom),
    gs: num(a.gs), track: num(a.track), trueHeading: num(a.true_heading), magHeading: num(a.mag_heading), trackRate: num(a.track_rate), roll: num(a.roll),
    baroRate: num(a.baro_rate), geomRate: num(a.geom_rate), squawk: str(a.squawk), category: str(a.category),
    emergency: a.emergency && a.emergency !== 'none' ? a.emergency : null, navAlt: num(a.nav_altitude_mcp), navQnh: num(a.nav_qnh),
    t: nowMs - seenPos * 1000, seen: num(a.seen) ?? 0,
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

// adsb.lol route lookup (origin/destination by callsign, from Virtual Radar Server standing data), batched
export class Routes {
  constructor({ url = 'https://api.adsb.lol/api/0/routeset' } = {}) { this.url = url; this.cache = new Map(); this.pending = new Set(); this.busy = false; }
  get(cs) { return this.cache.get(cs); }
  async request(list) { // list: [{callsign, lat, lng}]
    if (this.busy) return; const todo = list.filter(p => p.callsign && !this.cache.has(p.callsign) && !this.pending.has(p.callsign)).slice(0, 100);
    if (!todo.length) return;
    this.busy = true; todo.forEach(p => this.pending.add(p.callsign));
    let ok = false;
    try {
      const r = await fetch(this.url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ planes: todo }) });
      if (r.ok) {
        ok = true;
        const arr = await r.json();
        for (const x of arr) {
          const codes = (x._airport_codes_iata && x._airport_codes_iata !== 'unknown') ? x._airport_codes_iata.split('-') : null;
          this.cache.set(x.callsign, codes ? { codes, airports: (x._airports || []).map(a => ({ iata: a.iata, icao: a.icao, name: a.name, city: a.location, country: a.countryiso2 })), plausible: !!x.plausible } : null);
        }
      }
    } catch (e) { /* routes are optional */ }
    todo.forEach(p => { this.pending.delete(p.callsign); if (ok && !this.cache.has(p.callsign)) this.cache.set(p.callsign, null); });
    this.busy = false;
  }
}

export async function fetchMetar(station = 'KSFO', url = null) {
  try {
    const r = await fetch(url || `https://aviationweather.gov/api/data/metar?ids=${station}&format=raw&hours=2`, { cache: 'no-store' });
    if (!r.ok) return null; const t = (await r.text()).trim(); return t ? t.split('\n')[0].trim() : null;
  } catch (e) { return null; }
}
