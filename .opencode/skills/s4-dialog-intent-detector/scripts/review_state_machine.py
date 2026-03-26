"""
审核对话状态机 - Review Dialog State Machine

管理工务审核对话的完整流程，集成意图检测器和 S3 触发逻辑。

状态流转：
REVIEW_IN_PROGRESS → READY_TO_CONFIRM → CONFIRMATION_PENDING → LEARNING → COMPLETED
         ↑                    ↓
         └────────────────────┘ (取消/继续修改)

持久化集成：
- 使用 ReviewStateManager 将状态持久化到 Redis
- 支持进程重启后自动恢复审核状态
- TTL 1 小时，自动过期清理
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from dialog_intent_detector import (
    DialogIntentDetector,
    DialogContext,
    DialogState,
    IntentType,
    IntentResult,
    EditAction
)
from review_persistence import ReviewStateManager


class ReviewStateMachine:
    """
    审核对话状态机
    
    核心职责：
    1. 管理对话状态流转
    2. 集成意图检测器
    3. 生成修订摘要
    4. 构造 S3 输入
    5. 调用 S3 学习飞轮
    6. 持久化状态到 Redis（支持重启恢复）
    """
    
    def __init__(self, task_id: str, org_id: str, user_id: str, auto_load: bool = True):
        self.task_id = task_id
        self.org_id = org_id
        self.user_id = user_id
        
        self.detector = DialogIntentDetector()
        self.context = DialogContext()
        
        self.initial_report: Optional[Dict] = None
        self.current_report: Optional[Dict] = None
        self.edit_actions: List[EditAction] = []
        self.conversation_history: List[Dict] = []
        
        self.state = DialogState.REVIEW_IN_PROGRESS
        
        # 初始化持久化管理器
        self.persistence = ReviewStateManager()
        
        # 自动加载已有状态（如果存在）
        if auto_load:
            self.load_state()
    
    def save_state(self) -> bool:
        """
        保存当前状态到 Redis
        
        Returns:
            bool: 保存是否成功
        """
        try:
            state_data = {
                'task_id': self.task_id,
                'org_id': self.org_id,
                'user_id': self.user_id,
                'state': self.state.value,
                'context': {
                    'state': self.context.state.value if self.context.state else None,
                    'initial_report_exists': self.context.initial_report_exists,
                    'final_report_exists': self.context.final_report_exists,
                    'has_revisions': self.context.has_revisions,
                    'auto_save_enabled': self.context.auto_save_enabled,
                    'last_saved_at': self.context.last_saved_at,
                    'recovery_count': self.context.recovery_count
                },
                'initial_report': self.initial_report,
                'current_report': self.current_report,
                'edit_actions': [
                    {
                        'field': action.field,
                        'before': action.before,
                        'after': action.after,
                        'timestamp': action.timestamp,
                        'reason': action.reason
                    }
                    for action in self.edit_actions
                ],
                'conversation_history': self.conversation_history,
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.persistence.save_state(self.task_id, state_data)
            if success:
                self.context.last_saved_at = datetime.now().isoformat()
            return success
        except Exception as e:
            print(f"[WARN] 保存状态失败：{e}")
            return False
    
    def load_state(self) -> bool:
        """
        从 Redis 加载状态
        
        Returns:
            bool: 是否成功加载（False 表示无已存状态）
        """
        try:
            state_data = self.persistence.load_state(self.task_id)
            if state_data:
                self.state = DialogState(state_data.get('state', 'review_in_progress'))
                
                # 恢复上下文
                ctx = state_data.get('context', {})
                self.context.state = DialogState(ctx.get('state', 'review_in_progress'))
                self.context.initial_report_exists = ctx.get('initial_report_exists', False)
                self.context.final_report_exists = ctx.get('final_report_exists', False)
                self.context.has_revisions = ctx.get('has_revisions', False)
                self.context.auto_save_enabled = ctx.get('auto_save_enabled', True)
                self.context.last_saved_at = ctx.get('last_saved_at')
                self.context.recovery_count = ctx.get('recovery_count', 0) + 1
                
                # 恢复报告数据
                self.initial_report = state_data.get('initial_report')
                self.current_report = state_data.get('current_report')
                
                # 恢复编辑动作
                edit_actions_data = state_data.get('edit_actions', [])
                self.edit_actions = [
                    EditAction(
                        field=action['field'],
                        before=action['before'],
                        after=action['after'],
                        timestamp=action['timestamp'],
                        reason=action.get('reason', '')
                    )
                    for action in edit_actions_data
                ]
                
                # 恢复对话历史
                self.conversation_history = state_data.get('conversation_history', [])
                
                print(f"[INFO] 已恢复任务 {self.task_id} 的审核状态（第 {self.context.recovery_count} 次恢复）")
                return True
            else:
                print(f"[INFO] 任务 {self.task_id} 无已存状态，从初始状态开始")
                return False
        except Exception as e:
            print(f"[WARN] 加载状态失败：{e}")
            return False
    
    def delete_state(self) -> bool:
        """
        删除 Redis 中的状态（流程完成后清理）
        
        Returns:
            bool: 删除是否成功
        """
        try:
            return self.persistence.delete_state(self.task_id)
        except Exception as e:
            print(f"[WARN] 删除状态失败：{e}")
            return False
    
    def handle_user_message(self, message: str) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            message: 用户消息文本
            
        Returns:
            Dict: 响应内容（包含状态、消息、建议动作）
        """
        # 记录对话历史
        self.conversation_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # 检测意图
        intent_result = self.detector.detect_intent(message, self.context)
        
        # 根据意图执行相应动作
        if intent_result.intent == IntentType.MODIFY:
            result = self._handle_modify(message, intent_result)
        
        elif intent_result.intent == IntentType.READY_TO_CONFIRM:
            result = self._handle_ready_to_confirm(message, intent_result)
        
        elif intent_result.intent == IntentType.CONFIRM:
            result = self._handle_confirm(message, intent_result)
        
        elif intent_result.intent == IntentType.CANCEL:
            result = self._handle_cancel(message, intent_result)
        
        else:
            result = self._handle_unknown(message, intent_result)
        
        # 保存状态到 Redis（每次交互后自动持久化）
        self.save_state()
        
        return result
    
    def _handle_modify(self, message: str, intent: IntentResult) -> Dict[str, Any]:
        """处理修改意图"""
        # 更新状态
        self.state = DialogState.REVIEW_IN_PROGRESS
        self.context.state = DialogState.REVIEW_IN_PROGRESS
        
        # TODO: 这里需要调用 S6 或其他逻辑来实际修改报告
        # 暂时返回提示信息
        return {
            'status': 'modify',
            'message': f"收到修改请求：{message}\n（此处应调用 S6 修改评估报告）",
            'suggested_action': '调用 S6 修改报告',
            'intent': intent.intent.value,
            'confidence': intent.confidence
        }
    
    def _handle_ready_to_confirm(self, message: str, intent: IntentResult) -> Dict[str, Any]:
        """处理首次确认意图（进入二次确认流程）"""
        # 更新状态
        self.state = DialogState.CONFIRMATION_PENDING
        self.context.state = DialogState.CONFIRMATION_PENDING
        
        # 生成修订摘要
        if self.initial_report and self.current_report:
            revision_summary = self.detector.generate_revision_summary(
                self.initial_report,
                self.current_report
            )
        else:
            revision_summary = "无修订内容"
        
        # 构建确认消息
        confirm_message = f"""
好的，当前评估单已调整完成：

{revision_summary}

### [OK] 确认操作
- **确认将此版本作为最终稿** → 回复"确认"或"是的"
- **还需要修改** → 直接提出修改内容
- **取消审核** → 回复"取消"或"再想想"

> [BOOK] 确认后我将学习本次修订经验，用于优化未来评估质量。
"""
        
        return {
            'status': 'confirmation_pending',
            'message': confirm_message,
            'suggested_action': '等待用户二次确认',
            'intent': intent.intent.value,
            'confidence': intent.confidence,
            'revision_summary': revision_summary
        }
    
    def _handle_confirm(self, message: str, intent: IntentResult) -> Dict[str, Any]:
        """处理二次确认意图（触发 S3）"""
        # 更新状态
        self.state = DialogState.LEARNING
        self.context.state = DialogState.LEARNING
        self.context.final_report_exists = True
        
        # 构造 S3 输入
        s3_input = self._build_s3_input()
        
        # TODO: 实际调用 S3
        # learning_result = call_s3_learning(s3_input)
        
        # 模拟 S3 调用
        learning_result = {
            'success': True,
            'data': {
                'learning_sample_id': f"LF-{self.task_id}",
                'rule_candidates_count': 2,
                'preference_candidates_count': 1
            }
        }
        
        # 构建学习完成消息
        if learning_result.get('success'):
            complete_message = f"""
[OK] 已确认最终稿

[BOOK] 正在学习本次修订经验...

### 学习结果
- [OK] 已记录 1 个学习样本
- [OK] 已生成 {learning_result['data']['rule_candidates_count']} 条规则候选
- [OK] 已更新 {learning_result['data']['preference_candidates_count']} 项偏好模型

评估单已交付服贸人员用于报价。
"""
            # 更新状态为完成
            self.state = DialogState.COMPLETED
            self.context.state = DialogState.COMPLETED
            
            # 保存最终状态后清理（流程结束）
            self.save_state()
            self.delete_state()  # 完成后删除持久化状态
            
            return {
                'status': 'completed',
                'message': complete_message,
                'suggested_action': '无（流程结束）',
                'intent': intent.intent.value,
                'confidence': intent.confidence,
                's3_input': s3_input,
                'learning_result': learning_result
            }
        else:
            # S3 调用失败，但仍交付评估单
            return {
                'status': 'completed_with_error',
                'message': "[OK] 已确认最终稿，评估单已交付服贸。\n[WARN] 学习步骤失败，将异步重试。",
                'suggested_action': '异步重试 S3',
                'intent': intent.intent.value,
                'confidence': intent.confidence,
                'error': learning_result.get('error')
            }
    
    def _handle_cancel(self, message: str, intent: IntentResult) -> Dict[str, Any]:
        """处理取消意图"""
        # 重置状态
        self.state = DialogState.REVIEW_IN_PROGRESS
        self.context.state = DialogState.REVIEW_IN_PROGRESS
        
        # 保存取消后的状态
        self.save_state()
        
        return {
            'status': 'cancelled',
            'message': "好的，评估单保持待审核状态。\n您随时可以继续修改或确认。",
            'suggested_action': '继续审核流程',
            'intent': intent.intent.value,
            'confidence': intent.confidence
        }
    
    def _handle_unknown(self, message: str, intent: IntentResult) -> Dict[str, Any]:
        """处理未知意图"""
        return {
            'status': 'unknown',
            'message': f"收到：{message}\n请问您需要修改评估单还是确认最终稿？",
            'suggested_action': '询问澄清',
            'intent': intent.intent.value,
            'confidence': intent.confidence
        }
    
    def _build_s3_input(self) -> Dict[str, Any]:
        """
        构造 S3 学习飞轮的输入数据
        
        Returns:
            Dict: S3 输入 JSON 结构
        """
        return {
            "context": {
                "task_id": self.task_id,
                "org_id": self.org_id,
                "user_id": self.user_id,
                "business_type": "工程服务评估",  # TODO: 从需求中提取
                "ship_type": "未知"  # TODO: 从需求中提取
            },
            "artifacts": {
                "requirement_json": "{}",  # TODO: S5 输出
                "history_cases_json": "[]",  # TODO: S1 输出
                "assessment_reasoning_json": "{}",  # TODO: S2 输出
                "initial_report_json": json.dumps(self.initial_report, ensure_ascii=False),
                "final_report_json": json.dumps(self.current_report, ensure_ascii=False),
                "conversation_messages": json.dumps(self.conversation_history, ensure_ascii=False),
                "edit_actions": [
                    {
                        'field': action.field,
                        'before': action.before,
                        'after': action.after,
                        'timestamp': action.timestamp,
                        'reason': action.reason
                    }
                    for action in self.edit_actions
                ]
            },
            "versions": {
                "s5_version": "2.0.0",
                "s1_version": "1.0.0",
                "s2_version": "1.1.0",
                "s6_version": "1.0.0",
                "prompt_version": "report_prompt_v1",
                "references_version": "2026-03-25"
            },
            "options": {
                "store_learning_sample": True,
                "generate_rule_candidates": True,
                "generate_preference_candidates": True
            }
        }
    
    def set_initial_report(self, report: Dict):
        """设置初稿报告"""
        self.initial_report = report.copy()
        self.current_report = report.copy()
        self.context.initial_report_exists = True
        
        # 保存初始状态
        self.save_state()
    
    def apply_edit(self, field: str, before: str, after: str, reason: str = ""):
        """
        应用编辑操作
        
        Args:
            field: 修改字段
            before: 修改前值
            after: 修改后值
            reason: 修改原因
        """
        # 更新当前报告
        if self.current_report:
            self.current_report[field] = after
        
        # 记录编辑动作
        self.edit_actions.append(EditAction(
            field=field,
            before=before,
            after=after,
            timestamp=datetime.now().isoformat(),
            reason=reason
        ))
        
        # 更新上下文
        self.context.has_revisions = True
        
        # 保存编辑后的状态
        self.save_state()


# 测试代码
if __name__ == "__main__":
    # 创建状态机实例
    machine = ReviewStateMachine(
        task_id="TASK-2026-001",
        org_id="ORG-001",
        user_id="USER-工务 -001"
    )
    
    # 设置初稿报告
    machine.set_initial_report({
        'risk_level': '中',
        'total_hours': 96,
        'total_persons': 3,
        'status': 'draft'
    })
    
    print("审核对话状态机测试\n")
    print("=" * 80)
    
    # 模拟对话流程
    test_messages = [
        "风险等级调高一点",
        "工时也增加些",
        "再加 1 个人",
        "好了",
        "确认"
    ]
    
    for msg in test_messages:
        print(f"\n用户：{msg}")
        response = machine.handle_user_message(msg)
        print(f"Agent: {response['message']}")
        print(f"状态：{machine.state.value}")
        print("-" * 80)
    
    print(f"\n最终状态：{machine.state.value}")
    print(f"修订次数：{len(machine.edit_actions)}")
    print(f"S3 输入已构造：{machine._build_s3_input() is not None}")
