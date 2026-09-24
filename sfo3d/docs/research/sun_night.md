# Sun, Moon, sky and night appearance at SFO: verified ephemeris, sky options, airport night lighting and exposure

Research deliverable for the lighting, day/night and weather work (task `sun_night`). It is research only: no code
in `js/` or data in `data/` was changed. It adds:

- `tools/env/ephemeris.mjs`: a pure-JS Sun/Moon ephemeris. It covers azimuth and elevation, refraction, rise/set,
  civil/nautical/astronomical twilight, Moon phase, illuminated fraction and bright-limb angle, and natural
  illuminance (USNO Circular 171). It also has EV100 exposure helpers and a `skyState(date)` call for the renderer.
  Minified it is 11.4 KB (5.4 KB gzip).
- `tools/env/test_ephemeris.mjs`: a Node test (`node tools/env/test_ephemeris.mjs`) with 33 checks against NOAA, JPL
  Horizons, USNO and Meeus. **All pass.**
- `tools/env/fixtures/ephemeris_ref.json` holds the reference numbers, with the URL, fetch date and SHA-256 of every
  raw file. It is built by `tools/env/build_ephemeris_fixtures.mjs` from raw files that
  `tools/env/fetch_ephemeris_refs.py` downloads into `refs/cache/sun_night/` (gitignored).

Written 24 Sep 2026. Every source was fetched that day unless a note says otherwise.

**Provenance codes** (the same idea as `airfield_lighting.md` and `weather.md`):

| Code | Meaning |
|---|---|
| **V** | Verified. Quoted from, or computed with, the primary source cited next to it. |
| **T** | Verified numerically by `test_ephemeris.mjs` against an independent reference. |
| **obs** | Observed or measured by us, in a figure or in code. |
| **inf** | Inferred. This is our reasoning or choice, not a source's statement. |
| **NV** | Not verified. The source could not be reached or does not say. The item needs the owner or a follow-up. |

---------------------------------------------------------------------------------------------------------------------

## 1. Summary

1. **Ephemeris (T).** `ephemeris.mjs` matches **JPL Horizons (DE441, topocentric at the SFO ARP)** over 125 hourly epochs on 5 dates.

   | Body | Max elevation error | Max azimuth error (× cos el) | Other checks |
   |---|---|---|---|
   | Sun | 0.0066° | 0.0070° | |
   | Moon | 0.0008° | 0.0010° | illuminated fraction ±0.008 percentage points; phase angle ±0.007° |

   The Sun is off by at most 1/80 of its own diameter. It also matches **USNO's 2026 SFO tables**:
   - 730 sunrise/sunset times, 2 × 730 civil and nautical twilight times, 730 astronomical twilight times and 705 moonrise/moonset times;
   - every one agrees within 1 minute, and 97.4–98.9 % agree to the minute;
   - all 50 principal Moon phases agree within 2 minutes.

   In NOAA mode it reproduces the **NOAA Solar Calculator's own code** to 2 × 10⁻⁷°.
2. **The NOAA algorithm is good enough for the Sun; the current app lacks refraction (T, obs).**
   - The app's `solarPosition` (`js/world/textures.js:111`) is the NOAA algorithm without refraction. Airless, it is within 0.014° of Horizons.
   - Without refraction, the app's Sun reaches the horizon **2.9 min before the real apparent sunset** (23 Sep 2026). Refraction is 29′ at the horizon.
   - The "dusk"/"night" light modes (`js/live/app.js:114`) hard-code UTC−7. They are 1 h wrong from November to March.
3. **Twilight light levels (V: USNO Circular 171).** The public-domain USNO illuminance model gives these values for a clear sky:

   | Sun elevation | Horizontal illuminance |
   |---|---|
   | 0° | 984 lx |
   | −4° | 24 lx |
   | −6° (end of civil twilight) | 3.0 lx |
   | −12° | 0.004 lx |

   - Full Moon at the zenith: 0.40 lx.
   - Night-sky floor: 0.0005 lx.
   - Our transcription reproduces the Circular's printed sample run within 0.3 %–2.3 %.
   - This gives the renderer physically grounded ambient light, exposure and lamp-switching thresholds.
4. **Sky (V, obs).** For the r186 WebGPU renderer the best option is **@takram/three-atmosphere 0.19.1**.
   - It uses Bruneton precomputed scattering with Hillaire's multiple-scattering LUT.
   - It has a WebGPU/TSL path, and generates its LUTs at runtime on WebGL2 too.
   - It includes aerial perspective, the Moon with its phase, stars and light shafts.
   - **Licence:** the package is MIT. It also carries BSD-3-Clause (Bruneton), MIT (Epic Games) and Apache-2.0 (Intel) notices.
   - **Size:** 84.5 KB minified, 25.3 KB gzip for the `webgpu` entry with three.js external. Import resolution against three 0.186.0 is clean.
   - **Caveats:**
     - **by default it downloads `stars.bin` from media.githubusercontent.com**, which the artifact CSP blocks, so self-host the file;
     - its root entry pulls the WebGL/`postprocessing` build;
     - it has not been run on a GPU here.
   - three.js's own `SkyMesh` (Preetham) has no night sky, no aerial perspective, and an exposure constant baked in.
5. **Night sky over SFO (V, obs coarse).**
   - Natural sky background: 22.0 mag/arcsec² = 174 µcd/m² (Falchi et al. 2016).
   - The Bay Area sits in the atlas's red–magenta classes: artificial light is 10–41 × natural, 17.9–19.4 mag/arcsec². We read this off the published continental figure; we did not query the raster.
   - The Milky Way is not visible. Overcast skies over a city can be about 10 × brighter than clear skies (Kyba et al. 2011, Berlin).
   - **The atlas data are CC BY-NC 4.0**, and the raster download needs a request form. **NV** for a per-pixel SFO value.
6. **Aircraft lights (V: 14 CFR 25.1385–25.1401, 91.209, AIM 4-3-24).**
   - Position lights:
     - red to the left and green to the right, each visible over 110° from dead ahead;
     - white aft over 140°;
     - minimum 40/30/5 cd in the horizontal plane, a vertical-angle factor table, and overlap maxima.
   - Anti-collision lights:
     - aviation red or white;
     - **40–100 flashes per minute**;
     - at least **400 cd effective** within 0–5° of the horizontal, over ±75° of coverage;
     - Blondel–Rey effective intensity.
   - Usage (AIM, effective 9 Jul 2026, Change 3):
     - the beacon is on whenever engines run;
     - nav, anti-collision and logo lights go on before taxi;
     - the taxi light is on while moving and off when stopped;
     - all lights except landing lights go on when entering the runway;
     - landing lights go on at takeoff clearance, and below 10,000 ft.
   - An example LED landing light (Honeywell, 737NG/757/767/777) is 770,000 cd, 15° × 16°.
7. **Apron floodlight lamp type at SFO: NV.** No SFO or Airport Commission source states whether the apron masts are sodium, metal halide or LED.
   - The only SFO LED retrofit found is the Rental Car Center: 2,000+ metal-halide fixtures replaced with LED (SFPUC, 22 Jan 2025).
   - Harvey Milk Terminal 1 Boarding Area B uses LED luminous ceilings inside (QTL). Its apron lighting is not described.
   - We need a night photo from the owner, or an SFO document.
8. **Exposure (V: Frostbite 2014, Filament).**
   - EV100 = log₂(L·100/12.5). Saturation-based exposure = 1/(1.2·2^EV100).
   - Using the Circular 171 illuminance on an 18 % grey surface:

     | Scene | EV100 |
     |---|---|
     | Noon | about 15 (matches "sunny 16", EV 14.97) |
     | Sunset | 8.8 |
     | End of civil twilight | 0.5 |
     | Full-Moon night | −2.5 to −4 |
     | A 54 lx floodlit apron | 4.6 |

   - three.js r186 has **no auto-exposure** (verified by grep). Implement Filament/Frostbite-style metering: histogram or log-average, then Pattanaik adaptation. Clamp the EV range so night stays night.

