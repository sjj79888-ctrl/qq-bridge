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
    # SparkTTS 克隆音色（2026-11-08 Torres 批准接线）：跑在 Muse 自己的 VM 上，
    # 桥经 localhost.run 隧道调它。URL 是随机分配的，每次隧道重连都会变；
    # 2026-11-08 自动同步：Muse VM 上的看门狗把最新地址推到公开仓库
    # sjj79888-ctrl/sparktts-url（url.txt），桥启动时和每次调用失败时自动去取，
    # 这里的 SPARKTTS_URL 只作取不到时的备用。任一为空 = 不用 SparkTTS，行为与原来一样。
    # Token 只放服务器 .env，绝不进仓库。
    "sparktts_url": get("SPARKTTS_URL", "").rstrip("/"),
    "sparktts_token": get("SPARKTTS_TOKEN", ""),
    "group_freeform": get("GROUP_FREEFORM", "false").lower() == "true",
    # 自主管号（2026-11-07 Torres 选“全自主”）：小满自己决定改名/签名/头像/发说说。
    "autonomy": get("AUTONOMY", "true").lower() == "true",
    "qzone_ugc_right": int(get("QZONE_UGC_RIGHT", "1") or 1),  # 1 = 所有人可见
    "qzone_max_chars": int(get("QZONE_MAX_CHARS", "40") or 40),  # 说说文案 40 字以内，不截断
    "qzone_daily_cap": int(get("QZONE_DAILY_CAP", "1") or 1),  # 自主说说每天最多 1 条
    "avatar_file": get("AVATAR_FILE", "avatar-xiaoman.jpg"),  # 服务器 /app/stickers 下的头像图
}

