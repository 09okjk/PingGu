"""
用户通知处理器
在用户首次对话时主动通知未完成的评估任务
"""

import logging
from typing import List, Dict, Any, Optional, Callable

from .review_persistence import ReviewStateManager
from .redis_client import redis_client

logger = logging.getLogger(__name__)


class NotificationHandler:
    """通知处理器"""
    
    def __init__(self, notification_callback: Optional[Callable] = None):
        """
        初始化通知处理器
        
        Args:
            notification_callback: 通知回调函数，签名 (user_id: str, message: str, tasks: list)
        """
        self.redis_client = redis_client
        self.notification_callback = notification_callback
    
    def notify_user(self, user_id: str) -> Dict[str, Any]:
        """
        通知指定用户有关未完成的任务
        
        Args:
            user_id: 用户 ID
        
        Returns:
            通知结果字典
        """
        try:
            # 获取用户未完成任务
            pending_tasks = self._get_user_pending_tasks(user_id)
            
            if not pending_tasks:
                logger.info(f"用户 {user_id} 没有未完成任务")
                return {
                    'success': True,
                    'user_id': user_id,
                    'notified': False,
                    'pending_count': 0,
                    'message': '没有未完成任务'
                }
            
            # 生成通知消息
            message = self._generate_notification_message(user_id, pending_tasks)
            
            # 发送通知
            if self.notification_callback:
                self.notification_callback(user_id, message, pending_tasks)
                logger.info(f"已通知用户 {user_id} 关于 {len(pending_tasks)} 个未完成任务")
            else:
                logger.info(f"通知消息（未设置回调）：{message}")
            
            return {
                'success': True,
                'user_id': user_id,
                'notified': True,
                'pending_count': len(pending_tasks),
                'tasks': pending_tasks,
                'message': message
            }
        
        except Exception as e:
            logger.error(f"通知用户失败 {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e)
            }
    
    def notify_all_users(self) -> List[Dict[str, Any]]:
        """
        通知所有有未完成任务的用户
        
        Returns:
            通知结果列表
        """
        results = []
        
        try:
            # 获取所有未完成任务
            pending_list = self.redis_client.get('pending_tasks')
            
            if not pending_list:
                logger.info("没有未完成任务需要通知")
                return results
            
            # 按用户分组
            user_tasks = {}
            for task_id in pending_list:
                try:
                    manager = ReviewStateManager(task_id=task_id)
                    state_data = manager.load_state()
                    
                    if state_data:
                        user_id = state_data.get('user_id', '')
                        if user_id:
                            if user_id not in user_tasks:
                                user_tasks[user_id] = []
                            user_tasks[user_id].append({
                                'task_id': task_id,
                                'state': state_data.get('state', 'UNKNOWN'),
                                'updated_at': state_data.get('updated_at', '')
                            })
                except Exception as e:
                    logger.error(f"处理任务 {task_id} 失败：{e}")
            
            # 通知每个用户
            for user_id, tasks in user_tasks.items():
                result = self.notify_user(user_id)
                results.append(result)
            
            logger.info(f"已通知 {len(results)} 个用户")
            return results
        
        except Exception as e:
            logger.error(f"批量通知失败：{e}")
            return results
    
    def _get_user_pending_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户未完成任务列表
        
        Args:
            user_id: 用户 ID
        
        Returns:
            任务列表
        """
        pending_tasks = []
        
        try:
            # 从 Redis 获取待处理列表
            pending_list = self.redis_client.get('pending_tasks')
            
            if not pending_list:
                return pending_tasks
            
            for task_id in pending_list:
                try:
                    manager = ReviewStateManager(task_id=task_id)
                    state_data = manager.load_state()
                    
                    if state_data and state_data.get('user_id') == user_id:
                        pending_tasks.append({
                            'task_id': task_id,
                            'task_name': state_data.get('task_name', '未命名任务'),
                            'state': state_data.get('state', 'UNKNOWN'),
                            'updated_at': state_data.get('updated_at', ''),
                            'context': state_data.get('context', {})
                        })
                except Exception as e:
                    logger.error(f"获取任务信息失败 {task_id}: {e}")
            
            return pending_tasks
        
        except Exception as e:
            logger.error(f"获取用户任务列表失败 {user_id}: {e}")
            return pending_tasks
    
    def _generate_notification_message(self, user_id: str, tasks: List[Dict[str, Any]]) -> str:
        """
        生成通知消息
        
        Args:
            user_id: 用户 ID
            tasks: 任务列表
        
        Returns:
            通知消息文本
        """
        if not tasks:
            return "您没有未完成的评估任务。"
        
        message = f"您有 {len(tasks)} 个未完成的评估任务：\n\n"
        
        for i, task in enumerate(tasks, 1):
            task_name = task.get('task_name', '未命名任务')
            state = task.get('state', 'UNKNOWN')
            updated_at = task.get('updated_at', '未知时间')
            
            message += f"{i}. **{task_name}**\n"
            message += f"   - 状态：{state}\n"
            message += f"   - 最后更新：{updated_at}\n\n"
        
        message += "请输入任务 ID 或名称继续处理。"
        return message
    
    def set_notification_callback(self, callback: Callable):
        """
        设置通知回调函数
        
        Args:
            callback: 回调函数，签名 (user_id: str, message: str, tasks: list)
        """
        self.notification_callback = callback
        logger.info("通知回调已设置")
