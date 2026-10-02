#!/usr/bin/env python3
"""
DragonClaw 监控中心 - 入口文件 (简化版)
重构后: 仅保留 import + 配置 + 启动
所有业务逻辑移至 collect_loop.py
"""

import logging
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PORT
from collect_loop import start as start_collect_loop
from server.http_handler import ThreadedTCPServer, Handler
from server.auth import get_cached_auth_token

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('dashboard')


if __name__ == '__main__':
    auth_token = get_cached_auth_token()
    print(f"Dashboard server starting on port {PORT}...")
    print(f"Auth token: {auth_token}")
    
    # 启动收集循环（在独立线程中）
    start_collect_loop()
    logger.info(f"Dashboard collect loop started, token: {auth_token}")
    
    # 启动 HTTP 服务器
    server = ThreadedTCPServer(('0.0.0.0', PORT), Handler)
    print(f"Server running at http://0.0.0.0:{PORT}/")
    print(f"Token: {auth_token}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
