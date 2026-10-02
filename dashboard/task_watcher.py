#!/usr/bin/env python3
"""
DragonClaw Task Watcher
Version: V1.1.0
飞书任务实时监听器
- 保存所有历史任务，不只是新任务
- 检测429错误并自动重试（最多1000次，等待30秒）
"""
import json
import os
import time
from datetime import datetime, timedelta

SHARED_TASKS_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_shared_tasks.json"
SESSIONS_FILE = "/data/.openclaw/agents/main/sessions/sessions.json"
PROCESSED_IDS_FILE = "/data/DragonClaw/dashboard/data/dragonclaw_processed_ids.json"

MAX_RETRY_COUNT = 1000
MAX_PROCESSED_IDS = 10000  # FIFO 上限，防止无限增长
RETRY_WAIT_SECONDS = 30
ERROR_KEYWORDS = ['429', 'rate limit', '速率限制', 'network_error']

PENDING_TIMEOUT_MINUTES = 60  # pending 任务超过1小时标记为失败
AUTO_DONE_MINUTES = 30  # pending 任务超过30分钟自动标记为done

# 历史任务清理阈值
CLEANUP_FAILED_DAYS = 30   # failed 任务保留 30 天后清理
CLEANUP_DONE_DAYS = 60     # done 任务保留 60 天后清理

TASK_CATEGORIES = {
    'file': ['.xlsx', '.xls', '.docx', '.pdf', '.txt', 'file_key', 'media attached', 'file_name', '南光', '监控'],
    'code': ['sql', 'python', '代码', '编程', '函数', '脚本', '优化', '备份策略'],
    'skill': ['技能', 'skill', 'clowhub', '安装', '配置'],
    'question': ['帮我看看', '查下', '问问', '什么是', '如何', '怎么', '看看'],
    'create': ['帮我写', '生成', '创建', '整理', '拟定', '制作'],
}

def classify_task(title):
    """根据任务标题智能分类"""
    title_lower = title.lower()
    for category, keywords in TASK_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return category
    return 'other'

def deduplicate_tasks(tasks, existing_tasks):
    """去重任务：基于标题相似度"""
    new_tasks = []
    for task in tasks:
        title = task.get('title', '')
        is_duplicate = False
        for existing in existing_tasks:
            existing_title = existing.get('title', '')
            if title[:30] == existing_title[:30]:
                is_duplicate = True
                break
        if not is_duplicate:
            new_tasks.append(task)
    return new_tasks

