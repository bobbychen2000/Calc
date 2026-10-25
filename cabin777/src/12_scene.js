// ------------------------------------------------------------------
// Scene assembly: meshes, ambient-visibility volume, sun shadows, lighting moods, window shades, rendering
// ------------------------------------------------------------------
const MOODS = {
  // boarding = the ANA photo look: neutral-cool white LED light, high key (ref/ana y_47300, c_27312, py_37302)
  // QA r1: two LED circuits. led = ceiling cove (stays near-white in boarding/cruise: aisle ceiling + aisle-side bins lit
  // white), sideLed = the lens under the outboard bins, ANA's saturated blue sidewall band fading to white at the window
  // belt [V: tlfl_IMG_9217 #5b5cc4 (cruise), sany_10 #5466e8 / sany_12 #4c5edc (boarding), roame_7672 #5e7fef].
  // hemiBot lowered and exposure raised with the fill/AO rework (u_fill 0.7 -> 0.45) so mean tones stay put while
  // undersides, footwells and the floor darken [V: tlfl_IMG_9217 PSU underside #615c5d, c_27312 footwell #2d2c30]
  // QA r2: sideLed raised so the band under the outboard bins reads saturated blue now that the shader cuts the white
  // hemi / bounce / wash inside the band [V: tlfl_IMG_9217 #5d5eca at the lens, #867db2 at the window tops; sany_12
  // boarding #4c5edc]
  // QA r3: the sRGB display encode, AO_TUNE (unoccluded hemisphere share 0.15 -> 0.22, emitter cells under the bins)
  // and the THE Suite lift raise the shadowed faces, so the exposures come down (boarding 1.40 -> 1.20, cruise 1.15 ->
  // 1.0), set on the photo's material tones at HEAD: q06 charcoal shells #42454f (c_27312 #394049-#414755), aisle ash
  // ends #bbb9b3 (#bdbaab-#cfcabd), window wall #d2d4d5 (#cacdd2); q15 window-block backs #566aa0 (y_47300 #415385-
  // #4d5e8c); q03 console #594d45 (omaat_f11 #514537) [D renders, V photos].
  // Boarding keeps the white sidewall of ANA's official photos (c_27312, y_47300, py_37302, sans_14 at HND: no blue
  // band; from_integration / from_shell 1): a near-white lens with a light band cut. The saturated blue band that runs
  // down past the windows is the in-service cruise look: the lens alone lights the wall under the bins (bandCut 0.8),
  // 0.2 of it at the belt [V: tlfl_IMG_9217 #5c5dc6, belt #736a88; sany_12 #556df7, window line #5362e0; stwis_img_6082
  // #1961f9]; sideLed from the ACES inverse of #5467ef at the lens [D]. Boarding vs blue: questions_lighting.md 1
  // QA r1 (light), tonal range: with the crevice term in mainFS (near-blacks only where ao < 0.5) the exposures go up,
  // boarding 1.20 -> 1.38, cruise 1.00 -> 1.12: whites stopped at 225-239 and mid-tones sat 10-15 % low [V: p99 / % >235
  // c_27312 255 / 7.2 %, y_47301 254 / 9.5 %, py_37301 246 / 6.5 % vs q06 238 / 1.5 %, q16 228 / 0.4 %, q14 237 / 1.3 %;
  // Y fabric mean L66 (y_47300) vs 56] (integration r1). Boarding lens cool white and brighter, bandCut 0.15: the band
  // from the lens to the window tops is the brightest part of the official photos' wall, slightly cool [V: y_47301
  // #f0f1f5 / #ebeaf0, y_47300 #e3e7ed / #dee3ef (B-R +5..17), c_27312 #eaedf0 vs q16 #d3d3d3, q15 #c6c7c7]
  // Cruise band: lighter and less saturated, fading out by the window belt (sideLow 0.10) and off the reveals next to
  // the glass (mainFS nearPane) [V: sany_22 #5f70e4 / #666cb3 (L107-117, s0.40-0.58); sany_12 #4d62e2; tlfl_IMG_9217
  // lens #5c67e7, wall top #5a59b9; tlfl_IMG_9206 band #7371bd / #686ad1 (h239-241); ucr_the-room-takeoff #6f88da, upper
  // #7d89be, belt #858897; was c03 #5c6ae5 / q16 #2334e1 (s0.84)] (lighting + integration r1). sideLed hue between the
  // raters' two fits (h~232) [D]; bandCut 0.8 kept: the suggested 0.55 washed the band to #9896d6 (L156 s0.30), 0.75
  // with the new tone read L127-157 s0.39-0.47 (c16) [D renders]
  boarding: { label: 'Boarding', hemiTop: [0.97, 0.99, 1.03], hemiBot: [0.36, 0.37, 0.40], wash: [0.25, 0.26, 0.28], led: [1.0, 0.98, 0.92], sideLed: [0.48, 0.53, 0.66], bandCut: 0.15, k: 1.05, exposure: 1.38, toe: 1 },
  // QA r2 (light): cruise sideLow 0.10 -> 0.30, the lavender wash reaches the window belt in THE Suite (the reveals by
  // the glass stay near-white through mainFS nearPane) [V: ml_DSC_1939-1 wall column y45 #6e9bfc (B-R +141), y150
  // #7a89be, belt y240 #888db0 (+40) vs cF03 belt #cccccf (+3)]
  cruise: { label: 'Cruise', hemiTop: [0.86, 0.88, 0.98], hemiBot: [0.24, 0.24, 0.28], wash: [0.25, 0.26, 0.30], led: [1.0, 0.98, 0.92], sideLed: [0.08, 0.14, 1.35], bandCut: 0.8, sideLow: 0.30, k: 0.95, exposure: 1.12, toe: 1 },
  // QA r2 (light): ANA's full-blue phase (safety video, after take-off, early night): cove LED, sidewall lens and vault
  // saturated blue-violet, the seat zone washed blue and dim, the galley ends warm (monFill), the screens lighting their
  // surround [V: sany_47 (SANspotter Y) cove #1d21bd / #2227cb s0.85, crown #181a39, seat backs #171a7a, galley #776349,
  // mean 29/28/81; ml_DSC_1945 (MileLion, THE Suite during the safety video) sidewall #5a61b2, console top #3b3e6e,
  // ottoman #454987, mean 81/79/111; ml_DSC_1946 bulkhead #493f97; ml_IMG_20200208_0717146 lavender-blue console].
  // Levels [D]: the raters' fit ([0.05, 0.06, 0.30] hemi, vault [0.04, 0.05, 0.35]) read 1.7x the sany_47 mean (bl16f
  // 50/60/139, crown #1a207e) with the THE Suite ottoman at L23 (ml #454987 L77) and the wall over-saturated (#7184eb vs
  // #5a61b2), so a darker deep-blue top (hemiTop, vault: crown #181a39), a lavender seat level (lowTint / lowGain, ml
  // ottoman / console G/R ~1.05, B/R ~1.9) and a weaker lens; emisGain as Night (signs dimmed). Second pass: the two
  // photos are exposed ~2x apart (sany_47 mean 29/28/81, ml_DSC_1945 81/79/111), exposure 1.7 sits between them, the
  // bin doors' fill lift at 0.4 (sany_47 dark bins under bright cove lines), seat level x1.6 (b8: Y mean 49/56/124,
  // F ottoman L26) [D renders]
  blue: { label: 'Blue', hemiTop: [0.035, 0.04, 0.21], hemiBot: [0.008, 0.009, 0.035], wash: [0.015, 0.015, 0.07], led: [0.06, 0.08, 1.0], sideLed: [0.05, 0.06, 0.70], bandCut: 0.8, sideLow: 0.6, vault: [0.025, 0.028, 0.10], lowTint: [1.8, 1.7, 1.0], lowGain: 1.6, fillLift: 0.4, monFill: [0.06, 0.05, 0.035], cove: 0.35, k: 1, exposure: 1.7, screenGain: 0.6, scrSpill: 1, emisGain: 0.55, strips: true },
  // dining / sunrise, QA r2: ANA's amber phase is a saturated amber LED line on the bin lens and cove, amber-washed bin
  // faces and a much darker lower cabin, not a beige high key [V: ff_door-gap lens #ffa43d (h32 s0.76), bins #955b2d /
  // #673e1e (s ~0.7)]. Sunrise uses the same levels with a pinker LED [A: no ANA sunrise photo]
  // QA r3: led / sideLed inverted through ACES for #ffa33c at the cove / lens gains (the r2 [1, 0.22, 0.02] put G at
  // ~1.5 before ACES and clipped to lemon #fce04f) [D]; hemi softened (the ceiling and bins read #d9b77d / #b87130 at
  // s 0.4-0.7, not saturated orange) and the dim vault wash takes its own warm-beige colour [V: ff_seat-with-door-closed
  // ceiling #d9b77d, bins #7f6440; ff_door-gap bins #945a2a / #b87130]; lowTint neutralises the amber below 1.25 m
  // (hemi x lowTint = [0.81, 0.78, 0.72]) so seat-level ash stays grey and brighter than the bins [V: ff_door-gap ash
  // #afafaf / #acb1ba (s <= 0.08), grey shell #6f7982]; the lens light reaches the wall less red (sideWall) and not past
  // the window tops (sideLow 0) [A: no amber-phase sidewall photo, questions_lighting.md 2]
  // QA r1 (light): the amber reaches seat level, warm and dimmer, in every real photo of the phase: lowTint [1.3, 2.6,
  // 6.5] -> [1.0, 1.35, 2.0] (hemi x lowTint ~h28; [1, 1.25, 1.8] rendered the ash #624023 s0.64, a little over the
  // photos' s0.5-0.6) and 0.6 gain below 1.25 m (lowGain: d07 lower third L132 -> 90); lens light on the wall
  // down to half way past the windows (sideLow 0.5) in the hemi's amber (sideWall = hemiTop / sideLed share: the
  // sideLed that renders the clipped lens #ffa33c is near-red below the clip, and with the cool day window light it
  // left the lower wall pink, #635655 h6; sideWall 1 tried, salmon) [V: ff_seat-with-door-closed ash cabinet #ab7f58, shell #251f17, ottoman #2e2219;
  // ff_door-gap ash #b29f84 / #6b5946 at 1024 px; ucr_the-room-cabin ash #ae7134 / #885635, sidewall #ba895b-#bb8a60,
  // reveal shadow #b48357, bottom third L55; kn_room_35 ash fronts #804e10-#8f5c20] (lighting r1)
  // QA r2 (light + integration): (1) fillLift 0.35: the small-e fill lift on the PSU band / bin doors no longer glows tan
  // [V: ff_door-gap PSU band #603b1d L65, ucr_the-room-cabin #6f482a L79 vs q21 #ad7c42]; (2) vault [0.40, 0.15, 0.045]
  // (G/R 0.38, the led hue) so the door domes and the vault stay saturated after ACES [V: ucr ceiling #c89552 s0.59, far
  // door zone #c28440 s0.67 vs q21 #e8cf99 s0.34]; (3) lensCore: the lens core clips pale yellow, the frame's highlight
  // [V: ucr lens #fefed6, ff_door-gap #fefeb6]; (4) seat level brighter and less fiery: lowGain 0.6 -> 0.9, lowTint
  // [1.0, 1.35, 2.0] -> [1.0, 1.5, 2.6] (light G/R ~0.6, B/R ~0.4 on the ash), sideWall [0.4, 2.4, 4.5] -> [0.4, 2.8, 7.0],
  // sideLow 0.5 -> 0.65 [V: ucr ash #ae7136 L122 / #895636 L95, pier #bc895e L145, reveal #b58459; ff_seat-with-door-
  // closed ash cabinet #ab7f58 L133 vs dining_room ash #593717 L60 s0.74]; (5) screens spill at half the night level.
  // Tuned on renders [D]: the raters' fillLift 0.35 left the band at L100 (q21), so 0.15; lowGain 0.9 left the
  // dining_room ash at L84 and lowTint [1.0, 1.5, 2.6] read s0.4-0.5 against ucr's foreground ash #9a6330 s0.69, so
  // lowGain 1.4 (the photos are auto-exposed: seat level ~0.7-0.85 of the ceiling, the render 0.55) with lowTint [1.0,
  // 1.42, 2.3]; vault x0.9 (q21 door dome L164 s0.64 vs ucr #c89552 L156)
  dining: { label: 'Dining', hemiTop: [0.62, 0.30, 0.11], hemiBot: [0.15, 0.07, 0.025], wash: [0.30, 0.14, 0.05], led: [0.55, 0.042, 0.009], sideLed: [1.25, 0.10, 0.02], sideLow: 0.65, sideWall: [0.5, 1.5, 2.5], bandCut: 0.3, vault: [0.36, 0.135, 0.04], vaultE: [0.10, 1], lowTint: [1.0, 1.08, 1.2], lowGain: 0.8, fillLift: 0.15, lensCore: [0, 0.55, 0.15], scrSpill: 0.5, k: 0.9, exposure: 1.3, strips: true },
  // night, QA r2: THE Room in service at night is near-black and neutral-warm; the light comes from the IFE screens, the
  // warm strip under each screen, small white reading lamps and amber PSU lamps [V: ucr_room-night-lighting ceiling
  // #1e1915, sidewall #24211c, bins #322a1f, PSU lamp #9e5e38, strip #ffeb97, mean RGB 39/34/33]. The blue night refs
  // used in r1 (roame_7672, sany_10) were boarding shots on the ground (daylight in the windows), so not the night scene
  // QA r3: cove / lens saturated amber (was warm white) [V: stwis_img_6223 cove #dc9340 / #b0671a (h25-32, s0.71-0.85),
  // ucr PSU lamp #9f5e39], the lens light kept to the upper wall (ucr sidewall #24211c); vault wash the same amber hue
  // (G/R 0.36, as the photo's dim amber h25-30), mid-vault <= #2a2219 [D]; hemi unchanged (image mean already matches
  // ucr 39/35/33)
  // QA r1 (light): the r3 amber came from one cove sample (stwis_img_6223) and washed the vault and the whole sidewall
  // orange (#26150a / #301607, s0.73-0.87); none of the four real night photos looks like that. Neutral-warm cove and
  // vault (G/R ~0.85; vault 0.020 rendered the mid-vault L12 vs ucr #211a14 L27 at the same place, so 2.5x), a cool-grey
  // dim lens light down the wall (sideLow 0.6), and a dim neutral fill in the galley /
  // door zones (monFill: #c8c0b4 at ~0.25 of the boarding level, after exposure) [V: ucr_room-night-lighting ceiling
  // #352f2a / #16110e (s0.2-0.38), bins #312820, sidewall #23201c, lower sidewall #4f515b, far galley wall #645f57;
  // sany_40 ceiling #42413d-#605d5f (s <= 0.08), sidewall #434c67-#8d9bc1] (lighting r1); hemi, screens, strips unchanged.
  // Exposure 2.2 -> 2.5: q20 median L25 vs ucr 30, and economy at night (sany_40, median L58) read about half as bright
  // as the photo (wall L25-43 vs #494f67 L80, ceiling L39 vs #474647 L71) [D: renders r1b]
  // QA r2 (light): the IFE screens light their surround (scrSpill 1, mainFS u_scrP) [V: ml_IMG_20200208_1919534 THE Suite
  // housing #251e1e, ucr_room-night-lighting near wall #302218]; emisGain 0.55 = the r2 night sign level
  sleep: { label: 'Night', hemiTop: [0.030, 0.027, 0.024], hemiBot: [0.010, 0.009, 0.008], wash: [0.012, 0.010, 0.008], led: [0.030, 0.025, 0.020], sideLed: [0.018, 0.021, 0.032], sideLow: 0.6, vault: [0.050, 0.043, 0.035], vaultE: [0, 0.12], monFill: [0.060, 0.055, 0.047], cove: 0.35, k: 1, exposure: 2.5, readingLights: true, strips: true, screenGain: 0.6, scrSpill: 1, emisGain: 0.55 },
  // QA r1 (light): sunrise follows dining at seat level (sideWall = hemiTop share, sideLow 0.5). QA r2: as dining, the
  // fill lift off the PSU band (fillLift 0.15), the saturated vault, the pale lens core, lowGain 0.6 -> 1.4 and lowTint
  // [1.0, 1.3, 1.6] -> [1.0, 1.4, 1.95] [A: no ANA sunrise photo; dining's sources and levels]
  wake: { label: 'Sunrise', hemiTop: [0.62, 0.30, 0.16], hemiBot: [0.15, 0.07, 0.035], wash: [0.30, 0.14, 0.07], led: [0.55, 0.05, 0.03], sideLed: [1.2, 0.11, 0.06], sideLow: 0.5, sideWall: [0.42, 2.25, 2.2], bandCut: 0.3, vault: [0.36, 0.135, 0.04], vaultE: [0.10, 1], lowTint: [1.0, 1.08, 1.2], lowGain: 0.8, fillLift: 0.15, lensCore: [0, 0.55, 0.15], k: 0.9, exposure: 1.3 },
};
// winExp: the view behind the glass at interior exposure; cabin photos show day windows near-white with a glowing
// reveal (tlfl_IMG_9217 / 9518, pane ~#eef3f8) [V]; eases back to 1 when the eye is at the window (looking out)
const SKIES = {
  // QA r3: winExp 1.6 -> 4.0: day panes must be the brightest thing in a cabin view, near-white against the wall
  // [V: c_27316 pane #ffffff vs wall #d1d1d1-#e2e2e2; y_47300 #fcfcfb; tlfl_IMG_9217 #fefefc]; 3.0 (rater) still left the
  // deep-blue sky reading #c4d8eb in the q03 pane [D]. Deeper day sky for the look-out view (winExp eases to 1 at the
  // window) [V: F-GSQR_1/_2 zenith #114892-#2472ca, from_exterior 2].
  // Exterior w5 (user: deep-blue cruise sky): zenith / horizon fitted with skyK 12 to #8fb8e6 (1 deg) #5d8cc4 (3) #3a66a0
  // (8.5) #2a4f86 (15) #1f4274 (25), between F-GSQR_1 and _2 [V photos, D fit].
  // extBounce = the lit deck seen by the exterior's undersides (0.55 x cloudLit) and extSun the exterior's sun scale
  // (the sun side of the cowl saturated at 5.2) [D: from_exterior 1 / 6; alv_ANA77W_NH211_26K cowl #9fabb7-#a9c0ce]
  day: { label: 'Day', sunEl: 30, sunAz: -60, sun: [5.2, 4.9, 4.4], zenith: [0.019, 0.05, 0.095], horizon: [0.20, 0.37, 1.0], skyK: 12, haze: [0.55, 0.66, 0.85], cloudLit: [1.25, 1.25, 1.25], cloudShade: [0.62, 0.68, 0.78], skyTop: [0.55, 0.68, 0.95], skyBot: [0.55, 0.55, 0.58], extBounce: [0.69, 0.69, 0.69], extSun: 0.6, winGlow: [0.45, 0.52, 0.62], winExp: 4.0, sunVis: 1, night: 0, sheer: 1.0 },
  // QA r3: dim blue-grey deck under a narrow orange horizon band, blue upper sky [V: Air_France_777-300ER_Greenland_
  // Sunrise deck #50595d-#646a67, band #d2a46d, sky #9cabaa; Emirates_77W_wing_view / alv_7282 zenith #527dc2]; dark cool
  // deck bounce and a grazing sun at 0.35 on the exterior, so the wing takes the sky colour (from_exterior 3)
  // QA r1 (light): a dim blue deck, not flat grey (haze / cloudLit), and a lighter, greyer exterior sky fill with a
  // weaker grazing sun (extSun 0.35 -> 0.25) so the wing reads grey-blue, not royal blue [V: omaat_f73 dusk deck #3d608b
  // (s0.56), sky #346cb1, thin warm horizon band; alv_7282 wing ~#6f83b7 vs s26K #3a4474] (lighting r1, from_exterior 8;
  // the suggested skyTop [0.22, 0.25, 0.42] rendered the 19A wing mauve-grey #615564 h287 under the red sun [D])
  sunset: { label: 'Sunset', sunEl: 5, sunAz: 110, sun: [4.2, 2.2, 0.9], zenith: [0.08, 0.14, 0.42], horizon: [1.1, 0.55, 0.30], haze: [0.10, 0.15, 0.24], cloudLit: [0.08, 0.12, 0.20], cloudShade: [0.018, 0.024, 0.034], skyTop: [0.28, 0.34, 0.60], skyBot: [0.4, 0.26, 0.2], extBounce: [0.07, 0.08, 0.10], extSun: 0.25, winGlow: [0.22, 0.12, 0.08], sunVis: 1, night: 0, sheer: 0.7 },
  night: { label: 'Night', sunEl: 38, sunAz: -40, sun: [0.07, 0.08, 0.12], zenith: [0.004, 0.006, 0.016], horizon: [0.02, 0.028, 0.05], haze: [0.018, 0.022, 0.036], cloudLit: [0.05, 0.055, 0.07], cloudShade: [0.012, 0.014, 0.02], skyTop: [0.02, 0.025, 0.04], skyBot: [0.01, 0.01, 0.015], extBounce: [0.028, 0.030, 0.038], extSun: 1, winGlow: [0.0, 0.0, 0.0], sunVis: 0, night: 1, sheer: 0.06 },
};
// QA r3 ambient-occlusion tuning [D: q06 / q15 / q03 / q05 / q14 against c_27312, y_47300, omaat_f11, f_17313,
// py_37301]: hemi = unoccluded share of the hemisphere fill (was 0.15), bounce = interreflection gain, emitLens /
// emitCtr = sky value of the air under the outboard bins (sidewall lens band) and under the centre bins, kAttF = voxel
// attenuation inside THE Suite zone (1.35 elsewhere), fLift = share of the AO lifted toward 1 inside the suites (shader)
// QA r3 (integration): azim / slope = sweep azimuths and cells sideways per layer (was 8 / 1), floorBlur = layers that
// take two extra i / k blur passes (computeAO)
const AO_TUNE = { hemi: 0.22, bounce: 1.0, emitLens: 0.45, emitCtr: 0.35, kAttF: 0.8, fLift: 0.35, azim: 16, slope: 0.5, floorBlur: 5 };
// QA r1 (light): cove = gain of the two cove LED line lights in the interior specular (mainFS coveSpec) [D: rim
// highlight ~1.3x the face on THE Room shell caps (c_27312), armrest p99 >= 240 (y_47303)]
// QA r3 (integration): sheen = gain of the grazing sheen lobe on SHEEN materials (mainFS) [D: q17 / q16 flaps against
// y_47303 / y_47301, q15 head-on unchanged]
const LIGHT_TUNE = { cove: 1.0, sheen: 0.84 };
// Shade states per window: 0 open, 1 half (manual) / sheer (electric), 2 closed (manual) / blackout (electric)
const SHADE_STATE = {
  label: (w, lv) => (w.electric ? ['open', 'sheer blind', 'blackout'] : ['open', 'half down', 'closed'])[lv],
  T: (w, lv) => (lv === 0 ? [0.92, 0.92, 0.92] : w.electric ? (lv === 1 ? [0.30, 0.29, 0.27] : [0.02, 0.02, 0.02]) : (lv === 1 ? [0.92, 0.92, 0.92] : [0.03, 0.03, 0.03])),
  open: (w, lv) => (lv === 0 ? 1 : lv === 1 ? (w.electric ? 0.35 : 0.55) : 0),
};

