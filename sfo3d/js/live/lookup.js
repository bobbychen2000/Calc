// Airline / aircraft-type naming and simplified airline colour schemes.
// Names: Virtual Radar Server standing data (github.com/vradarserver/standing-data), with a few type-name corrections.
// Liveries are simplified colour families only (no logos, artwork or lettering).
import { AIRLINES, TYPE_NAMES } from '../../data/lookup.js';

// ICAO type designators whose standing-data model name is a military or licence variant; use the common civil name
const TYPE_FIX = {
  GLF4: 'Gulfstream|IV / G400 / G450', GLF5: 'Gulfstream|V / G550', GLF6: 'Gulfstream|G650', C172: 'Cessna|172 Skyhawk', C182: 'Cessna|182 Skylane',
  PC12: 'Pilatus|PC-12', AT76: 'ATR|72-600', AT75: 'ATR|72-500', EC35: 'Airbus Helicopters|H135', EC45: 'Airbus Helicopters|H145', B06: 'Bell|206',
  AS50: 'Airbus Helicopters|H125 / AS350', R44: 'Robinson|R44', SR22: 'Cirrus|SR22', C208: 'Cessna|208 Caravan', BE20: 'Beechcraft|King Air 200',
  C130: 'Lockheed|C-130 Hercules', C17: 'Boeing|C-17 Globemaster III', K35R: 'Boeing|KC-135', MD11: 'McDonnell Douglas|MD-11',
};
const AIRLINE_FIX = { NKS: 'Spirit Airlines|NK', LXJ: 'Flexjet|' };

export function airlineInfo(icao) {
  const s = AIRLINE_FIX[icao] || AIRLINES[icao]; if (!s) return null;
  const [name, iata] = s.split('|'); return { icao, name, iata: iata || null };
}
// callsign "UAL1234" -> airline + flight number "UA 1234"
export function parseCallsign(cs) {
  if (!cs) return { callsign: null, airline: null, number: null, display: null };
  cs = cs.trim().toUpperCase();
  const m = /^([A-Z]{3})(\d[0-9A-Z]{0,4})$/.exec(cs);
  if (m) {
    const al = airlineInfo(m[1]);
    if (al) { const num = m[2].replace(/^0+(?=\d)/, ''); return { callsign: cs, airline: al, number: num, display: (al.iata ? al.iata + ' ' : al.icao + ' ') + num }; }
  }
  return { callsign: cs, airline: null, number: null, display: cs };
}
export function typeInfo(icao, desc) {
  const s = (icao && (TYPE_FIX[icao] || TYPE_NAMES[icao])) || null;
  if (!s) return { icao: icao || null, maker: null, model: null, full: desc ? titleCase(desc) : (icao || 'Unknown type'), engines: null, species: null, wake: null };
  const [maker, model, engines, engType, species, wake] = s.split('|');
  const short = maker.replace(/ (Aerospace|Aircraft|Aviation|Helicopters|Industries|Corporation|Company)$/, '');
  return { icao, maker, model, full: (short + ' ' + model).trim(), engines: +engines || null, engType, species, wake };
}
function titleCase(s) { return s.toLowerCase().replace(/\b([a-z])/g, (m, c) => c.toUpperCase()).replace(/\b(Ii|Iii|Iv)\b/g, x => x.toUpperCase()); }

