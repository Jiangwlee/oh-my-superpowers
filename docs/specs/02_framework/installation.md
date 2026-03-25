# Installation

本文档定义 oh-my-superpowers 的安装设计：Bootstrap、omp 命令语义、局部与全局安装。

## 设计原则

1. **omp 是全局命令**，任何目录下均可调用
2. **默认局部安装**，不污染全局命名空间
3. **全局安装需显式 `--global` 标志**
4. **源码单一修改入口**，安装目录是只读副本（symlink）

---

## Bootstrap（一次性安装）

将 oh-my-superpowers 本体安装到固定目录，并注册 omp 到 PATH：

```bash
./install.sh
```

**安装结果：**

```
~/.oh-my-superpowers/        ← 项目副本（symlink 或 clone）
~/.local/bin/omp             ← symlink → ~/.oh-my-superpowers/bin/omp
```

**为什么是 `~/.oh-my-superpowers/`：**
- 与 `~/.oh-my-zsh/` 同一惯例，项目名直接映射
- 路径固定 → Skills 中的 CLI 可使用绝对路径 `~/.oh-my-superpowers/scripts/...`
- 用户易于发现和管理

**PATH 要求：**`~/.local/bin` 必须在 PATH 中（多数现代 Linux/macOS 默认已包含）。

---

## omp 命令

### install

```bash
# 局部安装（安装到当前项目目录）
omp install skill <name>
omp install agent <name>

# 全局安装（安装到用户 home 下）
omp install skill <name> --global
omp install agent <name> --global
```

**局部安装目标：**

```
$PWD/.agents/skills/<name>/    ← symlink → ~/.oh-my-superpowers/skills/<name>/  （Pi）
$PWD/.claude/skills/<name>/    ← symlink → ~/.oh-my-superpowers/skills/<name>/  （Claude Code）
$PWD/.pi/agents/<name>.md      ← symlink → ~/.oh-my-superpowers/agents/<name>.md
```

**全局安装目标：**

```
~/.agents/skills/<name>/       ← symlink → ~/.oh-my-superpowers/skills/<name>/  （Pi）
~/.claude/skills/<name>/       ← symlink → ~/.oh-my-superpowers/skills/<name>/  （Claude Code）
~/.pi/agents/<name>.md         ← symlink → ~/.oh-my-superpowers/agents/<name>.md
```

Pi 的 Skill 发现路径：`~/.agents/skills/`（全局）和 `.agents/skills/`（局部，当前目录优先）。

### remove

```bash
omp remove skill <name>           # 移除当前目录的局部安装
omp remove skill <name> --global  # 移除全局安装
omp remove agent <name>
omp remove agent <name> --global
```

只删除 symlink，不删除 `~/.oh-my-superpowers/` 下的源文件。

### list

```bash
omp list                          # 列出已安装的 skills 和 agents（局部）
omp list --global                 # 仅列出全局安装
omp list --type skill             # 只列出 skills
omp list --type agent             # 只列出 agents
```

### test

```bash
omp test <name>                   # 运行指定 skill 的 T1 测试
```

### run

```bash
omp run <name> [--model TEXT] [prompt...]
# 示例：
omp run media-editor 今天有什么 AI 动态
omp run reviewer --model litellm-local/qwen3.5-27b review skills/foo
```

---

## Skill CLI 封装（CLI 化规范）

Skills 中的脚本必须封装为 CLI 命令，使模型可以用命令名调用，而无需关心路径。

**封装方式：**

```bash
# ~/.oh-my-superpowers/bin/omp-<skill>-<command>
# 或在 install 时注册到 ~/.local/bin/

#!/usr/bin/env bash
exec ~/.oh-my-superpowers/skills/<skill-name>/scripts/foo.sh "$@"
```

**SKILL.md 中只写 CLI 命令名**，不写路径：

```markdown
# 正确
Run: `omp-myskill fetch --date 2026-03-24`

# 错误
Run: `bash scripts/fetch.sh --date 2026-03-24`
```

---

## 目录结构总览

```
~/.oh-my-superpowers/       ← 安装后的源码位置
├── skills/
│   └── <name>/             ← 被 symlink 到 .agents/skills/<name>/
├── agents/
│   └── <name>.md           ← 被 symlink 到 .pi/agents/<name>.md
└── bin/
    └── omp                 ← 被 symlink 到 ~/.local/bin/omp

$PROJECT_ROOT/              ← 局部安装的目标（任意项目）
├── .agents/
│   └── skills/<name>/      ← symlink（Pi 读取）
├── .claude/
│   └── skills/<name>/      ← symlink（Claude Code 读取）
└── .pi/
    └── agents/<name>.md    ← symlink

~/                          ← 全局安装的目标
├── .agents/
│   └── skills/<name>/      ← symlink（Pi 读取）
├── .claude/
│   └── skills/<name>/      ← symlink（Claude Code 读取）
└── .pi/
    └── agents/<name>.md    ← symlink
```
