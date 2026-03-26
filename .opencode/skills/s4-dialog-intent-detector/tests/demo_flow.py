"""
对话意图检测器 - 完整流程演示
"""
import subprocess
import json
import sys


def run_integration(action, **kwargs):
    """运行集成入口并返回结果。"""
    cmd = [
        sys.executable,
        "integration_main.py",
        "--action", action,
        "--pretty"
    ]
    
    for key, value in kwargs.items():
        key = key.replace("_", "-")
        if isinstance(value, dict):
            cmd.extend(["--json-input", json.dumps(value, ensure_ascii=False)])
        elif value is not None:
            cmd.extend([f"--{key}", str(value)])
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return json.loads(result.stdout)


def main():
    task_id = "demo-task-001"
    
    print("=" * 60)
    print("Dialog Intent Detector - Integration Demo")
    print("=" * 60)
    print()
    
    scenarios = [
        ("风险等级调高一点", "Modify risk level"),
        ("工时也增加些", "Add more work hours"),
        ("好了", "Ready to confirm"),
        ("确认", "Confirm final version"),
    ]
    
    for i, (message, description) in enumerate(scenarios, 1):
        print(f"Step {i}: {description}")
        print(f"User: {message}")
        
        result = run_integration("process_message", message=message, task_id=task_id)
        
        print(f"Agent: {result['data']['message']}")
        print(f"State: {result['data']['state']}")
        print(f"Intent: {result['data']['intent']} (confidence: {result['data']['confidence']})")
        
        if result['data'].get('s3_input'):
            print()
            print(">>> S3 Learning Flywheel Triggered!")
            print(f"S3 input constructed: True")
        
        print()
    
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
