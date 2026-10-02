#!/usr/bin/env python3
"""
Server Status Report Script
收集服务器基本信息、磁盘使用情况和进程信息，生成带颜色标识的状态报告
"""

import os
import sys
import subprocess
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# 颜色定义
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_color(percentage, warning_threshold=80, critical_threshold=90):
    """根据使用百分比返回对应颜色"""
    if percentage >= critical_threshold:
        return Colors.RED
    elif percentage >= warning_threshold:
        return Colors.YELLOW
    else:
        return Colors.GREEN

def run_command(cmd):
    """安全执行shell命令，返回输出或None"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, Exception):
        return None

def get_hostname():
    """获取主机名"""
    return os.environ.get('HOSTNAME') or run_command('hostname') or 'Unknown'

def get_os_info():
    """获取操作系统信息"""
    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release', 'r') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    return line.split('=')[1].strip().strip('"')
    return run_command('uname -s') or 'Unknown'

def get_uptime():
    """获取系统运行时间"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except Exception:
        return run_command('uptime -p') or 'Unknown'

def get_cpu_info():
    """获取CPU核心数"""
    if PSUTIL_AVAILABLE:
        return psutil.cpu_count(logical=False), psutil.cpu_count(logical=True)
    else:
        physical = run_command("grep '^physical' /proc/cpuinfo | wc -l")
        logical = run_command("grep -c '^processor' /proc/cpuinfo")
        return (int(physical) if physical else 0, int(logical) if logical else 0)

def get_memory_info():
    """获取内存信息"""
    if PSUTIL_AVAILABLE:
        mem = psutil.virtual_memory()
        return mem.total, mem.available, mem.percent
    else:
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(':')] = int(parts[1])
                total = meminfo.get('MemTotal', 0) * 1024
                available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) * 1024
                used = total - available
                percent = (used / total * 100) if total > 0 else 0
                return total, available, percent
        except Exception:
            return 0, 0, 0

def get_disk_usage(path):
    """获取指定路径的磁盘使用情况"""
    if PSUTIL_AVAILABLE:
        try:
            disk = psutil.disk_usage(path)
            return disk.total, disk.used, disk.free, disk.percent
        except Exception:
            pass
    
    try:
        stat = os.statvfs(path)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        percent = (used / total * 100) if total > 0 else 0
        return total, used, free, percent
    except Exception:
        return 0, 0, 0, 0

def format_bytes(bytes_val):
    """将字节数格式化为可读字符串"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def count_python_processes():
    """统计当前运行的Python进程数"""
    if PSUTIL_AVAILABLE:
        return sum(1 for p in psutil.process_iter(['name']) 
                   if 'python' in p.info['name'].lower())
    else:
        result = run_command("ps aux | grep -c '[p]ython'")
        return int(result) if result and result.isdigit() else 0

def print_header(title):
    """打印带样式的标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*50}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*50}{Colors.END}")

def print_row(label, value, color_func=None):
    """打印表格行"""
    if color_func and callable(color_func):
        value_colored = f"{color_func(value)}{value}{Colors.END}"
        print(f"  {label:<20} : {value_colored}")
    else:
        print(f"  {label:<20} : {value}")

def main():
    """主函数：收集并输出服务器状态报告"""
    print(f"\n{Colors.BOLD}Server Status Report{Colors.END}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 服务器基本信息
    print_header("Server Basic Information")
    hostname = get_hostname()
    os_info = get_os_info()
    uptime = get_uptime()
    physical_cores, logical_cores = get_cpu_info()
    
    print_row("Hostname", hostname)
    print_row("OS", os_info)
    print_row("Uptime", uptime)
    print_row("CPU Cores", f"{physical_cores} Physical / {logical_cores} Logical")
    
    # 内存信息
    print_header("Memory Status")
    mem_total, mem_available, mem_percent = get_memory_info()
    mem_color = get_color(mem_percent)
    print_row("Total Memory", format_bytes(mem_total))
    print_row("Available Memory", format_bytes(mem_available))
    print_row("Usage", f"{mem_percent:.1f}%", lambda x: get_color(mem_percent))
    
    # 磁盘使用情况
    print_header("Disk Usage")
    partitions_to_check = [
        ("/", "Root Partition"),
        ("/data", "/data Partition") if os.path.exists('/data') else None,
    ]
    
    for partition in partitions_to_check:
        if partition is None:
            continue
        path, name = partition
        total, used, free, percent = get_disk_usage(path)
        color = get_color(percent)
        print(f"\n  {Colors.BOLD}{name}{Colors.END} ({path})")
        print_row("Total", format_bytes(total))
        print_row("Used", format_bytes(used))
        print_row("Free", format_bytes(free))
        print_row("Usage", f"{percent:.1f}%", lambda x, c=color: c)
    
    # Python进程统计
    print_header("Python Processes")
    py_count = count_python_processes()
    py_color = Colors.GREEN if py_count < 50 else (Colors.YELLOW if py_count < 100 else Colors.RED)
    print_row("Running Python Processes", str(py_count), lambda x: py_color)
    
    # 依赖检查提示
    if not PSUTIL_AVAILABLE:
        print(f"\n{Colors.YELLOW}Note: psutil not installed. Some info retrieved via /proc.{Colors.END}")
        print(f"{Colors.YELLOW}Install psutil for better compatibility: pip install psutil{Colors.END}")
    
    print()
    return 0

if __name__ == '__main__':
    sys.exit(main())
