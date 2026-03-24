---
name: markdown-to-anything
description: >
  Use when converting local Markdown files into publishable outputs.
  (1) "转成PDF"/"导出PDF"/"转成图片"/"导出PNG"/"导出文件"
  (2) "高质量图片"/"卡片风格"/"海报"/"好看一点"/"设计感"
---

# Markdown To Anything

把本地 Markdown 变成可交付产物的通用 Skill。
SKILL.md 负责 SOP 与路径分发；`scripts/` 负责确定性执行。

## Iron Law

NO EXPORT WITHOUT CHOOSING THE PATH FIRST.

先判断两件事：
1. 用户要的是 **标准导出**（PDF / 普通 PNG）还是 **高质量视觉图**
2. 输入是 **clean**、**light dirty** 还是 **semantic dirty**

- 高质量图片 / 海报 / 卡片 / 设计感 -> 路径2（视觉图）
- 其他导出请求 -> 路径1（标准程序化导出）
- light dirty -> 先调用脚本清洗
- semantic dirty -> 先由 Agent 提取 clean markdown，再调用脚本

## Preflight checks

开始前必须检查：
- 输入文件存在且是本地 `.md`
- 输出目标明确（pdf / png / html）
- 依赖可用：`python3`、`node`、`chromium`，以及优先使用的 `pandoc`
- 输入是否需要清洗：先运行 `scripts/inspect_input.py`

## 路径1：标准程序化导出

适合：
- 转成 PDF
- 转成图片 / 导出 PNG
- 快速导出完整文档

标准 SOP：
1. 运行 `python scripts/inspect_input.py <input.md> --json`
2. 若 `cleanliness=light_dirty`，运行 `python scripts/normalize_input.py <input.md> --output <clean.md> --json`
3. 若 `cleanliness=semantic_dirty`，**停止脚本流程**，由 Agent 先整理正文
4. 运行 `python scripts/convert.py <input.md> --mode report --format pdf|png|html --stdout-manifest`
5. 查看 manifest 中的 `files / warnings / errors`

常用命令：

```bash
python scripts/convert.py report.md --mode report --format pdf --same-dir --stdout-manifest
python scripts/convert.py report.md --mode report --format png --same-dir --stdout-manifest
python scripts/convert.py report.md --mode report --format pdf --keep-html --keep-clean --stdout-manifest
```

## 路径2：高质量视觉图

适合：
- 高质量图片
- 海报风格
- 卡片风格
- 好看一点 / 设计感

SOP：
1. Agent 先阅读 Markdown，提炼成适合视觉表达的内容
2. Agent 生成或整理 SVG / 视觉布局
3. 再调用 `node scripts/screenshot.js --png <input.html_or_svg> <output.png> 3 1080 0`
4. 可用 `python scripts/validate_output.py <output.png> --json` 做产物检查

最小约束：
- SVG 根元素必须带 `xmlns="http://www.w3.org/2000/svg"`
- 默认画布 `1080x1920`
- 正文字号建议 `>= 40px`
- meta 字号建议 `>= 28px`

## Dirty input handling

把清洗分成两类：

### Light dirty -> scripts
适合脚本做：
- fenced markdown 提取
- assistant 前言剥离
- BOM / 换行 / 首尾空白处理

对应脚本：

```bash
python scripts/inspect_input.py input.md --json
python scripts/normalize_input.py input.md --output input.clean.md --json
```

### Semantic dirty -> Agent first
如果脚本无法可靠判断正文边界，Agent 必须先处理，例如：
- 删除带语义歧义的解释段落
- 重排正文结构
- 从对话回答中提取真正要发布的 Markdown

处理完成后，再把 clean markdown 交给 `scripts/convert.py`。

## 输出规范

优先使用：

```bash
python scripts/convert.py <input.md> --stdout-manifest
```

manifest 至少包含：
- `files`: 最终产物
- `intermediate_files`: 中间 HTML
- `inspection`: 输入洁净度判断
- `normalization`: 是否清洗、是否需要 Agent
- `engine`: 使用的渲染引擎
- `warnings` / `errors`

## 更多参考

按需阅读：
- CLI 参数：`references/cli-params.md`
- 标准导出 SOP：`references/sop-standard-export.md`
- 脏输入 SOP：`references/sop-dirty-input.md`
- 视觉图 SOP：`references/sop-visual-card.md`
- 调试命令：`references/debug-commands.md`
- 依赖与降级：`references/dependencies.md`
- 字号规格：`references/font-spec.md`
- Chrome 导出细节：`references/chrome-cdp.md`
- 开发说明：`references/dev-guide.md`
