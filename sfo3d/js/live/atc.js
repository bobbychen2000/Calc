// ATC audio toggle (CLAUDE.md objective 7). Everything here comes from docs/research/atc.md (24 Sep 2026):
//  - LiveATC's KSFO feeds (mounts, titles, frequency labels) from the Internet Archive capture of
//    https://www.liveatc.net/search/?icao=ksfo of 23 Jun 2026 20:32Z (atc.md s.2.2, verified byte-identical);
//  - which frequencies the FAA publishes for SFO: Chart Supplement SW 3 Sep-29 Oct 2026 p.275, NASR 2026-09-03 FRQ.csv,
//    d-TPP 2609 plates/STARs/DPs (atc.md s.1). Every frequency carries src 'faa' (published for SFO) or 'latc'
//    (LiveATC label only, not found in any FAA publication for SFO: atc.md s.1.5) so the UI can badge it;
//  - LiveATC's terms (atc.md s.3): personal non-commercial use; no in-app playback, proxying, recording or automated
//    status checks without permission. This module therefore only LINKS OUT to LiveATC's own player page
//    https://www.liveatc.net/hlisten.php?mount=<mount>&icao=ksfo (a LiveATC web page with its ads and credit, s.3.2)
//    and never touches a stream URL.
// "Likely on this frequency" (atc.md s.4.2) is an inference from the engine's display-time phase and position: controllers
// choose their hand-off points and they are not published, so the UI always says "likely".
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const NM = 1852, DEG = Math.PI / 180;
export const LIVEATC_URL = 'https://www.liveatc.net';
export const LIST_DATE = '23 Jun 2026';           // date of the LiveATC feed list (latest archive capture, atc.md s.2.1)
export const FAA_EDITION = 'FAA Chart Supplement SW 3 Sep–29 Oct 2026, NASR 2026-09-03, d-TPP 2609';
export const playerUrl = (mount) => `${LIVEATC_URL}/hlisten.php?mount=${encodeURIComponent(mount)}&icao=ksfo`;

// frequency helpers: f MHz, lbl = LiveATC's label, src 'faa' | 'latc', note = what the FAA source says (tooltip)
const F = (f, lbl, src, note) => ({ f, lbl, src, note });
const TWR = F(120.5, 'San Francisco Tower', 'faa', 'Tower LCL/P 120.5 (Chart Supplement, NASR, every SFO plate)');
const TWR2 = F(128.65, 'Tower (secondary / backup)', 'latc', 'Not published for SFO by the FAA (atc.md s.1.5)');
const GND = F(121.8, 'San Francisco Ground', 'faa', 'Ground GND/P 121.8 (Chart Supplement, NASR, airport diagram)');
const GND2 = F(124.25, 'Ground / Gate Hold', 'faa', 'FAA publishes 124.25 as Ground (secondary, GND/S); "gate hold" is LiveATC\'s label');
const CLR = F(118.2, 'Clearance Delivery', 'faa', 'CLNC DEL / pre-taxi clearance 118.2 (Chart Supplement, NASR); most airline clearances use PDC/CPDLC');
const ATIS = F(118.85, 'KSFO Digital ATIS', 'faa', 'D-ATIS 118.85 (Chart Supplement, NASR)');
const APP_E = F(128.325, 'NORCAL App (Niles sector)', 'faa', 'NorCal Approach 128.325: APCH/P; initial contact on ALWYS, DYAMD, MODESTO, YOSEM STARs');
const APP_NW = F(133.95, 'NORCAL App (Boulder sector)', 'faa', 'NorCal Approach 133.95: APCH/S; initial contact on BDEGA, STLER, PIRAT, POINT REYES, STINS STARs');
const FIN_R1 = F(120.35, 'NORCAL App (Foster, 28R final)', 'latc', 'Not published for SFO by the FAA (atc.md s.1.5)');
const FIN_R2 = F(133.175, 'NORCAL App (Foster, 28R final)', 'latc', 'Not in NASR for California (atc.md s.1.5)');
const FIN_L = F(135.65, 'NORCAL App (Woodside, 28L final)', 'latc', 'Not published for SFO by the FAA (atc.md s.1.5)');
const DEP_NE = F(120.9, 'NORCAL Departure (NW–E)', 'faa', 'NorCal Departure 120.9 (NW–E) (Chart Supplement, NASR, DP charts)');
const DEP_SW = F(135.1, 'NORCAL Departure (SE–W)', 'faa', 'NorCal Departure 135.1 (SE–W) (Chart Supplement, NASR, DP charts)');
const F127 = F(127.0, 'NORCAL (labelled departure)', 'faa', 'The FAA lists 127.0 for SFO only as Class B NORTH (and for OAK); not as an SFO departure frequency');
const F127975 = F(127.975, 'NORCAL Departure (SW)', 'latc', 'Not in NASR for California (atc.md s.1.5)');
const RAMP = [F(127.575, 'Ramp A (East)', 'latc', 'Ramp control is not an FAA facility; no official SFO source found'), F(119.225, 'Ramp G (West)', 'latc', 'Ramp control is not an FAA facility; no official SFO source found'), F(131.0, 'Shadow Ramp', 'latc', 'Not an FAA frequency; unverified')];
const ZOA = [F(134.15, 'Oakland Center sector 35', 'faa', 'Oakland Center 134.15 is charted on the PIRAT STAR'), F(127.8, 'Oakland Center sector 40', 'latc', 'Not checked against an FAA source'), F(125.85, 'Oakland Center sector 41', 'faa', 'Oakland Center 125.85 is charted on the BDEGA and STLER STARs')];

