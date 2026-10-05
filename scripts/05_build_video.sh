#!/usr/bin/env bash
# 05_build_video.sh — slides/NN.png + audio/NN.wav → final.mp4 (1920x1080 H.264/AAC)
# 需要: ffmpeg
# 用法: bash scripts/05_build_video.sh [slides] [audio] [final.mp4]
set -euo pipefail

SLIDES="${1:-slides}"
AUDIO="${2:-audio}"
OUT="${3:-final.mp4}"

TMP="$(mktemp -d)"
LIST="$TMP/list.txt"
: > "$LIST"

VF="scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"

shopt -s nullglob
for wav in "$AUDIO"/*.wav; do
  n="$(basename "$wav" .wav)"
  png="$SLIDES/$n.png"
  if [ ! -f "$png" ]; then
    echo "跳過 $n：找不到 $png"
    continue
  fi
  ffmpeg -y -loglevel error -loop 1 -i "$png" -i "$wav" \
    -vf "$VF" -c:v libx264 -tune stillimage -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 192k -ar 44100 -shortest "$TMP/seg_$n.mp4"
  echo "file '$TMP/seg_$n.mp4'" >> "$LIST"
  echo "[$n] ok"
done

ffmpeg -y -loglevel error -f concat -safe 0 -i "$LIST" -c copy "$OUT"
echo "OK → $OUT"
