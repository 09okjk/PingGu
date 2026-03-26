# S7 - Review Persistence Skill - 评估单状态持久化

## 📋 元信息

| 字段 | 值 |
|-----|------|
| **名称** | S7 - Review Persistence Skill |
| **Slug** | `s7-review-persistence-skill` |
| **版本** | 2.0.0 |
| **作者** | 智能评估助理 |
| **描述** | 评估单状态持久化与恢复管理 (Phase 1-5 完整版) |
| **入口** | `scripts/main.py` |
| **运行环境** | Python 3.8+ |

---

## 🎯 功能概述

本 Skill 提供评估单状态的持久化存储与恢复能力，确保工务人员在审核/修改评估单过程中，即使遇到 Agent 重启、服务异常或中途离开等情况，也能无缝恢复审核流程。

### 核心能力

#### Phase 1-2: 基础持久化
1. **状态持久化** - 将评估单审核状态保存到 Redis
2. **状态恢复** - Agent 重启后自动恢复未完成的评估单
3. **未完成列表** - 支持查询用户/全局未完成的评估单

#### Phase 3: 深度集成
4. **状态机集成** - 与 ReviewStateMachine 深度集成，自动同步状态

#### Phase 4: 自动恢复
5. **启动恢复** - Agent 启动时自动扫描并恢复未完成状态

#### Phase 5: 主动通知
6. **用户通知** - 用户首次对话时主动提示未完成任务

#### 优化特性
7. **分布式锁** - Redis 锁防止并发修改
8. **部署配置** - 生产环境配置检查与验证

---

## 🔧 环境配置

### 必需环境变量

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 可选

# 过期时间配置
STATE_TTL_SECONDS=3600        # 状态缓存过期时间 (1 小时)
PENDING_LIST_TTL_SECONDS=86400  # 未完成列表过期时间 (24 小时)

# 锁配置
LOCK_TIMEOUT_SECONDS=30       # 分布式锁超时时间
LOCK_RETRY_DELAY_MS=100       # 锁重试延迟

# 通知配置
ENABLE_USER_NOTIFICATION=true # 是否启用用户通知
NOTIFICATION_CHANNEL=webchat  # 通知渠道
```

### Redis 安装

**Windows (开发环境)**:
```powershell
# 使用 Docker
docker run -d -p 6379:6379 --name redis redis:latest

# 或使用 Chocolatey
choco install redis-64
```

**Linux (生产环境)**:
```bash
sudo apt-get install redis-server
sudo systemctl enable redis
sudo systemctl start redis
```

### 依赖安装

#### 使用 uv (推荐)

```bash
# 创建虚拟环境
uv venv .venv

# 安装依赖
uv pip install -r requirements.txt

# 运行命令
uv run python -m scripts.main --help
```

#### 使用 pip

```bash
pip install redis
```

---

## 💡 使用方式

### CLI 命令

#### 基础命令 (Phase 1-2)

```bash
# 使用 uv 运行 (推荐，自动使用虚拟环境)
uv run python -m scripts.main save --task-id task_123 --org-id org_456 --user-id user_789 --state "REVIEW_IN_PROGRESS" --context '{"current_round": 3}'
uv run python -m scripts.main load --task-id task_123
uv run python -m scripts.main delete --task-id task_123
uv run python -m scripts.main list-user --user-id user_789
uv run python -m scripts.main list-global --limit 50
uv run python -m scripts.main find --name "XX 项目" --user-id user_789
uv run python -m scripts.main status

# 或激活虚拟环境后运行
.venv\Scripts\activate
python -m scripts.main --help
```

#### Phase 3: 状态机集成

```bash
uv run python -m scripts.main integrate --task-id task_123
```

#### Phase 4: 自动恢复

```bash
uv run python -m scripts.main recover --task-id task_123
uv run python -m scripts.main recover  # 恢复所有
```

#### Phase 5: 用户通知

```bash
uv run python -m scripts.main notify --user-id user_789
uv run python -m scripts.main notify  # 通知所有用户
```

#### 优化：分布式锁

```bash
uv run python -m scripts.main lock --resource "task_123" --timeout 10
uv run python -m scripts.main lock --resource "task_123" --release
```

#### 部署：配置检查

```bash
uv run python -m scripts.main deploy-config --check
uv run python -m scripts.main deploy-config --show
uv run python -m scripts.main deploy-config --test-connection
uv run python -m scripts.main deploy-config  # 显示部署指南
```

---

### Python API

#### Phase 1-2: 基础持久化

```python
from review_persistence import ReviewStateManager

