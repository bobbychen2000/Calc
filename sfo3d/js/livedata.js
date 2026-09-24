// Parse a live snapshot (METAR + ADS-B) into simulation inputs. Pure JS (runs in Node and browser).
import { llToWorld, ARP, runwayByEnd } from './geo.js';
import { ICAO_MAP } from './aircraft/types.js';

const FT = 0.3048, KT = 0.514444;
export function parseMetar(line) {
  const out = { raw: line.trim() };
  const m = /(\d{2})(\d{2})(\d{2})Z/.exec(line); if (m) out.time = { day: +m[1], h: +m[2], min: +m[3] };
  const w = /\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b/.exec(line); if (w) { out.windDir = w[1] === 'VRB' ? null : +w[1]; out.windKt = +w[2]; }
  const v = /\b(\d{1,2})SM\b/.exec(line); if (v) out.visSM = +v[1];
  out.clouds = []; const re = /\b(FEW|SCT|BKN|OVC)(\d{3})\b/g; let c; while ((c = re.exec(line))) out.clouds.push({ cover: c[1], ft: +c[2] * 100 });
  const t = /\b(M?\d{2})\/(M?\d{2})\b/.exec(line); if (t) { out.tempC = +t[1].replace('M', '-'); out.dewC = +t[2].replace('M', '-'); }
  const a = /\bA(\d{4})\b/.exec(line); if (a) out.altim = +a[1] / 100;
  return out;
}
export function parseAdsb(csv) {
  const lines = csv.trim().split(/\r?\n/); const hdr = lines[0].split(',');
  return lines.slice(1).map(l => { const f = l.split(','); const o = {}; hdr.forEach((h, i) => o[h] = f[i]); return o; }).map(o => ({
    hex: o.hex, flight: o.flight === 'N/A' ? null : o.flight, icao: o.t === 'N/A' ? null : o.t, reg: o.r === 'N/A' ? null : o.r,
    lat: +o.lat, lon: +o.lon, ground: o.alt_baro === 'ground', altFt: o.alt_baro === 'ground' ? 0 : +o.alt_baro,
    gsKt: +o.gs || 0, track: o.track === 'N/A' ? null : +o.track, vsFpm: o.baro_rate === 'N/A' ? null : +o.baro_rate,
  }));
}
// Registration-based type inference when the feed has no type (documented guesses)
export function inferType(a) {
  if (a.icao && ICAO_MAP[a.icao]) return { key: ICAO_MAP[a.icao], icao: a.icao, inferred: false };
  if (a.reg && /^N3\d\dDU$/.test(a.reg)) return { key: 'bcs3', icao: 'BCS3', inferred: true }; // Delta A220-300 registration block
  return { key: 'b738', icao: null, inferred: true };
}
const COVER = { FEW: 0.14, SCT: 0.4, BKN: 0.68, OVC: 0.95 };
const TYPE_NAMES = { B39M: 'Boeing 737 MAX 9', B38M: 'Boeing 737 MAX 8', B738: 'Boeing 737-800', B739: 'Boeing 737-900ER', B737: 'Boeing 737-700', B789: 'Boeing 787-9', B772: 'Boeing 777-200', B77W: 'Boeing 777-300ER', B753: 'Boeing 757-300', B752: 'Boeing 757-200', A319: 'Airbus A319', A320: 'Airbus A320', A321: 'Airbus A321', A21N: 'Airbus A321neo', E75L: 'Embraer E175', CRJ2: 'Bombardier CRJ200', BCS3: 'Airbus A220-300' };

