# 调试命令

## 校验 LLM SVG 布局

```bash
python scripts/validator.py /tmp/card_llm.svg --json
```

优先 Chrome `getBBox()`（本机有 Chrome + node 时）：

```bash
python scripts/validator.py /tmp/card_llm.svg --prefer-cdp --json
```

## 单独生成 HTML / PNG / PDF（报告链）

```bash
python scripts/report_render.py report.md --output /tmp/report.html --format html --stdout-result
python scripts/report_render.py report.md --output /tmp/report.png --format png --theme light --stdout-result
python scripts/report_render.py report.md --output /tmp/report.pdf --format pdf --theme blue --stdout-result
```

## 直接调用截图后端

```bash
node scripts/screenshot.js --png /tmp/report.html /tmp/report.png 3 750 0
node scripts/screenshot.js --pdf /tmp/report.html /tmp/report.pdf 750
node scripts/screenshot.js --png /tmp/card_llm.svg /tmp/card_llm.png 3 1080 0
```
