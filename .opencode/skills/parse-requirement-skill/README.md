# ParseRequirementSkill

用于将自然语言邮件解析为标准化服务需求项列表的 Skill。

## 功能特性

- 支持从一封邮件中拆分多个服务项
- 支持服务描述 / 服务类型 / 设备对象 / 数量 / 单位提取
- 支持枚举映射与别名匹配
- 支持歧义输出和待确认标记
- 当前不依赖外部模型，适合本地快速测试
- 后续可无缝扩展附件解析与 LLM 增强

## 快速开始

### 直接输入文本

```bash
python3 scripts/main.py \
  --input "The main engine shows abnormal vibration and may need inspection. The boiler has leakage and may require repair." \
  --refs references/r2-sample-enums.json \
  --pretty
```

### 从文件读取

```bash
python3 scripts/main.py \
  --input-file sample-email.txt \
  --refs references/r2-sample-enums.json \
  --pretty
```

## 输出说明

顶层返回：
- `success`
- `data`
- `error`

`data.requirements` 是解析后的服务项数组，可直接给下游 Skill 使用。

## 注意事项

1. 当前版本为 MVP，本地规则优先。
2. 若未命中正式枚举，可能输出 `null` 或低置信度候选。
3. 获取正式 R2 数据后，请替换参考文件中的示例枚举。
4. 当前未启用附件解析，但输入结构已预留扩展位。

## 推荐测试点

- 单设备单问题
- 多设备多问题
- 中英混合输入
- 含型号但无明确服务类型
- 含数量单位
- 描述模糊、需要歧义输出的邮件