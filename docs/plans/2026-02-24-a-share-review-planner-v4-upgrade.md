交易复盘模块（trade_review.py）详细设计文档
> 日期：2026-02-24
> 关联文件：skills/a-share-review-planner/scripts/trade_review.py（待创建）
> 前置依赖：broker_account.py、trend_scanner.py、decision_logger.py、active.yaml
---
一、设计动机（Why）
当前 a-share-review-planner 的工作流是：数据采集 → 市场分析 → 选股推荐 → 决策记录。这是一个开环系统——只有"建议"，没有"回查"。
交易复盘模块的目标是闭环：将实际交易执行与交易计划对比，自动检测六类瑕疵，输出可量化的改进建议。这是从"选股工具"进化为"交易教练"的关键一步。
1.1 核心价值
1. 客观性：人工复盘容易选择性遗忘失败交易，程序化检测无遗漏
2. 时效性：收盘后自动运行，当日瑕疵当日发现
3. 可追溯：所有瑕疵记录持久化，可追踪改进趋势
4. 策略演进驱动：瑕疵统计反馈到 evolution/ 目录，推动策略参数迭代
---
二、数据流架构
输入数据源                          处理核心                     输出
─────────────────────────────────────────────────────────────────────────
broker_account.py                                          trade_review.json
  ├─ positions (持仓快照)  ──┐                                 ├─ account_snapshot
  └─ orders (当日委托)     ──┤                                 ├─ execution_summary
                             │                                 ├─ flaws[]
decision_log.jsonl           ├──→  trade_review.py  ──→       ├─ timing_scores[]
  └─ candidates + action   ──┤       (核心模块)                ├─ position_check
                             │                                 ├─ flaw_counts
trend_scanner.py             │                                 ├─ improvement_suggestions
  ├─ daily kline (MA计算)  ──┤                                 └─ metadata
  └─ minute kline (VWAP)  ──┤
                             │                          evolution/feedback.md
strategy/active.yaml       ──┘                            (追加写入)
  ├─ position limits
  ├─ stop_loss rules
  └─ account_mode
2.1 数据源职责
| 数据源 | 获取方式 | 费用 | 提供信息 |
|--------|---------|------|---------|
| broker_account.py | JVQuant API（ticket 缓存复用） | 登录 0.5元/次，查询免费 | 当日委托列表、持仓快照、账户资金 |
| decision_log.jsonl | 本地文件读取 | 免费 | 历史选股建议（code, name, score, action） |
| trend_scanner.fetch_jrj_daily_kline() | JRJ 免费 API | 免费 | 日K线（计算 MA5/MA10/MA20） |
| trend_scanner.fetch_jrj_minute_kline() | JRJ 免费 API | 免费 | 分钟K线（计算 VWAP、日内价格位置） |
| strategy/active.yaml | 本地文件读取 | 免费 | 仓位限制、止损止盈规则、账户模式 |
---
三、六类瑕疵检测详细设计
3.1 选股偏离（Unplanned Trades）
检测逻辑：
对于 orders 中每笔买入委托：
  1. 在最近一次 decision_log 的 candidates 中查找该 code
  2. 如果找不到 → flaw: "计划外买入"  severity: warning
  3. 如果找到但 action == "watch" → flaw: "观察股误买"  severity: warning
  4. 如果找到且 action == "buy" → 正常，不产生 flaw
输入：
- orders 中 bs_flag == "buy" 的记录
- 当日（或前一交易日）decision_log.jsonl 最新条目的 candidates[]
边界情况：
- 当日无 decision_log 记录 → 所有买入均标记为 "无交易计划日的买入"，severity: info
- 委托被撤销（status 含 "撤"） → 跳过，不检测
- 同一股票多笔买入 → 每笔独立检测
3.2 遗漏执行（Missed Execution）
检测逻辑：
对于 decision_log 最新条目中 action == "buy" 的 candidates：
  1. 在 orders 中查找是否有该 code 的买入委托
  2. 如果没有 → flaw: "推荐买入未执行"  severity: info
  3. 在 positions 中查找是否已持有（之前已买）→ 如果已持有则跳过
