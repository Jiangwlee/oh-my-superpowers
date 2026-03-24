# 调试命令

## 1. 先看输入是否干净

```bash
python scripts/inspect_input.py report.md --json
```

如果返回：
- `clean` -> 可直接导出
- `light_dirty` -> 先跑 `normalize_input.py`
- `semantic_dirty` -> 先让 Agent 整理正文

## 2. 单独跑输入清洗

```bash
python scripts/normalize_input.py report.md --output /tmp/report.clean.md --json
```

适合排查：
- fenced markdown 提取是否正确
- assistant 前言是否被移除
- clean markdown 是否为空

## 3. 单独生成 HTML / PNG / PDF（标准报告链）

```bash
python scripts/report_render.py report.md --output /tmp/report.html --format html --stdout-result
python scripts/report_render.py report.md --output /tmp/report.png --format png --theme light --stdout-result
python scripts/report_render.py report.md --output /tmp/report.pdf --format pdf --theme blue --stdout-result
```

## 4. 直接调用主入口

```bash
python scripts/convert.py report.md --format pdf --same-dir --stdout-manifest
python scripts/convert.py report.md --format png --same-dir --keep-html --stdout-manifest
python scripts/convert.py report.md --format both --same-dir --keep-html --keep-clean --stdout-manifest
```

## 5. 直接调用截图后端

```bash
node scripts/screenshot.js --png /tmp/report.html /tmp/report.png 3 750 0
node scripts/screenshot.js --pdf /tmp/report.html /tmp/report.pdf 750
node scripts/screenshot.js --png /tmp/card_llm.svg /tmp/card_llm.png 3 1080 0
```

## 6. 校验导出产物

```bash
python scripts/validate_output.py /tmp/report.pdf --json
python scripts/validate_output.py /tmp/report.png --json
```

## 7. 校验 LLM SVG 布局

```bash
python scripts/validator.py /tmp/card_llm.svg --json
```

优先 Chrome `getBBox()`：

```bash
python scripts/validator.py /tmp/card_llm.svg --prefer-cdp --json
```

## 8. 典型排查顺序

1. `inspect_input.py`
2. `normalize_input.py`（如需要）
3. `report_render.py --format html`
4. `screenshot.js --pdf/--png`
5. `validate_output.py`

这样可以快速判断问题在：
- 输入内容
- markdown 渲染
- 浏览器导出
- 最终产物