// forked from sfo3d@e3218d6 js/live/entry.js
// Entry point: data injection, the extension files, model sources, the relay and the MODE, then startApp.
// sha3d changes: the data are the window globals of the data/*.js scripts that live.html loads before this module
// (window.SHA_AIRPORT, SHA_STANDS, SHA_TAXIGRAPH, SHA_GROUND_S2, SHA_SNAPSHOT) - injected into the app, never imported at
// module scope (arch.md R4); models by URL from sfo3d (window.SHA_MODEL_BASE, default ../sfo3d/data/models/, not copied);
// relay detection lives in js/live/relay.js (OFF unless ?relay=1 / window.SHA_RELAY; the relay's root redirects there).
//
// Modes (P2e), ?mode= or window.SHA_MODE, default 'auto':
//   'live'      a relay answers /api/ping {shalive: 1}: wall-clock time, the relay's ZSSS METAR / TAF (decoded from the raw
//               text), observed ADS-B only if the relay runs with --adsb. (?mode=live without a relay: wall clock, no
//               weather - the Phase 2 core behaviour, kept for QA.)
//   'snapshot'  static, no network at all: the recorded METARs / TAF of data/sha_snapshot.js at its instant (window.
//               SHA_SNAPSHOT.now; ?t= still overrides the environment time) and its traffic set (empty in Phase 2; a
//               replay set of simulated, inferred traffic comes in Phase 3).
//   'auto'      'live' when the relay answers, else 'snapshot'.
import { startApp } from './app.js';
// extension files (one per parallel package; each registers itself with js/live/ext.js)
import './markings.js';
import './gates.js';
import './terminals.js';
import './shell.js';            // UI shell (P2e): legend, stand labels / cards, runway mode, status, observed ADS-B
import { detectRelay, relayState } from './relay.js';
import { aboutHtml, attribHtml } from './about.js';
import { setSnapshotWx } from '../env/presets.js';

// the 23 converted sfo3d models (sfo3d@e3218d6 js/live/entry.js MODEL_KEYS); C919 / C909 come in Phase 4
const MODEL_KEYS = ['a319', 'a320', 'a321', 'a333', 'a359', 'a388', 'b738', 'b744', 'b748', 'b752', 'b763', 'b772', 'b77w', 'b788', 'bcs1', 'bcs3', 'crj2', 'crj7', 'crj9', 'e170', 'e190', 'e75l', 'md11'];
function b64ToBuf(s) { const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
(async () => {
  const q = new URLSearchParams(location.search);
  const airport = window.SHA_AIRPORT;
  if (!airport) throw new Error('data/sha_airport.js did not load (window.SHA_AIRPORT missing)');
  const want = (q.get('mode') || window.SHA_MODE || 'auto').toLowerCase();
  const relayInfo = want === 'snapshot' ? null : await detectRelay(); const relay = !!relayInfo;
  const snap = window.SHA_SNAPSHOT || null;
  let mode = want === 'live' ? 'live' : want === 'snapshot' ? 'snapshot' : relay ? 'live' : 'snapshot';
  if (mode === 'snapshot' && !snap) mode = 'live';          // no snapshot data: the plain static scene (wall clock)
  const snapshot = mode === 'snapshot' ? { now: snap.now, nowUtc: snap.now_utc, metars: snap.metars || [], tafs: snap.tafs || [], traffic: snap.traffic || { kind: 'empty', ac: [] } } : null;
  if (snapshot) setSnapshotWx({ metars: snapshot.metars, tafs: snapshot.tafs });
  const models = {};
  for (const k of MODEL_KEYS) {
    if (window.SHA_EMBED && window.SHA_EMBED[k]) models[k] = () => b64ToBuf(window.SHA_EMBED[k]);
    else models[k] = (window.SHA_MODEL_BASE || '../sfo3d/data/models/') + k + (window.SHA_MODEL_EXT || '.sfom');
  }
  const modeInfo = { mode, want, relay, relayInfo, relayWanted: relayState.wanted, relayError: relayState.error, snapshot };
  const app = await startApp({ mode, relay, relayInfo, snapshot, modeInfo, airport, stands: window.SHA_STANDS || null, taxigraph: window.SHA_TAXIGRAPH || null, s2: window.SHA_GROUND_S2 || null,
    models, about: aboutHtml({ ...modeInfo, s2: !!window.SHA_GROUND_S2 }), attrib: attribHtml({ mode }) });
  window.__shaReady = true;
  return app;
})().catch(e => { console.error(e); window.__shaError = String(e && e.stack || e); });
