# 复盘执行说明

## 目标

生成：`~/.ashare-assistant/data/{DATE}/market_review.md`

## 必要输入

1. `~/.ashare-assistant/data/{DATE}/report/news_sentiment.md`
2. `~/.ashare-assistant/data/{DATE}/report/social_sentiment.md`
3. `~/.ashare-assistant/data/{DATE}/filtered/market_sectors.md`
4. `~/.ashare-assistant/data/{DATE}/filtered/funding.md`
5. `~/.ashare-assistant/data/{DATE}/filtered/ths_report.md`
6. `~/.ashare-assistant/data/{DATE}/filtered/trend_report.md`
7. `~/.ashare-assistant/data/{DATE}/filtered/news_flash.md`
8. `~/.ashare-assistant/data/{DATE}/filtered/us_market.md`（缺失时标注“美股数据不可用”）
9. `skills/ashare-assistant/strategy/active.yaml`

## 步骤

1. 判断市场强弱：`strong/neutral/weak`，并给出仓位建议。
2. 总结美股前夜影响（可缺省，但必须说明缺省原因）。
3. 提炼主线题材、新兴题材、衰退题材。
4. 给出情绪证据：至少 2 条社区观点 + 1 条新闻标题。
5. 产出候选股分析：每只包含逻辑与风险。
6. 输出趋势候选股汇总：覆盖 `trend_report.md` 中全部 4 星/5 星个股。

## 输出骨架

```markdown
# A股市场复盘报告 - {DATE}

## 一、市场环境
## 二、美股前夜影响
## 三、题材线索
## 四、候选股分析
## 五、风险提示
## 六、精华言论
## 七、趋势候选股汇总
```

## 约束

1. 不得补造数字或事件。
2. 不得跳过“趋势候选股汇总”。
3. 不确定信息标注“待确认”。
