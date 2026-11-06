#!/usr/bin/env python3
"""patch_bridge_genie.DRAFT.py — 适配 bridge.py.DRAFT 的切桥脚本（DRAFT）

来源：../scripts/patch_bridge_genie.py（原版，写给服务器真本）。
改动唯一一处：原版按服务器版的缩进写死（config 行 8 空格、函数定义 4 空格，
说明真本是嵌套/类内结构）；本草稿 bridge.py.DRAFT 是模块级结构，
config 行 4 空格、函数定义 0 空格，原版脚本断言会失败
（已实测：原版跑草稿报 "config block not found"）。
本副本只改了 old_cfg / new_cfg / old_def / new_def 四段字符串的缩进，
Genie 逻辑（优先、失败回落 edge-tts、妈妈模式永远 edge-tts、响应 <1000 字节
算失败、超时 120 秒）与原版一字未动。

用法（只对草稿）：python3 patch_bridge_genie.DRAFT.py bridge.py.DRAFT
部署服务器真本时，用原版 ../scripts/patch_bridge_genie.py，不要用本副本。
幂等：跑两次，第二次报 already patched。
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
# （缩进按草稿：4 空格。原版是 8 空格。）
old_cfg = '''    "tts_voice": get("TTS_VOICE", "zh-CN-XiaoyiNeural"),
    "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),'''
new_cfg = '''    "tts_voice": get("TTS_VOICE", "zh-CN-XiaoyiNeural"),
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
# （缩进按草稿：函数定义 0 空格。原版是 4 空格。）
old_def = '''def tts_to_base64(text, mom=False):
    """Synthesize speech with edge-tts; return a OneBot base64:// ref or None."""
    voice = CFG["tts_voice_mom"] if mom else CFG["tts_voice"]'''
new_def = '''def genie_tts_to_base64(text):
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
