# 交易信号系统改进设计（Phase 1）

## 目标

对 `ashare-data` 完成完整数据侧重构，使交易信号由“评分型 buy_dip/watch”升级为可执行的状态机：

- 入场：`SETUP -> ENTRY` 两阶段；
- 出场：周线有效跌破止损 + 超涨减仓；
- 信号：统一结构化字段（状态、指标、建议仓位、T+1动作）；
- 参数：全部来自 `~/.ashare-assistant/config.json`；
- 状态：落盘到 `~/.ashare-assistant/memory/pullback_state.json`。

## 范围与非范围

### 范围

- 改造 `packages/ashare-data/ashare_data/watchlist_monitor.py`。
- 新增/调整 `packages/ashare-data/tests/test_watchlist_monitor.py`。
- 输出结构升级为状态机信号结构。

### 非范围

- 不改选股池来源（仍是东方财富人气榜逻辑）。
- 不改自动下单执行链路。
- 不改 assistant 侧文案消费（放在 Phase 2）。

## 设计决策

### 1. 状态机

每只股票按如下状态推进：

- `NONE`: 未满足条件；
- `SETUP`: 回撤健康，进入观察；
- `ENTRY`: 回撤结束确认，生成买点；
- `HOLD`: 趋势存在但不在买点；
- `REDUCE`/`EXIT`: 持仓管理信号。

核心是把“靠近 MA5W”从直接买点改成 `SETUP`，只有突破 `PB_HIGH` 才进入 `ENTRY`。

### 2. 状态持久化

在 `~/.ashare-assistant/memory/pullback_state.json` 存储每只股票：

- `pb_start_date`
- `pb_high`
- `pb_low`
- `updated_at`

扫描时读入、更新、回写。趋势破坏时清理状态，避免脏状态跨天残留。

### 3. 指标与阈值

统一量化指标：

- `ma5w`, `ma20w`, `ma20d`
- `dev5w`, `dev20w`
- `vr20d`
- `drawdown20`

统一参数（可配置）：

- `dev5w_band=0.03`
- `vr20d_shrink=0.80`
- `vr20d_expand=1.10`
- `pb_breakout_buffer=0.003`
- `intraday_break_allow=0.02`
- `ma5w_break_week=0.015`
- `fast_stop_pct=0.04`
- `dev20w_no_add=0.20`
- `dev20w_no_trade=0.25`
- `position_base=0.25`
- `position_yellow=0.15`

### 4. 输出结构

`watchlist_signals.json` 中每条信号输出：

- `state`
- `pb_start_date`, `pb_high`, `pb_low`
- `ma5w`, `ma20w`, `ma20d`
- `vr20d`, `dev20w`, `dev5w`
- `entry_price`, `stop_price`
- `position_target`
- `action_next_day`
- `reason`

不再输出旧语义 `buy_dip/watch`。

## 成功标准

1. 回到 MA5W 附近时仅进入 `SETUP`，不会直接给 `ENTRY`。
2. 仅当突破 `PB_HIGH + buffer` 且 `vr20d` 回归且收阳时，输出 `ENTRY`。
3. 价格进入加速区（`dev20w` 超阈值）不会输出加仓类信号。
4. 持仓满足“周线有效跌破”时输出 `EXIT`，满足超涨/乖离时输出 `REDUCE`。
5. 所有关键阈值从配置读取，测试覆盖状态转换和出场判定。
