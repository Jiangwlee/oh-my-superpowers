# ashare-data LLM 剥离 + 个股深研重构设计

> 日期: 2026-03-04
> 状态: approved

## 目标

将 ashare-data 从「数据采集 + LLM 分析」混合体改造为纯数据采集层。所有 LLM 调用迁移到 n8n 编排层。同时重构个股深研，建立独立档案体系和按需更新策略。

## 架构变更

```
Before:
  ashare-data = 数据采集 + filter + LLM(情绪分析) + LLM(深研报告)
  n8n → task-runner → ashare-data.collect() [一键全跑]

After:
  ashare-data = 数据采集 + filter + 深研档案管理（纯数据，零 LLM）
  n8n 编排:
    1. task-runner/ashare/collect        → 采集 + filter
    2. task-runner/ashare/deep-research  → 深研数据采集
    3. n8n LLM 节点                      → 情绪分析 + 深研报告
```

## 新增端点

### POST /ashare/deep-research/collect

确定深研目标 → 并发采集 → 写入档案 → 返回本次采集列表。

**目标确定逻辑**:
1. 读取当日趋势股（`raw/trend_scan.json`）+ watchlist
2. 合并去重
3. 对比 `index.json`，筛出：从未深研 + 距上次采集 ≥ 7天
4. 对筛出的股票并发采集东方财富股吧 + 淘股吧数据
5. 写入档案目录，更新 index.json

**请求**: 无必填参数（可选 `force: bool` 忽略 7 天时效）

**响应**:
```json
{
  "task_id": "uuid",
  "status": "success",
  "result": {
    "stocks": [
      {"code": "002050", "name": "三花智控", "status": "collected", "is_new": true},
      {"code": "600519", "name": "贵州茅台", "status": "skipped", "reason": "fresh"}
    ],
    "collected_count": 5,
    "skipped_count": 3,
    "total_targets": 8
  }
}
```

### GET /ashare/deep-research/data?code=002050

读取指定股票的深研原始数据，直接返回内容（非文件路径）。

**响应**:
```json
{
  "code": "002050",
  "name": "三花智控",
  "last_collected_at": "2026-03-04 15:30:00",
  "has_brief": false,
  "raw_em": { ... },
  "raw_tgb": { ... }
}
```

### POST /ashare/deep-research/save-report

保存 n8n LLM 节点生成的深研报告。

**请求**:
```json
{
  "code": "002050",
  "report": "# 002050 三花智控 深度研究报告\n\n..."
}
```

**响应**:
```json
{
  "code": "002050",
  "saved_at": "2026-03-04 16:00:00"
}
```

## 深研档案存储

```
~/.ashare-assistant/deep_research/
├── index.json                  # 全局索引
├── 002050/
│   ├── profile.json            # 元信息（代码、名称、首次/最后采集时间）
│   ├── raw_em.json             # 东方财富原始数据
│   ├── raw_tgb.json            # 淘股吧原始数据
│   └── brief.md                # LLM 深研报告（n8n 回写）
└── 600519/
    └── ...
```

**index.json 结构**:
```json
{
  "stocks": {
    "002050": {
      "name": "三花智控",
      "first_collected_at": "2026-02-25 22:10:00",
      "last_collected_at": "2026-03-04 15:30:00",
      "last_brief_at": null,
      "collect_count": 2
    }
  },
  "last_updated": "2026-03-04 15:30:00"
}
```

## 时效策略

- 每日可调用，仅采集：**从未深研** + **距上次采集 ≥ 7天**
- 目标来源：当日趋势股 + watchlist
- `force=true` 可忽略时效限制

## 代码清理清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 重写 | `deep_research_batch.py` | 纯采集 + 档案管理，移除 `_run_llm_brief`、`_STOCK_BRIEF_TEMPLATE`、LLM 步骤 |
| 删除 | `sentiment_preprocess.py` | 整个文件（LLM 调用迁移到 n8n） |
| 清理 | `collect_sentiment.py` | 移除深研相关参数/导入/调用 (`run_deep_research`, `deep_research_*`, `_load_buy_signal_targets`, `_build_deep_research_targets_from_signals`, deep_research import) |
| 清理 | `collect.py` | 移除 sentiment 相关参数/导入/调用 (`run_sentiment`, `sentiment_model`, `sentiment_timeout`, `sentiment_preprocess` import, CLI 参数) |
| 清理+新增 | task-runner `ashare.py` | 清理 collect 透传的 LLM 参数，新增 3 个深研端点 |
| 清理 | `pyproject.toml` | 无变更（entry points 不受影响） |

## n8n 编排流程（后续实现）

```
1. POST /ashare/collect              → 纯数据采集 + filter
2. POST /ashare/deep-research/collect → 返回需深研的股票列表
3. Loop 每只 collected 股票:
   GET  /ashare/deep-research/data?code=XXX  → 原始数据
   → n8n AI Agent / LLM 节点生成报告
   POST /ashare/deep-research/save-report    → 回写报告
4. n8n 读取 filtered/*.md → LLM 做情绪分析（独立于深研）
```

注：n8n 工作流实现不在本次 plan 范围内，本次只完成 ashare-data 侧的改造。
