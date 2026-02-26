# unified-memory 部署指南

## 架构概览

```text
项目目录
├── skills/unified-memory/                 # 源码（SKILL + scripts）
└── .memory/                               # 运行时记忆库（首次使用自动创建）
    ├── memories.jsonl                     # 结构化记忆（事实源）
    └── INDEX.md                           # topic 索引（可重建）

Claude Code / OpenCode / Codex
└── 调用 unified-memory CLI
    ├── add/search/show/topics
    ├── autoload-topics                    # /mem-autoload 后端
    └── prune/rebuild-index
```

`unified-memory` 当前是**项目级记忆**方案：每个项目独立维护自己的 `.memory/`。

---

## 一、前置要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 运行 `memory_cli.py` |
| Claude Code | 最新版（可选） | 若需 hooks 自动化 |
| OpenCode | 最新版（可选） | 若需 plugin 自动化 |
| Codex | 当前版本（可选） | 使用手动命令或 wrapper |

> MVP 不依赖第三方 Python 包，仅使用标准库。

---

## 二、首次部署（本地）

### 2.1 部署 Skill（源码 → 运行环境）

按你的编码工具选择部署位置（示例）：

```bash
# Claude Code（个人技能目录示例）
cp -r skills/unified-memory/ ~/.claude/skills/unified-memory/

# Codex（个人技能目录示例）
cp -r skills/unified-memory/ ~/.agents/skills/unified-memory/

# OpenCode（如果你通过 skills 目录方式管理）
cp -r skills/unified-memory/ ~/.config/opencode/skills/unified-memory/
```

> 仅修改 `skills/unified-memory/` 源码目录；部署目录是副本，不直接修改。

### 2.2 基础功能验证

在任意项目目录下执行（建议先切到一个测试项目）：

```bash
# 查看 topic（首次为空）
python3 /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" topics || python /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" topics

# 写入一条记忆
python3 /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add \
  --topic coding_preferences \
  --content "修改前先阅读 AGENTS.md 与相关 Skill 指南。" \
  --source explicit_user_memory || \
python /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add \
  --topic coding_preferences \
  --content "修改前先阅读 AGENTS.md 与相关 Skill 指南。" \
  --source explicit_user_memory

# 检索验证
python3 /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" search "AGENTS" || python /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" search "AGENTS"
```

执行后会自动创建：

```text
$PWD/.memory/memories.jsonl
$PWD/.memory/INDEX.md
```

---

## 三、`/mem-autoload` 部署与使用

`/mem-autoload` 的目标是：**只加载 Top 20 memory topics，不加载内容**。

### 3.1 后端命令

```bash
python3 /path/to/unified-memory/scripts/mem_autoload.py || python /path/to/unified-memory/scripts/mem_autoload.py
```

等价命令：

```bash
python3 /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20 || python /path/to/unified-memory/scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20
```

### 3.2 输出示例

```text
[mem-autoload] top topics (3):
- coding_preferences
- deployment_rules
- test_requirements
```

### 3.3 各工具映射建议（MVP）

说明：本 skill 不会自动安装 slash command 文件。需要按平台格式手动添加命令文件或别名。

- Claude Code：不依赖 custom slash command（官方文档已弱化/未强调），优先 hooks 或手动执行。
- Codex：使用平台要求的 slash command 文件格式（你反馈为 YAML）或 shell alias。
- OpenCode：使用 `~/.opencode/commands/*.md`（Markdown）命令文件。


#### Claude Code（如你仍使用本地 custom command）

将 `/mem-autoload` 映射为执行：

```bash
python3 ~/.claude/skills/unified-memory/scripts/mem_autoload.py || python ~/.claude/skills/unified-memory/scripts/mem_autoload.py
```

#### OpenCode

在 plugin/slash-command 配置中，将 `/mem-autoload` 映射为：

```bash
python3 ~/.config/opencode/skills/unified-memory/scripts/mem_autoload.py || python ~/.config/opencode/skills/unified-memory/scripts/mem_autoload.py
```

#### Codex

若无原生 slash 命令，使用 shell alias 代替：

```bash
alias mem-autoload='python3 ~/.agents/skills/unified-memory/scripts/mem_autoload.py || python ~/.agents/skills/unified-memory/scripts/mem_autoload.py'
```

> Codex 在当前 MVP 中未接入 hooks。`compacting`/退出会话时的自动记忆需要 wrapper 或平台级事件支持；否则请在退出前手动执行一次记忆检查点（按 `SKILL.md` 的 Session Capture Rules 提炼并写入）。

