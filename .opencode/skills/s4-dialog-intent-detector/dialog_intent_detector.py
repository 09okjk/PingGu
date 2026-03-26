"""
对话意图检测器 - Dialog Intent Detector

用于识别工务审核对话中的确认/修改/取消意图，触发 S3 学习飞轮。

核心逻辑：
1. S6 生成评估报告初稿后，进入审核对话流程
2. 检测工务消息中的意图关键词
3. 结合上下文（是否有修订历史）判断意图
4. 返回意图类型供上层决策是否触发 S3

意图类型：
- READY_TO_CONFIRM: 首次确认（进入二次确认流程）
- CONFIRM: 二次确认（触发 S3）
- MODIFY: 继续修改
- CANCEL: 取消/反悔
- UNKNOWN: 未知意图
"""

# Windows 编码修复
import sys
import io
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举"""
    READY_TO_CONFIRM = "READY_TO_CONFIRM"  # 首次确认
    CONFIRM = "CONFIRM"                    # 二次确认（触发 S3）
    MODIFY = "MODIFY"                      # 继续修改
    CANCEL = "CANCEL"                      # 取消/反悔
    UNKNOWN = "UNKNOWN"                    # 未知意图


class DialogState(str, Enum):
    """对话状态枚举"""
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"      # 审核中
    READY_TO_CONFIRM = "READY_TO_CONFIRM"          # 待确认（已检测到首次确认）
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"  # 二次确认中
    LEARNING = "LEARNING"                          # 学习中
    COMPLETED = "COMPLETED"                        # 已完成


@dataclass
class EditAction:
    """编辑动作记录"""
    field: str           # 修改字段
    before: str          # 修改前值
    after: str           # 修改后值
    timestamp: str       # 修改时间
    reason: str = ""     # 修改原因（可选）


@dataclass
class DialogContext:
    """对话上下文"""
    state: DialogState = DialogState.REVIEW_IN_PROGRESS
    has_revisions: bool = False
    edit_actions: List[EditAction] = field(default_factory=list)
    conversation_turns: int = 0
    initial_report_exists: bool = True
    final_report_exists: bool = False
    
    @property
    def edit_actions_count(self) -> int:
        """修订次数"""
        return len(self.edit_actions)


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float              # 置信度 (0.0-1.0)
    matched_pattern: str           # 匹配的关键词/模式
    explanation: str               # 解释说明
    suggested_action: str          # 建议的下一步动作


class DialogIntentDetector:
    """
    对话意图检测器
    
    使用规则匹配 + 上下文感知的方式识别工务意图。
    支持中文关键词、口语化表达、模糊表述。
    """
    
    def __init__(self):
        # 确认意图关键词（高置信度）
        self.confirm_patterns_high = [
            r'好了',
            r'可以了',
            r'没问题了',
            r'就这样吧',
            r'这样可以了',
            r'这样好了',
        ]
        
        # 通过表述（高置信度）
        self.pass_patterns_high = [
            r'通过',
            r'审核通过',
            r'确认',
            r'OK',
            r'ok',
            r'√',
            r'✓',
        ]
        
        # 交付指示（高置信度）
        self.delivery_patterns_high = [
            r'可以交付了',
            r'可以交付',
            r'给服贸吧',
            r'给服贸',
            r'交付吧',
            r'最终版',
            r'定稿',
        ]
        
        # 模糊确认（中置信度，需上下文确认）
        self.confirm_patterns_medium = [
            r'^嗯$',
            r'^好$',
            r'^行$',
            r'可以',
            r'行吧',
            r'好吧',
            r'暂时这样',
            r'先这样',
        ]
        
        # 修改意图关键词
        self.modify_patterns = [
            r'调整',
            r'调高',
            r'调低',
            r'增加',
            r'减少',
            r'修改',
            r'改',
            r'再加',
            r'再减',
            r'加点',
            r'减点',
            r'提高',
            r'降低',
            r'变大',
            r'变小',
        ]
        
        # 取消/反悔关键词
        self.cancel_patterns = [
            r'取消',
            r'再想想',
            r'等等',
            r'等一下',
            r'先不',
            r'暂时不',
            r'我再看看',
            r'我再想想',
        ]
        
        # 否定词（用于排除误判）
        self.negation_patterns = [
            r'不 (好 | 行 | 可以 | 对)',
            r'还没',
            r'不行',
            r'不对',
        ]
    
    def detect_intent(self, message: str, context: DialogContext) -> IntentResult:
        """
        检测用户消息的意图
        
        Args:
            message: 用户消息文本
            context: 对话上下文
            
        Returns:
            IntentResult: 意图识别结果
        """
        message = message.strip()
        
        # 检查是否为否定表述（排除误判）
        if self._matches_any(message, self.negation_patterns):
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.9,
                matched_pattern="negation",
                explanation="检测到否定表述，不视为确认",
                suggested_action="继续等待明确指令"
            )
        
        # 检测修改意图（优先级最高，避免误判为确认）
        modify_match = self._matches_any_with_pattern(message, self.modify_patterns)
        if modify_match:
            return IntentResult(
                intent=IntentType.MODIFY,
                confidence=0.95,
                matched_pattern=modify_match,
                explanation="检测到修改意图",
                suggested_action="执行修改并继续审核"
            )
        
        # 检测取消意图
        cancel_match = self._matches_any_with_pattern(message, self.cancel_patterns)
        if cancel_match:
            return IntentResult(
                intent=IntentType.CANCEL,
                confidence=0.9,
                matched_pattern=cancel_match,
                explanation="检测到取消/反悔意图",
                suggested_action="取消待确认状态，返回审核中"
            )
        
        # 根据当前状态判断确认意图
        if context.state == DialogState.CONFIRMATION_PENDING:
            # 二次确认状态：检测确认关键词
            confirm_match = self._matches_any_with_pattern(message, self.pass_patterns_high)
            if confirm_match or message in ['确认', '是的', '对', '好的', '好']:
                return IntentResult(
                    intent=IntentType.CONFIRM,
                    confidence=0.95,
                    matched_pattern=confirm_match or message,
                    explanation="二次确认，将触发 S3 学习",
                    suggested_action="调用 S3 learn_from_revision"
                )
            else:
                return IntentResult(
                    intent=IntentType.UNKNOWN,
                    confidence=0.7,
                    matched_pattern="no_match",
                    explanation="二次确认状态下未检测到明确确认",
                    suggested_action="询问用户是否确认"
                )
        
        elif context.state in [DialogState.REVIEW_IN_PROGRESS, DialogState.READY_TO_CONFIRM]:
            # 审核中状态：检测首次确认意图
            
            # 必须有修订历史才能触发确认流程（无修订时直接交付）
            has_revisions = context.edit_actions_count > 0
            
            # 高置信度确认
            high_conf_match = (
                self._matches_any_with_pattern(message, self.confirm_patterns_high) or
                self._matches_any_with_pattern(message, self.pass_patterns_high) or
                self._matches_any_with_pattern(message, self.delivery_patterns_high)
            )
            
            if high_conf_match:
                if has_revisions:
                    return IntentResult(
                        intent=IntentType.READY_TO_CONFIRM,
                        confidence=0.95,
                        matched_pattern=high_conf_match,
                        explanation="检测到首次确认意图（有修订历史）",
                        suggested_action="进入二次确认流程，展示修订摘要"
                    )
                else:
                    # 无修订直接确认，跳过二次确认
                    return IntentResult(
                        intent=IntentType.CONFIRM,
                        confidence=0.9,
                        matched_pattern=high_conf_match,
                        explanation="无修订直接确认，跳过二次确认",
                        suggested_action="直接交付，跳过 S3 学习"
                    )
            
            # 中置信度确认（需上下文确认）
            medium_conf_match = self._matches_any_with_pattern(message, self.confirm_patterns_medium)
            if medium_conf_match and has_revisions:
                return IntentResult(
                    intent=IntentType.READY_TO_CONFIRM,
                    confidence=0.6,
                    matched_pattern=medium_conf_match,
                    explanation="检测到模糊确认意图（需上下文确认）",
                    suggested_action="进入二次确认流程，展示修订摘要"
                )
        
        # 未匹配任何模式
        return IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.5,
            matched_pattern="no_match",
            explanation="未检测到明确意图",
            suggested_action="继续等待用户指令或询问澄清"
        )
    
    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        """检查文本是否匹配任一模式"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _matches_any_with_pattern(self, text: str, patterns: List[str]) -> Optional[str]:
        """检查文本是否匹配任一模式，返回匹配的模式"""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def generate_revision_summary(self, initial_report: dict, final_report: dict) -> str:
        """
        生成修订摘要（用于二次确认展示）
        
        Args:
            initial_report: 初稿报告
            final_report: 最终稿报告
            
        Returns:
            str: Markdown 格式的修订摘要
        """
        changes = []
        
        # 风险等级变化
        if initial_report.get('risk_level') != final_report.get('risk_level'):
            before = initial_report.get('risk_level', '-')
            after = final_report.get('risk_level', '-')
            changes.append({
                'field': '风险等级',
                'before': before,
                'after': after,
                'delta': f"⬆️ 调整" if self._level_up(before, after) else "⬇️ 调整"
            })
        
        # 工时变化
        initial_hours = initial_report.get('total_hours', 0)
        final_hours = final_report.get('total_hours', 0)
        if initial_hours != final_hours:
            delta = final_hours - initial_hours
            changes.append({
                'field': '总工时',
                'before': f"{initial_hours}人时",
                'after': f"{final_hours}人时",
                'delta': f"⬆️ +{delta}人时" if delta > 0 else f"⬇️ {delta}人时"
            })
        
        # 人数变化
        initial_persons = initial_report.get('total_persons', 0)
        final_persons = final_report.get('total_persons', 0)
        if initial_persons != final_persons:
            delta = final_persons - initial_persons
            changes.append({
                'field': '总人数',
                'before': f"{initial_persons}人",
                'after': f"{final_persons}人",
                'delta': f"⬆️ +{delta}人" if delta > 0 else f"⬇️ {delta}人"
            })
        
        # 构建 Markdown 表格
        if not changes:
            return "无实质性修订"
        
        markdown = "### 📊 修订摘要\n\n"
        markdown += "| 字段 | 初稿 | 最终稿 | 变化 |\n"
        markdown += "|------|------|--------|------|\n"
        
        for change in changes:
            markdown += f"| {change['field']} | {change['before']} | {change['after']} | {change['delta']} |\n"
        
        return markdown
    
    def _level_up(self, before: str, after: str) -> bool:
        """判断风险等级是否上调"""
        levels = {'低': 1, '中': 2, '高': 3}
        return levels.get(after, 0) > levels.get(before, 0)


