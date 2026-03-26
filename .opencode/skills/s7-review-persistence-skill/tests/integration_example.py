"""
Review Persistence Skill - 集成示例
展示如何将状态持久化与 ReviewStateMachine 集成使用
"""

import json
import logging
from typing import Dict, Any, Optional

from review_state_machine import ReviewStateMachine
from review_persistence import ReviewStateManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReviewPersistenceIntegration:
    """评估单持久化集成类"""
    
    def __init__(self, task_id: str, org_id: str, user_id: str):
        """
        初始化集成
        
        Args:
            task_id: 评估单 ID
            org_id: 组织 ID
            user_id: 用户 ID
        """
        self.task_id = task_id
        self.org_id = org_id
        self.user_id = user_id
        
        # 初始化状态机
        self.state_machine = ReviewStateMachine(task_id=task_id)
        
        # 初始化持久化管理器
        self.persistence = ReviewStateManager(
            task_id=task_id,
            org_id=org_id,
            user_id=user_id
        )
    
    def load_or_initialize(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        加载已有状态或初始化新状态
        
        Args:
            initial_context: 初始上下文（仅在创建新任务时使用）
        
        Returns:
            Dict: 当前状态数据
        """
        # 尝试从 Redis 加载
        state_data = self.persistence.load_state()
        
        if state_data:
            logger.info(f"已加载缓存状态：{self.task_id}")
            # 恢复状态机
            self.state_machine.set_state(state_data['state'])
            return state_data
        
        # 初始化新状态
        if not initial_context:
            raise ValueError("新任务需要提供 initial_context")
        
        logger.info(f"初始化新任务：{self.task_id}")
        context = {
            'task_name': initial_context.get('task_name', '未知项目'),
            'current_round': 0,
            **initial_context
        }
        
        # 保存初始状态
        self.persistence.save_state(
            state='REVIEW_IN_PROGRESS',
            context=context,
            modification_history=[]
        )
        
        return {
            'state': 'REVIEW_IN_PROGRESS',
            'context': context,
            'modification_history': []
        }
    
    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        处理用户消息并更新状态
        
        Args:
            message: 用户消息
        
        Returns:
            Dict: 处理后的状态数据
        """
        # 加载当前状态
        state_data = self.persistence.load_state()
        if not state_data:
            raise ValueError(f"未找到任务状态：{self.task_id}")
        
        # 恢复状态机
        self.state_machine.set_state(state_data['state'])
        
        # 使用状态机处理消息
        result = self.state_machine.process_message(message)
        
        # 更新持久化状态
        context = state_data.get('context', {})
        context['current_round'] = state_data.get('modification_count', 0) + 1
        
        modification_history = state_data.get('modification_history', [])
        if result.get('intent') == 'confirm':
            modification_history.append({
                'round': context['current_round'],
                'action': 'confirm',
                'message': message,
                'timestamp': result.get('timestamp')
            })
        elif result.get('intent') == 'modify':
            modification_history.append({
                'round': context['current_round'],
                'action': 'modify',
                'message': message,
                'changes': result.get('changes', []),
                'timestamp': result.get('timestamp')
            })
        
        # 保存新状态
        self.persistence.save_state(
            state=result.get('next_state', state_data['state']),
            context=context,
            modification_history=modification_history
        )
        
        return {
            'state': result.get('next_state'),
            'context': context,
            'modification_history': modification_history,
            'intent_result': result
        }
    
    def complete_task(self) -> bool:
        """
        完成任务（删除状态）
        
        Returns:
            bool: 是否成功
        """
        return self.persistence.complete_task()
    
    def get_pending_tasks_for_user(self) -> list:
        """
        获取当前用户的未完成任务列表
        
        Returns:
            list: 未完成任务列表
        """
        return self.persistence.get_user_pending_tasks(self.user_id)
    
    def format_pending_message(self) -> str:
        """
        格式化未完成列表消息
        
        Returns:
            str: Markdown 格式消息
        """
        pending_tasks = self.get_pending_tasks_for_user()
        return self.persistence.format_pending_message(pending_tasks)


# ==================== 使用示例 ====================

def example_usage():
    """使用示例"""
    
    # 示例 1: 初始化新任务
    print("=== 示例 1: 初始化新任务 ===")
    integration = ReviewPersistenceIntegration(
        task_id="task_20260326_001",
        org_id="org_123",
        user_id="user_456"
    )
    
    state_data = integration.load_or_initialize({
        'task_name': 'XX 系统开发项目',
        'client_type': '企业客户',
        'expected_delivery': '2026-04-30'
    })
    print(f"当前状态：{state_data['state']}")
    print(f"项目名称：{state_data['context']['task_name']}")
    
    # 示例 2: 处理用户消息
    print("\n=== 示例 2: 处理用户消息 ===")
    result = integration.process_user_message("开发阶段增加 3 人天")
    print(f"意图：{result['intent_result'].get('intent')}")
    print(f"下一状态：{result['state']}")
    print(f"修改轮数：{len(result['modification_history'])}")
    
    # 示例 3: 获取未完成列表
    print("\n=== 示例 3: 获取未完成列表 ===")
    pending_message = integration.format_pending_message()
    print(pending_message)
    
    # 示例 4: 完成任务
    print("\n=== 示例 4: 完成任务 ===")
    success = integration.complete_task()
    print(f"任务完成：{success}")


if __name__ == '__main__':
    example_usage()
