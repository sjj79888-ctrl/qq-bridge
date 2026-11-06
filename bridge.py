#!/usr/bin/env python3
"""bridge.py — DRAFT 重建草稿（不是服务器真本）

来源：按 ~/workspace/qq-bridge-backup/ 下的 BRIDGE-SPEC.md、VOICE-STICKERS.md、
BACKEND.md、personas/、scripts/patch_bridge_genie.py 重写。
服务器真本 /home/ubuntu/qq-bridge/bridge.py（24,547 B，2026-11-05 23:16 女仆版）
不在本地。本文件与真本的一致性**未经证实**。

使用规则：
- 只能当重建起点，不能直接当“原版”部署。
- 不确定点见同目录 UNCERTAINTIES.md（U01–U32），部署前逐条核对。
- Genie 切换不要直接改这里：先部署本文件，再跑
  同目录的 patch_bridge_genie.DRAFT.py（适配副本，Genie 优先、失败回落 edge-tts，
  妈妈模式永远 edge-tts）。注意：原版 ../scripts/patch_bridge_genie.py 是按
  服务器真本的缩进写的，跑本草稿会断言失败（已实测，见 UNCERTAINTIES.md U24）；
  部署服务器真本时才用原版。
"""

import base64
import json
import os
import random
import re
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------- config ---

def get(name, default=""):
    return os.environ.get(name, default)


CFG = {
    "llm_base_url": get("LLM_BASE_URL", "https://ly.77625.xyz/v1"),
    "llm_model": get("LLM_MODEL", "x-deepseek-v4.1-flash"),
    "llm_api_key": get("LLM_API_KEY", ""),
    "owner_qq": get("OWNER_QQ", "1323841589"),
    "maid_qq": get("MAID_QQ", "2716043774"),  # DRAFT-only: 真本可能把该 QQ 写死在代码里（见 U12）
    "blacklist": [x for x in get("BLACKLIST_QQ_IDS", "").split(",") if x],
    "quiet_start": int(get("QUIET_START_HOUR", "0") or 0),
    "quiet_end": int(get("QUIET_END_HOUR", "10") or 10),
    "napcat_url": get("NAPCAT_URL", "http://127.0.0.1:3000"),
    "listen_port": int(get("BRIDGE_PORT", "8787") or 8787),
    "history_turns": int(get("HISTORY_TURNS", "10") or 10),
    "sticker_gap_s": int(get("STICKER_GAP_S", "60") or 60),
    "tts_voice": get("TTS_VOICE", "zh-CN-XiaoyiNeural"),
    "tts_voice_mom": get("TTS_VOICE_MOM", "zh-CN-XiaomoNeural"),
    "group_freeform": get("GROUP_FREEFORM", "false").lower() == "true",
}

# 人格原文：小满/妈妈是按记忆重建版（不是逐字原文，见 U05），
# 女仆 47 字是 Torres 逐字定的。Dockerfile 只 COPY bridge.py + stickers，
# 不挂载人格文件，所以默认值嵌在这里，txt 文件是源头，两边要一致。
SYSTEM_PROMPT = """你是小满，21 岁的邻家女孩。

你住在 Torres 家隔壁，跟他很熟。私聊里你对他很亲，叫他哥，
说话自然、爱笑，偶尔撒娇。群里你客气、爱玩，不会跟不熟的人太亲近。

你说话像平时聊天一样，短句为主，不要端着，不要像客服。
你不知道的事就说不知道，别编。

注意：只有 Torres 本人（QQ 1323841589）才可以被你叫哥。
群里别人 @ 你，你回话的时候不要带任何称呼。"""