# 测试代码
if __name__ == "__main__":
    detector = DialogIntentDetector()
    
    # 测试用例
    test_cases = [
        # (message, state, has_revisions, expected_intent)
        ("好了", DialogState.REVIEW_IN_PROGRESS, True, IntentType.READY_TO_CONFIRM),
        ("可以了", DialogState.REVIEW_IN_PROGRESS, True, IntentType.READY_TO_CONFIRM),
        ("确认", DialogState.CONFIRMATION_PENDING, True, IntentType.CONFIRM),
        ("是的", DialogState.CONFIRMATION_PENDING, True, IntentType.CONFIRM),
        ("风险等级调高一点", DialogState.REVIEW_IN_PROGRESS, True, IntentType.MODIFY),
        ("再增加 2 个人", DialogState.REVIEW_IN_PROGRESS, True, IntentType.MODIFY),
        ("好的等一下看一下", DialogState.REVIEW_IN_PROGRESS, True, IntentType.CANCEL),  # 暂缓确认
        ("取消", DialogState.CONFIRMATION_PENDING, True, IntentType.CANCEL),
        ("我再想想", DialogState.CONFIRMATION_PENDING, True, IntentType.CANCEL),
        ("没问题了", DialogState.REVIEW_IN_PROGRESS, False, IntentType.CONFIRM),  # 无修订直接确认
        ("给服贸吧", DialogState.REVIEW_IN_PROGRESS, True, IntentType.READY_TO_CONFIRM),
    ]
    
    print("对话意图检测器测试\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for message, state, has_revisions, expected in test_cases:
        context = DialogContext(
            state=state,
            has_revisions=has_revisions,
            edit_actions=[EditAction("test", "a", "b", "2026-03-26")] if has_revisions else []
        )
        
        result = detector.detect_intent(message, context)
        status = "[PASS]" if result.intent == expected else "[FAIL]"
        
        if result.intent == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} 消息：'{message}' | 状态：{state.value} | 有修订：{has_revisions}")
        print(f"   预期：{expected.value} | 实际：{result.intent.value} | 置信度：{result.confidence}")
        print(f"   解释：{result.explanation}")
        print()
    
    print("=" * 80)
    print(f"测试结果：{passed} 通过，{failed} 失败")
