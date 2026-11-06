# NAPCAT-DEPLOY — NapCat 部署步骤草稿（DRAFT）

> 原服务器 NapCat 的镜像名、配置文件格式、取二维码的方式均不在备份里
> （见 UNCERTAINTIES.md U04）。本文件是按 NapCat 常规部署方式写的草稿，
> 部署时逐项核对，不要当成原版步骤。

## 部署前确认（必须先有答案再动手）

1. **NapCat 镜像名与版本**：原服务器用的是哪个镜像、哪个版本？备份里没有。
   草稿 compose 里暂填 `mlikiowa/napcat-docker:latest`（候选），部署时核对，
   版本不对可能导致 OneBot 字段、登录流程对不上。
2. **配置文件位置**：NapCat 的 OneBot 配置与登录态存在哪？草稿 compose 暂挂
   `./napcat-data:/app/napcat/config`（推测），部署时核对原服务器的实际路径。
3. **登录二维码怎么取**：NapCat 登录一般是看容器日志里的二维码，或 Web UI 扫码。
   原服务器用的是哪种，备份里没有。部署时看 NapCat 镜像文档，取码方式以实际为准。

## 步骤

### 1. 装好底座（重装系统后）

- Ubuntu 24.04 + Docker CE（原服务器是 Docker CE 27.5.1）。
- ubuntu 用户用 `sudo` 跑 docker（原服务器 ubuntu 用户直接跑 docker 会报
  socket 权限不足，记得用 passwordless sudo）。
- 新建工作目录 `/home/ubuntu/qq-bridge/`，把本仓库的文件拷进去：
  `bridge.py`（草稿审完改名后）、`Dockerfile.bridge`（改名 Dockerfile 后）、
  `docker-compose.yml`、`.env`（按 `.env.draft` 填好真 key 后）、`stickers/`、
  `genie/`、`scripts/patch_bridge_genie.py`。

### 2. 起 NapCat（先只起这一个）

```bash
sudo docker compose up -d napcat
sudo docker logs napcat --tail 60
```

- 看日志确认 NapCat 在监听 3000（OneBot HTTP），且只绑了 127.0.0.1。
- 若日志里出现登录二维码，截图/转发给 Torres 扫码（他本人扫）。
- 登录成功后，在日志里确认小号 **2750579528（小满）** 已登录、能收到消息。

### 3. OneBot HTTP 上报配置

- NapCat 的 OneBot HTTP 上报地址填桥的事件入口：
  `http://127.0.0.1:8787/event`（桥监听 8787，路径 /event，见 U25）。
- 上报格式按 OneBot 11。配置文件的具体字段名以 NapCat 实际版本为准，
  本草稿不编造字段名。
- 配置改完后重启 **NapCat 容器本身的一次性重启是允许的**——注意：这里说的
  是部署阶段的首次启动；一旦登录态建立，之后绝不能再用重启来“修”登录。

### 4. 登录态的红线（最重要）

- **绝不能重启 napcat 容器来“修”登录。** 重启会丢 QQ 登录态。
  登录过期、掉线的唯一办法是重新扫码（Torres 本人扫）。
- 2026-11-06 13:18 Torres 就报过“小满不说话了、疑似登录过期”，至今未核实；
  重建后第一次登录本来就是重新扫码，不存在“保留旧登录态”的选项。
- 登录成功后立刻记下来：登录时间、日志里确认收到群消息（望远镜窝交流群）
  与私聊消息的时间点，作为基线。

### 5. 再起 bridge 与 genie

- 先不要一起起。顺序：napcat（登录成功）→ bridge（见 REBUILD-CHECKLIST.md）
  → genie（先验证日志与内存，再切桥）。
- bridge 与 napcat 之间只走 127.0.0.1：napcat 3000 ← bridge 发消息；
  bridge 8787/event ← napcat 上报。

## 验证标准

- `sudo docker ps`：napcat、bridge、genie 三容器都在 Running。
- `sudo docker logs napcat --tail 60`：无登录过期、无反复重连、无报错刷屏。
- 私聊测试：Torres 大号发一句，小满回一句（不要用群聊先测）。
- 群聊测试：有人 @ 小满，她才回；没 @ 不回；0:00–10:00 不回（时间到了再测）。

## 回退办法

- NapCat 起不来：先看 `docker logs`，不要反复 `restart`；镜像名、卷路径、
  端口占用（3000 是否被占）逐项查。
- 登录扫码失败：换取码方式（日志二维码 ↔ Web UI），不要重启容器“重试”。
- 桥收不到上报：先查 napcat 上报地址是否 `http://127.0.0.1:8787/event`、
  bridge 是否在监听 8787、防火墙/端口是否只绑了 127.0.0.1。
