"""
System Collector - 系统信息采集
"""

import os
import time


def format_uptime(seconds):
    """格式化运行时长"""
    seconds = int(seconds)
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    if days > 0:
        return f'{days}d {hours}h {minutes}m'
    elif hours > 0:
        return f'{hours}h {minutes}m'
    return f'{minutes}m'


def get_system_uptime_seconds(server_start_time):
    """获取系统运行秒数"""
    try:
        with open('/proc/uptime', 'r') as f:
            return float(f.read().split()[0])
    except (FileNotFoundError, IOError, ValueError):
        return time.time() - server_start_time


def collect_system_info(server_start_time):
    """实际收集系统信息"""
    uptime_seconds = get_system_uptime_seconds(server_start_time)
    uptime_hours = round(uptime_seconds / 3600, 1)
    
    try:
        load1, load5, load15 = os.getloadavg()
    except AttributeError:
        load1 = load5 = load15 = 0.0
    
    # CPU 使用率 - 使用 /proc/stat 计算
    cpu_percent = 0.0
    try:
        with open('/proc/stat', 'r') as f:
            line1 = f.readline()
            fields1 = line1.split()
            if fields1[0] == 'cpu':
                idle1 = int(fields1[4])
                total1 = sum(int(x) for x in fields1[1:8])
        time.sleep(0.5)
        with open('/proc/stat', 'r') as f:
            line2 = f.readline()
            fields2 = line2.split()
            if fields2[0] == 'cpu':
                idle2 = int(fields2[4])
                total2 = sum(int(x) for x in fields2[1:8])
        if total2 > total1:
            cpu_percent = round((1 - (idle2 - idle1) / (total2 - total1)) * 100, 1)
    except Exception as e:
        pass
    
    mem_info = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        mem_info[parts[0].rstrip(':')] = int(parts[1]) * 1024
                    except ValueError:
                        pass
    except IOError:
        pass
    
    total = mem_info.get('MemTotal', 0)
    available = mem_info.get('MemAvailable', mem_info.get('MemFree', 0))
    used = total - available
    mem_percent = (used / total * 100) if total > 0 else 0
    
    disk_root = None
    extra_disks = {}
    for path in ['/', '/data']:
        try:
            stat = os.statvfs(path)
            total_d = stat.f_blocks * stat.f_frsize
            free_d = stat.f_bfree * stat.f_frsize
            used_d = total_d - free_d
            disk_data = {
                'path': path,
                'total': total_d,
                'used': used_d,
                'free': free_d,
                'percent': round((used_d / total_d * 100) if total_d > 0 else 0, 1)
            }
            if path == '/':
                disk_root = disk_data
            else:
                extra_disks[path] = disk_data
        except OSError:
            pass

    return {
        'uptime_seconds': int(uptime_seconds),
        'uptime_hours': uptime_hours,
        'uptime': format_uptime(uptime_seconds),
        'load': [round(load1, 2), round(load5, 2), round(load15, 2)],
        'cpu_percent': round(cpu_percent, 1),
        'memory': {
            'total': total,
            'used': used,
            'available': available,
            'percent': round(mem_percent, 1)
        },
        'disk': disk_root,
        'extra_disks': extra_disks
    }
