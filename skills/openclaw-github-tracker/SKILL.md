---
name: openclaw-github-tracker
description: >
  GitHub trending repository tracker with daily briefs, watchlist monitoring, and deep project analysis.
  Use when: 
  (1) user asks "看看今天GitHub热门"、"今日GitHub趋势"、"生成GitHub日报"、"github trending", 
  (2) user says "深度分析某个项目"、"分析这个仓库"、"建立项目档案"、"clone下来看看",
  (3) user asks "我的关注列表有更新吗"、"watchlist更新"、"关注项目动态".
  Generates PDF reports for daily briefs. Fast analysis by default, deep analysis only on request.
version: "2.0.0"
---

# GitHub 趋势追踪与项目分析

<HARD-GATE>
**NO DEEP ANALYSIS WITHOUT --deep FLAG.**
Default analysis uses API only (~2s per repo). Git clone only when user explicitly requests deep analysis.

**NO PDF REPORT WITHOUT HTML GENERATION.**
Daily briefs MUST be converted to HTML and screenshot as PDF for delivery. Text-only output is emergency fallback only.

**NO TRENDING DATA WITHOUT BROWSER VERIFICATION.**
Must verify URL is github.com/trending (not weekly/monthly) before extraction.
</HARD-GATE>

## 核心使用场景

本 Skill 支持三个独立场景，根据用户意图自动选择：

### 场景1：每日简报（默认）
**触发词**："看看今天GitHub热门"、"今日GitHub趋势"、"生成GitHub日报"、"github trending"

**输出**：PDF 格式日报，包含：
- 当日 Trending 完整列表（25-30个项目）
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

## Prerequisite Check (REQUIRED)

**STOP and resolve before proceeding:**

1. **GitHub CLI**: `command -v gh` → Install: https://cli.github.com
2. **Authentication**: `gh auth status` → Run `gh auth login` if needed
3. **Python 3.10+**: `python3 --version`
4. **Browser**: Confirm OpenClaw browser available
5. **pandoc**: Optional but recommended for PDF generation

---

## 场景1：生成每日简报（PDF报告）

### Step 1: 获取 Trending 数据

```bash
# 运行脚本获取浏览器操作指令
python3 .agents/skills/openclaw-github-tracker/scripts/fetch_trending.py \
  --memory-root .memory
```

**然后使用 Browser 工具**：
1. 打开 `github.com/trending`
2. 验证 URL 是 `/trending`（不是 `/trending/weekly`）
3. 提取所有项目数据

### Step 2: 生成简报数据

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/fetch_trending.py \
  --memory-root .memory \
  --data-json '[
    {"repo":"facebook/react","what_it_does":"A declarative, efficient, and flexible JavaScript library","tech_stack":"JavaScript, TypeScript","stars":"220000","stars_today":"45"},
    ...
  ]'
```

### Step 3: 获取 Watchlist 更新

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/track_updates.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
```

### Step 4: 生成综合日报

使用脚本自动生成详细报告（整合 Trending + Watchlist 数据）：

```bash
python3 .agents/skills/openclaw-github-tracker/scripts/generate_daily_report.py \
  --memory-root .memory \
  --date 2026-02-22
```

**输出位置**: `.memory/github-tracker/briefs/daily/2026-02-22.md`

**报告内容**:
- 📊 今日概览（项目数、总 Star、语言分布）
- 🔥 热门项目详解（功能、技术栈、Star 增长、热度分析）
- 📌 关注列表更新（Stars/Forks/Release 变更）
- 💡 今日洞察（趋势总结、建议关注）

### Step 5: 转换为 PDF

```bash
# 生成 HTML
python3 .agents/skills/openclaw-github-tracker/scripts/report_to_html.py \
  .memory/github-tracker/briefs/daily/2026-02-22.md \
  --title "GitHub Trending 日报"

# 使用 Browser 工具打开 HTML 并截图保存为 PDF
# Browser: open file:///path/to/report.html
# Browser: screenshot --pdf report.pdf
```

**PDF 交付**: 通过手机友好的格式展示，包含：
- 顶部统计卡片
- 项目卡片式布局（带Star增长标签）
- 关注列表更新区域
- 底部生成时间戳

---

## 场景2：深度项目分析

**仅在用户明确要求时使用 `--deep`**

```bash
# 快速分析（默认，~2秒）
python3 .agents/skills/openclaw-github-tracker/scripts/analyze_project.py \
  owner/repo \
  --memory-root .memory

# 深度分析（含git clone，~15秒）
python3 .agents/skills/openclaw-github-tracker/scripts/analyze_project.py \
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
python3 .agents/skills/openclaw-github-tracker/scripts/track_updates.py \
  --memory-root .memory \
  --config .agents/skills/openclaw-github-tracker/config.json
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
| "今天GitHub热门" | 场景1: 每日简报 | 生成PDF报告 |
| "深度分析X项目" | 场景2: 深度分析 | 加 --deep 参数 |
| "关注列表更新" | 场景3: Watchlist | 批量检查更新 |

### 性能约束
- **默认不clone**: 除非用户明确说"深度分析"或"clone"
- **并行处理**: 批量分析时使用 ThreadPoolExecutor
- **缓存机制**: 24小时内重复分析同一仓库使用缓存

### 输出约束
- **PDF优先**: 日报必须生成PDF，仅当工具失败时才文本输出
- **完整性**: Trending必须包含所有项目（≥10个）
- **功能性**: 每个项目必须有"what_it_does"描述

---

## 常见错误

| 错误场景 | 原因 | 解决 |
|---------|------|------|
| 分析太慢 | 误用了深度模式 | 检查是否有 --deep 参数 |
| PDF生成失败 | pandoc未安装 | 安装pandoc或使用降级模式 |
| 项目数量不足 | 浏览器提取不完整 | 重新滚动页面提取 |
| Weekly数据 | URL错误 | 确保是github.com/trending |

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
- [ ] 场景1: 确认生成PDF报告
- [ ] 场景2: 确认是否需要 --deep
- [ ] 场景3: 确认watchlist.json存在
- [ ] 验证github.com/trending URL正确
- [ ] 确保所有项目包含功能描述
- [ ] PDF成功生成并准备交付