export function buildLive(metarText, adsbCsv, nowMs) {
  const metars = metarText.trim().split(/\r?\n/).map(parseMetar);
  const M = metars[0]; // latest
  const ac = parseAdsb(adsbCsv);
  const now = new Date(nowMs);
  const lower = M.clouds.slice().sort((a, b) => a.ft - b.ft);
  const main = lower.find(c => c.cover !== 'FEW') || lower[0];
  const few = lower.find(c => c.cover === 'FEW' && c !== main);
  const env = {
    utc: now.toISOString(),
    visibilityM: M.visSM >= 10 ? 30000 : M.visSM * 1609,
    cloudCover: main ? COVER[main.cover] : 0.05, cloudBase: main ? Math.max(150, main.ft * FT) : 1500,
    cloudLow: few ? { cover: COVER.FEW, base: few.ft * FT } : null,
    windDir: M.windDir ?? 280, windKt: M.windKt ?? 5, slab: true,
  };
  // runway-aligned arrivals/departures
  const along = (a, end) => { const r = runwayByEnd(end); const w = llToWorld(a.lat, a.lon); const e = w[0], n = -w[2];
    const dx = e - r.thr[0], dy = n - r.thr[1]; const x = dx * r.dir[0] + dy * r.dir[1]; const off = -dx * r.dir[1] + dy * r.dir[0]; return { x, off }; };
  const label = (a) => { const t = inferType(a); const nm = TYPE_NAMES[t.icao] || (a.icao ? a.icao : null); return [a.flight, t.inferred && t.icao ? nm + ' (type inferred)' : nm, a.reg].filter(Boolean).join(' · '); };
  const arrivals = {};
  for (const a of ac.filter(a => !a.ground && a.altFt < 4000 && a.track != null && (a.vsFpm == null || a.vsFpm <= 0))) {
    let best = null;
    for (const end of ['28R', '28L', '1R', '1L']) {
      const r = runwayByEnd(end); const hdg = (Math.atan2(r.dir[0], r.dir[1]) * 180 / Math.PI + 360) % 360;
      const dh = Math.abs(((a.track - hdg + 540) % 360) - 180);
      const p = along(a, end);
      if (dh < 12 && p.x < 0 && p.x > -22000 && Math.abs(p.off) < 400 + (-p.x) * 0.03 && (!best || Math.abs(p.off) < Math.abs(best.off))) best = { end, a, x: p.x, off: p.off, label: label(a), type: inferType(a) };
    }
    if (best) (arrivals[best.end] = arrivals[best.end] || []).push(best);
  }
  for (const k in arrivals) arrivals[k].sort((p, q) => q.x - p.x);
  const away = (a) => { const w = llToWorld(a.lat, a.lon); const tr = a.track * Math.PI / 180; const v = [Math.sin(tr), -Math.cos(tr)]; const d = Math.hypot(w[0], w[2]); return (w[0] * v[0] + w[2] * v[1]) / d; };
  const departures = ac.filter(a => !a.ground && a.altFt < 6000 && a.track != null && ((a.vsFpm != null && a.vsFpm > 500) || (a.vsFpm == null && away(a) > 0.6))).map(a => ({ a, label: label(a), type: inferType(a), track: a.track }));
  const ground = ac.filter(a => a.ground && a.icao && ICAO_MAP[a.icao]);
  const taxiing = ground.filter(a => a.gsKt > 5);
  const parked = ground.filter(a => a.gsKt <= 5);
  const other = ac.filter(a => !a.ground);
  const fmtTime = (d) => { const pdt = new Date(d.getTime() - 7 * 3600e3); return pdt.toISOString().slice(11, 16) + ' PDT'; };
  const cloudsTxt = M.clouds.map(c => `${c.cover} ${c.ft.toLocaleString('en-US')} FT`).join(' · ');
  const info = {
    conditions: `LIVE ${fmtTime(now)}  ·  WIND ${String(M.windDir ?? 0).padStart(3, '0')}° ${M.windKt} KT  ·  VIS ${M.visSM} SM  ·  ${cloudsTxt}  ·  ${M.tempC}°C`,
    endLine: `Weather & traffic synced to live METAR and ADS-B data · ${now.toISOString().slice(0, 10)} ${now.toISOString().slice(11, 16)} UTC`,
    endLine2: 'Runways placed from FAA survey coordinates · procedural 3D recreation',
    metar: M.raw,
  };
  return { env, arrivals, departures, taxiing, parked, other, info, nowMs, metar: M };
}
