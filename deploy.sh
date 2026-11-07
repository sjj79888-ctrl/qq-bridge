#!/usr/bin/env bash
# 部署桥就用这个文件：./deploy.sh
# qq-bridge 一键部署：在服务器上拉下本仓库，进目录跑 ./deploy.sh。
# 做完的事：生成 .env、解码表情包、启动 SnowLuma + 桥、搭扫码页。
# 只动 bridge 相关容器，不动服务器上其他东西。
# QQ 协议端是 SnowLuma（2026-11-07 起）；NapCat 只留作回退，平时不启动。
set -euo pipefail
cd "$(dirname "$0")"

# 1. 配置：没有 .env 就从模板生成，等填 key 再跑一次。
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已从 .env.example 生成 .env，请把 LLM_API_KEY 填成真 key 再跑一次 ./deploy.sh"
  exit 1
fi
if grep -qE '^LLM_API_KEY=(<redacted>|PASTE_KEY_HERE)?$' .env; then
  echo ".env 里 LLM_API_KEY 还是占位符，先填真 key 再跑"
  exit 1
fi

# 2. NapCat WebUI token（回退用的 napcat 服务）：占位符就随机生成一个，记到 WEBUI_TOKEN.txt（别进仓库）。
if grep -q 'WEBUI_TOKEN: <redacted>' docker-compose.yml; then
  TOKEN=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  sed -i "s/WEBUI_TOKEN: <redacted>/WEBUI_TOKEN: $TOKEN/" docker-compose.yml
  echo "$TOKEN" > WEBUI_TOKEN.txt
  echo "已生成 NapCat WebUI token，记在 WEBUI_TOKEN.txt"
fi

# 3. SnowLuma VNC 密码：占位符就随机生成一个，写进 compose，记到 .snowluma-vnc-pass（0600，别进仓库）。
if grep -q 'VNC_PASSWD: <redacted>' docker-compose.yml; then
  VPASS=$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 12)
  sed -i "s/VNC_PASSWD: <redacted>/VNC_PASSWD: $VPASS/" docker-compose.yml
  echo "$VPASS" > .snowluma-vnc-pass
  chmod 600 .snowluma-vnc-pass
  echo "已生成 SnowLuma VNC 密码，记在 .snowluma-vnc-pass（0600）"
fi

# 4. 表情包：仓库里只存 base64 文本，部署时解回 jpg。
for b in stickers/*.b64; do
  jpg="${b%.b64}"
  [ -f "$jpg" ] || base64 -d "$b" > "$jpg"
done

# 5. 扫码页：截图循环 + 80 端口静态服务，没跑才启动。
# 循环脚本在 qr-page/qr-loop.sh（容器内 ffmpeg 截图 → 裁成 QQ 登录窗口 → web/qq-qr.png，每 15 秒）。
mkdir -p web
pgrep -f qr-loop.sh >/dev/null || (setsid nohup bash qr-page/qr-loop.sh >/dev/null 2>&1 &)
# 80 是特权端口，普通用户绑不上，用 sudo 起（2026-11-07 实测：不加 sudo 报 PermissionError）。
pgrep -f "http.server 80" >/dev/null || (cd web && setsid sudo nohup python3 -m http.server 80 >/dev/null 2>&1 &)

# 6. 构建并启动：必须用合并的两个 compose 文件（depends_on 在主文件里）。
# 注意：不要用 restart 来换新镜像，restart 不加载新镜像；要用 up -d 重建。
# 默认只起 snowluma + bridge；napcat 是 profile 门控的回退，平时不启动。
sudo docker compose -f docker-compose.yml -f docker-compose.bridge.yml up -d --build
sleep 5
sudo docker compose -f docker-compose.yml -f docker-compose.bridge.yml ps
sudo docker logs qq-bridge --tail 5
echo "下一步：浏览器打开 http://<服务器公网IP>/ 扫码登录小满（码约 2 分钟有效），或用 noVNC http://<服务器公网IP>:6081/（密码见 .snowluma-vnc-pass）进桌面扫码；再私聊发一句测回复"
