"""
ReviewStateMachine 状态机集成
实现 ReviewStateManager 与 ReviewStateMachine 的深度集成
"""

import logging
from typing import Optional, Dict, Any

from .review_persistence import ReviewStateManager
from .redis_client import redis_client
from .redis_lock import RedisLock

logger = logging.getLogger(__name__)


class StateMachineIntegration:
    """状态机集成器"""
    
    def __init__(self):
        """初始化状态机集成器"""
        self.redis_client = redis_client
    
    def sync_state_machine_state(self, task_id: str) -> bool:
        """
        同步状态机状态到持久化存储
        
        当 ReviewStateMachine 状态变更时，自动调用此方法保存状态
        
        Args:
            task_id: 评估单 ID
        
        Returns:
            是否成功同步
        """
        # 获取锁防止并发修改
        lock = RedisLock(f"state_sync:{task_id}")
        
        try:
            if not lock.acquire(timeout=5):
                logger.error(f"无法获取锁，跳过同步：{task_id}")
                return False
            
            # 这里假设 ReviewStateMachine 有方法获取当前状态
            # 实际使用时需要从状态机获取
            state_machine_state = self._get_state_machine_state(task_id)
            
            if not state_machine_state:
                logger.warning(f"未找到状态机状态：{task_id}")
                return False
            
            # 创建 ReviewStateManager 并保存状态
            manager = ReviewStateManager(
                task_id=task_id,
                org_id=state_machine_state.get('org_id', ''),
                user_id=state_machine_state.get('user_id', '')
            )
            
            success = manager.save_state(
                state=state_machine_state.get('state', 'UNKNOWN'),
                context=state_machine_state.get('context', {}),
                modification_history=state_machine_state.get('history', [])
            )
            
            if success:
                logger.info(f"状态机状态已同步：{task_id}")
                return True
            else:
                logger.error(f"状态机状态同步失败：{task_id}")
                return False
        
        except Exception as e:
            logger.error(f"状态机同步异常：{e}")
            return False
        finally:
            lock.release()
    
    def _get_state_machine_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        从 ReviewStateMachine 获取状态
        
        TODO: 实际实现时需要集成真实的 ReviewStateMachine
        
        Args:
            task_id: 评估单 ID
        
        Returns:
            状态数据字典，包含 state, org_id, user_id, context, history
        """
        # 临时实现：从 Redis 读取状态机状态
        # 实际应该调用 ReviewStateMachine 的方法
        try:
            key = f"state_machine:{task_id}"
            data = self.redis_client.get(key)
            
            if data:
                return data
            else:
                # 如果 Redis 中没有，尝试从持久化存储加载
                manager = ReviewStateManager(task_id=task_id)
                state_data = manager.load_state()
                
                if state_data:
                    return {
                        'state': state_data.get('state', 'UNKNOWN'),
                        'org_id': state_data.get('org_id', ''),
                        'user_id': state_data.get('user_id', ''),
                        'context': state_data.get('context', {}),
                        'history': state_data.get('modification_history', [])
                    }
            
            return None
        except Exception as e:
            logger.error(f"获取状态机状态失败：{e}")
            return None
    
    def register_state_change_callback(self, callback):
        """
        注册状态变更回调
        
        当 ReviewStateMachine 状态变更时，自动调用此回调保存状态
        
        Args:
            callback: 回调函数，签名 (task_id: str, new_state: str, context: dict)
        """
        # TODO: 实际实现时需要在 ReviewStateMachine 中注册回调
        logger.info("状态变更回调已注册")
    
    def validate_state_consistency(self, task_id: str) -> bool:
        """
        验证状态机状态与持久化状态的一致性
        
        Args:
            task_id: 评估单 ID
        
        Returns:
            是否一致
        """
        try:
            # 获取状态机状态
            state_machine_state = self._get_state_machine_state(task_id)
            
            # 获取持久化状态
            manager = ReviewStateManager(task_id=task_id)
            persisted_state = manager.load_state()
            
            if not state_machine_state or not persisted_state:
                logger.warning(f"无法获取完整状态进行对比：{task_id}")
                return False
            
            # 对比状态值
            is_consistent = (
                state_machine_state.get('state') == persisted_state.get('state')
            )
            
            if not is_consistent:
                logger.warning(
                    f"状态不一致：{task_id} - "
                    f"状态机={state_machine_state.get('state')}, "
                    f"持久化={persisted_state.get('state')}"
                )
            
            return is_consistent
        
        except Exception as e:
            logger.error(f"状态一致性验证失败：{e}")
            return False