// keys = which inferred roles a feed carries (twr, gnd, clr, ramp, fin28R, fin28L, fin, app128325, app13395, dep1209, dep1351)
export const FEEDS = [
  { mount: 'ksfo_twr', title: 'KSFO Tower', group: 'twr', def: true, freqs: [TWR, TWR2], keys: ['twr'] },
  { mount: 'ksfo_gnd_twr', title: 'KSFO Ground/Tower', group: 'twr', freqs: [GND, TWR], keys: ['twr', 'gnd'] },
  { mount: 'ksfo_twr2', title: 'KSFO Tower/Ground', group: 'twr', freqs: [GND, GND2, TWR, TWR2], keys: ['twr', 'gnd'] },
  { mount: 'ksfo_gnd', title: 'KSFO Ground', group: 'gnd', def: true, freqs: [GND], keys: ['gnd'] },
  { mount: 'ksfo_gnd2', title: 'KSFO Del/Gnd (Alt)/Twr (Alt)', group: 'clr', def: true, freqs: [CLR, GND2, TWR2], keys: ['clr'] },
  { mount: 'ksfo_app2_l', title: 'KSFO NORCAL App 28L/R', group: 'fin', def: true, freqs: [FIN_R1, FIN_R2, FIN_L], keys: ['fin', 'fin28R', 'fin28L'] },
  { mount: 'ksfo_app2', title: 'KSFO NORCAL App 28L/R + BSR/MOD STARs', group: 'fin', freqs: [FIN_R1, FIN_R2, FIN_L, APP_NW, APP_E], keys: ['fin', 'fin28R', 'fin28L', 'app128325', 'app13395'] },
  { mount: 'ksfo_app2_r', title: 'KSFO NORCAL BSR2/MOD2 Arrivals', group: 'app', def: true, freqs: [APP_NW, APP_E], keys: ['app128325', 'app13395'] },
  { mount: 'koak_dep', title: 'NORCAL Departure (KSFO/KOAK)', group: 'dep', def: true, freqs: [DEP_NE, F127, F127975, DEP_SW], keys: ['dep1209', 'dep1351'], note: 'LiveATC: southwest departures on the left channel, northeast departures on the right' },
  { mount: 'ksfo_dep1', title: 'KSFO Dep 120.9/127.0', group: 'dep', freqs: [F127, DEP_NE], keys: ['dep1209'] },
  { mount: 'ksfo_dep2', title: 'KSFO Dep 135.1', group: 'dep', freqs: [F127975, DEP_SW], keys: ['dep1351'] },
  { mount: 'ksfo_atis', title: 'KSFO D-ATIS', group: 'atis', def: true, freqs: [ATIS], keys: [] },
  { mount: 'ksfo_ramp', title: 'KSFO Ramp', group: 'ramp', def: true, freqs: RAMP, keys: ['ramp'] },
  { mount: 'zoa_sfo', title: 'ZOA Oakland Center (35/40/41)', group: 'ctr', def: true, freqs: ZOA, keys: [] },
  { mount: 'zoa_35', title: 'ZOA Oakland Center (35)', group: 'ctr', freqs: [ZOA[0]], keys: [] },
  { mount: 'ksfo_co', title: 'KSFO Company Channels', group: 'other', freqs: [], keys: [] },
];
export const FEED_BY = new Map(FEEDS.map(f => [f.mount, f]));
export const GROUPS = [
  ['twr', 'Tower', 'Runways, short final, lift-off'], ['gnd', 'Ground', 'Taxiways (movement area)'], ['clr', 'Clearance', 'At the gate before departure'],
  ['fin', 'Approach · finals', 'Final approach beyond ~6 nm'], ['app', 'Approach · arrivals', 'Arrivals before final'], ['dep', 'Departure', 'After lift-off'],
  ['atis', 'ATIS', 'Weather and runway information'], ['ramp', 'Ramp', 'Push-back and aprons'], ['ctr', 'Center', 'En-route traffic'], ['other', 'Other', ''],
];
// FAA-published approach frequencies that no LiveATC KSFO feed carries (atc.md s.2.3)
export const UNCOVERED = [
  F(128.575, 'NorCal Approach', 'faa', 'initial contact on the BIG SUR, SERFR and WWAVS STARs (arrivals from the south)'),
  F(134.5, 'NorCal Approach', 'faa', 'the approach frequency on every SFO plate; RISTI STAR'),
];

