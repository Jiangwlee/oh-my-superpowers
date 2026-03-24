# Skill Design: <name>

## 能力定义
- 封装的工具/规范/脚本：<具体描述>
- 核心价值：「它让模型能够 ___」
- 能力边界：能做 / 不能做

## 设计模式
- 主模式：<pattern>
- 组合模式（如有）：<pattern>
- 选择理由：<一句话说明>

## 目录结构
<根据模式生成>

## CLI 化方案（如适用）
- 命令接口：`<command> <args>` → `<output format>`
- 暴露方式：<omp 注册 / 独立 CLI>

## SKILL.md Frontmatter 草稿
```yaml
---
name: <skill-name>
description: >-
  <核心价值一句话>
  Use when: <场景>
  Do NOT use when: <排除场景>
metadata:
  pattern: <pattern>
---
```

## 渐进式披露规划
- SKILL.md body：<列出内容>
- references/：<列出文件及职责>
- assets/：<列出模板文件>

## Trigger Eval
- 应触发：<场景>
- 不应触发：<场景>

## T1 测试计划
- <需要验证的机械检查项>