---------------------------------------------------------------------------------------------------------------------

## 2. Sun and Moon positions (task a)

### 2.1 Algorithms in `ephemeris.mjs`

| Quantity | Method | Source |
|---|---|---|
| Sun ecliptic longitude, declination, RA, equation of time, distance | NOAA spreadsheet/web-calculator series (Meeus ch. 25 low accuracy) | [NOAA main.js](https://gml.noaa.gov/grad/solcalc/main.js), [calcdetails](https://gml.noaa.gov/grad/solcalc/calcdetails.html) (V) |
| Hour angle ("accurate" mode) | Apparent sidereal time: GMST [M 12.4] + Δψ cos ε | Meeus, *Astronomical Algorithms* 2nd ed. |
| Hour angle ("noaa" mode) | True solar time from the equation of time, exactly as NOAA | NOAA main.js `calcAzEl` (V) |
| Time scale | ΔT = TT − UT1 = 32.184 + 37 − (−0.015) = **69.2 s**. The Espenak–Meeus polynomials are used before 2017. | [IERS Bulletin A](https://datacenter.iers.org/data/latestVersion/bulletinA.txt): "TAI-UTC = 37.000 000 seconds"; UT1−UTC −0.0148 s on 25 Sep 2026; "There will NOT be a leap second … at the end of December 2026" (V) |
| Moon longitude, latitude, distance | Meeus ch. 47, the truncated ELP-2000/82 series: Tables 47.A/B, 60 + 60 terms, plus the A1–A3 and E terms | Tables transcribed programmatically from the MIT package [`astronomia` 4.2.0](https://registry.npmjs.org/astronomia/-/astronomia-4.2.0.tgz) `src/moonposition.js`. Reproduces Meeus Example 47.a to 3 × 10⁻⁷° (T). |
| Nutation | Meeus ch. 22 low-accuracy (4 terms, 0.5″) | Meeus |
| Topocentric parallax | Meeus ch. 40 on WGS-84 (ρ sin φ′, ρ cos φ′, h = 4 m) | Meeus. The Moon's parallax is up to about 1°. |
| Refraction | Default: Sæmundsson/Bennett [M 16.4] × (P/1010)(283/(273+T)), at 1010 hPa and 10 °C. Alternative: NOAA's piecewise formula. | Meeus; NOAA calcdetails |
| Phase angle and illuminated fraction | Angle at the Moon between the Sun and the observer (3-D vectors); k = (1 + cos i)/2 [M 48.1] | Meeus 48; reproduces Example 48.a (i = 69.0756°) to 4 × 10⁻⁵° (T) |
| Bright-limb position angle χ, parallactic angle q | [M 48.5], [M 14.1]. χ − q is the bright limb measured from the zenith, which orients the lit side in the rendered sky. | Meeus |
| Rise/set and twilight | Scan the day in 10 min steps and bisect to 0.5 s. Sun: geometric centre at −50′, −6°, −12°, −18°. Moon: geocentric zenith distance 90.5666° + SD − HP. | [USNO "Rise, Set, and Twilight Definitions"](https://aa.usno.navy.mil/faq/RST_defs) (V, quoted in §2.3) |
| Principal phases | The instant the geocentric apparent Moon − Sun longitude is 0/90/180/270° | Almanac definition |

NOAA states its own accuracy on [calcdetails](https://gml.noaa.gov/grad/solcalc/calcdetails.html) (V):
> "The sunrise and sunset results are theoretically accurate to within a minute for locations between +/- 72° latitude."

NOAA also warns:
> "Please be advised that the NOAA/GML Solar Calculator is no longer actively supported or maintained by our team."

This is why the independent Horizons and USNO checks below matter.

### 2.2 Verification results (T)

Data sources for the checks:
- **Horizons:** `ssd.jpl.nasa.gov/api/horizons.api`, observer table, `SITE_COORD='-122.3754167,37.6188056,0.004'` (SFO ARP, 13.1 ft). Quantities 2, 4, 10, 13, 20 and 24, hourly for 24 h. The header reads "Target body name: Moon (301) {source: DE441}", "EOP file: eop.260923.p261220".
- **Dates:** 11 Feb (equation of time near its minimum), 21 Jun (solstice), **23 Sep 2026** (equinox, and the snapshot date), 3 Nov (equation of time near its maximum) and 21 Dec (solstice).

| Check (n) | Max error | RMS | Tolerance |
|---|---|---|---|
| NOAA mode vs NOAA `main.js`: elevation / azimuth (125) | 4.4e-8° / 2.1e-7° | — | 1e-6° |
| Sunrise/sunset/noon vs NOAA `calcSunriseSet`/`calcSolNoon` (15) | 14.6 s | 5.5 s | 30 s |
| Sun elevation, airless, vs Horizons (125) | **0.0066°** | 0.0024° | 0.01° |
| Sun azimuth × cos(el), airless, vs Horizons | 0.0070° | 0.0028° | 0.01° |
| Sun, NOAA mode, airless, vs Horizons (what the app uses today) | 0.0138° el / 0.0128° az | 0.0055° | 0.02° |
| Sun apparent elevation (Bennett) vs Horizons refracted, el > 0 (58) | 0.0063° | — | 0.05° |
| Sun angular diameter vs Horizons | 0.97″ | — | 1″ |
| Moon elevation, airless, vs Horizons (125) | **0.0008°** | 0.0004° | 0.01° |
| Moon azimuth × cos(el) vs Horizons | 0.0010° | 0.0005° | 0.01° |
| Moon apparent elevation vs Horizons refracted, el > 5° (56) | 0.0008° | — | 0.01° |
| Moon illuminated fraction vs Horizons Illu% | 0.008 percentage points | — | 0.1 |
| Moon phase angle vs Horizons S-T-O | 0.007° | — | 0.02° |
| Moon angular diameter / topocentric distance vs Horizons | 0.2″ / 42 km | — | 0.5″ / 50 km |
| USNO 2026 sunrise/sunset (730) | 1 min (97.7 % to the minute) | — | 1 min |
| USNO civil / nautical / astronomical twilight (730 each) | 1 min (98.4 / 98.9 / 97.4 %) | — | 1 min |
| USNO moonrise/moonset (705) | 1 min (98.2 %) | — | 1 min |
| USNO principal phases (50) | 1.93 min; ours − USNO mean +0.65 min | — | 2 min |

Notes on the table:
- **Phase times.** The +0.65 min mean is consistent with USNO printing truncated minutes (**inf**). The spread comes from the low-precision Sun longitude (≤ 0.007° is about 50 s of elongation).
- **Refraction.** Horizons states its refraction assumes "yellow light, 10 C, 1010 mb". Our Bennett default uses the same conditions.

**Per date: sunrise and twilight in local time.** USNO values are from its one-day API (`tz=-8&dst=true`). "Max |Δel|" is the worst Horizons deviation that local day.

| Date (zone) | NOAA code rise / noon / set | ours rise / transit / set | USNO rise / transit / set | ours civil dawn / dusk | USNO civil | Sun max abs Δel, NOAA mode / accurate | Moon max abs Δel |
|---|---|---|---|---|---|---|---|
| 2026-02-11 (PST) | 07:03.24 / 12:23.73 / 17:44.70 | 07:03.23 / 12:23.70 / 17:44.66 | 07:03 / 12:24 / 17:45 | 06:36.24 / 18:11.67 | 06:36 / 18:12 | 0.0138° / 0.0066° | 0.0003° |
| 2026-06-21 (PDT) | 05:48.38 / 13:11.29 / 20:34.41 | 05:48.40 / 13:11.41 / 20:34.41 | 05:48 / 13:11 / 20:34 | 05:17.15 / 21:05.65 | 05:17 / 21:06 | 0.0037° / 0.0029° | 0.0008° |
| 2026-09-23 (PDT) | 06:58.34 / 13:01.95 / 19:04.59 | 06:58.33 / 13:01.75 / 19:04.56 | 06:58 / 13:02 / 19:05 | 06:32.20 / 19:30.65 | 06:32 / 19:31 | 0.0060° / 0.0022° | 0.0008° |
| 2026-11-03 (PST) | 06:36.85 / 11:53.01 / 17:08.71 | 06:36.92 / 11:53.06 / 17:08.75 | 06:37 / 11:53 / 17:09 | 06:09.67 / 17:35.99 | 06:10 / 17:36 | 0.0112° / 0.0018° | 0.0004° |
| 2026-12-21 (PST) | 07:20.87 / 12:07.50 / 16:54.62 | 07:20.88 / 12:07.74 / 16:54.61 | 07:21 / 12:08 / 16:55 | 06:51.52 / 17:23.97 | 06:52 / 17:24 | 0.0042° / 0.0011° | 0.0008° |

The fractional minutes are ours (for example 07:03.24 = 07:03 and 14 s). USNO rounds to whole minutes.

**Snapshot instant** (23 Sep 2026, 10:51 PDT = 17:51 UTC, the time of `data/snapshot.js`):
- Sun: az 133.781°, apparent el 41.586° (accurate mode).
- USNO's celestial-navigation API gives Hc 41.5671° and Zn 133.7795°. Hc is geocentric; minus the 0.0018° parallax (the API's `pa`) it becomes 41.5652°. Our airless topocentric value is 41.5671°.
- Moon: below the horizon (el −65.7°), 90.6 % lit, waxing gibbous. Moonrise 17:39 PDT; full Moon 26 Sep 09:49 PDT (USNO).

### 2.3 Definitions used (V, USNO [RST_defs](https://aa.usno.navy.mil/faq/RST_defs))

- Sunrise and sunset:
  > "For computational purposes, sunrise or sunset is defined to occur when the geometric zenith distance of center of the Sun is 90.8333 degrees … obtained by adding the average apparent radius of the Sun (16 arcminutes) to the average amount of atmospheric refraction at the horizon (34 arcminutes)."
- Civil twilight:
  > "Civil twilight is defined to begin in the morning, and to end in the evening when the center of the Sun is geometrically 6 degrees below the horizon. … after the end of civil twilight, artificial illumination is normally required to carry on ordinary outdoor activities."
- Nautical twilight (−12°):
  > "the horizon is still visible even on a Moonless night"
- Astronomical twilight (−18°):
  > "scattered light from the Sun is less than that from starlight and other natural sources."
- Moonrise:
  > "the geometric zenith distance of the center of the Moon is 90.5666 degrees + Moon's apparent angular radius - Moon's horizontal parallax."
- Accuracy:
  > "even under ideal conditions (e.g., a clear sky at sea) the times computed for rise or set may be in error by a minute or more."

  So a 1-minute agreement is the meaningful limit.

### 2.4 What the current code does (obs, code inspection)

- **`js/world/textures.js:111` `solarPosition`.**
  - It uses NOAA's formulas with the hour angle from the equation of time, and **no refraction and no ΔT**. It is equivalent to our `mode:'noaa', refraction:'none'`: max 0.014° from Horizons, airless (T).
  - It is fine for shadows.
  - For the horizon: the apparent Sun centre sets **2.86 min later** than the app's (23 Sep, T). At the horizon the Sun is drawn 29′ too low, about one solar diameter. That is visible in sunset views.
- **`js/live/app.js:114` `lightDate`.**
  - Its `{day: 13.0, dusk: 19.45, night: 22.5}` "local solar-ish times" add a fixed 7 h (PDT). In PST (1 Nov – 8 Mar 2026) "dusk" falls 1 h after the intended time.
  - Use `sunEvents()` instead, for example dusk = civil dusk − 10 min.
- **Night blend.**
  - `app.js:146–148`: `nightF = sstep(6, -4, el)`, `dark = sstep(2, -10, el)`, and exposure 0.45 → 2.4. These are heuristics.
  - §3 gives the physical light levels to replace them.
- **Moon and stars.** Neither renderer draws a Moon or stars. `js/three/sky.js:179` has a constant night "skyFloor" (moon/city glow).

### 2.5 API summary (`tools/env/ephemeris.mjs`)

```js
import { SFO, sunPosition, moonPosition, sunEvents, moonEvents, moonPhases, naturalIlluminanceAt, skyState,
         ev100ForIlluminance, exposureFromEV100, directionWorld } from './tools/env/ephemeris.mjs';
sunPosition(date, SFO)             // {az, el (apparent), elTrue, ra, dec, distAU, eqTime, semidiameter, ha}
sunPosition(date, SFO, {mode:'noaa'})   // bit-for-bit the NOAA web calculator
moonPosition(date, SFO)            // + distKm, angularDiameter, phaseAngle, illuminatedFraction, phaseName, brightLimbZenithAngle
sunEvents(2026, 9, 23, -7)         // sunrise/sunset, civil/nautical/astronomical dawn+dusk, transit (Dates)
moonEvents(2026, 9, 23, -7)        // moonrise, moonset
moonPhases(t0, t1)                 // [{date, phase}]
skyState(date)                     // {sun, moon, phase:'day'|'civil'|'nautical'|'astronomical'|'night', sunDir, moonDir, illuminance}
directionWorld(az, el)             // [x east, y up, z south], same convention as js/world/textures.js sunVector
```

---------------------------------------------------------------------------------------------------------------------

## 3. Natural light levels: day, twilight, Moon, night (V: USNO Circular 171)

**Source.** P. M. Janiczek & J. A. DeYoung, *Computer Programs for Sun and Moon Illuminance with Contingent Tables
and Diagrams*, USNO Circular 171 (1987). It is a US Government work; the PDF is at the [Internet Archive DTIC_ADA182110](https://archive.org/details/DTIC_ADA182110). The model is transcribed from the FORTRAN listing:
- statements 660–805 on p. 20;
- `REFR` and `ATMOS` on pp. 22–23, checked on the page images and against the BASIC versions on pp. 32–34 and 39–41.

What the model is:
- Direct light uses a Bemporad air-mass fit and a Jones & Condit extinction coefficient.
- Skylight is empirical from Jones & Condit, extended with Brown's 12,000 measurements (1943–47) down to nautical twilight.
- The Moon uses the Lumme–Bowell phase function, with a topocentric distance factor.

Faithful details:
- The listing adds **0.0005 lx** for the night sky, while Appendix B says ".0003 lux". We follow the code.
- The authors' caveat:
  > "There are situations in which the calculated illuminance differs from the real light level by a factor of 10 or more"
  > "Illuminance is given in lux … formally accurate to one or two digits."
- Cloud divisors (Brown, quoted in Appendix B): "divided by two" for thin cloud over the Sun, "three" for average cloud, "ten" for dark stratus.

**Our reproduction of the Circular's sample run** (Figure 3: 58° N, 4° W, 11 May 1987, 22:15 UT):

| Quantity | Ours | Printed |
|---|---|---|
| Sun | 0.0284 lx | 0.0278 |
| Moon | 0.0316 lx | 0.0317 |
| Total | 0.0605 lx | 0.0600 |
| Moon illuminated | 97 % | 97 % |

The small differences come from our more accurate positions (T).

**Horizontal illuminance vs Sun elevation.** Clear sky, no Moon. EV100 is for an 18 % grey Lambertian surface.

| Sun el | 60° | 30° | 10° | 5° | 0° | −2° | −4° | −6° | −8° | −10° | −12° | −15° | −18° |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lux | 103,000 | 51,300 | 11,200 | 4,250 | 984 | 169 | 24.4 | 2.99 | 0.345 | 0.039 | 0.0049 | 0.0007 | 0.0005 |
| EV100 | 15.5 | 14.5 | 12.3 | 10.9 | 8.8 | 6.3 | 3.5 | 0.5 | −2.7 | −5.8 | −8.8 | −11.7 | −12.1 |
| EV100, average cloud (÷3) | 13.9 | 12.9 | 10.7 | 9.3 | 7.2 | 4.7 | 1.9 | −1.1 | −4.2 | −7.4 | −10.4 | −13.3 | −13.7 |

**Moon.**

| Moon | Illuminance |
|---|---|
| Full, at the zenith | 0.397 lx (EV100 −2.5) |
| Full, at 30° elevation | 0.157 lx |
| Full, at 10° elevation | 0.030 lx |
| Quarter, at 45° elevation | 0.017 lx |

**Useful thresholds** (the Sun elevation at which the model reaches a given illuminance; T, computed):
- 1000 lx at +0.04°;
- 100 lx at −2.6°;
- 54 lx (5 fc) at −3.2°;
- 32 lx (3 fc) at −3.7°;
- 10.8 lx (1 fc) at −4.8°;
- 5.4 lx (0.5 fc) at −5.5°;
- 1 lx at −7.0°;
- 0.01 lx at −11.3°.

The ASOS day/night photocell switches "between 0.5 and 3 foot candles (deep twilight)" (quoted in `weather.md` §3.2). By this model that is a Sun elevation of **−3.7° to −5.5°** (inf).

**Examples at SFO on 23–26 Sep 2026** (`skyState`, T/inf):

| UTC | Phase | Sun el | Moon | Illuminance | EV100 |
|---|---|---|---|---|---|
| 17:51 (snapshot) | day | +41.6° | below the horizon | 73,900 lx | 15.0 |
| 02:04 on the 24th | sunset | −0.1° | at 14° | 702 lx | 8.3 |
| 02:30 | civil | −5.2° | | 3.5 lx | 0.7 |
| 03:01 | nautical | −11.3° | | 0.041 lx | −5.7 |
| 26 Sep 08:00 | night | | full Moon at 53° | 0.20 lx | −3.5 |

---------------------------------------------------------------------------------------------------------------------

## 4. Physically based sky for three.js r186 WebGPU (task b)

### 4.1 Options compared

| | three.js `SkyMesh` (r186) | Our port `js/three/sky.js` | **@takram/three-atmosphere 0.19.1** |
|---|---|---|---|
| Model | Preetham analytic, with a "cutoffAngle" hack for the Earth's shadow (obs, source) | Single-scattering Rayleigh + Mie, 32/8 steps, precomputed to a 1024×512 equirect (port of the WebGL renderer) | Bruneton 4-D scattering LUT, with Hillaire's multiple-scattering LUT replacing the stepwise higher orders. By default it ray-marches in-scatter between the camera and objects ([WEBGPU.md](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/atmosphere/WEBGPU.md), V). |
| Units | Relative; `texColor … .mul( 0.04 )` exposure baked in (obs) | Relative (`sunI 20`) | Luminance (cd/m²) with `luminanceScale` for half floats; solar irradiance and radiance-to-luminance coefficients given (WEBGPU.md, V) |
| Night / twilight | The "nightsky" is a constant `vec3(0.1)·Fex`. No Moon or stars. | Constant floor colour | `SkyNode` renders "the sun, moon, and stars". 0.19.0 added "preliminary support for moonlight and scattering in a low light setup" (CHANGELOG, V). |
| Aerial perspective | None (fog only) | Exponential height fog with a sky-coloured in-scatter | `AerialPerspectiveNode` (post-process on colour and depth), plus `ShadowLengthNode` light shafts via epipolar sampling |
| Scene lighting | None | Hemisphere terms + PMREM | `AtmosphereLight` (sun and sky irradiance for built-in materials) and `SkyEnvironmentNode` (PMREM) |
| WebGPU / WebGL2 | WebGPU only (a `Sky` class exists for WebGLRenderer) | Both (TSL) | The `webgpu` entry works on both. `AtmosphereLUTNode` picks `AtmosphereLUTTexturesWebGPU` (compute) or `…WebGL` (render targets) (src, obs). It needs `three >= 0.182.0` (CHANGELOG 0.18.0). |
| Size | In three | Ours | 84,503 B minified / 25,320 B gzip (three external): atmosphere 58.0 KB + three-geospatial 26.3 KB (esbuild 0.28.2, obs) |
| Licence | MIT | Ours | MIT (© 2024 Shota Matsuda), "except where indicated otherwise". Headers inside: BSD-3-Clause (© 2017 Eric Bruneton, © 2008 INRIA), MIT (© 2020 Epic Games, Hillaire), Apache-2.0 (© 2017 Intel, `ShadowLengthNode`) (V, source headers). |

Takram details (V from the package):
- Dependencies are `@takram/three-geospatial` 0.9.1 (MIT) and `astronomy-engine` ^2.1.19 (MIT).
- npm lists version 0.19.1 as published 2026-05-06. Its CHANGELOG heading says "[0.19.1] - 2026-05-26". This is a cosmetic discrepancy.

Takram caveats (obs, **must handle**):
1. **Runtime downloads.** `constants.ts` sets `DEFAULT_STARS_DATA_URL` (and the WebGL precomputed-texture URL) to
   `https://media.githubusercontent.com/media/takram-design-engineering/three-geospatial/<sha>/packages/atmosphere/assets/stars.bin`.
   The artifact CSP blocks external fetches, and the standalone app should not depend on GitHub LFS. **Self-host `assets/stars.bin` (90,960 bytes).** The WebGPU path computes its LUTs at runtime, so the 8 MB `.bin` LUTs are not needed.
2. **Entry points.** The sun/moon direction helpers live in the root entry (`getSunDirectionECI`, `getMoonDirectionECI`, `getECIToECEFRotationMatrix`). That entry imports the WebGL build, which needs `postprocessing` (230.8 KB minified with it external). Use only `@takram/three-atmosphere/webgpu`.
   - Feed `sunDirectionECEF` and `moonDirectionECEF` from `ephemeris.mjs`: convert az/el to ENU, then to ECEF with `Ellipsoid.WGS84.getNorthUpEastFrame` (**inf**).
   - The stars need the ECI→ECEF rotation. Rz(GAST) from our `gmst()` + nutation is enough for rendering; it ignores precession of about 0.36° since J2000 (**inf**).
   - The Moon's surface orientation (`matrixMoonFixedToECEF`) needs a lunar rotation model. If we want the real libration, `astronomy-engine`'s `RotationAxis` costs 53 KB minified / 23.5 KB gzip for the subset takram uses (obs).
3. **Deep import.** It imports `three/src/nodes/core/NodeUtils.js`. The esbuild bundle against three 0.186.0 resolves every import (obs), but deep imports can break on three upgrades. **It was not run on a GPU here** (the brief forbids Chromium). A render test is required before adoption.
4. **Coordinates.** The atmosphere works in ECEF with world-origin rebasing (`matrixWorldToECEF`). Our world is x = east, y = up, z = south. Use `getNorthUpEastFrame` at the ARP and swap axes (x_east → E, y → U, z_south → −N).
5. **Stars.** The default `starsNode.intensity = 1000` is documented as "far too bright from a physical standpoint … Set this value to 1 when physically correct star luminance is needed" (WEBGPU.md, V). With a physical camera and the SFO sky background, only the brightest stars should show (§4.3).
6. **Moon texture.** `MoonNode` takes optional colour and displacement maps from the NASA SVS [CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/), for example `lroc_color_2k.jpg` at 447 KB.
   - NASA's media guidelines: "texture maps and polygon data … generally are not subject to copyright in the United States", and "NASA should be acknowledged as the source" ([nasa.gov](https://www.nasa.gov/nasa-brand-center/images-and-media/), V).
   - The SVS credit line is "NASA's Scientific Visualization Studio".
   - `MoonNode` shades the disc Oren–Nayar from the Sun direction, so the **phase and terminator orientation come out of the geometry**. It has no opposition surge.

**Babylon.js 9.28** `@babylonjs/addons` also has a physically based atmosphere with aerial perspective (see `engine.md`). It is not an option inside three.js.

### 4.2 Recommendation for the sky (inf, grounded in the above)

- Adopt takram's `webgpu` entry in the new renderer. Use `skyBackground()`, `aerialPerspective(colour, depth)`, `AtmosphereLight` and `SkyEnvironmentNode` for IBL.
- Drive the Sun and Moon from `ephemeris.mjs`, and self-host `stars.bin`.
- Keep our TSL port (`js/three/sky.js`) as the fallback if the GPU test fails or LUT generation is too slow on phones.
- Keep the METAR clouds and fog from `weather.md`. Takram's aerial perspective handles clear-air haze; METAR-driven fog is a separate extinction term.

### 4.3 Night sky over SFO: natural background, light pollution, stars

- **Natural sky (V).** Falchi et al. 2016, *Sci. Adv.* 2:e1600377, [PMC4928945](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4928945/):
  > "We chose 22.0 mag/arcsec², corresponding to 174 μcd/m², as a typical brightness of the night sky background during solar minimum activity, excluding stars brighter than magnitude 7, away from Milky Way…"

  Conversion: L = 10.8×10⁴ × 10^(−0.4 m) cd/m². This is the Unihedron formula quoted by Kyba et al. 2011; it gives 22.0 → 1.71×10⁻⁴, consistent with Falchi's 174 µcd/m² (T).
- **Atlas classes (V, Falchi Table 1).** Each class is a ratio of artificial to natural brightness:

  | Ratio | Total brightness | Colour |
  |---|---|---|
  | 5.12–10.2 | 1.07–1.96 mcd/m² | red |
  | 10.2–20.5 | 1.96–3.74 mcd/m² | magenta |
  | 20.5–41 | 3.74–7.30 mcd/m² | pink |
  | > 41 | > 7.30 mcd/m² | white |

  - The Milky Way is lost above 688 µcd/m² artificial.
  - The atlas notes "almost half of the United States experience light-polluted nights". Its maps were "calibrated to match the time of satellite overpass, at around 1 a.m." and "brighter skies should typically be expected … earlier in the night".
- **SFO value (obs, coarse; NV exact).** We read Figure 3 (North America; from the PMC supplementary zip, 700 px wide) at the San Francisco Bay: the region is in the red/magenta/pink band. That is about 10–41 × natural, **1.96–7.3 mcd/m² total, about 19.4–17.9 mag/arcsec²**.
  - The exact pixel value needs the 2.9 GB GeoTIFF ([GFZ doi:10.5880/GFZ.1.4.2016.001](https://doi.org/10.5880/GFZ.1.4.2016.001)). Its download is behind a request form ("Access to the FTP site … can be requested via the data request form").
  - The alternative is the lightpollutionmap.info API, which answered "Invalid or missing authentication. Please request a key for API use."
  - **Licence: CC BY-NC 4.0** (GFZ DataCite `rightsList`, V). Even a single derived value used in a public app should be attributed. Discuss the "non-commercial" condition with the owner before any commercial use.
- **Clouds amplify city glow (V).** Kyba et al. 2011, [PLoS ONE 6:e17307](https://doi.org/10.1371/journal.pone.0017307):
  > "cloud coverage dramatically amplifies the sky luminance, by a factor of 10.1 for one location inside of Berlin and by a factor of 2.8 at 32 km from the city center … inside of the city overcast nights are brighter than clear rural moonlit nights, by a factor of 4.1."

  SFO's frequent marine-layer stratus (`weather.md` §4) should therefore raise the night-sky luminance several-fold and tint it the colour of the city lights. The Berlin factor applied to SFO is **inf**.
- **Stars.**
  - Takram uses the Yale Bright Star Catalogue v5: 9,110 stars, "more or less complete to V=7" ([Harvard TDC](http://tdc-www.harvard.edu/catalogs/bsc5.html), V).
  - **The BSC5 terms of use are not stated on that page (NV).** Takram redistributes a derived `stars.bin` under its MIT-"except where indicated" licence.
  - Under a 18–19.4 mag/arcsec² sky only first- to third-magnitude stars stand out. The exact naked-eye limit depends on the observer model (**inf**). A physical camera at EV −3 to −6 would show only a handful of stars and the Moon.
  - Recommendation: render stars with `intensity = 1` (physical), plus a user "star boost" off by default, so the SFO sky is not falsely dark.
- **Moon (T).**
  - Angular diameter at SFO in 2026 ranges from about 29.4′ to 33.5′ (the Horizons check covers this range within 0.2″).
  - The bright-limb angle and the phase come from `moonPosition`. Moonlight on the scene is §3 (≤ 0.4 lx).

---------------------------------------------------------------------------------------------------------------------

## 5. Night appearance of the airport (task c)

### 5.1 Apron floodlights

**FAA guidance (V).** AC 150/5360-13A §7.5.2:
> "Mounted floodlights are the preferred method of lighting the apron area. … install uniform illumination across lighted areas using multiple overlapping light sources from different directions to minimize strong ground shadowing."

The current AC has no illuminance numbers. The cancelled AC 150/5360-13 (1988), Table 4-1, gave:
- "Fences, gates, guard-shelters, building exteriors, apron areas …": 5.0 fc (54.0 lx);
- "General aircraft operations area": 0.15 (1.6);
- "Roadways": 1.5 (16.0);
- floodlights "typically mounted at a height of 25 to 50 feet (8 to 15 m) with a maximum spacing of 200 feet (60 m)".

These are historical values (the sibling's cached copy, `refs/cache/lighting/150_5360_13_part2.txt`).

**SFO masts (V, from `airfield_lighting.md` §7.5).** The FAA DOF lists 54 poles 60–157 ft AGL within 3 km. 28 of them match OSM `tower:type=lighting` masts.

**Lamp type and colour at SFO: NV.**
- **Searched:** SFO/flysfo, the Airport Commission, SFPUC, the T1 project pages (DBIA, Arup, QTL) and contractor pages.
- **Found:**
  - SFPUC (22 Jan 2025): "replacing over 2,000 outdated metal halide fixtures with advanced LED lighting" in the **Rental Car Center garage**, and "over 500 energy efficient LED fixtures" in its Quick Turn Around area ([sfpuc.gov](https://www.sfpuc.gov/about-us/news/cut-costs-and-reduce-energy-use-sfo-intl-turned-sfpuc)). This is landside, not apron.
  - A Schembri Construction portfolio entry titled "SFO – High Mast Lighting Replacement". The page returned 403/503 and has no archive copy. Its scope, fixture type and date are unknown.
- **No source states** whether the apron masts are high-pressure sodium (about 2,000 K, orange), metal halide (about 3,000–4,200 K) or LED (usually 4,000–5,000 K).
- **What the renderer should do.** Make floodlight CCT a per-mast parameter, defaulting to "unknown". Ask the owner for a night photo of each terminal apron (see open questions). Do not guess sodium-orange or LED-white.

For rendering with a physical camera, the 1988 target of 54 lx on the apron gives:
- EV100 about 4.6 on 18 % grey;
- EV100 about 5.6 on concrete of reflectance 0.35.

This is the right exposure anchor for night apron views (T/inf).

### 5.2 Terminal interior lighting

- **Harvey Milk Terminal 1, Boarding Area B (V).** The lighting design is by Janet Nolan Lighting Design with QTL fixtures. It uses "soft linear illumination", "luminous ceilings", "integrated linear lighting", "architectural cove lighting" and "concealed linear lighting" ([QTL](https://www.qtl.lighting/portfolio/san-francisco-international-airport/)). The page gives no CCT and no illuminance.
- **Illuminance targets (NV).** No free primary source was found. The usual references, EN 12464-1 and the IES handbook, are paywalled.
- **Rendering approach (inf).** Treat the glazing as an emitter. Luminance ≈ interior illuminance × interior reflectance / π × glass transmittance.
  - For example, 300 lx × 0.5 / π × 0.5 gives about 24 cd/m².
  - Scale this with the physical exposure, so terminals glow at night and read as dark glass by day.
  - Validate against owner night photos.

### 5.3 Jet bridge lights

- **Manufacturer standard (V).** The Oshkosh AeroTech Jetway Glass & Steel Truss sell sheet (2025):
  > "Exterior Lighting: Three floodlights illuminate the apron and wheel bogie areas. A sealed dual fluorescent tube 4'0" fixture illuminates the cab/aircraft interface area."

  Interior: "6" x 4' Low Profile LED Light" ([PDF](https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_Truss_Sell-Sheet_2025.pdf)).
- **An airport specification (V, BWI, not SFO).** MDOT MAA PEGS 15.4.7:
  > "Task Lighting installed on PBBs shall consist of two (2) floodlight fixtures … mounted 4 feet above the top of the PBB on the right side … The second … 10 feet above the left side … to illuminate the apron area adjacent to the aircraft"

  It also specifies "two (2) LED 60-minute rotary timers".
- **SFO's bridge makes and lights: NV.** The current `gates.js:156–160` has a cab-roof floodlight and an amber beacon that flashes while the bridge moves. The beacon is not supported by any source found here (**NV**): keep it only if the owner's photos or an SFO spec show one.

### 5.4 Aircraft exterior lights

**Regulations (V, eCFR, as amended; text fetched 24 Sep 2026).**

| Item | Rule | Source |
|---|---|---|
| Position lights: placement | "a red and a green light spaced laterally as far apart as practicable … the red light is on the left side and the green light is on the right side"; rear light "a white light mounted as far aft as practicable on the tail or on each wing tip" | §25.1385 |
| Coverage (dihedral angles) | L: 0–110° left of dead ahead; R: 0–110° right; A (aft white): "70 degrees to the right and to the left" of the rear axis, i.e. 140° total | §25.1387 |
| Minimum intensity, horizontal plane | Red/green: 0–10° **40 cd**, 10–20° **30 cd**, 20–110° **5 cd**. Rear white, 110–180°: **20 cd**. | §25.1391 |
| Vertical factor (× horizontal minimum) | 0°: 1.00; 0–5°: 0.90; 5–10°: 0.80; 10–15°: 0.70; 15–20°: 0.50; 20–30°: 0.30; 30–40°: 0.10; 40–90°: 0.05 | §25.1393 |
| Overlap maxima | Green in L: 10 cd (Area A) / 1 cd (Area B); red in R: 10/1; green or red in A: 5/1; rear white in L or R: 5/1. Area A is 10–20° beyond the boundary plane; Area B is more than 20° beyond. | §25.1395 |
| Colours | Aviation red "y is not greater than 0.335; and z is not greater than 0.002"; green and white CIE boxes | §25.1397 |
| Anti-collision | "effective flash frequency of not less than 40, nor more than 100 cycles per minute" (overlaps up to 180); "either aviation red or aviation white"; coverage "at least 75 degrees above and 75 degrees below the horizontal plane" | §25.1401(b)–(d) |
| Anti-collision minimum effective intensity | 0–5°: **400 cd**; 5–10°: 240; 10–20°: 80; 20–30°: 40; 30–75°: 20 | §25.1401(f) |
| Effective intensity (Blondel–Rey) | I_e = ∫_{t1}^{t2} I(t) dt / (0.2 + (t2 − t1)). This is the equation image in §25.1401(e), transcribed from the [LII rendering](https://www.law.cornell.edu/cfr/text/14/25.1401). | §25.1401(e) |
| When to light | "During the period from sunset to sunrise … Operate an aircraft unless it has lighted position lights"; anti-collision lights "need not be lighted when the pilot-in-command determines that, because of operating conditions, it would be in the interest of safety to turn the lights off" | 14 CFR 91.209 |
| Landing lights | Only qualitative: "enough light for night landing"; no candela minimum | §25.1383 |

The eCFR history API shows §25.1389 was last amended on 2016-12-30. Links: [25.1385](https://www.ecfr.gov/current/title-14/part-25/section-25.1385) … [25.1401](https://www.ecfr.gov/current/title-14/part-25/section-25.1401), [91.209](https://www.ecfr.gov/current/title-14/part-91/section-91.209).

**Operating practice (V, [AIM 4-3-24](https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_3.html), "Effective: 7/9/2026, Change 3").** The section was renumbered from 4-3-23. It says:

> "Aircraft position lights are required to be lighted on aircraft operated on the surface and in flight from sunset to sunrise. … aircraft equipped with an anti-collision light system are required to operate that light system during all types of operations (day and night)."

> "the FAA recommends that air carriers and commercial operators turn on their rotating beacons anytime their aircraft engines are in operation."

> "Prior to commencing taxi, it is recommended to turn on navigation, position, anti-collision, and logo lights (if equipped). … consider turning on the taxi light when the aircraft is moving or intending to move on the ground, and turning it off when stopped or yielding to other ground traffic. Strobe lights should not be illuminated during taxi if they will adversely affect the vision of other pilots or ground personnel."

> "When entering the departure runway for takeoff or to 'line up and wait,' all lights, except for landing lights, should be illuminated … Landing lights should be turned on when takeoff clearance is received"

> "Pilots are further encouraged to turn on their landing lights when operating below 10,000 feet, day or night, especially when operating within 10 miles of any airport"

**Example fixture (V).** Honeywell High Output LED Landing Light: "770,000 cd", "15° x 16°", "Boeing 737 NG, 757, 767 and 777", "2 (1 each wing root)" ([Honeywell](https://www.honeywellaerospace.com/us/en/products-and-services/products/control-systems/lighting/led-landing-and-taxi-lights/high-output-led-landing-light)).

**Not verified (NV).**
- Airline-specific SOPs: runway turn-off lights, wing and logo lights at the gate, strobe use on the ground. Boeing and Airbus FCOMs are not public.
- Typical strobe peak intensities and flash waveforms of specific LED units.

**Derived rendering rules (inf, from the regulations above).**
1. **Directional emitters, not omni sprites.** Nav light visibility follows §25.1387.
   - Red is visible only 0–110° to the left of the nose; green is the mirror image; white only within ±70° of the tail.
   - Intensity uses §25.1391 × §25.1393. Typical real units exceed the minima, so use about 2 × the minima as a default (**inf**).
2. **Flash rendering.** A display cannot reproduce Blondel–Rey integration. A flash drawn for n frames of duration t_f at intensity I_f is perceived as I_e = I_f·n·t_f / (0.2 + n·t_f). To show the regulatory 400 cd effective:
   - 1 frame at 60 Hz: I_f ≈ **5,200 cd**;
   - 2 frames: I_f ≈ 2,800 cd.

   The rate must stay within 40–100/min. The current strobe (1.1 Hz = 66/min, double flash) and beacon (1.0 Hz = 60/min) comply (`js/aircraft/fleet.js:125–126`).
3. **Light logic.** Changes to `app.js:253–256`, all per AIM:
   - add logo lights, on from before taxi until parked;
   - taxi light off when stopped or holding;
   - strobes on only from runway entry until the runway is vacated;
   - landing lights below 10,000 ft (3,048 m, not the current 3,000 m) and from takeoff clearance, that is the takeoff roll;
   - beacon from before pushback while engines run.
   - Nav lights on parked aircraft: position lights are required only when "operated" or moving at night (91.209(a)(2) also allows "clearly illuminated"). Whether parked, powered aircraft at SFO show nav lights is **NV**. Default to off at gates without a beacon, and let the owner decide.
4. **Colours.** Use the CIE boxes of §25.1397, the same aviation colours as `airfield_lighting.md` §10.2 (FAA EB 67D). The current `[1,0.06,0.04]` and `[0.1,1,0.3]` values are not converted from those boxes.

### 5.5 Road vehicles (partly V)

- FMVSS No. 108 (49 CFR 571.108, [eCFR](https://www.ecfr.gov/current/title-49/part-571/section-571.108)) defines the lamp set: headlamps (white), tail and stop lamps (red), turn signals, DRLs.
- A DRL made from an upper beam may run at a luminous intensity "at test point H-V … not more than 7,000 cd" (V, S7.10).
- The photometry tables (tail/stop minima and maxima, beam patterns) are images in eCFR and tables in the govinfo PDF. The eCFR image server redirected to a bot check, so they were not transcribed (**NV**).
- **Rendering (inf).** Headlamps as two forward cones, a few thousand to about 20,000 cd in the hot spot. Tail lamps a few cd, stop lamps tens to hundreds of cd, red. Only where the app draws traffic on US-101 and the airport roads. Verify the numbers against the FMVSS tables before relying on them.

---------------------------------------------------------------------------------------------------------------------

## 6. Exposure: physically based camera and auto-exposure (task d)

### 6.1 Definitions (V)

- **Frostbite** (Lagarde & de Rousiers, SIGGRAPH 2014, v3.2, [PDF](https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf)):
  - §4.3: "EV = log2(L_avg S / K) … ISO 2720:1974 recommends a range for K between 10.6 and 13.4. Two values for K are in common use: 12.5 (Canon, Nikon, and Sekonic) and 14 (Minolta, Kenko, and Pentax)."
  - Converting EV to luminance: "L = 2^(EV−3)" (Table 7).
  - §5.1: EV100 = log2(N²/t · 100/S), and the saturation-based `maxLuminance = 1.2f * pow(2.0f, EV100)`, with the exposure being its reciprocal. "Sunny 16": f/16, ISO 100, 1/125 s gives EV 14.97.
  - Measured illuminance in Stockholm in July: Sun + sky 85,500–113,600 lx; sky alone 19,300–29,000 lx (Table 11).
- **Filament** ([Filament.md](https://google.github.io/filament/Filament.md.html)):
  - "from 10⁻⁵ cd·m⁻² for starlight to 10⁹ cd·m⁻² for the sun".
  - "Pre-exposed lights": "simply apply the camera exposure … before writing out the result of the lighting pass", or pre-expose the lights so half floats never overflow.
  - "Automatic exposure": luminance downsampling or a histogram, spot, centre-weighted or matrix metering, and adaptation "L_avg = L_avg + (L − L_avg)(1 − e^(−Δt·τ))" (Pattanaik et al. 2000).
- **three.js r186 (V, source).**
  - `PointLight`/`SpotLight` intensity is "measured in candela (cd)". The distance falloff is Frostbite's 1/d² window (`LightUtils.js`).
  - `BRDF_Lambert` is diffuse/π and irradiance = N·L × lightColor. So a `DirectionalLight` intensity is illuminance in lux (inferred from the code; the docs do not state the unit).
  - There is no auto-exposure or luminance-adaptation node in `examples/jsm/tsl/display` (grep for exposure/adaptation/averageLuminance found none).
  - The renderer has `toneMappingExposure` and AgX/Neutral tone mappers.

### 6.2 EV100 by scene at SFO (T for the physics, inf for the scene choice)

18 % grey, clear sky unless noted:

| Scene | Illuminance | EV100 |
|---|---|---|
| Noon, Sun at 60° | 103,000 lx | 15.5 |
| Snapshot, 23 Sep 10:51 PDT (Sun at 41.6°) | 73,900 lx | 15.0 |
| Overcast noon (÷3) | | about 13.9 |
| Sunset (0°) | 984 lx | 8.8 |
| Sun at −4° | 24 lx | 3.5 |
| End of civil twilight (−6°) | 3 lx | 0.5 |
| Floodlit apron, 54 lx (1988 FAA target) | 54 lx | 4.6 (concrete 5.6) |
| Full Moon at 53°, no floodlights | 0.20 lx | −3.5 |
| Nautical twilight end (−12°) | 0.005 lx | −8.8 |
| Night sky itself, 18–19.4 mag/arcsec² | 3–7 × 10⁻³ cd/m² | −4 to −5 |

### 6.3 Auto-exposure recipe for the WebGPU renderer (inf, built on 6.1)

1. **Physical units throughout.** Sun and sky from takram in cd/m² (or our sky scaled to lux). Airfield lights in cd from `tools/env/lighting_spec.json`. Aircraft lights in cd (§5.4). Floodlights in lm or cd.
2. **Pre-expose** with the previous frame's EV (Filament), so RGBA16F never overflows: the Sun is about 1.6 × 10⁹ cd/m² and the half-float maximum is 65,504.
3. **Meter.**
   - Build a log₂-luminance mip chain; it works on WebGL2 too. On WebGPU, use a 64-bin compute histogram.
   - Use centre-weighted metering, and exclude the top 2 % and bottom 50 % of the histogram so point lights and sky do not dominate.
   - Target EV100 = log₂(L_avg·100/12.5) − EC.
4. **Clamp and bias for "looks like night".**
   - Clamp EV100 to about **[2, 16]**. EV 2–3 is roughly what a handheld night photo of a lit apron uses. Letting the meter reach EV −4 would turn moonlit night into day.
   - Add an exposure-compensation curve vs Sun elevation. It should darken below −4° so twilight reads blue and dim while airfield lights stay saturated and bloom.
   - These bounds are **inf** and should be set by visual QA against night photos of SFO.
5. **Adapt** with Filament's exponential, τ about 1–2 s brightening and 3–4 s darkening (inf). Snap immediately on camera cuts or view presets.
6. **Night vision (optional, inf).** Thompson, Shirley & Ferwerda 2002, "A Spatial Post-Processing Algorithm for Images of Night Scenes" (*J. Graphics Tools* 7(1)). Its abstract describes "low overall contrast, low overall brightnesses, desaturation, and … a 'blue shift'", plus noise and a loss of acuity. Apply it only below about EV 0 and keep it subtle. The formula was not fetched here.

---------------------------------------------------------------------------------------------------------------------

## 7. Weather interplay (cross-reference)

`weather.md` covers the METAR decoding, visibility → extinction, the marine layer, precipitation and wet surfaces. `airfield_lighting.md` §9–10 covers which airfield lights are on by day, night and IMC, and the Allard's-law fade. This report adds:

- **Clouds cut illuminance.** Divide sun and moon illuminance by 2 for thin cloud over the disc, 3 for average cloud, and 10 for dark stratus (Brown's factors via Circular 171, V). This is a better daylight/ambient model than the current `cloud[0] > 0.6` exposure bump (`app.js:148`).
- **Overcast nights are brighter and orange-white.** A low stratus deck (METAR BKN/OVC ≤ 5,000 ft) should raise the night-sky floor by a factor of several, up to about 10 (Kyba, V for Berlin, **inf** for SFO), in the colour of the city lights. It should also hide stars and the Moon.
- **Twilight in fog.** When METAR visibility is below about 1 SM, the civil-twilight sky gradient should collapse to a uniform grey, driven by the extinction coefficient from `weather.md` §3.1 (**inf**).

---------------------------------------------------------------------------------------------------------------------

## 8. Recommendations (priority order)

1. **Replace `solarPosition`** in the new renderer with `ephemeris.mjs` (`skyState(date)`).
   - This adds refraction: sunsets 2.9 min later, and the Sun drawn in the right place at the horizon.
   - It adds the Moon (position, phase and bright-limb orientation) and correct PST/PDT dusk presets from `sunEvents()`.
   - Run `node tools/env/test_ephemeris.mjs` in CI.
2. **Replace the night heuristics** (`nightF`, `dark`, the exposure formula) with Circular 171 illuminance and EV100. Suggested switches:
   - "floodlights on" when natural illuminance < 32 lx (Sun about −3.7°), matching the ASOS 3 fc end of the photocell range (**inf**);
   - "night" at the end of civil twilight (−6°).
3. **Adopt @takram/three-atmosphere `webgpu`**, after a GPU render test on desktop and on an iPhone.
   - Self-host `stars.bin`; feed the Sun and Moon from `ephemeris.mjs`.
   - Optionally add NASA CGI Moon Kit `lroc_color_2k.jpg` (447 KB), credited "NASA's Scientific Visualization Studio".
   - Include the BSD-3/MIT/Apache notices in `docs/ATTRIBUTION.md` (use `--legal-comments` in esbuild).
4. **Use physical light units plus auto-exposure** (§6.3). Use candela for every lamp. Pull airfield lamps from `lighting_spec.json` and aircraft lamps from §5.4.
5. **Aircraft lights:** directional nav lights (§25.1387/1391/1393), aviation colours from §25.1397, the corrected on/off logic from AIM 4-3-24, and logo lights.
6. **Night-sky floor:** a parameter for artificial zenith luminance. Default 3 mcd/m² (about 18.9 mag/arcsec², **inf** from the coarse atlas reading), × up to 10 under low overcast. Replace the default with the atlas pixel value once available (with attribution, CC BY-NC).
7. **Floodlight colour and terminal glow:** keep them parameters until the owner supplies night photos. Do not choose sodium-orange or LED-white by assumption.

## 9. Open questions for the owner

1. **Night photos of SFO.** Can you send night photos of the apron (each terminal), jet bridges, the terminal glazing and the tower? We need the colour of the apron floodlights (sodium, metal halide or LED), whether bridges show an amber beacon, and terminal glow. No public SFO source states these.
2. **Light-pollution value.** Should we request the Falchi atlas raster (GFZ request form) or a free lightpollutionmap.info API key to get SFO's exact artificial sky brightness? The data are **CC BY-NC 4.0**. Is the app strictly non-commercial?
3. **Look at night.** Should the default night view be "photographic" (auto-exposed, the apron well lit, a few stars) or "eye-like" (darker, desaturated, blue shift)? Both can be derived from the same physical values.
4. **Parked aircraft at night.** Should parked, powered aircraft at gates show nav and logo lights? Regulations only require position lights when operating; airline practice varies and is not public.
5. **Dependencies.** Is adding `@takram/three-atmosphere` (MIT, about 25 KB gzip plus a 91 KB star file) acceptable? The alternative is extending our own sky port with a Moon and stars.
6. **Star catalogue.** BSC5's terms of use are not stated on its Harvard page. Is the owner comfortable shipping takram's derived `stars.bin` under takram's MIT licence, or should we ask CDS/Harvard?

## 10. Method and reproducibility

```bash
python3 tools/env/fetch_ephemeris_refs.py        # raw NOAA/Horizons/USNO/IERS/C171 files -> refs/cache/sun_night/ (skips existing)
node tools/env/build_ephemeris_fixtures.mjs      # -> tools/env/fixtures/ephemeris_ref.json (numbers + URLs + SHA-256)
node tools/env/test_ephemeris.mjs                # 33 checks; exit 1 on failure (about 5 s)
```

- The NOAA reference values come from running NOAA's own `main.js` in a Node `vm`: SHA-256 `3832956f…856`, 20,880 bytes. Its calculation functions are plain JS with no DOM access at load.
- The takram measurements were made in a scratch npm install (three 0.186.0, esbuild 0.28.2); nothing was added to the project.
- Downloads not listed in the fixture are in `refs/cache/sun_night/`:
  - takram tarballs and docs;
  - eCFR XML;
  - the AIM chapter 4 page;
  - Circular 171 PDF and OCR text;
  - Frostbite PDF and `Filament.md.html`;
  - Falchi PMC XML and figures;
  - Kyba PMC XML;
  - the SFPUC page;
  - the Oshkosh and BWI PBB specifications;
  - the NASA SVS page.

## 11. Sources

All fetched on 24 Sep 2026.

**Ephemeris and illuminance**
- NOAA/GML Solar Calculator code: https://gml.noaa.gov/grad/solcalc/main.js; details page: https://gml.noaa.gov/grad/solcalc/calcdetails.html
- JPL Horizons API (DE441): https://ssd.jpl.nasa.gov/api/horizons.api
- USNO:
  - year tables: https://aa.usno.navy.mil/calculated/rstt/year (tasks 0–4);
  - one-day data: https://aa.usno.navy.mil/api/rstt/oneday;
  - phases: https://aa.usno.navy.mil/api/moon/phases/year?year=2026;
  - celestial navigation: https://aa.usno.navy.mil/api/celnav;
  - definitions: https://aa.usno.navy.mil/faq/RST_defs
- IERS Bulletin A: https://datacenter.iers.org/data/latestVersion/bulletinA.txt
- USNO Circular 171 (Janiczek & DeYoung 1987): https://archive.org/details/DTIC_ADA182110
- Meeus, *Astronomical Algorithms*, 2nd ed., 1998 (not online). Tables 47.A/B are from `astronomia` 4.2.0 (MIT): https://registry.npmjs.org/astronomia/-/astronomia-4.2.0.tgz; worked-example values from https://raw.githubusercontent.com/commenthol/astronomia/master/test/moonposition.test.js

**Sky**
- @takram/three-atmosphere 0.19.1: https://registry.npmjs.org/@takram/three-atmosphere/-/three-atmosphere-0.19.1.tgz; WEBGPU.md: https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/atmosphere/WEBGPU.md; licence: https://raw.githubusercontent.com/takram-design-engineering/three-geospatial/main/LICENSE
- three.js 0.186.0 source: `node_modules/three/examples/jsm/objects/SkyMesh.js`, `src/lights/*.js`, `src/nodes/lighting/LightUtils.js`
- NASA SVS CGI Moon Kit: https://svs.gsfc.nasa.gov/4720/; NASA media guidelines: https://www.nasa.gov/nasa-brand-center/images-and-media/
- Yale BSC5: http://tdc-www.harvard.edu/catalogs/bsc5.html

**Night sky and light pollution**
- Falchi et al. 2016: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4928945/ (Europe PMC XML and supplementary zip); data DOI: https://doi.org/10.5880/GFZ.1.4.2016.001
- Kyba et al. 2011: https://doi.org/10.1371/journal.pone.0017307 (PMC3047560)

**Regulations and practice**
- 14 CFR 25.1383–25.1401 and 91.209 via the eCFR API (2026-09-01 point in time)
- 25.1401(e) equation: https://www.law.cornell.edu/cfr/text/14/25.1401
- AIM 4-3-24: https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_3.html
- FMVSS 108: https://www.ecfr.gov/current/title-49/part-571/section-571.108; https://www.govinfo.gov/content/pkg/CFR-2024-title49-vol6/pdf/CFR-2024-title49-vol6-sec571-108.pdf
- AC 150/5360-13A §7.5 and AC 150/5360-13 (1988) Table 4-1: sibling cache `refs/cache/lighting/`

**Products and airports**
- Honeywell High Output LED Landing Light: https://www.honeywellaerospace.com/us/en/products-and-services/products/control-systems/lighting/led-landing-and-taxi-lights/high-output-led-landing-light
- Oshkosh AeroTech Jetway sell sheet: https://oshkoshaerotech.com/hubfs/images/Jetway%20SteelGlass_Truss_Sell-Sheet_2025.pdf
- BWI PEGS 15.4: https://public.airportal.maa.maryland.gov/PEGS/Volume_2_-_Architectural_and_Engineering/Chapter_15_Passenger_Boarding_Bridges/15_4_Typical_Passenger_Boarding_Bridge_Accessories.htm
- SFPUC SFO LED article: https://www.sfpuc.gov/about-us/news/cut-costs-and-reduce-energy-use-sfo-intl-turned-sfpuc
- QTL SFO T1: https://www.qtl.lighting/portfolio/san-francisco-international-airport/

**Exposure**
- Frostbite PBR v3.2: https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf
- Filament: https://google.github.io/filament/Filament.md.html
- Thompson, Shirley & Ferwerda 2002 (abstract only): https://www.researchgate.net/publication/255682295
