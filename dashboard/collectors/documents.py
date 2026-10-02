"""
Documents Collector - 文档和记忆文件采集
"""

import os
import time
from datetime import datetime


def collect_documents_data():
    """实际收集文档数据"""
    docs = []
    memories = []
    
    # 文档目录
    for base_dir in ['/data/docs', '/root/.openclaw/workspace']:
        if not os.path.exists(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            for fname in files:
                if fname.endswith(('.md', '.txt', '.pdf', '.docx')):
                    fpath = os.path.join(root, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        age_days = (time.time() - mtime) / 86400
                        if age_days < 30:
                            docs.append({
                                'name': fname,
                                'path': fpath,
                                'modified': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'),
                                'size': os.path.getsize(fpath),
                                'category': 'DBA文档' if '/docs/dba/' in fpath else '团队文档' if '/docs/' in fpath else '技能文档' if 'skills' in fpath else 'Markdown',
                                'is_recent': age_days < 1
                            })
                    except OSError:
                        pass
    
    # 记忆文件
    memory_dir = '/root/.openclaw/workspace/memory'
    if os.path.exists(memory_dir):
        for fname in os.listdir(memory_dir):
            if fname.endswith('.md'):
                fpath = os.path.join(memory_dir, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    age_days = (time.time() - mtime) / 86400
                    memories.append({
                        'name': fname,
                        'path': fpath,
                        'modified': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'),
                        'size': os.path.getsize(fpath),
                        'type': '记忆文件',
                        'status': 'recent' if age_days < 1 else 'normal',
                        'status_text': '今日更新' if age_days < 1 else '正常'
                    })
                except OSError:
                    pass
    
    return {'files': docs[:200], 'memories': memories[-50:]}


def collect_memories_data():
    """收集记忆数据 - 包含所有 Agent 的记忆"""
    memories_data = {'recent': [], 'total': 0, 'by_agent': {}}
    
    # Agent 名称映射
    agent_names = {
        'workspace': 'main',
        'workspace-creative': 'creative',
        'workspace-dba': 'dba',
        'workspace-dev': 'dev',
        'workspace-perfect_openclaw': 'perfect',
        'workspace-research': 'research',
        'workspace-security': 'security'
    }
    
    base_path = '/data/.openclaw'
    
    for ws_dir, agent_id in agent_names.items():
        memory_dir = os.path.join(base_path, ws_dir, 'memory')
        if os.path.exists(memory_dir):
            try:
                memory_files = sorted([f for f in os.listdir(memory_dir) if f.endswith('.md')], reverse=True)
                memories_data['by_agent'][agent_id] = memory_files[:10]  # 每个 agent 保存前10个
                memories_data['total'] += len(memory_files)
                # 合并到 recent
                for f in memory_files[:5]:
                    if f not in memories_data['recent']:
                        memories_data['recent'].append(f)
            except OSError:
                pass
    
    # 按时间排序 recent
    memories_data['recent'] = memories_data['recent'][:20]
    
    return memories_data
