#!/usr/bin/env bash
# 每 10 秒把 NapCat 容器里的最新二维码拷到 web/，供扫码页刷新。
# 由 deploy.sh 用 nohup setsid 在后台跑。按服务器运行状态重建，非逐字节原样。
DIR="$(cd "$(dirname "$0")/.." && pwd)"
while true; do
  sudo docker cp napcat:/app/napcat/cache/qrcode.png "$DIR/web/qrcode.png" 2>/dev/null || true
  sleep 10
done
