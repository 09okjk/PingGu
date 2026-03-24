# GenerateReportSkill v1

S6 报告合成 Skill，用于生成结构化评估报告草稿。

## 目录结构

```text
generate-report-skill/
├── SKILL.md
├── README.md
├── _meta.json
├── .env.example
├── .gitignore
├── scripts/
│   ├── main.py
│   ├── report_builder.py
│   ├── summary_builder.py
│   ├── risk_section.py
│   ├── task_section.py
│   ├── totals_section.py
│   ├── materials_section.py
│   ├── spare_parts_section.py
│   ├── confidence.py
│   ├── sources.py
│   └── utils.py
├── references/
│   ├── config.md
│   └── output.schema.json
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

## 快速测试

```bash
python3 scripts/main.py \
  --action generate_report \
  --json-input-file samples/sample-input.json \
  --pretty
```

## 当前版本特点

- 一项一报
- 结构化表格优先
- 支持风险、任务、总计、工具、耗材、专用工具、设备/备件三栏
- 支持 confidence / source / warnings / review_focus
- 支持“港口=航修”

## 当前实现边界

- 不直接生成报价单
- 不生成报价项建议
- 不做多服务项总报告
- 不重新执行 S2 推理
- 不接数据库，直接消费输入结果

## 后续建议

- 增强 task_rows 的骨架组织能力
- 接入 R4 模板
- 增强设备/备件归属规则
- 增加更多 sample case