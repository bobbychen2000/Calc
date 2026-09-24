#!/bin/bash
# usage: nosegrid.sh VIEW OUT TYPES
cd "$(dirname "$0")" && VIEW=$1 W=960 H=540 TYPES=${3:-b39m,a20n,e75l,b789,bcs3,b77w} timeout 600 node --expose-gc render.mjs jobs/noses.mjs 2>&1 | grep -a -iE "error|fail" | head -5
cd out && ffmpeg -y -loglevel error -i ns_0.png -i ns_1.png -i ns_2.png -i ns_3.png -i ns_4.png -i ns_5.png -filter_complex "[0][1][2]hstack=3[a];[3][4][5]hstack=3[b];[a][b]vstack,scale=1920:-1" $2
