"""
Agents Collector - Agent 统计数据采集
修复: shared_tasks.json 只读一次，通过参数传递
"""

import json
import os
from datetime import datetime


def collect_agent_stats(sessions_data_fn, shared_tasks=None):
    """
    实际收集 agent 统计
    
    Args:
        sessions_data_fn: 获取会话数据的回调函数
        shared_tasks: 可选的预加载任务列表，避免重复读取 shared_tasks.json
    """
    stats = {}
    sessions_data = sessions_data_fn()
    
    for sess in sessions_data:
        channel = sess.get('channel', 'unknown')
        if channel not in stats:
            stats[channel] = {'tasks': 0, 'sessions': 0, 'status': 'idle'}
        stats[channel]['sessions'] += 1
        if stats[channel]['status'] == 'idle':
            stats[channel]['status'] = 'active'
    
    # 任务统计 - 只读一次
    agent_task_counts = {}
    running_tasks = {}
    
    # 如果没有预加载数据，才读取文件
    if shared_tasks is None:
        shared_file = '/data/DragonClaw/dashboard/data/dragonclaw_shared_tasks.json'
        if os.path.exists(shared_file):
            try:
                with open(shared_file, 'r') as f:
                    shared_tasks = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError, IOError):
                shared_tasks = []
    
    if shared_tasks:
        now = datetime.now()
        for t in shared_tasks:
            task_time = t.get('time', '')
            agent = t.get('agent', 'main')
            
            # 统计30分钟内的任务
            try:
                time_part = task_time.split(' ')[-1]
                task_hour = int(time_part.split(':')[0])
                task_min = int(time_part.split(':')[1])
                diff_hours = (now.hour - task_hour) if now.hour >= task_hour else (24 - task_hour + now.hour)
                diff_minutes = diff_hours * 60 + (now.minute - task_min)
                if diff_minutes <= 30:
                    agent_task_counts[agent] = agent_task_counts.get(agent, 0) + 1
            except (ValueError, IndexError):
                pass
            
            # 统计正在运行的任务
            if t.get('status') in ['running', 'progress']:
                running_tasks[agent] = running_tasks.get(agent, 0) + 1
    
    for agent_key in ['main', 'research', 'creative', 'dev', 'perfect_openclaw', 'skill-vetter', 'security', 'dba']:
        if agent_key not in stats:
            stats[agent_key] = {'tasks': 0, 'sessions': 0, 'status': 'idle'}
        stats[agent_key]['tasks'] = agent_task_counts.get(agent_key, 0)
        if running_tasks.get(agent_key, 0) > 0:
            stats[agent_key]['status'] = 'busy'
    
    if 'feishu' in stats:
        stats['main']['sessions'] = stats['feishu'].get('sessions', 0)
        if stats['feishu'].get('status') == 'active':
            stats['main']['status'] = 'active'
    
    return stats