class Scene {
  constructor(gl, opts = {}) {
    this.gl = gl;
    this.q = opts.quality || 'high';
    const t0 = performance.now();
    this.layout = buildLayout();
    buildAtlas(this.layout);
    this.tex = {
      detail: gl.textureArray(buildDetailLayers(256), 256),
      photo: gl.textureArray(buildPhotoLayers(256), 256),
      atlas: gl.texture2D(ATL.canvas, { srgb: false }),
      cloud: gl.texture2D(buildCloudNoise(256), { w: 256, h: 256 }),
    };
    this.shell = buildShell(gl, this.layout);
    this.bins = buildBins(gl, this.layout);
    const sr = buildSeats(gl, this.layout);
    this.seats = sr.meshes; this.seatGroups = sr.groups;
    this.mono = buildMonuments(gl, this.layout);
    this.ext = buildExterior(gl);
    this.progs = {
      main: gl.program(SH.mainVS, SH.mainFS),
      depth: gl.program(SH.depthVS, SH.depthFS),
      sky: gl.program(SH.skyVS, SH.skyFS),
      glass: gl.program(SH.mainVS, SH.glassFS),
      glow: gl.program(SH.glowVS, SH.glowFS),
    };
    this.emptyVAO = gl.gl.createVertexArray();
    gl.use(this.progs.main); gl.set('u_fillLift', 1); gl.set('u_sheen', LIGHT_TUNE.sheen); gl.set('u_vaultE', [0, 1]);   // the studio may draw before the first cabin frame
    this.buildGlows();
    const sm = this.shell.meshes;
    this.opaque = [
      sm.shell, sm.upper, sm.revealR, sm.revealL, sm.shadeBtns,
      sm.shade_manual, sm.shade_sheer, sm.shade_blackout, sm.shadeRail_manual, sm.shadeRail_sheer, sm.shadeRail_blackout,
      ...Object.values(this.bins), ...Object.values(this.seats), this.mono.mesh,
    ];
    this.computeAO();
    this.winTex = null;
    this.winLevels = this.layout.windows.map(() => 0);
    this.mood = 'cruise'; this.sky = 'day'; this.globalShade = 0;
    this.xray = false;
    this.shadowDirty = true;
    this.updateWindowLUT();
    this.buildTime = performance.now() - t0;
  }