const SHORT = { twr: 'TWR', gnd: 'GND', clr: 'CLR', ramp: 'RAMP', fin: 'APP', app: 'APP', dep: 'DEP' };
const bearing = (la1, lo1, la2, lo2) => { const p1 = la1 * DEG, p2 = la2 * DEG, dl = (lo2 - lo1) * DEG; const y = Math.sin(dl) * Math.cos(p2), x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl); return ((Math.atan2(y, x) / DEG) + 360) % 360; };
const SFO_LL = [37.6188, -122.3754]; // ARP (FAA NASR), used only for bearings to route airports
const brgWorld = (x, z) => ((Math.atan2(x, -z) / DEG) + 360) % 360;   // world x east, z south
function routeAirport(tr, which) { // 'orig' | 'dest' airport record of the route relative to SFO
  const r = tr.route; if (!r || !r.codes || !r.plausible) return null; const i = r.codes.indexOf('SFO'); if (i < 0) return null;
  const code = which === 'orig' ? r.codes[i - 1] : r.codes[i + 1]; if (!code) return null;
  const a = r.airports && r.airports.find(q => q.iata === code || q.icao === code); return a && a.lat != null && a.lon != null ? a : null;
}
// arrival feeder sector from the origin airport's bearing (else the aircraft's bearing from SFO). [INF] grouping of the
// STARs by direction (atc.md s.1.3 table): east ALWYS/DYAMD/MODESTO/YOSEM 128.325, south BIG SUR/SERFR/WWAVS 128.575,
// north + west BDEGA/STLER/PIRAT/POINT REYES/STINS 133.95
function arrivalFreq(tr) {
  const o = routeAirport(tr, 'orig'); let b = o ? bearing(SFO_LL[0], SFO_LL[1], o.lat, o.lon) : null;
  if (b == null) { if (tr._atcEntry == null && tr.disp && tr.disp.valid) tr._atcEntry = brgWorld(tr.disp.x, tr.disp.z); b = tr._atcEntry; }
  if (b == null) return null;
  if (b >= 30 && b < 125) return { f: 128.325, key: 'app128325', how: o ? 'from ' + o.iata : 'from the east' };
  if (b >= 125 && b < 240) return { f: 128.575, key: 'app128575', how: o ? 'from ' + o.iata : 'from the south', uncovered: true };
  return { f: 133.95, key: 'app13395', how: o ? 'from ' + o.iata : 'from the north/west' };
}
// departure sector from the destination's bearing (Chart Supplement: 135.1 SE–W, 120.9 NW–E; in between: both)
function departureFreqs(tr) {
  const d = routeAirport(tr, 'dest'); if (!d) return [{ f: 135.1, key: 'dep1351' }, { f: 120.9, key: 'dep1209' }];
  const b = bearing(SFO_LL[0], SFO_LL[1], d.lat, d.lon);
  if (b >= 135 && b <= 270) return [{ f: 135.1, key: 'dep1351', how: 'to ' + d.iata }];
  if (b >= 315 || b <= 90) return [{ f: 120.9, key: 'dep1209', how: 'to ' + d.iata }];
  return [{ f: 135.1, key: 'dep1351', how: 'to ' + d.iata }, { f: 120.9, key: 'dep1209', how: 'to ' + d.iata }];
}

