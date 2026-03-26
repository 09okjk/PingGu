"""
Redis 客户端封装
提供统一的 Redis 连接和操作方法
"""

import os
import json
import logging
import uuid
from typing import Optional, Any, Dict, List
from datetime import datetime

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端单例封装"""
    
    _instance: Optional['RedisClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._client: Optional[redis.Redis] = None
        self._connect()
        self._initialized = True
    
    def _connect(self):
        """建立 Redis 连接"""
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        db = int(os.getenv('REDIS_DB', '0'))
        password = os.getenv('REDIS_PASSWORD') or None
        
        try:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._client.ping()
            logger.info(f"Redis 连接成功：{host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Redis 连接失败：{e}")
            self._client = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端实例"""
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False
    
    def setex(self, key: str, ttl: int, value: Any) -> bool:
        """设置带过期时间的键"""
        if not self._client:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis setex 失败：{e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        if not self._client:
            return None
        try:
            value = self._client.get(key)
            if value is None:
                return None
            # 尝试解析 JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            logger.error(f"Redis get 失败：{e}")
            return None
    
    def delete(self, key: str) -> bool:
        """删除键"""
        if not self._client:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete 失败：{e}")
            return False
    
    def sadd(self, key: str, *values: str) -> int:
        """向集合添加元素"""
        if not self._client:
            return 0
        try:
            return self._client.sadd(key, *values)
        except Exception as e:
            logger.error(f"Redis sadd 失败：{e}")
            return 0
    
    def srem(self, key: str, *values: str) -> int:
        """从集合删除元素"""
        if not self._client:
            return 0
        try:
            return self._client.srem(key, *values)
        except Exception as e:
            logger.error(f"Redis srem 失败：{e}")
            return 0
    
    def smembers(self, key: str) -> set:
        """获取集合所有成员"""
        if not self._client:
            return set()
        try:
            return self._client.smembers(key)
        except Exception as e:
            logger.error(f"Redis smembers 失败：{e}")
            return set()
    
    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """向有序集合添加元素"""
        if not self._client:
            return 0
        try:
            return self._client.zadd(key, mapping)
        except Exception as e:
            logger.error(f"Redis zadd 失败：{e}")
            return 0
    
    def zrem(self, key: str, *values: str) -> int:
        """从有序集合删除元素"""
        if not self._client:
            return 0
        try:
            return self._client.zrem(key, *values)
        except Exception as e:
            logger.error(f"Redis zrem 失败：{e}")
            return 0
    
    def zrange(self, key: str, start: int = 0, end: int = -1, withscores: bool = False) -> List:
        """获取有序集合范围"""
        if not self._client:
            return []
        try:
            return self._client.zrange(key, start, end, withscores=withscores)
        except Exception as e:
            logger.error(f"Redis zrange 失败：{e}")
            return []
    
    def zrevrange(self, key: str, start: int = 0, end: int = -1, withscores: bool = False) -> List:
        """逆序获取有序集合范围"""
        if not self._client:
            return []
        try:
            return self._client.zrevrange(key, start, end, withscores=withscores)
        except Exception as e:
            logger.error(f"Redis zrevrange 失败：{e}")
            return []
    
    def keys(self, pattern: str) -> List[str]:
        """匹配键"""
        if not self._client:
            return []
        try:
            return self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys 失败：{e}")
            return []
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置键过期时间"""
        if not self._client:
            return False
        try:
            return self._client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire 失败：{e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            logger.info("Redis 连接已关闭")
    
    # ==================== 分布式锁 ====================
    
    def acquire_lock(self, resource: str, timeout: int = 10, retry_interval: float = 0.1) -> Optional[str]:
        """
        获取分布式锁
        
        Args:
            resource: 资源名称（锁的 key）
            timeout: 锁超时时间（秒）
            retry_interval: 重试间隔（秒）
        
        Returns:
            锁标识符（成功时），None（失败时）
        """
        if not self._client:
            return None
        
        lock_key = f"lock:{resource}"
        lock_id = str(uuid.uuid4())
        end_time = datetime.now().timestamp() + timeout
        
        try:
            while datetime.now().timestamp() < end_time:
                # 尝试设置锁（NX = 仅当不存在时设置）
                if self._client.set(lock_key, lock_id, nx=True, ex=timeout):
                    logger.debug(f"成功获取锁：{resource} (lock_id={lock_id})")
                    return lock_id
                
                # 等待后重试
                import time
                time.sleep(retry_interval)
            
            logger.warning(f"获取锁超时：{resource}")
            return None
        except Exception as e:
            logger.error(f"获取锁失败：{e}")
            return None
    
    def release_lock(self, resource: str, lock_id: str) -> bool:
        """
        释放分布式锁
        
        Args:
            resource: 资源名称
            lock_id: 锁标识符（必须是获取锁时返回的 ID）
        
        Returns:
            是否成功释放
        """
        if not self._client:
            return False
        
        lock_key = f"lock:{resource}"
        
        try:
            # 使用 Lua 脚本确保原子性：只有锁 ID 匹配时才删除
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = self._client.eval(lua_script, 1, lock_key, lock_id)
            
            if result == 1:
                logger.debug(f"成功释放锁：{resource} (lock_id={lock_id})")
                return True
            else:
                logger.warning(f"释放锁失败：{resource} (锁不存在或 ID 不匹配)")
                return False
        except Exception as e:
            logger.error(f"释放锁失败：{e}")
            return False
    
    def extend_lock(self, resource: str, lock_id: str, additional_time: int) -> bool:
        """
        延长锁的超时时间
        
        Args:
            resource: 资源名称
            lock_id: 锁标识符
            additional_time: 额外延长时间（秒）
        
        Returns:
            是否成功延长
        """
        if not self._client:
            return False
        
        lock_key = f"lock:{resource}"
        
        try:
            # 使用 Lua 脚本确保原子性
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = self._client.eval(lua_script, 1, lock_key, lock_id, additional_time)
            return result == 1
        except Exception as e:
            logger.error(f"延长锁失败：{e}")
            return False


# 全局单例
redis_client = RedisClient()