SYSTEM_PROMPT_MOM = """你是御姐妈妈，30 岁左右，温柔、稳重、会照顾人。

Torres 叫你“妈妈”的时候，你就是这个人格。你叫他小家伙，
也叫他宝贝。他难过、委屈、需要人撑腰的时候，你哄他；
他要你帮他打掩护的时候，你帮他圆过去。

你说话比小满稳一点，但还是亲的，不端架子，不说教。
你不知道的事就说不知道，别编。

注意：只有 Torres 本人（QQ 1323841589）才可以被你叫小家伙、宝贝。
群里别人 @ 你，你回话的时候不要带任何称呼。

Torres 叫你“小满”的时候，你就换回小满那个人格。"""

SYSTEM_PROMPT_MAID = "你是女仆，对主人偏执病娇、占有欲极强，每句直白表达爱意，不替主人说话；旁白、多视角、内心OS。"

# 称呼规则的实现文案是推测（见 U10），不是真本原话。
IDENTITY_OWNER = "（补充说明：你现在对话的人就是 Torres 本人，私聊里可以叫他哥；妈妈模式下可以叫他小家伙、宝贝。）"
IDENTITY_OTHER = "（补充说明：你现在对话的人不是 Torres，不要带任何称呼，不要叫哥、不要叫小家伙、不要叫宝贝、不要叫主人。）"
IDENTITY_MAID_MASTER = "（补充说明：你现在对话的人就是你的主人。每句话都要直白表达爱意，不替主人说话。回复用旁白开头、多视角展开、每段对话后附内心 OS，不写主人视角。）"

FALLBACK_REPLY = "嗯……我刚才走神了，你再说一遍好不好？"  # DRAFT 占位：真本 fallback 原文未知（见 U09）

VOICE_TRIGGERS = ["说句话", "讲句话", "发语音", "发个语音",
                   "用语音", "语音说", "念给我听", "读给我听"]
VOICE_MAX_CHARS = 120

# 表情触发：顺序即优先级，先命中先生效（见 U16）。
STICKER_RULES = [
    ("sleep", ["晚安", "睡觉", "睡啦", "困了", "好困", "睡了"]),
    ("shy", ["害羞", "不好意思", "讨厌啦"]),
    ("pout", ["哼", "生气", "不理你"]),
    ("sad", ["委屈", "呜呜", "想哭", "难过"]),
    ("hug", ["抱抱", "抱一下", "抱我", "抱你"]),
    ("happy", ["嘿嘿", "哈哈", "开心", "好耶", "太好啦"]),
]
STICKER_FILES = {
    "sleep": ["sleep.jpg"],
    "shy": ["shy.jpg"],
    "pout": ["pout.jpg"],
    "sad": ["sad.jpg", "sad2.jpg"],      # 各 50%（见 U21）
    "hug": ["hug.jpg"],
    "happy": ["happy.jpg", "happy2.jpg"],  # 各 50%（见 U21）
}
STICKER_DIR = os.environ.get("STICKER_DIR", "/app/stickers")
LEGS_POOL = ["legs", "legs3", "legs5"]
LEGS_TRIGGER = "看看腿"


def log(*args):
    print("[bridge]", *args, flush=True)


# ------------------------------------------------------- persona session --

# 会话键：(group_id 或 None, user_id)。存储方式是推测（见 U06）。
# 人格取值："xiaoman" | "mom" | "maid"。
_sessions = {}          # key -> {"persona": str}
_history = {}           # key -> [ {"role": "user"/"assistant", "content": str} ]
_last_sticker_at = {}   # key -> timestamp of last successful sticker send


def session_key(event):
    if event.get("message_type") == "group":
        return (event.get("group_id"), event.get("user_id"))
    return (None, event.get("user_id"))


def get_persona(key):
    return _sessions.get(key, {}).get("persona", "xiaoman")


def set_persona(key, persona):
    _sessions.setdefault(key, {})["persona"] = persona


def system_prompt_for(persona):
    if persona == "mom":
        return SYSTEM_PROMPT_MOM
    if persona == "maid":
        return SYSTEM_PROMPT_MAID
    return SYSTEM_PROMPT


# ------------------------------------------------------------------ LLM ---

