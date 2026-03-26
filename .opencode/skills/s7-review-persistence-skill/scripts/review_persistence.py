"""
评估单状态持久化管理器
提供状态保存、加载、查询未完成列表等功能
支持分布式锁防止并发修改
"""

import os
import json
import time
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from .redis_client import redis_client
from .redis_lock import distributed_lock

logger = logging.getLogger(__name__)


class ReviewStateManager:
    """评估单状态管理器"""
    
    # Redis Key 前缀
    KEY_PREFIX_STATE = "review_state"
    KEY_PREFIX_USER_PENDING = "user_pending_tasks"
    KEY_PREFIX_GLOBAL_PENDING = "global_pending_tasks"
    
    # 过期时间 (秒)
    STATE_TTL = int(os.getenv('STATE_TTL_SECONDS', '3600'))  # 1 小时
    PENDING_LIST_TTL = int(os.getenv('PENDING_LIST_TTL_SECONDS', '86400'))  # 24 小时
    
    def __init__(self, task_id: Optional[str] = None, org_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        初始化状态管理器
        
        Args:
            task_id: 评估单 ID
            org_id: 组织 ID
            user_id: 用户 ID
        """
        self.task_id = task_id
        self.org_id = org_id
        self.user_id = user_id
        self.redis = redis_client.client
    
    def _get_state_key(self, task_id: Optional[str] = None) -> str:
        """获取状态键"""
        tid = task_id or self.task_id
        if not tid:
            raise ValueError("task_id 不能为空")
        return f"{self.KEY_PREFIX_STATE}:{tid}"
    
    def _get_user_pending_key(self, user_id: Optional[str] = None) -> str:
        """获取用户未完成列表键"""
        uid = user_id or self.user_id
        if not uid:
            raise ValueError("user_id 不能为空")
        return f"{self.KEY_PREFIX_USER_PENDING}:{uid}"
    
    def _get_global_pending_key(self) -> str:
        """获取全局未完成列表键"""
        return self.KEY_PREFIX_GLOBAL_PENDING
    
    def save_state(self, state: str, context: Dict[str, Any], 
                   modification_history: Optional[List] = None,
                   use_lock: bool = True) -> bool:
        """
        保存评估单状态到 Redis
        
        Args:
            state: 当前状态 (如 REVIEW_IN_PROGRESS, CONFIRMATION_PENDING)
            context: 上下文信息 (包含 task_name, current_round 等)
            modification_history: 修改历史记录
            use_lock: 是否使用分布式锁 (默认 True)
        
        Returns:
            bool: 保存是否成功
        """
        if not self.redis:
            logger.warning("Redis 未连接，跳过状态保存")
            return False
        
        if not self.task_id:
            logger.error("task_id 未设置，无法保存状态")
            return False
        
        try:
            # 使用分布式锁防止并发修改
            if use_lock:
                lock_key = f"state_save:{self.task_id}"
                with distributed_lock(lock_key, timeout_ms=5000) as acquired:
                    if not acquired:
                        logger.warning(f"无法获取锁，跳过保存：{self.task_id}")
                        return False
                    return self._do_save_state(state, context, modification_history)
            else:
                return self._do_save_state(state, context, modification_history)
                
        except Exception as e:
            logger.error(f"保存状态失败：{e}")
            return False
    
    def _do_save_state(self, state: str, context: Dict[str, Any], 
                       modification_history: Optional[List] = None) -> bool:
        """
        执行状态保存 (内部方法，假定已持有锁)
        
        Args:
            state: 当前状态
            context: 上下文信息
            modification_history: 修改历史记录
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 构建状态数据
            state_data = {
                'state': state,
                'task_name': context.get('task_name', '未知项目'),
                'org_id': self.org_id or '',
                'user_id': self.user_id or '',
                'context': context,
                'modification_history': modification_history or [],
                'last_modified': datetime.now().isoformat(),
                'modification_count': len(modification_history or [])
            }
            
            # 保存到 Redis
            key = self._get_state_key()
            success = redis_client.setex(key, self.STATE_TTL, state_data)
            
            if success:
                # 更新用户未完成列表
                self._add_to_user_pending()
                # 更新全局未完成列表
                self._add_to_global_pending()
                logger.info(f"状态已保存：{self.task_id} ({context.get('task_name')})")
            
            return success
            
        except Exception as e:
            logger.error(f"保存状态失败：{e}")
            return False
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        从 Redis 加载评估单状态
        
        Returns:
            Dict: 状态数据，如果不存在则返回 None
        """
        if not self.redis:
            logger.warning("Redis 未连接，无法加载状态")
            return None
        
        if not self.task_id:
            logger.error("task_id 未设置，无法加载状态")
            return None
        
        try:
            key = self._get_state_key()
            state_data = redis_client.get(key)
            
            if state_data:
                logger.info(f"状态已加载：{self.task_id} ({state_data.get('task_name')})")
                return state_data
            else:
                logger.debug(f"未找到缓存状态：{self.task_id}")
                return None
                
        except Exception as e:
            logger.error(f"加载状态失败：{e}")
            return None
    
    def delete_state(self) -> bool:
        """
        删除评估单状态 (任务完成时调用)
        
        Returns:
            bool: 删除是否成功
        """
        if not self.redis:
            return False
        
        if not self.task_id:
            return False
        
        try:
            key = self._get_state_key()
            redis_client.delete(key)
            
            # 从用户未完成列表移除
            self._remove_from_user_pending()
            # 从全局未完成列表移除
            self._remove_from_global_pending()
            
            logger.info(f"状态已删除：{self.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除状态失败：{e}")
            return False
    
    def complete_task(self) -> bool:
        """
        标记任务完成 (删除状态)
        
        Returns:
            bool: 是否成功
        """
        return self.delete_state()
    
    def _add_to_user_pending(self):
        """添加到用户未完成列表"""
        if not self.user_id or not self.task_id:
            return
        
        try:
            key = self._get_user_pending_key()
            redis_client.sadd(key, self.task_id)
            redis_client.expire(key, self.PENDING_LIST_TTL)
        except Exception as e:
            logger.error(f"添加到用户未完成列表失败：{e}")
    
    def _remove_from_user_pending(self):
        """从用户未完成列表移除"""
        if not self.user_id or not self.task_id:
            return
        
        try:
            key = self._get_user_pending_key()
            redis_client.srem(key, self.task_id)
        except Exception as e:
            logger.error(f"从用户未完成列表移除失败：{e}")
    
    def _add_to_global_pending(self):
        """添加到全局未完成列表"""
        if not self.task_id:
            return
        
        try:
            key = self._get_global_pending_key()
            redis_client.zadd(key, {self.task_id: time.time()})
            redis_client.expire(key, self.PENDING_LIST_TTL)
        except Exception as e:
            logger.error(f"添加到全局未完成列表失败：{e}")
    
    def _remove_from_global_pending(self):
        """从全局未完成列表移除"""
        if not self.task_id:
            return
        
        try:
            key = self._get_global_pending_key()
            redis_client.zrem(key, self.task_id)
        except Exception as e:
            logger.error(f"从全局未完成列表移除失败：{e}")
    
    def get_user_pending_tasks(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取用户的未完成评估单列表
        
        Args:
            user_id: 用户 ID，不传则使用实例的 user_id
        
        Returns:
            List[Dict]: 未完成任务列表
        """
        if not self.redis:
            return []
        
        uid = user_id or self.user_id
        if not uid:
            return []
        
        try:
            key = self._get_user_pending_key(uid)
            task_ids = redis_client.smembers(key)
            
            if not task_ids:
                return []
            
            # 加载每个任务的详细信息
            pending_tasks = []
            for task_id in task_ids:
                state_data = redis_client.get(f"{self.KEY_PREFIX_STATE}:{task_id}")
                if state_data:
                    pending_tasks.append(state_data)
                else:
                    # 状态已过期，从未完成列表移除
                    redis_client.srem(key, task_id)
            
            # 按最后修改时间排序
            pending_tasks.sort(
                key=lambda x: x.get('last_modified', ''),
                reverse=True
            )
            
            return pending_tasks
            
        except Exception as e:
            logger.error(f"获取用户未完成任务失败：{e}")
            return []
    
    def get_global_pending_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取全局未完成评估单列表 (按时间倒序)
        
        Args:
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 未完成任务列表
        """
        if not self.redis:
            return []
        
        try:
            key = self._get_global_pending_key()
            # 获取最新的 limit 个任务
            task_ids_with_scores = redis_client.zrevrange(key, 0, limit - 1, withscores=True)
            
            if not task_ids_with_scores:
                return []
            
            # 加载每个任务的详细信息
            pending_tasks = []
            for task_id, timestamp in task_ids_with_scores:
                state_data = redis_client.get(f"{self.KEY_PREFIX_STATE}:{task_id}")
                if state_data:
                    pending_tasks.append(state_data)
                else:
                    # 状态已过期，从全局列表移除
                    redis_client.zrem(key, task_id)
            
            return pending_tasks
            
        except Exception as e:
            logger.error(f"获取全局未完成任务失败：{e}")
            return []
    
    def get_task_by_name(self, task_name: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        根据任务名称查找未完成的评估单
        
        Args:
            task_name: 任务名称
            user_id: 用户 ID 限制范围
        
        Returns:
            Dict: 任务状态数据，未找到返回 None
        """
        # 获取用户未完成任务
        if user_id:
            pending_tasks = self.get_user_pending_tasks(user_id)
        else:
            pending_tasks = self.get_global_pending_tasks()
        
        # 模糊匹配任务名称
        for task in pending_tasks:
            if task_name.lower() in task.get('task_name', '').lower():
                return task
        
        return None
    
    def format_pending_message(self, pending_tasks: List[Dict[str, Any]]) -> str:
        """
        格式化未完成列表消息
        
        Args:
            pending_tasks: 未完成任务列表
        
        Returns:
            str: 格式化的 Markdown 消息
        """
        if not pending_tasks:
            return "✅ 所有评估单已完成，没有待办事项"
        
        count = len(pending_tasks)
        lines = [f"检测到您有 **{count} 个** 未完成的评估单：\n"]
        lines.append("| 序号 | 项目名称 | 当前状态 | 最后修改 | 已修改轮数 |")
        lines.append("|-----|---------|---------|---------|-----------|")
        
        for idx, task in enumerate(pending_tasks, 1):
            task_name = task.get('task_name', '未知项目')
            state = task.get('state', 'UNKNOWN')
            last_modified = task.get('last_modified', '')
            mod_count = task.get('modification_count', 0)
            
            # 格式化时间
            if last_modified:
                try:
                    dt = datetime.fromisoformat(last_modified)
                    now = datetime.now()
                    diff = now - dt
                    
                    if diff.days > 0:
                        time_str = f"{diff.days}天前"
                    elif diff.seconds > 3600:
                        time_str = f"{diff.seconds // 3600}小时前"
                    else:
                        time_str = f"{diff.seconds // 60}分钟前"
                except:
                    time_str = last_modified[:16]
            else:
                time_str = "未知"
            
            # 格式化状态
            state_map = {
                'REVIEW_IN_PROGRESS': '审核中',
                'CONFIRMATION_PENDING': '等待确认',
                'MODIFICATION_IN_PROGRESS': '修改中'
            }
            state_cn = state_map.get(state, state)
            
            lines.append(f"| {idx} | {task_name} | {state_cn} | {time_str} | {mod_count}轮 |")
        
        lines.append("\n请回复：")
        lines.append("- **数字** (如 \"1\") 选择继续")
        lines.append("- **项目名称** (如 \"XX 项目\") 直接继续")
        lines.append("- **忽略** 开始新任务")
        
        return "\n".join(lines)
    
    def scan_all_states(self) -> List[str]:
        """
        扫描所有状态键 (用于 Agent 启动时恢复)
        
        Returns:
            List[str]: 所有状态键列表
        """
        if not self.redis:
            return []
        
        try:
            pattern = f"{self.KEY_PREFIX_STATE}:*"
            return redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"扫描状态键失败：{e}")
            return []
