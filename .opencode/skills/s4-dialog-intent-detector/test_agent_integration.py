"""
主 Agent 集成测试

模拟主 Agent 调用对话意图检测器的完整流程。
"""
import subprocess
import json
import sys
import os


class MockAgent:
    """模拟主 Agent 的行为。"""
    
    def __init__(self):
        self.task_id = None
        self.org_id = "org-123"
        self.user_id = "user-456"
        self.current_state = "READY_FOR_REVIEW"
    
    def call_intent_detector(self, message: str) -> dict:
        """调用对话意图检测器。"""
        cmd = [
            sys.executable,
            "integration_main.py",
            "--action", "process_message",
            "--json-input", json.dumps({
                "message": message,
                "task_id": self.task_id,
                "org_id": self.org_id,
                "user_id": self.user_id,
                "state": self.current_state
            }, ensure_ascii=False),
            "--pretty"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        return json.loads(result.stdout)
    
    def handle_s3_trigger(self, s3_input: dict):
        """处理 S3 学习飞轮触发。"""
        print("\n📚 触发 S3 学习飞轮！")
        print("调用：python scripts/main.py --action store --json-input <s3_input>")
        
        # 模拟 S3 调用
        cmd = [
            sys.executable,
            "scripts/main.py",
            "--action", "store",
            "--json-input", json.dumps(s3_input, ensure_ascii=False)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "learning-flywheel-skill")
        )
        
        if result.returncode == 0:
            print("✅ S3 学习完成")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"⚠️ S3 调用结果：{result.stderr}")
    
    def process_user_message(self, message: str):
        """处理用户消息的完整流程。"""
        print(f"\n👤 用户：{message}")
        
        # 调用意图检测器
        result = self.call_intent_detector(message)
        
        if not result.get("success"):
            print(f"❌ 错误：{result.get('error')}")
            return
        
        data = result["data"]
        
        # 显示 Agent 响应
        print(f"🤖 Agent: {data['message']}")
        print(f"📊 状态：{data['state']}")
        print(f"🎯 意图：{data['intent']} (置信度：{data['confidence']})")
        
        # 更新当前状态
        self.current_state = data['state']
        
        # 检查是否需要触发 S3
        if data.get("s3_input"):
            self.handle_s3_trigger(data["s3_input"])
    
    def start_review(self, task_id: str):
        """开始新的审核流程。"""
        self.task_id = task_id
        self.current_state = "READY_FOR_REVIEW"
        print(f"\n📋 开始新审核：{task_id}")
        print("=" * 60)


def test_scenario_1():
    """场景 1: 完整审核流程。"""
    print("\n" + "=" * 60)
    print("场景 1: 完整审核流程测试")
    print("=" * 60)
    
    agent = MockAgent()
    agent.start_review("TASK-2026-001")
    
    # 模拟对话
    messages = [
        "风险等级调高一点",
        "工时也增加些",
        "好了",
        "确认"
    ]
    
    for message in messages:
        agent.process_user_message(message)
        input("\n按回车继续...")
    
    print("\n" + "=" * 60)
    print("✅ 场景 1 测试完成")
    print("=" * 60)


def test_scenario_2():
    """场景 2: 中途取消。"""
    print("\n" + "=" * 60)
    print("场景 2: 中途取消测试")
    print("=" * 60)
    
    agent = MockAgent()
    agent.start_review("TASK-2026-002")
    
    messages = [
        "调整一下技术风险",
        "等一下，我先看看别的",
    ]
    
    for message in messages:
        agent.process_user_message(message)
        input("\n按回车继续...")
    
    print("\n" + "=" * 60)
    print("✅ 场景 2 测试完成")
    print("=" * 60)


def test_scenario_3():
    """场景 3: 多次修改后确认。"""
    print("\n" + "=" * 60)
    print("场景 3: 多次修改后确认测试")
    print("=" * 60)
    
    agent = MockAgent()
    agent.start_review("TASK-2026-003")
    
    messages = [
        "风险调高",
        "工时增加",
        "人员级别也调整",
        "好了",
        "确认"
    ]
    
    for message in messages:
        agent.process_user_message(message)
        input("\n按回车继续...")
    
    print("\n" + "=" * 60)
    print("✅ 场景 3 测试完成")
    print("=" * 60)


def main():
    """运行所有测试场景。"""
    print("=" * 60)
    print("主 Agent 集成测试")
    print("=" * 60)
    print("\n此测试模拟主 Agent 调用对话意图检测器的完整流程")
    print("包括：意图识别、状态管理、S3 学习飞轮触发")
    
    # 询问测试模式
    print("\n选择测试模式：")
    print("1. 完整测试（所有场景）")
    print("2. 单场景测试（场景 1）")
    print("3. 快速测试（无交互）")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == "1":
        test_scenario_1()
        test_scenario_2()
        test_scenario_3()
    elif choice == "2":
        test_scenario_1()
    else:
        # 快速测试模式
        print("\n" + "=" * 60)
        print("快速测试模式")
        print("=" * 60)
        
        agent = MockAgent()
        agent.start_review("TASK-FAST-001")
        
        messages = [
            "风险等级调高一点",
            "好了",
            "确认"
        ]
        
        for message in messages:
            agent.process_user_message(message)
        
        print("\n" + "=" * 60)
        print("✅ 快速测试完成")
        print("=" * 60)
    
    print("\n🎉 所有测试完成！")


if __name__ == "__main__":
    main()
