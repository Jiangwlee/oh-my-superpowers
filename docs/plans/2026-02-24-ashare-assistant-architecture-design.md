# ashare-assistant 重构设计（2026-02-24）

## 1. 背景与目标
- 现有 skill 名为 a-share-review-planner，只对外宣称“复盘 + 选股”，但内部已经涵盖行情复盘、选股、交易计划、交易复盘、持仓洞察、策略进化等完整能力。
- 技术架构存在重复采集、模块边界模糊、缓存缺失、上下文压力大等问题；缓存目录分散在 /tmp、~/.openclaw 等路径，难以维护。
- 本设计旨在：完成 skill 重命名为 **ashare-assistant**，向 Agent 层完整暴露能力矩阵，并通过统一缓存与目录结构提升执行效率与可维护性。

## 2. 现状诊断摘要
| 类别 | 症状 | 影响 |
| --- | --- | --- |
| 能力暴露 | 仅描述复盘/选股，持仓洞察与策略进化不可被调度 | Agent 无法按需调用，需人工介入 |
| 数据采集 | JRJ K 线、券商账户、淘股吧等被多次抓取 | API 费用上升，数据出现时间差 |
| 阶段划分 | 阶段 3 混合分析、深研、风控、策略维护 | 上下文膨胀，错误定位困难 |
| 缓存缺失 | 10+ fetcher 难以复用结果，仅极少数内存缓存 | 运行时间长、重复 IO |
| 目录分散 | 输出落在 /tmp、.memory、~/.openclaw | 成果追溯困难，部署麻烦 |

## 3. 能力矩阵（SKILL.md frontmatter 中声明）
| 能力名称 | 描述 | 触发词示例 | 前置依赖 | 主要输出 |
| --- | --- | --- | --- | --- |
| `market-review` | 收盘后行情复盘，分析市场环境/题材/资金流 | 复盘、今日回顾、今天行情 | `data-collect` | `~/.ashare-assistant/data/{DATE}/report.md` (行情段) |
| `stock-pick` | 基于趋势扫描与题材，筛选候选股并触发深度研究 | 选股、明天买什么、涨停 | `market-review` | `~/.ashare-assistant/data/{DATE}/candidates.json` |
| `trading-plan` | 结合候选与持仓，输出次日交易计划 | 交易计划、明日计划 | `stock-pick`, `holding-insight` | `report.md + candidates.json` |
| `trade-review` | 计划 vs 实际执行差异诊断 | 交易复盘、执行回顾 | `data-collect` | `trade_review.json`, `evolution/feedback.md` |
| `holding-insight` | 规则引擎对持仓作出加仓/减仓/持有建议 | 持仓建议、加减仓 | `data-collect` | `holding_insight.json` |
| `strategy-evolution` | 根据复盘反馈微调策略参数与知识库 | 策略进化、诊断 | `trade-review` | `strategy/active.yaml`, `evolution/*.md` |

> 说明：`data-collect` 能力对应 `collect_sentiment.py`，统一负责拉取所有数据并写入缓存/数据目录。

## 4. 目录与路径设计
```
~/.ashare-assistant/
├── cache/            ← fetcher 层磁盘缓存
│   ├── kline/
│   ├── broker/
│   ├── news/
│   ├── taoguba/
│   ├── eastmoney/
│   ├── ths/
│   └── funding/
├── data/             ← 运行数据（原 /tmp/a-share-review/）
│   └── {DATE}/
│       ├── collect/
│       ├── analysis/
│       ├── report.md
│       ├── candidates.json
│       ├── trade_review.json
│       └── holding_insight.json
├── memory/           ← `.memory` 替代，含 decision_log.jsonl
└── broker_data/      ← 原 ~/.openclaw/broker_data/ 迁移
```

在源码侧创建 `scripts/core/config.py`，集中维护：
- `ASHARE_HOME / CACHE_DIR / DATA_DIR / MEMORY_DIR / BROKER_DIR`
- `DECISION_LOG` 路径
- `data_dir_for_date()` 与 `ensure_dirs()` 帮助函数

## 5. 缓存层设计
### 5.1 统一缓存模块（`scripts/core/cache.py`）
- 统一接口：`cache_get(category, key)`, `cache_set(category, key, data)`, `cache_invalidate(category, key=None)`, `cache_cleanup(max_age_days=7)`。
- 缓存文件结构：
```json
{
  "_cache_meta": {
    "created_at": "2026-02-24T15:30:00",
    "ttl_seconds": 1800,
    "category": "taoguba",
    "key": "tgb_hot_2026-02-24"
  },
  "data": { ... }
}
```
- 清理策略：`collect_sentiment.py` 每次运行前自动执行 `cache_cleanup(max_age_days=7)`；所有类型统一 7 天回收。

