# Openclaw Skills 内部机制深度分析

> 分析版本：OpenClaw 2026.2.17 (4134875)
> 分析时间：2026-02-19
> 核心源文件：`/opt/homebrew/lib/node_modules/openclaw/dist/skills-Cj-bjVUG.js`

---

## 一、Skills 加载的 6 个 Source

Openclaw 在 agent 启动时从 **6 个独立 source** 合并加载 skills，优先级从高到低：

| Source 名称 | 实际路径 | 说明 |
|-------------|---------|------|
| `openclaw-workspace` | `<workspace>/skills/` | Agent workspace 下的 skills（最高优先级） |
| `agents-skills-project` | `<workspace>/.agents/skills/` | 项目级开放规范目录 |
| `agents-skills-personal` | `~/.agents/skills/` | 个人全局开放规范目录 ⚠️ |
| `openclaw-managed` | `~/.openclaw/skills/` | openclaw 管理的全局 skills |
| `openclaw-extra` | 由 `config.skills.load.extraDirs` 配置 | 用户自定义扩展目录 |
| `openclaw-bundled` | openclaw 安装目录下的 `skills/` | 内置 skills（最低优先级） |

当前 workspace 为 `~/clawd`，因此各路径实例为：

```
~/clawd/skills/                  ← openclaw-workspace（已有 2 个 skill）
~/clawd/.agents/skills/          ← agents-skills-project（不存在）
~/.agents/skills/                ← agents-skills-personal（⚠️ 有 superpowers！）
~/.openclaw/skills/              ← openclaw-managed（目录不存在）
~/.openclaw/extensions/*/skills/ ← 插件携带的 skills（如 claude-mem）
/opt/homebrew/lib/node_modules/openclaw/skills/  ← openclaw-bundled（52 个内置 skill）
```

---

## 二、openclaw-bundled 路径解析逻辑

内置 skills 通过 `resolveBundledSkillsDir()` 函数动态定位，按以下优先级查找：

```
优先级 1：环境变量 OPENCLAW_BUNDLED_SKILLS_DIR（若设置则直接使用）
优先级 2：process.execPath 的同级 skills/ 目录
优先级 3：从 Node 模块目录向上遍历（最多 6 层），找到 looksLikeSkillsDir() 的目录
```

---

## 三、关键配置项

### `commands.nativeSkills`（易混淆！）

```json
"commands": {
    "native": "auto",
    "nativeSkills": "auto"
}
```

**这个配置与 skills 加载无关**，它控制的是 **Telegram/Discord 等聊天频道的斜杠命令（Slash Commands）**，决定是否把 skills 暴露为原生 bot 命令。不要误以为它是 skills 扫描开关。

### `skills.install.nodeManager`

```json
"skills": {
    "install": {
        "nodeManager": "npm"
    }
}
```

控制通过 clawhub 安装 skills 时使用的包管理器，不影响 skills 发现。

### `skills.load.extraDirs`（当前未配置）

若需要挂载额外目录，可在 `~/.openclaw/openclaw.json` 中添加：

```json
"skills": {
    "load": {
        "extraDirs": ["/path/to/custom/skills/"]
    }
}
```

对应 `openclaw-extra` source。

---

## 四、各平台的 Skills 加载目录对比

### Codex CLI 的加载路径

Codex 从以下路径加载 skills（已实机验证）：

| 路径 | 说明 |
|------|------|
| `~/.codex/skills/` | **Codex 专属全局**（含 `.system` 内置 skill） |
| `~/.agents/skills/` | 跨平台个人全局（开放规范） |
| `.agents/skills/` | 项目级（从 cwd 向上扫描至 repo root） |
| `/etc/codex/skills` | 系统级（管理员部署） |

`~/.codex/skills/` 是 Codex 的**私有全局目录**，扫描规则是递归查找任何含 `SKILL.md` 的子目录。OpenAI 在此安装内置 skill（`plan`、`skill-creator`），用户也可直接在此放自定义 skills。

### `~/.agents/skills/` 是跨平台开放标准

`~/.agents/skills/` 并非 openclaw 特有，而是 **Agent Skills 开放规范**约定的标准目录，多个 AI 平台共同遵循：

| 平台 | `~/.agents/skills/` | `~/.codex/skills/` | 平台专属全局目录 |
|------|--------------------|--------------------|----------------|
| **OpenAI Codex CLI** | ✅ | ✅（Codex 专属） | `~/.codex/skills/` |
| **OpenClaw** | ✅（`agents-skills-personal`） | ❌ | `~/.openclaw/skills/` |
| **Cursor** | ✅（项目级） | ❌ | — |
| **OpenCode** | ✅ | ❌ | — |
| **GitHub Copilot** | ✅（2026年加入） | ❌ | — |