# 初始化状态管理器
state_manager = ReviewStateManager(
    task_id="task_123",
    org_id="org_456",
    user_id="user_789"
)

# 保存状态
state_manager.save_state(
    state="REVIEW_IN_PROGRESS",
    context={
        "task_name": "XX 项目",
        "current_round": 3,
        "last_modification": {...}
    },
    modification_history=[...]
)

# 加载状态
loaded = state_manager.load_state()
if loaded:
    print(f"恢复状态：{loaded['state']}")
    print(f"已修改轮数：{loaded['modification_count']}")

# 查询未完成任务
pending_tasks = state_manager.get_user_pending_tasks(user_id="user_789")
for task in pending_tasks:
    print(f"- {task['task_name']}: {task['state']}")

# 完成任务并清理
state_manager.complete_task()
```

#### Phase 3: 状态机集成

```python
from state_machine_integration import StateMachineIntegration

# 初始化集成器
integration = StateMachineIntegration()

# 同步状态机状态
success = integration.sync_state_machine_state(task_id="task_123")

# 将状态机与持久化层绑定
class PersistentReviewStateMachine(ReviewStateMachine):
    def __init__(self, task_id, org_id, user_id):
        super().__init__(task_id, org_id, user_id)
        self.integration = StateMachineIntegration()
        
        # 自动加载持久化状态
        self.integration.load_persisted_state(self)
    
    def transition_to(self, new_state):
        super().transition_to(new_state)
        # 自动保存状态
        self.integration.save_state_machine_state(self)
    
    def complete(self):
        super().complete()
        # 自动清理持久化状态
        self.integration.clear_persisted_state(self.task_id)
```

#### Phase 4: 自动恢复

```python
from agent_bootstrap import AgentBootstrap

# 初始化启动管理器
bootstrap = AgentBootstrap()

# Agent 启动时自动恢复所有状态
async def on_agent_startup():
    recovered_count = bootstrap.recover_all_states()
    logger.info(f"已恢复 {recovered_count} 个未完成状态")

# 恢复指定任务
recovered = bootstrap.recover_single_state(task_id="task_123")
if recovered:
    logger.info(f"状态已恢复：{task_id}")
```

#### Phase 5: 用户通知

```python
from notification_handler import NotificationHandler

# 初始化通知处理器
notifier = NotificationHandler()

# 用户首次对话时检查未完成任务
async def on_user_first_message(user_id):
    pending_tasks = notifier.get_user_pending_tasks(user_id)
    if pending_tasks:
        message = notifier.format_welcome_back_message(pending_tasks)
        await send_message(user_id, message)

# 批量通知所有用户
notified_count = notifier.notify_all_users_with_pending_tasks()
logger.info(f"已通知 {notified_count} 个用户")
```

#### 优化：分布式锁

```python
from redis_lock import RedisLock

# 获取锁
lock = RedisLock("lock:task_123")
if lock.acquire(timeout=10):
    try:
        # 执行临界区代码
        modify_task_state()
    finally:
        lock.release()
else:
    logger.warning("无法获取锁，任务可能正在被其他进程修改")

# 使用上下文管理器
with RedisLock("lock:task_123", timeout=10) as lock:
    if lock.acquired:
        modify_task_state()
```

#### 部署：配置检查

```python
from deployment_config import DeploymentConfig

# 初始化配置检查器
config = DeploymentConfig()

# 验证配置
issues = config.validate_config()
if issues:
    for issue in issues:
        logger.error(f"配置问题：{issue}")
else:
    logger.info("配置检查通过")

# 测试 Redis 连接
if config.test_redis_connection():
    logger.info("Redis 连接正常")
else:
    logger.error("Redis 连接失败")

# 获取部署指南
guide = config.get_deployment_guide()
print(guide)
```

---

## 📊 Redis 数据结构

### Key 设计

```
# 单个评估单状态
review_state:{task_id} = JSON 对象
# 过期时间：STATE_TTL_SECONDS (默认 1 小时)

# 用户未完成列表 (Set)
user_pending_tasks:{user_id} = {task_id_1, task_id_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 24 小时)

# 全局未完成列表 (Sorted Set, 按时间排序)
global_pending_tasks = {task_id_1: timestamp_1, task_id_2: timestamp_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 24 小时)