// ------------------------------------------------------------------ colour families
const W = [0.94, 0.94, 0.95], NAVY = [0.07, 0.12, 0.3], GRAY = [0.6, 0.62, 0.66];
const L = (top, belly, tail, tail2, eng, bellyLine = -5, stripe = [0, 0, 0, 0]) => ({ top, belly, tail, tail2, eng, stripe, bellyLine, tailStyle: 1 });
export const NEUTRAL = L(W, W, [0.86, 0.87, 0.89], GRAY, [0.85, 0.86, 0.88]);
const FAM = {
  UAL: L(W, [0.16, 0.3, 0.6], [0.07, 0.14, 0.34], [0.16, 0.3, 0.6], [0.07, 0.14, 0.34], -0.35),
  ASA: L(W, W, [0.05, 0.15, 0.32], [0.1, 0.55, 0.6], [0.05, 0.15, 0.32], -5, [0.1, 0.55, 0.6, 1]),
  SWA: L([0.18, 0.3, 0.64], W, [0.18, 0.3, 0.64], [0.85, 0.15, 0.2], [0.18, 0.3, 0.64], 0.1),
  AAL: L([0.76, 0.78, 0.8], [0.76, 0.78, 0.8], [0.15, 0.3, 0.6], [0.8, 0.12, 0.15], [0.76, 0.78, 0.8]),
  DAL: L(W, [0.08, 0.12, 0.28], [0.08, 0.12, 0.28], [0.75, 0.1, 0.15], [0.08, 0.12, 0.28], -0.25),
  JBU: L(W, W, [0.1, 0.2, 0.5], [0.2, 0.45, 0.8], [0.1, 0.2, 0.5]),
  ACA: L(W, [0.25, 0.26, 0.28], [0.08, 0.08, 0.09], [0.75, 0.1, 0.1], W, -0.5),
  BAW: L(W, [0.09, 0.13, 0.32], [0.1, 0.16, 0.38], [0.78, 0.1, 0.14], GRAY, -0.3),
  DLH: L(W, W, [0.05, 0.1, 0.26], W, [0.05, 0.1, 0.26]),
  AFR: L(W, W, W, [0.1, 0.2, 0.55], W, -5, [0.1, 0.2, 0.55, 1]),
  KLM: L([0.0, 0.6, 0.85], W, [0.0, 0.6, 0.85], W, [0.0, 0.5, 0.78], -0.05),
  UAE: L(W, W, W, [0.75, 0.08, 0.1], W),
  QTR: L([0.9, 0.9, 0.9], [0.9, 0.9, 0.9], [0.38, 0.05, 0.2], W, [0.9, 0.9, 0.9]),
  SIA: L(W, W, [0.07, 0.16, 0.36], [0.9, 0.7, 0.2], W, -5, [0.07, 0.16, 0.36, 1]),
  CPA: L(W, [0.7, 0.72, 0.74], [0.1, 0.4, 0.35], W, W, -0.6),
  EVA: L(W, [0.55, 0.6, 0.55], [0.12, 0.36, 0.26], [0.95, 0.55, 0.1], [0.12, 0.36, 0.26], -0.55),
  CAL: L(W, W, [0.72, 0.32, 0.46], W, W),
  JAL: L(W, W, W, [0.8, 0.08, 0.1], W),
  ANA: L(W, [0.85, 0.86, 0.88], W, [0.05, 0.25, 0.55], [0.05, 0.25, 0.55], -0.5, [0.05, 0.25, 0.55, 1]),
  KAL: L([0.58, 0.75, 0.88], [0.7, 0.72, 0.75], W, [0.1, 0.25, 0.6], [0.58, 0.75, 0.88], -0.3),
  AAR: L(W, [0.62, 0.62, 0.66], [0.6, 0.6, 0.64], [0.85, 0.25, 0.2], W, -0.4),
  QFA: L(W, W, [0.82, 0.08, 0.1], W, W),
  ANZ: L(W, W, [0.06, 0.06, 0.07], W, [0.06, 0.06, 0.07]),
  WJA: L(W, W, [0.0, 0.33, 0.42], [0.1, 0.2, 0.4], W),
  VIR: L([0.88, 0.88, 0.9], [0.88, 0.88, 0.9], [0.78, 0.07, 0.15], [0.35, 0.1, 0.4], [0.78, 0.07, 0.15]),
  EIN: L(W, W, [0.0, 0.45, 0.4], W, W),
  THY: L(W, W, [0.8, 0.05, 0.1], W, W),
  AIC: L(W, W, [0.7, 0.1, 0.25], [0.85, 0.65, 0.25], W),
  PAL: L(W, W, [0.1, 0.2, 0.5], [0.85, 0.15, 0.15], W),
  CSN: L(W, W, [0.2, 0.45, 0.8], [0.85, 0.15, 0.2], W),
  FJI: L(W, W, [0.25, 0.18, 0.12], W, W),
  HAL: L(W, W, [0.35, 0.15, 0.45], [0.85, 0.35, 0.55], W),
  FFT: L(W, [0.1, 0.45, 0.25], [0.1, 0.45, 0.25], W, W, -0.4),
  NKS: L([0.95, 0.85, 0.12], [0.95, 0.85, 0.12], [0.95, 0.85, 0.12], [0.1, 0.1, 0.1], [0.95, 0.85, 0.12]),
  SCX: L(W, NAVY, [0.95, 0.5, 0.1], NAVY, W, -0.4),
  VOI: L(W, W, [0.45, 0.15, 0.5], [0.2, 0.7, 0.4], W),
  VIV: L(W, W, [0.35, 0.7, 0.2], W, W),
  AMX: L(W, [0.85, 0.86, 0.88], [0.06, 0.12, 0.25], W, W, -0.5),
  AVA: L([0.8, 0.05, 0.1], [0.8, 0.05, 0.1], [0.8, 0.05, 0.1], W, [0.8, 0.05, 0.1]),
  CMP: L(W, W, [0.07, 0.14, 0.36], [0.8, 0.65, 0.3], W),
  FDX: L(W, [0.55, 0.57, 0.6], [0.3, 0.1, 0.45], [0.95, 0.45, 0.1], W, -0.45),
  UPS: L([0.88, 0.88, 0.88], [0.3, 0.2, 0.12], [0.3, 0.2, 0.12], [0.85, 0.65, 0.2], [0.3, 0.2, 0.12], -0.2),
  GTI: L(W, W, [0.1, 0.2, 0.45], W, W),
  MXY: L(W, NAVY, NAVY, [0.3, 0.6, 0.85], W, -0.4),
  SWR: L(W, W, [0.82, 0.05, 0.1], W, W),
  IBE: L(W, W, [0.8, 0.1, 0.15], [0.95, 0.75, 0.1], W),
  AUA: L(W, W, [0.82, 0.05, 0.1], W, W),
  SAS: L(W, W, [0.07, 0.12, 0.35], W, [0.07, 0.12, 0.35]),
};
const SAME = { QXE: 'ASA', GJS: 'UAL', ASH: 'UAL', ENY: 'AAL', PDT: 'AAL', JIA: 'AAL' };
export function liveryForAirline(icao) { if (!icao) return NEUTRAL; return FAM[SAME[icao] || icao] || NEUTRAL; }
