#!/usr/bin/env bash
# qq-bridge 一键部署：在服务器上拉下本仓库，进目录跑 ./deploy.sh。
# 做完的事：生成 .env、解码表情包、启动扫码页、构建并启动 napcat + bridge。
# 只动 bridge 相关容器，不动服务器上其他东西。
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

# 2. NapCat WebUI token：占位符就随机生成一个，记到 WEBUI_TOKEN.txt（别进仓库）。
if grep -q 'WEBUI_TOKEN: <redacted>' docker-compose.yml; then
  TOKEN=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  sed -i "s/WEBUI_TOKEN: <redacted>/WEBUI_TOKEN: $TOKEN/" docker-compose.yml
  echo "$TOKEN" > WEBUI_TOKEN.txt
  echo "已生成 NapCat WebUI token，记在 WEBUI_TOKEN.txt"
fi

# 3. 表情包：仓库里只存 base64 文本，部署时解回 jpg。
for b in stickers/*.b64; do
  jpg="${b%.b64}"
  [ -f "$jpg" ] || base64 -d "$b" > "$jpg"
done

# 4. 扫码页：刷新循环 + 80 端口静态服务，没跑才启动。
mkdir -p web
pgrep -f refresh_qr.sh >/dev/null || (setsid nohup bash qr-page/refresh_qr.sh >/dev/null 2>&1 &)
pgrep -f "http.server 80" >/dev/null || (cd web && setsid nohup python3 -m http.server 80 >/dev/null 2>&1 &)

# 5. 构建并启动：必须用合并的两个 compose 文件（depends_on 在主文件里）。
# 注意：不要用 restart 来换新镜像，restart 不加载新镜像；要用 up -d 重建。
sudo docker compose -f docker-compose.yml -f docker-compose.bridge.yml up -d --build
sleep 5
sudo docker compose -f docker-compose.yml -f docker-compose.bridge.yml ps
sudo docker logs qq-bridge --tail 5
echo "下一步：浏览器打开 http://<服务器公网IP>/ 扫码登录小满，再私聊发一句测回复"
