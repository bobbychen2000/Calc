// The live G3000 PRIME pages' own stroke numerals (avionics.js / avx_pages.js): 0-9 . , - + : / degree and the dash,
// polylines and arcs on a 10-unit cap height (semi-condensed, round caps -- the DIN / Roboto-Condensed class of the
// Garmin pages), drawn with the canvas' own anti-aliased strokes.  No web font (the Artifact CSP allows none) and no
// system font: identical on every machine, so the screenshot tests stay stable.  The weight is the line width, so one
// table covers bold values and regular scale numerals.
//
// Words: every word goes through legend().  By default (owner decision 2026-10-24) it draws the text of the LEGENDS table
// -- the gauge and page labels (TRQ / ITT / NG ...), in a condensed system sans, squeezed to the stroke layout's width
// when a system font runs wider; never a brand or logo.  ?avxlabels=0 draws abstract word-length strokes at x-height
// instead (the model's no-lettering rule, which the owner lifted for the live displays).

const W = 5.2, R = W / 2, HC = 10;                 // digit width, its bowl radius, the cap height
const P = Math.PI;
// path ops (y up, origin at the baseline / left): ['M', x, y], ['L', x, y], ['E', cx, cy, rx, ry, a0, a1] (an elliptic
// arc a0 -> a1, joined to the current point), ['D', x, y] (a dot)
const GLYPHS = {
  '0': { w: W, p: [['M', 0, R + 0.4], ['L', 0, HC - R - 0.4], ['E', R, HC - R - 0.4, R, R + 0.4, P, 0], ['L', W, R + 0.4], ['E', R, R + 0.4, R, R + 0.4, 0, -P], ['Z']] },
  '1': { w: W, p: [['M', 1.5, HC - 1.6], ['L', 3.4, HC], ['L', 3.4, 0]] },
  '2': { w: W, p: [['E', R, HC - R - 0.1, R, R + 0.1, P * 0.93, -P * 0.22], ['L', 0, 0], ['L', W, 0]] },
  '3': { w: W, p: [['M', 0.4, HC - 0.4], ['L', W - 0.4, HC - 0.4], ['L', 1.9, 5.9], ['E', R, 3.05, R + 0.05, 3.05, P * 0.47, -P * 0.84]] },
  '4': { w: W, p: [['M', 3.9, 0], ['L', 3.9, HC], ['L', 0, 3.1], ['L', W + 0.2, 3.1]] },
  '5': { w: W, p: [['M', W - 0.3, HC], ['L', 0.55, HC], ['L', 0.25, 5.8], ['E', R, 3.2, R + 0.05, 3.2, P * 0.78, -P * 0.86]] },
  '6': { w: W, p: [['M', W - 0.6, HC - 0.2], ['L', 0.8, 4.6], ['E', R, 3.0, R, 3.0, P * 0.95, P * 2.95]] },
  '7': { w: W, p: [['M', 0, HC], ['L', W, HC], ['L', 1.4, 0]] },
  '8': { w: W, p: [['E', R, HC - 2.45, R - 0.25, 2.45, -P / 2, P * 1.5], ['E', R, 2.75, R + 0.05, 2.75, P / 2, P * 2.5]] },
  '9': { w: W, p: [['M', 0.6, 0.2], ['L', W - 0.8, 5.4], ['E', R, HC - 3.0, R, 3.0, -P * 0.05, P * 1.95]] },
  '.': { w: 1.2, p: [['D', 0.6, 0.55]] },
  ',': { w: 1.4, p: [['M', 0.9, 0.9], ['L', 0.3, -1.4]] },
  '-': { w: 4.4, p: [['M', 0.5, 4.8], ['L', 3.9, 4.8]] },
  '+': { w: 5.0, p: [['M', 0.3, 4.8], ['L', 4.7, 4.8], ['M', 2.5, 2.6], ['L', 2.5, 7.0]] },
  ':': { w: 1.4, p: [['D', 0.7, 1.4], ['D', 0.7, 6.4]] },
  '/': { w: 3.8, p: [['M', 0, -0.4], ['L', 3.8, HC + 0.4]] },
  '°': { w: 2.8, k: -0.9, p: [['E', 1.4, HC - 1.4, 1.3, 1.3, 0, 2 * P]] },
  ' ': { w: 2.6, p: [] },
  ' ': { w: W, p: [] },          // figure space: a digit's width
};
const GAP = 1.45;                      // between glyphs (units); scaled by the spacing option
export const NUMERALS = /^[0-9.,:+\-/°  ]*$/;

