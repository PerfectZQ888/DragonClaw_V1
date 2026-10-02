"""
API Models - 模型数据构建
"""

import logging
import json
import os

logger = logging.getLogger('dashboard')


def _get_openclaw_config():
    """获取 OpenClaw 配置（带缓存）"""
    return _config_cache.get('openclaw_config', _load_openclaw_config)


def _load_openclaw_config():
    """实际读取配置"""
    try:
        config_path = os.path.expanduser('~/.openclaw/openclaw.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load config: {e}")
        return {}


# 懒加载，避免循环导入
_config_cache = None


def set_config_cache(cache):
    """设置配置缓存引用"""
    global _config_cache
    _config_cache = cache


def build_models_data(agents, model_stats):
    """从 OpenClaw 配置构建所有模型数据"""
    models = []
    
    try:
        config = _get_openclaw_config()
        providers = config.get('models', {}).get('providers', {})
        
        current_models = set(a.get('model', '') for a in agents)
        
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
                
                expire_info = ''
                if '100万' in model_name:
                    expire_info = '付费模型'
                
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
