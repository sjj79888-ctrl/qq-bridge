# 服务器强制关机重置密码后核对清单

背景（2026-11-06 下午，北京时间）：小满 13:18 起不说话、疑似 QQ 登录失效；
终端进不去（TAT 免密登录不可用，实例上没装自动化助手客户端，一键安装 14:17
失败）；Torres 14:24 同意强制关机重置密码，14:30 提交成功、实例显示运行中，
新密码还没验证。他说过：“到时候要是少了哪些文件数据，就补一下呗”。
强制关机前 napcat、bridge、Genie 容器都没动过。
先让他用新密码登 OrcaTerm，登上后再按下面逐项核对。

更新（2026-11-06 15:52–15:54）：一键安装 15:47 又失败一次（15:49，同样的报错，实例没重启、容器没动）；智能诊断说 15:01/15:03 两次 SSH 超时是因为 15:47 开始的那次安装操作还在跑、占住了 SSH，实例/IP/防火墙都正常。安装现已结束（失败），SSH 应该不被占了，现在重试 SSH 密码登录很可能能进。15:54 已把 OrcaTerm 链接重新发给他，等他登。

## 1. 容器在不在跑

- `docker ps`：napcat、bridge、genie 三个容器是否都在跑。
  Genie 容器 ID 开头 `31c237b695c4`，镜像 `genie-tts-xiaoman`（ID `f71c25575289`，1.57GB）。
- `docker logs genie`：有没有 “genie xiaoman ready”；`free -h` 看加载后内存
  （服务器总共 1.7GB 内存，之前只剩 1.1GB 可用、swap 已用 219MB，Genie 很吃内存）。
- Genie 试合成一句“哥，我是小满”，记延迟和 wav 大小（本地 4 核约 9 秒/句，服务器 2 核只会更慢）。
- `docker logs napcat --tail 60`：找登录失效的报错、有没有二维码；有二维码就截图给他扫。
- `curl 127.0.0.1:3000` 和 `:6099` 通不通；`docker logs bridge --tail 30`。

## 2. 文件在不在（服务器路径 → 本地备份）

- `/home/ubuntu/qq-bridge/bridge.py`：legs 随机池那行还在不在
  （`random.choice(['legs','legs3','legs5'])`）。桥还没切 Genie，仍是 edge-tts；
  切桥脚本 `/home/ubuntu/qq-bridge/patch_bridge_genie.py`（3300 字节）已传上、还没跑。
- `/home/ubuntu/qq-bridge/.env`：`BLACKLIST_QQ_IDS=2482076278,428762607`、
  `QUIET_START_HOUR=0` / `QUIET_END_HOUR=10`、后端 x-deepseek-v4.1-flash @ ly.77625.xyz。
  备份 `.env.bak-20261105-silence`、`.env.bak-20261105-glms`、`.env.bak-20261105-deepseek` 别删。
- `/home/ubuntu/qq-bridge/stickers/`：11 张图（legs 原图、legs3 米色、legs5 牛仔等）。
  本地对照：`~/workspace/qq-bridge/stickers-new/legs3.jpg`（md5 f6827c53…）。
- `/home/ubuntu/qq-bridge/genie-data/GenieData/`：17 个文件，392MB。
  其中 speaker_encoder.onnx 184,812,166 B，chinese-hubert-base_weights_fp16.bin 188,741,632 B。
- `/home/ubuntu/qq-bridge/genie-voice/`：`xiaoman-onnx-official/` 9 个文件 321MB + ref-seg6.wav；
  tar.gz md5 `2c072cc75930b83064679bb0fa1ba2a1`。分块和 tar 包还留在那（共 585MB），清理还没做。
- 本地模型备份：`~/workspace/voice-reference/models/` 里
  xiaoman-sovits-e8.pth（md5 `3115ba0edf2345af11b42049ef030df7`）、
  xiaoman-gpt-e8.ckpt（md5 `a0811b7a03004bb695827b7e2e77ffab`）、ref-seg6.wav（md5 `942ed13de04b228d68c75c78f53e0293`）；
  官方顺序版在 `models/xiaoman-onnx-official/`，参数版在 `models/xiaoman-onnx-param/`，
  原版 `models/xiaoman-onnx/` 是回滚。
- Genie 部署文件本地在 `~/workspace/qq-bridge/genie/`（Dockerfile + entrypoint.sh）。
- 顺带：服务器上有个无关的 `cosy-poc` 容器，别碰它；Compose 网络是 `qq-bridge_default`。

## 3. 少了就补，补完再走下一步

- 模型/GenieData 缺了就从上面本地备份重传；`.env`/贴纸缺了按备份恢复；
  容器没起来先看日志再决定，不要顺手重启 napcat（重启会丢 QQ 登录）。
- 核对完 → Genie 验证 → 跑切桥脚本 → 测延迟 → 小满给他大号发一句测试语音
  （这句他 12:35 已 blanket 同意，不用再问）。
- 全部弄完再同步 our-story（本地三处已更新到 2026-11-06 下午，见
  `~/workspace/our-story/MEMORY.md`、`qq-bridge/VOICE-TRAINING.md`、`TODO.md`），
  Torres 已授权直接同步，不用每次问他确认。
