"""
Config - 全局配置
"""

import os
import time

# 服务启动时间
SERVER_START_TIME = time.time()

# 端口
PORT = 8888

# 数据文件路径
AGENT_COORD_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json"

# TTLCache 实例（ttl=60s for usage data, 高频数据）
_data_cache = None  # 延迟初始化

# 配置缓存（60s TTL）
_config_cache = None  # 延迟初始化


def get_data_cache():
    """获取数据缓存实例"""
    global _data_cache
    if _data_cache is None:
        from cache.ttl_cache import TTLCache
        _data_cache = TTLCache(ttl=60, max_size=500)
    return _data_cache


def get_config_cache():
    """获取配置缓存实例"""
    global _config_cache
    if _config_cache is None:
        from cache.ttl_cache import TTLCache
        _config_cache = TTLCache(ttl=60, max_size=100)
    return _config_cache
