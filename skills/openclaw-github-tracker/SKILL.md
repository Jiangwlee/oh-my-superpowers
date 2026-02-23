---
name: openclaw-github-tracker
description: >
  GitHub trending repository tracker with daily briefs, watchlist monitoring, and deep project analysis.
  Use when:
  (1) user asks "看看今天GitHub热门"、"今日GitHub趋势"、"生成GitHub日报"、"github trending",
  (2) user says "深度分析某个项目"、"分析这个仓库"、"建立项目档案"、"clone下来看看",
  (3) user asks "我的关注列表有更新吗"、"watchlist更新"、"关注项目动态".
version: "2.0.0"
---

# GitHub 趋势追踪与项目分析

<HARD-GATE>
**NO DEEP ANALYSIS WITHOUT --deep FLAG.**
Default analysis uses API only (~2s per repo). Git clone only when user explicitly requests deep analysis.

**NO DAILY BRIEF COMPLETION WITHOUT WRITING MARKDOWN FILE FIRST.**
Scene 1 completes only after `.memory/github-tracker/briefs/daily/YYYY-MM-DD.md` is written.

**NO TRENDING DATA WITHOUT BROWSER VERIFICATION.**
Must verify URL is github.com/trending (not weekly/monthly) before extraction.

**NO WEB_FETCH FOR GITHUB PAGES.**
GitHub is a SPA — web_fetch only returns shell HTML with no content. Browser tool is mandatory.
</HARD-GATE>

**Red Flags（常见规避借口）**

| 借口 | 现实 |
|------|------|
| "用户没明确要保存文件" | 场景1 默认要落盘 Markdown 日报，不是只在对话里口头总结 |
| "只抓到 8 个项目，先生成报告" | < 10 个视为提取失败，必须重新滚动页面提取 |
| "weekly 数据也是 trending" | 必须是 daily，URL 不对则重新导航 |
| "用户没说 deep，但我想分析深一点" | 无 --deep 则只用 API，不 clone |
| "用 web_fetch 看看页面结构" | 禁止，GitHub SPA 只返回壳，必须用 Browser |
| "tab 还有用，先不关" | 提取完成后立即关闭，避免资源积累 |

---

## Prerequisite Check (REQUIRED)

**STOP and resolve before proceeding:**

1. **GitHub CLI**: `command -v gh` → Install: https://cli.github.com
2. **Authentication**: `gh auth status` → Run `gh auth login` if needed
3. **Python 3.10+**: `python3 --version`
4. **Browser**: `openclaw browser status` → Run `openclaw browser start` if needed

---

## 核心使用场景

本 Skill 支持三个独立场景，根据用户意图自动选择：

### 场景1：每日简报（默认）
**触发词**："看看今天GitHub热门"、"今日GitHub趋势"、"生成GitHub日报"、"github trending"

**输出**：Markdown 日报（`.md`），包含：
- 当日 Trending 完整列表（10-15个项目）
- 每个项目的功能描述、技术栈、增长数据
- 关注列表(Watchlist)项目的一日更新汇总
- 统计数据与趋势分析

**执行时间**：~30秒（浏览器 + API，无需clone）

### 场景2：深度项目分析
**触发词**："深度分析某个项目"、"分析这个仓库"、"建立项目档案"、"clone下来看看"

**输出**：项目完整 Profile，包含：
- 代码结构分析（需clone）
- 技术栈详细扫描
- 架构信号与模块划分
- Roadmap 与里程碑分析

**执行时间**：~15秒（含git clone）

**必须加 --deep 参数**：
```bash
python3 scripts/analyze_project.py owner/repo --deep
```

### 场景3：关注列表监控
**触发词**："我的关注列表有更新吗"、"watchlist更新"、"关注项目动态"

**输出**：关注项目的变更摘要（Stars/Forks/Issues变化）

**执行时间**：~5秒 × 项目数量

---

## 场景1：生成每日简报（Markdown 报告）

### Step 1: 获取 Trending 数据

```bash
python3 scripts/fetch_trending.py \
  --memory-root .memory
```

**⚠️ GitHub 是 SPA，禁止使用 web_fetch**。必须使用 Browser 工具：

1. `openclaw browser open https://github.com/trending`
2. 验证 URL 是 `/trending`（不是 `/trending/weekly`）
3. 滚动页面，提取所有项目数据（目标 ≥10 个）
4. 提取完成后立即关闭 tab：
   ```bash
   openclaw browser tabs                     # 获取 targetId
   openclaw browser tab close <targetId>     # 关闭 trending tab
   ```

### Step 2: 生成简报数据

```bash
python3 scripts/fetch_trending.py \
  --memory-root .memory \
  --data-json '[
    {"repo":"facebook/react","what_it_does":"A declarative, efficient, and flexible JavaScript library","tech_stack":"JavaScript, TypeScript","stars":"220000","stars_today":"45"},
    ...
  ]'
```

