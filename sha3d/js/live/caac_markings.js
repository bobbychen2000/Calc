// sha3d CAAC marking / sign parameter table (new; no sfo3d code). ONE table for the ground shader (runway paint,
// js/live/markings.js) and the decal / sign builders (js/live/caac_decals.js, js/live/caac_signs.js).
//
// Source: MH 5001-2021 《民用机场飞行区技术标准》 (CAAC, in force 2021-12-01; 3rd printing with the 2024-01-16 errata) and its
// amendment 4 (2025-06-21), read in the local copy refs/cache/standards/caac_mh5001_2021/ (not redistributed; short
// numeric parameters with clause numbers only - docs/phase1/standards_refs.md §1.2). Every entry is
//   [value, 'clause'] for a value printed in the standard (obs), or
//   [value, 'inf: reason'] for a choice inside a printed range, a value not printed, or a rendering default.
// ZSSS facts (runway widths, displaced thresholds, blast pads, PAPI distances) are NOT here: they come from the data
// (data/sha_airport.js runways[].aip_facts, "AIP (mirror)").
// No FAA AC 150/5340-1 value is used anywhere in sha3d (the sfo3d FAA constants - 16 x 5.75 ft stripes, 1,020 ft aiming
// point, 3-2-2-1-1 TDZ bars, 60 ft numerals - are not forked).

const P = (v, src) => [v, src];
export const val = (e) => (Array.isArray(e) ? e[0] : e);
export const src = (e) => (Array.isArray(e) ? e[1] : '');

