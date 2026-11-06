# REBUILD-CHECKLIST — 重做清单（DRAFT）

> 按顺序执行。任何一步验证不通过就停下来，不要往下赶。
> 括号里是验证标准；“回退”是这步失败时怎么办。
> 需要 Torres 做的事集中在最后的清单里，不要默认他已做。

## 阶段 0 — 动手前（本地，不动服务器）

- [ ] 0.1 确认本仓库 `qq-bridge` 已在 GitHub 建好（私有空库）、Muse 的 GitHub App
  已授权到该库。验证：能在 GitHub 网页上看到该库；回退：等 Torres 建库授权。
- [ ] 0.2 把 `rebuild/` 下的草稿逐份审完：`bridge.py.DRAFT` 按 UNCERTAINTIES.md
  U01–U32 逐条过，能确认的改成“已确认”，确认不了的留着。验证：每条不确定
  都有结论（确认 / 待实测 / 待 Torres 定）；回退：不审完不部署。
- [ ] 0.3 确认 Torres 已定 Genie 内存限制的最终值（草稿建议 800m，未经实测，
  见 U30）。验证：他亲口定的数字；回退：不给定不上 genie。
- [ ] 0.4 确认 legs4 改什么（他说过“还要重新改一下”，改什么至今 TBD）。
  没定之前 legs4 不参与部署，只部署 legs / legs3 / legs5。

## 阶段 1 — 控制台重装系统

- [ ] 1.1 在腾讯云控制台对 lhins-7y2px0v5 做**重装系统**（不需要 SSH/VNC，
  能绕过假死）。选 Ubuntu 24.04、Docker 镜像（原服务器是 Docker CE-HubH 镜像，
  具体镜像 ID 待核对）。验证：控制台显示重装完成、实例运行中；
  回退：重装失败则按控制台提示处理，不要反复点。
- [ ] 1.2 确认重装后 IP、防火墙、安全组与原来一致（公网 139.199.204.177）。
  验证：控制台核对；回退：IP 变了要同步改所有记录。
- [ ] 1.3 首次登录：用新密码或密钥登录一次，确认能进终端。
  验证：能执行 `free -h`、`docker ps`；回退：登录不上先解决登录，不要继续。

## 阶段 2 — 底座

- [ ] 2.1 装 Docker CE（原服务器 27.5.1），ubuntu 用户用 passwordless sudo 跑 docker。
  验证：`sudo docker ps` 不报错；回退：按 socket 权限报错逐项查。
- [ ] 2.2 建工作目录 `/home/ubuntu/qq-bridge/`，拷入：`bridge.py`（草稿审完改名）、
  `Dockerfile.bridge`（改名 Dockerfile）、`docker-compose.yml`、`.env`（填好真 key）、
  `stickers/`（见 MISSING.md，缺的 9 张先空着）、`genie/`、`scripts/patch_bridge_genie.py`。
  验证：`ls -la` 逐项对；回退：缺文件先补，不要先起容器。
- [ ] 2.3 GenieData：让服务器自己从 hf-mirror 下 17 个文件（392MB，见 VOICE-MODELS.md），
  逐个对大小。验证：文件数与大小与清单一致；回退：单个文件失败只重下该文件。
- [ ] 2.4 语音 ONNX：传本地 `xiaoman-onnx-official.tar.gz`（306,136,288 B，
  md5 2c072cc75930b83064679bb0fa1ba2a1），解开 + 对 md5，`ref-seg6.wav` 一并传。
  验证：md5 一致、9 个文件齐全；回退：md5 不对重传，不要解开用。
  （上次是 15 个 20MB 分块经 OrcaTerm 文件管理器传的；传法按当时成功的办法。）

## 阶段 3 — NapCat（先只起这一个）

- [ ] 3.1 `sudo docker compose up -d napcat`，看日志确认监听 3000。
  验证：`docker logs napcat --tail 60` 无报错刷屏；回退：见 NAPCAT-DEPLOY.md。
- [ ] 3.2 Torres 重新扫码登录小号 2750579528。验证：日志确认登录成功、
  能收到群与私聊消息；回退：登录失败换取码方式，**绝不重启 napcat 容器来“修”登录**。
- [ ] 3.3 配 OneBot 上报 `http://127.0.0.1:8787/event`。验证：上报地址写对；
  回退：改配置，不要动 bridge。

## 阶段 4 — bridge