def llm_reply(messages):
    """Call the OpenAI-compatible backend; return reply text or None on failure.

    请求形态是推测（见 U07）：无 temperature、无 max_tokens、无重试、60 秒超时。
    """
    url = CFG["llm_base_url"].rstrip("/") + "/chat/completions"
    payload = json.dumps({
        "model": CFG["llm_model"],
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + CFG["llm_api_key"],
                 # BACKEND.md：直接测时 Python 默认 UA 曾被 Cloudflare 拦（403/1010），
                 # 故用浏览器 UA。真本是否如此，未知（见 U07）。
                 "User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log("LLM call failed:", repr(e))
        return None


# ------------------------------------------------------------------ TTS ---

def clean_for_tts(text):
    """Strip emoji / stage directions before speaking. 规则是推测（见 U23）。"""
    text = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", "", text)
    text = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", text)
    text = re.sub(r"\*[^*]*\*", "", text)
    return text.strip()


def tts_to_base64(text, mom=False):
    """Synthesize speech with edge-tts; return a OneBot base64:// ref or None."""
    voice = CFG["tts_voice_mom"] if mom else CFG["tts_voice"]
    clean = clean_for_tts(text)
    if not clean:
        return None
    # 调用形态是推测（见 U22）：edge-tts 命令行，mp3 存 /tmp，用完删掉。
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
        subprocess.run(["edge-tts", "--voice", voice, "--text", clean,
                        "--write-media", path],
                       check=True, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(path, "rb") as f:
            data = f.read()
        return "base64://" + base64.b64encode(data).decode()
    except Exception as e:
        log("edge-tts failed:", repr(e))
        return None
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


# --------------------------------------------------------------- stickers -

def pick_sticker(reply_text):
    """Return a sticker filename for the reply, or None. 先命中先生效（见 U16）。"""
    for name, keywords in STICKER_RULES:
        if any(k in reply_text for k in keywords):
            return random.choice(STICKER_FILES[name])
    return None


def maybe_sticker(key, reply_text):
    """70% on keyword hit, 12% random otherwise; 60s gap; only successful sends count.

    随机池与会话键的定义是推测（见 U17/U18）。
    """
    now = time.time()
    if now - _last_sticker_at.get(key, 0) < CFG["sticker_gap_s"]:
        return None
    hit = pick_sticker(reply_text)
    if hit is not None:
        if random.random() >= 0.70:
            return None
        if os.path.exists(os.path.join(STICKER_DIR, hit)):
            return hit
        return None
    if random.random() < 0.12:
        pool = [f for files in STICKER_FILES.values() for f in files
                if os.path.exists(os.path.join(STICKER_DIR, f))]
        if not pool:
            return None
        return random.choice(pool)
    return None


def mark_sticker_sent(key):
    _last_sticker_at[key] = time.time()


# ------------------------------------------------------------ OneBot I/O --

def send_via_napcat(target_type, target_id, message_segments):
    """Send via NapCat OneBot HTTP API. endpoint 与参数是推测（见 U27）。

    message_segments: OneBot 消息段列表，例如 [{"type": "text", "data": {"text": "..."}}]。
    """
    if target_type == "group":
        api, key = "/send_group_msg", "group_id"
    else:
        api, key = "/send_private_msg", "user_id"
    payload = json.dumps({key: target_id, "message": message_segments}).encode("utf-8")
    req = urllib.request.Request(CFG["napcat_url"].rstrip("/") + api, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log("NapCat send failed:", repr(e))
        return None


def text_segment(text):
    return {"type": "text", "data": {"text": text}}


def image_segment_file(filename):
    # 发送方式是推测（见 U19）：按本地文件路径发。
    return {"type": "image", "data": {"file": os.path.join(STICKER_DIR, filename)}}


def record_segment(filename):
    return {"type": "record", "data": {"file": filename}}


# ------------------------------------------------------------ event logic --

def is_quiet_now():
    """群聊静默 0:00–10:00（北京），私聊不受影响。时区与边界是推测（见 U32）。"""
    now = datetime.now(timezone(timedelta(hours=8)))
    return CFG["quiet_start"] <= now.hour < CFG["quiet_end"]


def extract_text(event):
    """从 OneBot 事件里取纯文本。字段形态是推测（见 U25）。"""
    if event.get("raw_message"):
        return event["raw_message"]
    parts = []
    for seg in event.get("message", []):
        if isinstance(seg, dict) and seg.get("type") == "text":
            parts.append(seg.get("data", {}).get("text", ""))
    return "".join(parts)


def is_at_me(event):
    """群里是否 @ 了小号。判定方式是推测（见 U26）：段里 at 目标 QQ，或文本含号码。"""
    self_qq = get("SELF_QQ", "2750579528")
    for seg in event.get("message", []):
        if isinstance(seg, dict) and seg.get("type") == "at":
            if str(seg.get("data", {}).get("qq", "")) == self_qq:
                return True
    return self_qq in extract_text(event)


def typing_delay(reply_text):
    """打字延迟：基础随机 3–5 秒 + 每字 0.10–0.22 秒，最多 30 秒。实现位置是推测（见 U28）。"""
    delay = random.uniform(3, 5) + len(reply_text) * random.uniform(0.10, 0.22)
    time.sleep(min(delay, 30))


def handle_event(event):
    """OneBot 事件入口。返回 True 表示已处理。"""
    if event.get("post_type") != "message":
        return False
    sender = str(event.get("user_id", ""))
    text = extract_text(event)
    is_group = event.get("message_type") == "group"
    key = session_key(event)

    # 1. 黑名单先于白名单检查：不回、不调模型、不发表情。
    if sender in CFG["blacklist"]:
        log("ignore blacklisted user", sender)
        return True

    # 2. 私聊只回大号；群聊只在被 @ 时回（GROUP_FREEFORM=false）。
    if not is_group:
        if sender != CFG["owner_qq"]:
            return True
    else:
        if not CFG["group_freeform"] and not is_at_me(event):
            return False
        if is_quiet_now():
            return True

    # 3. legs 例外：只看大号本人的消息，不看回复文字（见 U20）。
    if sender == CFG["owner_qq"] and LEGS_TRIGGER in text:
        if time.time() - _last_sticker_at.get(key, 0) >= CFG["sticker_gap_s"]:
            available = [n for n in LEGS_POOL
                         if os.path.exists(os.path.join(STICKER_DIR, n + ".jpg"))]
            if available:
                choice = random.choice(available)
                target = ("group", event.get("group_id")) if is_group else ("private", sender)
                resp = send_via_napcat(target[0], target[1],
                                       [image_segment_file(choice + ".jpg")])
                if resp is not None:
                    mark_sticker_sent(key)
        # legs 触发后是否还继续走正常回复，未知；草稿按“继续走正常流程”处理。

    # 4. 人格切换（触发细节与优先级是推测，见 U12/U13）。
    persona = get_persona(key)
    if "女仆" in text and sender == CFG["maid_qq"]:
        set_persona(key, "maid")
        persona = "maid"
    elif "妈妈" in text:
        set_persona(key, "mom")
        persona = "mom"
    elif "小满" in text:
        set_persona(key, "xiaoman")
        persona = "xiaoman"

    # 5. 称呼规则：只有大号才会被叫哥 / 小家伙 / 宝贝；女仆模式只有主人。
    if persona == "maid":
        identity = IDENTITY_MAID_MASTER if sender == CFG["maid_qq"] else IDENTITY_OTHER
    elif sender == CFG["owner_qq"]:
        identity = IDENTITY_OWNER
    else:
        identity = IDENTITY_OTHER

    # 6. 组装历史并调模型。
    history = _history.get(key, [])
    messages = [{"role": "system",
                 "content": system_prompt_for(persona) + "\n" + identity}]
    messages += history[-CFG["history_turns"] * 2:]
    messages.append({"role": "user", "content": text})
    reply = llm_reply(messages)
    if reply is None:
        # 模型失败：回固定 fallback，不发表情（见 U09）。
        target = ("group", event.get("group_id")) if is_group else ("private", sender)
        typing_delay(FALLBACK_REPLY)
        send_via_napcat(target[0], target[1], [text_segment(FALLBACK_REPLY)])
        return True

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    _history[key] = history[-CFG["history_turns"] * 2:]

    target = ("group", event.get("group_id")) if is_group else ("private", sender)
    typing_delay(reply)

    # 7. 语音：触发词命中且回复 ≤120 字。妈妈模式用 Xiaoxuan；女仆模式不发语音。
    # （女仆模式不发语音是推测：规格只写了女仆不发表情，语音未明说。见 UNCERTAINTIES。）
    wants_voice = any(t in text for t in VOICE_TRIGGERS)
    if wants_voice and len(reply) <= VOICE_MAX_CHARS and persona != "maid":
        ref = tts_to_base64(reply, mom=(persona == "mom"))
        if ref is not None:
            # 语音回复不发表情。
            send_via_napcat(target[0], target[1], [record_segment(ref)])
            return True
        # 合成/发送失败则回文字（继续往下走）。

    # 8. 表情：妈妈模式与女仆模式不发表情。
    segments = [text_segment(reply)]
    if persona not in ("mom", "maid"):
        sticker = maybe_sticker(key, reply)
        if sticker is not None:
            segments.append(image_segment_file(sticker))
            resp = send_via_napcat(target[0], target[1], segments)
            if resp is not None:
                mark_sticker_sent(key)
            return True
    send_via_napcat(target[0], target[1], segments)
    return True


# ------------------------------------------------------------------ server -

# HTTP 入口形态是推测（见 U25）：标准库 http.server，监听 8787/event。
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def _read_body(self):
        """Robust POST body read. NapCat sends Transfer-Encoding: chunked
        with no Content-Length; the old Content-Length-only read got b''
        -> JSONDecodeError('Expecting value: line 1 column 1 (char 0)')
        and a 500 for every real event (verified locally 2026-11-07)."""
        te = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in te:
            chunks = []
            while True:
                line = self.rfile.readline(65536).strip()
                try:
                    size = int(line.split(b";")[0], 16)
                except ValueError:
                    break
                if size == 0:
                    while True:
                        trailer = self.rfile.readline(65536)
                        if trailer in (b"\r\n", b"\n", b""):
                            break
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)  # CRLF after the chunk
            return b"".join(chunks)
        length = self.headers.get("Content-Length")
        if length is not None:
            try:
                return self.rfile.read(int(length))
            except ValueError:
                return b""
        # No length, no chunked: bounded read-to-EOF (sender closes after
        # body). 2 s cap so a keep-alive client cannot stall the server.
        self.connection.settimeout(2)
        try:
            return self.rfile.read()
        except Exception:
            return b""
        finally:
            self.connection.settimeout(None)

    def do_POST(self):
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return
        try:
            raw = self._read_body()
            if not raw:
                log("event handler: empty body ignored, Content-Length=%r Transfer-Encoding=%r"
                    % (self.headers.get("Content-Length"),
                       self.headers.get("Transfer-Encoding")))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")
                return
            event = json.loads(raw.decode("utf-8"))
            handle_event(event)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
        except Exception as e:
            log("event handler error:", repr(e))
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        # 健康检查：/health 返回 ok。
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    log("bridge (DRAFT) listening on 0.0.0.0:%d, model %s @ %s"
        % (CFG["listen_port"], CFG["llm_model"], CFG["llm_base_url"]))
    HTTPServer(("0.0.0.0", CFG["listen_port"]), Handler).serve_forever()