export const CAAC = {
  doc: 'MH 5001-2021 (CAAC) + amendment 4 (2025-06-21)',
  // ---------------------------------------------------------------------------------------------------- colours
  // App. I gives chromaticity boundaries; these are linear rendering albedos chosen inside them [inf].
  colour: {
    runway: P('white', '6.2.1-3'), taxiway: P('yellow', '6.2.1-4'), border: P('black', '6.2.1-7 (light pavement)'),
    standSafety: P('red', '6.2.17-1'), otherApron: P('white', '6.2.17-1'), mandatory: P('red background, white characters', '6.2.12-5'),
    location: P('black background, yellow characters', '6.2.13-3'), direction: P('yellow background, black characters', '6.2.13-3'),
    preThreshold: P('yellow', '6.2.25'),
  },
  albedo: {   // linear albedo (ground shader / decal shader) [inf: rendering defaults; paint chromaticity per App. I not modelled]
    white: P([0.70, 0.70, 0.68], 'inf'), yellow: P([0.80, 0.52, 0.035], 'inf'), red: P([0.46, 0.035, 0.03], 'inf'),
    black: P([0.022, 0.022, 0.024], 'inf'), rubber: P([0.035, 0.034, 0.033], 'inf'),
  },
  // ---------------------------------------------------------------------------------------------------- runway
  runway: {
    // threshold stripes: count by runway width; from 6 m inside the threshold; >= 30 m (preferably 45 m) long; ~1.8 m wide,
    // ~1.8 m apart, double centre gap; out to <= 3 m from the edge or 27 m from the CL
    stripeCount: P({ 18: 4, 23: 6, 30: 8, 45: 12, 60: 16 }, '6.2.4 table 6.2.4-1'),
    stripeStart: P(6, '6.2.4-2'),
    stripeLen: P(45, '6.2.4-3 ("宜为 45 m")'),
    stripeW: P(1.8, '6.2.4-3 (约 1.8 m)'),
    stripeEdgeClear: P(3.0, '6.2.4-3 (<= 3 m from the edge, or 27 m from the CL)'),
    stripeMaxFromCL: P(27, '6.2.4-3'),
    // the gap is fitted so the outer stripe ends exactly 3 m from the edge: 45 m -> 1.45 m, 60 m -> 1.575 m (the text says
    // "约 1.8 m"; the 3 m rule decides here) [inf]
    stripeGapRule: P('fit: outer stripe edge 3 m from the pavement edge', 'inf: standards_refs.md §1.3 (45 m -> 1.45 m, 60 m -> 1.575 m)'),
    // displaced threshold (permanent, fig. 6.2.4 (b)): transverse bar >= 1.8 m; centreline arrows before it
    dthrBarW: P(1.8, '6.2.4-4'),
    arrowFirstTipBeforeThr: P(20, 'fig. 6.2.4 (b)'),
    arrowLen: P(30, 'fig. 6.2.4 (b)'),
    arrowGap: P(20, 'inf: fig. 6.2.4 (b) shows arrows L >= gaps L\'; centreline rhythm 30 / 20 m'),
    arrowHeadH: P({ 18: 10.2, 23: 10.2, 30: 12, 45: 12, 60: 12 }, '6.2.4 table 6.2.4-2 (h)'),
    arrowLegW: P(1 / 12, '6.2.4 fig. 6.2.4 (>= h/12, as a fraction of h)'),
    arrowHeadHalfBase: P(1 / 8, 'inf: fraction of h (the figure is not dimensioned)'),
    arrowEndMargin: P(3, 'inf: an arrow is drawn only if its tail is >= 3 m inside the pavement'),
    // designation (fig. 6.2.2-1 (b), parallel runways): stripes; 12 m; letter 9 m; 6 m; number 9 m; 12 m; centreline
    desigGapAfterStripes: P(12, 'fig. 6.2.2-1 (b)'),
    desigH: P(9, '6.2.2-4 (>= 9 m, may scale to 2x; ZSSS size unknown: 9 m inf)'),
    desigLetterNumberGap: P(6, 'fig. 6.2.2-1 (b)'),
    desigGapToCL: P(12, 'fig. 6.2.2-1 (a)/(b)'),
    digitClearGap: P(2.2, 'fig. 6.2.2-2 note (>= 2.2 m; 3.8 m in "11")'),
    // centreline: stripe + gap 50-75 m, stripe >= max(gap, 30 m); width >= 0.45 m for CAT I precision runways
    clStripe: P(30, 'inf: 6.2.3-3 range (stripe + gap 50-75 m, stripe >= max(gap, 30 m))'),
    clGap: P(20, 'inf: 6.2.3-3 range'),
    clW: P(0.45, '6.2.3-4 (CAT I; ZSSS PALS CAT I per AIP (mirror))'),
    // runway edge: >= 0.9 m (runway >= 30 m), outer edge at the pavement edge; interrupted at taxiway / runway junctions
    edgeW: P(0.9, '6.2.7-5'),
    edgeInterruptAtTaxiways: P(true, '6.2.7-2'),
    // aiming point: start >= 400 m for LDA >= 2400 m, or the visual approach slope origin where a PAPI exists; 45-60 m
    // long, 6-10 m wide, inner gap 18-22.5 m
    aimStartNoPapi: P({ 800: 150, 1200: 250, 2400: 300, Infinity: 400 }, '6.2.5 table 6.2.5'),
    aimAtPapi: P(true, '6.2.5-2 (start = visual approach slope origin; PAPI position used as that origin: inf)'),
    aimLen: P(60, 'inf: 6.2.5 table range 45-60 m'),
    aimW: P(9, 'inf: 6.2.5 table range 6-10 m'),
    aimGap: P({ 45: 18, 60: 22.5 }, 'inf: 6.2.5 table range 18-22.5 m (min for 45 m, max for 60 m)'),
    // touchdown zone: pairs by LDA / distance between thresholds (>= 2400 m: 6); every 150 m from 150 m; pairs within
    // 50 m of the aiming point omitted; pattern A bars >= 22.5 x 3 m (pattern B 22.5 x 1.8 with 1.5 m gaps)
    tdzPairs: P({ 900: 1, 1200: 2, 1500: 3, 2400: 4, Infinity: 6 }, '6.2.6 table 6.2.6'),
    tdzPitch: P(150, '6.2.6-3'),
    tdzOmitNearAim: P(50, '6.2.6-3'),
    tdzPattern: P('A', 'inf: pattern A or B unknown at ZSSS (6.2.6-3 allows both)'),
    tdzLen: P(22.5, '6.2.6-3 (pattern A >= 22.5 m)'),
    tdzW: P(3, '6.2.6-3 (pattern A >= 3 m)'),
    // pre-threshold pavement >= 60 m unfit for aircraft: yellow ">" chevrons, line >= 0.9 m, 45 deg, apex towards the
    // runway, X = W, apexes 30 m apart; the nearest chevron's legs start X/4 before the threshold line (fig. 6.2.25)
    chevronMinLen: P(60, '6.2.25'), chevronW: P(0.9, '6.2.25'), chevronPitch: P(30, 'fig. 6.2.25'),
    chevronAngle: P(45, 'fig. 6.2.25'), chevronLastLegFromThr: P(1 / 4, 'fig. 6.2.25 (X/4)'),
    rubber: P(true, 'inf: tyre rubber deposits around the touchdown zone (rendering)'),
  },
  // runway designation numerals and letters, fig. 6.2.2-2 (dimensions in metres). Polygons were drawn by us from the
  // printed dimensions; vertices the figure does not dimension (diagonal ends of "2", the waist of "8", the "R" leg) were
  // read off the figure at 400 dpi to +-0.1 m [inf]. x to the right as read, y up (away from the threshold), origin at
  // the glyph's lower-left; holes as extra rings (even-odd). "6" and "9" are 9.5 m tall (the tail), as drawn.
  glyphs: {
    src: 'fig. 6.2.2-2 (forms and dimensions); our polygons',
    width: { '1': 1.1, '4': 3.9, '7': 3.5 },   // others 3.0 (fig. 6.2.2-2)
    rings: {
      '0': [[[0, 0], [3, 0], [3, 9], [0, 9]], [[0.8, 1.5], [2.2, 1.5], [2.2, 7.5], [0.8, 7.5]]],
      '1': [[[0.3, 0], [1.1, 0], [1.1, 9], [0.3, 9], [0, 8.7], [0, 7.5], [0.3, 7.5]]],
      '2': [[[0, 0], [3, 0], [3, 1.5], [0.8, 1.5], [0.8, 2.4], [3, 5.9], [3, 9], [0, 9], [0, 6.6], [0.8, 6.6], [0.8, 7.5], [2.2, 7.5], [2.2, 6.6], [0, 2.6]]],
      '3': [[[0, 0], [3, 0], [3, 4.3], [2.2, 5.4], [3, 6.5], [3, 9], [0, 9], [0, 7.5], [2.2, 7.5], [2.2, 6.6], [0.8, 5.4], [2.2, 4.0], [2.2, 1.5], [0, 1.5]]],
      '4': [[[2.3, 0], [3.1, 0], [3.1, 1.9], [3.9, 1.9], [3.9, 3.4], [3.1, 3.4], [3.1, 6.3], [2.3, 6.3], [2.3, 3.4], [1.15, 3.4], [2.2, 9], [1.4, 9], [0, 1.9], [2.3, 1.9]]],
      '5': [[[0, 0], [3, 0], [3, 6.3], [0.8, 6.3], [0.8, 7.5], [3, 7.5], [3, 9], [0, 9], [0, 4.8], [2.2, 4.8], [2.2, 1.5], [0, 1.5]]],
      '6': [[[0, 0], [3, 0], [3, 5.5], [0.8, 5.5], [0.8, 7.23], [2.2, 8.5], [2.2, 9.5], [0, 7.5]], [[0.8, 1.5], [2.2, 1.5], [2.2, 4.0], [0.8, 4.0]]],
      '7': [[[0, 9], [3.5, 9], [1.1, 0], [0.3, 0], [2.3, 7.5], [0, 7.5]]],
      '8': [[[0, 0], [3, 0], [3, 4.4], [2.6, 5.2], [3, 6.0], [3, 9], [0, 9], [0, 6.0], [0.4, 5.2], [0, 4.4]], [[0.8, 1.5], [2.2, 1.5], [2.2, 4.4], [0.8, 4.4]], [[0.8, 6.0], [2.2, 6.0], [2.2, 7.5], [0.8, 7.5]]],
      // "9" = "6" turned through 180 deg (fig. 6.2.2-2 draws them so: 9.5 m, the tail 0.5 m below the line)
      '9': null,
      L: [[[0, 0], [3, 0], [3, 1.5], [0.8, 1.5], [0.8, 9], [0, 9]]],
      R: [[[0, 0], [0.8, 0], [0.8, 3.7], [1.5, 3.7], [2.2, 0], [3, 0], [2.3, 3.7], [3, 3.7], [3, 9], [0, 9]], [[0.8, 5.2], [2.2, 5.2], [2.2, 7.5], [0.8, 7.5]]],
      C: [[[0, 0], [3, 0], [3, 2.1], [2.2, 2.1], [2.2, 1.5], [0.8, 1.5], [0.8, 7.5], [2.2, 7.5], [2.2, 6.9], [3, 6.9], [3, 9], [0, 9]]],
    },
    order: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'L', 'R', 'C'],   // atlas cell index
  },
  // ---------------------------------------------------------------------------------------------------- taxiways
  taxiway: {
    clW: P(0.15, '6.2.8-2 (>= 0.15 m, continuous yellow)'),
    clBorder: P(0.05, '6.2.8-2 (black edges >= 0.05 m on light pavement; interrupted on the runway, fig. 6.2.8-2 note)'),
    clClearOfHold: P(0.9, '6.2.8-3 (0.9 m clear of holding / intermediate holding / runway CL markings)'),
    clRunwayOffset: P(0.9, '6.2.8-5 (exit CL parallel to the runway CL, 0.9 m clear)'),
    clRunwayParallel: P(60, '6.2.8-5 (>= 60 m beyond the tangent point, code 3-4)'),
    edgeLineW: P(0.15, '6.2.14-3'), edgeLineGap: P(0.15, '6.2.14-3'),
    edgeClearOfHold: P(0.9, 'amd. 4, 6.2.14-4'),
    // enhanced centreline: side dashes 0.15 m wide, 3 m long, 1 m gaps, 0.15 m clear of the CL, over 47 m from
    // holding position A, at every taxiway / runway junction except exit-only taxiways
    enhDashW: P(0.15, '6.2.8-6 3)'), enhDash: P(3, 'fig. 6.2.8-4 (a)'), enhGap: P(1, 'fig. 6.2.8-4 (a)'),
    enhClear: P(0.15, 'fig. 6.2.8-4 (a)'), enhLen: P(47, '6.2.8-6 3)'), enhWhere: P('every runway entry except exit-only', 'amd. 4, 6.2.8-6 2)'),
    enhAtZSSS: P(true, 'inf: presence at ZSSS not observed; drawn because amd. 4 makes it mandatory'),
  },
  hold: {
    // pattern A: 4 lines 0.3 m with 0.3 m gaps (2.1 m); the two on the runway side dashed 0.9 / 0.9 m; 0.1 m black
    // surround on light pavement; across the taxiway pavement plus shoulders; perpendicular to the CL
    aLineW: P(0.3, 'fig. 6.2.10-1'), aGap: P(0.3, 'fig. 6.2.10-1'), aDash: P(0.9, 'fig. 6.2.10-1'), aDashGap: P(0.9, 'fig. 6.2.10-1'),
    border: P(0.1, '6.2.10-6'), acrossShoulders: P(true, 'amd. 4, 6.2.10-1'),
    // pattern B (CAT II/III): two 0.3 m lines 1.5 m apart with paired 0.3 m rungs every 3 m - ZSSS is CAT I (AIP (mirror)
    // PALS CAT I), and only one runway-holding position per taxiway: pattern B is not used (6.2.10-3)
    bUsed: P(false, '6.2.10-3 (CAT I, single holding position -> pattern A)'),
    // intermediate holding position: single dashed line 0.3 m, 0.9 / 0.9 m, black surround on light pavement
    iLineW: P(0.3, 'fig. 6.2.11-1'), iDash: P(0.9, 'fig. 6.2.11-1'), iDashGap: P(0.9, 'fig. 6.2.11-1'),
    // classification of the OSM holding_position nodes (no designators in OSM): <= 120 m from a runway CL = runway-holding
    // position (CAT I code 4: 90 m, code F 100 m, 4.12.6); farther (182-310 m, on the parallel taxiways C / D / M4 / M6)
    // = intermediate holding position
    runwayHoldMaxFromCL: P(120, 'inf: classification rule (4.12.6: 90 / 100 m)'),
    halfWidthCap: P(22, 'inf: taxiway 23 m + shoulders to 44 m (data surfaces)'),
  },
  mandatoryMarking: {
    // red background, white characters (runway designation as seen); characters 4 m (code C-F); background >= 0.5 m
    // beyond the characters; >= 1 m from the CL marking and the holding marking; on taxiways >= 23 m one each side of
    // the CL, on the holding side
    charH: P(4, '6.2.12-7'), margin: P(0.5, '6.2.12-8'), clearOfCL: P(1, '6.2.12-3'), clearOfHold: P(1, '6.2.12-3'),
    twoPlatesFromW: P(23, '6.2.12-3'),
    where: P('pattern-A runway holds, not on exit-only taxiways', 'inf: 6.2.12-2 recommends them for runway-incursion prevention'),
  },
  infoMarking: { charH: P(4, '6.2.13-5'), arrowLen: P(2, '6.2.13-5') },
  // marking characters (fig. 6.2.12-3): tall condensed sans; we draw them with a condensed system font [inf: shapes
  // approximate fig. 6.2.12-3; width about 0.33 x height as measured on the figure]
  markChars: { widthRatio: P(0.33, 'inf: fig. 6.2.12-3 (characters about 0.28-0.35 x height, incl. spacing); two "18L-36R" plates then fit a 23 m taxiway'), font: P('bold condensed sans', 'inf') },
  // ---------------------------------------------------------------------------------------------------- stands, apron
  stand: {
    leadW: P(0.15, '6.2.16-5 (>= 0.15 m)'), leadBorder: P(0.05, '6.2.16-5 (>= 0.05 m black on light pavement)'),
    stopLen: P(6, 'inf: 6.2.16-7 says >= 2 m; 6 m drawn'), stopW: P(0.3, 'inf: 6.2.16-7 says >= 0.15 m'),
    alignBeyondStop: P(4, 'inf: alignment line continued past the stop line'),
    // stand number: yellow pentagon, black characters A = 4 m, plate B = 5 m + point E = 2 m, black border D = 0.1 m;
    // "a short distance after the start of the lead-in"; plate axis 45-75 deg to the taxilane; 1 m clear of the line
    numCharH: P(4, 'fig. 6.2.16-2 (A)'), numPlateH: P(5, 'fig. 6.2.16-2 (B)'), numPoint: P(2, 'fig. 6.2.16-2 (E)'),
    numBorder: P(0.1, 'fig. 6.2.16-2 (D)'), numClear: P(1, 'fig. 6.2.16-3 / -4 (1 m)'),
    numAlong: P(18, 'inf: plate centre 18 m along the lead-in from its start'),
    // stand safety line (red, >= 0.1 m) around the parked aircraft at clearance B (table 4.13.5); dashed with 45 deg
    // hatching (0.1 m lines, 2 m apart) where adjacent stands overlap
    safetyW: P(0.1, '6.2.18-4'), hatchW: P(0.1, '6.2.18-5'), hatchGap: P(2, '6.2.18-5'), safetyDash: P([1.0, 0.5], 'fig. 6.2.18-1 (b): 1.0 m dashes, 0.5 m gaps'),
    clearB: P({ A: 3, B: 3, C: 4.5, D: 7.5, E: 7.5, F: 7.5 }, 'table 4.13.5 (aircraft to adjacent aircraft / objects)'),
    noseE: P(3.75, 'inf: table 4.13.5 note a (nose-in with visual docking guidance: may reduce to 3.75 m); used at every stand'),
    // bridge activity area: red outline 0.1-0.15 m, 45 deg hatching 2 m apart (6.2.17, 6.2.20)
    bridgeOutlineW: P(0.12, '6.2.20 (0.1-0.15 m)'), bridgeHatchGap: P(2, '6.2.20'), bridgeAreaHalfW: P(4.5, 'inf'),
    // equipment parking areas: white outline 0.15 m, text "设备区" in white 黑体
    equipW: P(0.15, 'inf: 6.2.20 (white lines)'), equipText: P('设备区', '6.2.20-1 (white, 黑体)'),
    pushDash: P([1, 1], '6.2.16-9 (white dashed 0.15 m, 1 m / 1 m; only where operations need it: not drawn)'),
    classLetter: P({ B: 'C', C: 'C', CL: 'D', D: 'D', E: 'E', EL: 'E', F: 'F' }, 'inf: sfo3d stand class -> ICAO code letter'),
  },
  // ---------------------------------------------------------------------------------------------------- signs (ch. 8, app. H)
  sign: {
    mandFaceH: P(0.6, 'table 8.2.6 (code 3-4: 400 mm text on a 600 mm face)'), mandTextH: P(0.4, 'table 8.2.6'),
    infoFaceH: P(0.45, 'table 8.2.6 (300 mm text on 450 mm)'), infoTextH: P(0.3, 'table 8.2.6'),
    mountMax: P(1.1, 'table 8.2.6 (<= 1,100 mm for 600 mm faces)'),
    twySetback: P([11, 21], 'table 8.2.6 (from the taxiway pavement edge, code 3-4)'),
    rwySetback: P([8, 15], 'table 8.2.6 (from the runway pavement edge)'),
    setbackUsed: P(11, 'inf: the minimum of the range'),
    mandColours: P(['#c4161c', '#ffffff'], '8.3.2 (red, white; colours per app. I: inf sRGB)'),
    locColours: P(['#111111', '#f6c400'], '8.4.2-2 (black, yellow; yellow border when alone)'),
    dirColours: P(['#f6c400', '#111111'], '8.4.3-2 (yellow, black)'),
    holdSigns: P('runway designation sign at both ends of holding A, location sign outboard', '8.3.3, 8.3.5, 8.4.2-3 1)'),
    designationOrder: P('as seen from the sign side', '8.3.6'),
    dirLeftSide: P(true, '8.4.3-12 (left side of the taxiway)'),
    dirBeforeJunction: P(60, '8.4.3-10 (>= 60 m before the intersecting CL, code 3-4)'),
    dividerFrac: P(0.7, 'H.0.12 (divider about 0.7 x stroke)'),
    latinOnly: P(true, '8.4.1 (taxi-guidance signs: Latin letters and digits)'),
    texts: P('taxiway refs from OSM where present; otherwise the sign is not drawn', 'inf'),
  },
};

