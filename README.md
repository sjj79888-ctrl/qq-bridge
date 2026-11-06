# QQ桥接

> **部署桥就用这个文件：`./deploy.sh`**（先在 `.env` 里填真 key，见下一节）

QQ 小号「小满」的 NapCat + 桥接仓库。拉下来就能部署。

- 小号：2750579528（小满）
- Torres 大号：1323841589（长温），私聊白名单
- 服务器：腾讯云 Lighthouse 广州，实例 `lhins-7y2px0v5`，公网 139.199.204.177，2 核 2G，免费试用到 **2026-12-04 00:02:55**

## 一键部署（拉下来就能用）

```bash
git clone https://github.com/sjj79888-ctrl/qq-bridge.git
cd qq-bridge
./deploy.sh        # 第一次会生成 .env 停下来，等填 key
# 把 LLM_API_KEY 填成真 key（Torres 本人给），再跑一次：
./deploy.sh
```

`deploy.sh` 会做的事：解码表情包、启动扫码页（80 端口）、构建并启动 napcat + bridge。跑完浏览器打开 `http://<服务器公网IP>/` 扫码登录小满，再私聊发一句测回复。

- `.env` 真配置永远不进仓库。这里只有 `.env.example` 模板，key 是占位符。
- 根目录的 `bridge.py` 就是服务器上正在跑的版本（2026-11-07 验证，md5 `146eb82215f4f1111d907a199332ed5b`，镜像 `49fc2a4d6603`）。
- `rebuild/` 是 2026-11-06 重建时的草稿历史，别当部署文件用。

## 最重要的两条

1. **不要随便重启 napcat 容器。** 重启会丢 QQ 登录状态，之后要重新扫码（2026-11-06 晚就是这么恢复的：重启 → 新二维码 → 扫码 → 上线）。
2. **换新镜像不要用 `restart`，要用 `up -d` 重建。** `restart` 只重启旧容器，不加载新打好的镜像（2026-11-07 00:29 踩过这个坑）。

## 文件清单

| 文件 | 内容 |
|---|---|
| `bridge.py` | 桥本體，已验证版本；含分块请求修复（见下） |
| `Dockerfile.bridge` | 桥镜像定义（python:3.12-slim + edge-tts） |
| `docker-compose.yml` | napcat 服务（mlikiowa/napcat-docker:v4.18.42） |
| `docker-compose.bridge.yml` | bridge 服务（必须和主文件合并用） |
| `deploy.sh` | 一键部署脚本 |
| `.env.example` | 配置模板，无真 key |
| `qr-page/` | 扫码页：`index.html` + `refresh_qr.sh`（按服务器运行状态重建，非逐字节原样） |
| `stickers/` | 表情包清单 + legs3、legs5 的 base64 文本（部署时由 `deploy.sh` 解回 jpg；其余原图只在服务器上） |
| `BRIDGE-SPEC.md` | 桥的行为规格：回复规则、人格切换、称呼、黑名单 |
| `BACKEND.md` | 模型后端：中转、GLM 备胎、2026-11-05 故障 |
| `VOICE-STICKERS.md` | 语音和表情包的触发规则 |
| `VOICE-TRAINING.md` | 给小满训专属声音的全过程 |
| `VOICE-MODELS.md` | 语音模型清单（文件名、md5、批准的配置），无二进制 |
| `SERVER-STATE.md` | 服务器现状、工单、快照、升配价格、重建清单 |
| `POST-RESET-CHECKLIST.md` | 密码重置后逐项核对清单（2026-11-06） |
| `personas/` | 三个人格：小满、妈妈、女仆（含女仆 47 字压缩版草稿） |
| `genie/` | Genie-TTS 服务的 Dockerfile + entrypoint.sh |
| `scripts/patch_bridge_genie.py` | 把桥的语音切到 Genie 的补丁脚本（未在服务器上跑过） |

## 回复规则（摘要，详见 BRIDGE-SPEC.md）

- 私聊只回大号 1323841589；群聊只在被 @ 时回。
- 群聊静默已关（2026-11-07 00:12 起 QUIET_START_HOUR=0、QUIET_END_HOUR=0，全天都回）；私聊一直不受影响。
- 黑名单（先于白名单检查）：2482076278、428762607。
- 女仆模式只对 QQ 2716043774 生效，他说「女仆」才切入，叫他主人；其余任何人（包括 Torres）不带称呼。说「小满」退出。
- 只有大号才会被叫哥 / 小家伙 / 宝贝；群里别人 @ 她，回话不带称呼。

## 模型后端（摘要）

- 在用：`x-deepseek-v4.1-flash` @ `https://ly.77625.xyz/v1`（2026-11-05 18:00 切回）。
- 备胎：GLM `glm-5.3-flash` @ `https://www.kamente.com/v1`，key 没写进 `.env`，没上线。
- 语音：现在仍是 edge-tts（平时 Xiaoyi，妈妈模式 Xiaoxuan）；Genie 专属音色已批准、文件已上服务器、容器已启动，但未验证、桥还没切过去。

## 2026-11-07 分块请求修复（为什么改 bridge.py）

NapCat 上报事件用的是 `Transfer-Encoding: chunked`，不带 `Content-Length`。旧桥只按 `Content-Length` 读 body，读到空内容就报 `JSONDecodeError('Expecting value: line 1 column 1 (char 0)')`、回 500，消息收到了也永远回不出来（2026-11-07 00:03、00:10 两条私聊都是这么丢的）。修复后的 `_read_body()` 会解析分块、按长度读、没长度就限时读到连接关闭，本地三种方式都测过，全是 200。部署验证：2026-11-07 00:34 Torres 收到小满的回复「哥，咋啦？」。

## 重建要做的事

完整清单见 `SERVER-STATE.md`，摘要：

1. 重新扫码登录 QQ 小号（NapCat 登录态随重装丢失）。
2. 重新填 `.env` 的 key（Torres 本人给）。
3. 按 `BRIDGE-SPEC.md` 重建 bridge.py（规格在，逐字代码只在服务器上）。
4. 重新传 Genie 文件约 747MB（GenieData 392MB + ONNX 321MB + 参考音频）。
5. 表情包缺的原图从服务器取；服务器没了就按清单重新生成。