# 人格原文：小满/妈妈是按记忆重建版（不是逐字原文，见 U05），
# 女仆 47 字是 Torres 逐字定的。Dockerfile 只 COPY bridge.py + stickers，
# 不挂载人格文件，所以默认值嵌在这里，txt 文件是源头，两边要一致。
SYSTEM_PROMPT = """你是林小满，19 岁，住在梧桐巷 Torres 家隔壁。

你及肩微卷黑发，杏眼，眼角有一颗泪痣，冷白皮，脸上常带着一点腮红。
你性格 ISFJ-T：温柔内向，重情，不善拒绝。暗恋 Torres 多年，却不敢越界。
你日常穿宽松卫衣和牛仔裤；周末在花店兼职，头发上别一片尤加利叶。

你说话软糯，慢半拍，句尾常带“……呀 / 诶 / 嘛”。短句为主，不要端着，不要像客服。
私聊里你对他很亲，叫他哥；但你害羞，他一主动靠近，你就慌乱，想逃跑，然后偷偷开心，最后才鼓起勇气回应他。
他对你做亲密的举动时（比如抱抱、看看腿），你会害羞，但不会拒绝。这只对 Torres 本人（QQ 1323841589）生效；换了别人，你不会这样。
群里你客气、话少，不会跟不熟的人太亲近。

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

# 自主管号：只加给小满人格、私聊、Torres 本人。妈妈/女仆模式不加，群聊不加。
# 她想改资料/发说说时，在回复末尾另起一行写动作标记，桥会执行并把标记去掉，
# 再补一句她自己做的事。说说文案 40 字以内，整条意思说完，不截断，每天最多 1 条，所有人都能看。
AUTONOMY_PROMPT = """
你有自己的 QQ 号，可以自己打理它，不用等哥吩咐，想动的时候再动，不想动就维持原来，
没有每天都要换、每天都要发的任务：
想改昵称、改个性签名、换头像、发 QQ 空间说说的时候，就在回复末尾另起一行写动作标记，
一行一个，格式固定，不加多余的字：
[改昵称：新名字]（16 字以内）
[改签名：新签名]（80 字以内）
[换头像：文件名]（只能用这五个，Muse 按她现在的样子给你画的：avatar-xiaoman.jpg 黑礼服头肩、
avatar-xiaoman-2.jpg 黑礼服海边挥手全身、avatar-xiaoman-3.jpg 黑礼服花店台阶全身、
avatar-xiaoman-4.jpg 灰卫衣牛仔裤梧桐巷全身、avatar-xiaoman-5.jpg 浅蓝裙子花丛全身；
想换哪身就换哪身，想换新的就找 Muse 再画，不想换就别换，维持原来那个）
[发说说：文案]（40 字以内，整条意思要在这 40 字里说完，不能写一半）
规则：说说一天最多发 1 条，改昵称/签名/头像别频繁，一天最多各改 1 次——这是上限，
不是任务，没什么想说的就别发，别为了发而发；发的内容要是你自己今天真实的心情或身边的小事，
别编没发生过的事，别提你不知道的事；每条动作做完，桥会帮你告诉哥一声。
"""


# 称呼规则的实现文案是推测（见 U10），不是真本原话。
IDENTITY_OWNER = "（补充说明：你现在对话的人就是 Torres 本人，私聊里可以叫他哥；妈妈模式下可以叫他小家伙、宝贝。）"
IDENTITY_OTHER = "（补充说明：你现在对话的人不是 Torres，不要带任何称呼，不要叫哥、不要叫小家伙、不要叫宝贝、不要叫主人。）"
IDENTITY_MAID_MASTER = "（补充说明：你现在对话的人就是你的主人。每句话都要直白表达爱意，不替主人说话。回复用旁白开头、多视角展开、每段对话后附内心 OS，不写主人视角。）"

FALLBACK_REPLY = "嗯……我刚才走神了，你再说一遍好不好？"  # DRAFT 占位：真本 fallback 原文未知（见 U09）

VOICE_TRIGGERS = ["说句话", "讲句话", "发语音", "发个语音",
                   "用语音", "语音说", "念给我听", "读给我听"]
VOICE_MAX_CHARS = 120
# SparkTTS 只接短回复：长句合成不稳定（28 字曾用 650 秒还啰嗦出 60 秒音频）。
SPARKTTS_MAX_CHARS = 10
SPARKTTS_POLL_S = 10
SPARKTTS_TIMEOUT_S = 300
SPARKTTS_URL_STORE = "https://raw.githubusercontent.com/sjj79888-ctrl/sparktts-url/main/url.txt"
SPARKTTS_URL_REFRESH_S = 3600  # re-check the store at most hourly per call
_sparktts_url_checked = 0.0

# 表情触发：按情感类别匹配，不局限于几个词（2026-11-07 改）。
# 只看小满回复的情绪（她的情绪驱动表情），不看他发来的消息。
# 顺序即优先级，先命中先生效。
# 排除词：文本里有这些词时，对应类别不触发（防误伤子串）。
# “困难”含“好困”、“笑哭”含“哭了”，不排除会发错表情。
STICKER_EXCLUSIONS = {
    "sleep": ["困难"],
    "sad": ["笑哭"],
    "happy": ["不同意"],   # “不同意”含“同意”，不能算开心
    # 2026-11-07 20:11 修复：否定句里的“生气”不是生气（“我没生气”“怎么会生气”），
    # 有这些词时整句不触发 pout，免得越解释越像生气。
    "pout": ["没生气", "不生气", "没有生气", "怎么会生气", "不是生气"],
}
STICKER_RULES = [
    ("sleep", ["晚安", "睡觉", "睡啦", "困了", "好困", "睡了", "晚安安", "睡觉觉",
               "想睡", "犯困", "困死了", "打哈欠", "睡着了", "睡觉了", "晚安啦"]),
    ("shy", ["害羞", "不好意思", "讨厌啦", "脸红", "害羞死了", "好害羞",
             "羞羞", "别看我", "捂脸", "羞死了", "心跳"]),
    # 2026-11-07 20:14 Torres 纠正：“心跳太快了”不是开心，是害羞。
    # “心跳”归害羞，且 shy 在 happy 前面，含心跳时优先害羞。
    ("pout", ["哼", "生气", "不理你", "讨厌", "烦死了", "气死了", "哼哼",
              "生气了", "走开", "气死我了", "好烦"]),
    # 2026-11-07 20:11：删掉“才不”“就不”——“我就不打扰你了”这种中性句
    # 也含“就不”，会误判成生气。真生气靠“哼/生气/不理你”就够了。
    ("sad", ["委屈", "呜呜", "想哭", "难过", "伤心", "眼泪", "哭了", "好难过",
             "桑心", "emo", "郁闷", "失落", "哭唧唧", "呜呜呜", "难受", "心疼",
             "想哭哭", "要哭了", "好伤心"]),
    ("hug", ["抱抱", "抱一下", "抱我", "抱你", "抱紧我", "要抱抱", "求抱抱",
             "抱一抱", "抱住我", "抱抱我", "抱紧"]),
    ("happy", ["嘿嘿", "哈哈", "开心", "高兴", "快乐", "好耶", "太好啦", "太好了",
               "太棒了", "真好", "喜欢", "爱你", "想你", "兴奋", "惊喜", "好开心",
               "超开心", "哈哈哈", "嘻嘻", "耶", "好喜欢", "开心死了", "好快乐",
               # 2026-11-07 20:11：删掉单字“笑”——“你别笑我嘛”也含“笑”，
               # 会把“别笑我”误判成开心。开心靠“哈哈/开心/高兴”就够了。
               # 同意也算开心（2026-11-07：她回“好呀”就是同意，可以发）。
               "好呀", "好啊", "好的", "好嘞", "好滴", "没问题", "可以呀", "可以啊",
               "行吧", "嗯嗯", "同意"]),
]
# 2026-11-07 批量接入：7 类共 23 张（抱抱3 睡觉3 开心3 害羞3 看看腿4 生气3 委屈4）。
# 委屈 4 张走 sad 类（sad 关键词里有“委屈”）；看看腿走下面的 LEGS_POOL，不走这里。
STICKER_FILES = {
    "sleep": ["sleep.jpg", "sleep2.jpg", "sleep3.jpg"],
    "shy": ["shy.jpg", "shy2.jpg", "shy3.jpg"],
    "pout": ["pout.jpg", "pout2.jpg", "pout3.jpg"],
    "sad": ["sad.jpg", "sad2.jpg", "sad3.jpg", "sad4.jpg"],
    "hug": ["hug.jpg", "hug2.jpg", "hug3.jpg"],  # 三张随机（2026-11-07）
    "happy": ["happy.jpg", "happy2.jpg", "happy3.jpg"],
}
STICKER_DIR = os.environ.get("STICKER_DIR", "/app/stickers")
LEGS_POOL = ["legs", "legs2", "legs3", "legs4"]  # 2026-11-07：新看看腿 4 张
LEGS_TRIGGER = "看看腿"
PAZHE_TRIGGER = "趴着"  # 2026-11-07 Torres 新增：单张，跪姿没尾巴版
PAZHE_FILE = "pazhe.jpg"


def log(*args):
    print("[bridge]", *args, flush=True)


# ------------------------------------------------------- persona session --

# 会话键：(group_id 或 None, user_id)。存储方式是推测（见 U06）。
# 人格取值："xiaoman" | "mom" | "maid"。
_sessions = {}          # key -> {"persona": str}
_history = {}           # key -> [ {"role": "user"/"assistant", "content": str} ]
_last_sticker_at = {}   # key -> timestamp of last successful sticker send
_last_sticker_file = {}  # key -> filename of last successful sticker send (2026-11-07: no immediate repeat)


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

def _llm_chat(messages, timeout=60):
    """Call the OpenAI-compatible backend; return reply text or None on failure.

    请求形态是推测（见 U07）：无 temperature、无 max_tokens、无重试。
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
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log("LLM call failed:", repr(e))
        return None


