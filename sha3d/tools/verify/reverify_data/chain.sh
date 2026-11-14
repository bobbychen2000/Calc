#!/bin/bash
# Re-run the fixer's builder chain on a scratch root R (all outputs inside R). Logs to $2.
R=$1; LOG=$2; set -o pipefail
run(){ echo "### $*" >>$LOG; ( cd $R/.. && "$@" ) >>$LOG 2>&1 || { echo "FAILED: $*" >>$LOG; echo "FAILED: $*"; }; }
T=$R/tools
run python3 -I $T/osm/pin_extract.py $R/refs/cache/osm_pinned_raw/20261114 $R/refs/cache/osm_pinned
run python3 -I $T/osm/write_sources.py $R
run python3 -I $T/common/test_frame.py $R/refs/cache/osm_pinned/pin_summary.json
run python3 -I $T/geo/s2_cut_extent.py $R
run python3 -I $T/airport/rwy_ends.py $R $R/data/meas/rwy_ends.json $R/docs/phase1/airport_rwy_ends.png
run python3 -I $T/airport/twy_refit.py $R $R/data/meas/twy_refit.json $R/docs/phase1/airport_twy_refit.png
run python3 -I $T/airport/build_airport.py $R
run python3 -I $T/airport/sar_registration.py $R $R/data/meas/sar_registration.json
run python3 -I $T/airport/stand_s2.py $R $R/data/meas/stand_s2.json
run python3 -I $T/airport/stand_sar.py $R $R/data/meas/stand_sar.json $R/docs/phase1/bridges_sar
run python3 -I $T/airport/build_stands.py $R
run python3 -I $T/airport/build_taxigraph.py $R
run python3 -I $T/airport/overlay.py $R $R/docs/phase1/airport_overlay.jpg $R/docs/phase1/airport_overlay_umbra.jpg
run python3 -I $T/airport/twy_check_plate.py $R $R/docs/phase1/airport_twy_checks.jpg
run python3 -I $T/airport/stands_plates.py $R
run python3 -I $T/airport/write_sources_phase1.py $R
echo DONE >>$LOG
