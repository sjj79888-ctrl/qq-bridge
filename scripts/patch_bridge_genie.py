#!/usr/bin/env python3
"""Patch bridge.py: route xiaoman-mode voice through the Genie TTS service,
falling back to the existing edge-tts path on any failure. Mom mode keeps
edge-tts (Xiaoxuan) unchanged. Idempotent: safe to run twice.

Usage: python3 patch_bridge_genie.py /home/ubuntu/qq-bridge/bridge.py
Exits non-zero if any expected pattern is not found (unless already patched).
"""
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

if "GENIE_URL" in src and "genie_tts_to_base64" in src:
    print("already patched, nothing to do")
    sys.exit(0)

# 1. Config: add genie_url next to the tts_voice lines.
old_cfg = '''        "tts_voice": get("TTS_VOICE", "zh-CN-XiaoyiNeural"),
        "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),'''
new_cfg = '''        "tts_voice": get("TTS_VOICE", "zh-CN-XiaoyiNeural"),
        "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),
        # Genie-TTS sidecar (xiaoman ONNX voice); edge-tts stays as fallback.
        "genie_url": get("GENIE_URL", "http://genie:8000"),'''
assert old_cfg in src, "config block not found"
src = src.replace(old_cfg, new_cfg, 1)

# 2. Ensure urllib/json imports exist (add after the first import line if missing).
if "import urllib.request" not in src:
    m = re.search(r"^import .*$", src, re.M)
    assert m, "no import line found"
    src = src[: m.end()] + "\nimport urllib.request\nimport json" + src[m.end():]

# 3. Add genie_tts_to_base64() right before tts_to_base64(), and make
#    tts_to_base64() try Genie first for non-mom replies.
old_def = '''    def tts_to_base64(text, mom=False):
        """Synthesize speech with edge-tts; return a OneBot base64:// ref or None."""
        voice = CFG["tts_voice_mom"] if mom else CFG["tts_voice"]'''
new_def = '''    def genie_tts_to_base64(text):
        """Synthesize speech with the Genie sidecar; return a OneBot base64:// ref or None."""
        url = CFG["genie_url"].rstrip("/") + "/tts"
        payload = json.dumps({"character_name": "xiaoman",
                              "text": text,
                              "split_sentence": False}).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            if len(data) < 1000:
                log("Genie TTS returned too little data:", len(data))
                return None
            return "base64://" + base64.b64encode(data).decode()
        except Exception as e:
            log("Genie TTS failed:", repr(e))
            return None

    def tts_to_base64(text, mom=False):
        """Synthesize speech; Genie first for xiaoman, edge-tts fallback (mom always edge-tts)."""
        if not mom:
            ref = genie_tts_to_base64(text)
            if ref:
                return ref
            log("Genie TTS unavailable, falling back to edge-tts")
        voice = CFG["tts_voice_mom"] if mom else CFG["tts_voice"]'''
assert old_def in src, "tts_to_base64 definition not found"
src = src.replace(old_def, new_def, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

print("patched OK")
