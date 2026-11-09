#!/bin/bash
# 小满主动找 Torres 聊天：每天最多 7 次，08:00-23:00 之间随机时间。
# crontab 每 30 分钟跑一次，每次 35% 概率触发；距上次触发不到 45 分钟不触发。
# 状态文件：.proactive-state（日期 次数 上次触发时间戳）。
# 桥的 /proactive 自己还会再检查一遍（45 分钟内不重复、Torres 一小时内聊过不发、
# 人格不是小满不发、克隆语音不可用不发），这里只管“想什么时候就什么时候”的随机。
STATE=/home/ubuntu/qq-bridge/.proactive-state
NOW=$(date +%s)
TODAY=$(date +%Y-%m-%d)
HOUR=$(date +%H)
if [ "$HOUR" -lt 8 ] || [ "$HOUR" -ge 23 ]; then exit 0; fi
COUNT=0; LAST=0; DAY=""
if [ -f "$STATE" ]; then read -r DAY COUNT LAST < "$STATE"; fi
if [ "$DAY" != "$TODAY" ]; then COUNT=0; LAST=0; fi
if [ "$COUNT" -ge 7 ]; then exit 0; fi
if [ $((NOW - LAST)) -lt 2700 ]; then exit 0; fi
if [ $((RANDOM % 100)) -ge 35 ]; then exit 0; fi
# 触发：调桥的 /proactive（处理要几分钟，8 秒不等回包；桥会自己跑完）。
curl -s -m 8 -X POST http://127.0.0.1:8787/proactive -o /dev/null
echo "$TODAY $((COUNT + 1)) $NOW" > "$STATE"
echo "$(date '+%Y-%m-%d %H:%M:%S') proactive tick fired (count $((COUNT + 1))/7)"