class TaskWatcher:
    def __init__(self):
        self.processed_ids = self._load_processed()
        self.all_tasks = self._load_all_tasks()
        self._cleanup_counter = 0  # 每 N 次循环执行一次清理
    
    def _cleanup_old_tasks(self):
        """清理过期的 failed/done 任务，防止数据无限膨胀"""
        before = len(self.all_tasks)
        now = datetime.now()
        kept = []
        removed_failed = 0
        removed_done = 0
        
        for t in self.all_tasks:
            status = t.get('status', '')
            task_time_str = t.get('time', '')
            
            # 解析任务时间
            try:
                if not task_time_str:
                    task_dt = None
                elif task_time_str.startswith('20') and '-' in task_time_str and ' ' in task_time_str:
                    # 格式: "2026-03-21 12:10" (完整日期)
                    task_dt = datetime.strptime(task_time_str, "%Y-%m-%d %H:%M")
                elif ' ' in task_time_str and '-' in task_time_str:
                    # 格式: "03-26 13:32" -> 2026-03-26 13:32
                    parts = task_time_str.split(' ')
                    date_part = parts[0]
                    time_part = parts[1]
                    year = now.year
                    task_dt = datetime.strptime(f"{year}-{date_part} {time_part}", "%Y-%m-%d %H:%M")
                else:
                    task_dt = None
            except:
                task_dt = None
            
            # 判断是否过期
            if task_dt:
                days_old = (now - task_dt).days
                if status == 'failed' and days_old > CLEANUP_FAILED_DAYS:
                    removed_failed += 1
                    continue
                if status == 'done' and days_old > CLEANUP_DONE_DAYS:
                    removed_done += 1
                    continue
            
            kept.append(t)
        
        if removed_failed or removed_done:
            self.all_tasks = kept
            print(f"[CLEANUP] 清理 {removed_failed} 个过期 failed 任务，{removed_done} 个过期 done 任务 (剩余 {len(self.all_tasks)})")
            self._save_all_tasks()
        
        return before - len(self.all_tasks)
    
    def _load_processed(self):
        try:
            if os.path.exists(PROCESSED_IDS_FILE):
                with open(PROCESSED_IDS_FILE, 'r') as f:
                    return set(json.load(f))
        except:
            pass
        return set()
    
    def _load_all_tasks(self):
        try:
            if os.path.exists(SHARED_TASKS_FILE):
                with open(SHARED_TASKS_FILE, 'r') as f:
                    tasks = json.load(f)
                    for t in tasks:
                        if 'category' not in t:
                            t['category'] = classify_task(t.get('title', ''))
                    return tasks
        except:
            pass
        return []
    
    def _save_processed(self):
        try:
            with open(PROCESSED_IDS_FILE, 'w') as f:
                json.dump(list(self.processed_ids), f)
        except:
            pass
    
    def _save_all_tasks(self):
        try:
            with open(SHARED_TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.all_tasks, f, ensure_ascii=False)
        except:
            pass
    
    def _parse_task(self, text):
        """Parse user message text to extract task title.
        Supports: Feishu envelope format, QQ bot format, plain messages.
        """
        if not text:
            return None

        import re
        text = text.strip()

        TASK_KEYWORDS = ['任务', 'TODO', '待办', '帮我', '重新', '检查', '处理', '分析',
                         '整理', '生成', '创建', 'Word', '文档', '研究', '开发', '计划',
                         '协调', '技能', '看看', '发我', 'V1.0', 'V2.0', 'V2.5', 'V2.6',
                         'V2.7', 'V2.8', '修改', '更新', '按照', '优化', '修复', '排查',
                         '挪到', '部署', '配置', '安装', '清理', '检查下', '转换']

        # Case 1: Feishu envelope — extract "用户XXXX:" content
        if 'Conversation info' in text:
            match = re.search(r'用户\d+:\s*(.+)', text, re.DOTALL)
            if match:
                user_text = match.group(1).strip()
                # Handle JSON file attachments
                if user_text.startswith('{') and 'file_key' in user_text:
                    fn_match = re.search(r'"file_name"\s*:\s*"([^"]+)"', user_text)
                    if fn_match:
                        return f'[文件] {fn_match.group(1)}'[:150]
                    return None
                if user_text and len(user_text) > 1:
                    # Check for task keywords OR file attachments
                    if any(kw in user_text for kw in TASK_KEYWORDS) or 'media attached' in user_text:
                        return user_text[:150]
                    # Plain messages > 5 chars are also tasks
                    if len(user_text) > 5:
                        return user_text[:150]

            # Fallback: scan last non-meta lines
            lines = text.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if not line or line.startswith('```') or line.startswith('{') or line.startswith('}'):
                    continue
                user_text = re.sub(r'^用户\d+:\s*', '', line).strip()
                if user_text and len(user_text) > 1:
                    return user_text[:150]

        # Case 2: Plain text — find first meaningful line
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            if any(x in line for x in ['Conversation info', 'untrusted', '```', '```json']):
                continue
            if any(kw in line for kw in TASK_KEYWORDS) or len(line) > 5:
                return line[:150]

        return None
    
    def _extract_tasks_from_session(self, session_id, session_file, agent_name='main'):
        tasks = []
        
        if not os.path.exists(session_file):
            return tasks
        
        # 获取会话的渠道信息
        source = 'feishu'  # 默认
        try:
            sessions_file = f'/data/.openclaw/agents/{agent_name}/sessions/sessions.json'
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r') as f:
                    sessions_data = json.load(f)
                    # 查找对应的会话
                    for key, value in sessions_data.items():
                        if isinstance(value, dict) and value.get('sessionId') == session_id:
                            # 从 session key 或 lastChannel 获取来源
                            if 'qqbot' in key.lower() or value.get('lastChannel') == 'qqbot':
                                source = 'qq'
                            elif 'feishu' in key.lower() or value.get('lastChannel') == 'feishu':
                                source = 'feishu'
                            break
        except:
            pass
        
        try:
            with open(session_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if '"type":"message"' not in line or '"role":"user"' not in line:
                        continue
                    
                    try:
                        msg_data = json.loads(line)
                        msg = msg_data.get('message', {})
                        content = msg.get('content', '')
                        
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get('type') == 'text':
                                    text = c.get('text', '')
                                    task = self._parse_task(text)
                                    
                                    if task:
                                        msg_id = msg_data.get('id', 'unknown')
                                        if msg_id not in self.processed_ids:
                                            self.processed_ids.add(msg_id)
                                            # FIFO 裁剪：超过上限时删除最早的 ID
                                            if len(self.processed_ids) > MAX_PROCESSED_IDS:
                                                # set 无顺序，转为有序列表裁剪后转回 set
                                                ids_sorted = sorted(self.processed_ids)
                                                ids_sorted = ids_sorted[-MAX_PROCESSED_IDS:]
                                                self.processed_ids = set(ids_sorted)
                                            
                                            ts = msg_data.get('timestamp', '')
                                            task_datetime = datetime.now()
                                            task_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                                            if ts:
                                                try:
                                                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                                    dt = dt.replace(tzinfo=None)
                                                    dt_beijing = dt + timedelta(hours=8)
                                                    task_time = dt_beijing.strftime('%Y-%m-%d %H:%M')
                                                    task_datetime = dt_beijing
                                                except:
                                                    pass
                                            
                                            task_category = classify_task(task)
                                            
                                            tasks.append({
                                                'id': f'{agent_name}-{msg_id}',
                                                'title': task,
                                                'agent': agent_name,
                                                'status': 'pending',
                                                'priority': 'high',
                                                'category': task_category,
                                                'time': task_time,
                                                'source': source,
                                                'retry_count': 0,
                                                'last_error_time': ''
                                            })
                    except:
                        pass
        except Exception as e:
            print(f"读取会话文件错误: {e}")
        
        return tasks
    
    def _check_task_errors(self):
        """检查任务执行是否有错误（如429限流），如果有则增加重试次数"""
        error_tasks = []
        
        agents_base = '/data/.openclaw/agents'
        agent_dirs = ['main', 'research', 'creative', 'dev', 'perfect_openclaw', 'security', 'skill-vetter']
        
        for agent_name in agent_dirs:
            sessions_dir = f'{agents_base}/{agent_name}/sessions'
            
            if not os.path.exists(sessions_dir):
                continue
            
            try:
                sessions_file = f'{sessions_dir}/sessions.json'
                if not os.path.exists(sessions_file):
                    continue
                    
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
            except:
                continue
            
            for session_key, session_data in sessions.items():
                session_id = session_data.get('sessionId', '')
                if not session_id:
                    continue
                
                session_file = f'{sessions_dir}/{session_id}.jsonl'
                if not os.path.exists(session_file):
                    continue
                
                try:
                    with open(session_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            
                            try:
                                msg_data = json.loads(line)
                                msg = msg_data.get('message', {})
                                
                                error_msg = msg.get('errorMessage', '')
                                if error_msg and any(keyword in str(error_msg).lower() for keyword in [k.lower() for k in ERROR_KEYWORDS]):
                                    # 找到用户消息的ID
                                    parent_id = msg_data.get('parentId', '')
                                    if parent_id:
                                        # 找用户消息的ID
                                        with open(session_file, 'r', encoding='utf-8', errors='ignore') as f_check:
                                            for line_check in f_check:
                                                try:
                                                    d_check = json.loads(line_check)
                                                    if d_check.get('id') == parent_id and d_check.get('message', {}).get('role') == 'user':
                                                        task_id = f'{agent_name}-{parent_id}'
                                                        error_tasks.append(task_id)
                                                        break
                                                except:
                                                    pass
                            except:
                                pass
                except:
                    pass
        
        updated_count = 0
        for t in self.all_tasks:
            task_id = t.get('id', '')
            if task_id in error_tasks:
                retry_count = t.get('retry_count', 0)
                
                if retry_count < MAX_RETRY_COUNT:
                    t['retry_count'] = retry_count + 1
                    
                    if t.get('status') == 'done':
                        t['status'] = 'pending'
                        t['last_error_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 任务 {task_id[:40]}... 检测到429错误，第 {retry_count + 1} 次重试 (等待{RETRY_WAIT_SECONDS}秒)")
                        updated_count += 1
                else:
                    if t.get('status') != 'failed':
                        t['status'] = 'failed'
                        t['last_error_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 任务 {task_id[:40]}... 已达最大重试次数({MAX_RETRY_COUNT})，标记为失败")
                        updated_count += 1
        
        return updated_count
    
    def check_for_new_tasks(self):
        """检查新任务"""
        new_tasks_count = 0
        try:
            now = datetime.now()
            
            agents_base = '/data/.openclaw/agents'
            agent_dirs = ['main', 'research', 'creative', 'dev', 'perfect_openclaw', 'security', 'skill-vetter']
            
            for agent_name in agent_dirs:
                sessions_file = f'{agents_base}/{agent_name}/sessions/sessions.json'
                sessions_dir = f'{agents_base}/{agent_name}/sessions'
                
                if not os.path.exists(sessions_file):
                    continue
                
                try:
                    with open(sessions_file, 'r', encoding='utf-8') as f:
                        sessions = json.load(f)
                except:
                    continue
                
                for session_key, session_data in sessions.items():
                    session_id = session_data.get('sessionId', '')
                    if not session_id:
                        continue
                    
                    session_file = f'{sessions_dir}/{session_id}.jsonl'
                    new_tasks = self._extract_tasks_from_session(session_id, session_file, agent_name)
                    
                    new_tasks = deduplicate_tasks(new_tasks, self.all_tasks)
                    
                    for t in new_tasks:
                        exists = any(x.get('id') == t.get('id') for x in self.all_tasks)
                        if not exists:
                            self.all_tasks.append(t)
                            new_tasks_count += 1
            
            status_changed = False
            for t in self.all_tasks:
                if t.get('status') == 'pending':
                    task_time = t.get('time', '00:00')
                    
                    # 解析时间，支持 "HH:MM" 或 "MM-DD HH:MM" 格式
                    try:
                        if ' ' in task_time and '-' in task_time:
                            # 格式: "03-26 13:32"
                            time_part = task_time.split(' ')[1]
                            task_hour = int(time_part.split(':')[0])
                            task_min = int(time_part.split(':')[1])
                        else:
                            # 格式: "13:32"
                            task_hour = int(task_time.split(':')[0])
                            task_min = int(task_time.split(':')[1]) if ':' in task_time else 0
                        
                        current_hour = now.hour
                        current_min = now.minute
                        
                        # 计算分钟差
                        if current_hour >= task_hour:
                            minutes_diff = (current_hour - task_hour) * 60 + (current_min - task_min)
                        else:
                            minutes_diff = ((24 - task_hour) + current_hour) * 60 + (current_min - task_min)
                        
                        # pending 超过1小时，标记为失败
                        if minutes_diff > PENDING_TIMEOUT_MINUTES:
                            t['status'] = 'failed'
                            t['last_error_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] 任务超时({minutes_diff}分钟)，标记为失败: {t.get('title','')[:40]}")
                            status_changed = True
                        # pending 超过5分钟，标记为done（临时方案）
                        elif minutes_diff > AUTO_DONE_MINUTES:
                            t['status'] = 'done'
                            status_changed = True
                    except Exception as e:
                        pass
            
            if new_tasks_count > 0 or status_changed:
                self._save_processed()
                self._save_all_tasks()
                if new_tasks_count > 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 发现 {new_tasks_count} 个新任务 (共 {len(self.all_tasks)} 个)")
        
        except Exception as e:
            print(f"检查任务错误: {e}")
        
        return new_tasks_count
    
    def run(self):
        print("🚀 飞书任务监听器 v4.1 启动...")
        print(f"   监控: {SESSIONS_FILE}")
        print(f"   输出: {SHARED_TASKS_FILE}")
        print(f"   已有任务: {len(self.all_tasks)} 个")
        print(f"   重试配置: 最多{MAX_RETRY_COUNT}次，等待{RETRY_WAIT_SECONDS}秒")
        print("   每3秒检查一次...")
        
        while True:
            try:
                self.check_for_new_tasks()
                
                error_count = self._check_task_errors()
                if error_count > 0:
                    self._save_all_tasks()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 更新了 {error_count} 个任务的错误状态")
                
                # 每 100 次循环（约 5 分钟）执行一次历史清理
                self._cleanup_counter += 1
                if self._cleanup_counter >= 100:
                    self._cleanup_counter = 0
                    self._cleanup_old_tasks()
                
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n⛔ 停止监听")
                break
            except Exception as e:
                print(f"监听循环错误: {e}")
                time.sleep(3)

if __name__ == '__main__':
    watcher = TaskWatcher()
    watcher.run()