// Detail-card replay: the app's engine (feed.js parsePayload -> traffic.js Traffic -> ground.js GroundPhysics, wired as
// js/live/app.js wires them) on a relay event sequence of the real recording, with the /api/gates payloads as the browser
// got them and the routes as the relay answered them; Date.now() is the simulated wall clock. For the hexes asked for it
// writes, every 2 s, the phase, runway / gate fields, the 3-D label and the detail-card text (js/live/ui.js
// UI.prototype.renderCard, unmodified, with traffic.planFor as app.js passes it) -- to check what the owner would read on
// the card against SFO's flight status and the raw ADS-B (review round 2 method, adapted from the reviewer's tool).
//
// usage: CANVAS_MODULE=/abs/.../@napi-rs/canvas/index.js node tools/live/card_replay.mjs DIR hex1,hex2 [--from ISO] [--until ISO] [--out F]
//   DIR: stream.jsonl.gz (tools/live/build_stream.py), gates*.jsonl.gz ({T, gates: /api/gates payload} per line), optional
//   routes.json ({callsign: relay routeset answer}). Output: DIR/cards_<hexes>.jsonl (one row per hex per 2 s; `card` only
//   when it changed) and a last line {events}.
import fs from 'fs'; import path from 'path'; import zlib from 'zlib'; import readline from 'readline'; import { fileURLToPath } from 'url';
const HERE = path.dirname(fileURLToPath(import.meta.url)); const ROOT = path.resolve(HERE, '..', '..');
const argv = process.argv.slice(2); const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const DIR = argv[0]; const HEX = new Set((argv[1] || '').split(',').filter(Boolean));
const FROM = opt('from') ? Date.parse(opt('from')) : null, UNTIL = opt('until') ? Date.parse(opt('until')) : null;
let createCanvas; for (const m of [process.env.CANVAS_MODULE, '@napi-rs/canvas'].filter(Boolean)) { try { ({ createCanvas } = await import(m)); break; } catch (e) { } }
if (!createCanvas) { console.error('no canvas module: set CANVAS_MODULE'); process.exit(1); }
let simNow = 0; const _now = Date.now; Date.now = () => simNow || _now();
globalThis.document = { createElement: () => createCanvas(1, 1), hidden: false, body: { classList: { add() { }, remove() { } } } };
globalThis.localStorage = { getItem: () => null, setItem() { }, removeItem() { } };
const imp = (p) => import(path.join(ROOT, p));
const { AIRPORT } = await imp('data/sfo_airport.js'); const { DETAILS } = await imp('data/sfo_details.js'); const { STANDS } = await imp('data/sfo_stands.js');
const { PAINT } = await imp('data/sfo_paint.js'); const { PAVEMENT } = await imp('data/sfo_pavement.js');
const { TAXIGRAPH } = await imp('data/sfo_taxigraph.js');
const { standGates, paintAirportMapReal, endZoneRects } = await imp('js/live/airport.js');
const { Traffic, phaseLabel, category } = await imp('js/live/traffic.js');
const { GroundPhysics, buildingGrid } = await imp('js/live/ground.js');
const { parsePayload } = await imp('js/live/feed.js');
const { UI } = await imp('js/live/ui.js');
let atcRoles = null; try { ({ atcRoles } = await imp('js/live/atc.js')); } catch (e) { }
const gates = standGates(STANDS);
const apt = paintAirportMapReal(AIRPORT, gates, undefined, DETAILS, { paint: PAINT, pavement: PAVEMENT, endZones: endZoneRects() });
const building = buildingGrid(AIRPORT);
const traffic = new Traffic({ gates, airport: AIRPORT, persist: false, centerlines: DETAILS.centerlines, taxigraph: TAXIGRAPH, stands: STANDS });
traffic.buildingAt = building;
const physics = new GroundPhysics({ paved: apt.paved, building, net: traffic.net });
async function readLines(f, fn) { const rl = readline.createInterface({ input: fs.createReadStream(f).pipe(zlib.createGunzip()), crlfDelay: Infinity }); for await (const l of rl) if (l) fn(JSON.parse(l)); }
const events = []; await readLines(path.join(DIR, 'stream.jsonl.gz'), (j) => events.push(j));
const plans = []; for (const f of fs.readdirSync(DIR).filter(f => /^gates.*\.jsonl\.gz$/.test(f)).sort().slice(-1)) await readLines(path.join(DIR, f), (j) => plans.push(j));
const RT = fs.existsSync(path.join(DIR, 'routes.json')) ? JSON.parse(fs.readFileSync(path.join(DIR, 'routes.json'))) : {};
const mapRoute = (x) => { if (!x) return null; const codes = (x._airport_codes_iata && x._airport_codes_iata !== 'unknown') ? x._airport_codes_iata.split('-') : null;
  return codes ? { codes, airports: (x._airports || []).map(a => ({ iata: a.iata, icao: a.icao, name: a.name, city: a.location, country: a.countryiso2, lat: a.lat ?? null, lon: a.lon ?? null })), plausible: !!x.plausible, sfo: x._sfo || null, src: x._src || null } : null; };
