#!/usr/bin/env bash
# SnowLuma 桌面截图循环：给扫码页供图。
# 每 15 秒：容器内 ffmpeg 截 1920x1080 桌面 → 裁成 QQ 登录窗口（320x460+800+300）
# → 拷到 web/qq-qr.png；页面（index.html）每 10 秒带时间戳刷新图片（防缓存）。
# 由 deploy.sh 用 nohup setsid 在后台跑；只在仓库/服务器根目录跑（web/ 在它隔壁）。
# QQ 二维码约 2 分钟过期，过期后点窗口里的“刷新”按钮（桌面坐标 931,594）：
#   sudo docker exec snowluma sh -c 'DISPLAY=:1 xdotool mousemove 931 594 click 1'
# （xdotool 容器里没有就先装：进容器 apt-get install -y xdotool，源慢换清华镜像。）
# 如果截图全黑、窗口截不到：窗口可能在别的虚拟桌面，用 xdotool 查桌面号并移回当前桌面：
#   DISPLAY=:1 xdotool get_desktop_for_window <窗口ID>；get_desktop
#   DISPLAY=:1 xdotool set_desktop_for_window <窗口ID> <当前桌面>
#   DISPLAY=:1 xdotool search --name "QQ" windowmap windowactivate windowraise
cd "$(dirname "$0")/.."
mkdir -p web
while true; do
  sudo docker exec snowluma sh -c "ffmpeg -y -loglevel error -f x11grab -video_size 1920x1080 -i :1 -frames:v 1 /tmp/desktop.png" || true
  sudo docker exec snowluma sh -c "ffmpeg -y -loglevel error -i /tmp/desktop.png -vf crop=320:460:800:300 /tmp/qqwin.png" || true
  sudo docker cp snowluma:/tmp/qqwin.png web/qq-qr.png || true
  sleep 15
done
