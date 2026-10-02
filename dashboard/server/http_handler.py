"""
HTTP Handler - HTTP 服务层
"""

import json
import os
import queue
import secrets
import socketserver
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

from server.auth import check_auth, _validate_token_input, get_cached_auth_token, regenerate_auth_token
from server.sse_manager import add_client, remove_client

logger = logging.getLogger('dashboard')


class ThreadedTCPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    last_data = {
        'status': 'init',
        'agents': [],
        'tasks': [],
        'skills': {'ready': 0, 'missing': 0, 'skills': []},
        'usage': {},
        'summary': {},
        'collaboration': {'sessions': [], 'messages': [], 'task_chains': []},
        'documents': {'files': [], 'memories': []},
        'risks': [],
        'file_changes': [],
        'system': {}
    }
    
    def do_GET(self):
        if not check_auth(self):
            return
        
        path = self.path.split('?')[0]
        
        # 根路径重定向到 index.html
        if path == '/':
            path = '/index.html'
        
        # 静态文件
        if path.endswith(('.html', '.js', '.css', '.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2')):
            static_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if '..' in path:
                self.send_response(403)
                self.end_headers()
                return
            filepath = os.path.join(static_dir, path.lstrip('/'))
            realpath = os.path.realpath(filepath)
            if not realpath.startswith(os.path.realpath(static_dir) + os.sep):
                self.send_response(403)
                self.end_headers()
                return
            if os.path.isfile(filepath):
                import mimetypes
                mime, _ = mimetypes.guess_type(filepath)
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', mime or 'application/octet-stream')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(content)
                except IOError:
                    self.send_response(500)
                    self.end_headers()
                return
        
        # API 端点
        if path == '/api/status':
            data = json.dumps(Handler.last_data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        
        if path.startswith('/api/events'):
            self._send_sse_response()
            return
        
        if path == '/api/coordination':
            coord_data = self._get_coordination_data()
            data = json.dumps(coord_data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        
        if path == '/api/verify-token':
            self._handle_verify_token()
            return
        
        if path == '/api/generate-token':
            self._handle_generate_token()
            return
        
        # 根路径重定向到 index.html
        if path == '/':
            path = '/index.html'
            # 继续处理静态文件
        
        self.send_response(404)
        self.end_headers()
    
    def do_POST(self):
        if self.path.split('?')[0] == '/api/verify-token':
            self._handle_verify_token()
            return
        if not check_auth(self):
            return
        self.send_response(405)
        self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _handle_verify_token(self):
        """验证 token"""
        content_length = min(int(self.headers.get('Content-Length', 0)), 1024)
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        token = ''
        try:
            data = json.loads(body)
            token = data.get('token', '')
        except json.JSONDecodeError:
            pass
        
        if not _validate_token_input(token):
            self._json_response(400, {'valid': False, 'error': 'Invalid token format'})
            return
        
        current_token = get_cached_auth_token()
        if token == current_token and current_token:
            self._json_response(200, {'valid': True})
        else:
            self._json_response(401, {'valid': False, 'error': 'Invalid token'})
    
    def _handle_generate_token(self):
        """生成新 token"""
        new_token = regenerate_auth_token()
        if new_token:
            self._json_response(200, {'token': new_token, 'message': 'Token generated'})
        else:
            self._json_response(500, {'error': 'Failed to generate token'})
    
    def _json_response(self, code, data):
        """发送 JSON 响应"""
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def _get_coordination_data(self):
        """获取协作数据"""
        from config import AGENT_COORD_FILE
        try:
            if os.path.exists(AGENT_COORD_FILE):
                with open(AGENT_COORD_FILE, 'r') as f:
                    tasks = json.load(f)
                    return {
                        'status': 'ok',
                        'total': len(tasks),
                        'spawn_count': len([t for t in tasks if t.get('type') == 'spawn']),
                        'delegate_count': len([t for t in tasks if t.get('type') == 'delegate']),
                        'tasks': tasks[:50],
                        'last_update': self._now_iso()
                    }
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Coordination data error: {e}")
        return {'status': 'ok', 'total': 0, 'spawn_count': 0, 'delegate_count': 0, 'tasks': [], 'last_update': self._now_iso()}
    
    def _now_iso(self):
        """获取当前时间 ISO 格式"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _send_sse_response(self):
        """SSE 流式响应"""
        # SSE 需要认证已在 check_auth 中处理
        client_queue = queue.Queue(maxsize=50)
        client = add_client(client_queue, self.wfile)
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # 连接建立时立即推送当前数据
        try:
            current_data = Handler.last_data
            if current_data and current_data.get('status') == 'healthy':
                init_msg = f"data: {json.dumps(current_data, ensure_ascii=False)}\n\n"
                self.wfile.write(init_msg.encode())
                self.wfile.flush()
        except Exception:
            pass
        
        try:
            while True:
                try:
                    msg = client_queue.get(timeout=30)
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b': keepalive\n\n')
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            remove_client(client)
    
    def log_message(self, format, *args):
        pass
