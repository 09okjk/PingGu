# SearchHistoryCasesSkill（本地运行版）

## 1) 准备输入文件

创建 `input.json`：

```json
{
  "business_type": "轮机",
  "service_desc_code": "RS0000000001",
  "service_type_code": "CS0017",
  "equipment_model_code": "ET000000000826",
  "task_description": "主机常规坞修保养工作",
  "remark": "工期因交叉作业、备件、船厂进出坞等因素可能延迟",
  "top_k": 5
}
```

## 2) 执行

```bash
npm install pg dotenv
node ./scripts/main.mjs --input ./input.json --pretty
```

## 3) 可选：初始化扩展和索引

```bash
psql -h 127.0.0.1 -U postgres -d pinggu -f ./scripts/schema.sql
```