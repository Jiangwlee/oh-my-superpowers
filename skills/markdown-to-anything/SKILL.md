---
name: markdown-to-anything
description: >
  Use when converting Markdown into shareable images or documents.
  (1) "转成图片"/"转成PDF"/"图片报告"/"导出PNG"/"导出文件" -> 程序化路径（MD -> HTML -> PNG/PDF）
  (2) "高质量图片"/"卡片风格"/"海报"/"好看一点"/"设计感"/"自由风格" -> LLM SVG 路径（LLM 自由 SVG -> PNG）
---

# Markdown To Anything

通用 Markdown 渲染与导出 Skill。输入 Markdown，输出 PNG / PDF / HTML（调试）。

## 路径分发（Iron Law）

NO PNG output WITHOUT checking trigger words FIRST.

- 质量触发词（高质量/海报/卡片/好看/设计感/自由风格） -> 路径2（LLM SVG）
- 其他触发词或无触发词 -> 路径1（程序化）
- No exceptions. 默认情况也走路径1。

## 路径1：程序化（MD -> HTML -> PNG/PDF）

适合“转成图片 / 转成PDF / 快速导出 / 图片报告 / PDF报告”。
PNG 与 PDF 共用 HTML 生成路径，只有 Chrome CDP 命令不同。

默认建议：
- `report + png` 使用 `light` 主题（浅色科技风）
- `report + pdf` 使用 `blue` 主题
- `--mode auto` 无触发词信息时默认输出 PDF

命令示例：

```bash
python scripts/convert.py report.md --mode report --format png --theme light --stdout-manifest
python scripts/convert.py report.md --mode report --format pdf --theme blue --stdout-manifest
python scripts/convert.py report.md --mode auto --stdout-manifest
```

## 路径2：LLM SVG（LLM -> SVG -> PNG）

适合“高质量图片 / 海报风格 / 卡片风格 / 好看一点 / 设计感”。
LLM 自由创作 SVG，不使用模板，只保留最小约束：

| 约束项 | 要求 |
|---|---|
| 画布 | 默认 `1080x1920`（全屏贴合可用 `1080x2340`） |
| 根元素 | 必须带 `xmlns="http://www.w3.org/2000/svg"` |
| 正文字号 | `>= 40px` |
| meta 字号 | `>= 28px` |

工作流：

```bash
# 1) LLM 生成 SVG（自由布局）
# 2) SVG -> PNG
node scripts/screenshot.js --png /tmp/card_llm.svg /tmp/card_llm.png 3 1080 0
# 3) 可选校验
python scripts/validator.py /tmp/card_llm.svg --json
```

防重叠提示：
- 行间距 >= 字号 x 1.5
- CJK 字宽约等于字号 px；ASCII 约为字号 x 0.6

## 输出

主入口建议使用 `python scripts/convert.py <input.md> --stdout-manifest`。

- `files`: 生成文件列表
- `warnings`: 非致命警告（降级/布局/依赖）
- `errors`: 致命错误（非空时命令非 0 退出）

## 更多参考

- CLI 完整参数：`references/cli-params.md`（需要调参数时读）
- 调试命令：`references/debug-commands.md`（遇到渲染问题时读）
- 字号规格：`references/font-spec.md`（需要调整字号时读）
- 依赖与降级：`references/dependencies.md`（环境不完整时读）
- 开发/测试：`references/dev-guide.md`（修改脚本时读）
- Chrome CDP 细节：`references/chrome-cdp.md`（调 screenshot.js 时读）
