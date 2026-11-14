#!/bin/bash
# md5 of every output of the chain under root $1
R=$1; cd $R && find data refs/cache/osm_pinned refs/cache/s2 refs/cache/s2_precut refs/cache/aip_checks docs/phase1 -maxdepth 3 -type f \( -name '*.json' -o -name '*.js' -o -name '*.geojson' -o -name '*.tif' -o -name '*.jpg' -o -name '*.png' \) ! -path '*/qa/*' | sort | xargs md5sum
