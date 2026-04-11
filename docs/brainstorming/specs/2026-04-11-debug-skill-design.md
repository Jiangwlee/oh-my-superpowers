# Skill Design: debug

独立调试 skill，将 `coding-orchestrator` 中已验证的调试方法论与编码行为约束抽离为可直接调用的自治能力。

## 目录

1. [能力定义](#能力定义)
2. [设计模式](#设计模式)
3. [目录结构](#目录结构)
4. [SKILLmd-frontmatter-草稿](#skillmd-frontmatter-草稿)
5. [设计方案](#设计方案)
6. [渐进式披露规划](#渐进式披露规划)
7. [Trigger Eval](#trigger-eval)
8. [行动原则](#行动原则)
9. [行动计划](#行动计划)
10. [T1 测试计划](#t1-测试计划)

## 能力定义

- 封装的工具/规范/脚本：日志驱动调试流程、调试时的编码行为约束、调试边界与禁止行为。
- 核心价值：「它让模型能够在测试失败或行为异常时，按统一流程定位根因并做最小修复，而不是猜测式乱改。」
- 能力边界：
  - 能做：调试 failing tests、定位异常行为、约束调试过程中的改动方式。
  - 不能做：任务拆分、sub-agent 编排、story/task 管理、handoff 恢复。

## 设计模式

- 主模式：`Pipeline`
- 组合模式：`Tool Wrapper`
- 选择理由：核心是带检查点的调试流程，同时用 references 封装项目内部的调试与编码规范。

## 目录结构

```text
skills/debug/
├── SKILL.md
├── references/
│   ├── coding-guideline.md
│   └── debugging-guideline.md
└── tests/
    └── test_static.py
```

无 `scripts/` 目录。该 skill 纯知识型，不需要 CLI。

## SKILL.md Frontmatter 草稿

```yaml
---
name: debug
description: >-
  Systematic debugging for failing tests, runtime errors, and unexpected
  behavior. Use when you can reproduce a bug and need to find the root cause
  with logs and targeted inspection. Do NOT use for feature design, task
  orchestration, or speculative rewrites.
---
```

## 设计方案

`debug` 从 `coding-orchestrator` 中内化两类知识，但去掉 orchestrator 语境：

1. `debugging-guideline.md`
   - 提供 6 步调试法：列原因、加诊断日志、读日志、缩小范围、修复验证、清理痕迹。
   - 保留差分调试、二分定位、最小复现等方法。
   - 明确禁止 YOLO fixing、shotgun debugging、trial-and-error loop。

2. `coding-guideline.md`
   - 从 `constitution.md` 提炼 4 条对调试最关键的行为原则：
     - Think Before Coding
     - Simplicity First
     - Surgical Changes
     - Goal-Driven Execution
   - 作用不是指导“完整开发流程”，而是约束调试时不要过度修复和隐式扩写需求。

`SKILL.md` 只保留骨架：

1. 先确认问题可复现，不能复现先补足复现条件。
2. 先读 `references/coding-guideline.md`，校准改动边界。
3. 再读 `references/debugging-guideline.md`，按日志驱动流程定位根因。
4. 只做最小修复，验证原失败用例和相关回归。
5. 清理临时日志和调试痕迹。

关键设计决定：

- 不复用 `coding-orchestrator/references/constitution.md` 路径，避免破坏 skill 自治。
- 不引入脚本，避免把“调试”误做成一个 CLI 工具；这里封装的是规范和工作流。
- 不引入 `worker-guideline.md`，因为那是 orchestrator 分发语境，不适合作为独立 skill 的一部分。

## 渐进式披露规划

- `SKILL.md body`：触发边界、调试 checklist、何时加载哪份 reference。
- `references/coding-guideline.md`：调试过程中的编码行为约束。
- `references/debugging-guideline.md`：调试方法论与反模式。

## Trigger Eval

- 应触发：
  - “帮我 debug 一下这个 failing test”
  - “这个功能行为不对，帮我定位 root cause”
  - “运行报错了，先别乱改，系统化查一下”
- 不应触发：
  - “帮我设计一个新功能”
  - “帮我 orchestrate 多个 agent 做开发”
  - “帮我顺手重构一下这个模块”

## 行动原则

1. `Zero-Context Entry`：`SKILL.md` 前 20 行要能说明职责、触发和边界。
2. `Break, Don't Bend`：不依赖 `coding-orchestrator` 文件路径，所有必要知识都内化到 `debug`。
3. `Minimum Blast Radius`：只抽调试直接相关内容，不把 orchestrator 的任务管理语义带进来。
4. `Explicit Contract`：禁止行为、修复边界、验证要求都写明，不依赖隐式理解。

## 行动计划

### Task 1: 创建设计文档

产出：`docs/brainstorming/specs/2026-04-11-debug-skill-design.md`

内容：
- 定义能力边界
- 明确 references 拆分原则
- 写清楚为何不依赖 `coding-orchestrator`

### Task 2: 创建 `skills/debug/SKILL.md`

产出：`skills/debug/SKILL.md`

内容：
- frontmatter
- checklist 式调试流程
- 引导按需读取两份 references

### Task 3: 内化 references

产出：
- `skills/debug/references/coding-guideline.md`
- `skills/debug/references/debugging-guideline.md`

要求：
- 去除 worker/orchestrator 角色依赖
- 保留对调试最关键的行为准则和方法论

### Task 4: 添加 T1 静态测试

产出：`skills/debug/tests/test_static.py`

检查：
- `SKILL.md` 存在、frontmatter 正确
- 无相对路径脚本调用
- 两份 reference 存在且非空

### Task 5: 完成核查

- 确认 `skills/debug` 不依赖项目中其他 skill 文件
- 运行 T1 测试
- 对照本设计文档确认无静默偏离

## T1 测试计划

- `python -m unittest skills/debug/tests/test_static.py`
- 必要时补充 `python -m py_compile skills/debug/tests/test_static.py`