// draw a numeral string: x, y = the anchor (align 'left' | 'right' | 'center', y = the baseline), size = cap height in
// the context's units, opts {weight (line width / cap height, default 0.13), color, spacing (x the gap), halo (a dark
// outline width in units, for symbols over the SVT), log (an array: {w: widget id, s})}
export function drawNum(ctx, str, x, y, size, opts = {}) {
  str = String(str);
  const k = size / HC, gap = GAP * (opts.spacing == null ? 1 : opts.spacing);
  let w = 0;
  for (const ch of str) { const g = GLYPHS[ch] || GLYPHS[' ']; w += g.w + gap + (g.k || 0); }
  w = Math.max(0, w - gap) * k;
  const align = opts.align || 'left';
  let x0 = align === 'right' ? x - w : align === 'center' ? x - w / 2 : x;
  if (opts.log) opts.log.push({ w: opts.id || '', s: str });
  const weight = opts.weight || 0.13, lw = weight * size;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const trace = () => {
    let cx = x0;
    ctx.beginPath();
    for (const ch of str) {
      const g = GLYPHS[ch] || GLYPHS[' '];
      cx += (g.k || 0) * k;
      let prev = null;
      for (const op of g.p) {
        const X = (u) => cx + u * k, Y = (v) => y - v * k;
        // an arc joins the stroke before it only after a line (0, 3, 5, 6, 9); otherwise it starts its own sub-path
        if (op[0] === 'E' && prev !== 'M' && prev !== 'L') ctx.moveTo(X(op[1] + op[3] * Math.cos(op[5])), Y(op[2] + op[4] * Math.sin(op[5])));
        prev = op[0];
        if (op[0] === 'M') ctx.moveTo(X(op[1]), Y(op[2]));
        else if (op[0] === 'L') ctx.lineTo(X(op[1]), Y(op[2]));
        else if (op[0] === 'Z') ctx.closePath();
        else if (op[0] === 'D') { ctx.moveTo(X(op[1]) - 0.01, Y(op[2])); ctx.lineTo(X(op[1]) + 0.01, Y(op[2])); }
        else if (op[0] === 'E') {
          // y flips (canvas y down): angles negate, the sweep direction reverses
          const [, ex, ey, rx, ry, a0, a1] = op;
          ctx.ellipse(X(ex), Y(ey), rx * k, ry * k, 0, -a0, -a1, a1 > a0);
        }
      }
      cx += (g.w + gap) * k;
    }
  };
  if (opts.halo) {
    trace();
    ctx.strokeStyle = opts.haloColor || 'rgba(0,0,0,0.85)';
    ctx.lineWidth = lw + 2 * opts.halo * k * HC / 10;
    ctx.stroke();
  }
  trace();
  ctx.strokeStyle = opts.color || '#eceef0';
  ctx.lineWidth = lw;
  ctx.stroke();
  ctx.restore();
  return w;
}
export function numWidth(str, size, spacing = 1) {
  const k = size / HC, gap = GAP * spacing;
  let w = 0;
  for (const ch of String(str)) { const g = GLYPHS[ch] || GLYPHS[' ']; w += g.w + gap + (g.k || 0); }
  return Math.max(0, w - gap) * k;
}

