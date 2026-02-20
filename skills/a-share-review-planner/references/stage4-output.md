# 阶段4：输出交易计划

按以下结构产出完整报告并保存到文件：

```markdown
# A股复盘报告 - {DATE}

## 一、市场环境
- 强弱评级：[强/中/弱]
- 主线风格：[题材驱动/趋势主导/混沌轮动]
- 账户健康度：[growth/normal/defensive/critical/未知]
- 最终仓位建议：[激进/标准/防守/观望]
- 判断依据：...

## 二、题材线索

### 主线题材
- [题材名] | 阶段：[启动/加速/分歧/衰退] | 龙头：[个股]

### 新兴线索
- [题材名] | 催化：[事件] | 评估：[高/中/低]

### 衰退警示
- [题材名] | 信号：[具体信号]

### 市场情绪
[乐观/谨慎/恐慌] - [依据]

## 三、交易计划

### [代码] [名称] [类型：趋势/题材]
- 选股理由：...
- 深度分析校准：...
- 趋势评分：[星级] [总分] | [情绪标签]（趋势股）
- 所属题材：[题材名] | 阶段：[X]（题材股）
- 入场条件：...
- 目标仓位：...
- 止盈条件：...
- 止损条件：...
- 持有周期：...
- 风险点：...

## 四、风险提示
- 集中度：[正常/偏高]
- 计划变更：[新增/移除/调整]
- 特殊风险：[如有]

## 五、策略调整
- 当前策略评估：[适用/需微调]
- 调整内容：[无/具体修改]

## 六、精华言论
1. [经验1] —— *[作者]*
...
10. [经验10] —— *[作者]*
```

强制语言约束：

1. 不使用缩写词（例如 `THS`、`DR`），统一写全称（例如“同花顺”“深度分析”）。
2. 不单独输出“深度分析校准结论”章节，校准内容必须并入对应个股条目。

保存报告：

```bash
mkdir -p /tmp/a-share-review/{DATE}
cat > /tmp/a-share-review/{DATE}/report.md << '__REPORT__'
[完整报告正文]
__REPORT__
```

**candidates.json 关键字段约束**：

1. `run_id`：必须使用阶段2读取的 `run_id.json` 中的值，不得自行生成
2. `market.regime` 只能是 `strong` / `neutral` / `weak`
3. `candidates[].action` 只能是 `buy` / `hold` / `sell` / `watch`
4. `thesis_short` 与 `risk_note` 不超过 30 字

若阶段3结构校验通过（`validate_output.py` 返回 `ok=true`），执行：

```bash
python3 {SKILL_DIR}/scripts/decision_logger.py \
  --input /tmp/a-share-review/{DATE}/candidates.json \
  --log-file {SKILL_DIR}/.memory/decision_log.jsonl
```
