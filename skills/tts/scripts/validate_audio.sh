#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <audio-directory>" >&2
  exit 2
fi

audio_dir=$1
if [[ ! -d "$audio_dir" ]]; then
  echo "Not a directory: $audio_dir" >&2
  exit 2
fi

for command_name in ffmpeg ffprobe shasum; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing command: $command_name" >&2
    exit 2
  fi
done

count=0
while IFS= read -r -d '' audio_file; do
  count=$((count + 1))
  echo "FILE $audio_file"
  ffprobe -v error \
    -select_streams a:0 \
    -show_entries stream=codec_name,sample_rate,channels,bit_rate \
    -show_entries format=duration,size:format_tags=title,artist,album \
    -of json "$audio_file"
  ffmpeg -nostdin -v error -i "$audio_file" -f null -
  shasum -a 256 "$audio_file"
done < <(find "$audio_dir" -type f -iname '*.mp3' -print0)

if [[ $count -eq 0 ]]; then
  echo "No MP3 files found in: $audio_dir" >&2
  exit 1
fi

echo "OK: decoded and hashed $count MP3 file(s)"