### Step 3: 获取 Watchlist 更新

```bash
python3 scripts/track_updates.py \
  --memory-root .memory
```

### Step 4: 生成综合日报

> **STEP 0**：生成前先读输出格式模板 `references/formats.md §1 (Daily Brief)`，基于模板生成，不要从零重建。

```bash
python3 scripts/generate_daily_report.py \
  --memory-root .memory \
  --date $(date +%Y-%m-%d)
```

**输出位置**: `.memory/github-tracker/briefs/daily/YYYY-MM-DD.md`

**报告内容**:
- 📊 今日概览（项目数、总 Star、语言分布）
- 🔥 热门项目详解（功能、技术栈、Star 增长、热度分析）
- 📌 关注列表更新（Stars/Forks/Release 变更）
- 💡 今日洞察（趋势总结、建议关注）

---

## 场景2：深度项目分析

**仅在用户明确要求时使用 `--deep`**

```bash
# 快速分析（默认，~2秒）
python3 scripts/analyze_project.py \
  owner/repo \
  --memory-root .memory

# 深度分析（含git clone，~15秒）
python3 scripts/analyze_project.py \
  owner/repo \
  --memory-root .memory \
  --deep
```

### 快速分析输出（API only）
- 基础信息（description, stars, forks, license）
- 语言统计
- 最近更新时间
- README 内容

### 深度分析输出（含clone）
- 代码目录结构扫描
- 技术栈标记文件检测（package.json, Cargo.toml等）
- 模块架构分析
- 里程碑与发布版本详情

---

## 场景3：关注列表监控

```bash
# 批量检查 watchlist 中所有项目
python3 scripts/track_updates.py \
  --memory-root .memory
```

如果 watchlist 为空或不存在，先初始化：
参考 `references/formats.md §3 (Update Note)` 了解数据格式，然后编辑或创建 `.memory/github-tracker/watchlist.json`：
```json
[
  {"repo": "owner/repo", "added_at": "YYYY-MM-DD"}
]
```

输出每个项目的变更摘要：
- Stars/Forks/Issues 数量变化
- 最新 Release 信息
- 最近 Commit 活动

---

## Guardrails

### 场景识别约束
| 用户输入 | 识别的场景 | 必须执行的操作 |
|---------|-----------|--------------|
| "今天GitHub热门" | 场景1: 每日简报 | 生成并落盘 Markdown 日报 |
| "深度分析X项目" | 场景2: 深度分析 | 加 --deep 参数 |
| "关注列表更新" | 场景3: Watchlist | 批量检查更新 |

### 性能约束
- **默认不clone**: 除非用户明确说"深度分析"或"clone"
- **并行处理**: 批量分析时使用 ThreadPoolExecutor
- **缓存机制**: 24小时内重复分析同一仓库使用缓存

### 输出约束
- **落盘优先**: 日报必须先写入 `.memory/github-tracker/briefs/daily/YYYY-MM-DD.md`
- **完整性**: Trending必须包含所有项目（≥10个）
- **功能性**: 每个项目必须有"what_it_does"描述

---

## 常见错误

| 错误场景 | 原因 | 解决 |
|---------|------|------|
| 分析太慢 | 误用了深度模式 | 检查是否有 --deep 参数 |
| 项目数量不足 | 浏览器提取不完整 | 重新滚动页面提取 |
| Weekly数据 | URL错误 | 确保是 github.com/trending |
| Trending 抓取内容为空 | 误用了 web_fetch | 改用 Browser 工具 |

---

## Configuration

```bash
# HTTP代理
export GITHUB_TRACKER_HTTP_PROXY="http://127.0.0.1:10801"
export GITHUB_TRACKER_HTTPS_PROXY="http://127.0.0.1:10801"

# 或编辑 config.json
```

---

## Pre-Execution Checklist

- [ ] 识别正确的使用场景（1/2/3）
- [ ] 场景1: 日报 `.md` 已落盘到 `.memory/github-tracker/briefs/daily/`
- [ ] 场景1: 验证 github.com/trending URL正确（非 weekly/monthly）
- [ ] 场景1: 确保所有项目包含功能描述（≥10个）
- [ ] 场景1: Browser tab 用后已关闭（trending tab）
- [ ] 场景2: 确认是否需要 --deep
- [ ] 场景3: 确认 watchlist.json 存在

**Terminal state**：
- 场景1：Markdown 日报已写入 `.memory/github-tracker/briefs/daily/`，trending tab 已关闭
- 场景2：Profile 文件已写入 `.memory/github-tracker/projects/`
- 场景3：所有 watchlist 项目变更摘要已输出
