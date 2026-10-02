"""
SSE Manager - SSE 客户端管理
"""

import json
import queue
import threading


sse_clients = []
sse_lock = threading.Lock()


def add_client(client_queue, wfile):
    """添加 SSE 客户端"""
    client = {'queue': client_queue, 'wfile': wfile}
    with sse_lock:
        sse_clients.append(client)
    return client


def remove_client(client):
    """移除 SSE 客户端"""
    with sse_lock:
        if client in sse_clients:
            sse_clients.remove(client)


def broadcast_sse(data):
    """广播 SSE 消息"""
    msg = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    dead = []
    
    with sse_lock:
        for client in sse_clients:
            try:
                client['queue'].put_nowait(msg)
            except queue.Full:
                dead.append(client)
        for client in dead:
            if client in sse_clients:
                sse_clients.remove(client)


def get_client_count():
    """获取当前 SSE 客户端数量"""
    with sse_lock:
        return len(sse_clients)
