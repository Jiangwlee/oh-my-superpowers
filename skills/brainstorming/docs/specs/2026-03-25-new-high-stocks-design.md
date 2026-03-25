# 历史新高股票数据采集与存储方案

> 实现同花顺"历史新高"股票的每日采集、持久化存储和 API 查询功能，服务于市场监控和历史回溯分析。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 背景与目标

**问题**：当前平台缺少对"创历史新高"股票的追踪能力，无法回答"今日哪些股票创新高"、"某股票何时首次突破历史高点"等问题。

**痛点**：
- 无法快速定位当日强势股（历史新高往往是资金聚焦信号）
- 缺乏历史回溯能力，难以分析新高的后续表现
- 现有情绪指标缺少"新高数量"这一重要维度

**成功标准**：
1. 每日收盘后自动采集并存储历史新高股票数据
2. API 可查询任意交易日的历史新高列表
3. 支持按股票代码回溯其历史新高记录
4. 集成到 `collect-all` pipeline，无需手动触发

### 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     ashare-platform                          │
├─────────────────────────────────────────────────────────────┤
│  [同花顺网页]                                                │
│      ↓ HTTP GET + Referer                                    │
│  ashare_data/fetchers/new_high.py                           │
│      ↓ HTML 解析 → list[dict]                                │
│  app/app/pipelines/build_new_high.py                        │
│      ↓ 清洗、格式化                                          │
│  app/app/models/new_high_daily.py (ORM)                     │
│      ↓ bulk_insert()                                         │
│  PostgreSQL 数据库                                           │
└─────────────────────────────────────────────────────────────┘

API 层：
  GET /new-high/daily/{trade_date}        → 单日新高列表
  GET /new-high/stocks/{code}             → 某股票新高历史
  GET /new-high/stats/breakthrough?days=N → 近 N 天突破统计
```

**组件职责**：
| 模块 | 职责 |
|------|------|
| `new_high.py` (fetcher) | HTTP 请求 + HTML 解析，返回标准化数据 |
| `build_new_high.py` (pipeline) | 调用 fetcher → 数据清洗 → 批量入库 |
| `new_high_daily.py` (model) | SQLAlchemy ORM 模型定义 |
| `new_high.py` (route) | REST API 路由实现 |

### 关键决策

- **HTML 解析而非 JSON API**：同花顺未提供公开 JSON 接口，返回 HTML 表格。使用 `requests` + `BeautifulSoup4` 解析，轻量且可控。

- **仅存储每日快照（非完整轨迹）**：按用户选择 A，只存当日新高股票列表，不追踪"首次突破"标记。如需回溯某股票的新高历史，通过 `code + trade_date` 查询即可。

- **集成到 collect-all pipeline**：作为 `build_consecutive_red` 之后的一个步骤，保证每日自动运行。

- **字段设计与现有模型对齐**：参考 `consecutive_red_daily` 和 `market_emotion_daily`，使用 `trade_date`、`run_id`、`code`、`name` 等统一命名。

---

## 行动原则

> 从固定原则库选取适用原则。

- **TDD（测试驱动开发）**：先写失败测试，再写最小实现。**禁止：** 无测试的代码提交到主分支。

- **Break Don't Bend（宁可报错也不静默失败）**：fetcher 层遇到网络/解析错误应抛出异常，由 pipeline 层统一处理。**禁止：** 在 fetcher 中 `except: return []` 掩盖真实问题。

- **Zero-Context Entry（零上下文入口）**：每个模块的入口函数必须有完整 docstring，说明输入输出和异常场景。**禁止：** 无文档的公开函数。

- **Explicit Contract（显式契约）**：API 响应使用 Pydantic 模型定义，字段类型和必填项明确。**禁止：** 返回裸 dict，类型不明确。

- **[任务专属] 不依赖浏览器自动化**：使用纯 HTTP 请求 + HTML 解析，避免 Puppeteer/Playwright 等重型依赖。**禁止：** 引入 Chrome CDP 或 Selenium。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `ashare_data/fetchers/new_high.py` | 历史新高数据采集器 |
| 新增 | `app/app/models/new_high_daily.py` | SQLAlchemy ORM 模型 |
| 新增 | `app/app/pipelines/build_new_high.py` | 数据处理流水线 |
| 新增 | `app/app/api/routes/new_high.py` | REST API 路由 |
| 修改 | `app/app/tasks/collect_all.py` | 集成到 collect-all pipeline |
| 修改 | `app/app/api/routes/__init__.py` | 注册新路由 |
| 新增 | `app/alembic/versions/xxx_new_high_daily.py` | 数据库迁移脚本 |
| 新增 | `tests/test_fetcher_new_high.py` | fetcher 单元测试 |

### 任务步骤

#### Task 1: 实现 fetcher 模块

**Files:**
- 新增：`ashare_data/fetchers/new_high.py`
- 测试：`tests/test_fetcher_new_high.py`

- [ ] **Step 1: 写失败测试**

```python
def test_fetch_new_high_stocks_returns_empty_on_network_error():
    """网络请求失败时返回空列表"""
    # Mock http_json 抛出异常
    with patch("ashare_data.core.http_client.http_text") as mock:
        mock.side_effect = RequestException("Network error")
        result = fetch_new_high_stocks()
        assert result == []

def test_fetch_new_high_stocks_parses_html_correctly():
    """正确解析 HTML 表格数据"""
    # Mock 返回示例 HTML
    sample_html = """<table><tr><td>002039</td><td>黔源电力</td>...</tr></table>"""
    with patch("ashare_data.core.http_client.http_text") as mock:
        mock.return_value = sample_html
        result = fetch_new_high_stocks()
        assert len(result) > 0
        assert "code" in result[0]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_fetcher_new_high.py -v
