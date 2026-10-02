"""
Sessions Collector - 会话数据采集
"""

import json
import os
from datetime import datetime


def _count_session_messages(session_id, agent_name='main'):
    """从 session jsonl 文件统计真实消息数"""
    jsonl_file = f'/data/.openclaw/agents/{agent_name}/sessions/{session_id}.jsonl'
    count = 0
    try:
        if os.path.exists(jsonl_file):
            with open(jsonl_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    try:
                        msg = json.loads(line.strip())
                        if msg.get('type') == 'message':
                            role = msg.get('message', {}).get('role', '')
                            if role in ('user', 'assistant'):
                                count += 1
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        pass
    return count


def collect_sessions_data():
    """实际收集会话数据"""
    sessions = []
    sessions_file = '/data/.openclaw/agents/main/sessions/sessions.json'
    now = datetime.now()
    
    try:
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                sessions_data = json.load(f)
                for key, data in sessions_data.items():
                    updated_at = data.get('updatedAt', 0)
                    if not updated_at:
                        continue
                    session_time = datetime.fromtimestamp(updated_at / 1000)
                    diff_minutes = (now - session_time).total_seconds() / 60
                    if diff_minutes > 30:
                        continue
                    
                    channel = data.get('lastChannel', data.get('deliveryContext', {}).get('channel', 'unknown'))
                    parts = key.split(':')
                    agent_name = parts[1] if len(parts) > 1 else 'main'
                    label = data.get('label', '')
                    session_id = data.get('sessionId', key[:8])
                    
                    if label:
                        display_name = label
                    elif len(parts) > 2 and parts[2] == 'subagent':
                        display_name = f'subagent:{parts[3][:8]}' if len(parts) > 3 else 'subagent'
                    else:
                        display_name = agent_name
                    
                    sessions.append({
                        'id': session_id,
                        'agent': agent_name,
                        'label': display_name,
                        'channel': channel,
                        'status': data.get('status', 'active'),
                        'messages': _count_session_messages(session_id, agent_name),
                        'updated': session_time.strftime('%H:%M')
                    })
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        pass
    
    return sessions
