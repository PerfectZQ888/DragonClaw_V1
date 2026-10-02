#!/usr/bin/env python3
"""
DragonClaw 协作日志自动记录器（完整版）
自动记录所有任务相关事件
"""

import subprocess
import os
import json
import re
import fcntl
from datetime import datetime

TASK_LOG = "/data/DragonClaw/tasks/coordination/task_log.jsonl"
COORD_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json"

# 任务分发命令关键词
SPAWN_COMMANDS = ['/spawn', '/delegate', '/broadcast', '/create', '/launch']
TASK_KEYWORDS = ['任务', '检查', '分析', '编写', '创建', '部署', '配置', '优化', '修复']

def log_event(event: str, agent: str, detail: str):
    """记录协作事件到日志文件"""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 写入 JSONL 格式日志
    record = {
        "time": timestamp,
        "event": event,
        "agent": agent,
        "detail": detail[:500]
    }

    os.makedirs(os.path.dirname(TASK_LOG), exist_ok=True)
    with open(TASK_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # 同时写入 markdown 格式日志
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

def auto_log_dispatch(agent: str, task_desc: str):
    """自动记录任务分发事件"""
    log_event("TASK_DISPATCHED", agent, task_desc)

def auto_log_received(agent: str, task_desc: str):
    """自动记录任务接收事件"""
    log_event("TASK_RECEIVED", agent, task_desc)

def auto_log_completed(agent: str, task_desc: str, token_count: int = 0):
    """自动记录任务完成事件"""
    detail = task_desc[:400]
    if token_count > 0:
        detail += f" | 消耗 {token_count} tokens"
    log_event("TASK_COMPLETED", agent, detail)

def detect_task_from_message(message: str) -> tuple[bool, str]:
    """从消息中检测是否为任务分发"""
    message = message.strip()

    # 检查是否包含任务分发命令
    for cmd in SPAWN_COMMANDS:
        if message.startswith(cmd):
            # 提取任务描述
            task_desc = message[len(cmd):].strip()
            if task_desc:
                return True, task_desc
            else:
                return True, "未知任务（无描述）"

    # 检查是否包含任务关键词
    for keyword in TASK_KEYWORDS:
        if keyword in message:
            return True, message

    return False, ""

# 测试函数
if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 2:
        # 测试消息检测
        message = ' '.join(sys.argv[1:])
        is_task, task_desc = detect_task_from_message(message)
        if is_task:
            print(f"检测到任务: {task_desc}")
            auto_log_dispatch('main', task_desc)
        else:
            print("未检测到任务")
    else:
        print("用法: python3 coord_logger_auto.py <消息内容>")
        print("示例: python3 coord_logger_auto.py /spawn 研究助手检查系统状态")
