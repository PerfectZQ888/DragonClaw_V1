"""
Collect Loop - 主收集循环
修复:
- P1-1: shared_tasks.json 只读一次，通过参数传递
- P1-2: 分离高频/低频采集，优化 collect() 性能
- 高频数据(30s): usage, sessions, connections
- 低频数据(300s): tasks, documents, agents
- 极低频数据(600s): risks, task_chains
"""

import json
import os
import time
import logging
import threading
from datetime import datetime

from config import SERVER_START_TIME, AGENT_COORD_FILE, get_data_cache, get_config_cache
from models.constants import AGENT_CONFIG
from collectors import system, usage, sessions, agents, tasks, documents, connections, risks, task_chains

logger = logging.getLogger('dashboard')


def get_openclaw_config():
    """获取 OpenClaw 配置（带缓存）"""
    return get_config_cache().get('openclaw_config', _load_openclaw_config)


def _load_openclaw_config():
    """实际读取配置"""
    try:
        config_path = os.path.expanduser('~/.openclaw/openclaw.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


def format_uptime(seconds):
    """格式化运行时长"""
    return system.format_uptime(seconds)


# === 缓存数据访问器 ===
def get_usage_data_cached():
    """获取使用数据（带缓存）"""
    return get_data_cache().get('usage_data', usage.collect_usage_data)


def get_sessions_data_cached():
    """获取会话数据（带缓存）"""
    return get_data_cache().get('sessions_data', sessions.collect_sessions_data)


def get_system_info_cached():
    """获取系统信息（带缓存）"""
    return get_data_cache().get('system_info', lambda: system.collect_system_info(SERVER_START_TIME))


def get_connections_cached():
    """获取连接状态（带缓存，30s）"""
    return get_data_cache().get('connections_status', connections.get_connections_status)


def get_tasks_data_cached():
    """获取任务数据（带缓存，300s）"""
    return get_data_cache().get('tasks_data', tasks.collect_tasks_data)


def get_documents_data_cached():
    """获取文档数据（带缓存，300s）"""
    return get_data_cache().get('documents_data', _collect_documents_cached)


def _collect_documents_cached():
    """组合文档+记忆数据"""
    docs = documents.collect_documents_data()
    mems = documents.collect_memories_data()
    return {'documents': docs, 'memories': mems}


def get_risks_cached():
    """获取风险评估（带缓存，600s）"""
    return get_data_cache().get('risks_data', risks.collect_risks)


def get_task_chains_cached():
    """获取任务链（带缓存，600s）"""
    return get_data_cache().get('task_chains', task_chains.get_task_chains)


def get_agent_participation_cached():
    """获取 agent 参与统计（带缓存）"""
    return get_data_cache().get('agent_participation', _collect_agent_participation)


def _collect_agent_participation():
    """从用量数据获取 agent 参与统计"""
    participation = {}
    try:
        usage_data = get_usage_data_cached()
        agent_stats = usage_data.get('agent_stats', {})
        for agent_name, stats in agent_stats.items():
            participation[agent_name] = {
                'events': stats.get('calls', 0),
                'tokens': stats.get('tokens', 0),
                'tasks': stats.get('tasks', 0)
            }
    except Exception as e:
        logger.warning(f'Failed to get participation: {e}')
    
    if not participation:
        try:
            with open(AGENT_COORD_FILE, 'r') as f:
                tasks_data = json.load(f)
                for task in tasks_data:
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


def _build_models_data(agents_list, model_stats):
    """从 OpenClaw 配置构建所有模型数据"""
    models = []
    try:
        config = get_openclaw_config()
        providers = config.get('models', {}).get('providers', {})
        current_models = set(a.get('model', '') for a in agents_list)
        
        for provider_name, provider_config in providers.items():
            provider_models = provider_config.get('models', [])
            for m in provider_models:
                model_id = m.get('id', '')
                model_name = m.get('name', model_id)
                stats = model_stats.get(model_id, {})
                tokens = stats.get('tokens', 0)
                calls = stats.get('calls', 0)
                is_free = m.get('cost', {}).get('input', 0) == 0 and m.get('cost', {}).get('output', 0) == 0
                is_primary = model_id in current_models
                expire_info = '付费模型' if '100万' in model_name else ''
                
                models.append({
                    'name': model_name,
                    'model_id': model_id,
                    'provider': provider_name,
                    'type': 'primary' if is_primary else 'backup',
                    'is_free': is_free,
                    'expire_info': expire_info,
                    'quota_used': tokens,
                    'quota_total': None,
                    'quota_percent': 0,
                    'calls': calls
                })
    except Exception as e:
        logger.warning(f'Failed to build models data: {e}')
    return models


def _collect_skills_data():
    """收集 skills 数据"""
    skills_list = []
    skills_dir = '/data/.openclaw/workspace/skills'
    ready_count = 0
    missing_count = 0
    try:
        if os.path.exists(skills_dir):
            for skill_name in os.listdir(skills_dir):
                skill_path = os.path.join(skills_dir, skill_name)
                if os.path.isdir(skill_path):
                    skill_file = os.path.join(skill_path, 'SKILL.md')
                    status = 'ready' if os.path.exists(skill_file) else 'missing'
                    if status == 'ready':
                        ready_count += 1
                    else:
                        missing_count += 1
                    skills_list.append({'name': skill_name, 'status': status})
    except OSError as e:
        logger.warning(f"Failed to scan skills directory: {e}")
    return {'ready': ready_count, 'missing': missing_count, 'skills': skills_list[:50]}


def _collect_memories_data():
    """收集记忆数据"""
    memories_data = {'recent': [], 'total': 0}
    memory_dir = '/root/.openclaw/workspace/memory'
    if os.path.exists(memory_dir):
        try:
            memory_files = sorted([f for f in os.listdir(memory_dir) if f.endswith('.md')], reverse=True)
            memories_data['total'] = len(memory_files)
            memories_data['recent'] = memory_files[:5]
        except OSError:
            pass
    return memories_data


def _collect_subscription_info():
    """收集订阅信息"""
    subscription_info = {'plan': '未配置', 'quota_info': '未配置', 'reset_date': 'N/A'}
    limits_info = {
        'requests': {'used': 0, 'limit': None, 'percent': 0, 'type': 'unknown', 'reset': 'N/A'},
        'tokens': {'used': 0, 'limit': None, 'percent': 0, 'type': 'monthly', 'reset': '每月重置'}
    }
    try:
        providers = get_openclaw_config().get('models', {}).get('providers', {})
        for provider_name, provider_config in providers.items():
            if provider_config.get('apiKey'):
                subscription_info = {'plan': provider_name, 'quota_info': '已配置', 'reset_date': '每月重置'}
                break
    except Exception as e:
        logger.warning(f"Subscription info error: {e}")
    return subscription_info, limits_info


def _collect_token_consumers(usage_data):
    """收集 token 消费者数据"""
    token_consumers = []
    model_stats = usage_data.get('model_stats', {})
    if model_stats:
        for model_name, stats in model_stats.items():
            tokens = stats.get('tokens', 0)
            calls = stats.get('calls', 0)
            provider = 'unknown'
            if '/' in model_name:
                provider = model_name.split('/')[0]
            elif 'glm' in model_name.lower():
                provider = 'zai'
            elif 'qwen' in model_name.lower():
                provider = 'bailian'
            elif 'MiniMax' in model_name or 'minimax' in model_name.lower():
                provider = 'minimax'
            elif 'hunyuan' in model_name.lower():
                provider = 'hunyuan'
            token_consumers.append({
                'model': model_name,
                'provider': provider,
                'total_tokens': tokens,
                'input_tokens': tokens,
                'output_tokens': 0,
                'cache_read': 0,
                'count': calls
            })
    
    if not token_consumers:
        try:
            with open(AGENT_COORD_FILE, 'r') as f:
                coord_data = json.load(f)
                agent_tokens = {}
                for item in coord_data:
                    agent = item.get('agent', 'unknown')
                    tokens = item.get('tokens', 0)
                    agent_tokens[agent] = agent_tokens.get(agent, 0) + tokens
                token_consumers = [
                    {'model': k, 'provider': 'unknown', 'total_tokens': v, 'input_tokens': v,
                     'output_tokens': 0, 'cache_read': 0, 'count': 0}
                    for k, v in sorted(agent_tokens.items(), key=lambda x: x[1], reverse=True)[:5]
                ]
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass
    
    return token_consumers


# === 主收集循环 ===
_loop_running = False
_loop_thread = None


def collect():
    """
    主收集循环 - 分离高频/低频采集
    高频(30s): usage, sessions, connections
    低频(300s): tasks, documents, agents
    极低频(600s): risks, task_chains
    """
    global _loop_running
    _loop_running = True
    
    # 上次执行时间跟踪
    last_high = 0      # 高频数据
    last_low = 0       # 低频数据
    last_vlow = 0      # 极低频数据
    last_full = 0      # 上次完整收集
    
    # 预加载的 shared_tasks（避免重复读取）
    cached_tasks = None
    cached_task_info = None
    
    # 预加载的 skills（低频）
    cached_skills = None
    
    # 预加载的文档（低频）
    cached_documents = None
    cached_memories = None
    
    # 预加载的风险（极低频）
    cached_risks = None
    
    # 预加载的任务链（极低频）
    cached_task_chains = None
    cached_agent_participation = None
    
    while _loop_running:
        try:
            now = time.time()
            interval = now - last_full
            
            # 高频数据（30s 间隔）
            if now - last_high >= 30:
                last_high = now
                # usage, sessions, connections 在高频路径更新
                pass
            
            # 低频数据（300s 间隔）
            if now - last_low >= 300:
                last_low = now
                cached_tasks, cached_task_info = get_tasks_data_cached()
                cached_skills = _collect_skills_data()
                docs_and_mems = get_documents_data_cached()
                cached_documents = docs_and_mems.get('documents', {})
                cached_memories = docs_and_mems.get('memories', {})
            
            # 极低频数据（600s 间隔）
            if now - last_vlow >= 600:
                last_vlow = now
                cached_risks = get_risks_cached()
                cached_task_chains = get_task_chains_cached()
                cached_agent_participation = get_agent_participation_cached()
            
            # === 执行数据收集 ===
            # 1. 读取 shared_tasks 一次
            if cached_tasks is None:
                cached_tasks, cached_task_info = get_tasks_data_cached()
            tasks_list = cached_tasks
            task_info = cached_task_info
            
            # 2. 高频数据
            usage_data = get_usage_data_cached()
            sessions_data = get_sessions_data_cached()
            connections_data = get_connections_cached()
            
            # 3. 低频数据（如果还没缓存）
            if cached_skills is None:
                cached_skills = _collect_skills_data()
            if docs_and_mems is None:
                docs_and_mems = get_documents_data_cached()
                cached_documents = docs_and_mems.get('documents', {})
                cached_memories = docs_and_mems.get('memories', {})
            
            # 4. 极低频（如果还没缓存）
            if cached_risks is None:
                cached_risks = get_risks_cached()
            if cached_task_chains is None:
                cached_task_chains = get_task_chains_cached()
            if cached_agent_participation is None:
                cached_agent_participation = get_agent_participation_cached()
            
            # === 构建 agents 列表 ===
            agents_list = _build_agents_list(usage_data, sessions_data, task_info, tasks_list)
            
            # === 会话统计 ===
            total_sessions_count = len(sessions_data)
            active_sessions_count = len([s for s in sessions_data if s.get('status') == 'active'])
            
            # === 订阅信息 ===
            subscription_info, limits_info = _collect_subscription_info()
            
            # === Token 消费者 ===
            token_consumers = _collect_token_consumers(usage_data)
            
            # === 系统信息 ===
            sys_info = get_system_info_cached()
            
            # === 任务统计 ===
            running = task_info['running']
            completed = task_info['done']
            
            # === Uptime ===
            server_uptime_seconds = time.time() - SERVER_START_TIME
            server_uptime_hours = round(server_uptime_seconds / 3600, 1)
            
            # === 模型数据 ===
            models_data = _build_models_data(agents_list, usage_data.get('model_stats', {}))
            
            # === 更新 Handler.last_data ===
            from server.http_handler import Handler
            
            Handler.last_data = {
                'status': 'healthy',
                'task_monitor': {
                    'total_tasks': task_info['total'],
                    'pending_tasks': task_info['pending'],
                    'running_tasks': task_info['running'],
                    'completed_tasks': task_info['done'],
                    'last_detect_time': task_info['last_detect']
                },
                'agents': agents_list,
                'tasks': tasks_list,
                'skills': cached_skills,
                'usage': {
                    'requests_today': usage_data.get('requests_today', 0),
                    'messages_today': usage_data.get('messages_today', 0),
                    'input_tokens_today': usage_data.get('input_tokens_today', 0),
                    'output_tokens_today': usage_data.get('output_tokens_today', 0),
                    'cache_read_today': usage_data.get('cache_read_today', 0),
                    'cache_write_today': usage_data.get('cache_write_today', 0),
                    'cost_estimate': usage_data.get('cost_estimate', 0),
                    'cache_hit_rate': usage_data.get('cache_hit_rate', 0),
                    'tokens_today': usage_data.get('tokens_today', 0),
                    'uptime': format_uptime(server_uptime_seconds),
                    'connections': connections_data,
                    'subscription': subscription_info,
                    'limits': limits_info,
                    'token_consumers': token_consumers,
                    'today_stats': {
                        'input_tokens': usage_data.get('input_tokens_today', 0),
                        'output_tokens': usage_data.get('output_tokens_today', 0),
                        'cache_read': usage_data.get('cache_read_today', 0),
                        'total_tokens': usage_data.get('tokens_today', 0),
                        'request_count': usage_data.get('requests_today', 0)
                    },
                    'model_stats': usage_data.get('model_stats', {}),
                    'recent_activities': usage_data.get('recent_activities', [])
                },
                'summary': {
                    'system_status': 'healthy',
                    'active_agents': len([a for a in agents_list if a.get('status') in ['active', 'busy']]),
                    'running_tasks': running,
                    'completed_tasks': completed,
                    'failed_tasks': task_info.get('failed', 0),
                    'total_tasks': task_info['total'],
                    'total_sessions': total_sessions_count,
                    'active_sessions': active_sessions_count,
                    'uptime_hours': server_uptime_hours,
                    'system_uptime_hours': sys_info.get('uptime_hours', server_uptime_hours)
                },
                'collaboration': {
                    'sessions': sessions_data,
                    'messages': usage_data.get('recent_activities', [])[:50],
                    'task_chains': cached_task_chains,
                    'agent_participation': cached_agent_participation,
                    'recent_activities': usage_data.get('recent_activities', [])
                },
                'documents': cached_documents,
                'memories': cached_memories,
                'risks': cached_risks,
                'file_changes': [],
                'system': sys_info,
                'connections': connections_data,
                'last_update': datetime.now().isoformat(),
                'models': models_data
            }
            
            # === 广播 SSE ===
            from server.sse_manager import broadcast_sse
            broadcast_sse(Handler.last_data)
            
            last_full = now
            
        except Exception as e:
            logger.error(f"Collect loop error: {e}")
        
        time.sleep(10)


def _build_agents_list(usage_data, sessions_data, task_info, tasks_list):
    """构建 agents 列表"""
    agents_list = []
    
    config = get_openclaw_config()
    defaults = config.get('agents', {}).get('defaults', {})
    primary = defaults.get('model', {}).get('primary', '')
    default_model = primary.split('/')[-1] if '/' in primary else 'glm-4.7-flash'
    
    agent_models = {}
    for agent_cfg in config.get('agents', {}).get('list', []):
        aid = agent_cfg.get('id', '')
        model_cfg = agent_cfg.get('model', {})
        if model_cfg and model_cfg.get('primary'):
            agent_models[aid] = model_cfg['primary'].split('/')[-1]
    
    # 从会话数据统计每个 agent 的活跃状态
    agent_stats = {}
    for sess in sessions_data:
        channel = sess.get('channel', 'unknown')
        if channel not in agent_stats:
            agent_stats[channel] = {'sessions': 0, 'status': 'idle'}
        agent_stats[channel]['sessions'] += 1
        if agent_stats[channel]['status'] == 'idle':
            agent_stats[channel]['status'] = 'active'
    
    # 从任务数据统计每个 agent 的任务数
    agent_task_counts = {}
    running_tasks_count = {}
    for t in tasks_list:
        agent = t.get('agent', 'main')
        agent_task_counts[agent] = agent_task_counts.get(agent, 0) + 1
        if t.get('status') in ['running', 'progress']:
            running_tasks_count[agent] = running_tasks_count.get(agent, 0) + 1
    
    # 从配置获取 agents
    try:
        agent_list = config.get('agents', {}).get('list', [])
        for agent_cfg in agent_list:
            aid = agent_cfg.get('id', '')
            name = agent_cfg.get('name', aid)
            name_key = aid.lower()
            cfg = AGENT_CONFIG.get(name_key, {'icon': '🤖', 'label': name})
            stat = agent_stats.get(name_key, {'tasks': 0, 'sessions': 0, 'status': 'idle'})
            status = stat.get('status', 'idle')
            if running_tasks_count.get(name_key, 0) > 0:
                status = 'busy'
            agents_list.append({
                'name': name,
                'name_key': name_key,
                'status': status,
                'config': cfg,
                'tasks': agent_task_counts.get(name_key, 0),
                'sessions': stat.get('sessions', 0),
                'model': agent_models.get(name_key, default_model)
            })
        if not agents_list:
            raise ValueError('No agents in config')
    except Exception as e:
        logger.warning(f"Failed to get agents from config: {e}")
        for name_key, cfg in AGENT_CONFIG.items():
            stat = agent_stats.get(name_key, {'tasks': 0, 'sessions': 0, 'status': 'idle'})
            status = stat.get('status', 'idle')
            if running_tasks_count.get(name_key, 0) > 0:
                status = 'busy'
            agents_list.append({
                'name': cfg.get('label', name_key),
                'name_key': name_key,
                'status': status,
                'config': cfg,
                'tasks': agent_task_counts.get(name_key, 0),
                'sessions': stat.get('sessions', 0),
                'model': agent_models.get(name_key, default_model)
            })
    
    return agents_list


def start():
    """启动收集循环（在独立线程中）"""
    global _loop_thread, _loop_running
    if _loop_running:
        return
    _loop_running = True
    
    # 立即执行一次数据收集，避免初始空数据
    try:
        collect_once()
    except Exception as e:
        logger.warning(f"Initial collect failed: {e}")
    
    _loop_thread = threading.Thread(target=collect, daemon=True)
    _loop_thread.start()
    logger.info("Collect loop started")


def collect_once():
    """立即执行一次数据收集"""
    logger.info("Performing initial data collection...")
    
    # 获取所有数据
    cached_tasks, cached_task_info = get_tasks_data_cached()
    cached_skills = _collect_skills_data()
    docs_and_mems = get_documents_data_cached()
    cached_documents = docs_and_mems.get('documents', {})
    cached_memories = docs_and_mems.get('memories', {})
    cached_risks = get_risks_cached()
    cached_task_chains = get_task_chains_cached()
    cached_agent_participation = get_agent_participation_cached()
    
    tasks_list = cached_tasks
    task_info = cached_task_info
    
    usage_data = get_usage_data_cached()
    sessions_data = get_sessions_data_cached()
    sys_info = get_system_info_cached()
    connections_data = get_connections_cached()
    
    # 计算统计数据
    tasks_copy = list(tasks_list) if tasks_list else []
    running = len([t for t in tasks_copy if t.get('status') in ['running', 'progress']])
    done = len([t for t in tasks_copy if t.get('status') in ['done', 'completed']])
    pending = len([t for t in tasks_copy if t.get('status') == 'pending'])
    failed = len([t for t in tasks_copy if t.get('status') == 'failed'])
    
    total_sessions_count = len(sessions_data) if sessions_data else 0
    active_sessions_count = len([s for s in sessions_data if s.get('active')]) if sessions_data else 0
    
    server_uptime_seconds = time.time() - SERVER_START_TIME
    server_uptime_hours = round(server_uptime_seconds / 3600, 1)
    
    models_data = _build_models_data([], usage_data.get('model_stats', {}))
    
    from server.http_handler import Handler
    
    Handler.last_data = {
        'status': 'healthy',
        'task_monitor': {
            'total_tasks': task_info['total'],
            'pending_tasks': task_info['pending'],
            'running_tasks': task_info['running'],
            'completed_tasks': task_info['done'],
            'last_detect_time': task_info['last_detect']
        },
        'agents': [],
        'tasks': tasks_list,
        'skills': cached_skills,
        'usage': {
            'requests_today': usage_data.get('requests_today', 0),
            'messages_today': usage_data.get('messages_today', 0),
            'input_tokens_today': usage_data.get('input_tokens_today', 0),
            'output_tokens_today': usage_data.get('output_tokens_today', 0),
            'cache_read_today': usage_data.get('cache_read_today', 0),
            'cache_write_today': usage_data.get('cache_write_today', 0),
            'cost_estimate': usage_data.get('cost_estimate', 0),
            'cache_hit_rate': usage_data.get('cache_hit_rate', 0),
            'tokens_today': usage_data.get('tokens_today', 0),
            'uptime': format_uptime(server_uptime_seconds),
            'connections': connections_data,
            'token_consumers': [],
            'today_stats': {
                'input_tokens': usage_data.get('input_tokens_today', 0),
                'output_tokens': usage_data.get('output_tokens_today', 0),
                'cache_read': usage_data.get('cache_read_today', 0),
                'total_tokens': usage_data.get('tokens_today', 0),
                'request_count': usage_data.get('requests_today', 0)
            },
            'model_stats': usage_data.get('model_stats', {}),
            'recent_activities': usage_data.get('recent_activities', [])
        },
        'summary': {
            'system_status': 'healthy',
            'active_agents': 0,
            'running_tasks': running,
            'completed_tasks': done,
            'failed_tasks': failed,
            'total_tasks': task_info['total'],
            'total_sessions': total_sessions_count,
            'active_sessions': active_sessions_count,
            'uptime_hours': server_uptime_hours,
            'system_uptime_hours': sys_info.get('uptime_hours', server_uptime_hours)
        },
        'collaboration': {
            'sessions': sessions_data,
            'messages': usage_data.get('recent_activities', [])[:50],
            'task_chains': cached_task_chains,
            'agent_participation': cached_agent_participation,
            'recent_activities': usage_data.get('recent_activities', [])
        },
        'documents': cached_documents,
        'memories': cached_memories,
        'risks': cached_risks,
        'file_changes': [],
        'system': sys_info,
        'connections': connections_data,
        'last_update': datetime.now().isoformat(),
        'models': models_data
    }
    
    logger.info(f"Initial data collected: {task_info['total']} tasks, {total_sessions_count} sessions")


def stop():
    """停止收集循环"""
    global _loop_running
    _loop_running = False
