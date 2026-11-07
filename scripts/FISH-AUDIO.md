# Fish Audio — 云端合成备选

状态：已死路（2026-11-07 13:39 服务器实测：api.fish.audio 和 fish.audio 均超时无响应，000）。Torres 2026-11-07 13:41 决定先不装语音系统，继续用 edge-tts。除非服务器网络变化，否则不要重试。补丁 `scripts/patch_bridge_fish.py` 仅作存档。

## 怎么做

1. Torres 在 fish.audio 注册，建一个 API key → 写进服务器 `.env` 的
   `FISH_API_KEY`（走安全 vault，绝不进仓库、绝不发聊天记录）。
2. 在 fish.audio playground 用 G.E.M. 参考素材（李诞播客 60 秒干声）克隆声音，
   拿到 voice model id → 写进服务器 `.env` 的 `FISH_REFERENCE_ID`。
3. 先在服务器上测 api.fish.audio 通不通（HuggingFace 之前从服务器连不上，
   别默认能通）：
   ```bash
   curl -s -o /tmp/fish-test.mp3 -w "http:%{http_code} size:%{size_download}\n" \
     -X POST https://api.fish.audio/v1/tts \
     -H "Authorization: Bearer $FISH_API_KEY" -H "model: s2.1-pro-free" \
     -H "Content-Type: application/json" \
     -d '{"text":"你好，我是小满","reference_id":"<voice model id>","format":"mp3"}'
   ```
   http:200 + 真 mp3 = 能用；401 = 通但 key 错了；超时/DNS 失败 = 服务器连不上，
   走 Genie。
4. 跑补丁：`python3 scripts/patch_bridge_fish.py /home/ubuntu/qq-bridge/bridge.py`
   （幂等，可重跑），再加上面两行 `.env`，`./deploy.sh` 重建桥。
5. 部署完让小满给大号发一句测试语音（他提前同意过的）。

## 费用

- 模型 `s2.1-pro-free`：和付费版 s2.1-pro 同一个模型，免费到 2026-11-30，
  不用绑卡；免费档每次最多 500 字，桥的语音回复本来就限 120 字以内，不受影响。
- 免费期过后：$15 / 100 万 UTF-8 字节，按桥的量算约每月不到 1 美元。

## 规则

- 妈妈模式不走 Fish，永远 edge-tts（Xiaoxuan）。
- Fish 失败就回 edge-tts，不影响回消息。
