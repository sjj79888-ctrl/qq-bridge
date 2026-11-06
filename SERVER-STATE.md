# SERVER-STATE — 服务器现状（2026-11-06 晚）

## 实例

- 腾讯云 Lighthouse，广州，实例 `lhins-7y2px0v5`，名 Docker CE-HubH
- 公网 IP：139.199.204.177，内网 10.1.0.14
- 配置：2 核 2G，40GB CLOUD_SSD 系统盘，Docker CE 27.5.1，Ubuntu 24.04，登录用户 ubuntu
- 免费试用，到期 **2026-12-04 00:02:55**，续费方式 NOTIFY_AND_MANUAL_RENEW（到期前要定办法）

## 故障经过（2026-11-06）

- ~13:18 Torres 说 QQ 小满不说话了，疑似小号登录过期，要一张新的登录二维码。至今未核实。
- 13:20 起 OrcaTerm 终端进不去：TAT 自动化助手客户端状态「未安装」，扫码免密登录不可用；一键安装 TAT 两次失败（14:14、15:47，均约 2 分钟，无重启）。
- 14:25 离线密码重置已提交（强制关机，新密码 Torres 自己设的），实例回到运行中。
- 此后所有登录通道都超时（不是密码错误）：OrcaTerm SSH 密码登录 15:01、15:03、16:07、17:30 均「远程会话连接超时」；手机 uterm SSH 17:02、17:08、17:09 均 Read timed out（VPN 开关都试过，确认是服务端问题）；执行命令无输入框；VNC 15:21 两次黑屏。
- 17:50–17:56 按 VNC 方案做了一次普通重启（先开 VNC 页再重启），实例回到运行中（重启约 6 分钟，重启前控制台内存约 1498.8MB/2GB）；VNC 再次黑屏「连接已断开，请刷新重试」，刷新重试同样报错。**至今没有进过终端，6 项只读检查一次都没跑成，没有停掉任何进程，napcat 没动过，也没下单升配。**

## 工单

- 腾讯云工单 **202611060711**，2026-11-06 17:13 提交，状态处理中。
- 客服回复 #1（17:18，AI 生成，仅供参考）：云平台网络/安全组正常；称根因是内存耗尽、假死，一个 python3 进程持续占约 1.5GB，物理内存 + swap 全满；步骤：快照 → 重启 → VNC 跑 `free -h` 和 `ps aux --sort=-%rss | head -12` 发回。
- Torres 17:22 同意按客服说的做。**快照 Snapshot-20261106172304（lhsnap-13eiob9f）17:23 建好，状态正常**；普通重启 17:23–17:26，实例回到运行中。
- Torres 17:31 在工单里回复：快照+重启做了，但 17:30 登录仍超时，free/ps 跑不了，问高内存进程是不是又回来了、有没有别的办法进去停掉。
- 客服回复 #2（17:35:28，AI 生成，仅供参考）：复查称重启后 python3 进程又自启，1 分钟内吃满内存，系统再次假死，内存 90%+ 有 OOM 记录；平台看不到启动来源、停不掉。步骤：别用 OrcaTerm SSH，改走控制台 VNC——先开 VNC 页、重启、立刻进 VNC；跑 `ps -eo pid,ppid,rss,cmd --sort=-rss | head -10`，kill 掉最占内存的 python3；查自启 `systemctl list-units --type=service --state=running | grep -i -E "python|py"` / `systemctl disable --now <服务>`，或是 Docker 就 `docker ps` 后停容器；VNC 也太慢就升内存到 4GB+ 争取时间。
- Muse 未验证的判断（只是推测）：最可疑的是 Genie 容器（`--restart unless-stopped` 启动，服务器总共才 1.7GB 内存）。若能进终端，先停 genie 容器，不要乱 kill，绝对不要重启 napcat。

## 升配到 2 核 4G 的实查价（控制台，2026-11-06 17:39–17:43，只查价，未下单）

- 65 元/月档：2 核 4GB、60GB SSD、5Mbps、500GB 流量/月，补差价 **23.34 元（不含税）**
- 75 元/月档：2 核 4GB、70GB SSD、6Mbps、600GB 流量/月，补差价 **32.67 元（不含税）**
- 计费方式：按剩余时间补差价到到期日，不是按年重计；**到期时间不变，仍是 2026-12-04 00:02:55**；IP、防火墙、密码/密钥、快照不受影响。
- Torres 17:47 决定：先不升，走 VNC。VNC 17:56 再次失败后，下一步待他定（继续 VNC / 升配 / 升级人工客服 / 全部重做）。

## 容器与文件（最后已知状态，2026-11-06 ~13:20，之后未验证）

- 容器：napcat、bridge、genie（Genie 容器 ID `31c237b695c4`，镜像 `genie-tts-xiaoman` f71c25575289，1.57GB，127.0.0.1:8000）。另有一个无关的 `cosy-poc` 容器，别碰。Compose 网络 `qq-bridge_default`，服务名是 `bridge` 不是 `qq-bridge`。
- `/home/ubuntu/qq-bridge/`：bridge.py（24,547 B，含 legs 三张随机、女仆、黑名单）、.env 及多个 .env.bak-20261105-* 备份、stickers/ 11 张、genie-data/GenieData/ 17 个文件 392MB、genie-voice/xiaoman-onnx-official/ 321MB + ref-seg6.wav、patch_bridge_genie.py（已传，未跑）。分块和 tar 包还留在 genie-voice/（共 585MB，未清理）。
- 桥仍是 edge-tts；Genie 容器是否还活着、日志有没有 "genie xiaoman ready"、内存和合成延迟，全都没验证。

## 全部重做时需要的东西

1. 控制台重装系统（不需要 SSH/VNC，能绕过假死），或新开一台实例。
2. 重新扫码登录 QQ 小号 2750579528（NapCat 登录态随重装丢失，Torres 本人扫）。
3. 重新填 `.env` 的 key（Torres 本人给；relay key、GLM key 都只在服务器 .env 和安全存储里）。
4. 按 `BRIDGE-SPEC.md` 重建 bridge.py；Dockerfile 用清华 pip 源；重建放后台跑。
5. 重新传 Genie 文件约 747MB（GenieData 可让服务器自己从 hf-mirror 下；ONNX tar.gz 本地有，md5 见 VOICE-MODELS.md；上次是 15 个 20MB 分块经 OrcaTerm 文件管理器传的）。
6. 表情包：legs3、legs5 在本仓库；其余原图从服务器取，服务器没了就按 `stickers/MANIFEST.md` 重新生成（legs4 灰色待重做，改什么等 Torres 说；legs2 粉色已废弃，不要）。
7. 重建后：验证 bridge/napcat/genie → 跑切桥脚本 → 测延迟 → 小满给大号发一句测试语音（Torres 2026-11-05 20:13 已提前同意过这一句）。
