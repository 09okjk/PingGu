"""
Redis 分布式锁封装
提供简单的锁获取/释放接口
"""

import logging
from typing import Optional

from .redis_client import redis_client

logger = logging.getLogger(__name__)


class RedisLock:
    """Redis 分布式锁"""
    
    def __init__(self, resource: str):
        """
        初始化锁
        
        Args:
            resource: 资源名称（锁的 key 会加上 "lock:" 前缀）
        """
        self.resource = resource
        self.lock_id: Optional[str] = None
    
    def acquire(self, timeout: int = 10, retry_interval: float = 0.1) -> bool:
        """
        获取锁
        
        Args:
            timeout: 锁超时时间（秒）
            retry_interval: 重试间隔（秒）
        
        Returns:
            是否成功获取
        """
        self.lock_id = redis_client.acquire_lock(
            self.resource,
            timeout=timeout,
            retry_interval=retry_interval
        )
        return self.lock_id is not None
    
    def release(self) -> bool:
        """
        释放锁
        
        Returns:
            是否成功释放
        """
        if not self.lock_id:
            logger.warning("尝试释放未获取的锁")
            return False
        
        success = redis_client.release_lock(self.resource, self.lock_id)
        if success:
            self.lock_id = None
        return success
    
    def extend(self, additional_time: int) -> bool:
        """
        延长锁超时时间
        
        Args:
            additional_time: 额外延长时间（秒）
        
        Returns:
            是否成功延长
        """
        if not self.lock_id:
            logger.warning("尝试延长未获取的锁")
            return False
        
        return redis_client.extend_lock(self.resource, self.lock_id, additional_time)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False


def distributed_lock(resource: str, timeout_ms: int = 5000):
    """
    分布式锁上下文管理器（兼容旧接口）
    
    Args:
        resource: 资源名称
        timeout_ms: 超时时间（毫秒）
    
    Returns:
        上下文管理器，返回 (acquired: bool)
    """
    lock = RedisLock(resource)
    timeout_sec = timeout_ms / 1000.0
    acquired = lock.acquire(timeout=int(timeout_sec))
    
    class LockContext:
        def __init__(self, lock_instance, acquired):
            self.lock = lock_instance
            self.acquired = acquired
        
        def __enter__(self):
            return self.acquired
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.acquired:
                self.lock.release()
            return False
    
    return LockContext(lock, acquired)
