# S7 - ReviewPersistenceSkill 详细设计

> 创建日期：2026-03-26  
> 最后修改：2026-03-26  
> 状态：设计确认（v2.0.0 Phase 3-5 完整版）  
> 所属模块：智能评估 Agent — Skills 层

---

## 目录

1. [Skill 定位与职责](#一skill-定位与职责)
2. [为什么需要独立的评估单状态持久化层](#二为什么需要独立的评估单状态持久化层)
3. [整体定位与设计原则](#三整体定位与设计原则)
4. [已确认设计决策](#四已确认设计决策)
5. [核心能力设计](#五核心能力设计)
6. [Redis 数据结构设计](#六redis-数据结构设计)
7. [环境配置设计](#七环境配置设计)
8. [执行流程设计](#八执行流程设计)
9. [与 S4 / S6 的关系](#九与-s4--s6-的关系)
10. [分布式锁设计](#十分布式锁设计)
11. [对外接口设计](#十一对外接口设计)
12. [开发阶段实现建议](#十二开发阶段实现建议)
13. [工程目录建议](#十三工程目录建议)
14. [伪代码设计](#十四伪代码设计)
15. [测试设计](#十五测试设计)
16. [后续演进预留](#十六后续演进预留)

---

## 一、Skill 定位与职责

| 项目 | 内容 |
|------|------|
| **Skill 名称** | ReviewPersistenceSkill |
| **编号** | S7 |
| **核心职责** | 评估单状态持久化存储与恢复管理，支持进程重启后无缝恢复审核流程 |
| **调用方** | S4 DialogIntentDetector / 上层 Agent 主流程 |
| **实施阶段** | MVP 增强（v1.0.0 基础版，v2.0.0 Phase 3-5 完整版） |
| **输出边界** | **输出状态保存/恢复结果 + 未完成列表 + 用户通知** |
| **持久化介质** | **Redis（内存缓存）+ PostgreSQL（可选，长期存储）** |

### 核心定位

ReviewPersistenceSkill 是智能评估 Agent 中的"**状态持久化层 / 会话恢复层**"，负责在工务人员审核评估单过程中：

- 将审核状态持久化到 Redis
- 支持进程重启后自动恢复状态
- 查询用户未完成的评估单
- 用户首次对话时主动提示未完成任务
- 提供分布式锁防止并发修改

### 核心职责

S7 负责：

1. **Phase 1-2: 基础持久化**
   - 状态持久化到 Redis
   - 状态恢复
   - 未完成列表查询

2. **Phase 3: 深度集成**
   - 与 ReviewStateMachine 深度集成
   - 自动同步状态机状态

3. **Phase 4: 自动恢复**
   - Agent 启动时自动扫描未完成状态
   - 重建状态机实例

4. **Phase 5: 主动通知**
   - 用户首次对话时主动提示未完成任务
   - 支持用户选择继续或开始新任务

5. **优化特性**
   - 分布式锁防止并发修改
   - 部署配置检查与验证

### 职责边界

S7：

- **负责状态持久化**
- **负责状态恢复**
- **负责未完成列表管理**
- **负责分布式锁**

S7 不负责：

- 意图识别（S4）
- 报告内容修改（S6）
- 学习飞轮（S3）
- 业务逻辑判断

---

## 二、为什么需要独立的评估单状态持久化层

### 2.1 生产环境痛点

在工务审核评估单的实际生产场景中，存在以下痛点：

1. **进程重启导致状态丢失**
   - Agent 服务意外重启
   - 开发调试时频繁重启
   - 部署更新导致进程终止

2. **用户中途离开**
   - 审核中途开会/休息
   - 网络中断
   - 同时处理多个评估单

3. **并发修改风险**
   - 多个工务同时修改同一评估单
   - 前后端状态不一致
   - 覆盖他人修改

4. **用户体验差**
   - 重启后必须重新开始
   - 无法查看未完成任务
   - 没有"欢迎回来"提示

### 2.2 为什么不应把持久化逻辑塞进 S4

虽然 S4 管理状态机，但如果把持久化逻辑合并进 S4，会导致：

- S4 职责过重（既要意图识别又要持久化）
- 持久化逻辑与意图识别逻辑耦合
- 难以独立测试持久化可靠性
- 无法灵活调整 Redis Key 设计

因此，S7 必须独立，承担"**状态持久化基础设施**"职责。

### 2.3 为什么选择 Redis

| 方案 | 优点 | 缺点 | 选择理由 |
|------|------|------|---------|
| **Redis** | 读写快、支持 TTL、支持锁 | 内存存储、需持久化配置 | ✅ 适合会话缓存 |
| PostgreSQL | 持久化、支持复杂查询 | 读写慢、无原生 TTL | ❌ 不适合高频会话 |
| 内存 | 最快、无依赖 | 重启丢失 | ❌ 不满足需求 |
| 文件系统 | 简单、持久化 | 并发差、性能低 | ❌ 不适合生产 |

**结论**: Redis + TTL + 持久化配置 是最佳方案。

---

## 三、整体定位与设计原则

### 3.1 在总流程中的位置

```text
S5 ParseRequirementSkill
    ↓
S1 SearchHistoryCasesSkill
    ↓
S2 AssessmentReasoningSkill
    ↓
S6 GenerateReportSkill
    ↓
┌─────────────────────────────────────┐
│ S4 DialogIntentDetector             │
│  - 意图识别                          │
│  - 状态机管理                        │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ S7 ReviewPersistenceSkill           │
│  - 状态持久化 (Redis)                │
│  - 状态恢复                          │
│  - 未完成列表                        │
│  - 用户通知                          │
│  - 分布式锁                          │
└────────────────┬────────────────────┘
                 │
                 ▼
S3 LearningFlywheelSkill
```

### 3.2 三个核心原则

#### 原则 1：透明持久化
S4 调用 S7 保存状态时，不需要关心 Redis 细节，只需传入状态对象。

#### 原则 2：自动恢复
Agent 启动时自动扫描 Redis 中的未完成状态，重建状态机实例。

#### 原则 3：用户无感
用户首次对话时主动提示未完成任务，但不强制继续，可选择忽略。

### 3.3 五阶段实施路线

```
Phase 1-2: 基础持久化
  - 状态保存到 Redis
  - 状态加载
  - 未完成列表查询

Phase 3: 深度集成
  - 与 ReviewStateMachine 集成
  - 自动同步状态

Phase 4: 自动恢复
  - Agent 启动时扫描
  - 重建状态机

Phase 5: 主动通知
  - 用户首次对话提示
  - 支持选择继续

优化：分布式锁
  - Redis 锁
  - 防止并发修改

部署：配置检查
  - 环境变量验证
  - Redis 连接测试
```

---

## 四、已确认设计决策

以下事项已确认，并作为本设计稿的正式约束：

| 编号 | 事项 | 确认结论 |
|------|------|----------|
| 1 | 持久化介质 | **Redis（内存缓存）+ TTL** |
| 2 | 状态 TTL | **3600 秒（1 小时）** |
| 3 | 未完成列表 TTL | **86400 秒（24 小时）** |
| 4 | 分布式锁超时 | **30 秒** |
| 5 | 锁重试延迟 | **100 毫秒** |
| 6 | 用户通知 | **仅在会话第一条消息时触发** |
| 7 | 状态恢复 | **Agent 启动时自动扫描** |
| 8 | 并发保护 | **生产环境必须使用 Redis 锁** |
| 9 | 隐私保护 | **Redis 中不存储敏感信息** |
| 10 | 完成清理 | **审核完成后自动删除 Redis 状态** |

---

## 五、核心能力设计

### 5.1 Phase 1-2: 基础持久化

#### 能力 1: 状态保存

```python
def save_state(task_id, org_id, user_id, state, context, modification_history):
    """
    保存评估单状态到 Redis
    
    Key: review_state:{task_id}
    Value: JSON 对象
    TTL: 3600 秒
    """
    redis_key = f"review_state:{task_id}"
    state_data = {
        "state": state,
        "task_name": context.get("task_name"),
        "org_id": org_id,
        "user_id": user_id,
        "context": context,
        "modification_history": modification_history,
        "last_modified": datetime.now().isoformat(),
        "modification_count": len(modification_history)
    }
    
    redis.setex(redis_key, 3600, json.dumps(state_data, ensure_ascii=False))
    
    # 更新用户未完成列表
    redis.sadd(f"user_pending_tasks:{user_id}", task_id)
    redis.expire(f"user_pending_tasks:{user_id}", 86400)
    
    # 更新全局未完成列表
    redis.zadd("global_pending_tasks", {task_id: time.time()})
    redis.expire("global_pending_tasks", 86400)
```

#### 能力 2: 状态加载

```python
def load_state(task_id):
    """
    从 Redis 加载评估单状态
    
    返回：
    - 成功：状态数据
    - 失败：None（表示状态不存在或已过期）
    """
    redis_key = f"review_state:{task_id}"
    state_data = redis.get(redis_key)
    
    if state_data:
        return json.loads(state_data)
    else:
        return None
```

#### 能力 3: 未完成列表查询

```python
def get_user_pending_tasks(user_id):
    """
    获取用户未完成的评估单列表
    
    返回：
    - 任务列表（含任务名称、状态、最后修改时间）
    """
    task_ids = redis.smembers(f"user_pending_tasks:{user_id}")
    
    pending_tasks = []
    for task_id in task_ids:
        state_data = load_state(task_id)
        if state_data:
            pending_tasks.append({
                "task_id": task_id,
                "task_name": state_data["task_name"],
                "state": state_data["state"],
                "last_modified": state_data["last_modified"],
                "modification_count": state_data["modification_count"]
            })
    
    return sorted(pending_tasks, key=lambda x: x["last_modified"], reverse=True)
```

### 5.2 Phase 3: 深度集成

#### 能力 4: 与 ReviewStateMachine 集成

```python
class PersistentReviewStateMachine(ReviewStateMachine):
    """
    支持持久化的 ReviewStateMachine
    
    特性：
    - 初始化时自动从 Redis 加载状态
    - 状态流转时自动保存到 Redis
    - 完成时自动清理 Redis
    """
    
    def __init__(self, task_id, org_id, user_id):
        super().__init__(task_id, org_id, user_id)
        self.state_manager = ReviewStateManager(task_id, org_id, user_id)
        
        # 尝试从 Redis 加载状态
        loaded = self.state_manager.load_state()
        if loaded:
            self.state = DialogState(loaded['state'])
            self.modification_history = loaded['modification_history']
            self.context = loaded['context']
    
    def transition_to(self, new_state):
        super().transition_to(new_state)
        # 自动保存到 Redis
        self.state_manager.save_state(
            state=new_state.value,
            context=self.context,
            modification_history=self.modification_history
        )
    
    def complete(self):
        super().complete()
        # 自动清理 Redis
        self.state_manager.complete_task()
```

### 5.3 Phase 4: 自动恢复

#### 能力 5: Agent 启动时恢复

```python
def recover_all_states():
    """
    Agent 启动时自动恢复所有未完成状态
    
    步骤：
    1. 扫描 global_pending_tasks
    2. 过滤未过期的 task_id
    3. 加载每个 task_id 的状态
    4. 重建状态机实例
    5. 记录恢复日志
    """
    recovered_count = 0
    recovered_tasks = []
    
    # 扫描全局未完成列表
    task_ids = redis.zrange("global_pending_tasks", 0, -1)
    
    for task_id in task_ids:
        state_data = load_state(task_id)
        if state_data:
            # 重建状态机
            state_machine = PersistentReviewStateMachine(
                task_id=task_id,
                org_id=state_data["org_id"],
                user_id=state_data["user_id"]
            )
            
            recovered_count += 1
            recovered_tasks.append({
                "task_id": task_id,
                "task_name": state_data["task_name"],
                "user_id": state_data["user_id"],
                "state": state_data["state"]
            })
    
    logger.info(f"已恢复 {recovered_count} 个未完成状态")
    return recovered_tasks
```

### 5.4 Phase 5: 主动通知

#### 能力 6: 用户首次对话时提示

```python
def notify_user_with_pending_tasks(user_id):
    """
    用户首次对话时主动提示未完成任务
    
    返回：
    - 格式化消息（Markdown 表格）
    """
    pending_tasks = get_user_pending_tasks(user_id)
    
    if not pending_tasks:
        return None
    
    # 构建 Markdown 消息
    message = f"欢迎回来！检测到您有 **{len(pending_tasks)}** 个未完成的评估单：\n\n"
    message += "| 序号 | 项目名称 | 当前状态 | 最后修改 | 已修改轮数 |\n"
    message += "|-----|---------|---------|---------|-----------|\n"
    
    for i, task in enumerate(pending_tasks, 1):
        last_modified = format_time(task["last_modified"])
        message += f"| {i} | {task['task_name']} | {task['state']} | {last_modified} | {task['modification_count']} 轮 |\n"
    
    message += "\n请回复：\n"
    message += "- **数字** (如 \"1\") 选择继续\n"
    message += "- **项目名称** (如 \"XX 项目\") 直接继续\n"
    message += "- **忽略** 开始新任务"
    
    return message
```

### 5.5 优化：分布式锁

#### 能力 7: Redis 分布式锁

```python
class RedisLock:
    """
    Redis 分布式锁
    
    用途：
    - 防止并发修改同一评估单
    - 确保同一时间只有一个进程修改状态
    """
    
    def __init__(self, resource_name, timeout=30):
        self.lock_key = f"lock:{resource_name}"
        self.timeout = timeout
        self.lock_value = f"{os.getpid()}:{time.time()}"
    
    def acquire(self, retry_delay=0.1):
        """
        获取锁
        
        参数：
        - retry_delay: 重试延迟（秒）
        
        返回：
        - True: 获取成功
        - False: 获取失败（锁已被占用）
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # 尝试设置锁
            if redis.set(self.lock_key, self.lock_value, nx=True, ex=self.timeout):
                return True
            
            # 等待重试
            time.sleep(retry_delay)
        
        return False
    
    def release(self):
        """
        释放锁
        
        注意：
        - 只有锁的持有者才能释放
        - 使用 Lua 脚本保证原子性
        """
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        redis.eval(lua_script, 1, self.lock_key, self.lock_value)
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
```

---

## 六、Redis 数据结构设计

### 6.1 Key 设计

```
# 单个评估单状态（Hash）
review_state:{task_id} = Hash
# 字段：state, task_name, org_id, user_id, context, modification_history, ...
# 过期时间：STATE_TTL_SECONDS (默认 3600 秒)

# 用户未完成列表 (Set)
user_pending_tasks:{user_id} = Set{task_id_1, task_id_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 86400 秒)

# 全局未完成列表 (Sorted Set, 按时间排序)
global_pending_tasks = ZSet{task_id_1: timestamp_1, task_id_2: timestamp_2, ...}
# 过期时间：PENDING_LIST_TTL_SECONDS (默认 86400 秒)

# 分布式锁 (String)
lock:{resource_name} = "locked"
# 过期时间：LOCK_TIMEOUT_SECONDS (默认 30 秒)
```

### 6.2 状态数据结构

```json
{
  "state": "REVIEW_IN_PROGRESS",
  "task_name": "XX 项目",
  "org_id": "ORG-001",
  "user_id": "USER-001",
  "context": {
    "current_round": 3,
    "last_modification": {
      "edit_instruction": "风险等级调高一点",
      "timestamp": "2026-03-26T10:30:00+08:00",
      "modified_fields": ["risk_rows[0].risk_level"]
    }
  },
  "modification_history": [
    {
      "round": 1,
      "timestamp": "2026-03-26T10:30:00+08:00",
      "edit_instruction": "风险等级调高一点",
      "intent": "MODIFY",
      "modified_fields": ["risk_rows[0].risk_level"],
      "before_value": "medium",
      "after_value": "high"
    }
  ],
  "last_modified": "2026-03-26T10:30:00+08:00",
  "modification_count": 1
}
```

### 6.3 索引设计

为了提高查询效率，建议建立以下索引：

```python
# 用户索引（Set）
user_pending_tasks:{user_id}

# 时间索引（Sorted Set）
global_pending_tasks (按 timestamp 排序)

# 组织索引（可选，Set）
org_pending_tasks:{org_id}
```

---

## 七、环境配置设计

### 7.1 必需环境变量

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
NOTIFICATION_CHANNEL=webchat  # 通知渠道 (webchat/email/wechat)
```

### 7.2 生产环境配置建议

```bash
# 生产 Redis 配置
REDIS_HOST=redis-cluster.prod.internal
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_strong_password

# 延长过期时间
STATE_TTL_SECONDS=7200        # 2 小时
PENDING_LIST_TTL_SECONDS=172800  # 48 小时

# 增强锁配置
LOCK_TIMEOUT_SECONDS=60       # 1 分钟
LOCK_RETRY_DELAY_MS=50        # 50 毫秒

# 启用通知
ENABLE_USER_NOTIFICATION=true
NOTIFICATION_CHANNEL=wechat
```

### 7.3 配置检查

```python
def validate_config():
    """
    验证环境配置
    
    返回：
    - issues: 配置问题列表
    """
    issues = []
    
    # 检查必需环境变量
    required_vars = [
        "REDIS_HOST",
        "REDIS_PORT",
        "STATE_TTL_SECONDS",
        "PENDING_LIST_TTL_SECONDS"
    ]
    
    for var in required_vars:
        if var not in os.environ:
            issues.append(f"缺少必需环境变量：{var}")
    
    # 检查 TTL 合理性
    state_ttl = int(os.environ.get("STATE_TTL_SECONDS", 0))
    if state_ttl < 300:
        issues.append(f"STATE_TTL_SECONDS 过小 ({state_ttl}s)，建议 >= 300s")
    
    # 检查 Redis 连接
    if not test_redis_connection():
        issues.append("Redis 连接失败")
    
    return issues
```

---

## 八、执行流程设计

### 8.1 状态保存流程

```text
输入：task_id + org_id + user_id + state + context + modification_history
    ↓
Step 1: 序列化状态数据
    ↓
Step 2: 保存到 review_state:{task_id}
    ↓
Step 3: 设置 TTL = STATE_TTL_SECONDS
    ↓
Step 4: 更新 user_pending_tasks:{user_id}
    ↓
Step 5: 更新 global_pending_tasks
    ↓
输出：保存结果（success / error）
```

### 8.2 状态恢复流程

```text
输入：task_id
    ↓
Step 1: 从 review_state:{task_id} 读取
    ↓
Step 2: 反序列化 JSON
    ↓
Step 3: 重建状态机实例
    ↓
Step 4: 返回状态数据
    ↓
输出：状态数据或 None
```

### 8.3 Agent 启动恢复流程

```text
Agent 启动
    ↓
Step 1: 扫描 global_pending_tasks
    ↓
Step 2: 过滤未过期的 task_id
    ↓
Step 3: 对每个 task_id:
  - 加载 review_state:{task_id}
  - 重建 PersistentReviewStateMachine
  - 记录恢复日志
    ↓
Step 4: 输出恢复统计
    ↓
输出：恢复的任务列表
```

### 8.4 用户通知流程

```text
用户发送第一条消息
    ↓
Step 1: 检查 is_first_message_in_session
    ↓
Step 2: 查询 user_pending_tasks:{user_id}
    ↓
Step 3: 如果有未完成任务:
  - 构建 Markdown 消息
  - 发送给用户
  - 等待用户选择
    ↓
Step 4: 根据用户选择:
  - 数字/项目名称 → 继续该任务
  - 忽略 → 开始新任务
    ↓
输出：用户选择结果
```

### 8.5 并发修改保护流程

```text
请求修改任务状态
    ↓
Step 1: 获取 Redis 锁 lock:{task_id}
    ↓
Step 2: 如果获取失败:
  - 返回错误 "任务正在被其他进程修改"
  - 建议稍后重试
    ↓
Step 3: 如果获取成功:
  - 执行临界区代码（修改状态）
  - 释放锁
    ↓
输出：修改结果
```

---

## 九、与 S4 / S6 的关系

### 与 S4 DialogIntentDetector

S4 负责：
- 意图识别
- 状态机管理
- 修订历史记录

S7 负责：
- 状态持久化
- 状态恢复
- 未完成列表

关系：
- **S7 是 S4 的持久化层**
- **S4 每次交互后自动调用 S7 保存状态**
- **S4 重启后从 S7 恢复状态**

集成示例：

```python
# S4 中集成 S7
class DialogIntentDetector:
    def __init__(self, task_id, org_id, user_id):
        self.state_machine = PersistentReviewStateMachine(task_id, org_id, user_id)
        # PersistentReviewStateMachine 内部已集成 S7
    
    def process_message(self, message):
        # 识别意图
        intent = self.detect_intent(message)
        
        # 状态流转
        self.state_machine.transition_to(new_state)
        # 自动保存到 Redis（通过 PersistentReviewStateMachine）
        
        return {"intent": intent, "state": new_state}
```

### 与 S6 GenerateReportSkill

S6 负责：
- 报告生成
- 报告修改

S7 负责：
- 状态持久化（不关心报告内容）

关系：
- **S7 不直接调用 S6**
- **S6 修改报告后，由 S4 调用 S7 保存状态**
- **S7 只保存状态元数据，不保存报告全文**

---

## 十、分布式锁设计

### 10.1 为什么需要分布式锁

在多进程/多实例部署场景下：

- 同一工务可能在多个浏览器标签页操作
- 多个工务可能同时修改同一评估单（协作场景）
- Agent 服务可能多实例部署（负载均衡）

如果没有分布式锁：

- 并发修改导致状态不一致
- 后提交的覆盖先提交的
- 修订历史记录丢失

### 10.2 Redis 分布式锁实现

```python
class RedisLock:
    """
    基于 Redis 的分布式锁
    
    特性：
    - 互斥性：同一时间只有一个进程持有锁
    - 超时自动释放：防止死锁
    - 原子性：使用 Lua 脚本保证释放锁的原子性
    - 可重入：同一进程可多次获取同一把锁
    """
    
    def __init__(self, resource_name, timeout=30, retry_delay=0.1):
        self.lock_key = f"lock:{resource_name}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.lock_value = f"{os.getpid()}:{threading.get_ident()}:{time.time()}"
        self.acquired = False
    
    def acquire(self):
        """
        获取锁
        
        策略：
        1. 尝试 SETNX
        2. 失败则等待重试
        3. 超时则放弃
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            # 尝试设置锁（NX = Not eXists）
            if redis.set(self.lock_key, self.lock_value, nx=True, ex=self.timeout):
                self.acquired = True
                return True
            
            # 等待重试
            time.sleep(self.retry_delay)
        
        return False
    
    def release(self):
        """
        释放锁
        
        注意：
        - 使用 Lua 脚本保证原子性
        - 只有锁的持有者才能释放
        """
        if not self.acquired:
            return
        
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        redis.eval(lua_script, 1, self.lock_key, self.lock_value)
        self.acquired = False
    
    def __enter__(self):
        if not self.acquire():
            raise LockAcquisitionError(f"无法获取锁：{self.lock_key}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
```

### 10.3 使用示例

```python
# 方式 1: 手动获取/释放
lock = RedisLock(f"task:{task_id}", timeout=30)
if lock.acquire():
    try:
        # 临界区代码
        modify_task_state(task_id, new_state)
    finally:
        lock.release()
else:
    logger.warning(f"无法获取锁，任务 {task_id} 正在被其他进程修改")

# 方式 2: 上下文管理器（推荐）
try:
    with RedisLock(f"task:{task_id}", timeout=30) as lock:
        # 临界区代码
        modify_task_state(task_id, new_state)
except LockAcquisitionError:
    logger.warning(f"无法获取锁，任务 {task_id} 正在被其他进程修改")
```

---

## 十一、对外接口设计

### 11.1 CLI 命令

| 命令 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `save` | task_id + org_id + user_id + state + context | 保存结果 | 保存状态 |
| `load` | task_id | 状态数据 | 加载状态 |
| `delete` | task_id | 删除结果 | 删除状态 |
| `list-user` | user_id | 任务列表 | 用户未完成列表 |
| `list-global` | limit | 任务列表 | 全局未完成列表 |
| `find` | name + user_id | 任务列表 | 按名称搜索 |
| `status` | 无 | 统计信息 | Redis 状态统计 |
| `integrate` | task_id | 集成结果 | 与状态机集成 |
| `recover` | task_id（可选） | 恢复结果 | 恢复状态 |
| `notify` | user_id（可选） | 通知结果 | 用户通知 |
| `lock` | resource + timeout | 锁结果 | 获取/释放锁 |
| `deploy-config` | check/test-connection | 检查结果 | 配置验证 |

### 11.2 Python API

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

---

## 十二、开发阶段实现建议

### 12.1 MVP 优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 基础持久化（Phase 1-2） | 保存/加载/删除 |
| P0 | Redis 客户端封装 | 统一 Redis 操作 |
| P0 | 状态机集成（Phase 3） | PersistentReviewStateMachine |
| P1 | 自动恢复（Phase 4） | Agent 启动时扫描 |
| P1 | 用户通知（Phase 5） | 首次对话提示 |
| P1 | 分布式锁 | 并发保护 |
| P2 | 部署配置检查 | 环境验证 |

### 12.2 实现策略建议

#### 基础持久化
- 使用 Redis Hash 结构
- 设置合理 TTL
- 完成时自动清理

#### 状态机集成
- 继承 ReviewStateMachine
- 重写 transition_to 方法
- 自动保存/清理

#### 自动恢复
- Agent 启动时调用
- 扫描 global_pending_tasks
- 重建状态机实例

#### 用户通知
- 检查会话第一条消息
- 构建 Markdown 消息
- 支持用户选择

---

## 十三、工程目录建议

```text
s7-review-persistence-skill/
├── SKILL.md
├── scripts/
│   ├── main.py                       # CLI 入口
│   ├── review_persistence.py         # Phase 1-2: 核心持久化
│   ├── redis_client.py               # Redis 客户端封装
│   ├── state_machine_integration.py  # Phase 3: 状态机集成
│   ├── agent_bootstrap.py            # Phase 4: 启动恢复
│   ├── notification_handler.py       # Phase 5: 用户通知
│   ├── redis_lock.py                 # 优化：分布式锁
│   └── deployment_config.py          # 部署：配置检查
├── references/
│   ├── config.md
│   ├── env.example
│   └── redis-schema.json
├── samples/
│   ├── sample-save.json
│   └── sample-output.json
└── tests/
    ├── test_review_persistence.py
    ├── test_state_machine_integration.py
    ├── test_agent_bootstrap.py
    └── test_redis_lock.py
```

---

## 十四、伪代码设计

```python
def save_state(task_id, org_id, user_id, state, context, modification_history):
    """保存评估单状态到 Redis"""
    redis_key = f"review_state:{task_id}"
    
    state_data = {
        "state": state,
        "task_name": context.get("task_name"),
        "org_id": org_id,
        "user_id": user_id,
        "context": context,
        "modification_history": modification_history,
        "last_modified": datetime.now().isoformat(),
        "modification_count": len(modification_history)
    }
    
    # 保存到 Redis
    redis.setex(redis_key, 3600, json.dumps(state_data))
    
    # 更新用户未完成列表
    redis.sadd(f"user_pending_tasks:{user_id}", task_id)
    redis.expire(f"user_pending_tasks:{user_id}", 86400)
    
    # 更新全局未完成列表
    redis.zadd("global_pending_tasks", {task_id: time.time()})
    redis.expire("global_pending_tasks", 86400)
    
    return {"success": True, "task_id": task_id}


def load_state(task_id):
    """从 Redis 加载评估单状态"""
    redis_key = f"review_state:{task_id}"
    state_data = redis.get(redis_key)
    
    if state_data:
        return json.loads(state_data)
    else:
        return None


def recover_all_states():
    """Agent 启动时自动恢复所有未完成状态"""
    recovered_tasks = []
    task_ids = redis.zrange("global_pending_tasks", 0, -1)
    
    for task_id in task_ids:
        state_data = load_state(task_id)
        if state_data:
            state_machine = PersistentReviewStateMachine(
                task_id=task_id,
                org_id=state_data["org_id"],
                user_id=state_data["user_id"]
            )
            
            recovered_tasks.append({
                "task_id": task_id,
                "task_name": state_data["task_name"],
                "user_id": state_data["user_id"],
                "state": state_data["state"]
            })
    
    logger.info(f"已恢复 {len(recovered_tasks)} 个未完成状态")
    return recovered_tasks


def notify_user(user_id):
    """用户首次对话时主动提示未完成任务"""
    pending_tasks = get_user_pending_tasks(user_id)
    
    if not pending_tasks:
        return None
    
    message = f"欢迎回来！检测到您有 **{len(pending_tasks)}** 个未完成的评估单：\n\n"
    message += "| 序号 | 项目名称 | 当前状态 | 最后修改 | 已修改轮数 |\n"
    message += "|-----|---------|---------|---------|-----------|\n"
    
    for i, task in enumerate(pending_tasks, 1):
        message += f"| {i} | {task['task_name']} | {task['state']} | {task['last_modified']} | {task['modification_count']} |\n"
    
    message += "\n请回复序号或项目名称继续"
    
    return message
```

---

## 十五、测试设计

### 15.1 测试目标

- 状态保存/加载正确
- 状态恢复可靠
- 未完成列表准确
- 分布式锁有效
- 用户通知正常
- Redis 连接稳定

### 15.2 测试场景

#### 场景 A：基础持久化

```
1. 保存状态 → 成功
2. 加载状态 → 数据一致
3. 删除状态 → Redis 中不存在
预期：CRUD 操作正常
```

#### 场景 B：状态恢复

```
1. 保存状态
2. 模拟进程重启
3. 恢复状态 → 成功
预期：状态、修订历史完整恢复
```

#### 场景 C：未完成列表

```
1. 保存 3 个任务状态
2. 查询用户未完成列表 → 3 个
3. 完成 1 个任务
4. 查询用户未完成列表 → 2 个
预期：列表准确
```

#### 场景 D：分布式锁

```
1. 进程 A 获取锁
2. 进程 B 尝试获取锁 → 失败
3. 进程 A 释放锁
4. 进程 B 获取锁 → 成功
预期：互斥性正常
```

#### 场景 E：用户通知

```
1. 用户有 2 个未完成任务
2. 用户发送第一条消息
3. 返回通知消息 → Markdown 表格
预期：消息格式正确
```

### 15.3 测试检查清单

- [ ] 输出包含 `success`, `data`, `error`
- [ ] 状态保存/加载正常
- [ ] 状态恢复正常
- [ ] 未完成列表准确
- [ ] 分布式锁有效
- [ ] 用户通知正常
- [ ] Redis 连接稳定
- [ ] 中文正常显示，无乱码

---

## 十六、后续演进预留

### 16.1 第二期增强

- PostgreSQL 长期存储
- Web 管理界面
- 监控指标（Prometheus/Grafana）
- 自动过期清理任务

### 16.2 第三期增强

- 多 Redis 实例支持（主从/集群）
- 跨地域灾备
- 审计日志
- 性能优化（批量操作/管道）

### 16.3 长期方向

- 形成完整的会话管理体系
- 支持更多持久化场景
- 与工务审核流程深度集成

---

*文档持续更新中，最后修改：2026-03-26*
