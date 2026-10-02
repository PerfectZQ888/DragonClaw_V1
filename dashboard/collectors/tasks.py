"""
Tasks Collector - 任务数据采集
"""

import json
import os


def collect_tasks_data():
    """收集任务数据"""
    tasks = []
    task_info = {'total': 0, 'pending': 0, 'running': 0, 'done': 0, 'last_detect': None}
    
    # 获取 agent token 统计
    agent_tokens = {}
    try:
        from collectors import usage
        usage_data = usage.collect_usage_data()
        agent_tokens = usage_data.get('agent_stats', {})
    except Exception:
        pass
    
    shared_file = '/data/DragonClaw/dashboard/data/dragonclaw_shared_tasks.json'
    if os.path.exists(shared_file):
        try:
            with open(shared_file, 'r') as f:
                shared_tasks = json.load(f)
                if isinstance(shared_tasks, list):
                    task_info['total'] = len(shared_tasks)
                    task_info['pending'] = len([t for t in shared_tasks if t.get('status') == 'pending'])
                    task_info['running'] = len([t for t in shared_tasks if t.get('status') in ['running', 'progress']])
                    task_info['done'] = len([t for t in shared_tasks if t.get('status') in ['done', 'completed']])
                    
                    if shared_tasks:
                        sorted_tasks = sorted(shared_tasks, key=lambda x: x.get('time', ''), reverse=True)
                        task_info['last_detect'] = sorted_tasks[0].get('time', 'N/A') if sorted_tasks else 'N/A'
                        
                        def time_sort_key(t):
                            time_str = t.get('time', '00:00')
                            try:
                                if ' ' in time_str:
                                    parts = time_str.split(' ')
                                    date_parts = parts[0].split('-')
                                    time_parts = parts[1].split(':')
                                    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                                    hours, minutes = int(time_parts[0]), int(time_parts[1])
                                    return year * 1000000 + month * 10000 + day * 100 + hours * 60 + minutes
                                else:
                                    parts = time_str.split(':')
                                    return int(parts[0]) * 60 + int(parts[1])
                            except (ValueError, IndexError):
                                return 0
                        
                        def sort_key(t):
                            status = t.get('status', '')
                            status_priority = 10000 if status in ['pending', 'done'] else 0
                            return status_priority + time_sort_key(t)
                        
                        valid_tasks = [t for t in shared_tasks
                                      if t.get('title') and len(t.get('title', '')) > 3
                                      and 'Conversation' not in t.get('title', '')
                                      and 'GMT' not in t.get('title', '')]
                        valid_tasks.sort(key=sort_key, reverse=True)
                        
                        for t in valid_tasks:
                            agent_id = t.get('agent', 'main')
                            # 从 agent_tokens 获取该 agent 的 token 统计
                            agent_token_data = agent_tokens.get(agent_id, {})
                            agent_tokens_sum = agent_token_data.get('tokens', 0)
                            tasks.append({
                                'id': t.get('id', 'task'),
                                'title': t.get('title', '')[:300],
                                'agent': agent_id,
                                'status': t.get('status', 'pending'),
                                'priority': t.get('priority', 'medium'),
                                'time': t.get('time', ''),
                                'source': 'task_watcher',
                                'tokens': agent_tokens_sum  # 关联 agent 的 token 统计
                            })
        except (json.JSONDecodeError, IOError) as e:
            pass
    
    return tasks, task_info
