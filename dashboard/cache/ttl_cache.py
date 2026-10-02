"""
TTLCache - 线程安全的 LRU TTL 缓存
"""

import threading
import time


class TTLCache:
    """线程安全的 LRU TTL 缓存"""
    
    def __init__(self, ttl=10, max_size=1000):
        self.ttl = ttl
        self.max_size = max_size
        self._cache = {}
        self._times = {}
        self._access_order = []
        self._lock = threading.Lock()

    def _prune_expired(self, now):
        """清理所有过期条目"""
        expired = [k for k, t in list(self._times.items()) if now - t >= self.ttl]
        for k in expired:
            self._cache.pop(k, None)
            self._times.pop(k, None)
            if k in self._access_order:
                self._access_order.remove(k)

    def _evict_lru(self):
        """LRU 淘汰：移除最久未访问的条目"""
        while len(self._cache) >= self.max_size and self._access_order:
            oldest = self._access_order.pop(0)
            self._cache.pop(oldest, None)
            self._times.pop(oldest, None)

    def _touch(self, key):
        """更新 LRU 顺序"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def get(self, key, collector_fn=None, *args, **kwargs):
        """获取缓存值或调用 collector_fn"""
        now = time.time()
        
        with self._lock:
            # 读取路径：检查缓存
            if key in self._cache:
                if now - self._times.get(key, 0) < self.ttl:
                    self._touch(key)
                    return self._cache[key]
                # 已过期，清理
                self._cache.pop(key, None)
                self._times.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
            
            if collector_fn is None:
                return None
        
        # 在锁外执行 collector_fn（避免死锁）
        result = collector_fn(*args, **kwargs)
        
        with self._lock:
            self._evict_lru()
            self._cache[key] = result
            self._times[key] = now
            self._access_order.append(key)
        
        return result

    def set(self, key, value):
        """直接设置缓存"""
        now = time.time()
        with self._lock:
            self._prune_expired(now)
            self._evict_lru()
            self._cache[key] = value
            self._times[key] = now
            self._touch(key)

    def invalidate(self, key=None):
        """使缓存失效"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
                self._times.pop(key, None)
                if key in self._access_order:
                    self._access_order.remove(key)
            else:
                self._cache.clear()
                self._times.clear()
                self._access_order.clear()

    def stats(self):
        """返回缓存统计（调试用）"""
        now = time.time()
        with self._lock:
            expired = sum(1 for t in self._times.values() if now - t >= self.ttl)
            return {"size": len(self._cache), "max_size": self.max_size, "ttl": self.ttl, "expired": expired}
