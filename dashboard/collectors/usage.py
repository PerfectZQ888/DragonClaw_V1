"""
Usage Collector - 使用数据采集（jsonl 扫描）
修复: 统一 UTC 时区, ttl=60s, 增量扫描位置记录
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('dashboard')

_SCAN_POSITIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', '.usage_scan_positions.json')


def _load_scan_positions():
    """加载增量扫描位置"""
    try:
        if os.path.exists(_SCAN_POSITIONS_FILE):
            with open(_SCAN_POSITIONS_FILE, 'r') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        pass
    return {}


def _save_scan_positions(positions):
    """保存增量扫描位置"""
    try:
        os.makedirs(os.path.dirname(_SCAN_POSITIONS_FILE), exist_ok=True)
        with open(_SCAN_POSITIONS_FILE, 'w') as f:
            json.dump(positions, f)
    except IOError as e:
        logger.warning(f"Failed to save scan positions: {e}")


def collect_usage_data():
    """实际收集使用数据 - 北京时间, 增量扫描"""
    now_utc = datetime.utcnow()
    midnight_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)

    api_calls = 0
    input_tokens = 0
    output_tokens = 0
    cache_read = 0
    cache_write = 0
    total_tokens = 0
    cost_total = 0.0
    model_stats = {}
    agent_stats = {}
    recent_activities = []
    messages_today = 0

    SKIP_PREFIXES = (
        'Conversation info', 'Sender (untrusted metadata)', 'System: [',
        '[cron:', 'Pre-compction', '[Sat ', '[Sun ', '[Mon ', '[Tue ',
        '[Wed ', '[Thu ', '[Fri ', 'An async command',
        'Continue where you left off', 'OpenClaw runtime context',
        'HEARTBEAT_OK', '[Subagent Context]', '[Inter-session message]',
        'Exec failed,',
    )

    scan_positions = _load_scan_positions()

    agents_base = '/data/.openclaw/agents/'
    if os.path.exists(agents_base):
        for agent_name in os.listdir(agents_base):
            agent_sessions_dir = os.path.join(agents_base, agent_name, 'sessions')
            if not os.path.isdir(agent_sessions_dir):
                continue

            for fname in os.listdir(agent_sessions_dir):
                if not fname.endswith('.jsonl'):
                    continue
                fpath = os.path.join(agent_sessions_dir, fname)
                file_key = f"{agent_name}/{fname}"

                try:
                    file_size = os.path.getsize(fpath)
                    last_pos = scan_positions.get(file_key, 0)

                    if last_pos > file_size:
                        last_pos = 0

                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_pos)

                        for line in f:
                            try:
                                msg = json.loads(line.strip())
                                ts = msg.get('timestamp', '')
                                if not ts:
                                    continue

                                try:
                                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                    if dt.tzinfo:
                                        dt = dt.replace(tzinfo=None)
                                    dt = dt - timedelta(hours=8)
                                except ValueError:
                                    continue

                                if dt < midnight_utc:
                                    continue

                                msg_type = msg.get('type', '')
                                msg_data = msg.get('message', {})
                                role = msg_data.get('role', '')
                                content = msg_data.get('content', '')

                                if msg_type == 'message' and role in ('user', 'assistant'):
                                    messages_today += 1

                                if msg_type == 'message' and role == 'assistant':
                                    usage = msg_data.get('usage', {})
                                    if usage and usage.get('totalTokens', 0) > 0:
                                        api_calls += 1
                                        input_tokens += usage.get('input', 0)
                                        output_tokens += usage.get('output', 0)
                                        cache_read += usage.get('cacheRead', 0)
                                        cache_write += usage.get('cacheWrite', 0)
                                        total_tokens += usage.get('totalTokens', 0)
                                        cost_info = usage.get('cost', {})
                                        cost_total += cost_info.get('total', 0)

                                        model = msg_data.get('model', 'unknown')
                                        if model not in model_stats:
                                            model_stats[model] = {'calls': 0, 'tokens': 0, 'cost': 0.0}
                                        model_stats[model]['calls'] += 1
                                        model_stats[model]['tokens'] += usage.get('totalTokens', 0)
                                        model_stats[model]['cost'] += cost_info.get('total', 0)

                                        if agent_name not in agent_stats:
                                            agent_stats[agent_name] = {'calls': 0, 'tokens': 0, 'tasks': 0}
                                        agent_stats[agent_name]['calls'] += 1
                                        agent_stats[agent_name]['tokens'] += usage.get('totalTokens', 0)

                                if msg_type == 'message' and role == 'user':
                                    content_str = ''
                                    if isinstance(content, list):
                                        for c in content:
                                            if isinstance(c, dict):
                                                content_str += str(c.get('text', ''))
                                    elif isinstance(content, str):
                                        content_str = content

                                    content_short = content_str[:100].strip() if content_str else ''
                                    if content_short and not content_short.startswith(SKIP_PREFIXES):
                                        recent_activities.append({
                                            'time': dt.strftime('%m-%d %H:%M'),
                                            'type': 'message',
                                            'content': content_short,
                                            'agent': agent_name
                                        })

                            except Exception:
                                continue
                        scan_positions[file_key] = f.tell()

                except Exception:
                    continue
    _save_scan_positions(scan_positions)
    recent_activities.sort(key=lambda x: x.get('time', ''), reverse=True)

    return {
        'requests_today': api_calls,
        'messages_today': messages_today,
        'tokens_today': total_tokens,
        'input_tokens_today': input_tokens,
        'output_tokens_today': output_tokens,
        'cache_read_today': cache_read,
        'cache_write_today': cache_write,
        'cost_estimate': cost_total,
        'model_stats': model_stats,
        'agent_stats': agent_stats,
        'recent_activities': recent_activities[:100]
    }
