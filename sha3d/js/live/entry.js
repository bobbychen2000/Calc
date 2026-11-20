// forked from sfo3d@e3218d6 js/live/entry.js
// Entry point: data injection, the extension files, model sources and the relay, then startApp.
// sha3d changes: the data are the window globals of the data/*.js scripts that live.html loads before this module
// (window.SHA_AIRPORT, SHA_STANDS, SHA_TAXIGRAPH, SHA_GROUND_S2) - injected into the app, never imported at module scope
// (arch.md R4); no snapshot mode yet; models by URL from sfo3d (window.SHA_MODEL_BASE, default ../sfo3d/data/models/,
// not copied); relay detection lives in js/live/relay.js (owned by the relay package; OFF unless ?relay=1).
import { startApp } from './app.js';
// extension files (one per parallel package; each registers itself with js/live/ext.js)
import './markings.js';
import './gates.js';
import './terminals.js';
import { detectRelay } from './relay.js';
import { aboutHtml, attribHtml } from './about.js';

// the 23 converted sfo3d models (sfo3d@e3218d6 js/live/entry.js MODEL_KEYS); C919 / C909 come in Phase 4
const MODEL_KEYS = ['a319', 'a320', 'a321', 'a333', 'a359', 'a388', 'b738', 'b744', 'b748', 'b752', 'b763', 'b772', 'b77w', 'b788', 'bcs1', 'bcs3', 'crj2', 'crj7', 'crj9', 'e170', 'e190', 'e75l', 'md11'];
function b64ToBuf(s) { const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
(async () => {
  const q = new URLSearchParams(location.search);
  const airport = window.SHA_AIRPORT;
  if (!airport) throw new Error('data/sha_airport.js did not load (window.SHA_AIRPORT missing)');
  const mode = q.get('mode') || window.SHA_MODE || 'live';
  const relayInfo = mode === 'live' ? await detectRelay() : null; const relay = !!relayInfo;
  const models = {};
  for (const k of MODEL_KEYS) {
    if (window.SHA_EMBED && window.SHA_EMBED[k]) models[k] = () => b64ToBuf(window.SHA_EMBED[k]);
    else models[k] = (window.SHA_MODEL_BASE || '../sfo3d/data/models/') + k + (window.SHA_MODEL_EXT || '.sfom');
  }
  const app = await startApp({ mode, relay, relayInfo, airport, stands: window.SHA_STANDS || null, taxigraph: window.SHA_TAXIGRAPH || null, s2: window.SHA_GROUND_S2 || null,
    models, about: aboutHtml({ mode, relay, s2: !!window.SHA_GROUND_S2 }), attrib: attribHtml({ mode }) });
  window.__shaReady = true;
  return app;
})().catch(e => { console.error(e); window.__shaError = String(e && e.stack || e); });
