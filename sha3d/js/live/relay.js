// sha3d relay client: OWNED BY THE RELAY PACKAGE (P2e: sha_live_server.py and this file). Imported by js/live/entry.js
// (detectRelay) and the UI shell (js/live/shell.js: METAR / TAF / observed ADS-B polls).
// Rules (task brief / docs/PLAN.md s.6b Q10): the relay is OFF unless enabled (?relay=1 or window.SHA_RELAY = true; the
// relay's own root URL redirects to live.html?relay=1); the relay's User-Agent towards providers is generic (no owner
// details); OpenSky is never called; adsb.lol at most one upstream request per 180 s and only while the relay runs with
// --adsb (OFF by default: keyless quota 500 / day / IP, and a recorder may share the IP). The browser never polls a
// provider directly: without a relay there is no live data (the 'snapshot' mode uses data/sha_snapshot.js).
export const RELAY = {
  enabled: (() => { try { const q = new URLSearchParams(location.search); return q.get('relay') === '1' || window.SHA_RELAY === true; } catch (e) { return false; } })(),
  ping: 'api/ping',                           // GET -> {"shalive": 1, mode, dataNow, features: {metar, taf, adsb}, attribution, ua}
  metar: 'api/metar?ids=ZSSS&format=json',    // [{icaoId, metarType, obsTime, reportTime, receiptTime, rawOb}], newest first
  taf: 'api/taf?ids=ZSSS&format=json',        // [{icaoId, issueTime, validTimeFrom, validTimeTo, rawTAF}]
  adsb: 'api/adsb',                           // {enabled, ac: [adsb_icao records, src 'obs'], excluded, next_request_in_s, ...}
  metarPollMs: 60000,            // client -> relay; the relay itself asks aviationweather.gov at most once per 10 min
  tafPollMs: 15 * 60000,
  adsbPollMs: 60000,             // client -> relay; the relay asks adsb.lol at most once per 180 s (and only with --adsb)
  adsbMinIntervalMs: 180000,     // adsb.lol: never more than one upstream request per 180 s (relay side, enforced there)
};
/** Relay detection state for the UI: {wanted, answered, error}. */
export const relayState = { wanted: RELAY.enabled, answered: false, error: null };
/** {shalive: 1, ...} from the relay, or null (relay not enabled, file://, or no relay answering). */
export async function detectRelay() {
  if (!RELAY.enabled) return null;
  if (!/^https?:$/.test(location.protocol)) { relayState.error = 'file:// page: no relay'; return null; }
  try {
    const r = await fetch(RELAY.ping, { cache: 'no-store' });
    if (!r.ok) { relayState.error = 'HTTP ' + r.status; return null; }
    const j = await r.json();
    if (j && j.shalive) { relayState.answered = true; return j; }
    relayState.error = 'not a SHA relay'; return null;
  } catch (e) { relayState.error = String(e && e.message || e).slice(0, 120); return null; }
}
const getJson = async (url) => { try { const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) return null; return await r.json(); } catch (e) { return null; } };
/** relay METAR list [{obsTime, rawOb, ...}] (newest first) or null. Decode rawOb, never AWC JSON weather fields. */
export async function fetchMetarList() { const j = await getJson(RELAY.metar); return Array.isArray(j) && j.length ? j : null; }
/** relay TAF list [{issueTime, rawTAF, ...}] or null */
export async function fetchTaf() { const j = await getJson(RELAY.taf); return Array.isArray(j) && j.length ? j[0] : null; }
/** relay observed-aircraft payload {enabled, ac, ...} or null */
export async function fetchAdsb() { const j = await getJson(RELAY.adsb); return j && typeof j === 'object' ? j : null; }
