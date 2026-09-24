#!/bin/bash
# usage: mkprev.sh <shotIndex> <label>
i=$1; lab=$2; cd "$(dirname "$0")/out"
ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=width,height,nb_read_packets -of csv=p=0 sfo4k_shot$i.mp4
nice -n 19 ffmpeg -y -loglevel error -i sfo4k_shot$i.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -movflags +faststart /mnt/user-data/outputs/preview_shot$((i+1))_${lab}_1080p.mp4
nice -n 19 ffmpeg -y -loglevel error -sseof -4 -i sfo4k_shot$i.mp4 -frames:v 1 -vf scale=1280:720 chk_s$i.png
echo ok