const card = { innerHTML: '', className: '', hidden: true };
const fakeUI = { el: { card }, sel: null };
const strip = (h) => h.replace(/<br>/g, ' | ').replace(/<\/(dd|div)>/g, ' ; ').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/\s+/g, ' ').trim();
const OUT = opt('out', path.join(DIR, 'cards_' + [...HEX].join('_').slice(0, 60) + '.jsonl')); const out = fs.createWriteStream(OUT);
const LAT = 0.08, DT = 0.1;
simNow = (events[0].T + LAT) * 1000; const tEnd = Math.min(UNTIL ?? Infinity, (events[events.length - 1].T + LAT) * 1000);
let k = 0, p = 0, nextLog = simNow, nextRoute = simNow; const lastCard = new Map();
while (simNow < tEnd) {
  while (p < plans.length && (plans[p].T + LAT) * 1000 <= simNow) { traffic.setPlan(plans[p].gates); p++; }
  while (k < events.length && (events[k].T + LAT) * 1000 <= simNow) { const P = parsePayload(events[k].p, events[k].T * 1000); traffic.ingest(P, (events[k].T + LAT) * 1000); k++; }
  traffic.update(simNow, DT); physics.resolve(traffic, DT);
  if (simNow >= nextRoute) { nextRoute += 6000; for (const t of traffic.tracks.values()) if (t.route === undefined && t.cs && t.cs.airline && t.last) { const x = RT[t.cs.callsign]; traffic.setRoute(t, x ? mapRoute(x) : null); } }
  if (simNow >= nextLog && (FROM == null || simNow >= FROM)) {
    nextLog += 2000;
    for (const tr of traffic.tracks.values()) {
      if (!HEX.has(tr.hex)) continue; const D = tr.disp;
      let c = ''; try { UI.prototype.renderCard.call(fakeUI, tr, { sfo: traffic.planFor(tr), atc: atcRoles ? atcRoles(tr, traffic, simNow) : [] }); c = strip(card.innerHTML); } catch (e) { c = 'ERR ' + e.message; }
      const row = { T: new Date(simNow).toISOString().slice(11, 21), hex: tr.hex, ph: tr.phase, mph: tr.m.phase, lbl: phaseLabel(tr, simNow), cat: category(tr), rwy: tr.m.rwy || null, arrR: tr.arrRunway || null, depR: tr.depRunway || null,
        gate: tr.gate ? tr.gate.name : null, gateSrc: tr.gateSrc || null, x: +D.x.toFixed(1), z: +D.z.toFixed(1), hdg: +(D.hdg * 180 / Math.PI).toFixed(1), g: D.ground ? 1 : 0, gs: +(D.gs || 0).toFixed(1), a: D.alpha != null ? +D.alpha.toFixed(2) : null, stale: tr.stale ? 1 : 0, dir: tr.dirSFO || null };
      if (lastCard.get(tr.hex) !== c) { row.card = c; lastCard.set(tr.hex, c); }
      out.write(JSON.stringify(row) + '\n');
    }
  } else if (simNow >= nextLog) nextLog += 2000;
  simNow += DT * 1000;
}
out.write(JSON.stringify({ events: traffic.events.filter(e => HEX.has(e.hex)) }) + '\n'); out.end();
await new Promise(r => out.on('finish', r));
console.log(OUT);
