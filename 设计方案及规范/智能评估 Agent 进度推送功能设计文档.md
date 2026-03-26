# 智能评估 Agent 进度推送功能设计文档

> **版本**: v1.0.0  
> **创建日期**: 2026-03-26  
> **状态**: 设计完成，待实施  
> **负责人**: 09okjk

---

## 📋 目录

1. [背景与目标](#一背景与目标)
2. [需求分析](#二需求分析)
3. [整体架构设计](#三整体架构设计)
4. [模块详细设计](#四模块详细设计)
5. [接口定义](#五接口定义)
6. [数据流设计](#六数据流设计)
7. [配置设计](#七配置设计)
8. [实施计划](#八实施计划)
9. [测试方案](#九测试方案)
10. [部署指南](#十部署指南)
11. [风险与应对](#十一风险与应对)

---

## 一、背景与目标

### 1.1 背景

当前智能评估 Agent 执行完整流程需要 **8-22 秒**，用户在等待过程中没有任何反馈，导致：
- ❌ 用户不知道任务是否在执行
- ❌ 无法预估等待时间
- ❌ 可能重复提交或放弃等待
- ❌ 用户体验差

### 1.2 目标

实现**流式进度推送 + 精简通知**机制，让用户：
- ✅ 实时了解处理进度
- ✅ 减少等待焦虑
- ✅ 早期发现问题
- ✅ 提升整体体验

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **最小打扰** | 只推送关键节点（4-5 次），不过度干扰 |
| **即时响应** | 收到请求后 1 秒内响应 |
| **可配置** | 支持开启/关闭，支持渠道选择 |
| **可降级** | 推送失败不影响主流程 |
| **可观测** | 完整的日志和监控 |

---

## 二、需求分析

### 2.1 功能需求

| 编号 | 需求 | 优先级 |
|------|------|--------|
| FR-001 | 支持 4 个关键节点进度推送 | P0 |
| FR-002 | 支持配置开启/关闭进度推送 | P0 |
| FR-003 | 支持多种推送渠道（控制台/文件/API） | P1 |
| FR-004 | 推送失败不影响主流程 | P1 |
| FR-005 | 支持任务超时通知 | P1 |
| FR-006 | 支持错误信息推送 | P1 |
| FR-007 | 支持预计剩余时间显示 | P2 |
| FR-008 | 支持用户取消任务 | P2 |

### 2.2 非功能需求

| 编号 | 需求 | 指标 |
|------|------|------|
| NFR-001 | 推送延迟 | < 500ms |
| NFR-002 | 推送成功率 | > 99% |
| NFR-003 | 系统可用性 | > 99.9% |
| NFR-004 | 并发支持 | 支持 100 并发任务 |
| NFR-005 | 消息不丢失 | 至少一次投递 |

### 2.3 用户故事

```
作为 评估人员
我希望 在处理过程中看到进度反馈
以便于 知道任务是否正常执行，减少等待焦虑

作为 系统管理员
我希望 可以配置进度推送的开关和渠道
以便于 根据不同环境调整策略

作为 开发者
我希望 进度推送模块解耦且可降级
以便于 维护和故障排查
```

---

## 三、整体架构设计

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面层                              │
│  (对话界面 / Web 界面 / API 客户端)                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 Agent 编排层 (新增)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ProgressTracker (进度追踪器)                      │  │
│  │  - 管理任务状态                                    │  │
│  │  - 计算进度百分比                                  │  │
│  │  - 触发推送事件                                    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 进度推送层 (新增)                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  ProgressNotifier (进度推送器)                     │  │
│  │  - 格式化推送消息                                  │  │
│  │  - 选择推送渠道                                    │  │
│  │  - 处理推送失败                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                            ↓                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
│  │ Console │  │  File   │  │   API   │  推送渠道       │
│  │ Channel │  │ Channel │  │ Channel │                 │
│  └─────────┘  └─────────┘  └─────────┘                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Skill 执行层 (现有)                       │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐               │
│  │  S5  │→ │  S1  │→ │  S2  │→ │  S6  │               │
│  │解析  │  │检索  │  │推理  │  │生成  │               │
│  └──────┘  └──────┘  └──────┘  └──────┘               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  数据存储层 (可选)                         │
│  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Redis         │  │   PostgreSQL    │              │
│  │   (进度缓存)    │  │   (任务历史)    │              │
│  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 3.2 模块划分

| 模块 | 职责 | 新增/现有 |
|------|------|----------|
| **Agent 编排器** | 编排 Skill 执行 + 触发进度推送 | 🆕 新增 |
| **ProgressTracker** | 追踪任务进度状态 | 🆕 新增 |
| **ProgressNotifier** | 执行推送操作 | 🆕 新增 |
| **Channels** | 具体推送渠道实现 | 🆕 新增 |
| **Config** | 配置管理 | 🆕 新增 |
| **Skills** | S5/S1/S2/S6 | ✅ 现有（微调） |

### 3.3 技术选型

| 组件 | 技术选择 | 理由 |
|------|---------|------|
| 异步框架 | `asyncio` | Python 原生支持，轻量 |
| 进度存储 | Redis (可选) | 高性能，支持 TTL |
| 配置管理 | 环境变量 + YAML | 灵活，易部署 |
| 日志 | `logging` | Python 标准库 |
| 监控 | Prometheus (可选) | 业界标准 |

---

## 四、模块详细设计

### 4.1 ProgressTracker（进度追踪器）

**文件**: `agent/progress_tracker.py`

**职责**:
- 管理任务生命周期
- 计算进度百分比
- 触发推送事件

**类设计**:

```python
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProgressStage(Enum):
    START = "start"
    S5_COMPLETE = "s5_complete"
    S1_COMPLETE = "s1_complete"
    S2_COMPLETE = "s2_complete"
    S6_COMPLETE = "s6_complete"

class ProgressTracker:
    def __init__(self, task_id: str, user_id: str, notifier: ProgressNotifier):
        self.task_id = task_id
        self.user_id = user_id
        self.notifier = notifier
        self.status = TaskStatus.PENDING
        self.current_stage = None
        self.progress_percent = 0
        self.start_time = None
        self.end_time = None
    
    async def start(self):
        """任务开始"""
        self.status = TaskStatus.PROCESSING
        self.start_time = datetime.now()
        self.current_stage = ProgressStage.START
        self.progress_percent = 0
        await self.notifier.send(self.user_id, "📋 已收到需求，开始处理...")
    
    async def on_stage_complete(self, stage: ProgressStage, **context):
        """阶段完成"""
        self.current_stage = stage
        self.progress_percent = self._calculate_progress(stage)
        message = self._format_message(stage, context)
        await self.notifier.send(self.user_id, message)
    
    def _calculate_progress(self, stage: ProgressStage) -> int:
        """计算进度百分比"""
        progress_map = {
            ProgressStage.START: 0,
            ProgressStage.S5_COMPLETE: 25,
            ProgressStage.S1_COMPLETE: 50,
            ProgressStage.S2_COMPLETE: 75,
            ProgressStage.S6_COMPLETE: 100,
        }
        return progress_map.get(stage, 0)
    
    def _format_message(self, stage: ProgressStage, context: dict) -> str:
        """格式化推送消息"""
        templates = {
            ProgressStage.S5_COMPLETE: "✅ 需求解析完成，识别出 {requirement_count} 个服务项",
            ProgressStage.S1_COMPLETE: "🔍 已检索到 {case_count} 个相似历史案例",
            ProgressStage.S2_COMPLETE: "🧠 评估推理完成，识别到 {risk_count} 个风险项",
            ProgressStage.S6_COMPLETE: "📄 评估报告已生成",
        }
        template = templates.get(stage, "")
        return template.format(**context)
    
    async def on_success(self, result: Any):
        """任务成功完成"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.now()
        await self.on_stage_complete(ProgressStage.S6_COMPLETE)
    
    async def on_error(self, error: Exception):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        await self.notifier.send(
            self.user_id,
            f"❌ 处理失败：{str(error)} (耗时 {elapsed:.1f}秒)"
        )
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() if self.start_time else 0
```

---

### 4.2 ProgressNotifier（进度推送器）

**文件**: `agent/progress_notifier.py`

**职责**:
- 管理推送渠道
- 执行推送操作
- 处理推送失败

**类设计**:

```python
class PushChannel(ABC):
    """推送渠道基类"""
    
    @abstractmethod
    async def send(self, user_id: str, message: str) -> bool:
        """发送消息"""
        pass

class ConsoleChannel(PushChannel):
    """控制台渠道"""
    
    async def send(self, user_id: str, message: str) -> bool:
        print(f"[{user_id}] [{datetime.now().strftime('%H:%M:%S')}] {message}")
        return True

class FileChannel(PushChannel):
    """文件渠道"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    async def send(self, user_id: str, message: str) -> bool:
        try:
            with open(self.filepath, 'a', encoding='utf-8') as f:
                f.write(f"[{user_id}] [{datetime.now().isoformat()}] {message}\n")
            return True
        except Exception as e:
            logging.error(f"File channel error: {e}")
            return False

class APIChannel(PushChannel):
    """API 渠道"""
    
    def __init__(self, webhook_url: str, api_key: str = None):
        self.webhook_url = webhook_url
        self.api_key = api_key
    
    async def send(self, user_id: str, message: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "user_id": user_id,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                async with session.post(self.webhook_url, json=payload, headers=headers) as resp:
                    return resp.status == 200
        except Exception as e:
            logging.error(f"API channel error: {e}")
            return False

class ProgressNotifier:
    """进度推送器"""
    
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", True)
        self.channels = self._init_channels(config)
        self.retry_count = config.get("retry_count", 3)
        self.timeout = config.get("timeout", 5)  # 秒
    
    def _init_channels(self, config: dict) -> List[PushChannel]:
        """初始化推送渠道"""
        channels = []
        channel_types = config.get("channels", ["console"])
        
        for channel_type in channel_types:
            if channel_type == "console":
                channels.append(ConsoleChannel())
            elif channel_type == "file":
                channels.append(FileChannel(config.get("file_path", "progress.log")))
            elif channel_type == "api":
                channels.append(APIChannel(
                    config.get("webhook_url"),
                    config.get("api_key")
                ))
        
        return channels
    
    async def send(self, user_id: str, message: str) -> bool:
        """发送推送消息"""
        if not self.enabled:
            return False
        
        success = False
        for i in range(self.retry_count):
            for channel in self.channels:
                try:
                    result = await asyncio.wait_for(
                        channel.send(user_id, message),
                        timeout=self.timeout
                    )
                    if result:
                        success = True
                except asyncio.TimeoutError:
                    logging.warning(f"Channel timeout after {self.timeout}s")
                except Exception as e:
                    logging.error(f"Channel error: {e}")
            
            if success:
                break
            
            if i < self.retry_count - 1:
                await asyncio.sleep(0.5 * (i + 1))  # 递增延迟
        
        return success
```

---

### 4.3 Agent 编排器

**文件**: `agent/main.py`

**职责**:
- 编排 Skill 执行
- 集成进度推送
- 异常处理

**核心逻辑**:

```python
class AssessmentAgent:
    """智能评估 Agent"""
    
    def __init__(self, config: dict):
        self.config = config
        self.notifier = ProgressNotifier(config.get("progress", {}))
        self.skill_runner = SkillRunner(config)
    
    async def assess(self, email_text: str, user_id: str) -> dict:
        """完整评估流程"""
        task_id = self._generate_task_id()
        tracker = ProgressTracker(task_id, user_id, self.notifier)
        
        try:
            # 开始任务
            await tracker.start()
            
            # S5: 需求解析
            s5_result = await self.skill_runner.run(
                "parse-requirement-skill",
                {"action": "parse", "input": email_text}
            )
            await tracker.on_stage_complete(
                ProgressStage.S5_COMPLETE,
                requirement_count=len(s5_result['data']['requirements'])
            )
            
            # S1: 历史检索
            s1_result = await self.skill_runner.run(
                "search-history-cases-skill",
                {"requirement": s5_result['data']['requirements'][0]}
            )
            await tracker.on_stage_complete(
                ProgressStage.S1_COMPLETE,
                case_count=len(s1_result['data']['cases'])
            )
            
            # S2: 评估推理
            s2_result = await self.skill_runner.run(
                "assessment-reasoning-skill",
                {
                    "action": "reason_assessment",
                    "requirement": s5_result['data']['requirements'][0],
                    "history_cases": s1_result['data']['cases']
                }
            )
            await tracker.on_stage_complete(
                ProgressStage.S2_COMPLETE,
                risk_count=len(s2_result['data']['risk_results'])
            )
            
            # S6: 报告生成
            s6_result = await self.skill_runner.run(
                "generate-report-skill",
                {
                    "action": "generate_report",
                    "requirement": s5_result['data']['requirements'][0],
                    "history_cases": s1_result['data']['cases'],
                    "assessment_result": s2_result['data']
                }
            )
            await tracker.on_success(s6_result)
            
            return s6_result
            
        except Exception as e:
            await tracker.on_error(e)
            raise
```

---

## 五、接口定义

### 5.1 对外接口

#### 评估接口（带进度推送）

```python
async def assess_with_progress(
    email_text: str,
    user_id: str,
    enable_progress: bool = True
) -> dict:
    """
    执行评估并推送进度
    
    Args:
        email_text: 客户原始邮件
        user_id: 用户 ID
        enable_progress: 是否启用进度推送
    
    Returns:
        评估报告
    """
```

#### 查询进度接口

```python
async def get_task_progress(task_id: str) -> dict:
    """
    查询任务进度
    
    Returns:
        {
            "task_id": "TASK-001",
            "status": "processing",
            "progress": 50,
            "current_stage": "s1_complete",
            "message": "已检索到 5 个相似历史案例",
            "elapsed_time": 5.2
        }
    """
```

#### 取消任务接口

```python
async def cancel_task(task_id: str) -> bool:
    """
    取消任务
    
    Returns:
        是否成功取消
    """
```

### 5.2 配置接口

```python
class ProgressConfig(BaseModel):
    """进度推送配置"""
    enabled: bool = True
    channels: List[str] = ["console"]
    file_path: str = "progress.log"
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    retry_count: int = 3
    timeout: int = 5  # 秒
```

---

## 六、数据流设计

### 6.1 正常流程数据流

```
用户请求
    ↓
[Agent] assess_with_progress(email, user_id)
    ↓
[Tracker] start() → 推送 "📋 已收到需求..."
    ↓
[S5] parse_requirement()
    ↓
[Tracker] on_stage_complete(S5) → 推送 "✅ 解析完成..."
    ↓
[S1] search_history()
    ↓
[Tracker] on_stage_complete(S1) → 推送 "🔍 检索到案例..."
    ↓
[S2] assess_reasoning()
    ↓
[Tracker] on_stage_complete(S2) → 推送 "🧠 推理完成..."
    ↓
[S6] generate_report()
    ↓
[Tracker] on_success() → 推送 "📄 报告已生成"
    ↓
返回完整报告
```

### 6.2 异常流程数据流

```
用户请求
    ↓
[Agent] assess_with_progress(email, user_id)
    ↓
[Tracker] start()
    ↓
[S5] parse_requirement() → 异常！
    ↓
[Tracker] on_error(exception)
    ↓
推送 "❌ 处理失败：{错误信息}"
    ↓
抛出异常
```

### 6.3 数据结构

```python
# 任务状态
{
    "task_id": "TASK-20260326-001",
    "user_id": "USER-001",
    "status": "processing",  # pending/processing/completed/failed/cancelled
    "current_stage": "s1_complete",
    "progress_percent": 50,
    "start_time": "2026-03-26T10:00:00Z",
    "end_time": None,
    "elapsed_seconds": 5.2,
    "last_message": "已检索到 5 个相似历史案例"
}

# 推送消息
{
    "task_id": "TASK-20260326-001",
    "user_id": "USER-001",
    "stage": "s1_complete",
    "message": "🔍 已检索到 5 个相似历史案例",
    "timestamp": "2026-03-26T10:00:05Z",
    "progress_percent": 50
}
```

---

## 七、配置设计

### 7.1 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `PROGRESS_ENABLED` | 是否启用进度推送 | `true` | `true`/`false` |
| `PROGRESS_CHANNELS` | 推送渠道（逗号分隔） | `console` | `console,file,api` |
| `PROGRESS_FILE_PATH` | 文件渠道输出路径 | `progress.log` | `/var/log/progress.log` |
| `PROGRESS_WEBHOOK_URL` | API 渠道 Webhook URL | - | `https://api.example.com/notify` |
| `PROGRESS_API_KEY` | API 渠道认证密钥 | - | `sk-xxx` |
| `PROGRESS_RETRY_COUNT` | 推送重试次数 | `3` | `3` |
| `PROGRESS_TIMEOUT` | 推送超时（秒） | `5` | `5` |
| `PROGRESS_STORE_REDIS` | 是否使用 Redis 存储进度 | `false` | `true`/`false` |
| `REDIS_HOST` | Redis 主机 | `localhost` | `192.168.1.100` |
| `REDIS_PORT` | Redis 端口 | `6379` | `6379` |

### 7.2 YAML 配置文件

**文件**: `agent/config/progress_config.yaml`

```yaml
progress:
  enabled: true
  
  # 推送渠道
  channels:
    - type: console
      enabled: true
    - type: file
      enabled: true
      path: /var/log/assessment/progress.log
    - type: api
      enabled: false
      webhook_url: https://api.example.com/notify
      api_key: ${PROGRESS_API_KEY}
  
  # 重试配置
  retry:
    count: 3
    delay: 0.5  # 秒
    timeout: 5  # 秒
  
  # 存储配置（可选）
  storage:
    type: redis  # 或 memory
    redis:
      host: localhost
      port: 6379
      db: 0
      ttl: 3600  # 1 小时
  
  # 消息模板
  templates:
    start: "📋 已收到需求，开始处理..."
    s5_complete: "✅ 需求解析完成，识别出 {requirement_count} 个服务项"
    s1_complete: "🔍 已检索到 {case_count} 个相似历史案例"
    s2_complete: "🧠 评估推理完成，识别到 {risk_count} 个风险项"
    s6_complete: "📄 评估报告已生成"
    error: "❌ 处理失败：{error} (耗时 {elapsed:.1f}秒)"
```

---

## 八、实施计划

### 8.1 阶段划分

| 阶段 | 内容 | 工时 | 优先级 |
|------|------|------|--------|
| **Phase 1** | MVP - 基础推送功能 | 4 小时 | P0 |
| **Phase 2** | 多渠道支持 + 配置系统 | 4 小时 | P1 |
| **Phase 3** | Redis 存储 + 进度查询 | 4 小时 | P1 |
| **Phase 4** | 监控 + 日志 + 测试 | 4 小时 | P2 |

### 8.2 Phase 1: MVP（4 小时）

**目标**: 实现基础推送功能，支持控制台渠道

**任务**:
- [ ] 创建 `progress_notifier.py`（50 行）
- [ ] 创建 `progress_tracker.py`（100 行）
- [ ] 创建简单编排脚本 `assess_with_progress.py`（100 行）
- [ ] 测试端到端流程
- [ ] 编写 MVP 文档

**交付物**:
- ✅ 可运行的进度推送功能
- ✅ 控制台输出进度
- ✅ 基础测试用例

### 8.3 Phase 2: 多渠道（4 小时）

**目标**: 支持文件/API 渠道，完善配置系统

**任务**:
- [ ] 实现 `FileChannel`
- [ ] 实现 `APIChannel`
- [ ] 创建配置管理系统
- [ ] 支持环境变量配置
- [ ] 支持 YAML 配置
- [ ] 编写配置文档

**交付物**:
- ✅ 3 种推送渠道
- ✅ 灵活的配置系统
- ✅ 配置示例

### 8.4 Phase 3: 持久化（4 小时）

**目标**: Redis 存储进度，支持进度查询

**任务**:
- [ ] 实现 Redis 存储
- [ ] 创建进度查询接口
- [ ] 实现任务取消功能
- [ ] 添加 TTL 自动过期
- [ ] 编写 API 文档

**交付物**:
- ✅ 进度持久化
- ✅ 进度查询 API
- ✅ 任务取消 API

### 8.5 Phase 4: 生产化（4 小时）

**目标**: 监控、日志、测试、部署

**任务**:
- [ ] 完善日志系统
- [ ] 添加 Prometheus 指标
- [ ] 编写单元测试（覆盖率>80%）
- [ ] 编写集成测试
- [ ] 编写部署文档
- [ ] 性能测试

**交付物**:
- ✅ 完整的测试套件
- ✅ 监控指标
- ✅ 部署文档

---

## 九、测试方案

### 9.1 单元测试

```python
# test_progress_tracker.py
class TestProgressTracker(unittest.TestCase):
    
    def test_start(self):
        tracker = ProgressTracker("TASK-001", "USER-001", mock_notifier)
        await tracker.start()
        self.assertEqual(tracker.status, TaskStatus.PROCESSING)
        self.assertEqual(tracker.progress_percent, 0)
    
    def test_on_stage_complete(self):
        tracker = ProgressTracker("TASK-001", "USER-001", mock_notifier)
        await tracker.on_stage_complete(ProgressStage.S5_COMPLETE, requirement_count=2)
        self.assertEqual(tracker.progress_percent, 25)
    
    def test_on_error(self):
        tracker = ProgressTracker("TASK-001", "USER-001", mock_notifier)
        await tracker.on_error(ValueError("Test error"))
        self.assertEqual(tracker.status, TaskStatus.FAILED)
```

### 9.2 集成测试

```python
# test_integration.py
class TestEndToEnd(unittest.TestCase):
    
    async def test_assess_with_progress(self):
        agent = AssessmentAgent(test_config)
        result = await agent.assess(test_email, "USER-001")
        
        # 验证推送了 5 次
        self.assertEqual(mock_notifier.send_count, 5)
        
        # 验证报告生成
        self.assertIn("summary", result['data'])
```

### 9.3 性能测试

```python
# test_performance.py
async def test_concurrent_tasks():
    """测试 100 并发任务"""
    tasks = [
        agent.assess(test_email, f"USER-{i}")
        for i in range(100)
    ]
    
    start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    
    # 所有任务应在 30 秒内完成
    assert elapsed < 30
    assert len(results) == 100
```

---

## 十、部署指南

### 10.1 环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| Python | 3.8+ | 3.10+ |
| Redis (可选) | 5.0+ | 6.0+ |
| 内存 | 512MB | 2GB |
| 磁盘 | 100MB | 1GB |

### 10.2 安装步骤

```bash
# 1. 克隆代码
git clone <repo>
cd PingGu/.opencode/skills/agent

# 2. 创建虚拟环境
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
uv pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 配置

# 5. 测试运行
python main.py --test
```

### 10.3 Docker 部署（可选）

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  agent:
    build: .
    environment:
      - PROGRESS_ENABLED=true
      - PROGRESS_CHANNELS=console,file
    volumes:
      - ./logs:/var/log/assessment
  
  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
```

---

## 十一、风险与应对

### 11.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 推送延迟影响主流程 | 中 | 高 | 异步推送 + 超时控制 |
| Redis 不可用 | 低 | 中 | 降级到内存存储 |
| 推送渠道失败 | 中 | 低 | 多渠道路由 + 重试 |
| 并发过高导致性能下降 | 中 | 中 | 限流 + 队列 |

### 11.2 运维风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 日志文件过大 | 高 | 低 | 日志轮转 + 清理策略 |
| 配置错误导致推送失败 | 中 | 中 | 配置验证 + 默认值 |
| 监控缺失 | 中 | 高 | Prometheus 指标 + 告警 |

### 11.3 用户体验风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 推送过于频繁 | 中 | 中 | 精简推送点（4-5 次） |
| 推送消息不清晰 | 低 | 中 | 消息模板审核 + 测试 |
| 用户无法关闭推送 | 低 | 低 | 提供配置开关 |

---

## 附录

### A. 文件清单

```
.opencode/skills/
├── agent/                          # 🆕 新增
│   ├── __init__.py
│   ├── main.py                     # Agent 主入口
│   ├── progress_tracker.py         # 进度追踪器
│   ├── progress_notifier.py        # 进度推送器
│   ├── channels.py                 # 推送渠道
│   ├── config.py                   # 配置管理
│   ├── skill_runner.py             # Skill 执行器
│   └── config/
│       ├── progress_config.yaml    # 推送配置
│       └── agent_config.yaml       # Agent 配置
│
├── docs/
│   └── PROGRESS_NOTIFICATION_GUIDE.md  # 使用指南
│
└── tests/
    ├── test_progress_tracker.py
    ├── test_progress_notifier.py
    └── test_integration.py
```

### B. 依赖清单

```txt
# requirements.txt
asyncio-mqtt>=0.16.0
aiohttp>=3.8.0
redis>=4.5.0
pyyaml>=6.0
pydantic>=1.10.0
prometheus-client>=0.16.0
```

### C. 变更日志

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0.0 | 2026-03-26 | 初始设计完成 |

---

**文档结束**
