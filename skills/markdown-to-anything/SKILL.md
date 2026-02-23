---
name: markdown-to-anything
description: Use when a skill or user needs to convert Markdown into Telegram-friendly outputs (PNG summary card and/or PDF report), asks for Markdown rendering/export, report image/pdf generation, or a reusable markdown-to-image/markdown-to-pdf pipeline. Supports two card modes: (1) LLM-direct SVG — LLM creates the SVG visually, then screenshot.js converts to PNG (recommended for high-quality, designed cards); (2) programmatic templates via convert.py (fast, structured).
---

# Markdown To Anything

通用 Markdown 渲染与导出 Skill。
输入是 Markdown 文本或 `.md` 文件，输出可以是：
- `PNG`（摘要卡，适合 Telegram 发图）
- `PDF`（完整报告，适合阅读）
- `HTML`（中间产物，调试或 PDF 之前检查）

## 适用边界

**适用**：任何“已生成 Markdown，下一步要渲染/导出”的场景。

**不负责**：
- 业务数据抓取
- 业务分析/摘要生成（调用方可先做摘要，再把 Markdown 交给本 skill）
- Telegram 发送

## LLM 直出 SVG 模式（推荐用于高品质摘要卡）

程序化模板只能生成机械排版。如需更美观的视觉设计，**由 LLM 自行创作 SVG，再交本 skill 转 PNG**。

### 触发时机

用户或调用方说"高品质卡片"、"设计感"、"好看一点"、"自由风格"时，**优先走本路线**。

### 画布规格（LLM 写 SVG 时必须遵守）

| 项目 | 值 |
|------|-----|
| 尺寸 | `1080 × 1920`（竖版 9:16） |
| 命名空间 | `xmlns="http://www.w3.org/2000/svg"` |
| 背景 | 深色推荐：`#0d1117` / `#1c2432` |
| 强调色 | `#58a6ff` |
| 正文色 | `#e6edf3` |
| 辅助色 | `#8b949e` |
| 推荐字体 | `-apple-system,'PingFang SC','Noto Sans CJK SC',sans-serif` |
| 推荐字号 | 标题 60–72px，副标题 32–36px，正文 40–48px |
| 安全边距 | 左右各留 56px；文字结束 x < 1024，y < 1900 |

### 防文字重叠规则（必须遵守）

- 每行文字竖向间距 ≥ 字号 × 1.5
- 单行文字宽度估算：CJK 字符 ≈ 字号 px，ASCII ≈ 字号 × 0.6 px
- 不同文字元素之间 y 方向至少留 字号 × 0.5 px 空隙

### 工作流

```bash
# 1. LLM 将 Markdown 内容创作为 SVG，写入文件
#    SVG 根元素必须是: <svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">

# 2. SVG → PNG（Chrome CDP 渲染）
node scripts/screenshot.js --png /tmp/card_llm.svg /tmp/card_llm.png 3 1080 0

# 3. 可选：校验布局（检查溢出和文字重叠）
python scripts/validator.py /tmp/card_llm.svg --json
# 如果 ok=false，根据错误信息修正 SVG 后重新执行步骤 2
```

> `screenshot.js --png <svg_file> <png_file> <dpr> <width> 0`
> - dpr=3 对应 iPhone 高清屏，实际输出为 `3240 × 5760` px（3× 超采样）
> - dpr=2 输出 `2160 × 3840` px

---

## 快速使用（程序化通道）

### 1) 自动选择通道（默认）

```bash
python scripts/convert.py report.md --stdout-manifest
```

`--mode auto`（默认）会按结构复杂度自动选择 `card` 或 `report`。

### 2) 强制摘要卡（PNG）

```bash
python scripts/convert.py report.md \
  --mode card \
  --format png \
  --theme dark \
  --font-size medium \
  --stdout-manifest
```

### 3) 强制完整报告（PDF）

```bash
python scripts/convert.py report.md \
  --mode report \
  --format pdf \
  --theme blue \
  --stdout-manifest
```

### 4) 同时输出摘要卡 + 完整 PDF

```bash
python scripts/convert.py report.md \
  --mode auto \
  --format both \
  --stdout-manifest
```

## CLI 参数（主入口）

`python scripts/convert.py <input.md> [options]`

- `--mode auto|card|report`：通道选择（默认 `auto`）
- `--format png|pdf|both`：输出格式（未指定时按 mode 默认）
- `--theme dark|blue`：主题（默认 `dark`）
- `--font-size small|medium|large`：字号档位（默认 `medium`）
- `--output <path>`：输出文件或输出基路径
- `--template <name>`：强制指定 card 模板（覆盖自动选择）
- `--engine auto|pandoc|marked|fallback`：report 通道 Markdown 渲染后端
- `--stdout-manifest`：输出 JSON manifest（推荐调用方使用）
- `--prefer-cdp-validator`：card 校验优先走 Chrome `getBBox()`

## 调试子命令（按需）

### 分析 Markdown 结构

```bash
python scripts/analyze.py report.md --pretty
```

### 单独生成 SVG 摘要卡

```bash
python scripts/card_render.py report.md \
  --output /tmp/card.svg \
  --template hero-summary \
  --stdout-result
```

### 校验 SVG 布局

```bash
python scripts/validator.py /tmp/card.svg --json
# 或（本机有 node + Chrome 时）
python scripts/validator.py /tmp/card.svg --prefer-cdp --json
```

### 单独生成 HTML / PDF

```bash
python scripts/report_render.py report.md --output /tmp/report.html --format html --stdout-result
python scripts/report_render.py report.md --output /tmp/report.pdf --format pdf --stdout-result
```

## 依赖与降级

- `pandoc`：report 通道首选 Markdown→HTML 后端（可选）
- `node` + `Google Chrome/Chromium`：PNG/PDF 渲染与 CDP 校验所需
- 无 `pandoc` 时：优先使用 `scripts/vendor/marked.min.js`
- `marked` 不可用时：回退到内置 Python Markdown 渲染（结构化 HTML，不是纯 `pre`）

## 输出与错误语义（调用方建议）

推荐调用方始终读取 `--stdout-manifest`：
- `files`：生成的文件列表
- `warnings`：降级、字体、依赖等非致命信息
- `errors`：致命错误（非空时命令退出非0）

## 开发与测试

```bash
python -m unittest discover -s skills/markdown-to-anything/tests -p "test_*.py"
python -m py_compile skills/markdown-to-anything/scripts/*.py
```

## 参考资料

- Chrome CDP 渲染/截图/PDF：`references/chrome-cdp.md`