// inferred ATC position(s) of a track at display time: [{role, f, key, conf}] (empty = not on an SFO frequency)
export function atcRoles(tr, T, now = Date.now()) {
  if (!tr || tr.vehicle || tr.stale || !tr.disp || !tr.disp.valid) return [];
  const D = tr.disp, ph = tr.phase; const out = [];
  const apron = () => { const net = T && T.net; return !!(net && net.ok && net.aprons && net.aprons.length && net.inApron(D.x, D.z)); };
  switch (ph) {
    case 'gate': case 'parked': {
      const depExpected = tr.dirSFO === 'dep' || (tr.route && tr.route.codes && tr.route.codes[0] === 'SFO' && !tr.landedAt);
      if (tr.cs && tr.cs.airline && depExpected) out.push({ role: 'clr', f: 118.2, key: 'clr', conf: 'low' });
      break;
    }
    case 'pushback': case 'pushed': out.push({ role: 'ramp', f: null, key: 'ramp', conf: 'low' }); break;
    case 'taxi': case 'holding':
      if (apron()) out.push({ role: 'ramp', f: null, key: 'ramp', conf: 'low' });
      else out.push({ role: 'gnd', f: 121.8, key: 'gnd', conf: 'med' });
      break;
    case 'lineup': case 'takeoff': case 'landing': case 'goaround': out.push({ role: 'twr', f: 120.5, key: 'twr', conf: 'high' }); break;
    case 'final': {
      const d = tr.finalInfo ? -tr.finalInfo.a / NM : null; const rw = tr.finalInfo && tr.m.rwyFirm !== false ? tr.finalInfo.R.name : null;   // (a pair not yet told apart: no runway-specific final frequency)
      if (d != null && d <= 6) out.push({ role: 'twr', f: 120.5, key: 'twr', conf: 'med' });
      else out.push({ role: 'fin', f: rw === '28R' ? 133.175 : rw === '28L' ? 135.65 : null, key: rw === '28R' ? 'fin28R' : rw === '28L' ? 'fin28L' : 'fin', conf: 'low', rwy: rw });
      break;
    }
    case 'approach': { const a = arrivalFreq(tr); if (a) out.push({ role: 'app', f: a.f, key: a.key, conf: 'low', how: a.how, uncovered: a.uncovered }); break; }
    case 'departure': {
      const since = tr.liftoffAt ? (now - (T ? T.delay + (T.audioDelay || 0) : 0) - tr.liftoffAt) / 1000 : 1e9;
      const altFt = tr.info && tr.info.altBaro != null ? tr.info.altBaro : null;
      if (tr.dirSFO === 'dep' || tr.depRunway) {
        if (since < 90 || (altFt != null && altFt < 2500)) out.push({ role: 'twr', f: 120.5, key: 'twr', conf: 'low' });
        for (const d of departureFreqs(tr)) out.push({ role: 'dep', f: d.f, key: d.key, conf: 'low', how: d.how });
      }
      break;
    }
    default: break;
  }
  return out;
}
export const roleChip = (r) => r ? `${SHORT[r.role] || r.role.toUpperCase()}${r.f ? ' ' + r.f : ''}` : '';
export function onFeed(roles, feed) { if (!feed || !roles.length) return null; for (const r of roles) if (feed.keys.includes(r.key) || (r.key === 'fin' && feed.keys.includes('fin'))) return r; return null; }