- [ ] 4.1 后台构建 bridge（OrcaTerm 断线会杀前台构建，用 nohup/setsid）：
  `sudo docker compose up -d --build bridge`（服务名是 bridge）。
  验证：构建成功、无 Traceback；回退：看构建日志，pip 源必须是清华源。
- [ ] 4.2 `sudo docker logs bridge --tail 30` + `/health` 返回 ok。
  验证：启动日志有 `x-deepseek-v4.1-flash @ https://ly.77625.xyz/v1`；
  回退：key、地址、模型三项逐项查。
- [ ] 4.3 私聊真消息测试（Torres 大号先发一句）：回一句正常话。
  验证：收到回复、称呼是“哥”；回退：看 bridge 日志的 LLM 调用报错。

## 阶段 5 — Genie 与切桥

- [ ] 5.1 起 genie（**不要**用无限制自启；按定好的内存限制起）。
  验证：日志出现 `genie xiaoman ready`；`free -h` 看加载后内存，
  2G 实例上必须留余量；回退：内存超了先停 genie，不要动 napcat/bridge。
- [ ] 5.2 合成延迟测试：`POST http://127.0.0.1:8000/tts`
  `{"character_name": "xiaoman", "text": "哥，我是小满", "split_sentence": false}`，
  计时。验证：出声、延迟可接受（Torres 定的标准）；回退：延迟过高先不切桥。
- [ ] 5.3 跑切桥脚本：备份 bridge.py 后跑**适配副本**
  `patch_bridge_genie.DRAFT.py`（原版 patch 按服务器真本缩进写死，跑草稿会断言
  失败，见 U24；部署真本时才用原版 `../scripts/patch_bridge_genie.py`），
  只重建 bridge 服务。
  验证：脚本输出 `patched OK`、bridge 重启后无 Traceback；回退：用备份恢复 bridge.py。
- [ ] 5.4 发已授权的那句测试语音到 Torres 大号 1323841589
  （2026-11-05 20:13 他提前同意过的那一句）。验证：他确认收到、声音是对的；
  回退：他说不行就切回 edge-tts（Genie 失败自动回落也应验证一次）。

## 阶段 6 — 全面真消息验证（缺一不可）

- [ ] 6.1 群 @ 回复、私聊回复、静默期（到点再测）、黑名单 2482076278/428762607
  （黑名单发消息应无回复、无 LLM 调用、无表情）。
- [ ] 6.2 人格切换：妈妈（叫“妈妈”切入、叫“小满”切回）、女仆（仅 QQ 2716043774
  说“女仆”生效、叫主人、说“小满”退出）。
- [ ] 6.3 语音触发词、≤120 字发语音、妈妈模式 Xiaoxuan、表情触发与 60 秒间隔、
  legs（大号说“看看腿”三张随机）。
- [ ] 6.4 把实测结果逐条记下来，与记忆不符的改代码、改 UNCERTAINTIES.md，
  不要只看“能跑起来”就当完成。

## 阶段 7 — 收尾

- [ ] 7.1 清理服务器上残留的分块与 tar 包（上次 585MB 未清理），确认磁盘余量。
- [ ] 7.2 把重建后的实际配置（真本 bridge.py 的 diff、最终内存限制、实测延迟）
  写回本仓库与 SERVER-STATE.md，并把 UNCERTAINTIES.md 里证实了的条目
  改成“已确认：……”+ 证据。
- [ ] 7.3 告诉 Torres：重建完成、声音已切（或未切）、各项测试结果。

---

## 需要 Torres 做的事（不要默认他已做）

1. **GitHub 上新建私有空库 `qq-bridge`**（不要勾选加 README），并把 Muse 的
   GitHub App 授权给该库（与 our-story 同样的做法）。没这个，备份推不上去。
2. **重新给 key**：中转 key（ly.77625.xyz）、GLM key（备胎，可选）。不要发在群里，
   按服务器上的办法写进 `.env`；终端历史若留过 key，记得 `history -c; history -w`。
3. **重新扫码登录 QQ 小号 2750579528**（NapCat 登录态重装即丢）。
4. **定 Genie 内存限制的最终值**（草稿建议 800m，未经实测；太小 Genie 可能起不来）。
5. **定 legs4 改什么**（他说过“还要重新改一下”，改什么至今 TBD）。没定之前不做 legs4。
6. **测试后确认**：阶段 5.4 的测试语音、阶段 6 的各项真消息测试，由他点头才算通过。
7. **定服务器续费办法**：免费试用到 2026-12-04 00:02:55，重建后仍是这个到期日，
   到期前要定续费方案（不要拖到最后一刻）。
