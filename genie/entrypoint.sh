#!/bin/bash
# Start the Genie server, then load character xiaoman + set the reference audio.
set -e

GENIE_HOST="${GENIE_HOST:-0.0.0.0}"
GENIE_PORT="${GENIE_PORT:-8000}"
BASE="http://127.0.0.1:${GENIE_PORT}"

python3 -m genie_tts.Server &
SERVER_PID=$!

echo "waiting for genie server on ${BASE} ..."
for i in $(seq 1 60); do
  if curl -sf -o /dev/null "${BASE}/docs" 2>/dev/null || curl -sf -o /dev/null -X POST "${BASE}/tts" -H 'Content-Type: application/json' -d '{"character_name":"__ping__","text":"x"}' 2>/dev/null; then
    break
  fi
  sleep 2
done

echo "loading character xiaoman ..."
curl -sf -X POST "${BASE}/load_character" \
  -H 'Content-Type: application/json' \
  -d '{"character_name":"xiaoman","onnx_model_dir":"/app/genie-voice/xiaoman-onnx-official","language":"zh"}'
echo

echo "setting reference audio ..."
curl -sf -X POST "${BASE}/set_reference_audio" \
  -H 'Content-Type: application/json' \
  -d '{"character_name":"xiaoman","audio_path":"/app/genie-voice/ref-seg6.wav","audio_text":"所以拍摄停滞不前，我自己在家里面两三个月没事干。","language":"zh"}'
echo

echo "genie xiaoman ready, waiting on server pid ${SERVER_PID}"
wait "${SERVER_PID}"