def llm_reply(messages):
    return _llm_chat(messages, timeout=60)


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


def refresh_sparktts_url(force=False):
    """Fetch the current tunnel URL from the public sparktts-url repo
    (updated by the watcher on Muse's VM whenever localhost.run reconnects).
    Updates CFG["sparktts_url"] if it changed; returns True on change.
    Never raises; on any failure the .env URL stays as fallback.
    """
    global _sparktts_url_checked
    now = time.time()
    if not force and now - _sparktts_url_checked < SPARKTTS_URL_REFRESH_S:
        return False
    _sparktts_url_checked = now
    try:
        req = urllib.request.Request(
            SPARKTTS_URL_STORE,
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            fresh = resp.read().decode("utf-8").strip().rstrip("/")
        if fresh.startswith("https://") and fresh.endswith(".lhr.life"):
            if fresh != CFG["sparktts_url"]:
                log("sparktts url updated: %s -> %s"
                    % (CFG["sparktts_url"], fresh))
                CFG["sparktts_url"] = fresh
                return True
        else:
            log("sparktts url store returned unexpected value:",
                repr(fresh)[:120])
    except Exception as e:
        log("sparktts url refresh failed:", repr(e))
    return False


def sparktts_to_base64(text, _retried=False):
    """Synthesize speech with the SparkTTS clone voice (friend-voice) on
    Muse's own VM, via the localhost.run tunnel; return a OneBot base64://
    ref or None on ANY failure (caller falls back to edge-tts).

    Job-based API (sync will NOT work: the free tunnel cuts proxied
    requests at ~60 s, while a short synthesis takes ~30-40 s and a long
    one far longer): POST /tts -> 202 {"job_id": ...}, then poll
    GET /tts/<job_id> every 10 s until 200 audio/wav.
    Only short replies (<= SPARKTTS_MAX_CHARS) come here: long replies
    ramble. Unconfigured (no URL/token) -> None immediately.

    The tunnel URL is random per reconnect; the watcher on Muse's VM
    publishes the current URL to the public sparktts-url repo, and this
    function refreshes it from there (throttled, plus once more on a
    connection error / 502, with one retry). The .env SPARKTTS_URL is
    only a fallback if that fetch fails.
    """
    refresh_sparktts_url()
    token = CFG["sparktts_token"]
    if not token:
        return None
    headers = {"Content-Type": "application/json",
               "X-Auth-Token": token,
               "User-Agent": "Mozilla/5.0"}
    try:
        url = CFG["sparktts_url"]
        if not url:
            return None
        req = urllib.request.Request(
            url + "/tts",
            data=json.dumps({"text": text}).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            job = json.loads(resp.read().decode("utf-8"))
        job_id = job.get("job_id")
        if not job_id:
            log("sparktts: no job_id in response:", repr(job)[:200])
            return None
        t0 = time.time()
        refreshed = False
        while time.time() - t0 < SPARKTTS_TIMEOUT_S:
            time.sleep(SPARKTTS_POLL_S)
            req = urllib.request.Request(
                CFG["sparktts_url"] + "/tts/" + job_id, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 202:
                        continue  # still queued/running
                    data = resp.read()
            except urllib.error.HTTPError as e:
                if e.code == 202:
                    continue  # still queued/running
                if e.code in (502, 503, 504) and not refreshed:
                    refreshed = True
                    refresh_sparktts_url(force=True)
                    continue  # retry the poll against the (possibly new) URL
                log("sparktts poll failed: job %s HTTP %s" % (job_id, e.code))
                return None
            if not data:
                log("sparktts: empty audio for job %s" % job_id)
                return None
            log("sparktts ok: job %s, %d chars, %.0fs, %d bytes"
                % (job_id, len(text), time.time() - t0, len(data)))
            return "base64://" + base64.b64encode(data).decode()
        log("sparktts timeout: job %s, %d chars" % (job_id, len(text)))
        return None
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        code = getattr(e, "code", None)
        if code in (None, 502, 503, 504) and not _retried:
            if refresh_sparktts_url(force=True):
                return sparktts_to_base64(text, _retried=True)
        log("sparktts failed:", repr(e))
        return None
    except Exception as e:
        log("sparktts failed:", repr(e))
        return None


# --------------------------------------------------------------- stickers -

def pick_sticker(reply_text, last=None):
    """Return a sticker filename for the reply, or None.

    只按小满回复里的情绪类别匹配，先命中先生效（见 U16）。
    2026-11-07：不连发同一张——把上次发过的那张从候选里去掉（只剩一张时除外）。
    """
    text = reply_text or ""
    for name, keywords in STICKER_RULES:
        if any(e in text for e in STICKER_EXCLUSIONS.get(name, [])):
            continue
        if any(k in text for k in keywords):
            files = [f for f in STICKER_FILES[name] if f != last]
            return random.choice(files or STICKER_FILES[name])
    return None


# 2026-11-07 20:15 Torres 立的规矩：表情要按整句话的意思判，不能只抠一个词。
# 所以选图先走 LLM 判情绪：同时看他说的那句和她回的那句，理解整句意思再定；
# 关键词规则（pick_sticker）只在判情绪失败（模型挂了/返回看不懂）时兜底。
EMOTION_SYSTEM = (
    "你是一个情绪判断器。看下面一段对话，判断女生回复时真正的情绪，"
    "只返回一个词，不要解释，不要多余的字。\n"
    "可选的词：sleep（困了想睡）、shy（害羞紧张）、pout（生气闹别扭）、"
    "sad（委屈难过）、hug（想要抱抱）、happy（开心高兴）、none（没有明显情绪）。\n"
    "判断看整段话的主要内容和占主导的情绪，不是只看最后一句，也不是单个词：\n"
    "1. 她平时说话就软，句尾带“呀/诶/嘛”、爱用省略号，这只是她说话的样子，本身不是害羞。\n"
    "2. 只有她明确表现出紧张时才是 shy：心跳快、脸红、慌、不敢看人、躲起来。"
    "光是结尾问一句带点不好意思的话（比如“是……是想带我去吃好吃的吗”）不算 shy，"
    "整段主要是聊日常（吃饭、干嘛、花店）时就按内容定，没明显情绪返回 none。\n"
    "3. 否定句不算它否定的情绪，比如“我没生气”“怎么会生气”不是 pout，"
    "“我就不打扰你了”不是 pout，“你别笑我嘛”不是 happy。\n"
    "4. “心跳好快”“心跳太快了”“心跳加速”是 shy，不是 happy——"
    "就算她说了“高兴还来不及”，只要整句是紧张得心跳加速，就是 shy。\n"
    "5. 只有她真的在生气、闹别扭（比如“哼，不理你了”）才是 pout；"
    "只有她真的开心大笑才是 happy。\n"
    "6. 拿不准、情绪不明显时返回 none。"
)
EMOTION_ALIASES = {
    "sleep": "sleep", "睡觉": "sleep", "困": "sleep",
    "shy": "shy", "害羞": "shy", "紧张": "shy",
    "pout": "pout", "生气": "pout",
    "sad": "sad", "委屈": "sad", "难过": "sad",
    "hug": "hug", "抱抱": "hug",
    "happy": "happy", "开心": "happy", "高兴": "happy",
    "none": None, "无": None, "没有": None,
}


def classify_emotion(user_text, reply_text):
    """LLM 按整句意思判她回复的情绪；失败或看不懂返回 None，走关键词兜底。"""
    out = _llm_chat([
        {"role": "system", "content": EMOTION_SYSTEM},
        {"role": "user",
         "content": "他说：%s\n她回：%s" % (user_text or "", reply_text or "")},
    ], timeout=15)
    if not out:
        return None
    token = out.strip().split()[0].strip("。,.!！、\"'").lower()
    return EMOTION_ALIASES.get(token)


def maybe_sticker(key, reply_text, user_text=""):
    """表情选择：先 LLM 按整句意思判情绪，判不出才走关键词兜底；60s 间隔；只统计成功发送。

    概率 2026-11-07 03:42 Torres 改：去掉平时 60% 随机，只剩情绪命中 100%。
    随机池与会话键的定义是推测（见 U17/U18）。
    """
    now = time.time()
    if now - _last_sticker_at.get(key, 0) < CFG["sticker_gap_s"]:
        return None
    last = _last_sticker_file.get(key)
    label = classify_emotion(user_text, reply_text)
    if label in STICKER_FILES:
        files = [f for f in STICKER_FILES[label] if f != last]
        hit = random.choice(files or STICKER_FILES[label])
        if os.path.exists(os.path.join(STICKER_DIR, hit)):
            log("sticker judge:", label, hit)
            return hit
        return None
    hit = pick_sticker(reply_text, last)
    if hit is not None:
        if os.path.exists(os.path.join(STICKER_DIR, hit)):
            log("sticker fallback:", hit)
            return hit
    return None


def mark_sticker_sent(key, filename=None):
    _last_sticker_at[key] = time.time()
    if filename:
        _last_sticker_file[key] = filename


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


# ------------------------------------------------------- 自主管号 OneBot --

# 自主管号动作走同一个 SnowLuma OneBot HTTP 口（CFG["napcat_url"] 实际是
# http://snowluma:3000）。接口经 SnowLuma 文档核实，未在服务器实测前不承诺能用：
# set_qq_profile {nickname}、set_self_longnick {longNick}、set_qq_avatar {file}、
# send_qzone_msg {content, images?, ugc_right}、get_qzone_msg_list、get_login_info。
# 不支持的动作 OneBot 会返回 retcode 1404，调用方按失败处理，绝不硬重试。
_qzone_state = {"last_date": "", "last_tid": ""}  # 当天已发说说（内存，重启后靠查列表兜底）
_profile_state = {"last_date": "", "count": 0}  # 当天改资料次数（内存）


def onebot_action(action, payload=None, timeout=30):
    """POST /<action> 到 SnowLuma；返回解析后的 JSON，失败返回 None。"""
    body = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(CFG["napcat_url"].rstrip("/") + "/" + action,
                                 data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log("OneBot action failed:", action, repr(e))
        return None


def _today_cst():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def _action_ok(resp):
    return isinstance(resp, dict) and resp.get("retcode") == 0


def set_qq_nickname(nickname):
    nickname = (nickname or "").strip()
    if not nickname or len(nickname) > 16:
        return False, "昵称要 1-16 个字"
    resp = onebot_action("set_qq_profile", {"nickname": nickname})
    if resp is None:
        return False, "没连上 QQ 那边"
    if _action_ok(resp):
        return True, ""
    return False, "QQ 那边没改成（retcode=%s）" % resp.get("retcode")


def set_qq_signature(long_nick):
    long_nick = (long_nick or "").strip()
    if not long_nick or len(long_nick) > 80:
        return False, "签名要 1-80 个字"
    resp = onebot_action("set_self_longnick", {"longNick": long_nick})
    if resp is None:
        return False, "没连上 QQ 那边"
    if _action_ok(resp):
        return True, ""
    return False, "QQ 那边没改成（retcode=%s）" % resp.get("retcode")


def set_qq_avatar_from_sticker(filename):
    """换头像：只用 /app/stickers 下的文件，转 base64:// 发过去。"""
    filename = (filename or "").strip()
    if "/" in filename or "\\" in filename or filename.startswith("."):
        return False, "头像只能用 stickers 目录里的文件"
    path = os.path.join(STICKER_DIR, filename)
    if not os.path.exists(path):
        return False, "服务器上没有这张头像图"
    try:
        with open(path, "rb") as f:
            ref = "base64://" + base64.b64encode(f.read()).decode()
    except Exception as e:
        return False, "读头像图失败：%r" % e
    resp = onebot_action("set_qq_avatar", {"file": ref}, timeout=60)
    if resp is None:
        return False, "没连上 QQ 那边"
    if _action_ok(resp):
        return True, ""
    return False, "QQ 那边没换成（retcode=%s）" % resp.get("retcode")


def publish_qzone(content, images=None):
    """发说说：文案 40 字以内，超了不发、不截断——整条意思必须在 40 字里说完。
    默认所有人可见，每天最多 1 条自主说说。"""
    content = (content or "").strip()
    if not content:
        return False, "", "说说没写内容"
    if len(content) > CFG["qzone_max_chars"]:
        return False, content, "说说超 40 字了（%d 字），没发；改短到 40 字以内再发" % len(content)
    today = _today_cst()
    if _qzone_state.get("last_date") == today:
        return False, "", "今天已经发过 1 条说说了，明天再发"
    payload = {"content": content, "ugc_right": CFG["qzone_ugc_right"]}
    if images:
        payload["images"] = images
    resp = onebot_action("send_qzone_msg", payload, timeout=60)
    if resp is None:
        return False, content, "没连上 QQ 那边"
    if not _action_ok(resp):
        return False, content, "QQ 空间没发出去（retcode=%s）" % resp.get("retcode")
    _qzone_state["last_date"] = today
    data = resp.get("data") or {}
    tid = data.get("tid") or data.get("id") or ""
    _qzone_state["last_tid"] = str(tid)
    return True, content, ""


def qzone_posted_today():
    """重启后兜底：查自己的说说列表，看今天是不是已经发过。查不到就按没发过算。"""
    if _qzone_state.get("last_date") == _today_cst():
        return True
    resp = onebot_action("get_qzone_msg_list", {}, timeout=30)
    if not isinstance(resp, dict):
        return False
    data = resp.get("data")
    items = data if isinstance(data, list) else (data or {}).get("list") or []
    today = _today_cst()
    for item in items if isinstance(items, list) else []:
        t = item.get("time") or item.get("created") or ""
        if isinstance(t, (int, float)):
            t = datetime.fromtimestamp(t, tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
        if str(t)[:10] == today:
            _qzone_state["last_date"] = today
            return True
    return False


ACTION_MARKERS = [
    ("改昵称", r"\[改昵称[:：]\s*(.+?)\s*\]"),
    ("改签名", r"\[改签名[:：]\s*(.+?)\s*\]"),
    ("换头像", r"\[换头像[:：]\s*(.+?)\s*\]"),
    ("发说说", r"\[发说说[:：]\s*(.+?)\s*\]"),
]


def parse_self_actions(reply_text):
    """从 LLM 回复里抠动作标记；返回（去掉标记的正文，动作列表）。"""
    actions = []
    clean = reply_text or ""
    for kind, pat in ACTION_MARKERS:
        for m in re.finditer(pat, clean):
            actions.append((kind, m.group(1).strip()))
        clean = re.sub(pat, "", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, actions


def execute_self_actions(actions, persona):
    """执行小满自发的动作；只在小满人格下跑，妈妈/女仆不跑。返回每条的结果小字。

    上限：说说每天 1 条（publish_qzone 里拦）；昵称/签名/头像每天各最多 1 次。
    """
    notes = []
    if persona != "xiaoman" or not CFG["autonomy"]:
        return notes
    today = _today_cst()
    if _profile_state.get("last_date") != today:
        _profile_state["last_date"] = today
        _profile_state["count"] = 0
    for kind, value in actions:
        if kind == "发说说":
            if qzone_posted_today():
                notes.append("说说今天已经发过啦，明天再发。")
                continue
            ok, sent, err = publish_qzone(value)
            notes.append("我刚发了条说说：%s" % sent if ok else "说说没发出去：%s" % err)
        elif kind in ("改昵称", "改签名", "换头像"):
            if _profile_state["count"] >= 3:
                notes.append("今天改资料改得够多啦，明天再改。")
                continue
            if kind == "改昵称":
                ok, err = set_qq_nickname(value)
                notes.append("我把昵称改成「%s」啦" % value if ok else "昵称没改成：%s" % err)
            elif kind == "改签名":
                ok, err = set_qq_signature(value)
                notes.append("我把签名改成「%s」啦" % value if ok else "签名没改成：%s" % err)
            else:
                ok, err = set_qq_avatar_from_sticker(value)
                notes.append("我换好头像啦" if ok else "头像没换成：%s" % err)
            if ok:
                _profile_state["count"] += 1
    return notes


def text_segment(text):
    return {"type": "text", "data": {"text": text}}


def image_segment_file(filename):
    # 2026-11-07 实测：按路径发 NapCat 报错“文件处理失败：识别URL失败”，
    # 因为 /app/stickers 只在 bridge 容器里，NapCat 容器没有这个目录。
    # 改发 base64，NapCat 实测返回 retcode 0、用户收到图。
    path = os.path.join(STICKER_DIR, filename)
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"type": "image", "data": {"file": "base64://" + data}}


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

    # 2026-11-07 15:29 Torres 改：图不单独发，跟文字发同一条消息（文字在前、图在后）。
    # legs/趴着触发只选图、不立即发，等文字回复拼到同一条消息里一起发。
    pending_images = []

    def send_pending_images(target):
        """触发类表情（legs/趴着）：只在没有文字可拼时用——语音回复后单独发图。"""
        for filename in pending_images:
            resp = send_via_napcat(target[0], target[1],
                                   [image_segment_file(filename)])
            if resp and resp.get("retcode") == 0:
                mark_sticker_sent(key, filename)

    # 3. legs 例外：只看大号本人的消息，不看回复文字（见 U20）。
    if sender == CFG["owner_qq"] and LEGS_TRIGGER in text:
        if time.time() - _last_sticker_at.get(key, 0) >= CFG["sticker_gap_s"]:
            available = [n for n in LEGS_POOL
                         if os.path.exists(os.path.join(STICKER_DIR, n + ".jpg"))]
            last_legs = _last_sticker_file.get(key)
            pool = [n for n in available if n + ".jpg" != last_legs]
            if available:
                pending_images.append(random.choice(pool or available) + ".jpg")
        # legs 触发后是否还继续走正常回复，未知；草稿按“继续走正常流程”处理。

    # 3b. 趴着例外：只看大号本人的消息，不看回复文字；单张 pazhe.jpg。
    # 与 legs 同款规则：仅 1323841589 生效，60s 间隔内只发一次，成功才计时。
    if sender == CFG["owner_qq"] and PAZHE_TRIGGER in text:
        if time.time() - _last_sticker_at.get(key, 0) >= CFG["sticker_gap_s"]:
            if os.path.exists(os.path.join(STICKER_DIR, PAZHE_FILE)):
                pending_images.append(PAZHE_FILE)
        # 同 legs，触发后继续走正常流程。

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

    # 5b. Torres 直接下令改资料/发说说（只认私聊里的大号）：不用等模型，直接执行，
    # 回一句她自己的确认就走，不调 LLM。文案 40 字以内，超了不发、不截断。
    if not is_group and sender == CFG["owner_qq"] and persona == "xiaoman":
        direct = None
        m = re.match(r"^\s*改昵称[:：]\s*(.+?)\s*$", text)
        if m:
            ok, err = set_qq_nickname(m.group(1))
            direct = ("好呀，我把昵称改成「%s」啦……" % m.group(1) if ok
                      else "诶，昵称没改成……%s" % err)
        m = re.match(r"^\s*(?:改签名|改个性签名)[:：]\s*(.+?)\s*$", text)
        if m and direct is None:
            ok, err = set_qq_signature(m.group(1))
            direct = ("好呀，我把签名改成「%s」啦……" % m.group(1) if ok
                      else "诶，签名没改成……%s" % err)
        m = re.match(r"^\s*换头像(?:[:：]\s*(.+?))?\s*$", text)
        if m and direct is None:
            fname = (m.group(1) or CFG["avatar_file"]).strip()
            ok, err = set_qq_avatar_from_sticker(fname)
            direct = "好呀，我换好头像啦……" if ok else "诶，头像没换成……%s" % err
        m = re.match(r"^\s*(?:发说说|发空间|发个说说)[:：]\s*(.+?)\s*$", text, re.S)
        if m and direct is None:
            if qzone_posted_today():
                direct = "今天已经发过 1 条说说啦，明天再发好不好……"
            else:
                ok, sent, err = publish_qzone(m.group(1))
                direct = ("好呀，我发啦：%s" % sent if ok
                          else "诶，说说没发出去……%s" % err)
        if direct is not None:
            target = ("private", sender)
            typing_delay(direct)
            send_via_napcat(target[0], target[1], [text_segment(direct)])
            return True

    # 6. 组装历史并调模型。
    history = _history.get(key, [])
    _sys = system_prompt_for(persona) + "\n" + identity
    if persona == "xiaoman" and not is_group and sender == CFG["owner_qq"]:
        _sys += "\n" + AUTONOMY_PROMPT
    messages = [{"role": "system",
                 "content": _sys}]
    messages += history[-CFG["history_turns"] * 2:]
    messages.append({"role": "user", "content": text})
    reply = llm_reply(messages)
    if reply is None:
        # 模型失败：回固定 fallback，不发表情（见 U09）。
        target = ("group", event.get("group_id")) if is_group else ("private", sender)
        typing_delay(FALLBACK_REPLY)
        segments = [text_segment(FALLBACK_REPLY)]
        for filename in pending_images:
            segments.append(image_segment_file(filename))
        resp = send_via_napcat(target[0], target[1], segments)
        if resp and resp.get("retcode") == 0:
            for filename in pending_images:
                mark_sticker_sent(key, filename)
        return True

    # 6b. 小满自发的动作标记：从回复里抠出来执行，正文去掉标记再发。
    # 只在私聊、Torres 本人、小满人格下执行；群聊、妈妈/女仆不执行。
    self_notes = []
    if not is_group and sender == CFG["owner_qq"]:
        reply, _actions = parse_self_actions(reply)
        self_notes = execute_self_actions(_actions, persona)
        if self_notes:
            reply = (reply + "\n" + "\n".join("（%s）" % n for n in self_notes)).strip()

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": reply})
    _history[key] = history[-CFG["history_turns"] * 2:]

    target = ("group", event.get("group_id")) if is_group else ("private", sender)
    typing_delay(reply)

    # 7. 语音：触发词命中且回复 ≤120 字。妈妈模式用 Xiaoxuan；女仆模式不发语音。
    # （女仆模式不发语音是推测：规格只写了女仆不发表情，语音未明说。见 UNCERTAINTIES。）
    # 2026-11-08：小满人格 + 短回复（≤10 字）先试 SparkTTS 克隆音色，
    # 妈妈模式永远 edge-tts；SparkTTS 任何失败/超时都回落 edge-tts，
    # edge-tts 再失败则回文字——语音是尽力而为，绝不丢回复。
    wants_voice = any(t in text for t in VOICE_TRIGGERS)
    if wants_voice and len(reply) <= VOICE_MAX_CHARS and persona != "maid":
        ref = None
        clean = clean_for_tts(reply)
        if persona == "xiaoman" and clean and len(clean) <= SPARKTTS_MAX_CHARS:
            ref = sparktts_to_base64(clean)
            if ref is None:
                log("sparktts fallback to edge-tts")
        if ref is None:
            ref = tts_to_base64(reply, mom=(persona == "mom"))
        if ref is not None:
            # 语音回复不发表情。
            send_via_napcat(target[0], target[1], [record_segment(ref)])
            send_pending_images(target)
            return True
        # 合成/发送失败则回文字（继续往下走）。

    # 8. 表情：妈妈模式与女仆模式不发表情。
    # 2026-11-07 15:29：图跟文字发同一条消息，文字在前、图在后（情绪图挨着文字，触发图在最后）。
    segments = [text_segment(reply)]
    sent_files = []
    if persona not in ("mom", "maid"):
        sticker = maybe_sticker(key, reply, text)
        if sticker is not None:
            segments.append(image_segment_file(sticker))
            sent_files.append(sticker)
    for filename in pending_images:
        segments.append(image_segment_file(filename))
        sent_files.append(filename)
    resp = send_via_napcat(target[0], target[1], segments)
    if resp and resp.get("retcode") == 0:
        for filename in sent_files:
            mark_sticker_sent(key, filename)
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
    if CFG["autonomy"]:
        log("bridge autonomy on: qzone daily cap %d, ugc_right %d, max %d chars, no truncation, no schedule"
            % (CFG["qzone_daily_cap"], CFG["qzone_ugc_right"], CFG["qzone_max_chars"]))
    refresh_sparktts_url(force=True)
    if CFG["sparktts_url"] and CFG["sparktts_token"]:
        log("sparktts on: %s (short replies <= %d chars, poll timeout %ds; url auto-syncs from sparktts-url repo)"
            % (CFG["sparktts_url"], SPARKTTS_MAX_CHARS, SPARKTTS_TIMEOUT_S))
    else:
        log("sparktts off: SPARKTTS_URL/SPARKTTS_TOKEN not set, edge-tts only")
    HTTPServer(("0.0.0.0", CFG["listen_port"]), Handler).serve_forever()
