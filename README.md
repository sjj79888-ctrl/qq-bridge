# QQ桥接

> **部署桥就用这个文件：`./deploy.sh`**（先在 `.env` 里填真 key，见下一节；如果提示没有执行权限，用 `bash deploy.sh`）

QQ 小号「小满」的 SnowLuma + 桥接仓库。拉下来就能部署。

- 小号：2750579528（小满）
- Torres 大号：1323841589（长温），私聊白名单
- 服务器：腾讯云 Lighthouse 广州，实例 `lhins-7y2px0v5`，公网 139.199.204.177，2 核 2G，免费试用到 **2026-12-04 00:02:55**
- QQ 协议端：**SnowLuma**（真 QQ 客户端 + ptrace hook，OneBot v11），2026-11-07 起替代 NapCat。NapCat 已停，只留作回退（`docker-compose.yml` 里用 `profiles: ["napcat"]` 门控，别同时起——两个服务都绑 127.0.0.1:3000，会端口冲突）。

## 一键部署（拉下来就能用）

```bash
git clone https://github.com/sjj79888-ctrl/qq-bridge.git
cd qq-bridge
./deploy.sh        # 第一次会生成 .env 停下来，等填 key
# 把 LLM_API_KEY 填成真 key（Torres 本人给），再跑一次：
./deploy.sh
```

`deploy.sh` 会做的事：生成 `.env`（占位符的 WebUI token 和 VNC 密码会随机生成）、解码表情包、启动 SnowLuma + 桥、搭扫码页（80 端口截图循环）。跑完打开 `http://<服务器公网IP>/` 扫码登录小满（码约 2 分钟有效），或用 noVNC `http://<服务器公网IP>:6081/`（密码在服务器上的 `.snowluma-vnc-pass` 文件里）进桌面扫码。再私聊发一句测回复。

- 防火墙要放行：80（扫码页）、5099（SnowLuma WebUI）、6081（noVNC）。
- `.env` 真配置永远不进仓库。这里只有 `.env.example` 模板，key 是占位符。
- 根目录的 `bridge.py` 就是服务器上正在跑的版本（2026-11-07 验证，md5 `4b26e0b3c98a39668949f75d4e86ab90`）。
- `rebuild/` 是 2026-11-06 重建时的草稿历史，别当部署文件用。

## 最重要的几条

1. **不要随便删 QQ 协议端容器。** NapCat 时代重启会丢登录状态；SnowLuma 的登录态存在 `./snowluma-config` 挂载里，重启容器不丢，但删容器前必须确认挂载在，删了挂载等于删了登录态，之后要重新扫码。
2. **换新镜像不要用 `restart`，要用 `up -d` 重建。** `restart` 只重启旧容器，不加载新打好的镜像（2026-11-07 00:29 踩过这个坑）。
3. **只用 `up -d` 起默认服务。** napcat 是回退用的 profile，平时别起；回退要先停 snowluma 再起 napcat（两个都绑 3000），并把 `.env` 的 `NAPCAT_URL` 改回 `http://napcat:3000`。

## 扫码页（QR 页）怎么工作

扫码页不是 NapCat 那种直接拿二维码文件——SnowLuma 的码在 QQ 客户端窗口里，所以是截图循环：

- 容器内 ffmpeg 每 15 秒截一次桌面（`x11grab :1`，1920x1080），裁成 QQ 登录窗口那一块（320x460+800+300），覆盖 `web/qq-qr.png`；`python3 -m http.server 80` 供页面访问；页面 JS 每 10 秒带时间戳刷新图片（防浏览器缓存旧图）。
- 循环脚本在 `qr-page/qr-loop.sh`，由 `deploy.sh` 启动；`qr-page/index.html` 是页面本身。
- QQ 二维码约 2 分钟过期，过期后页面显示红色“当前二维码已过期”，要点窗口里的“刷新”按钮——桌面坐标 (931,594)，容器内用 `DISPLAY=:1 xdotool mousemove 931 594 click 1` 点（xdotool 容器里没有就 `apt-get install -y xdotool`，源慢就换清华镜像）。
- 如果截图全黑、窗口截不到：QQ 登录窗口可能在别的虚拟桌面（2026-11-07 踩过：窗口在桌面 0，当前桌面是 2）。容器内查 `DISPLAY=:1 xdotool get_desktop_for_window <窗口ID>` 和 `get_desktop`，用 `set_desktop_for_window <窗口ID> <当前桌面>` 移回来，再 `windowmap windowactivate windowraise`。
- `xmessage` 弹窗说找不到壁纸工具（fluxbox fbsetbg）是无害提示，不用管。

## 文件清单

