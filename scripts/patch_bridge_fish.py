#!/usr/bin/env python3
"""Patch bridge.py: route xiaoman-mode voice through Fish Audio cloud TTS,
falling back to the existing edge-tts path on any failure. Mom mode keeps
edge-tts (Xiaoxuan) unchanged. Server memory cost: zero -- synthesis happens
on Fish Audio's servers, the bridge only posts text and gets mp3 back.

Why Fish Audio (checked 2026-11-07 against docs.fish.audio + fish.audio/developers):
- POST https://api.fish.audio/v1/tts, Bearer API key, model chosen with the
  `model` HTTP header (not a body field); voice is a saved clone id passed
  as body field `reference_id`; response is a raw audio stream (mp3).
- `s2.1-pro-free` is the same model as paid s2.1-pro at $0 under fair use,
  free through 2026-11-30, no SLA; after that the paid model is $15 per 1M
  UTF-8 bytes (at this bridge's volume -- voice replies are <=120 chars --
  roughly $1/month). No card required for the free model.
- Free-plan 500 chars/generation does not bind us: voice replies are
  already capped at 120 chars before TTS.

Prereqs (Torres does these in a browser; the key never goes in chat):
  1. Register at fish.audio, create an API key -> FISH_API_KEY in server .env
     (via secure storage, same as the relay key).
  2. In the fish.audio playground, clone the voice from the reference clip
     (the same 60s podcast dry voice used for Genie) and copy the voice
     model id -> FISH_REFERENCE_ID in server .env.
  3. From the Lighthouse server first test reachability (HuggingFace was
     unreachable from there, so do not assume):
       curl -s -o /tmp/fish-test.mp3 -w "http:%{http_code} size:%{size_download}\n" \
         -X POST https://api.fish.audio/v1/tts \
         -H "Authorization: Bearer $FISH_API_KEY" -H "model: s2.1-pro-free" \
         -H "Content-Type: application/json" \
         -d '{"text":"你好，我是小满","reference_id":"<voice model id>","format":"mp3"}'
     http:200 + a real mp3 = works; http:401 = reachable but key wrong;
     timeout / DNS failure = blocked from the server, stop and use Genie.

Usage: python3 patch_bridge_fish.py /home/ubuntu/qq-bridge/bridge.py
Then add the two .env lines on the server and rebuild/restart the bridge
with ./deploy.sh (same flow as the live bridge.py, md5 4b26e0b3).
Idempotent: safe to run twice. Exits non-zero if any expected pattern is
not found (unless already patched). Anchors are exact strings from the
live bridge.py (md5 4b26e0b3c98a39668949f75d4e86ab90, verified 2026-11-07).
"""
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

if "FISH_API_KEY" in src and "fish_tts_to_base64" in src:
    print("already patched, nothing to do")
    sys.exit(0)

# 1. Config: add Fish keys next to the tts_voice lines.
old_cfg = '''    "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),'''
new_cfg = '''    "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),
    # Fish Audio cloud TTS (xiaoman clone); edge-tts stays as fallback.
    # FISH_REFERENCE_ID is the voice model id cloned in the playground.
    "fish_api_key": get("FISH_API_KEY", ""),
    "fish_reference_id": get("FISH_REFERENCE_ID", ""),
    "fish_model": get("FISH_MODEL", "s2.1-pro-free"),'''
assert old_cfg in src, "config block not found"
src = src.replace(old_cfg, new_cfg, 1)

# 2. Add fish_tts_to_base64() right before tts_to_base64(), and make
#    tts_to_base64() try Fish first for non-mom replies.
old_def = '''def tts_to_base64(text, mom=False):
    """Synthesize speech with edge-tts; return a OneBot base64:// ref or None."""'''
new_def = '''def fish_tts_to_base64(text):
    """Synthesize speech with Fish Audio cloud TTS; return a OneBot base64:// ref or None.

    Model is selected with the `model` HTTP header; the voice is the saved
    clone id in FISH_REFERENCE_ID. Returns None (caller falls back) when
    the key/id is unset or the call fails. No server memory is used.
    """
    clean = clean_for_tts(text)
    if not clean or not CFG["fish_api_key"] or not CFG["fish_reference_id"]:
        return None
    payload = json.dumps({"text": clean,
                          "reference_id": CFG["fish_reference_id"],
                          "format": "mp3"}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.fish.audio/v1/tts", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + CFG["fish_api_key"],
                 "model": CFG["fish_model"],
                 # Browser UA: the relay once 403'd the Python default UA.
                 "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 1000:
            log("Fish TTS returned too little data:", len(data))
            return None
        return "base64://" + base64.b64encode(data).decode()
    except Exception as e:
        log("Fish TTS failed:", repr(e))
        return None


def tts_to_base64(text, mom=False):
    """Synthesize speech with edge-tts; return a OneBot base64:// ref or None."""'''
assert old_def in src, "tts_to_base64 definition not found"
src = src.replace(old_def, new_def, 1)

# 3. Try Fish first for xiaoman replies; mom mode stays edge-tts only.
old_body = '''    clean = clean_for_tts(text)
    if not clean:
        return None'''
new_body = '''    clean = clean_for_tts(text)
    if not clean:
        return None
    if not mom:
        ref = fish_tts_to_base64(text)
        if ref:
            return ref'''
assert old_body in src, "tts_to_base64 body not found"
src = src.replace(old_body, new_body, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("patched OK:", path)