// ------------------------------------------------------------------ legends (words)
// the texts behind the abstract strokes (shown only with AVX_LABELS): every word on the pages has an id here
export const LEGENDS = {
  trq: 'TRQ', itt: 'ITT', ng: 'NG', np: 'NP', t1: 'T1', oil: 'Oil', psi: 'PSI', degc: '°C', pct: '%', rpm: 'RPM',
  fuel: 'Fuel', qty: 'QTY', ff: 'FF', end: 'END', lb: 'LB', lbh: 'LB/H', hm: 'H:M', bat1: 'BAT1', bat2: 'BAT2', v: 'V',
  a: 'A', inertSep: 'INERT SEP', fmsElev: 'FMS ELEV', cabAlt: 'CAB ALT', dp: 'ΔP', cabRate: 'CAB Rate', ft: 'FT',
  fpm: 'FPM', ident: 'IDENT', fl: 'FL', C: 'C', M: 'M', pumpL: 'L Pump', pumpR: 'R Pump', starter: 'STARTER', ignition: 'IGNITION', idl: 'IDL', to: 'T/O',
  rev: 'REV', fea: 'FEATHER', dn: 'DN', up: 'UP', com1: 'COM1', fltId: 'FLT ID', rol: 'ROL', pit: 'PIT',
  alts: 'ALTS', hdg: 'HDG', dtk: 'DTK', crs: 'CRS', gs: 'GS', tas: 'TAS', sat: 'SAT', isa: 'ISA', kt: 'KT', ra: 'RA',
  baroMin: 'BARO MIN', inHg: 'IN', hPa: 'HPA', std: 'STD', pre: 'PRE', loc1: 'LOC1', loc2: 'LOC2', dme: 'DME', nm: 'NM',
  fms: 'FMS', rnp: 'RNP', cas: 'CAS', tmr: 'TMR', utc: 'UTC', ete: 'ETE', dis: 'DIS', wpt: 'NY240', vy: 'Y', vx: 'X',
  vr: 'R', door: 'PAX + CARGO DOOR', flapsCas: 'FLAPS', aural: 'AURAL WARN FAIL', dryMot: 'DRY MOTORING',
  starterCas: 'STARTER', toConfig: 'TAKEOFF CONFIG', fuelLow: 'FUEL LOW', dest: 'DEST', dtg: 'DTG',
  enr: 'ENR', fod: 'FOD', endr: 'ENDR', msa: 'MSA', flt: 'FLT', tod: 'TOD', map: 'Map', northUp: 'North Up',
  autoFpl: 'Auto FPL', status: 'Status', field: 'EDNY', dep: 'DEP', arr: 'ARR', origin: 'Origin', proc: 'PROC',
  activeFpl: 'Active Flight Plan', audio: 'Audio & Radios', msgs: 'Messages', stby: 'STBY', mic: 'MIC', mon: 'MON',
  com2: 'COM2', xpdr: 'XPDR1', alt: 'ALT', guard: 'Guard/EMER', takeoffData: 'Takeoff Data', elev: 'Elevation',
  oat: 'OAT', altimeter: 'Altimeter', pa: 'Pressure Alt', da: 'Density Alt', wind: 'Wind', head: 'Head', cross: 'Cross',
  rwy: 'Runway', toTrq: 'T/O Torque', flaps: 'Flaps', zfw: 'Fuel', vspeeds: 'V-Speeds', safeTaxi: 'Airport',
  trkUp: 'Heading Up', options: 'Options', nyRw: 'RW24', legs: '', climb: 'Climb', gpu: 'GPU',
  depHdr: 'Departure', destHdr: 'Destination', destF: 'EDDH', fix1: 'ROTEK', fix2: 'ODMEK', fix3: 'KPT',
  traffic: 'Traffic', terrain: 'Terrain', weather: 'Weather',
  gpuCas: 'GPU', ktR: 'KT R', ktL: 'KT L',
};

export const AVX_LABELS = { on: true };

// a word / phrase of the pages: an abstract stroke (default) or its text (AVX_LABELS.on); x, y = the left / right
// anchor at the baseline, size = the cap height; returns the width drawn
export function legend(ctx, id, x, y, size, color = '#eceef0', opts = {}) {
  const text = LEGENDS[id] != null ? LEGENDS[id] : String(id);
  const align = opts.align || 'left';
  if (AVX_LABELS.on) {
    ctx.save();
    ctx.fillStyle = color;
    ctx.font = `${opts.bold ? 'bold ' : ''}${(size * 1.38).toFixed(2)}px "Roboto Condensed", "Arial Narrow", "DejaVu Sans Condensed", Arial, sans-serif`;
    ctx.textAlign = align;
    ctx.textBaseline = 'alphabetic';
    // the room the layout gave the word (1.9 x the stroke layout's width): a wider system font is squeezed into it
    const words = text.split(/\s+/).filter(Boolean), cw = size * (opts.cw || 0.5);
    const room = 1.9 * (words.reduce((n, wd) => n + Math.max(1, wd.length) * cw, 0) + size * 0.42 * Math.max(0, words.length - 1));
    const w = Math.min(ctx.measureText(text).width, opts.maxW || Math.max(room, size * 1.2));
    ctx.fillText(text, x, y, w);
    ctx.restore();
    if (opts.log) opts.log.push({ w: opts.id || id, s: text, label: true });
    return w;
  }
  // word-length strokes at x-height: each word its own rounded bar (0.52 cap heights a character), letters' share
  const words = text.split(/\s+/).filter(Boolean);
  const cw = size * (opts.cw || 0.5), gapW = size * 0.42, h = size * (opts.h || 0.5);
  let total = 0;
  for (const wd of words) total += Math.max(1, wd.length) * cw;
  total += gapW * Math.max(0, words.length - 1);
  let cx = align === 'right' ? x - total : align === 'center' ? x - total / 2 : x;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.globalAlpha *= opts.alpha == null ? 0.85 : opts.alpha;
  ctx.lineCap = 'round';
  ctx.lineWidth = h;
  const yc = y - size * 0.36;
  for (const wd of words) {
    const L = Math.max(1, wd.length) * cw;
    ctx.beginPath();
    ctx.moveTo(cx + h / 2, yc);
    ctx.lineTo(cx + Math.max(h / 2 + 0.01, L - h / 2), yc);
    ctx.stroke();
    cx += L + gapW;
  }
  ctx.restore();
  return total;
}