// ------------------------------------------------------------------------------------------------ derived helpers
CAAC.glyphs.rings['9'] = CAAC.glyphs.rings['6'].map(r => r.map(([x, y]) => [3 - x, 9 - y]));
export const glyphWidth = (ch) => CAAC.glyphs.width[ch] || 3.0;

/** threshold stripe layout for a runway width W: {n per side, gap (m), w, len, start} (6.2.4 + the inf fit rule) */
export function stripeLayout(W) {
  const R = CAAC.runway; const tab = val(R.stripeCount);
  const keys = Object.keys(tab).map(Number).sort((a, b) => a - b);
  let n = tab[keys[0]]; for (const k of keys) if (W >= k - 0.5) n = tab[k];
  const per = n / 2, w = val(R.stripeW);
  const lim = Math.min(W / 2 - val(R.stripeEdgeClear), val(R.stripeMaxFromCL));
  const gap = (lim - per * w) / per;   // (per - 1) gaps between stripes + half of the doubled centre gap
  return { n, per, gap, w, len: val(R.stripeLen), start: val(R.stripeStart) };
}
/** number of TDZ pairs for a landing distance / distance between thresholds (table 6.2.6) */
export function tdzPairCount(dist) {
  const tab = val(CAAC.runway.tdzPairs); for (const k of Object.keys(tab).map(Number).sort((a, b) => a - b)) if (dist < k) return tab[k]; return 6;
}
/** TDZ pair positions (m from the threshold) painted for an aiming point starting at aim (6.2.6-3) */
export function tdzPositions(dist, aim) {
  const R = CAAC.runway; const n = tdzPairCount(dist); const out = [];
  const a0 = aim, a1 = aim + val(R.aimLen), om = val(R.tdzOmitNearAim), L = val(R.tdzLen);
  for (let k = 1; k <= n; k++) {
    const x0 = val(R.tdzPitch) * k, x1 = x0 + L;
    const gap = x1 < a0 ? a0 - x1 : x0 > a1 ? x0 - a1 : 0;   // clear distance to the aiming point (0 = overlap)
    out.push({ x0, keep: gap > om });
  }
  return out;
}
/** aiming point start without a PAPI (table 6.2.5) */
export function aimStartNoPapi(lda) { const tab = val(CAAC.runway.aimStartNoPapi); for (const k of Object.keys(tab).map(Number).sort((a, b) => a - b)) if (lda < k) return tab[k]; return 400; }
/** arrow head height h for a runway width (table 6.2.4-2) */
export function arrowH(W) { const tab = val(CAAC.runway.arrowHeadH); let h = 12; for (const k of Object.keys(tab).map(Number).sort((a, b) => a - b)) if (W >= k - 0.5) h = tab[k]; return h; }
/** flat [{key, value, src}] list of every parameter (for the report / About panel) */
export function paramList() {
  const out = [];
  const walk = (o, pre) => { for (const [k, v] of Object.entries(o)) { if (Array.isArray(v) && v.length === 2 && typeof v[1] === 'string') out.push({ key: pre + k, value: v[0], src: v[1] }); else if (v && typeof v === 'object' && !Array.isArray(v) && k !== 'rings') walk(v, pre + k + '.'); } };
  walk(CAAC, ''); return out;
}