// ------------------------------------------------------------------ panel
const fmtF = (f) => { const s = String(+f.toFixed(3)); return s.includes('.') ? s : s + '.0'; };
const badge = (q) => `<span class="fq ${q.src}" title="${esc(q.lbl + ' — ' + (q.note || ''))}"><b class="mono">${fmtF(q.f)}</b> <i>${q.src === 'faa' ? 'FAA' : 'LiveATC label'}</i></span>`;
// state: {tuned, delayS, snapshot, likely: Map(mount -> [{hex,name,chip}])}
export function atcHtml(S) {
  const tuned = S.tuned ? FEED_BY.get(S.tuned) : null;
  const likely = tuned ? S.likely.get(tuned.mount) || [] : [];
  const groups = GROUPS.map(([g, name, sub]) => {
    const fs = FEEDS.filter(f => f.group === g); if (!fs.length) return '';
    return `<div class="ag"><div class="agh"><b>${name}</b>${sub ? ` <span class="dim">${sub}</span>` : ''}</div>${fs.map(f => {
      const n = (S.likely.get(f.mount) || []).length; const on = S.tuned === f.mount;
      return `<div class="feed${on ? ' on' : ''}" data-mount="${f.mount}">
  <div class="fh"><span class="ft">${esc(f.title)}</span><span class="mono dim fm">${f.mount}</span></div>
  <div class="fqs">${f.freqs.map(badge).join('') || '<span class="dim">no frequencies listed</span>'}</div>
  ${f.note ? `<div class="dim small">${esc(f.note)}</div>` : ''}
  <div class="fa"><a class="listen" href="${playerUrl(f.mount)}" target="_blank" rel="noopener" data-mount="${f.mount}">Listen on LiveATC ↗</a>${f.keys.length ? `<button class="tune" data-mount="${f.mount}" aria-pressed="${on}">${on ? 'Highlighting' : 'Highlight'}${n ? ` · ${n}` : ''}</button>` : ''}</div>
  ${S.snapshot ? `<div class="url mono">${esc(playerUrl(f.mount))}</div>` : ''}
</div>`;
    }).join('')}</div>`;
  }).join('');
  return `<h3>ATC audio</h3>
<p class="credit">ATC audio: <a href="${LIVEATC_URL}" target="_blank" rel="noopener">LiveATC.net</a>. “Listen” opens LiveATC's own player in a new tab — press Play there, then come back. This app does not play, relay or record the audio (LiveATC's terms), and cannot know who is talking.</p>
${S.snapshot ? '<p class="warn">This copy shows a recorded snapshot, so live audio will not match the aircraft. If the link does not open, copy the address shown under each feed.</p>' : ''}
<div class="adl"><label for="atc-delay">Audio delay <b class="mono" id="atc-delay-v">${S.delayS} s</b></label>
<input id="atc-delay" type="range" min="0" max="30" step="1" value="${S.delayS}">
<div class="dim small">Holds the whole scene back so it lines up with the audio (LiveATC: “typically less than 20 seconds”). If you hear a clearance before the aircraft moves, increase it.</div></div>
${tuned ? `<div class="tuned"><div><b>Highlighting ${esc(tuned.title)}</b> <button class="untune">Off</button></div>
<div class="dim small">Aircraft likely on this feed now (inferred from their phase and position; controllers choose the hand-off points):</div>
<div class="lk">${likely.length ? likely.map(i => `<button class="chip" data-hex="${esc(i.hex)}">${esc(i.name)} <span class="dim">${esc(i.chip)}</span></button>`).join('') : '<span class="dim">none right now</span>'}</div></div>` : '<p class="dim small">Pick “Highlight” on a feed to mark the aircraft that are likely on it.</p>'}
${groups}
<p class="dim small">Not on any LiveATC KSFO feed: ${UNCOVERED.map(q => `<b class="mono">${fmtF(q.f)}</b> ${esc(q.lbl)} (${esc(q.note)})`).join('; ')}.</p>
<p class="dim small">Frequencies: <span class="fq faa"><i>FAA</i></span> = published for SFO (${FAA_EDITION}); <span class="fq latc"><i>LiveATC label</i></span> = LiveATC's label only, not found in any FAA publication for SFO. Feed list as of ${LIST_DATE}; feed status is shown on LiveATC.</p>`;
}
