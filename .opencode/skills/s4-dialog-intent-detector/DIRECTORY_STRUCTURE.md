# S4 - DialogIntentDetector 目录结构说明

## 标准目录结构

```
s4-dialog-intent-detector/
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── SKILL.md                  # Skill 使用说明（主文档）
├── README.md                 # 快速入门指南
├── USAGE.md                  # 详细使用文档
├── INTEGRATION.md            # 集成指南
├── COMPLETION_REPORT.md      # 完成报告
├── TEST_REPORT.md            # 测试报告
│
├── scripts/                  # 核心代码目录
│   ├── main.py                            # CLI 入口
│   ├── dialog_intent_detector.py          # 意图识别核心逻辑
│   ├── review_state_machine.py            # 状态机管理
│   └── samples/                           # 测试样本
│       ├── sample-message.json
│       └── sample-output.json
│
├── tests/                    # 测试代码目录
│   ├── test_agent_integration.py   # 集成测试
│   ├── test_agent_quick.py           # 快速测试
│   ├── demo_flow.py                  # 演示流程
│   └── integration_main.py           # 集成测试入口
│
└── references/               # 参考资料目录（预留）
    ├── config.md                    # 配置说明
    ├── intent-keywords.json         # 意图关键词配置
    └── state-transitions.json       # 状态流转表
```

## 文件说明

### 根目录文件

| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量模板（Redis 配置等） |
| `requirements.txt` | Python 依赖列表 |
| `SKILL.md` | **主文档**，包含完整使用说明 |
| `README.md` | 快速入门指南 |
| `USAGE.md` | 详细使用文档 |
| `INTEGRATION.md` | 与其他 Skill 集成指南 |
| `COMPLETION_REPORT.md` | 开发完成报告 |
| `TEST_REPORT.md` | 测试报告 |

### scripts/ 目录

| 文件 | 说明 | 核心功能 |
|------|------|---------|
| `main.py` | **CLI 入口** | 命令行接口，处理 `process_message` / `get_state` / `reset_state` 等操作 |
| `dialog_intent_detector.py` | **意图识别核心** | 识别 MODIFY / READY_TO_CONFIRM / CONFIRM / CANCEL 意图 |
| `review_state_machine.py` | **状态机管理** | 管理 REVIEW_IN_PROGRESS / CONFIRMATION_PENDING / COMPLETED 状态流转 |
| `samples/` | 测试样本 | JSON 格式的测试输入输出样本 |

### tests/ 目录

| 文件 | 说明 |
|------|------|
| `test_agent_integration.py` | 完整集成测试（S4 + S6 + S7 联调） |
| `test_agent_quick.py` | 快速测试（仅测试 S4 核心功能） |
| `demo_flow.py` | 演示流程脚本 |
| `integration_main.py` | 集成测试入口 |

### references/ 目录（预留）

| 文件 | 说明 |
|------|------|
| `config.md` | 配置说明文档 |
| `intent-keywords.json` | 意图关键词配置 |
| `state-transitions.json` | 状态流转表定义 |

## 使用方式

### 运行主程序

```bash
# 处理用户消息
python scripts/main.py --action process_message \
  --message "风险等级调高一点" \
  --task-id "TASK-001" \
  --pretty

# 获取当前状态
python scripts/main.py --action get_state \
  --task-id "TASK-001" \
  --pretty

# 重置状态
python scripts/main.py --action reset_state \
  --task-id "TASK-001" \
  --pretty
```

### 运行测试

```bash
# 快速测试
python tests/test_agent_quick.py

# 集成测试
python tests/test_agent_integration.py

# 演示流程
python tests/demo_flow.py
```

## 清理建议

如遇 `__pycache__` 目录，可安全删除：

```bash
# 删除 Python 缓存
rm -rf scripts/__pycache__
rm -rf tests/__pycache__
rm -rf __pycache__
```

## 版本信息

- **当前版本**: v1.1.0（状态持久化版）
- **最后更新**: 2026-03-26
- **整理完成**: 2026-03-26
