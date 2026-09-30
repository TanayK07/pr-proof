#!/usr/bin/env bash
# Renders demo.html into demo.gif and demo.mp4: one headless-Chrome screenshot per step,
# held for that step's duration. Needs google-chrome and ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
out=$(mktemp -d)
name="${1:-demo}"
url="file://$PWD/$name.html"
chrome() { google-chrome --headless=new --disable-gpu --hide-scrollbars --no-first-run \
  --user-data-dir="$out/profile" --window-size=1200,${HEIGHT:-760} "$@" 2>/dev/null; }
durs=$(chrome --dump-dom "$url#1" | grep -o 'data-durs="[^"]*"' | sed 's/data-durs="//;s/"$//;s/&quot;/"/g')
n=$(python3 -c "import json,sys;print(len(json.loads(sys.argv[1])))" "$durs")
: > "$out/list.txt"
for k in $(seq 1 "$n"); do
  f=$(printf "%s/f%03d.png" "$out" "$k")
  chrome --screenshot="$f" "$url#$k"
  d=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])[int(sys.argv[2])-1]/1000)" "$durs" "$k")
  printf "file '%s'\nduration %s\n" "$f" "$d" >> "$out/list.txt"
done
printf "file '%s'\n" "$f" >> "$out/list.txt"   # concat demuxer needs the last frame repeated
ffmpeg -loglevel error -y -f concat -safe 0 -i "$out/list.txt" -vf "fps=12,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none" "$name.gif"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$out/list.txt" -vf "fps=30,format=yuv420p" -c:v libx264 -crf 20 "$name.mp4"
rm -rf "$out"
ls -la "$name.gif" "$name.mp4"
