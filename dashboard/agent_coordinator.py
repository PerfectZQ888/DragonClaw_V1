#!/usr/bin/env python3
"""
DragonClaw Agent Coordination Monitor
监控 Agent 协作任务，支持 sessions_spawn、delegate 等
"""
import json
import os
import time
import glob
from datetime import datetime

# 配置
AGENTS_DIR = "/root/.openclaw/agents"
SHARED_COORD_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_agent_coordination.json"
COORD_LOG_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_coordination_log.json"

class AgentCoordinationMonitor:
    def __init__(self):
        self.tasks = self._load_tasks()
        self.processed_messages = self._load_processed()
        
    def _load_tasks(self):
        """加载已有任务"""
        try:
            if os.path.exists(SHARED_COORD_FILE):
                with open(SHARED_COORD_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def _load_processed(self):
        """加载已处理的消息 ID"""
        try:
            if os.path.exists(COORD_LOG_FILE):
                with open(COORD_LOG_FILE, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def _save_tasks(self):
        """保存任务"""
        try:
            with open(SHARED_COORD_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _save_processed(self):
        """保存已处理的消息 ID"""
        try:
            with open(COORD_LOG_FILE, 'w') as f:
                json.dump(list(self.processed_messages), f)
        except:
            pass
    
    def _get_session_files(self):
        """获取所有 session 文件"""
        files = []
        for agent_dir in glob.glob(f"{AGENTS_DIR}/*/sessions/*.jsonl"):
            if not agent_dir.endswith('.lock') and '.deleted.' not in agent_dir and '.reset.' not in agent_dir:
                files.append(agent_dir)
        return files
    
    def _parse_arguments(self, args_raw):
        """安全解析 arguments 字符串或字典"""
        if isinstance(args_raw, dict):
            return args_raw
        if isinstance(args_raw, str):
            try:
                return json.loads(args_raw)
            except:
                return {}
        return {}
    
    def _extract_agent_from_path(self, filepath):
        """从文件路径提取 agent 名称"""
        parts = filepath.split('/')
        for i, part in enumerate(parts):
            if part == 'agents' and i + 1 < len(parts):
                return parts[i + 1]
        return 'unknown'
    
    def _parse_session_file(self, filepath):
        """解析 session 文件，提取协作任务"""
        tasks = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        msg_id = data.get('id', '')
                        
                        # 跳过已处理的消息
                        if msg_id in self.processed_messages:
                            continue
                            
                        message = data.get('message', {})
                        
                        # 检查是否有 toolCall
                        content = message.get('content', [])
                        if isinstance(content, list):
                            for item in content:
                                if not isinstance(item, dict):
                                    continue
                                    
                                # sessions_spawn 调用
                                if item.get('type') == 'toolCall' and item.get('name') == 'sessions_spawn':
                                    args = self._parse_arguments(item.get('arguments', '{}'))
                                    task_info = {
                                        'id': msg_id,
                                        'type': 'spawn',
                                        'tool_name': item.get('name'),
                                        'tool_call_id': item.get('id', ''),
                                        'parent_session': os.path.basename(filepath),
                                        'timestamp': data.get('timestamp', ''),
                                        'agent': self._extract_agent_from_path(filepath),
                                        'target_agent': args.get('agentId', 'unknown'),
                                        'task': str(args.get('task', ''))[:200],
                                        'mode': args.get('runtime', 'subagent'),
                                        'status': 'spawned'
                                    }
                                    tasks.append(task_info)
                                    self.processed_messages.add(msg_id)
                                    
                                # sessions_spawn 结果
                                elif item.get('type') == 'toolResult' and item.get('toolName') == 'sessions_spawn':
                                    content_list = item.get('content', [])
                                    result = {}
                                    for c in content_list:
                                        if isinstance(c, dict) and c.get('type') == 'text':
                                            try:
                                                result = json.loads(c.get('text', '{}'))
                                            except:
                                                pass
                                    
                                    task_info = {
                                        'id': msg_id,
                                        'type': 'spawn_result',
                                        'tool_call_id': item.get('toolCallId', ''),
                                        'parent_session': os.path.basename(filepath),
                                        'timestamp': data.get('timestamp', ''),
                                        'agent': self._extract_agent_from_path(filepath),
                                        'status': result.get('status', 'unknown'),
                                        'child_session_key': result.get('childSessionKey', ''),
                                        'run_id': result.get('runId', ''),
                                        'mode': result.get('mode', '')
                                    }
                                    tasks.append(task_info)
                                    self.processed_messages.add(msg_id)
                                    
                                # delegate/sessions_send 调用
                                elif item.get('type') == 'toolCall' and item.get('name') in ['delegate', 'sessions_send', 'message']:
                                    args = self._parse_arguments(item.get('arguments', '{}'))
                                    task_info = {
                                        'id': msg_id,
                                        'type': 'delegate',
                                        'tool_name': item.get('name'),
                                        'tool_call_id': item.get('id', ''),
                                        'parent_session': os.path.basename(filepath),
                                        'timestamp': data.get('timestamp', ''),
                                        'agent': self._extract_agent_from_path(filepath),
                                        'target': str(args.get('target', args.get('agentId', 'unknown'))),
                                        'task': str(args.get('task', args.get('message', '')))[:200],
                                        'status': 'delegated'
                                    }
                                    tasks.append(task_info)
                                    self.processed_messages.add(msg_id)
                    except:
                        continue
        except:
            pass
        return tasks
    
    def scan_sessions(self):
        """扫描所有 session 文件"""
        new_tasks = []
        
        for filepath in self._get_session_files():
            try:
                tasks = self._parse_session_file(filepath)
                new_tasks.extend(tasks)
            except Exception as e:
                print(f"扫描 {filepath} 错误: {e}")
        
        # 添加新任务
        if new_tasks:
            self.tasks.extend(new_tasks)
            # 按时间排序
            self.tasks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            # 只保留最近 100 条
            self.tasks = self.tasks[:100]
            self._save_tasks()
            self._save_processed()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 发现 {len(new_tasks)} 个新协作记录")
        
        return len(new_tasks)
    
    def get_coordination_summary(self):
        """获取协作摘要"""
        summary = {
            'total': len(self.tasks),
            'by_type': {},
            'by_agent': {},
            'recent_tasks': self.tasks[:20]
        }
        
        for task in self.tasks:
            task_type = task.get('type', 'unknown')
            agent = task.get('agent', 'unknown')
            summary['by_type'][task_type] = summary['by_type'].get(task_type, 0) + 1
            summary['by_agent'][agent] = summary['by_agent'].get(agent, 0) + 1
        
        return summary
    
    def run_once(self):
        """运行一次扫描"""
        print("🔍 扫描 Agent 协作任务...")
        count = self.scan_sessions()
        print(f"扫描完成，找到 {count} 个新记录")
        print(f"总计 {len(self.tasks)} 个协作记录")
        for t in self.tasks[:5]:
            print(f"  - [{t.get('type')}] {t.get('agent')} → {t.get('target_agent', t.get('target', '?'))}: {t.get('task', '')[:60]}")
        return self.tasks
    
    def run(self):
        """运行监控循环"""
        print("🚀 Agent 协作监控启动...")
        print(f"   目录: {AGENTS_DIR}")
        print(f"   输出: {SHARED_COORD_FILE}")
        print(f"   已有记录: {len(self.tasks)} 条")
        print("   每 3 秒检查一次...")
        
        while True:
            try:
                self.scan_sessions()
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n⛔ 停止监控")
                break
            except Exception as e:
                print(f"监控循环错误: {e}")
                time.sleep(3)

if __name__ == '__main__':
    import sys
    monitor = AgentCoordinationMonitor()
    
    if '--once' in sys.argv or '-c' in sys.argv:
        monitor.run_once()
    else:
        monitor.run()
