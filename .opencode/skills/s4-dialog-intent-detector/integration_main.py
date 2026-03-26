"""
对话意图检测器 - 主流程集成入口

将对话意图检测器与 S3 学习飞轮集成，实现完整的工务审核对话流程。
"""
import argparse
import io
import json
import sys
from typing import Any, Dict, Optional

# Windows 编码兼容性修复
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )

from dialog_intent_detector import DialogIntentDetector, DialogState, IntentType
from review_state_machine import ReviewStateMachine


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="对话意图检测器 - 主流程集成")
    parser.add_argument(
        "--action",
        required=True,
        choices=["process_message", "get_state", "reset_state"],
        help="操作类型"
    )
    parser.add_argument("--message", help="用户消息内容")
    parser.add_argument("--task-id", help="任务 ID")
    parser.add_argument("--state", help="当前状态（可选，默认从状态机读取）")
    parser.add_argument("--json-input-file", help="从文件读取 JSON 输入")
    parser.add_argument("--json-input", help="直接传 JSON 字符串")
    parser.add_argument("--pretty", action="store_true", help="格式化输出")
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    """从文件或内联 JSON 加载 payload。"""
    if args.json_input_file:
        with open(args.json_input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    if args.json_input:
        return json.loads(args.json_input)
    return None


def process_message(
    message: str,
    task_id: str,
    current_state: Optional[str] = None,
    org_id: str = "default-org",
    user_id: str = "default-user"
) -> Dict[str, Any]:
    """
    处理用户消息，返回 Agent 响应和状态更新。
    
    Args:
        message: 用户消息内容
        task_id: 任务 ID
        current_state: 当前状态（可选）
        org_id: 组织 ID
        user_id: 用户 ID
    
    Returns:
        包含响应消息、状态更新、动作指示的字典
    """
    # 初始化检测器和状态机
    detector = DialogIntentDetector()
    state_machine = ReviewStateMachine(task_id=task_id, org_id=org_id, user_id=user_id)
    
    # 如果有当前状态，先设置
    if current_state:
        try:
            state_machine.state = DialogState(current_state)
        except ValueError:
            pass  # 忽略无效状态
    
    # 检测意图
    intent_result = detector.detect_intent(message, state_machine.context)
    
    # 状态机处理
    response = state_machine.handle_user_message(message)
    
    # 构造返回结果
    result = {
        "success": True,
        "data": {
            "message": response.get("message", ""),
            "state": state_machine.context.state.value,
            "intent": intent_result.intent.value if intent_result.intent else "UNKNOWN",
            "confidence": intent_result.confidence,
            "action": response.get("action"),
            "s3_input": response.get("s3_input"),
            "s3_input_constructed": response.get("s3_input_constructed", False),
        },
        "error": None
    }
    
    # 如果触发了 S3，添加 S3 调用指示
    if response.get("action") == "call_s3":
        result["data"]["call_s3"] = True
        result["data"]["s3_payload"] = response.get("s3_input")
    
    return result


def get_state(task_id: str, org_id: str = "default-org", user_id: str = "default-user") -> Dict[str, Any]:
    """获取当前状态。"""
    state_machine = ReviewStateMachine(task_id=task_id, org_id=org_id, user_id=user_id)
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "state": state_machine.context.state.value,
            "modification_count": state_machine.modification_count,
        },
        "error": None
    }


def reset_state(task_id: str, org_id: str = "default-org", user_id: str = "default-user") -> Dict[str, Any]:
    """重置状态。"""
    state_machine = ReviewStateMachine(task_id=task_id, org_id=org_id, user_id=user_id)
    state_machine.reset()
    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "state": state_machine.state.value,
            "message": "状态已重置",
        },
        "error": None
    }


def main():
    args = parse_args()
    
    try:
        if args.action == "process_message":
            if not args.message:
                # 从 JSON 输入中获取消息
                payload = load_payload(args)
                if not payload or "message" not in payload:
                    print(json.dumps({
                        "success": False,
                        "data": None,
                        "error": "message is required"
                    }, ensure_ascii=False))
                    return
                message = payload["message"]
                task_id = payload.get("task_id", "default")
                current_state = payload.get("state")
                org_id = payload.get("org_id", "default-org")
                user_id = payload.get("user_id", "default-user")
            else:
                message = args.message
                task_id = args.task_id or "default"
                current_state = args.state
                org_id = "default-org"
                user_id = "default-user"
            
            result = process_message(message, task_id, current_state, org_id, user_id)
        
        elif args.action == "get_state":
            task_id = args.task_id or "default"
            result = get_state(task_id)
        
        elif args.action == "reset_state":
            task_id = args.task_id or "default"
            result = reset_state(task_id)
        
        else:
            result = {
                "success": False,
                "data": None,
                "error": f"Unknown action: {args.action}"
            }
        
        # 输出结果
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
    
    except Exception as e:
        print(json.dumps({
            "success": False,
            "data": None,
            "error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
