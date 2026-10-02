"""
Risks Collector - 风险评估采集
"""

import json
import os


def collect_risks():
    """获取风险评估"""
    risks = []
    
    # 检查磁盘空间
    try:
        stat = os.statvfs('/')
        free_percent = (stat.f_bfree / stat.f_blocks) * 100
        if free_percent < 10:
            risks.append({
                'level': 'high',
                'message': f'根分区可用空间不足 {free_percent:.1f}%'
            })
    except OSError:
        pass
    
    # 检查内存
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    avail = int(line.split()[1]) * 1024
                    total = 0
                    for l2 in open('/proc/meminfo', 'r'):
                        if l2.startswith('MemTotal:'):
                            total = int(l2.split()[1]) * 1024
                            break
                    if total > 0 and avail / total < 0.1:
                        risks.append({
                            'level': 'medium',
                            'message': f'系统内存可用率低于 10%'
                        })
                    break
    except (IOError, ValueError):
        pass
    
    # 检查未完成的任务
    shared_file = '/data/DragonClaw/dashboard/data/dragonclaw_shared_tasks.json'
    if os.path.exists(shared_file):
        try:
            with open(shared_file, 'r') as f:
                tasks = json.load(f)
                pending = [t for t in tasks if t.get('status') == 'pending']
                if len(pending) > 20:
                    risks.append({
                        'level': 'low',
                        'message': f'存在 {len(pending)} 个待处理任务'
                    })
        except (json.JSONDecodeError, IOError):
            pass
    
    return risks