---

## 四、Claude Code（可选）自动化接入

> 本仓库当前已实现 CLI 与 Skill；hooks 自动化接入可后续补充。

建议接入事件：

1. `SessionStart`：读取高权重 topics / 或 Top-N 记忆
2. `UserPromptSubmit`：检测“请记住 xxx”并写入 memory
3. `PreCompact`：会话压缩前提炼长期信息（自动会话记忆）
4. `SessionEnd`：会话结束时提炼长期信息（自动会话记忆）

接入方式建议：

1. hooks 脚本只做参数解析与事件转发
2. 所有读写统一调用 `memory_cli.py`
3. hook 注入上下文时遵循官方 hooks JSON 输出格式

---

## 五、OpenCode（可选）自动化接入

> 本仓库当前已实现 CLI 与 Skill；plugin 自动化接入可后续补充。

建议接入事件：

1. `session.start`：topic / memory autoload
2. `message.sent`：识别显式“请记住”
3. `session.compacted`：compact 后提炼长期信息（自动会话记忆）

接入方式建议：

1. plugin 内部调用 `memory_cli.py`
2. 与 Claude Code 共享同一 `.memory/` 文件协议
3. 优先注入 topics，再按需检索内容，避免上下文膨胀

---

## 六、更新部署

修改 `unified-memory` 后重新复制部署目录：

```bash
# Claude Code
cp -r skills/unified-memory/ ~/.claude/skills/unified-memory/

# Codex
cp -r skills/unified-memory/ ~/.agents/skills/unified-memory/

# OpenCode
cp -r skills/unified-memory/ ~/.config/opencode/skills/unified-memory/
```

若只更新脚本，可增量复制：

```bash
cp skills/unified-memory/scripts/memory_cli.py ~/.claude/skills/unified-memory/scripts/
cp skills/unified-memory/scripts/mem_autoload.py ~/.claude/skills/unified-memory/scripts/
```

---

## 七、目录结构说明

```text
skills/unified-memory/
├── SKILL.md
├── DEPLOYMENT.md
├── scripts/
│   ├── memory_cli.py          # 核心 CLI（唯一读写入口）
│   └── mem_autoload.py        # /mem-autoload wrapper
└── tests/
    └── test_memory_cli.py
```

运行时目录（项目级）：

```text
.memory/
├── memories.jsonl             # 结构化记忆列表（append + rewrite）
└── INDEX.md                   # topic 索引（rebuild-index 重建）
```

---

## 八、手动验证清单

```bash
# 1. 单测
python3 -m unittest skills/unified-memory/tests/test_memory_cli.py || python -m unittest skills/unified-memory/tests/test_memory_cli.py

# 2. 语法检查
python3 -m py_compile skills/unified-memory/scripts/memory_cli.py skills/unified-memory/scripts/mem_autoload.py || python -m py_compile skills/unified-memory/scripts/memory_cli.py skills/unified-memory/scripts/mem_autoload.py

# 3. 功能验证（项目目录内）
python3 skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add --topic test_note --content "这是测试记忆" || python skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add --topic test_note --content "这是测试记忆"
python3 skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20 || python skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" autoload-topics --limit 20
python3 skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" rebuild-index || python skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" rebuild-index
```

- [ ] 测试通过
- [ ] 无语法错误
- [ ] `.memory/` 自动创建
- [ ] `/mem-autoload`（或等价命令）仅返回 topic
- [ ] `INDEX.md` 成功生成

---

## 九、常见问题

**Q: `memory_cli.py` 提示找不到 `.memory/`**

正常。CLI 会在首次写入或重建索引时自动创建 `.memory/`。

**Q: `add` 被拒绝并提示 sensitive content**

命中了敏感信息拦截（例如 token/private key/cookie）。请改写为非敏感摘要后再保存。

**Q: `/mem-autoload` 没有返回任何 topic**

先写入至少一条 `active` 记忆：

```bash
python3 skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add \
  --topic coding_preferences \
  --content "修改前先阅读 AGENTS.md" || \
python skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" add \
  --topic coding_preferences \
  --content "修改前先阅读 AGENTS.md"
```

**Q: 想清理旧记忆并保留高权重条目**

执行：

```bash
python3 skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" prune --max-items 200 || python skills/unified-memory/scripts/memory_cli.py --project-dir "$PWD" prune --max-items 200
```
