#!/usr/bin/env python3
"""
DragonClaw 任务分发自动检测器
监控主会话消息，自动记录 TASK_RECEIVED 和 TASK_DISPATCHED 事件
"""

import json
import os
import re
from datetime import datetime
import subprocess

TASK_LOG = "/data/DragonClaw/tasks/coordination/task_log.jsonl"
COORD_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json"
SESSIONS_DIR = "/data/.openclaw/agents/main/sessions"

# 任务分发命令关键词
SPAWN_COMMANDS = ['/spawn', '/delegate', '/broadcast', '/create', '/launch']
TASK_KEYWORDS = ['任务', '检查', '分析', '编写', '创建', '部署', '配置', '优化', '修复', '研究', '测试']

# 已记录的任务ID（避免重复）
RECORDING_IDS_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_task_recording_ids.json"

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

    # 同时更新 coordination json 文件
    try:
        coord_data = []
        if os.path.exists(COORD_FILE):
            with open(COORD_FILE, 'r') as f:
                coord_data = json.load(f)
        coord_data.append(record)
        coord_data = coord_data[-200:]
        with open(COORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(coord_data, f, ensure_ascii=False, indent=2)
    except:
        pass

    print(f"✅ [{timestamp}] {event} {agent} | {detail[:60]}")

def load_recording_ids():
    """加载已记录的任务ID"""
    try:
        if os.path.exists(RECORDING_IDS_FILE):
            with open(RECORDING_IDS_FILE, 'r') as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_recording_ids(recording_ids):
    """保存已记录的任务ID"""
    try:
        with open(RECORDING_IDS_FILE, 'w') as f:
            json.dump(list(recording_ids), f)
    except:
        pass

def detect_task_from_message(message: str) -> tuple[bool, str]:
    """从消息中检测是否为任务分发"""
    message = message.strip()

    # 排除内部上下文消息
    internal_patterns = [
        r'<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>',
        r'Conversation info',
        r'untrusted metadata',
        r'sender_id',
        r'sender',
        r'timestamp',
    ]
    for pattern in internal_patterns:
        if re.search(pattern, message):
            return False, ""

    # 检查是否包含任务分发命令
    for cmd in SPAWN_COMMANDS:
        if message.startswith(cmd):
            # 提取任务描述
            task_desc = message[len(cmd):].strip()
            if task_desc:
                return True, task_desc
            else:
                return True, "未知任务（无描述）"

    # 检查是否包含任务关键词（但不是内部消息）
    for keyword in TASK_KEYWORDS:
        if keyword in message:
            # 排除纯元数据消息
            if not any(re.search(pattern, message) for pattern in internal_patterns):
                return True, message

    return False, ""

def scan_main_session():
    """扫描主会话，检测新的任务分发"""
    recording_ids = load_recording_ids()

    # 获取所有会话文件
    session_files = []
    if os.path.exists(SESSIONS_DIR):
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith('.jsonl') and filename.startswith('f7'):
                session_files.append(os.path.join(SESSIONS_DIR, filename))

    # 按修改时间排序（最新的在前）
    session_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # 只检查最新的会话文件
    if session_files:
        latest_session = session_files[0]
        print(f"扫描会话文件: {latest_session}")

        # 读取会话文件，查找新消息
        with open(latest_session, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in reversed(lines):  # 从后往前扫描
            try:
                data = json.loads(line)
                msg = data.get('message', {})
                role = msg.get('role', '')

                # 只检查用户消息
                if role == 'user':
                    content = msg.get('content', [])
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get('text', '')

                        # 检测是否为任务分发
                        is_task, task_desc = detect_task_from_message(text)
                        if is_task:
                            # 生成任务ID
                            task_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(task_desc) % 100000:05d}"

                            # 检查是否已经记录
                            if task_id not in recording_ids:
                                # 记录 TASK_RECEIVED
                                log_event("TASK_RECEIVED", "main", task_desc[:200])

                                # 记录 TASK_DISPATCHED
                                log_event("TASK_DISPATCHED", "main", task_desc[:200])

                                # 标记为已记录
                                recording_ids.add(task_id)
                                save_recording_ids(recording_ids)

                                print(f"✅ 自动记录任务: {task_desc[:60]}")
                            else:
                                print(f"⏭️  任务已记录: {task_desc[:60]}")

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"⚠️  处理消息时出错: {e}")
                continue

    return recording_ids

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # 测试模式
        test_messages = [
            "/spawn 研究助手检查系统状态",
            "/delegate creative 编写技术文档",
            "检查数据库性能",
            "创建一个新的skill",
        ]

        for msg in test_messages:
            is_task, task_desc = detect_task_from_message(msg)
            if is_task:
                print(f"检测到任务: {task_desc}")
                log_event("TASK_DISPATCHED", "main", task_desc)
            else:
                print("未检测到任务")

    else:
        # 正常模式：扫描并记录
        print("🔍 DragonClaw 任务分发自动检测器启动...")
        scan_main_session()
        print("✅ 扫描完成")
