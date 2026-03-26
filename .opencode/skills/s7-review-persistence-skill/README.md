# Review Persistence Skill - 使用文档

## 📋 概述

Review Persistence Skill 提供评估单状态的持久化存储与恢复功能，支持：

- ✅ 状态保存与加载（Redis 缓存）
- ✅ 用户未完成列表管理
- ✅ 全局未完成列表查询
- ✅ 任务名称模糊搜索
- ✅ 自动过期清理（TTL 机制）

## 🔧 环境配置

### Redis 配置

在 `_meta.json` 或环境变量中配置：

```json
{
  "env": {
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "REDIS_PASSWORD": "",  // 可选
    "STATE_TTL_SECONDS": "3600",      // 状态缓存 1 小时
    "PENDING_LIST_TTL_SECONDS": "86400"  // 未完成列表 24 小时
  }
}
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 🚀 快速开始

### 1. Python 代码集成

```python
from review_persistence import ReviewStateManager

# 初始化管理器
manager = ReviewStateManager(
    task_id="task_20260326_001",
    org_id="org_123",
    user_id="user_456"
)

# 保存状态
manager.save_state(
    state='REVIEW_IN_PROGRESS',
    context={'task_name': 'XX 项目', 'current_round': 1},
    modification_history=[{'round': 1, 'changes': '初始版本'}]
)

# 加载状态
state_data = manager.load_state()
print(f"当前状态：{state_data['state']}")

# 获取用户未完成任务
pending_tasks = manager.get_user_pending_tasks()
print(manager.format_pending_message(pending_tasks))

# 完成任务
manager.complete_task()
```

### 2. 命令行使用

```bash
# 保存状态
python scripts/main.py save \
  --task-id task_001 \
  --org-id org_123 \
  --user-id user_456 \
  --state REVIEW_IN_PROGRESS \
  --context '{"task_name":"XX 项目"}'

# 加载状态
python scripts/main.py load --task-id task_001

# 列出用户未完成任务
python scripts/main.py list-user --user-id user_456

# 列出全局未完成任务
python scripts/main.py list-global --limit 20

# 根据名称查找任务
python scripts/main.py find --name "XX 项目" --user-id user_456

# 检查 Redis 连接
python scripts/main.py status
```

## 📊 Redis 数据结构

### Key 设计

| Key 模式 | 类型 | 用途 | TTL |
|---------|------|------|-----|
| `review_state:{task_id}` | Hash | 存储评估单状态 | 1 小时 |
| `user_pending_tasks:{user_id}` | Set | 用户未完成任务 ID 集合 | 24 小时 |
| `global_pending_tasks` | ZSet | 全局未完成任务（按时间排序） | 24 小时 |

### 状态数据结构

```json
{
  "state": "REVIEW_IN_PROGRESS",
  "task_name": "XX 系统开发项目",
  "org_id": "org_123",
  "user_id": "user_456",
  "context": {
    "task_name": "XX 系统开发项目",
    "current_round": 3,
    "client_type": "企业客户"
  },
  "modification_history": [
    {
      "round": 1,
      "action": "modify",
      "changes": ["开发阶段 +3 人天"],
      "timestamp": "2026-03-26T10:00:00"
    }
  ],
  "last_modified": "2026-03-26T11:30:00",
  "modification_count": 3
}
```

## 🔄 与 ReviewStateMachine 集成

参考 `integration_example.py`：

```python
from review_state_machine import ReviewStateMachine
from review_persistence import ReviewStateManager

class ReviewPersistenceIntegration:
    def __init__(self, task_id, org_id, user_id):
        self.state_machine = ReviewStateMachine(task_id)
        self.persistence = ReviewStateManager(task_id, org_id, user_id)
    
    def process_user_message(self, message):
        # 1. 加载状态
        state_data = self.persistence.load_state()
        
        # 2. 状态机处理
        self.state_machine.set_state(state_data['state'])
        result = self.state_machine.process_message(message)
        
        # 3. 保存新状态
        self.persistence.save_state(
            state=result['next_state'],
            context=state_data['context'],
            modification_history=updated_history
        )
        
        return result
```

## 🎯 典型使用场景

### 场景 1: Agent 启动时恢复状态

```python
def on_agent_start():
    manager = ReviewStateManager()
    all_states = manager.scan_all_states()
    
    if all_states:
        print(f"发现 {len(all_states)} 个未完成评估单")
        # 提示用户选择继续哪个任务
```

### 场景 2: 用户主动查询待办

```python
def handle_pending_query(user_id):
    manager = ReviewStateManager(user_id=user_id)
    pending_tasks = manager.get_user_pending_tasks()
    
    if pending_tasks:
        return manager.format_pending_message(pending_tasks)
    else:
        return "✅ 所有评估单已完成"
```

### 场景 3: 任务完成清理

```python
def on_task_complete(task_id):
    manager = ReviewStateManager(task_id=task_id)
    manager.complete_task()  # 删除状态 + 清理列表
```

## 🧪 测试

```bash
# 运行单元测试
pytest tests/test_persistence.py -v

# 运行集成示例
python integration_example.py
```

## ⚠️ 注意事项

1. **Redis 连接失败处理**: 所有方法都会检查连接状态，失败时返回安全值（False/None/[]）
2. **TTL 过期**: 状态 1 小时后自动过期，未完成列表 24 小时后过期
3. **并发安全**: Redis 操作是原子的，但应用层需要注意并发修改
4. **内存管理**: 定期清理过期键，避免 Redis 内存占用过高

## 📝 输出格式示例

### 未完成列表消息

```markdown
检测到您有 **3 个** 未完成的评估单：

| 序号 | 项目名称 | 当前状态 | 最后修改 | 已修改轮数 |
|-----|---------|---------|---------|-----------|
| 1 | XX 系统开发项目 | 审核中 | 30 分钟前 | 3 轮 |
| 2 | YY 小程序开发 | 等待确认 | 2 小时前 | 1 轮 |
| 3 | ZZ 数据平台 | 修改中 | 1 天前 | 5 轮 |

请回复：
- **数字** (如 "1") 选择继续
- **项目名称** (如 "XX 项目") 直接继续
- **忽略** 开始新任务
```

---

_专业持久化，让评估状态有据可查。_
