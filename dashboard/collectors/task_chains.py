"""
Task Chains Collector - 任务链数据采集
"""

import json
import os


def get_task_chains():
    """获取任务链数据"""
    chains = []
    try:
        with open('/data/DragonClaw/dashboard/data/dragonclaw_processed_ids.json', 'r') as f:
            processed = json.load(f)
            if isinstance(processed, list) and len(processed) > 0:
                chains.append({
                    'id': 'main-chain',
                    'title': '任务协作链',
                    'agents': ['main'],
                    'steps': processed,
                    'status': 'completed'
                })
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        pass
    return chains


def get_agent_participation(usage_data_fn):
    """获取 agent 参与统计"""
    participation = {}
    
    try:
        usage = usage_data_fn()
        agent_stats = usage.get('agent_stats', {})
        for agent_name, stats in agent_stats.items():
            participation[agent_name] = {
                'events': stats.get('calls', 0),
                'tokens': stats.get('tokens', 0),
                'tasks': stats.get('tasks', 0)
            }
    except Exception:
        pass
    
    if not participation:
        try:
            with open('/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json', 'r') as f:
                tasks = json.load(f)
                for task in tasks:
                    agent = task.get('agent', 'unknown')
                    if agent not in participation:
                        participation[agent] = {'events': 0, 'tokens': 0, 'tasks': 0}
                    participation[agent]['events'] += 1
                    participation[agent]['tokens'] += task.get('tokens', 0)
                    participation[agent]['tasks'] += 1
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass
    
    if not participation:
        participation = {'main': {'events': 1, 'tokens': 0, 'tasks': 1}}
    
    return participation