  // ---------------- ambient visibility volume ----------------
  computeAO() {
    // ~8.3 cm voxels (QA r1: 10 cm cells could not resolve the 0.1 m footwells / console gaps) [D]
    const nx = 72, ny = 34, nz = 712;
    const min = [-3.0, 0, 2.6], size = [6.0, 2.8, 59.2];
    const cell = [size[0] / nx, size[1] / ny, size[2] / nz];
    const occ = new Float32Array(nx * ny * nz);
    const solid = new Uint8Array(nx * ny * nz);   // bins, monuments and the space outside the wall (not seat voxels)
    const idx = (i, j, k) => (k * ny + j) * nx + i;
    const box = (x0, x1, y0, y1, z0, z1, d = 1) => {
      const i0 = Math.max(0, Math.floor((x0 - min[0]) / cell[0])), i1 = Math.min(nx - 1, Math.floor((x1 - min[0]) / cell[0]));
      const j0 = Math.max(0, Math.floor((y0 - min[1]) / cell[1])), j1 = Math.min(ny - 1, Math.floor((y1 - min[1]) / cell[1]));
      const k0 = Math.max(0, Math.floor((z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((z1 - min[2]) / cell[2]));
      for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) { const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + d); if (d >= 1) solid[q] = 1; }
    };
    // local box of a unit (room / suite) -> world
    const boxL = (s, x0, x1, y0, y1, z0, z1, d = 1) => {
      const a = localToWorld(s, [x0, y0, z0]), b = localToWorld(s, [x1, y1, z1]);
      box(Math.min(a[0], b[0]), Math.max(a[0], b[0]), y0, y1, Math.min(a[2], b[2]), Math.max(a[2], b[2]), d);
    };
    // seats: voxelise the real instanced geometry (surface samples every ~5 cm, each adds partial occupancy) so
    // footwells, seat undersides, shell corners and console gaps get soft occlusion that matches their shapes
    const dOcc = 0.34, step2 = 0.05 * 0.05;
    const mark = (x, y, z) => {
      const i = Math.floor((x - min[0]) / cell[0]), j = Math.floor((y - min[1]) / cell[1]), k = Math.floor((z - min[2]) / cell[2]);
      if (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) return;
      const q = idx(i, j, k); occ[q] = Math.min(1, occ[q] + dOcc);
    };
    for (const g of Object.values(this.seatGroups || {})) {
      const P = g.geo.pos, I = g.geo.idx;
      const samples = [];   // local-space sample points of this unit, reused for every instance
      for (let t = 0; t < I.length; t += 3) {
        const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
        const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2];
        const vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
        const cx = uy * vz - uz * vy, cy = uz * vx - ux * vz, cz = ux * vy - uy * vx;
        const area = 0.5 * Math.hypot(cx, cy, cz);
        const n = Math.min(64, Math.ceil(area / step2));
        for (let m = 0; m < n; m++) {
          let r1 = ((m * 0.618034 + t * 0.1234) % 1), r2 = ((m * 0.754878 + t * 0.4321) % 1);
          if (r1 + r2 > 1) { r1 = 1 - r1; r2 = 1 - r2; }
          samples.push(P[a] + ux * r1 + vx * r2, P[a + 1] + uy * r1 + vy * r2, P[a + 2] + uz * r1 + vz * r2);
        }
      }
      for (const M of g.mats) for (let q = 0; q < samples.length; q += 3) {
        const x = samples[q], y = samples[q + 1], z = samples[q + 2];
        mark(M[0] * x + M[4] * y + M[8] * z + M[12], M[1] * x + M[5] * y + M[9] * z + M[13], M[2] * x + M[6] * y + M[10] * z + M[14]);
      }
    }
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      box(1.46, 2.95, 1.60, 2.30, zn.z0, zn.z1); box(-2.95, -1.46, 1.60, 2.30, zn.z0, zn.z1);
      box(-0.83, 0.83, 1.84, 2.34, zn.z0, zn.z1);
    }
    for (const m of this.layout.mon) if (m.h > 0) box(m.x0, m.x1, 0, m.h, m.z0, m.z1);
    for (let j = 0; j < ny; j++) {
      const y = min[1] + (j + 0.5) * cell[1];
      const xw = wallAt(Math.min(y, 2.3))[0];
      for (let i = 0; i < nx; i++) { const x = min[0] + (i + 0.5) * cell[0]; if (Math.abs(x) > xw) for (let k = 0; k < nz; k++) { occ[idx(i, j, k)] = 1; solid[idx(i, j, k)] = 1; } }
    }
    // QA r3: THE Suite geometry occludes less (kAtt 0.8 in the F zone): the 1.3 m shells are open-topped under the
    // bright ceiling, and the ottoman / console / pier read near-black next to a white wall where the daylight photos
    // show mid-tones [V: f_17300, omaat_f2 / f5 / f11 ottoman #9f8c85, console #514537; q03 #312f2d]
    const kAtt = 1.35, kAttF = AO_TUNE.kAttF;
    const fz = this.layout.zones.find((zn) => zn.cls === 'F');
    const kf0 = fz ? Math.floor((fz.z0 - min[2]) / cell[2]) : -1, kf1 = fz ? Math.floor((fz.z1 - min[2]) / cell[2]) : -1;
    const att = new Float32Array(occ.length);
    for (let q = 0; q < occ.length; q++) { const k = Math.floor(q / (nx * ny)); att[q] = Math.exp(-(k >= kf0 && k <= kf1 && !solid[q] ? kAttF : kAtt) * occ[q]); }
    // QA r3: emitter cells. The sweep only sees the ceiling, so everything under the outboard bins read 0 (window seats,
    // the inside of THE Suite) although the sidewall lens, the lit bin undersides and the windows light it. Air cells in
    // the lens band (y 1.30-1.60, |x| 1.55 to the wall) count as sky at 0.45 and the strip under the centre bins
    // (y 1.74-1.84, |x| < 0.83) at 0.35, in the seat zones (bins above) [D: probe of the volume; q05 ottoman 62 -> 98 L
    // vs f_17313 97, q14 median 68 -> 114 vs py_37301 117; 0.55 overshot the suite caps under the lens]
    const emit = new Float32Array(occ.length);
    for (const zn of this.layout.zones) {
      if (zn.type !== 'seat') continue;
      const k0 = Math.max(0, Math.floor((zn.z0 - min[2]) / cell[2])), k1 = Math.min(nz - 1, Math.floor((zn.z1 - min[2]) / cell[2]));
      for (let j = 0; j < ny; j++) {
        const y = min[1] + (j + 0.5) * cell[1];
        const xw = wallAt(y)[0];
        for (let i = 0; i < nx; i++) {
          const ax = Math.abs(min[0] + (i + 0.5) * cell[0]);
          const e = y > 1.30 && y < 1.60 && ax > 1.55 && ax < xw ? AO_TUNE.emitLens : y > 1.74 && y < 1.84 && ax < 0.83 ? AO_TUNE.emitCtr : 0;
          if (e) for (let k = k0; k <= k1; k++) { const q = idx(i, j, k); if (!solid[q]) emit[q] = e; }
        }
      }
    }
    const acc = new Float32Array(nx * ny * nz);
    // QA r3 (integration): AO_TUNE.azim sweep azimuths (was 8 at 45 deg, one cell sideways per layer) stepping
    // AO_TUNE.slope cells sideways per layer, read bilinearly. The 8 diagonal sweeps let every 1.15-1.3 m THE Room shell
    // throw a 1.0-1.3 m wedge across the 0.55 m aisle, periodic at each seat pair [V: q06 aisle p10 20, 34 % < 30 vs
    // c_27312 p10 41, 5.5 %; kn_room_1 no stain beyond the contact line]; vertical share 0.28 kept [D]
    const dirs = [[0, 0, 0.28]];
    for (let a = 0; a < AO_TUNE.azim; a++) {
      const t = (a + 0.5) * 2 * Math.PI / AO_TUNE.azim;
      dirs.push([Math.cos(t) * AO_TUNE.slope, Math.sin(t) * AO_TUNE.slope, 0.72 / AO_TUNE.azim]);
    }
    const layerA = new Float32Array(nx * nz), layerB = new Float32Array(nx * nz);
    for (const [ox, oz, wgt] of dirs) {
      let prev = layerA, cur = layerB;
      prev.fill(1);
      const fx = Math.floor(ox), fz = Math.floor(oz), tx = ox - fx, tz = oz - fz;
      const w00 = (1 - tx) * (1 - tz), w10 = tx * (1 - tz), w01 = (1 - tx) * tz, w11 = tx * tz;
      // visibility one layer up at (pi, pk): outside the wall 0, past the cabin ends open
      const vAt = (pi, pk) => (pi < 0 || pi >= nx ? 0 : pk < 0 || pk >= nz ? 1 : prev[pk * nx + pi]);
      for (let j = ny - 1; j >= 0; j--) {
        for (let k = 0; k < nz; k++) for (let i = 0; i < nx; i++) {
          const pi = i + fx, pk = k + fz;
          let V = w00 * vAt(pi, pk);
          if (w10) V += w10 * vAt(pi + 1, pk);
          if (w01) V += w01 * vAt(pi, pk + 1);
          if (w11) V += w11 * vAt(pi + 1, pk + 1);
          const q = idx(i, j, k);
          if (emit[q] > V) V = emit[q];
          acc[q] += wgt * V;
          cur[k * nx + i] = V * att[q];
        }
        const t = prev; prev = cur; cur = t;
      }
    }
    // QA r3: three separable [1/4, 1/2, 1/4] passes (i, j, k) smooth the 9-direction sweep's V-shaped wedges on flat
    // walls (q19 closet faces vs py_37302 uniform bulkhead); solid cells (walls, bins, monuments) are not averaged in,
    // so the faces next to them do not darken [D]
    // QA r3 (integration): two more i / k passes on the lowest AO_TUNE.floorBlur layers (y < 0.42 m), where the carpet
    // and the seat bases read the volume: the 3-tap blur is one cell wide, the shell wedges ~6 [D]
    const tmp = new Float32Array(acc.length), nb = AO_TUNE.floorBlur;
    const passes = [[0, nx, 1, ny], [1, ny, nx, ny], [2, nz, nx * ny, ny], [0, nx, 1, nb], [2, nz, nx * ny, nb], [0, nx, 1, nb], [2, nz, nx * ny, nb]];
    for (const [di, n, stride, jn] of passes) {
      tmp.set(acc);
      for (let k = 0; k < nz; k++) for (let j = 0; j < jn; j++) for (let i = 0; i < nx; i++) {
        const q = idx(i, j, k);
        if (solid[q]) continue;
        const c = di === 0 ? i : di === 1 ? j : k;
        const a = c > 0 && !solid[q - stride] ? tmp[q - stride] : tmp[q];
        const b = c < n - 1 && !solid[q + stride] ? tmp[q + stride] : tmp[q];
        acc[q] = 0.25 * a + 0.5 * tmp[q] + 0.25 * b;
      }
    }
    const vis = new Uint8Array(nx * ny * nz);
    for (let q = 0; q < acc.length; q++) vis[q] = Math.round(clamp(acc[q], 0, 1) * 255);
    this.ao = { tex: this.gl.texture3D(vis, nx, ny, nz), min, size };
  }

  buildGlows() {
    const gl = this.gl;
    const q = raw();
    q.p.push(-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0); q.n.push(0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1);
    q.u.push(0, 0, 1, 0, 1, 1, 0, 1); q.i.push(0, 1, 2, 0, 2, 3);
    const b = new Builder(); b.add(q, null, { c: '#ffffff' });
    this.glowMesh = gl.mesh(b.build(), { name: 'glow', instances: [] });
    this.readingMesh = gl.mesh(b.build(), { name: 'reading', instances: [] });
    const mats = [], tints = [];
    for (const l of this.ext.lights) { mats.push(M4.trs(l.p[0], l.p[1], l.p[2], 0, 0, 0, l.s, l.s, l.s)); tints.push([...l.c, l.blink]); }
    gl.setInstances(this.glowMesh, mats, tints);
    const rnd = mulberry32(42);
    const rm = [], rt = [];
    // flat 16-gon oval facing down, 0.10 m fore-aft x 0.045 m across
    const oval = raw();
    oval.p.push(0, 0, 0); oval.n.push(0, -1, 0); oval.u.push(0.5, 0.5);
    for (let k = 0; k < 16; k++) {
      const a = (k / 16) * Math.PI * 2;
      oval.p.push(Math.sin(a) * 0.0225, 0, Math.cos(a) * 0.05); oval.n.push(0, -1, 0); oval.u.push(0.5 + Math.sin(a) / 2, 0.5 + Math.cos(a) / 2);
      oval.i.push(0, 1 + k, 1 + ((k + 1) % 16));
    }
    fixWinding(oval);
    const lens = new Builder();
    // QA r1: a small lit lens (4 cm sprite) at the lamp + a warm pool on the seat from the shader spot term, not a floating
    // halo [V: tlfl_IMG_9377 / roame_7672 dimmed cabins: small lens, pool of light on the seat]
    this.spots = [];
    for (const s of this.layout.seats) {
      if (rnd() > 0.18) continue;
      let p, t;
      if (s.kind === 'room') { p = localToWorld(s, s.odd ? [0.03, 1.02, -1.18] : [-0.07, 1.02, 1.18]); t = localToWorld(s, s.odd ? [-0.24, 0.55, -0.75] : [0.20, 0.55, 0.75]); }
      else if (s.kind === 'suite') { p = localToWorld(s, [0.1, 1.06, -0.2]); t = localToWorld(s, [-0.1, 0.55, -0.55]); }
      else {
        const y = Math.abs(s.x) < 1.1 ? 1.82 : binBottomY(s.x * 0.92) - 0.03;
        p = [s.x * 0.92, y, s.z - (s.kind === 'py' ? 0.5 : 0.45)]; t = [s.x, 0.62, s.z - 0.3];
      }
      rm.push(M4.trs(p[0], p[1], p[2], 0, 0, 0, 0.04, 0.04, 0.04)); rt.push([2.4, 2.0, 1.4, 0]);
      this.spots.push({ p, t });
      // amber PSU lamp above each lit seat. QA r3: a crisp emissive oval lens (0.10 x 0.045 m) flush under the PSU
      // plus a 3 cm core sprite, not a 7 cm halo floating in front of the bin [V: ucr_room-night-lighting sharp ~2:1
      // oval lenses, core #ac6437, small halo; size A; e 0.25 gives the #ac6437 core at the night gains D]
      const px = s.x * 0.92, ctr = Math.abs(px) < 1.1;
      const py = ctr ? CBIN_Y - 0.011 : binBottomY(px) - 0.0085;
      const pz = s.kind === 'econ' || s.kind === 'py' ? p[2] + 0.12 : s.z;
      rm.push(M4.trs(px, py - 0.004, pz, 0, 0, 0, 0.03, 0.03, 0.03)); rt.push([1.1, 0.6, 0.3, 0]);
      lens.add(oval, M4.trs(px, py, pz, 0, 0, ctr ? 0 : -TILT_O * Math.sign(px)), { c: '#c07040', r: 0.4, e: 0.25 });
    }
    gl.setInstances(this.readingMesh, rm, rt);
    this.psuLensMesh = gl.mesh(lens.build(), { name: 'psuLens', castShadow: false });
    // THE Room seat mood strips: warm LED line under each monitor bezel (bottom edge 0.645 m) and along the ottoman
    // toe line under the footwell mouth, SEATMAT.moodGlow [V: ucr_room-night-lighting strip under the screen #ffeb97;
    // upperclassroom review: mood lighting under the TV and the ottoman; strip sizes D from the 0.64 m bezel / 0.43 m
    // footwell mouth]. Their light on the console / footwell is the shader strip term (u_stripP, nearest 8)
    // QA r2 (light / integration): the strip LED is saturated warm yellow, not cream: '#ffc860' over SEATMAT.moodGlow's
    // '#ffd9a0' (which only this mesh uses), e 0.25 kept [V: ucr_room-night-lighting strip top-40 px #ffee94 s0.42 /
    // #fde98c vs q20 #eee3c2 s0.18, d06 #eee2c0]
    const glow = { ...SEATMAT.moodGlow, c: '#ffc860' };
    const sb = new Builder();
    this.strips = [];
    for (const s of this.layout.seats) {
      if (s.kind !== 'room') continue;
      const [xm, zf, dir, xo, zm] = s.odd ? [-0.245, MON.zO, -1, -0.345, MON.zO] : [0.21, MON.zE, 1, 0.34, MON.zE];
      // QA r1 (light): the screen strip moved 0.642 -> 0.580, just under the sill lip, which the room w8 raise of the
      // monitor sill to y 0.583-0.667 put over it (from_room w8) [V: tpg_53 bezel borders]
      for (const [x, y, z, w] of [[xm, 0.580, zf + dir * 0.02, 0.56], [xo, 0.03, zm - dir * 0.02, 0.40]]) {
        sb.add(gBox(w, 0.006, 0.012), M4.mul(unitXF(s), M4.trs(s.mir ? -x : x, y, z)), glow);
        const c = localToWorld(s, [x, y, z]), e = localToWorld(s, [x + w / 2, y, z]);
        this.strips.push({ p: c, a: V3.sub(e, c) });
      }
    }
    this.stripMesh = gl.mesh(sb.build(), { name: 'moodStrips', castShadow: false });
    this.buildScreens();
  }

  // QA r2 (light): IFE screens as area lights for the dimmed moods (mainFS u_scrP / u_scrN): the screen quads
  // (layer 13) of each seat unit, clustered into screens (centre, outward normal, area), then placed per instance.
  // Read from the geometry, so they follow the builders: THE Suite 43 in (0.952 x 0.535), THE Room monitor
  // (0.531 x 0.299), PY 0.345 x 0.194 and Y 0.294 x 0.166 seat-back screens; handsets (< 0.02 m2) left out
  buildScreens() {
    this.screens = [];
    for (const g of Object.values(this.seatGroups || {})) {
      const P = g.geo.pos, Nn = g.geo.nrm, Mt = g.geo.mat, I = g.geo.idx, cl = [];
      for (let t = 0; t < I.length; t += 3) {
        const a = I[t], b = I[t + 1], c = I[t + 2];
        if (Mt[a * 4 + 2] !== 13) continue;
        const pa = [P[a * 3], P[a * 3 + 1], P[a * 3 + 2]], pb = [P[b * 3], P[b * 3 + 1], P[b * 3 + 2]], pc = [P[c * 3], P[c * 3 + 1], P[c * 3 + 2]];
        const area = 0.5 * V3.len(V3.cross(V3.sub(pb, pa), V3.sub(pc, pa)));
        const ctr = V3.scale(V3.add(V3.add(pa, pb), pc), 1 / 3), n = V3.norm([Nn[a * 3], Nn[a * 3 + 1], Nn[a * 3 + 2]]);
        let q = cl.find((k) => V3.len(V3.sub(V3.scale(k.c, 1 / k.a), ctr)) < 0.35 && V3.dot(V3.norm(k.n), n) > 0.8);
        if (!q) cl.push(q = { c: [0, 0, 0], n: [0, 0, 0], a: 0 });
        q.c = V3.add(q.c, V3.scale(ctr, area)); q.n = V3.add(q.n, V3.scale(n, area)); q.a += area;
      }
      for (const k of cl) {
        if (k.a < 0.02) continue;
        const c = V3.scale(k.c, 1 / k.a), n = V3.norm(k.n);
        for (const M of g.mats) {
          this.screens.push({
            p: [M[0] * c[0] + M[4] * c[1] + M[8] * c[2] + M[12], M[1] * c[0] + M[5] * c[1] + M[9] * c[2] + M[13], M[2] * c[0] + M[6] * c[1] + M[10] * c[2] + M[14]],
            n: V3.norm([M[0] * n[0] + M[4] * n[1] + M[8] * n[2], M[1] * n[0] + M[5] * n[1] + M[9] * n[2], M[2] * n[0] + M[6] * n[1] + M[10] * n[2]]),
            a: k.a,
          });
        }
      }
    }
  }

  // shade geometry for one window (no upload when batch = true)
  applyShade(i, level, batch) {
    const w = this.layout.windows[i];
    const S = this.shell.shades, G = this.gl;
    const put = (mesh, j, m) => { if (batch) mesh.idata.set(m, j * 20); else G.setMatrix(mesh, j, m); };
    if (w.electric) {
      const js = S.sheer.list.indexOf(i), jb = S.blackout.list.indexOf(i);
      const ms = shadeMats(w, level >= 1 ? 1 : 0, 0), mb = shadeMats(w, level >= 2 ? 1 : 0, -0.012);
      put(S.sheer.panel, js, ms.panel); put(S.sheer.rail, js, ms.rail);
      put(S.blackout.panel, jb, mb.panel); put(S.blackout.rail, jb, mb.rail);
    } else {
      const j = S.manual.list.indexOf(i);
      const m = shadeMats(w, [0, 0.5, 1][level], 0);
      put(S.manual.panel, j, m.panel); put(S.manual.rail, j, m.rail);
    }
  }
  setWindow(i, level) {
    this.winLevels[i] = level;
    this.applyShade(i, level, false);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  setAllWindows(level) {
    this.globalShade = level;
    for (let i = 0; i < this.winLevels.length; i++) { this.winLevels[i] = level; this.applyShade(i, level, true); }
    const S = this.shell.shades, G = this.gl;
    for (const k of ['manual', 'sheer', 'blackout']) for (const m of [S[k].panel, S[k].rail]) G.setInstancesRaw(m, m.idata, m.instances);
    this.updateWindowLUT();
    this.shadowDirty = true;
  }
  updateSheerTint() {
    const k = SKIES[this.sky].sheer;
    const m = this.shell.shades.sheer.panel;
    for (let i = 0; i < m.instances; i++) { m.idata[i * 20 + 16] = k; m.idata[i * 20 + 17] = k; m.idata[i * 20 + 18] = k; }
    this.gl.setInstancesRaw(m, m.idata, m.instances);
  }
  updateWindowLUT() {
    // QA r3: 4096 texels (1.4 cm, was 5.8 cm) and 0 between the windows: the skin is opaque, so the sun only enters
    // through a pane (was 0.92 everywhere, leaving the shadow map alone to stop it: hairline streaks on the seat backs,
    // q15). Rows 0 / 1 (left / right): rgb = shade transmittance over the glass +-0.127 m (CAB.win.w, 10 in [V]) plus
    // 3 cm, alpha = the reveal glow, full over +-0.22 m and cosine-feathered to 0 at +-0.30 m (was a hard 0.48 m block:
    // pale rectangles round each window, from_shell 2). QA r1 (light): row 2 = zone row, r / g = |dz| / half-width to
    // the nearest left / right pane (/4; the shader gates the sun with a rounded-pane superellipse, no hard z edge),
    // b = 1 under the outboard bins / lens (seat zones, as 08_bins builds them; eased over 0.25 m at the zone ends)
    // QA r2 (light): row 3 = shade row, r / g = the left / right shade transmittance / 0.92 over the +-0.30 m reveal span
    // (mainFS nearPane: a closed shade keeps the lens / band light of the wall round it; from_shell w10a)
    const N = 4096, d = new Uint8Array(N * 4 * 4);
    const z0 = this.ao ? this.ao.min[2] : 2.6, z1 = z0 + 59.2, dz = (z1 - z0) / N, hw = CAB.win.w / 2;
    for (let x = 0; x < N; x++) {
      const z = z0 + (x + 0.5) * dz, o = (2 * N + x) * 4;
      d[o] = d[o + 1] = 255;
      let m = 0;
      for (const zn of this.layout.zones) {
        if (zn.type !== 'seat') continue;
        const e = clamp((z - zn.z0 + 0.10) / 0.25, 0, 1) * clamp((zn.z1 + 0.10 - z) / 0.25, 0, 1);
        m = Math.max(m, e * e * (3 - 2 * e));
      }
      d[o + 2] = Math.round(m * 255);
    }
    let open = 0;
    this.layout.windows.forEach((w, i) => {
      const lv = this.winLevels[i];
      const T = SHADE_STATE.T(w, lv);
      open += SHADE_STATE.open(w, lv);
      const r = w.side > 0 ? 1 : 0;
      const a = Math.floor((w.z - 0.30 - z0) / dz), b = Math.ceil((w.z + 0.30 - z0) / dz);
      for (let x = Math.max(0, a); x <= Math.min(N - 1, b); x++) {
        const u = Math.abs(z0 + (x + 0.5) * dz - w.z), o = (r * N + x) * 4, oz = (2 * N + x) * 4 + r;
        const gw = u < 0.22 ? 1 : 0.5 + 0.5 * Math.cos(Math.PI * clamp((u - 0.22) / 0.08, 0, 1));
        if (u < hw + 0.03) for (let c = 0; c < 3; c++) d[o + c] = Math.max(d[o + c], Math.round(T[c] * 255));
        if (u < 0.30) d[(3 * N + x) * 4 + r] = Math.max(d[(3 * N + x) * 4 + r], Math.round(clamp(T[1] / 0.92, 0, 1) * 255));
        d[o + 3] = Math.max(d[o + 3], Math.round(gw * 255));
        d[oz] = Math.min(d[oz], Math.round(clamp(u / hw / 4, 0, 1) * 255));
      }
    });
    this.openness = open / Math.max(1, this.layout.windows.length);
    const gl = this.gl.gl;
    if (!this.winTex) {
      this.winTex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, this.winTex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    gl.bindTexture(gl.TEXTURE_2D, this.winTex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, N, 4, 0, gl.RGBA, gl.UNSIGNED_BYTE, d);
    this.winZ = [z0, z1];
  }

  sunDir() {
    const s = SKIES[this.sky];
    const el = s.sunEl * DEG, az = s.sunAz * DEG;
    return V3.norm([Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el)]);
  }

  // sun shadow map. QA r3: fitted to a cabin slice round the camera (zc +-11 m: ~4x the texel density of the whole
  // 59 m cabin, so the sun-patch edges no longer stair-step [V: omaat_f57 / f58 soft patches]); render() re-fits it when
  // the slice centre moves 2 m. No zc (studio) = the whole cabin. Seats outside the slice are left out of the pass
  renderShadow(zc) {
    const G = this.gl, gl = G.gl;
    const L = this.sunDir();
    const full = zc === undefined;
    const za = full ? 2.6 : clamp(zc - 11, 2.6, 50.6), zb = full ? 61.6 : za + 22;
    const center = [0, 1.2, (za + zb) / 2];
    const view = M4.lookAt(V3.add(center, V3.scale(L, 45)), center, Math.abs(L[1]) > 0.95 ? [0, 0, 1] : [0, 1, 0]);
    const corners = [];
    for (const x of [-3.1, 3.1]) for (const y of [-0.1, 2.6]) for (const z of [za, zb]) corners.push(M4.point(view, [x, y, z]));
    const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
    for (const c of corners) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], c[a]); mx[a] = Math.max(mx[a], c[a]); }
    const ex = mx[0] - mn[0], ey = mx[1] - mn[1];
    const W = Math.min(4096, G.maxTex);
    const H = clamp(Math.ceil((W * ey / ex) * 1.15 / 64) * 64, 256, Math.min(2048, G.maxTex));
    if (!this.shadow || this.shadow.w !== W || this.shadow.h !== H) this.shadow = G.shadowTarget(W, H);
    const proj = M4.ortho(mn[0] - 0.05, mx[0] + 0.05, mn[1] - 0.05, mx[1] + 0.05, -mx[2] - 1, -mn[2] + 1);
    this.shadowMat = M4.mul(proj, view);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.shadow.fb);
    gl.viewport(0, 0, W, H);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.POLYGON_OFFSET_FILL);
    gl.polygonOffset(2.0, 3.0);
    G.use(this.progs.depth);
    G.set('u_viewProj', this.shadowMat);
    for (const g of Object.values(this.seatGroups)) {
      let buf = g.master, n = g.n;
      if (!full) {
        buf = g.hiBuf || (g.hiBuf = new Float32Array(g.n * 20)); n = 0;
        for (let i = 0; i < g.n; i++) {
          const o = i * 20, z = g.master[o + 14];
          if (g.master[o + 13] > -10 && z > za - 1.5 && z < zb + 1.5) { buf.set(g.master.subarray(o, o + 20), n * 20); n++; }
        }
      }
      G.setInstancesRaw(g.hi, buf, n); if (g.lo) G.setInstancesRaw(g.lo, g.master, 0); g.dirty = true;
    }
    for (const m of this.opaque) if (m.castShadow && m.visible) G.draw(m);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.enable(gl.CULL_FACE);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.shadowDirty = false;
    this.shadowZ = full ? null : zc;
  }

  render(cam, w, h, time) {
    const G = this.gl, gl = G.gl;
    G.stats.calls = 0; G.stats.tris = 0;
    const sky = SKIES[this.sky], mood = MOODS[this.mood];
    const zc = clamp(cam.pos[2] + cam.fwd[2] * 5, 2.6, 61.6);   // slice centre 5 m ahead of the eye
    if (this.shadowDirty || this.shadowZ == null || Math.abs(zc - this.shadowZ) > 2) this.renderShadow(zc);
    const lc = this.lodCam;
    const moved = !lc || V3.len(V3.sub(lc.pos, cam.pos)) > 0.35 || V3.dot(lc.fwd, cam.fwd) < 0.985 || lc.xray !== this.xray;
    if (moved || Object.values(this.seatGroups).some((g) => g.dirty)) {
      const cosCull = Math.cos(Math.min(Math.PI * 0.95, cam.halfDiag + 0.35));
      updateSeatLOD(G, this.seatGroups, cam, { cosCull: this.xray ? -2 : cosCull, near: this.xray ? 0 : 9.5 });
      this.lodCam = { pos: [...cam.pos], fwd: [...cam.fwd], xray: this.xray };
    }
    gl.viewport(0, 0, w, h);
    if (this.xray) gl.clearColor(0.043, 0.07, 0.125, 1); else gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    const vp = M4.mul(cam.proj, cam.view);
    const L = this.sunDir();
    const op = this.openness ?? 1;
    const winExp = this.xray ? 1 : 1 + ((sky.winExp || 1) - 1) * (1 - clamp((Math.abs(cam.pos[0]) - 2.0) / 0.45, 0, 1));
    const winGlow = sky.winGlow.map((v) => v * (0.15 + 0.85 * op));
    const P = this.progs.main;
    G.use(P);
    G.set('u_viewProj', vp);
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_sunCol', sky.sun);
    G.set('u_shadowMat', this.shadowMat);
    G.tex('u_shadow', 0, this.shadow.tex);
    G.set('u_shadowTexel', [1 / this.shadow.w, 1 / this.shadow.h]);
    const k = mood.k;
    G.set('u_hemiTop', mood.hemiTop.map((v) => v * k));
    G.set('u_hemiBot', mood.hemiBot.map((v) => v * k));
    G.set('u_wash', mood.wash);
    G.set('u_led', mood.led);
    G.set('u_sideLed', mood.sideLed || mood.led);
    G.set('u_vault', mood.vault || mood.led);
    G.set('u_lowTint', mood.lowTint || [1, 1, 1]);
    G.set('u_aoTune', [AO_TUNE.hemi, AO_TUNE.bounce]);
    const fz = this.layout.zones.find((zn) => zn.cls === 'F');
    G.set('u_fZone', fz ? [fz.z0, fz.z1, AO_TUNE.fLift] : [0, 0, 0]);
    G.set('u_bandCut', mood.bandCut ?? 0.65); G.set('u_sideLow', mood.sideLow ?? 0.4); G.set('u_sideWall', mood.sideWall || [1, 1, 1]);
    G.set('u_lowGain', mood.lowGain ?? 1); G.set('u_monFill', mood.monFill || [0, 0, 0]); G.set('u_cove', LIGHT_TUNE.cove * (mood.cove ?? 1)); G.set('u_sheen', LIGHT_TUNE.sheen);
    G.set('u_toe', mood.toe ?? 0);
    G.set('u_extBounce', [0, 0, 0]);
    // reading-light pools: the 8 lit lamps nearest the eye [A: count, a phone-sized loop]
    const sp = new Float32Array(32), st = new Float32Array(32);
    if (mood.readingLights && !this.xray) {
      const near = this.spots.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { sp.set([...q.p, 1], i * 4); st.set([...q.t, 0], i * 4); });
    }
    G.set('u_spotP', sp); G.set('u_spotT', st);
    G.set('u_spotCol', [1.0, 0.85, 0.65].map((v) => v * 0.5));   // warm lamp colour [V: tlfl_IMG_9377], gain [A]
    // seat mood strips light the console top / footwell only in the dimmed moods (#ffd9a0 x 0.25 = SEATMAT.moodGlow)
    const spp = new Float32Array(32), spa = new Float32Array(32);
    if (mood.strips && !this.xray) {
      const near = this.strips.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 8);
      near.forEach(([, q], i) => { spp.set([...q.p, 1], i * 4); spa.set([...q.a, 0], i * 4); });
    }
    G.set('u_stripP', spp); G.set('u_stripA', spa);
    G.set('u_stripCol', [0.25, 0.173, 0.087]);
    // QA r2 (light): screen spill, the 6 screens nearest the eye; colour = the mean IFE picture radiance: the screen
    // emission (SEATMAT.screen e 0.9 x 4 x screenGain, mainFS layer 13) x a mean picture of ~0.75 x [0.30, 0.40, 0.55]
    // (cool-neutral), i.e. 2.7 x screenGain x [0.30, 0.40, 0.55], x scrSpill (Night / Blue 1, Dining 0.5, else 0)
    // [D: the raters' hue; x1 left the nF03 housing L12 vs ml_IMG_20200208_1919534 L32]
    const scp = new Float32Array(24), scn = new Float32Array(24);
    const spill = this.xray ? 0 : mood.scrSpill || 0;
    if (spill > 0) {
      const near = this.screens.map((q) => [V3.len(V3.sub(q.p, cam.pos)), q]).sort((a, b) => a[0] - b[0]).slice(0, 6);
      near.forEach(([, q], i) => { scp.set([...q.p, q.a], i * 4); scn.set([...q.n, 0], i * 4); });
    }
    G.set('u_scrP', scp); G.set('u_scrN', scn);
    G.set('u_scrCol', [0.30, 0.40, 0.55].map((v) => v * 2.7 * (mood.screenGain || 0.8) * spill));
    G.set('u_fillLift', mood.fillLift ?? 1); G.set('u_lensCore', mood.lensCore || [0, 0, 0]); G.set('u_vaultE', mood.vaultE || [0, 1]);
    G.set('u_winGlow', winGlow);
    G.tex('u_ao', 1, this.ao.tex, gl.TEXTURE_3D);
    G.set('u_aoMin', this.ao.min);
    G.set('u_aoSize', this.ao.size);
    G.tex('u_detail', 2, this.tex.detail, gl.TEXTURE_2D_ARRAY);
    G.tex('u_photo', 5, this.tex.photo, gl.TEXTURE_2D_ARRAY); G.set('u_photoOn', PHOTO_PIX ? 1 : 0);
    const lp = new Float32Array(N_LAYERS * 4);
    for (const [kk, v] of Object.entries(LAYER_PARAMS)) lp.set(v, +kk * 4);
    G.set('u_layer', lp);
    G.tex('u_atlas', 3, this.tex.atlas);
    G.set('u_screenStep', ATL.screenStep);
    G.set('u_emisGain', mood.emisGain ?? 1.0);
    G.set('u_screenGain', mood.screenGain || 0.8);   // QA r2 night 0.35 -> 0.6: the screen stays the brightest element [V: ucr_room-night-lighting]
    G.tex('u_win', 4, this.winTex);
    G.set('u_winZ', this.winZ);
    G.set('u_R', CAB.R + 0.10);
    G.set('u_yc', CAB.yc); G.set('u_winY', [CAB.win.yc, CAB.win.h / 2]);
    G.set('u_exposure', mood.exposure);
    G.set('u_fill', this.fill ?? 0.45);   // QA r1: 0.7 flattened AO and the ceiling-to-floor falloff [V: c_27312 shell gradients]
    G.set('u_exterior', 0);
    G.set('u_skyTop', sky.skyTop);
    G.set('u_skyBot', sky.skyBot);
    G.set('u_detailOn', this.q === 'low' ? 0 : 1);
    for (const m of this.opaque) {
      if (this.xray && (m.layer === 'upper')) continue;
      G.draw(m);
    }
    // QA r3: the THE Room mood strips are lit only in the dimmed moods (day photos c_27312 / ff_seat-with-door-closed
    // show nothing lit under the monitor; ucr_room-night-lighting at night does) [V]; PSU amber lenses with the reading lamps
    if (mood.strips) G.draw(this.stripMesh);
    if (mood.readingLights && !this.xray) G.draw(this.psuLensMesh);
    if (!this.xray) {
      G.set('u_exterior', 1);
      G.set('u_exposure', winExp);
      // exterior: cloud-deck bounce and a lower sun (from_exterior 1 / 6: the sun side of the cowl saturated at 5.2)
      G.set('u_extBounce', sky.extBounce);
      G.set('u_sunCol', sky.sun.map((v) => v * sky.extSun));
      // up to two exterior lights with a `light` gain light the airframe at night, blinking like their glow sprite
      const pp = new Float32Array(8), pc = new Float32Array(6);
      let np = 0;
      for (const l of this.ext.lights) {
        if (!l.light || !sky.night || np > 1) continue;
        const on = l.blink > 1.5 ? ((time * 0.9 + l.blink) % 1 >= 0.92 ? 1 : 0) : 1;
        pp.set([...l.p, 1], np * 4); pc.set(l.c.map((v) => v * l.light * on), np * 3); np++;
      }
      G.set('u_extPtP', pp); G.set('u_extPtC', pc);
      G.draw(this.ext.mesh);
      G.set('u_extBounce', [0, 0, 0]); G.set('u_extPtP', new Float32Array(8));   // the studio (same program) keeps its plain fill
    }
    G.set('u_toe', 0); G.set('u_fillLift', 1); G.set('u_vaultE', [0, 1]);   // ... and its plain tone, fill lift and vault (14_studio renders through the same program)
    gl.depthFunc(gl.LEQUAL);
    gl.depthMask(false);
    const S = this.progs.sky;
    G.use(S);
    G.set('u_invViewProj', M4.invert(vp));
    G.set('u_camPos', cam.pos);
    G.set('u_sunDir', L);
    G.set('u_time', time);
    G.set('u_zenith', sky.zenith); G.set('u_horizon', sky.horizon); G.set('u_haze', sky.haze); G.set('u_skyK', sky.skyK || 0);
    G.set('u_sunTint', sky.sun.map((v) => v / 5));
    G.set('u_night', sky.night);
    G.set('u_cloudLit', sky.cloudLit); G.set('u_cloudShade', sky.cloudShade);
    G.set('u_exposure', winExp); G.set('u_toe', mood.toe ?? 0);
    G.set('u_sunVis', sky.sunVis);
    G.tex('u_cloud', 0, this.tex.cloud);
    gl.bindVertexArray(this.emptyVAO);
    if (!this.xray) gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.depthFunc(gl.LESS);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.DST_COLOR, gl.ZERO);
    gl.disable(gl.CULL_FACE);
    G.use(this.progs.glass);
    G.set('u_viewProj', vp);
    G.draw(this.shell.meshes.glassR); G.draw(this.shell.meshes.glassL);
    gl.blendFunc(gl.ONE, gl.ONE);
    G.use(this.progs.glow);
    G.set('u_viewProj', vp);
    G.set('u_camRight', cam.right); G.set('u_camUp', cam.up);
    G.set('u_time', time);
    if (sky.night && !this.xray) G.draw(this.glowMesh);
    if (mood.readingLights) G.draw(this.readingMesh);
    gl.enable(gl.CULL_FACE);
    gl.disable(gl.BLEND);
    gl.depthMask(true);
  }
}