设计考量：
- severity 为 info 而非 warning，因为用户可能有合理理由不买入
- 如果是 score >= 80 的高分推荐且未买入 → 提升为 warning
3.3 择时瑕疵（Timing Flaws）
检测逻辑（买入方向）：
对于每笔成交的买入委托：
  1. 获取该股当日分钟K线
  2. 计算日内价格区间 [day_low, day_high]
  3. 计算 VWAP = sum(amount) / sum(volume) / 10000
  4. 买入价位置 = (buy_price - day_low) / (day_high - day_low)
  判定:
  - 位置 > 0.67 → flaw: "追高买入"  severity: warning
  - 位置 > 0.80 → flaw: "严重追高"  severity: error
  - buy_price > VWAP * 1.02 → flaw: "买入价高于VWAP 2%+"  severity: info
检测逻辑（卖出方向）：
对于每笔成交的卖出委托：
  1. 同样获取分钟K线、计算价格位置
  2. 卖出价位置 = (sell_price - day_low) / (day_high - day_low)
  判定:
  - 位置 < 0.33 → flaw: "恐慌卖出"  severity: warning
  - 位置 < 0.20 → flaw: "严重恐慌卖出"  severity: error
  - sell_price < VWAP * 0.98 → flaw: "卖出价低于VWAP 2%+"  severity: info
timing_score 输出：
每笔成交交易输出一个 timing_score 对象：
{
    "code": "000001",
    "name": "平安银行",
    "direction": "buy",          # buy / sell
    "price": 10.82,              # 成交价
    "vwap": 10.65,               # 当日VWAP
    "day_high": 11.05,
    "day_low": 10.50,
    "position_pct": 0.58,        # 价格在日内区间的位置 (0-1)
    "vs_vwap_pct": 1.6,          # 相对VWAP偏离 %
    "grade": "B",                # A/B/C/D 评级
}
评级标准：
- A: 买入在下 1/3 或 卖出在上 1/3
- B: 买入在中 1/3 或 卖出在中 1/3
- C: 买入在上 1/3 或 卖出在下 1/3
- D: 买入在上 20% 或 卖出在下 20%
3.4 仓位瑕疵（Position Sizing Flaws）
检测逻辑：
1. 读取 active.yaml 中的限制：
   - trend_stock.position: "单只不超过总仓位20%"  → max_single_trend = 0.20
   - theme_stock.position: "单只不超过总仓位15%"  → max_single_theme = 0.15
   - market_position: strong=60-80%, neutral=30-50%, weak=10-20%
2. 从 positions 中计算：
   - total_assets = positions.total
   - 每只持仓的 market_value / total_assets = single_pct
3. 检测单股超限：
   - single_pct > 0.20 → flaw: "单股仓位超限"  severity: warning
   - single_pct > 0.30 → severity: error
4. 检测总仓位 vs 市场模式：
   - 从最近 decision_log 获取 market_regime
   - total_position_pct = (total - usable) / total
   - 与 market_position[regime] 对比
   - 如 regime=weak 但仓位>30% → flaw: "弱市重仓"  severity: warning
5. 检测总仓位 vs 账户模式：
   - account_pnl_pct = hold_earn / total
   - 映射到 account_mode (growth/normal/defensive/critical)
   - defensive 模式下仓位 > 50% → flaw: "防御模式仓位过高"  severity: warning
   - critical 模式下有任何持仓 → flaw: "危急模式仍有持仓"  severity: error
position_check 输出：
{
    "total_assets": 100000.0,
    "usable_cash": 40000.0,
    "total_position_pct": 60.0,         # 总仓位 %
    "market_regime": "neutral",
    "account_mode": "normal",
    "account_pnl_pct": 5.2,             # 账户盈亏 %
    "regime_position_range": "30-50%",   # 策略建议区间
    "single_stock_max_pct": 18.5,        # 最大单股仓位 %
    "single_stock_max_name": "平安银行",
    "compliant": true,                   # 是否合规
}
3.5 持仓管理瑕疵（Holding Management Flaws）
检测逻辑：
对于 positions 中的每只持仓：
1. 止损检测：
   - 获取最近 20 日 daily kline
   - 计算 MA20 = 最近20日收盘价均值
   - 如果 current_price < MA20：
     - 查历史持仓记录，连续几日低于 MA20
     - 低于 MA20 达 3 日 → flaw: "未执行MA20止损"  severity: error
     - 低于 MA20 达 1-2 日 → flaw: "逼近MA20止损线"  severity: info
