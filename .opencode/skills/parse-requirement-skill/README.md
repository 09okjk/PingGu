# ParseRequirementSkill v2

支持三阶段交互闭环的需求解析 Skill：

- `parse`：把邮件解析成需求单草稿
- `revise`：吸收用户反馈并更新需求单
- `confirm`：最终确认，停止继续追问

## 目录结构

```text
parse-requirement-skill/
├── SKILL.md
├── README.md
├── _meta.json
├── .env.example
├── .gitignore
├── scripts/
│   └── main.py
├── references/
│   ├── config.md
│   ├── r2-enums.json
│   ├── aliases.json
│   └── *.schema.json
└── samples/
    └── *.json
```

## 快速测试

### 1. parse
```bash
python3 scripts/main.py \
  --action parse \
  --json-input-file samples/sample-input.json \
  --refs references/r2-enums.json \
  --pretty
```

### 2. revise
```bash
python3 scripts/main.py \
  --action revise \
  --json-input-file samples/sample-revise-input.json \
  --refs references/r2-enums.json \
  --pretty
```

### 3. confirm
```bash
python3 scripts/main.py \
  --action confirm \
  --json-input-file samples/sample-confirm-input.json \
  --refs references/r2-enums.json \
  --pretty
```

## 交互闭环思路

1. 用户提交原始邮件
2. Skill 初始解析生成需求项草稿
3. 用户提出修改意见
4. Skill 更新需求项并继续提问
5. 用户确认无需再修改
6. Skill 输出 `confirmed` 状态
7. 进入后续 S1/S2/S6

## 当前版本特点

- 规则优先
- 本地可跑
- 支持 session / revision history
- 支持 next_questions
- 保留未来接入 LLM 的扩展位

## 后续建议

- 接入正式 R2 枚举
- 丰富 alias 映射
- 增加字段级精细修订
- 增加会话持久化
- 增加离线飞轮学习