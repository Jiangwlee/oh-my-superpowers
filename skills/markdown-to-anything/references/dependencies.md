# 依赖与降级

## 必需依赖（标准导出路径）

- `python3`
  - 运行 `convert.py` / `inspect_input.py` / `normalize_input.py`
- `node`
  - 运行 `scripts/screenshot.js`
- `Google Chrome` / `Chromium`
  - 用于 HTML -> PDF / PNG

## 可选依赖

- `pandoc`
  - Markdown -> HTML 首选引擎
  - 缺失时允许降级

- `scripts/vendor/marked.min.js`
  - 浏览器端 Markdown 渲染后备

## 当前 PDF 默认链路

```text
Markdown -> HTML -> Chromium print-to-pdf
```

## 当前 PNG 默认链路

```text
Markdown -> HTML -> Chromium screenshot
```

## Markdown -> HTML 降级顺序

```text
pandoc -> marked -> Python fallback
```

调用方应读取 manifest 中的：
- `engine`
- `warnings`
- `errors`

不要假设一定使用了 `pandoc`。

## 输入清洗分工

### scripts 负责
- 去 BOM
- 统一换行
- 去首尾空白
- fenced markdown 提取
- 常见 assistant 前言剥离

### Agent 负责
- 删除有语义歧义的说明段
- 重排正文结构
- 从对话回答中提取最终要发布的 markdown

如果 `inspect_input.py` 判断为 `semantic_dirty`，应停止脚本自动导出，先让 Agent 介入。

## 常见故障

### `python3 not found`
安装 Python 3 并确保在 PATH 中。

### `node not found`
安装 Node.js，确认 `node` 在 PATH 中。

### `Chrome not found`
安装 Google Chrome 或 Chromium。
`screenshot.js` 会尝试常见路径，包括：
- `/usr/bin/chromium`
- `/snap/bin/chromium`
- `/usr/bin/google-chrome`

### `pandoc not found`
不是致命错误。
主流程会尝试降级，但样式或 Markdown 支持可能变弱。

### `input requires agent semantic cleanup before export`
说明输入不是简单的壳层问题，而是需要 Agent 理解正文边界。
先整理 clean markdown，再重新运行 `convert.py`。

### `invalid PDF signature` / `invalid PNG signature`
说明导出产物文件已生成，但内容异常。
建议按以下顺序排查：
1. `report_render.py --format html`
2. `node scripts/screenshot.js --pdf/--png ...`
3. `validate_output.py`

## 产物建议

默认建议：
- 调试时加 `--keep-html`
- 脏输入排查时加 `--keep-clean`
- Agent 调用时优先加 `--stdout-manifest`