---

## 五、Superpowers 出现在 Openclaw 的完整链路

```
安装来源：Codex 安装引导 (.codex/INSTALL.md)
    ↓
克隆至：~/.codex/superpowers/
    ↓
创建符号链接：
    ~/.agents/skills/superpowers  →  /Users/mindora/.codex/superpowers
    （Codex 的 personal skills 约定位置）
    ↓
Openclaw 启动时扫描 ~/.agents/skills/（agents-skills-personal source）
    ↓
发现链接目标中的 skills/ 子目录，加载其中 14 个 SKILL.md
    ↓
结果：superpowers 的 14 个 skill 出现在 openclaw agent 的 skills 列表中
```

实际路径验证：

```bash
$ ls -la ~/.agents/skills/
lrwxr-xr-x  superpowers -> /Users/mindora/.codex/superpowers

$ ls ~/.agents/skills/superpowers/skills/
brainstorming  dispatching-parallel-agents  executing-plans
finishing-a-development-branch  receiving-code-review  requesting-code-review
subagent-driven-development  systematic-debugging  test-driven-development
using-git-worktrees  using-superpowers  verification-before-completion
writing-plans  writing-skills
```

---

## 六、CLI `openclaw skills list` vs Agent 运行时的差异

**发现**：`openclaw skills list` CLI 命令输出的是 `openclaw-bundled` 内置 skills（52 个），**不包含** `agents-skills-personal` 等外部 source 的 skills。

但 openclaw agent 运行时（TUI/API）会从**全部 6 个 source** 加载 skills，因此 superpowers 的 14 个 skill 出现在 TUI 中，却不出现在 CLI 的 `skills list` 输出里。

同样，`openclaw skills info <name>` 也只能查询 bundled skills：

```bash
$ openclaw skills info brainstorming
Skill "brainstorming" not found.   ← 但 brainstorming 确实在 TUI 中可用
```

---

## 七、卸载 / 隔离 Superpowers

### 方案 A：完全卸载（Codex + Openclaw 同时移除）

```bash
rm ~/.agents/skills/superpowers
rm -rf ~/.codex/superpowers  # 可选，删除克隆本体
openclaw gateway restart
```

### 方案 B：迁移至 `~/.codex/skills/`，仅保留给 Codex ✅（推荐）

利用 Codex 的私有目录 `~/.codex/skills/` 与 openclaw 实现隔离：

```bash
# 1. 将 superpowers 移入 Codex 专属目录
mv ~/.codex/superpowers ~/.codex/skills/superpowers

# 2. 删除跨平台共享目录中的链接
rm ~/.agents/skills/superpowers

# 3. 重启 openclaw，使其不再加载 superpowers
openclaw gateway restart
```

效果：
- Codex 从 `~/.codex/skills/superpowers/` 递归发现所有 14 个 SKILL.md ✅
- openclaw 的 `agents-skills-personal` source（`~/.agents/skills/`）为空，不再加载 superpowers ✅

### 方案 C：完全卸载（Codex + Openclaw 同时移除）

```bash
rm ~/.agents/skills/superpowers
rm -rf ~/.codex/superpowers
openclaw gateway restart
```

### 方案 D：保持现状

两个平台共享同一份 superpowers，行为一致，无副作用。

---

## 八、Skills 发现对 Skills 开发的启示

1. **`~/clawd/skills/`（openclaw-workspace）是开发首选位置**
   优先级最高，且只影响 openclaw，不会泄漏给其他平台。

2. **`~/.agents/skills/` 是真正的"全局"位置**
   放在这里的 skills 会被 Codex、openclaw、Cursor 等多个平台同时发现，适合跨平台通用 skills。**注意：放在此处会污染所有平台，使用前需谨慎评估。**

3. **`~/.codex/skills/` 是 Codex 专属全局**
   只有 Codex 扫描此目录，openclaw 不读取。适合仅供 Codex 使用的 skills（如 superpowers）。

4. **`~/.openclaw/skills/`（openclaw-managed）是 openclaw 专属全局**
   目录当前不存在（需手动创建），适合只想在 openclaw 中全局可用、但不想暴露给其他平台的 skills。

4. **Skills 的 `description` 字段决定 LLM 触发精度**
   不同平台（Codex/openclaw/Cursor）都依赖 `SKILL.md` 中 YAML frontmatter 的 `description` 做语义匹配，description 越精确，触发命中率越高。
