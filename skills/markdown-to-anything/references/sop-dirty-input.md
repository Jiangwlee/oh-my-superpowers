# SOP：脏输入处理

本 skill 把脏输入分成两类。

## 1. light dirty

典型特征：
- 外层有 ```markdown 包装
- 有常见 assistant 前言
- 主要正文仍是完整 Markdown

处理方式：

```bash
python scripts/inspect_input.py input.md --json
python scripts/normalize_input.py input.md --output input.clean.md --json
python scripts/convert.py input.clean.md --format pdf --stdout-manifest
```

## 2. semantic dirty

典型特征：
- 需要理解哪些段落该保留
- 对话内容和正文混在一起
- 仅靠脚本无法安全提取正文

处理方式：
- Agent 先阅读原文
- 生成 clean markdown
- 再调用 `convert.py`

## 原则

- scripts 只做确定性清洗
- 需要语义判断时，必须由 Agent 介入
- 不要让脚本“猜”正文边界