# 分布式锁
lock:{resource_name} = "locked"
# 过期时间：LOCK_TIMEOUT_SECONDS (默认 30 秒)
```

### 状态数据结构

```json
{
  "state": "REVIEW_IN_PROGRESS",
  "task_name": "XX 项目",
  "org_id": "org_456",
  "user_id": "user_789",
  "context": {
    "current_round": 3,
    "last_modification": {...}
  },
  "modification_history": [...],
  "last_modified": "2026-03-26T10:30:00+08:00",
  "modification_count": 3
}
```

---

## 🔄 集成示例

### 与 ReviewStateMachine 集成 (Phase 3)

```python
# review_state_machine.py
from review_persistence import ReviewStateManager
from state_machine_integration import StateMachineIntegration

class PersistentReviewStateMachine(ReviewStateMachine):
    def __init__(self, task_id, org_id, user_id):
        super().__init__(task_id, org_id, user_id)
        self.state_manager = ReviewStateManager(task_id, org_id, user_id)
        self.integration = StateMachineIntegration()
        
        # 尝试从 Redis 加载状态
        loaded = self.state_manager.load_state()
        if loaded:
            self.state = DialogState(loaded['state'])
            self.modification_history = loaded['modification_history']
            self.context = loaded['context']
    
    def transition_to(self, new_state):
        super().transition_to(new_state)
        # 保存状态到 Redis
        self.state_manager.save_state(
            state=new_state.value,
            context=self.context,
            modification_history=self.modification_history
        )
        # 同步到状态机集成层
        self.integration.save_state_machine_state(self)
    
    def complete(self):
        super().complete()
        # 清理 Redis 缓存
        self.state_manager.complete_task()
        # 清除状态机集成层
        self.integration.clear_persisted_state(self.task_id)
```

### Agent 启动时恢复 (Phase 4)

```python
# agent_startup.py
from agent_bootstrap import AgentBootstrap

async def on_agent_startup():
    """Agent 启动时扫描未完成的评估单"""
    bootstrap = AgentBootstrap()
    
    # 扫描所有未完成任务
    recovered_states = bootstrap.recover_all_states()
    
    if recovered_states:
        logger.info(f"恢复 {len(recovered_states)} 个未完成的评估单")
        for state in recovered_states:
            logger.info(f"  - {state['task_name']} (用户：{state['user_id']}, 状态：{state['state']})")
    
    return recovered_states
```

### 用户首次对话时主动告知 (Phase 5)

```python
# dialog_handler.py
from notification_handler import NotificationHandler

async def on_user_message(user_id, message):
    """用户发送消息时检查是否有未完成任务"""
    notifier = NotificationHandler()
    
    # 检查是否是会话第一条消息
    if is_first_message_in_session(user_id):
        pending_tasks = notifier.get_user_pending_tasks(user_id)
        
        if pending_tasks:
            response = notifier.format_welcome_back_message(pending_tasks)
            await send_message(user_id, response)
            return WAITING_FOR_SELECTION
    
    # 正常处理消息
    return await process_normal_message(user_id, message)
```

### 并发修改保护 (优化)

```python
# task_modifier.py
from redis_lock import RedisLock

async def modify_task_state(task_id, new_state):
    """修改任务状态 (带锁保护)"""
    lock = RedisLock(f"lock:{task_id}")
    
    if not lock.acquire(timeout=10):
        raise ConcurrentModificationError(f"任务 {task_id} 正在被其他进程修改")
    
    try:
        # 临界区：修改状态
        state_manager = ReviewStateManager(task_id=task_id)
        state_manager.save_state(state=new_state)
        logger.info(f"任务状态已更新：{task_id} -> {new_state}")
    finally:
        lock.release()
```

---

## 🎨 输出格式

### 未完成列表格式

```markdown
欢迎回来！检测到您有 **2 个** 未完成的评估单：

| 序号 | 项目名称 | 当前状态 | 最后修改 | 已修改轮数 |
|-----|---------|---------|---------|-----------|
| 1   | XX 项目  | 等待确认 | 10:30   | 3 轮      |
| 2   | YY 项目  | 审核中   | 昨天    | 1 轮      |

请回复：
- **数字** (如 "1") 选择继续
- **项目名称** (如 "XX 项目") 直接继续
- **忽略** 开始新任务
```

### 主动查询格式

```markdown
当前有 **3 个** 未完成的评估单：

