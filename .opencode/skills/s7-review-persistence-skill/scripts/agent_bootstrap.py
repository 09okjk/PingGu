"""
Agent 启动时自动状态恢复
在 Agent 启动时自动恢复所有未完成的评估单状态
"""

import logging
from typing import List, Dict, Any

from .review_persistence import ReviewStateManager
from .redis_client import redis_client

logger = logging.getLogger(__name__)


class AgentBootstrap:
    """Agent 启动引导器"""
    
    def __init__(self):
        """初始化启动引导器"""
        self.redis_client = redis_client
    
    def recover_all_states(self) -> List[Dict[str, Any]]:
        """
        恢复所有未完成状态
        
        Returns:
            恢复的状态列表
        """
        recovered_states = []
        
        try:
            # 获取所有未完成任务的 task_id 列表
            pending_list = self.redis_client.get('pending_tasks')
            
            if not pending_list:
                logger.info("没有未完成的任务需要恢复")
                return recovered_states
            
            logger.info(f"发现 {len(pending_list)} 个未完成任务，开始恢复...")
            
            for task_id in pending_list:
                try:
                    state_data = self._recover_single_state(task_id)
                    if state_data:
                        recovered_states.append(state_data)
                except Exception as e:
                    logger.error(f"恢复任务状态失败 {task_id}: {e}")
            
            logger.info(f"完成 {len(recovered_states)} 个任务状态恢复")
            return recovered_states
        
        except Exception as e:
            logger.error(f"批量恢复状态失败：{e}")
            return recovered_states
    
    def recover_single_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        恢复单个任务状态
        
        Args:
            task_id: 评估单 ID
        
        Returns:
            恢复的状态数据
        """
        return self._recover_single_state(task_id)
    
    def _recover_single_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        恢复单个任务状态的内部实现
        
        Args:
            task_id: 评估单 ID
        
        Returns:
            恢复的状态数据
        """
        try:
            # 从 Redis 加载状态
            manager = ReviewStateManager(task_id=task_id)
            state_data = manager.load_state()
            
            if not state_data:
                logger.warning(f"未找到任务状态：{task_id}")
                return None
            
            # 验证状态是否过期
            if self._is_state_expired(state_data):
                logger.warning(f"任务状态已过期，跳过恢复：{task_id}")
                self._cleanup_expired_state(task_id)
                return None
            
            # 将状态恢复到内存/活动状态列表
            self._restore_to_active_list(task_id, state_data)
            
            logger.info(f"任务状态已恢复：{task_id} - {state_data.get('state')}")
            return state_data
        
        except Exception as e:
            logger.error(f"恢复任务状态失败 {task_id}: {e}")
            return None
    
    def _is_state_expired(self, state_data: Dict[str, Any]) -> bool:
        """
        检查状态是否过期
        
        Args:
            state_data: 状态数据
        
        Returns:
            是否过期
        """
        # TODO: 实现状态过期检查逻辑
        # 可以根据 created_at 或 updated_at 字段判断
        return False
    
    def _cleanup_expired_state(self, task_id: str):
        """
        清理过期状态
        
        Args:
            task_id: 评估单 ID
        """
        try:
            manager = ReviewStateManager(task_id=task_id)
            manager.delete_state()
            logger.info(f"已清理过期状态：{task_id}")
        except Exception as e:
            logger.error(f"清理过期状态失败 {task_id}: {e}")
    
    def _restore_to_active_list(self, task_id: str, state_data: Dict[str, Any]):
        """
        将状态恢复到活动列表
        
        实际使用时，这里应该将状态恢复到 Agent 的内存或活动状态管理器中
        
        Args:
            task_id: 评估单 ID
            state_data: 状态数据
        """
        # TODO: 实际实现时需要根据具体的 Agent 架构实现
        # 这里仅记录日志
        logger.debug(f"状态已恢复到活动列表：{task_id}")
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """
        获取恢复摘要信息
        
        Returns:
            恢复摘要字典
        """
        try:
            pending_list = self.redis_client.get('pending_tasks')
            pending_count = len(pending_list) if pending_list else 0
            
            return {
                'pending_tasks_count': pending_count,
                'pending_task_ids': pending_list or [],
                'status': 'ready' if pending_count == 0 else 'has_pending'
            }
        except Exception as e:
            logger.error(f"获取恢复摘要失败：{e}")
            return {
                'pending_tasks_count': 0,
                'pending_task_ids': [],
                'status': 'error',
                'error': str(e)
            }
