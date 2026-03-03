# 交易信号系统改进设计

## 背景与问题

### 交易哲学
趋势跟随，只做上升趋势中的人气股。选股池为东方财富人气前200，选股逻辑不变。

### 已完成改进
- 买入信号已从"日线MA5/10 ±1%回调"改为"5周均线 ±3%回调"（`watchlist_monitor.py`）
- 已切换 JRJ 周K线数据源

### 当前仍存在的缺陷

1. **5周均线方向未验证**：只判断"价格是否在均线附近"，未判断均线本身是否向上。
   均线在下行时价格贴近均线，不是买点是逃离点。
   → 直接导致网宿科技连续4天发出错误买入信号。

2. **无出场信号**：系统只有买入信号，持仓后无任何止损/止盈提示，
   盈利不知何时兑现，亏损不知何时止损。

3. **两套信号并行，制造混乱**：
   - `watchlist_monitor.py` → 新逻辑 → `watchlist_signals.json`
   - `trend_scanner.py` → 旧逻辑（日线MA±1%）→ `watchlist_scan.json`
   两套系统同时运行，容易依赖旧信号（错误系统）做决策。

---

## 改进范围

**仅修改信号逻辑，不改选股池。**

---

## 三处具体改动

### 改动一：`watchlist_monitor.py` — 加入均线方向验证

**位置**：`_analyze_signal()` 函数，在现有"跌破5周均线直接排除"之后。

**逻辑**：
```python
# 5周均线必须向上倾斜（当前MA5W > 3周前MA5W）
if len(weekly_closes) >= 8:
    ma5w_prev = sum(weekly_closes[-8:-3]) / 5
    if ma5w_now <= ma5w_prev:
        return None  # 均线方向向下，趋势无效
```

**效果**：
- 消灭"均线下行+价格贴近均线→买入"的误判
- 确保只在趋势上行期间买入

---

### 改动二：`watchlist_monitor.py` — 加入持仓出场信号

**新增函数**：`_check_exit_signals(holdings, kline_map) -> list[StockSignal]`

**输入**：当前持仓列表（从 broker_account 读取）

**逻辑**：
- 对每只持仓股，获取5周均线
- 若**本周收盘 < 5周均线** → signal = `stop_loss`，原因："收盘跌破5周均线"
- 若**本周收盘 > 5周均线 × 1.25** → signal = `take_profit_partial`，原因："超涨25%，建议减仓"

**输出格式**（写入 `watchlist_signals.json` 新增 `exits` 字段）：
```json
{
  "scanned_at": "...",
  "market": {...},
  "signals": [...],
  "watched": [...],
  "exits": [
    {
      "code": "603256",
      "name": "宏和科技",
      "signal": "stop_loss",
      "price": 76.21,
      "ma5_week": 78.5,
      "reason": "收盘跌破5周均线"
    }
  ]
}
```

**出场规则**（完整）：
| 条件 | 信号类型 | 操作建议 |
|------|---------|---------|
| 收盘 < 5周均线 | `stop_loss` | 止损出局 |
| 收盘 > 5周均线 × 1.25 | `take_profit_partial` | 减仓50%，剩余跟踪 |

---

### 改动三：`trend_scanner.py` — 移除交易信号输出

**位置**：`_trade_signal_from_ma()` 函数

**改动**：将函数返回值固定为 `("观察", "趋势扫描仅供研究，交易信号见 watchlist_monitor")`，
不再输出"买入"/"卖出"信号。

`trend_scanner.py` 退化为**纯研究工具**（评分、趋势分析），不再作为操作信号来源。

**效果**：系统只有一个信号来源 `watchlist_signals.json`，消除混乱。

---

## 数据依赖

| 数据 | 来源 | 已有？ |
|------|------|-------|
| 5周K线 | JRJ | ✅ |
| 实时报价 | 现有 | ✅ |
| 当前持仓 | broker_account | ✅ |
| 当日情绪 | market_sentiment | ✅ |

---

## 不在本次改动范围内

- 选股池变更（人气前200保留）
- 自动下单执行
- 持仓规模管理（仓位大小）
- 回测验证

---

## 成功标准

1. 网宿科技场景重现：均线方向向下时，即使价格贴近5周均线也不发出买入信号
2. 持仓跌破5周均线时，`exits` 字段出现对应 `stop_loss` 条目
3. `watchlist_scan.json` 中不再出现"买入"/"卖出"字样（只有"观察"）