# 预期：FAIL（函数尚未实现）
```

- [ ] **Step 3: 写最小实现**

参考 `market_turnover.py` 结构，使用 `http_text` + `BeautifulSoup` 解析 HTML 表格。

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_fetcher_new_high.py -v
# 预期：PASS
```

- [ ] **Step 5: 提交**

```bash
git add ashare_data/fetchers/new_high.py tests/test_fetcher_new_high.py
git commit -m "feat: add new_high fetcher for THS history high stocks"
```

#### Task 2: 实现数据库模型

**Files:**
- 新增：`app/app/models/new_high_daily.py`

- [ ] **Step 1: 定义 ORM 模型**

参考 `consecutive_red_daily.py`，定义字段：
- `trade_date` (String, index)
- `run_id` (String, index)
- `code` (String)
- `name` (String)
- `price` (Float)
- `change_pct` (Float)
- `turnover_rate` (Float)
- `prev_high` (Float)
- `prev_high_date` (String)

- [ ] **Step 2: 生成数据库迁移**

```bash
alembic revision --autogenerate -m "add new_high_daily table"
alembic upgrade head
```

- [ ] **Step 3: 提交**

```bash
git add app/app/models/new_high_daily.py app/alembic/versions/xxx_.py
git commit -m "feat: add NewHighDaily ORM model"
```

#### Task 3: 实现 pipeline

**Files:**
- 新增：`app/app/pipelines/build_new_high.py`

- [ ] **Step 1: 写测试**

```python
def test_build_new_high_pipeline_inserts_data():
    """pipeline 成功将数据写入数据库"""
    with open_session() as session:
        result = build_new_high(trade_date="2026-03-25", session=session)
        assert result["inserted_count"] > 0
```

- [ ] **Step 2: 实现 pipeline**

调用 `fetch_new_high_stocks()` → 清洗数据 → `bulk_insert_mappings()`

- [ ] **Step 3: 运行测试**

```bash
pytest app/tests/test_build_new_high.py -v
# 预期：PASS
```

- [ ] **Step 4: 提交**

```bash
git add app/app/pipelines/build_new_high.py
git commit -m "feat: add build_new_high pipeline"
```

#### Task 4: 实现 API 路由

**Files:**
- 新增：`app/app/api/routes/new_high.py`
- 修改：`app/app/api/routes/__init__.py`

- [ ] **Step 1: 定义 Pydantic 响应模型**

```python
class NewHighStockResponse(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float
    # ...

class NewHighDailyResponse(BaseModel):
    trade_date: str
    stocks: list[NewHighStockResponse]
```

- [ ] **Step 2: 实现路由**

```python
@router.get("/daily/{trade_date}")
def get_new_high_daily(trade_date: str) -> NewHighDailyResponse:
    with open_session() as session:
        stocks = repo.get_by_date(session, trade_date)
        return NewHighDailyResponse(trade_date=trade_date, stocks=stocks)
```

- [ ] **Step 3: 注册路由**

在 `__init__.py` 中导入并注册 `new_high.router`

- [ ] **Step 4: 测试 API**

```bash
curl http://localhost:8000/new-high/daily/2026-03-25
# 预期：返回 JSON 数据
```

- [ ] **Step 5: 提交**

```bash
git add app/app/api/routes/new_high.py app/app/api/routes/__init__.py
git commit -m "feat: add new-high API routes"
```

#### Task 5: 集成到 collect-all pipeline

**Files:**
- 修改：`app/app/tasks/collect_all.py`
- 修改：`app/app/cli.py`（可选，如需新增 CLI 参数）

- [ ] **Step 1: 导入 pipeline**

```python
from app.pipelines.build_new_high import build_new_high
```

- [ ] **Step 2: 在 run() 中调用**

```python
day_result["build_new_high"] = build_new_high(trade_date=resolved_trade_date)
```

- [ ] **Step 3: 测试集成**

```bash
ashare-platform collect-all --date 2026-03-25
# 预期：输出中包含 "build_new_high" 结果
```

- [ ] **Step 4: 提交**

```bash
git add app/app/tasks/collect_all.py
git commit -m "feat: integrate new_high into collect-all pipeline"
```

#### Task 6: 文档更新

> 本次新增核心模块（fetcher + model + pipeline + API），属于重大变更，需要更新文档。

**Files:**
- 修改：`README.md`（如包含功能列表）
- 修改：`AGENTS.md`（数据源列表）

- [ ] **Step 1: 更新 AGENTS.md 数据源列表**

在"数据源开发"章节添加：
```markdown
### 已有 Fetcher 列表

| 模块 | 数据源 | 用途 |
|------|--------|------|
| `new_high` | 同花顺数据中心 | 历史新高股票 |
| ... | ... | ... |
```

- [ ] **Step 2: 提交**

```bash
git add AGENTS.md
git commit -m "docs: update data source list with new_high fetcher"
```

---

## 开发模式推荐

建议使用 **Subagent 模式**：本次任务涉及 6 个独立模块（fetcher、model、pipeline、API、integration、docs），可并行执行提速。

**选项：**
- **A) Subagent 模式（推荐）** — 每个 Task 分配独立 subagent，主会话负责 review
- **B) 内联执行** — 在当前会话中逐步执行

*输入 A/B，或直接说「同意」采用推荐方案，我立即开始。*