| 文件 | 内容 |
|---|---|
| `bridge.py` | 桥本體，已验证版本；含分块请求修复（见下） |
| `Dockerfile.bridge` | 桥镜像定义（python:3.12-slim + edge-tts） |
| `docker-compose.yml` | snowluma 服务（默认启动）+ napcat 服务（profile 回退） |
| `docker-compose.bridge.yml` | bridge 服务（必须和主文件合并用） |
| `deploy.sh` | 一键部署脚本 |
| `.env.example` | 配置模板，无真 key |
| `qr-page/` | 扫码页：`index.html`（JS 时间戳刷新）+ `qr-loop.sh`（ffmpeg 截图裁图循环） |
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
- 语音：现在仍是 edge-tts（平时 Xiaoyi，妈妈模式 Xiaoxuan）；Genie 专属音色已批准，服务器部署被 2026-11-06 清盘抹了，等 Torres 定下一步（备选：Fish Audio 免费版）。

## 2026-11-07 分块请求修复（为什么改 bridge.py）

NapCat 上报事件用的是 `Transfer-Encoding: chunked`，不带 `Content-Length`。旧桥只按 `Content-Length` 读 body，读到空内容就报 `JSONDecodeError('Expecting value: line 1 column 1 (char 0)')`、回 500，消息收到了也永远回不出来（2026-11-07 00:03、00:10 两条私聊都是这么丢的）。修复后的 `_read_body()` 会解析分块、按长度读、没长度就限时读到连接关闭，本地三种方式都测过，全是 200。部署验证：2026-11-07 00:34 Torres 收到小满的回复「哥，咋啦？」。

## 2026-11-07 换 SnowLuma（为什么换协议端）

NapCat 的 QQ 会话 2026-11-07 一天掉了四次，最后一次是静默掉线（04:12 后无消息，10:13 直接发消息报 1006514“网络连接异常”；只看日志和 hourly 同步看不出掉线，只有直接发消息才能验证）。Torres 决定换 SnowLuma（真 QQ 客户端 + ptrace hook，社区反馈比 NapCat 稳）。迁移验证 13:05–13:08：扫码登录成功，`get_login_info` 返回小满 2750579528，OneBot 3000 通，直接发私聊 retcode 0，Torres 发“看看腿”收到腿图（腿图是单独一条消息，害羞表情包跟文字回复一起——先看到害羞是正常的，不是 bug）。

## 重建要做的事

完整清单见 `SERVER-STATE.md`，摘要：

1. 重新扫码登录 QQ 小号（登录态在 `./snowluma-config` 挂载里，删挂载才丢）。
2. 重新填 `.env` 的 key（Torres 本人给）。
3. `bridge.py` 就在仓库根目录（已验证版本，md5 `4b26e0b3c98a39668949f75d4e86ab90`），不用重写。
4. 重新传 Genie 文件约 747MB（GenieData 392MB + ONNX 321MB + 参考音频）。
5. 表情包缺的原图从服务器取；服务器没了就按清单重新生成。

## 语音：SparkTTS 克隆音色（2026-11-08 接线）

- 平时语音走 edge-tts（小满 Xiaoyi、妈妈 Xiaoxuan），触发词不变。
- 小满人格 + 短回复（≤10 字）先试 SparkTTS 克隆音色（朋友的声音）：跑在 Muse
  自己的 VM 上，桥经 localhost.run 隧道调它（`SPARKTTS_URL` / `SPARKTTS_TOKEN`，
  见 `.env.example`）。失败、超时（轮询 300 秒）、隧道断了，都自动回落 edge-tts；
  edge-tts 再失败就回文字——语音是尽力而为，绝不丢回复。妈妈模式永远 edge-tts。
- **隧道地址自动同步（2026-11-08）**：localhost.run 的 URL 随机分配，每次重连都换新
  地址。Muse VM 上的看门狗（`sparktts-urlsync.service`）一发现地址变了，就把它推
  到公开仓库 [`sjj79888-ctrl/sparktts-url`](https://github.com/sjj79888-ctrl/sparktts-url)
  的 `url.txt`；桥启动时和每次 SparkTTS 调用失败（连接错误/502）时自动去
  `https://raw.githubusercontent.com/sjj79888-ctrl/sparktts-url/main/url.txt` 取最新
  地址，取不到才用服务器 `.env` 里的 `SPARKTTS_URL` 备用——不用再手动改配置了。
  那个公开仓库里只有地址一行，没有口令。想彻底固定地址得用 Cloudflare 命名隧道
  （要 Torres 的 Cloudflare 登录），还没搭。
- 长句不走 SparkTTS：28 字曾用 650 秒还啰嗦出 60 秒音频，所以只接 ≤10 字的短回复。
