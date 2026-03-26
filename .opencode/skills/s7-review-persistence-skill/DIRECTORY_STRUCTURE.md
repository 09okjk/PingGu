# S7 - ReviewPersistenceSkill 目录结构说明

## 标准目录结构

```
s7-review-persistence-skill/
├── .env                      # 环境变量配置（本地开发用）
├── .env.example              # 环境变量模板
├── .gitignore                # Git 忽略配置
├── _meta.json                # Skill 元数据
├── requirements.txt          # Python 依赖
├── SKILL.md                  # Skill 使用说明（主文档）
├── README.md                 # 快速入门指南
│
├── scripts/                  # 核心代码目录
│   ├── main.py                            # CLI 入口
│   ├── review_persistence.py              # Phase 1-2: 核心持久化
│   ├── redis_client.py                    # Redis 客户端封装
│   ├── state_machine_integration.py       # Phase 3: 状态机集成
│   ├── agent_bootstrap.py                 # Phase 4: 启动恢复
│   ├── notification_handler.py            # Phase 5: 用户通知
│   ├── redis_lock.py                      # 优化：分布式锁
│   └── deployment_config.py               # 部署：配置检查
│
├── tests/                    # 测试代码目录
│   └── integration_example.py       # 集成测试示例
│
└── references/               # 参考资料目录（预留）
    ├── config.md                    # 配置说明
    ├── env.example                  # 环境变量模板
    └── redis-schema.json            # Redis 数据结构定义
```

## 文件说明

### 根目录文件

| 文件 | 说明 |
|------|------|
| `.env` | 本地开发环境变量配置 |
| `.env.example` | 环境变量模板（Redis 配置等） |
| `.gitignore` | Git 忽略配置 |
| `_meta.json` | Skill 元数据（版本、作者等） |
| `requirements.txt` | Python 依赖列表 |
| `SKILL.md` | **主文档**，包含完整使用说明 |
| `README.md` | 快速入门指南 |

### scripts/ 目录

| 文件 | 说明 | 对应 Phase |
|------|------|-----------|
| `main.py` | **CLI 入口** | 全部 Phase |
| `review_persistence.py` | **核心持久化逻辑** | Phase 1-2 |
| `redis_client.py` | Redis 客户端封装 | Phase 1-2 |
| `state_machine_integration.py` | 状态机集成 | Phase 3 |
| `agent_bootstrap.py` | Agent 启动恢复 | Phase 4 |
| `notification_handler.py` | 用户通知处理 | Phase 5 |
| `redis_lock.py` | 分布式锁实现 | 优化特性 |
| `deployment_config.py` | 部署配置检查 | 部署支持 |

### tests/ 目录

| 文件 | 说明 |
|------|------|
| `integration_example.py` | 集成测试示例 |

### references/ 目录（预留）

| 文件 | 说明 |
|------|------|
| `config.md` | 配置说明文档 |
| `env.example` | 环境变量模板 |
| `redis-schema.json` | Redis 数据结构定义 |

## 使用方式

### CLI 命令

```bash
# 保存状态
python scripts/main.py save \
  --task-id task_123 \
  --org-id org_456 \
  --user-id user_789 \
  --state "REVIEW_IN_PROGRESS" \
  --context '{"current_round": 3}'

# 加载状态
python scripts/main.py load \
  --task-id task_123

# 删除状态
python scripts/main.py delete \
  --task-id task_123

# 查询用户未完成任务
python scripts/main.py list-user \
  --user-id user_789

# 查询全局未完成任务
python scripts/main.py list-global \
  --limit 50

# 恢复状态
python scripts/main.py recover \
  --task-id task_123

# 用户通知
python scripts/main.py notify \
  --user-id user_789

# 获取/释放锁
python scripts/main.py lock \
  --resource "task_123" \
  --timeout 10

python scripts/main.py lock \
  --resource "task_123" \
  --release

# 部署配置检查
python scripts/main.py deploy-config \
  --check

python scripts/main.py deploy-config \
  --test-connection
```

### Python API

```python
# 基础持久化
from review_persistence import ReviewStateManager

state_manager = ReviewStateManager(task_id, org_id, user_id)
state_manager.save_state(state, context, modification_history)
loaded = state_manager.load_state()
state_manager.complete_task()

# 状态机集成
from state_machine_integration import StateMachineIntegration

integration = StateMachineIntegration()
integration.sync_state_machine_state(task_id)

# 自动恢复
from agent_bootstrap import AgentBootstrap

bootstrap = AgentBootstrap()
recovered = bootstrap.recover_all_states()

# 用户通知
from notification_handler import NotificationHandler

notifier = NotificationHandler()
message = notifier.notify_user_with_pending_tasks(user_id)

# 分布式锁
from redis_lock import RedisLock

with RedisLock(f"task:{task_id}", timeout=30):
    modify_task_state()
```

## 运行测试

```bash
# 运行集成测试示例
python tests/integration_example.py

# 运行单元测试（待实现）
python -m pytest tests/
```

## 环境配置

编辑 `.env` 文件：

```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 过期时间配置
STATE_TTL_SECONDS=3600
PENDING_LIST_TTL_SECONDS=86400

# 锁配置
LOCK_TIMEOUT_SECONDS=30
LOCK_RETRY_DELAY_MS=100

# 通知配置
ENABLE_USER_NOTIFICATION=true
NOTIFICATION_CHANNEL=webchat
```

## 清理建议

如遇 `__pycache__` 或 `.venv` 目录，可安全删除：

```bash
# 删除 Python 缓存
rm -rf scripts/__pycache__
rm -rf tests/__pycache__
rm -rf __pycache__

# 删除虚拟环境（可选）
rm -rf .venv
```

## 版本信息

- **当前版本**: v2.0.0（Phase 3-5 完整版）
- **最后更新**: 2026-03-26
- **整理完成**: 2026-03-26