2. 止盈检测：
   - 计算 MA5 = 最近5日收盘价均值
   - deviation = (current_price - MA5) / MA5
   - deviation > 0.15 → flaw: "偏离MA5超15%未减仓"  severity: warning
   - deviation > 0.20 → severity: error
3. 恶化持仓检测：
   - 如果 hold_earn（该股持仓盈亏）< -10% 且连续持有 > 5个交易日
   - flaw: "持续亏损持仓未处理"  severity: warning
数据依赖：
- fetch_jrj_daily_kline(code, range_num=30) — 获取30日K线计算MA
- 历史持仓快照 load_history(days=5) — 判断连续低于MA20的天数
- 并发获取：多只持仓的K线数据用 ThreadPoolExecutor 并行拉取
3.6 纪律执行瑕疵（Discipline Violations）
检测逻辑：
1. 防御/危急模式加仓：
   - 当前 account_mode == "defensive" or "critical"
   - orders 中有买入委托
   - flaw: "防御模式下加仓"  severity: error
2. 频繁翻转交易：
   - 查最近 5 个交易日的 orders 历史
   - 如果同一只股票在 3 天内既有买入又有卖出
   - flaw: "频繁翻转交易"  severity: warning
3. 分散持仓（可选）：
   - 持仓超过 8 只
   - flaw: "持仓过于分散"  severity: info
---
四、输出 Schema
4.1 trade_review.json 完整结构
{
  review_date: 2026-02-24,
  generated_at: 2026-02-24T15:30:00+08:00,
  account_snapshot: {
    total_assets: 100000.0,
    usable_cash: 40000.0,
    day_earn: 1200.0,
    hold_earn: 5200.0,
    position_count: 3,
    account_mode: normal,
    account_pnl_pct: 5.2
  },
  execution_summary: {
    total_orders: 5,
    buy_orders: 3,
    sell_orders: 2,
    cancelled_orders: 1,
    planned_buys: 2,
    unplanned_buys: 1,
    missed_buys: 0,
    plan_match_rate: 66.7
  },
  flaws: [
    {
      category: unplanned_trade,
      severity: warning,
      code: 002345,
      name: 潮宏基,
      message: 计划外买入: 该股不在当日推荐列表中,
      detail: {
        buy_price: 12.50,
        buy_amount: 1000
      }
    }
  ],
  timing_scores: [
    {
      code: 000001,
      name: 平安银行,
      direction: buy,
      price: 10.82,
      vwap: 10.65,
      day_high: 11.05,
      day_low: 10.50,
      position_pct: 0.58,
      vs_vwap_pct: 1.6,
      grade: B
    }
  ],
  position_check: {
    total_assets: 100000.0,
    usable_cash: 40000.0,
    total_position_pct: 60.0,
    market_regime: neutral,
    account_mode: normal,
    account_pnl_pct: 5.2,
    regime_position_range: 30-50%,
    single_stock_max_pct: 18.5,
    single_stock_max_name: 平安银行,
    compliant: true
  },
  flaw_counts: {
    error: 0,
    warning: 1,
    info: 2,
    total: 3,
    by_category: {
      unplanned_trade: 1,
      missed_execution: 0,
      timing_flaw: 0,
      position_flaw: 0,
      holding_flaw: 1,
      discipline_flaw: 1
    }
  },
  improvement_suggestions: [
    当日存在1笔计划外买入，建议严格按照推荐列表执行,
    持仓「平安银行」已连续2日低于MA20，明日需关注止损
  ],
  metadata: {
    strategy_version: v1.0,
    decision_log_date: 2026-02-24,
    decision_log_run_id: 20260224-review-143000,
    data_completeness: {
      broker_data: true,
      decision_log: true,
      minute_kline: true,
      daily_kline: true
    }
  }
}
---
五、模块内部结构
5.1 文件分块计划
trade_review.py 预计 400-500 行，分以下逻辑区块：
区块1: 模块 docstring + 导入 + 常量 + 类型定义        (~40行)
区块2: 数据加载层（读 decision_log、strategy、broker）  (~60行)
区块3: 选股偏离分析 _check_unplanned_trades()          (~40行)
区块4: 遗漏执行分析 _check_missed_execution()          (~35行)
区块5: 择时分析 _analyze_timing()                      (~70行)
区块6: 仓位合规检查 _check_position_compliance()        (~60行)
区块7: 持仓管理检查 _check_holding_management()         (~70行)
区块8: 纪律检查 _check_discipline()                    (~40行)
区块9: 汇总 + 建议生成 _generate_suggestions()          (~40行)
区块10: 主入口 run_trade_review() + CLI main()          (~50行)
5.2 关键函数签名
# ── 数据加载 ──
def _load_latest_decision(log_path: str, target_date: str) -> dict | None
def _load_strategy(yaml_path: str) -> dict
def _parse_position_limits(strategy: dict) -> dict
# ── 六类检测（每个返回 list[dict]） ──
def _check_unplanned_trades(orders: list, candidates: list) -> list[dict]
def _check_missed_execution(orders: list, candidates: list, positions: list) -> list[dict]
def _analyze_timing(orders: list) -> tuple[list[dict], list[dict]]  # (flaws, scores)
def _check_position_compliance(positions: dict, strategy: dict, regime: str) -> tuple[list[dict], dict]
def _check_holding_management(hold_list: list, history: dict) -> list[dict]
def _check_discipline(orders: list, account_mode: str, history: dict) -> list[dict]
# ── 汇总 ──
def _count_flaws(flaws: list[dict]) -> dict
def _generate_suggestions(flaws: list[dict], timing_scores: list) -> list[str]
# ── 主入口 ──
def run_trade_review(
    broker_data: dict | None = None,
    decision_log_path: str = ".memory/decision_log.jsonl",
    strategy_path: str = "strategy/active.yaml",
    output_path: str = "trade_review.json",
) -> dict
5.3 account_mode 计算逻辑
def _determine_account_mode(total: float, hold_earn: float) -> str:
    """根据 active.yaml 中的 account_mode 规则判定当前模式。"""
    if total <= 0:
        return "normal"
    pnl_pct = hold_earn / total
    if pnl_pct <= -0.30:
        return "critical"
    elif pnl_pct <= -0.10:
        return "defensive"
    elif pnl_pct >= 0.20:
        return "growth"
    else:
        return "normal"
