"""The single Umbra registration of Phase 1 (re-verify N4, fix round 2; docs/phase1/qa_data.md).

Umbra Lab, Inc., Umbra SAR Open Data, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), modified: GEC scene
2024-06-02 (UMBRA-05), its 4x overview (1.4 m) and the full-resolution windows cut from the same GEC product (same
georeferencing).

UMBRA_MINUS_OSM_EN = (+3.07 m east, 0 m north), in metres on the ground (world x east; north positive here).
* East: measured by tools/airport/twy_refit.py (runway_band_registration) on the dark paved band of BOTH runways
  (runway + shoulders, half-level edges) every 50 m from 300 m to L - 300 m on the 4x overview: 41 stations, median
  +3.07 m (18L/36R +3.86, n = 5; 18R/36L +2.85, n = 36). twy_refit.py measures it on every run and stops if the result
  differs from this constant by more than 0.05 m, so the constant cannot drift silently.
* Cross-checks: QA C1 (umb_reg.py, 43 stations) +2.99 m; A2 / sar_registration.py on 6 full-resolution bands
  +3.44 m (2.87-4.12). The spread of these three (0.45 m) is a third of the overview pixel.
* North: 0 m (docs/phase1/stands.md s.2: Umbra and Sentinel-2 agree north-south at H2).
Used by: twy_refit.py (Umbra term of the taxiway re-fit), stand_sar.py (jet-bridge windows), stands_plates.py (SAR
zooms), sar_registration.py (the applied shift it records).
Not used (stated reasons, docs/phase1/qa_data.md "Fix round 2"): rwy_ends.py fits along-track steps on N-S runways
(an east shift does not move them) and overlay.py / twy_check_plate.py show every image in its own georeferencing;
tools/standards/umbra_layover.py and umbra_crops.py (task B3, outside the data builders) still use the former taxiway
fit +6.1 E / -0.9 N, see the fix-round note.
"""
UMBRA_MINUS_OSM_EN = (3.07, 0.0)
UMBRA_REG_NOTE = ('Umbra minus OSM = +3.07 m E, 0 m N: median of 41 runway-band stations on the 4x overview '
                  '(tools/airport/twy_refit.py runway_band_registration; tools/common/umbra_reg.py); QA C1 +2.99, '
                  'A2 full-resolution bands +3.44')