| 序号 | 项目名称 | 当前状态 | 最后修改时间 | 已修改轮数 |
|-----|---------|---------|-------------|-----------|
| 1   | XX 项目  | 等待确认 | 10:30       | 3 轮      |
| 2   | YY 项目  | 审核中   | 昨天 15:20  | 1 轮      |
| 3   | ZZ 项目  | 审核中   | 周一 9:00   | 2 轮      |

请回复序号或项目名称继续
```

### 部署配置检查输出

```markdown
✅ 配置检查通过

Redis 连接：正常
环境变量：完整
TTL 配置：合理
锁配置：已启用

生产环境就绪！
```

---

## 📁 文件结构

```
skills/review-persistence-skill/
├── SKILL.md                          # 本文件
├── _meta.json                        # 技能元数据
└── scripts/
    ├── main.py                       # CLI 入口
    ├── review_persistence.py         # Phase 1-2: 核心持久化
    ├── redis_client.py               # Redis 客户端封装
    ├── state_machine_integration.py  # Phase 3: 状态机集成
    ├── agent_bootstrap.py            # Phase 4: 启动恢复
    ├── notification_handler.py       # Phase 5: 用户通知
    ├── redis_lock.py                 # 优化：分布式锁
    └── deployment_config.py          # 部署：配置检查
```

---

## ⚠️ 注意事项

1. **Redis 依赖** - 本 Skill 依赖 Redis，确保 Redis 服务可用
2. **过期清理** - 状态缓存 1 小时后过期，超时后需从数据库恢复
3. **并发安全** - 生产环境必须使用 Redis 锁防止并发修改
4. **隐私保护** - Redis 中不存储敏感信息 (客户联系方式、合同细节等)
5. **性能优化** - 未完成列表使用缓存，避免频繁查询数据库
6. **通知频率** - 用户通知仅在会话第一条消息时触发，避免打扰

---

## 🧪 测试

### 单元测试

```bash
cd skills/review-persistence-skill
python -m pytest tests/
```

### 集成测试

```bash
# 启动 Redis
docker run -d -p 6379:6379 --name redis redis:latest

# 设置环境变量
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
$env:REDIS_DB="0"
$env:STATE_TTL_SECONDS="3600"
$env:PENDING_LIST_TTL_SECONDS="86400"

# 运行测试
python test_integration.py
```

### CLI 命令测试

```bash
# 使用 uv 运行所有命令 (推荐)
uv run python -m scripts.main save --task-id test_001 --org-id org_test --user-id user_test --state "REVIEW_IN_PROGRESS" --context '{"test": true}'
uv run python -m scripts.main load --task-id test_001
uv run python -m scripts.main list-user --user-id user_test
uv run python -m scripts.main list-global --limit 10
uv run python -m scripts.main recover --task-id test_001
uv run python -m scripts.main lock --resource "test_resource" --timeout 5
uv run python -m scripts.main lock --resource "test_resource" --release
uv run python -m scripts.main deploy-config --check
uv run python -m scripts.main deploy-config --test-connection
```

---

## 📚 相关文件

| 文件 | 说明 |
|-----|------|
| `scripts/main.py` | CLI 主入口 |
| `scripts/review_persistence.py` | Phase 1-2: 核心持久化实现 |
| `scripts/redis_client.py` | Redis 客户端封装 |
| `scripts/state_machine_integration.py` | Phase 3: 状态机集成 |
| `scripts/agent_bootstrap.py` | Phase 4: Agent 启动恢复 |
| `scripts/notification_handler.py` | Phase 5: 用户通知处理 |
| `scripts/redis_lock.py` | 优化：分布式锁实现 |
| `scripts/deployment_config.py` | 部署：配置检查与验证 |
| `tests/` | 测试用例 |

---

## 🔄 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 2.0.0 | 2026-03-26 | Phase 3-5 完整版 + 优化特性 |
| 1.0.0 | 2026-03-26 | 初始版本，支持基础持久化功能 (Phase 1-2) |

---

## 🚀 下一步计划

- [ ] 添加单元测试覆盖所有 Phase
- [ ] 实现 Web 管理界面查看未完成列表
- [ ] 支持多 Redis 实例 (主从/集群)
- [ ] 添加监控指标 (Prometheus/Grafana)
- [ ] 实现自动过期清理任务

---

_专业评估，让工程服务评估有据可依。_