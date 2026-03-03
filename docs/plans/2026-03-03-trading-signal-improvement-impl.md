# Trading Signal Improvement (Phase 1) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `watchlist_monitor` 从评分制信号升级为 `SETUP -> ENTRY -> HOLD/REDUCE/EXIT` 状态机，并输出结构化交易信号。

**Architecture:** 在 `watchlist_monitor.py` 内新增参数层与状态持久化层，重写信号计算与出场规则，最后统一输出新 JSON 结构。测试以 `test_watchlist_monitor.py` 覆盖状态迁移、触发条件、风控分支。

**Tech Stack:** Python 3.10+, unittest, dataclasses, JSON file persistence

---

### Task 1: 参数与状态存储基础

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py`
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`

**Step 1: Write the failing test**

新增测试：配置缺省值可回退、`pullback_state.json` 读写与坏数据容错。

**Step 2: Run test to verify it fails**

Run: `python -m unittest packages.ashare-data.tests.test_watchlist_monitor -v`  
Expected: 相关新测试失败。

**Step 3: Write minimal implementation**

在 `watchlist_monitor.py` 增加：
- `_PULLBACK_STATE_FILE` 常量；
- 参数默认字典与读取函数；
- `_load_pullback_state()` / `_save_pullback_state()`。

**Step 4: Run test to verify it passes**

Run: `python -m unittest packages.ashare-data.tests.test_watchlist_monitor -v`  
Expected: 新增配置/状态测试通过。

**Step 5: Commit**

```bash
git add packages/ashare-data/ashare_data/watchlist_monitor.py packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "feat: add watchlist signal params and pullback state persistence"
```

### Task 2: SETUP/ENTRY 状态机信号重写

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py`
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`

**Step 1: Write the failing test**

新增测试覆盖：
- 满足回撤条件只产出 `SETUP`；
- 突破 `PB_HIGH`+量能回归+收阳才产出 `ENTRY`；
- 趋势破坏或数据不足返回 `None/NONE`。

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s packages/ashare-data/tests -p "test_watchlist_monitor.py"`  
Expected: 状态机相关测试失败。

**Step 3: Write minimal implementation**

重写 `_analyze_signal()`：
- 计算 `ma20d/ma5w/ma20w/dev5w/dev20w/vr20d/drawdown20`；
- 执行趋势过滤；
- 管理 `SETUP` 状态与 `PB_HIGH/PB_LOW` 更新；
- 满足确认条件输出 `ENTRY`；
- 其他趋势完整场景输出 `HOLD`。

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s packages/ashare-data/tests -p "test_watchlist_monitor.py"`  
Expected: 状态机测试通过。

**Step 5: Commit**

```bash
git add packages/ashare-data/ashare_data/watchlist_monitor.py packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "feat: implement setup-trigger state machine for watchlist signals"
```

### Task 3: 出场信号和输出结构升级

**Files:**
- Modify: `packages/ashare-data/ashare_data/watchlist_monitor.py`
- Test: `packages/ashare-data/tests/test_watchlist_monitor.py`

**Step 1: Write the failing test**

新增测试覆盖：
- 周线有效跌破触发 `EXIT`；
- 超涨/乖离过大触发 `REDUCE`；
- 输出 JSON 包含新字段（`state`, `position_target`, `action_next_day` 等）。

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s packages/ashare-data/tests -p "test_watchlist_monitor.py"`  
Expected: 出场/输出结构测试失败。

**Step 3: Write minimal implementation**

改造：
- `_check_exit_signals()` 按周线有效跌破与超涨规则输出 `EXIT/REDUCE`；
- `_write_signals()` 改为写统一 `signals`（状态机记录）；
- `main()` 集成状态读写与新输出逻辑。

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s packages/ashare-data/tests -p "test_watchlist_monitor.py"`  
Expected: 全通过。

**Step 5: Commit**

```bash
git add packages/ashare-data/ashare_data/watchlist_monitor.py packages/ashare-data/tests/test_watchlist_monitor.py
git commit -m "feat: emit structured watchlist states and quantified exit signals"
```

### Task 4: Phase 1 验证与交付

**Files:**
- Verify: `packages/ashare-data/ashare_data/watchlist_monitor.py`
- Verify: `packages/ashare-data/tests/test_watchlist_monitor.py`
- Verify: `docs/plans/2026-03-03-trading-signal-improvement-design.md`

**Step 1: Syntax check**

Run: `python -m py_compile packages/ashare-data/ashare_data/watchlist_monitor.py`

**Step 2: Full targeted test**

Run: `python -m unittest discover -s packages/ashare-data/tests -p "test_watchlist_monitor.py"`

**Step 3: Share result summary**

输出：
- 已落地字段与状态；
- 关键阈值实际值；
- 下一阶段 assistant 侧改造入口文件。

