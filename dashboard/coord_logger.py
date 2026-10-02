#!/usr/bin/env python3
"""
DragonClaw 协作日志自动记录器
用法: python3 coord_logger.py <event> <agent> <detail>
示例: python3 coord_logger.py TASK_DISPATCHED research "搜索天气信息"
"""

import sys
import json
import os
import fcntl
from datetime import datetime, timedelta

TASK_LOG = "/data/DragonClaw/tasks/coordination/task_log.jsonl"
COORD_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json"

def log_event(event: str, agent: str, detail: str):
    """记录协作事件到日志文件"""
    now = datetime.now()  # 系统已是 CST (UTC+8)，无需再加偏移
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 写入 JSONL 格式日志（便于 dashboard 读取）
    record = {
        "time": timestamp,
        "event": event,
        "agent": agent,
        "detail": detail[:500]
    }
    
    os.makedirs(os.path.dirname(TASK_LOG), exist_ok=True)
    with open(TASK_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # 同时写入 markdown 格式日志（AGENTS.md 规范）
    md_log = TASK_LOG.replace('.jsonl', '.md')
    with open(md_log, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {event} {agent} {detail}\n")
    
    # 同时更新 coordination json 文件（加文件锁防止竞态）
    _write_coord_safe(record)

def _write_coord_safe(record):
    """线程安全写入 coordination 文件"""
    try:
        os.makedirs(os.path.dirname(COORD_FILE), exist_ok=True)
        with open(COORD_FILE, 'a+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read()
                coord_data = json.loads(content) if content else []
                coord_data.append(record)
                MAX_COORD_RECORDS = 5000
                coord_data = coord_data[-MAX_COORD_RECORDS:]
                f.seek(0)
                f.truncate()
                json.dump(coord_data, f, ensure_ascii=False)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    
    print(f"✅ [{timestamp}] {event} {agent} | {detail[:60]}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("用法: coord_logger.py <event> <agent> <detail>")
        print("事件: TASK_RECEIVED | TASK_DISPATCHED | AGENT_COMPLETED | TASK_COMPLETED")
        sys.exit(1)
    
    event = sys.argv[1].upper()
    agent = sys.argv[2]
    detail = ' '.join(sys.argv[3:])
    
    log_event(event, agent, detail)
