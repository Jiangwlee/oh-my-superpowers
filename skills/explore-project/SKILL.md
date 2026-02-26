---
name: explore-project
description: 项目代码知识库，积累跨会话的结构化研究笔记（.memory/research/）。Use whenever about to read or explore project code — check existing notes before exploring. Also use when: (1) 用户要求分析、理解项目代码或某个功能；(2) 用户说"看看代码"、"研究一下"、"这是怎么实现的"；(3) 编码任务需要先理解相关代码背景。Do NOT trigger for direct code modification tasks.
---

# explore-project

项目代码探索与知识积累工具。每次探索只更新**本次实际读过的笔记**，其他笔记保持不变。

## 知识库结构

```
.memory/research/
  ├── INDEX.md          ← topic 索引，按时间倒序排列
  └── topics/
      ├── <topic>.md    ← 每个 topic 一个文件（必须有 TOC 在前10行）
```

---

## Workflow

### Step 1：查阅已有知识

**1a.** 检查 `.memory/research/INDEX.md` 是否存在：
- 不存在 → 跳到 Step 2
- 存在 → 读取 INDEX.md，识别与当前任务可能相关的 topics

**1b.** 对每个候选 topic，**只读该文件的前10行（TOC）**，判断是否与当前任务相关：
- 相关 → 读取完整笔记
- 不相关 → 跳过，**不读全文**

### Step 2：探索代码

用 Glob / Grep / Read 完成当前任务所需的代码探索。

### Step 3：懒更新笔记

<EXTREMELY-IMPORTANT>
只处理 Step 1b 中读过完整内容的 topic，以及本次新发现的 topic：

- 笔记与代码一致 → 不修改
- 笔记有过时或缺失内容 → 更新该文件
- 发现值得记录的新 topic → 新建 topics/&lt;topic&gt;.md
- **只读了 TOC 的 topic 文件：绝不修改**
- **未读到的 topic 文件：绝不修改**
</EXTREMELY-IMPORTANT>

### Step 4：更新 INDEX.md

- 新增 topic 追加到顶部
- 修改过的 topic 更新日期
- 未改动的 topic 不动

---

## Topic 笔记格式（严格遵守）

前10行是 TOC，必须包含足够的信息让LLM判断是否需要读全文：

```markdown
# <Topic 标题>

Last updated: YYYY-MM-DD
Covers: <涉及的主要文件，用逗号分隔>
Summary: <一句话：这个 topic 记录了什么>

## 目录
- [范围](#范围) - <一句话>
- [关键发现](#关键发现) - <一句话>
- [注意点](#注意点) - <一句话>

---

## 范围
涉及哪些文件/模块（用 `file:line` 格式标注关键位置）

## 关键发现
架构决策、设计模式、重要实现细节

## 注意点
已知坑、边界条件、容易误解的地方
```

## INDEX.md 格式

```markdown
# Research Index

- [topic-name.md](topics/topic-name.md) - YYYY-MM-DD
- [another-topic.md](topics/another-topic.md) - YYYY-MM-DD
```

第一行是最新更新的 topic，按时间倒序排列。

---

## Guardrails

- **查阅顺序不可颠倒**：先读 INDEX → 读候选 topic 的前10行 TOC → 再决定是否读全文
- **不要为了"完整性"读所有 topic**——只读 TOC 判断相关性，不相关直接跳过
- **不要创建过细的笔记**——每个 topic 代表一个有意义的逻辑单元，不是每个文件对应一个笔记
- **笔记是给 Claude 读的**——简洁、技术性，不需要对人类友好的叙述
- **每个 topic 文件控制在 80 行以内**——超出时合并或拆分