> 注意：hysteresis_days: 3 规则需要历史数据支持。首版实现先用单日判定，后续迭代加入滞后逻辑。
---
六、并发与性能设计
6.1 K线数据并发获取
持仓管理检查和择时分析都需要 K线数据。合并所有需要的股票代码后统一并发获取：
codes_needing_daily = set(pos["code"] for pos in hold_list)
codes_needing_minute = set(order["code"] for order in filled_orders)
all_codes = codes_needing_daily | codes_needing_minute
with ThreadPoolExecutor(max_workers=min(8, len(all_codes))) as pool:
    daily_futures = {code: pool.submit(fetch_jrj_daily_kline, code, 30) for code in codes_needing_daily}
    minute_futures = {code: pool.submit(fetch_jrj_minute_kline, code) for code in codes_needing_minute}
6.2 费用控制
- JRJ K线：完全免费，无频率限制顾虑（但仍设 max_workers=8 避免过激）
- JVQuant：仅 fetch_broker_account() 调用一次，ticket 缓存复用
- 总费用：每次复盘 0 ~ 0.5 元（仅 ticket 过期时产生登录费用）
---
七、输出文件与演进反馈
7.1 trade_review.json
主输出文件，结构见第四节。存放在 skill 工作目录，供 SKILL.md 的 LLM 读取并生成用户可读报告。
7.2 evolution/feedback.md 追加
每次复盘后，将关键统计追加到 evolution/feedback.md：
 2026-02-24 交易复盘
- 瑕疵: 0 error / 1 warning / 2 info
- 择时评分: 买入均分 B, 卖出均分 A
- 仓位合规: 通过
- 关键问题: 1笔计划外买入（潮宏基）
7.3 evolution/known_pitfalls.md 追加
当 error 级别瑕疵出现时，追加到 pitfalls 记录：
 2026-02-24: 未执行MA20止损
