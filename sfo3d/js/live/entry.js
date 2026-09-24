// Entry point: chooses live / snapshot mode, model sources and the ADS-B relay, then starts the app.
import { startApp } from './app.js';
import { AIRPORT } from '../../data/sfo_airport.js';
import { SNAPSHOT, SNAPSHOT_METAR } from '../../data/snapshot.js';
import { DETAILS } from '../../data/sfo_details.js';
import { BUILDINGS } from '../../data/sfo_buildings.js';
import { STANDS } from '../../data/sfo_stands.js';
import { PAINT } from '../../data/sfo_paint.js';
import { PAVEMENT } from '../../data/sfo_pavement.js';
import { aboutHtml, attribHtml } from './about.js';

const MODEL_KEYS = ['a319', 'a320', 'a321', 'a333', 'a359', 'a388', 'b738', 'b744', 'b748', 'b752', 'b763', 'b788', 'bcs1', 'bcs3', 'crj2', 'crj7', 'crj9', 'e170', 'e190', 'e75l', 'md11'];
function b64ToBuf(s) { const bin = atob(s); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
async function detectRelay() {
  if (!/^https?:$/.test(location.protocol)) return null;
  try { const r = await fetch('api/ping', { cache: 'no-store' }); if (!r.ok) return null; const j = await r.json(); return j && j.sfolive ? j : null; } catch (e) { return null; }
}
// OSM taxi graph (ODbL, tools/live/build_taxigraph.py); optional: the engine falls back to free motion without it
async function loadTaxigraph() { try { return (await import('../../data/sfo_taxigraph.js')).TAXIGRAPH; } catch (e) { return null; } }
(async () => {
  const q = new URLSearchParams(location.search);
  const mode = q.get('mode') || window.SFO_MODE || 'live';
  const relayInfo = mode === 'live' ? await detectRelay() : null; const relay = !!relayInfo;
  const taxigraph = await loadTaxigraph();
  const models = {};
  for (const k of MODEL_KEYS) {
    if (window.SFO_EMBED && window.SFO_EMBED[k]) models[k] = () => b64ToBuf(window.SFO_EMBED[k]);
    else models[k] = (window.SFO_MODEL_BASE || 'data/models/') + k + (window.SFO_MODEL_EXT || '.sfom');
  }
  const app = await startApp({ mode, relay, relayInfo, taxigraph, airport: AIRPORT, details: DETAILS, buildings: BUILDINGS, stands: STANDS, paint: PAINT, pavement: PAVEMENT, snapshot: SNAPSHOT, snapshotLabel: 'Recorded · 23 Sep 10:51 PDT', metar: mode === 'snapshot' ? SNAPSHOT_METAR : null,
    models, about: aboutHtml({ mode, relay }), attrib: attribHtml({ mode }) });
  window.__sfoReady = true;
  return app;
})().catch(e => { console.error(e); window.__sfoError = String(e && e.stack || e); });
