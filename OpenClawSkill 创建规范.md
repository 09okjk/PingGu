# OpenClaw Skill 创建规范 🛠️

## 📁 核心目录结构

```
my-skill/
├── SKILL.md              # 【必需】技能定义文件
├── _meta.json            # 【可选】元数据（版本、作者等）
├── .env.example          # 【可选】环境变量示例
├── .gitignore            # 【可选】Git 忽略规则
├── README.md             # 【可选】使用说明
├── scripts/              # 【可选】脚本目录
│   ├── main.mjs          # 主脚本（Node.js）
│   └── helper.py         # 辅助脚本（Python 等）
└── references/           # 【可选】参考资料目录
    └── config.md         # 配置说明
```

---

## 📄 SKILL.md 格式（核心文件）

### 1. Front Matter（YAML 头部）

```yaml
---
name: 技能名称
slug: 技能标识符（小写，连字符分隔）
version: 1.0.0
homepage: https://...
description: 一句话描述技能的用途
changelog: 更新日志（可选）
metadata:
  clawdbot:
    emoji: 🎯
    requires:
      bins: ["node", "curl"]  # 需要的命令行工具
      env: ["API_KEY"]        # 需要的环境变量
    os: ["linux", "darwin", "win32"]  # 支持的操作系统
---
```

### 2. 正文内容（Markdown）

```markdown
# 技能名称

简短介绍。

## When to Use（何时使用）

✅ 使用场景列表
- 用户说 "xxx" 时
- 需要 xxx 功能时

## When NOT to Use（何时不用）

❌ 不适用场景
- xxx 情况请用其他方法

## Setup（安装配置）

1. 第一步
2. 第二步

```bash
# 示例命令
node {baseDir}/scripts/main.mjs "参数"
```

## Options（选项说明）

- `-n <count>`: 参数说明
- `--flag`: 开关说明

## Core Rules（核心规则）

重要的技术细节、注意事项、常见陷阱。

## Security & Privacy（安全说明）

数据处理方式、隐私保护说明。

## Related Skills（相关技能）

推荐配合使用的其他技能。

## Feedback（反馈）

- 有用请 star
- 更新请 sync
```

---

## 🔑 关键规范

| 文件/目录 | 作用 | 必需 |
|-----------|------|------|
| `SKILL.md` | 技能定义 + 使用文档 | ✅ 必需 |
| `scripts/` | 可执行脚本 | ⚠️ 功能性技能需要 |
| `references/` | 参考资料、配置模板 | ❌ 可选 |
| `.env.example` | 环境变量模板 | ⚠️ 需要 API Key 时推荐 |
| `_meta.json` | ClawHub 元数据 | ❌ 可选 |

---

## 📝 示例参考

**简单技能**（如 tavily-search）：
```
tavily-search/
├── SKILL.md
├── _meta.json
└── scripts/
    ├── search.mjs
    └── extract.mjs
```

**复杂技能**（如 email-automation）：
```
email-automation/
├── SKILL.md
├── README.md
├── .env
├── .env.example
├── .gitignore
├── scripts/
│   └── email_processor.py
├── references/
│   └── config.md
└── *.py (多个功能脚本)
```

---

## 🚀 快速开始

1. **创建目录**：`mkdir my-skill && cd my-skill`
2. **写 SKILL.md**：按上面格式填写
3. **加脚本**（如需要）：`mkdir scripts` 写可执行代码
4. **测试**：在 OpenClaw 中触发技能描述的场景
5. **发布**（可选）：用 `clawhub publish` 发布到 ClawHub

---