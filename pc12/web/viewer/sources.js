// Provenance of the model, transcribed from pc12/CLAUDE.md ("Sourced facts" and
// "Estimated / reconstructed").  Shown in the Specs tab.  Keep in sync with CLAUDE.md.

export const SOURCED = [
  {
    source: 'Pilatus (PC-12 PRO / NGX published data)',
    facts: [
      'Wing span 16.28 m, length 14.40 m, height 4.26 m, wing area 25.81 m²',
      'Tailplane span 5.20 m, wheel track 4.53 m',
      'Cabin 5.16 × 1.52 × 1.47 m, flat floor 1.30 m wide',
      'Passenger (airstair) door 0.61 × 1.35 m; cargo door 1.35 × 1.32 m',
      'Propeller 2.67 m, 5-blade Hartzell composite; ground clearance 0.32 m',
    ],
  },
  {
    source: 'EASA TCDS (propeller)',
    facts: ['Hartzell HC-E5A-31A / NC10245B'],
  },
  {
    source: 'EASA TCDS IM.E.008 (engine)',
    facts: [
      'PT6E-67XP length 1,870.9 mm, diameter 481.8 mm',
      '2-stage reduction gearbox, 2-stage power turbine, 1-stage compressor turbine',
      'Compressor: 4 axial + 1 centrifugal stage',
    ],
  },
  {
    source: 'POH, PC-12 NGX',
    facts: [
      'Datum 3.000 m ahead of the firewall; three-view wheelbase 3.48 m',
      'Electromechanical gear; trailing-link mains retract inward, one leg-mounted door each; tyres protrude ~1 in when retracted',
      'Nose gear retracts aft, enclosed by doors; over-centre two-piece folding struts',
      'Ailerons with Flettner geared balance tabs (opposite motion); elevator in two halves; single-piece rudder',
      'Stabiliser trim: leading edge down = nose up',
    ],
  },
  {
    source: "Jane's All the World's Aircraft",
    facts: [
      'Airfoils LS(1)-0417MOD root, LS(1)-0313 tip',
      'Fowler flaps over 67 % of the trailing edge; T-tail with bullet fairing',
      'Dorsal fin and ventral strakes',
      'Tyres 22 × 8.50-10 (main), 17.5 × 6.25-6 (nose); nose-wheel steering ±60°',
      'Emergency exit on the right side over the wing (plug hatch, as drawn by Pilatus)',
    ],
  },
  {
    source: 'PC-12 PRO',
    facts: [
      "Pilot's direct-vision window deleted",
      'Garmin G3000 PRIME: 3 × 14-in and 2 × 7-in touch displays',
      'PC-24-style yokes; radome enlarged for the 12-in GWX 8000 antenna',
    ],
  },
  {
    source: 'NGX; POPA variant guide',
    facts: [
      'Rectangular PC-24-style cabin windows, 10 % larger; dark windshield surround trim (NGX)',
      '"PC-21 style" winglets from Series 10A (MSN 684+)',
      'Weather-radar pod on the right wing',
    ],
  },
];

export const ESTIMATED = [
  'Fuselage contours between the anchor dimensions',
  'Windshield and side-window outlines (fitted to the Pilatus NGX drawing and checked against PC-12 PRO photos)',
  'Winglet cant (51° from vertical), sweep and height: drawn; the straight part lengthened to the official span',
  'Wing dihedral (6.2° from the drawn surfaces), incidence and washout',
  'Airfoil ordinates (reconstructions of the named sections)',
  'Fin and tailplane planform details',
  'Engine module proportions inside the TCDS envelope',
  'Interior layout',
  'Livery: the MSN 3008 (N81DW) scheme reconstructed from photographs, no lettering',
];

// Values the viewer animates with.  They come from the model's pivot data and are
// modelled / estimated, not sourced from the POH.
export const ANIMATION_NOTES = [
  'Control travel: ailerons −20° / +15°, elevators −20° / +15°, rudder ±25°, rudder tab trim ±12°',
  'Aileron tab gearing −0.6 × aileron; stabiliser incidence −4° to +2°',
  'Flap Fowler travel and hinge line (detents 0 / 15 / 30 / 40° as in the build notes)',
  'Blade pitch: feather +62°, reverse −38° relative to the modelled fine pitch',
  'Propeller 1,700 rpm (1,550 rpm low-speed mode) per the build notes; the ~1,000 rpm idle is a viewer estimate',
  'Gear and door angles, retraction timing (~6 s) and brace geometry',
];
