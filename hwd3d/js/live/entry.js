// Forked from sfo3d/js/live/entry.js @ a967f9b. Kept: the entry's job (pick the mode, detect the relay with api/ping, load
// the optional taxi graph dynamically, start the app, set the readiness / error flags for the harness). Changed (fork map
// 2.2 / 2.10): the relay is accepted only when its ping says {hwdlive: 1} (an sfo3d relay, {sfolive: 1}, is not); modes
// live | replay | snapshot; the replay pack of P1 (out/replay/pack.json.gz, hwd-pack/1) is replayed in the page through
// P1's shim (out/replay/replay_shim.js installReplay, imported BEFORE detectRelay so the app then runs its live code path)
// when ?mode=replay, or when no relay answers; the snapshot mode reads the same pack directly and hands one instant to the
// app; the airport is data/hwd_airport.js (HWD_AIRPORT, Phase 1); window.HWD_MODE / HWD_PACK and __hwdReady /
// __hwdError instead of the SFO names (fork map 2.0 names). Dropped: the 7 SFO data modules, the airliner model keys
// (MODEL_KEYS, SFO_EMBED: Phase 2 draws GA placeholders, fork map 2.9), data/snapshot.js (it mixes adsb.fi records, which
// may not be redistributed; the pack replaces it, fork map 1.7).
//
//   ?mode=live      (default) relay detected via api/ping: live, or the relay's own --replay; no relay -> the pack (replay)
//   ?mode=replay    the pack through the in-page shim (P1), real speed, looping; ?pack=<url> another pack
//   ?mode=snapshot  one instant of the pack, frozen (for the phone artifact); ?at=<ISO UTC | minutes into the window>
import { startApp } from './app.js';
import { HWD_AIRPORT } from '../../data/hwd_airport.js';
import { aboutHtml, attribHtml } from './about.js';

const PACK_DEFAULT = 'out/replay/pack.json.gz';   // P1 (tools/live/build_replay.py): the weekend window, type-only (D1)
// ?pack= takes only a same-origin relative path to a .json / .json.gz file (fix round 1: any URL was accepted, and the
// pack's description reached the About sheet's innerHTML)
const safePack = (p) => p && !/^[a-z][a-z0-9+.-]*:|^\/\/|\.\.|\\/i.test(p) && /^[\w./-]+\.json(\.gz)?$/.test(p) ? p : null;
const SHIM = '../../out/replay/replay_shim.js';    // P1 copies tools/live/replay_shim.js there at pack time

async function detectRelay() {
  if (!/^https?:$/.test(location.protocol)) return null;
  try {
    const r = await fetch('api/ping', { cache: 'no-store' }); if (!r.ok) return null;
    const j = await r.json(); return j && j.hwdlive === 1 ? j : null;
  } catch (e) { return null; }
}
// OSM taxi graph (ODbL, P1 tools/live/build_taxigraph.py); optional: the engine falls back to free motion without it
async function loadTaxigraph() { try { return (await import('../../data/hwd_taxigraph.js')).TAXIGRAPH; } catch (e) { console.warn('taxi graph not loaded', e); return null; } }
async function useShim(url) { const m = await import(SHIM); return m.installReplay({ url, loop: true }); }
// the pack itself (snapshot mode): gzip by magic bytes (a server may already have decoded it), as P1's shim does
async function loadPack(url) {
  const r = await fetch(url, { cache: 'no-store' }); if (!r.ok) throw new Error('replay pack HTTP ' + r.status + ' (' + url + ')');
  const buf = new Uint8Array(await r.arrayBuffer());
  let txt;
  if (buf[0] === 0x1f && buf[1] === 0x8b) {
    if (typeof DecompressionStream === 'undefined') throw new Error('this browser has no DecompressionStream (gzip)');
    txt = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
  } else txt = new TextDecoder().decode(buf);
  const pack = JSON.parse(txt);
  if (pack.v !== 'hwd-pack/1') throw new Error('not an hwd-pack/1 file (' + pack.v + ')');
  return pack;
}
// ?at= : an ISO UTC time, or minutes after the start of the window; default: the payload with the most aircraft that
// still has PRE_S of history before it and lookahead_s after it (the busiest instant of the window)
const PRE_S = 600;
function snapshotAt(pack, at) {
  const L = pack.lookahead_s || 60, lo = pack.from + Math.min(PRE_S, (pack.until - pack.from) / 3), hi = pack.until - L - 1;
  let S = null;
  if (at != null && at !== '') {
    if (/^\d+(\.\d+)?$/.test(at)) S = pack.from + L + (+at) * 60;
    else { const ms = Date.parse(/Z$|[+-]\d\d:?\d\d$/.test(at) ? at : at + 'Z'); if (Number.isFinite(ms)) S = ms / 1000; }
  }
  if (S == null) { let best = -1; for (const e of pack.events) if (e.T >= lo && e.T <= hi && e.p.d.length > best) { best = e.p.d.length; S = e.T; } }
  return Math.min(hi, Math.max(pack.from + L, S ?? (pack.from + pack.until) / 2));
}

(async () => {
  const q = new URLSearchParams(location.search);
  let mode = q.get('mode') || window.HWD_MODE || 'live';
  const packUrl = safePack(q.get('pack')) || window.HWD_PACK || PACK_DEFAULT;
  let relayInfo = null, replayInfo = null, snapshot = null, note = null;
  if (mode === 'snapshot') {
    const pack = await loadPack(packUrl);
    snapshot = { pack, at: snapshotAt(pack, q.get('at')), preS: PRE_S, url: packUrl };
  } else if (mode === 'replay') {
    try { replayInfo = await useShim(packUrl); } catch (e) { note = 'Replay pack not available (' + (e.message || e) + ').'; console.warn(note); }
    relayInfo = await detectRelay();
  } else {
    mode = 'live';
    relayInfo = await detectRelay();
    if (relayInfo && relayInfo.mode === 'replay') mode = 'replay';
    if (!relayInfo) {
      // no relay (opened from a plain static server or a file): the recorded pack instead, through the same shim (fork map 2.2)
      try { replayInfo = await useShim(packUrl); relayInfo = await detectRelay(); mode = 'replay'; note = 'No live relay answered: showing the recorded replay.'; }
      catch (e) { note = 'No live relay answered and no replay pack was found.'; }
    }
  }
  const taxigraph = await loadTaxigraph();
  const app = await startApp({ mode, relayInfo, replayInfo, snapshot, note, airport: HWD_AIRPORT, taxigraph,
    about: aboutHtml({ mode, relayInfo, replayInfo, snapshot }), attrib: attribHtml({ mode, relayInfo }) });
  window.__hwdReady = true;
  return app;
})().catch(e => { console.error(e); window.__hwdError = String(e && e.stack || e); const el = document.querySelector('#loading .msg'); if (el) el.textContent = 'Could not start: ' + (e && e.message || e); });
