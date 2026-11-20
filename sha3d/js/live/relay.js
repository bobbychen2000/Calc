// sha3d relay client configuration: OWNED BY THE RELAY PACKAGE (sha_live_server.py and its client side). Imported by
// js/live/entry.js; nothing else in the core edits these lines.
// Rules (task brief / docs/PLAN.md s.6b Q10): the relay is OFF unless enabled (?relay=1 or window.SHA_RELAY = true); the
// relay's User-Agent towards providers is generic (no owner details); OpenSky is never called; adsb.lol at most one
// request per 180 s (keyless quota 500 / day, and a recorder may share the IP). The browser never polls a provider
// directly in Phase 2: without a relay there is no traffic and no METAR (clear default sky, or ?metar=<raw report>).
export const RELAY = {
  enabled: (() => { try { const q = new URLSearchParams(location.search); return q.get('relay') === '1' || window.SHA_RELAY === true; } catch (e) { return false; } })(),
  ping: 'api/ping',              // GET -> {"shalive": 1, features: {...}}
  metar: 'api/metar?ids=ZSSS&format=json',   // relay-cached aviationweather.gov METARs (docs/phase1/sources_sim.md s.3.1)
  taf: 'api/taf?ids=ZSSS&format=json',
  metarPollMs: 60000,            // relay endpoint (its own upstream cache decides how often it fetches)
  adsbMinIntervalMs: 180000,     // adsb.lol: never more than one upstream request per 180 s (relay side)
};
/** {shalive: 1, ...} from the relay, or null (relay disabled, file://, or no relay answering). */
export async function detectRelay() {
  if (!RELAY.enabled || !/^https?:$/.test(location.protocol)) return null;
  try { const r = await fetch(RELAY.ping, { cache: 'no-store' }); if (!r.ok) return null; const j = await r.json(); return j && j.shalive ? j : null; } catch (e) { return null; }
}
/** relay METAR list [{obsTime, rawOb, ...}] or null */
export async function fetchMetarList() {
  try { const r = await fetch(RELAY.metar, { cache: 'no-store' }); if (!r.ok) return null; const j = await r.json(); return Array.isArray(j) && j.length ? j : null; } catch (e) { return null; }
}