### 5.2 TTL 策略（交易日 + TTL 混合）
| 分类 | 数据 | 缓存键模式 | 过期策略 |
| --- | --- | --- | --- |
| 收盘后固化 | 日 K、涨停快照/历史、板块资金、北向/主力流、趋势扫描、美股、券商账户/委托 | `{code}_daily_{trade_date}` 等 | 以 `trade_date` 为 key，**不设置 TTL**，仅由 7 天清理回收 |
| 帖子/讨论 | 淘股吧精华、推荐、热门、个股；东方财富股吧 | `tgb_*_{date}` / `em_guba_{code}_{date}` | TTL = 30 分钟 |
| 高时效信息 | 7x24 快讯、头条、市况直击、机会情报、每日财经、分钟 K | `news_*_{date}_{hour}` / `{code}_minute_{date}_{hour}` | 快讯 15 分钟；头条/市况/机会 30 分钟；每日财经 2 小时；分钟 K 5 分钟（盘后视为当日固定） |

## 6. 公共模块与 HTTP 层
- 在 `scripts/core/` 下新增：
  - `http_client.py`：`http_json()` 与 `http_text()`，统一重试、UA、超时设置，替代 fetcher 内部 6 套实现。
  - `shared.py`：收敛 `holding_insight.py` 与 `trade_review.py` 中 11 个重复函数（如 `_safe_float`, `_norm_code`, `_enrich_hold_list_prices` 等）及 `DEFAULT_STRATEGY`。
- 现有 `scripts/utils/http_client.py` 调整为 `core/http_client.py` 的薄封装，逐步迁移引用。

## 7. 阶段/能力重组
| 现状阶段 | 新能力 | 说明 |
| --- | --- | --- |
| Stage 1 数据采集 | `data-collect` | 保持脚本不变，输出目录改为 `~/.ashare-assistant/data/{DATE}/collect/`，并写入缓存层；负责执行自动缓存清理。 |
| Stage 2 数据读取 | `market-review` | SKILL.md 引导按需加载 references/maket-review.md，强调逐步加载与上下文控制。 |
| Stage 3 分析+深研+风控+策略 | `stock-pick`, `trading-plan`, `holding-insight`, `strategy-evolution` | 拆分职责，深研（原步骤 3.5）仍由脚本负责数据采集，但输出落在新数据目录并复用缓存。 |
| Stage 4 输出 | `trading-plan` | 仅负责报告格式化与 `decision_logger.py`。 |
| Stage 5 交易复盘 | `trade-review` | 独立能力，可直接触发；同样复用缓存与统一路径。 |
| Stage 6 持仓洞察 | `holding-insight` | 成为显式能力，可与交易计划解耦。

references/ 重命名：`data-collect.md`, `market-review.md`, `stock-pick.md`, `trading-plan.md`, `trade-review.md`, `holding-insight.md`, `evolution.md`，并更新 SKILL.md 链接。

## 8. 迁移/实施计划
| PR | 范围 | 关键检查 |
| --- | --- | --- |
| PR1：基础设施 | 新建 `scripts/core/{config,cache,http_client,shared}.py`，补充单元测试 (`tests/test_cache.py`, `tests/test_shared.py`) | 确认新模块可独立运行，目录初始化无副作用 |
| PR2：fetcher 重构 | 所有 fetcher 接入缓存与统一 HTTP；`holding_insight.py`、`trade_review.py` 改用 shared 模块；路径切换到 `config.DATA_DIR` | 运行 `python -m unittest discover -s skills`，确保无回归 |
| PR3：文档/能力声明 | 编写新的 SKILL.md frontmatter（含 capabilities），重组 references/，更新 commands.md 路径 | 手动审阅触发词、能力依赖是否准确 |
| PR4：重命名与部署 | 复制 `skills/a-share-review-planner/` → `skills/ashare-assistant/`，旧目录标记 deprecated；同步 `.claude/skills/`、`.agents/skills/`；更新 AGENTS.md | 验证部署脚本与依赖路径；确保双目录共存期内无冲突 |

## 9. 风险与注意事项
- **双目录过渡**：在 deprecated 目录中添加显眼提示，避免下游继续引用旧路径；设置移除日期。
- **缓存膨胀**：虽然 7 天清理，但需在 `cache_cleanup` 中增加磁盘容量守卫（如超 500MB 时强制清理）。
- **权限**：`~/.ashare-assistant/` 需要在安装脚本中创建并赋予正确的 chmod，避免多用户冲突。
- **Agent 调度**：capabilities 列表上线后，需要同步更新任何引用旧 skill 名称的 orchestrator/工作流配置。

## 10. 验收标准
1. LLM Agent 通过 `capabilities` 字段可独立调用六项能力，依赖关系正确解析。
2. `collect_sentiment.py` 运行一次即可填充缓存目录，再次运行同日任务时命中率 ≥ 80%。
3. 所有产物在 `~/.ashare-assistant/data/{DATE}/` 下可追溯，`.memory/decision_log.jsonl` 成功迁移到 `~/.ashare-assistant/memory/`。
4. `holding_insight.py` 与 `trade_review.py` 代码重复率显著下降，公共函数仅维护于 `core/shared.py`。
5. docs/plans 中的本设计被审阅通过，并作为实施依据。
