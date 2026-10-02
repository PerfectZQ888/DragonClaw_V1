#!/bin/bash
# Token 状态定时检查
# 用法: 添加到 crontab
# */5 * * * * /data/DragonClaw/dashboard/check_token.sh >> /data/DragonClaw/dashboard/logs/token_check.log 2>&1

LOG_DIR="/data/DragonClaw/dashboard/logs"
mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Token check started"

# 运行 Python 检查脚本
python3 /data/DragonClaw/dashboard/token_manager.py

exit $?
