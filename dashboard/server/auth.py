"""
Auth - Token 认证逻辑（已禁用）
"""

import os
import logging

logger = logging.getLogger('dashboard')


def _validate_token_input(token):
    """验证 token 输入格式和长度"""
    import re
    if not token or not isinstance(token, str):
        return False
    if len(token) != 32:
        return False
    if not re.match(r'^[a-fA-F0-9]+$', token):
        return False
    return True


def check_auth(handler):
    """检查 token 认证 - 已禁用，所有请求都放行"""
    # 所有请求都放行，不做任何验证
    return True


def get_cached_auth_token():
    """获取当前有效的 auth token"""
    token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.auth_token')
    try:
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return f.read().strip()
    except (FileNotFoundError, IOError):
        pass
    return ''


def regenerate_auth_token():
    """重新生成 auth token"""
    import secrets
    new_token = secrets.token_hex(16)
    token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.auth_token')
    try:
        with open(token_file, 'w') as f:
            f.write(new_token)
        os.chmod(token_file, 0o600)
        return new_token
    except IOError as e:
        logger.error(f"Failed to write token file: {e}")
        return None
