#!/usr/bin/env python3
"""
Token 管理器 - 校验和同步 Dashboard Token 与 OpenClaw Gateway Token
- 检查 Dashboard token 是否与 OpenClaw 配置一致
- 验证 token 格式和有效性
- 记录 token 状态变更
"""

import os
import sys
import json
import re
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('token_manager')

DASHBOARD_DIR = '/data/DragonClaw/dashboard'
DASHBOARD_TOKEN_FILE = os.path.join(DASHBOARD_DIR, '.auth_token')
OPENCLAW_CONFIG = '/root/.openclaw/openclaw.json'
OPENCLAW_STATE_DIR = os.environ.get('OPENCLAW_STATE_DIR', '/data/.openclaw')


def get_openclaw_gateway_token():
    """从环境变量或配置获取 OpenClaw Gateway Token"""
    # 优先从环境变量获取
    token = os.environ.get('OPENCLAW_GATEWAY_TOKEN', '')
    if token:
        return token
    
    # 尝试从配置文件读取（如果是明文）
    try:
        with open(OPENCLAW_CONFIG, 'r') as f:
            config = json.load(f)
            auth = config.get('gateway', {}).get('auth', {})
            token = auth.get('token', '')
            if token and not token.startswith('${'):
                return token
    except Exception as e:
        logger.warning(f"Failed to read OpenClaw config: {e}")
    
    return ''


def get_dashboard_token():
    """获取 Dashboard 当前 token"""
    try:
        if os.path.exists(DASHBOARD_TOKEN_FILE):
            with open(DASHBOARD_TOKEN_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to read dashboard token: {e}")
    return ''


def validate_token_format(token):
    """验证 token 格式"""
    if not token or not isinstance(token, str):
        return False, "Token is empty or not a string"
    
    # Dashboard token: 32字符十六进制
    if len(token) == 32 and re.match(r'^[a-fA-F0-9]+$', token):
        return True, "Valid dashboard token format"
    
    # Gateway token: 可能是更长的十六进制字符串
    if re.match(r'^[a-fA-F0-9]+$', token):
        if len(token) >= 32:
            return True, f"Valid gateway token format ({len(token)} chars)"
    
    return False, f"Invalid token format (len={len(token)})"


def sync_token():
    """同步 Token"""
    gateway_token = get_openclaw_gateway_token()
    dashboard_token = get_dashboard_token()
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'gateway_token': gateway_token[:8] + '...' if gateway_token else 'None',
        'gateway_token_length': len(gateway_token) if gateway_token else 0,
        'dashboard_token': dashboard_token[:8] + '...' if dashboard_token else 'None',
        'dashboard_token_length': len(dashboard_token) if dashboard_token else 0,
        'tokens_match': gateway_token == dashboard_token if (gateway_token and dashboard_token) else False,
        'status': 'ok'
    }
    
    # 验证格式
    if dashboard_token:
        valid, msg = validate_token_format(dashboard_token)
        result['dashboard_token_valid'] = valid
        result['dashboard_token_msg'] = msg
        if not valid:
            result['status'] = 'warning'
            logger.warning(f"Dashboard token format issue: {msg}")
    else:
        result['dashboard_token_valid'] = False
        result['dashboard_token_msg'] = "No dashboard token found"
        result['status'] = 'error'
    
    if gateway_token:
        valid, msg = validate_token_format(gateway_token)
        result['gateway_token_valid'] = valid
        result['gateway_token_msg'] = msg
    else:
        result['gateway_token_valid'] = False
        result['gateway_token_msg'] = "No gateway token found"
        result['status'] = 'error'
    
    # 如果 token 不匹配，记录警告
    if gateway_token and dashboard_token and gateway_token != dashboard_token:
        result['status'] = 'warning'
        result['note'] = "Tokens differ (separate auth systems)"
        logger.warning(f"Token mismatch: Gateway={gateway_token[:8]}... Dashboard={dashboard_token[:8]}...")
    
    return result


def main():
    print("🔐 DragonClaw Token 状态检查")
    print("=" * 50)
    
    result = sync_token()
    
    print(f"\n⏰ 检查时间: {result['timestamp']}")
    print(f"\n📊 Token 状态:")
    print(f"   Gateway Token: {result['gateway_token']} ({result['gateway_token_length']} chars) - {result.get('gateway_token_msg', 'N/A')}")
    print(f"   Dashboard Token: {result['dashboard_token']} ({result['dashboard_token_length']} chars) - {result.get('dashboard_token_msg', 'N/A')}")
    print(f"   格式验证: Dashboard={'✅' if result.get('dashboard_token_valid') else '❌'} Gateway={'✅' if result.get('gateway_token_valid') else '❌'}")
    print(f"   Token 一致: {'✅ 是' if result['tokens_match'] else '⚠️ 否（独立认证系统）'}")
    
    status_icon = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}
    print(f"\n📈 总体状态: {status_icon.get(result['status'], '❓')} {result['status'].upper()}")
    
    if result.get('note'):
        print(f"   💡 {result['note']}")
    
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