- 股票: 平安银行(000001)
- 连续低于MA20: 4天
- 持仓亏损: -8.5%
- 教训: MA20止损规则必须严格执行，不可因"感觉要反弹"而拖延
---
八、错误处理与降级策略
| 场景 | 处理方式 |
|------|---------|
| broker_account 获取失败 | 跳过全部分析，输出 {"error": "broker_data_unavailable"} |
| decision_log 无当日记录 | 跳过选股偏离和遗漏执行检测，其余正常 |
| 某只股票 K线获取失败 | 该股跳过择时分析，生成 info 级 flaw: "K线数据缺失" |
| active.yaml 读取失败 | 使用内置默认值（20% 单股上限） |
| 当日无委托 | 仅执行持仓管理检查，跳过择时和选股偏离 |
所有异常均 logger.exception() 记录，不抛出，确保部分数据缺失时仍能输出可用结果。
---
九、测试计划
9.1 单元测试覆盖
class TestTradeReview(unittest.TestCase):
    # 选股偏离
    def test_unplanned_buy_detected(self): ...
    def test_watch_stock_bought_detected(self): ...
    def test_planned_buy_no_flaw(self): ...
    # 遗漏执行
    def test_missed_buy_detected(self): ...
    def test_already_held_not_flagged(self): ...
    # 择时分析
    def test_chasing_high_detected(self): ...
    def test_panic_sell_detected(self): ...
    def test_timing_grade_calculation(self): ...
    # 仓位检查
    def test_single_stock_over_limit(self): ...
    def test_weak_market_heavy_position(self): ...
    def test_defensive_mode_constraint(self): ...
    # 持仓管理
    def test_ma20_stop_loss_missed(self): ...
    def test_ma5_deviation_take_profit(self): ...
    # 纪律
    def test_defensive_mode_new_buy(self): ...
    def test_flip_trading_detected(self): ...
    # 集成
    def test_full_review_with_mock_data(self): ...
    def test_no_orders_day(self): ...
    def test_no_decision_log(self): ...
9.2 测试数据
所有测试使用构造的 mock 数据，不依赖网络。通过 unittest.mock.patch 替换 fetch_jrj_daily_kline 和 fetch_jrj_minute_kline。
---
十、实现顺序
| 步骤 | 内容 | 预计行数 | 依赖 |
|------|------|---------|------|
| 1 | 骨架：导入、常量、类型、主入口签名 | ~40 | 无 |
| 2 | 数据加载：decision_log、strategy 解析 | ~60 | 步骤1 |
| 3 | 选股偏离 + 遗漏执行检测 | ~75 | 步骤2 |
| 4 | 择时分析（依赖 minute kline） | ~70 | 步骤1 |
| 5 | 仓位合规检查 | ~60 | 步骤2 |
| 6 | 持仓管理检查（依赖 daily kline + history） | ~70 | 步骤1 |
| 7 | 纪律检查 | ~40 | 步骤2 |
| 8 | 汇总、建议生成、JSON 输出、CLI | ~50 | 步骤3-7 |
| 9 | 单元测试 | ~200 | 步骤8 |
| 10 | 部署到 ~/clawd/skills/ | - | 步骤9 |
写入策略：每步单独写入文件，验证语法后再写下一步。避免一次性写入大文件导致工具中断。
---
十一、首版限制与后续迭代
首版不做（明确排除）
1. hysteresis_days 滞后判定 — 需要连续多日数据积累，首版用单日判定
2. 股票分类（趋势股 vs 题材股）— 首版统一用 20% 上限，后续从 decision_log 的 tag 区分
3. 自动策略参数调整 — 首版只输出建议，不自动修改 active.yaml
4. Telegram 推送 — 复用已有的 send_telegram_file.py，但不在本模块内集成
后续迭代方向
1. T+1/T+5 收益追踪：与 decision_log 的 outcome 字段联动
2. 周度/月度汇总：聚合多日 trade_review.json 生成周报
3. 瑕疵趋势图：可视化各类瑕疵出现频率随时间的变化
4. 策略参数自动推荐：基于瑕疵统计推荐 active.yaml 参数调整
