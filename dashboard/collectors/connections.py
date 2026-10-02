"""
Connections Collector - 连接状态采集
修复: 优先使用 OpenClaw 官方接口检测通道状态
"""

import json
import os
import subprocess


def get_connections_status():
    """获取连接状态（优先级: openclaw CLI > 配置文件 > 进程检测）"""
    status = {}

    # 获取配置
    config = _get_openclaw_config()
    channels_config = config.get('channels', {})

    # Gateway - 使用 openclaw gateway status（最可靠）
    gateway_status = _get_gateway_status()
    status['gateway'] = gateway_status

    # Feishu - 优先通过 CLI 检测
    feishu_status = _detect_feishu_status(config, channels_config)
    status['feishu'] = feishu_status

    # QQ Bot - 检查配置文件和进程
    qqbot_status = _detect_qqbot_status(config, channels_config)
    status['qqbot'] = qqbot_status

    # 微信 - channel 内置于 gateway，配置文件检测
    weixin_key_exists = 'openclaw-weixin' in channels_config
    status['weixin'] = 'configured' if weixin_key_exists else 'disconnected'

    # API - dashboard_server 自身就是 API，始终在线
    status['api'] = 'active'

    return status


def _get_gateway_status():
    """使用 openclaw gateway status 检测 gateway 状态"""
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'status'],
            capture_output=True, timeout=5, text=True
        )
        output = result.stdout + result.stderr
        if 'Runtime: running' in output or 'state active' in output or result.returncode == 0:
            return 'running'
        # 降级：检查进程
        proc_result = subprocess.run(
            ['pgrep', '-f', 'openclaw-gateway'],
            capture_output=True, timeout=3
        )
        if proc_result.returncode == 0:
            return 'running'
        return 'stopped'
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # 降级：检查进程
        try:
            proc_result = subprocess.run(
                ['pgrep', '-f', 'openclaw-gateway'],
                capture_output=True, timeout=3
            )
            if proc_result.returncode == 0:
                return 'running'
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return 'stopped'


def _detect_feishu_status(config, channels_config):
    """检测飞书通道状态"""
    # 方案1: openclaw feishu status 命令（如果可用）
    try:
        result = subprocess.run(
            ['openclaw', 'feishu', 'status'],
            capture_output=True, timeout=5, text=True
        )
        output = result.stdout + result.stderr
        if 'connected' in output.lower() or 'active' in output.lower():
            return 'connected'
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # 方案2: 检查配置文件
    feishu_config = channels_config.get('feishu', {})
    gateway_running = _check_gateway_process()

    if gateway_running and feishu_config.get('enabled'):
        return 'connected'
    elif feishu_config.get('enabled'):
        return 'configured'
    elif gateway_running:
        # Gateway 运行但飞书未配置
        return 'disconnected'
    else:
        return 'disconnected'


def _detect_qqbot_status(config, channels_config):
    """检测 QQ Bot 通道状态"""
    # 检查进程
    qqbot_process = _check_qqbot_process()

    # 检查环境变量（已配置密钥表示已启用）
    qqbot_env = os.environ.get('QQBOT_CLIENT_SECRET', '')
    qqbot_config = channels_config.get('qqbot', {})
    qqbot_enabled = (
        qqbot_config.get('enabled') or
        (bool(qqbot_env) and qqbot_env != '${QQBOT_CLIENT_SECRET}')
    )

    if qqbot_process or (qqbot_enabled and qqbot_env):
        return 'connected'
    elif qqbot_enabled:
        return 'configured'
    else:
        return 'disconnected'


def _check_gateway_process():
    """检查 gateway 进程是否存在"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'openclaw-gateway'],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _check_qqbot_process():
    """检查 qqbot 进程是否存在"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'qqbot'],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _get_openclaw_config():
    """获取 OpenClaw 配置"""
    try:
        config_path = os.path.expanduser('~/.openclaw/openclaw.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return {}
