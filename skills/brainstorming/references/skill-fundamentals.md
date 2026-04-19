# Skill 基础知识

Skill 设计的核心原则和判断标准。在 Phase 0 能力检验时参照本文件。

---

## 1. Skill 自治原则（最重要）

**一个 Skill 只能依赖自身目录内的文件。**

```
my-skill/
├── SKILL.md
├── references/   ← 所有知识、规范、标准都在这里
├── assets/       ← 所有模板都在这里
└── scripts/      ← 所有脚本都在这里
```

**自治意味着**：复制这个目录到任何地方，Skill 的行为完全不变。

**违反自治的表现**：
- 引用项目中其他文件：`docs/specs/xxx.md`、`agents/xxx.md`
- 依赖其他 Skill 或 Agent
- 引用外部 URL 或网络资源（运行时请求除外）
- 引用绝对路径（除脚本 CLI 调用外）

**修复方式**：将需要的知识内化到 `references/` 中。如果某个项目规范文件是判断依据，就把它的核心内容提炼进 references/ 里。

---

## 2. 什么时候需要 Skill

Skill 的价值在于封装**模型自身无法直接完成**的能力：

| 需要 Skill | 不需要 Skill |
|-----------|------------|
| 特定 CLI 工具的操作方式 | "帮我写一篇文章" |
| 内部/私有编码规范 | 通用代码审查 |
| 可执行脚本的结果处理 | 通用分析推理 |
| 专有知识体系（打包进 references/） | 公开的通用知识 |
| 强制性工作流程（有检查点） | 简单的一步任务 |

**判断核心**：去掉这个 Skill，模型用通用知识能做到一样好吗？
- 能 → 不需要 Skill
- 不能（缺少工具/规范/脚本/私有知识）→ 需要 Skill

---

## 3. 自治检验清单

设计 Skill 前逐项确认：

- [ ] 这个 Skill 需要的**所有判断标准**，是否都可以写进 `references/`？
- [ ] 这个 Skill 需要的**所有模板**，是否都可以放进 `assets/`？
- [ ] 这个 Skill 需要的**所有脚本**，是否都可以放进 `scripts/`？
- [ ] 这个 Skill 是否**不依赖**其他 Skill、Agent、或项目外部文件？

有任何一项为否 → 需要重新设计，将依赖内化。

---

## 4. Skill 与 Agent 的边界

| | Skill | Agent |
|--|-------|-------|
| 身份 | 无（工具/工作流） | 有（职业/职能角色） |
| 依赖 | 自身目录 | Skills + 自身 system prompt |
| 调用方式 | 被 Agent/Claude 加载 | 独立运行 |
| 决策归属 | 跟随调用方 | 自主决策 |

如果一个需求有明确角色身份、自主决策权、对结果负责 → Agent，不是 Skill。
如果没有角色身份，只是"帮我做 X" → Skill 或直接用模型。

---

## 5. 脚本 CLI 化规则（强制）

**凡是 skill 有 `scripts/` 目录，必须将所有脚本封装为一个统一 CLI。**

### 规则

1. **一个 Skill，只能有一个 CLI**
   - 入口唯一，不允许多个并列脚本供调用方随意选择

2. **命名规范：`omp <skill-name>`**
   - 例：skill 名为 `skill-review` → CLI 调用为 `omp skill-review`
   - CLI 模块放在 `cli/<skill-name>/main.py`，由 `omp` 统一路由

3. **SKILL.md 中只引用 CLI 名称，不写相对路径**
   ```
   # 错误 — 相对路径调用
   python scripts/<your-script>.py --skill-dir <path>

   # 正确 — CLI 调用
   omp <skill-name> --skill-dir <path>
   ```

### 为什么这样设计

- 相对路径调用绑死了运行位置，Skill 复制到其他地方就失效
- 多个脚本入口让调用方需要理解内部结构，破坏封装
- CLI 化后 `omp install` 可以直接将 CLI 安装到全局 PATH，Skill 完全自治

### 自治检验补充项

- [ ] scripts/ 下的所有脚本是否已合并进一个 `omp-<skill-name>` CLI？
- [ ] SKILL.md 中是否没有任何 `bash scripts/` 或 `python scripts/` 调用？

---

## 6. 常见设计错误

以下示例使用占位符（`<project-docs-path>` 等），仅为教学，不是真实路径。

**错误 1：把项目文档路径写进 SKILL.md**
```
# 错误
读取 <project-docs-path>/README.md 中的规范...

# 正确
读取 references/<your-spec>.md 中的规范...
```

**错误 2：Skill 调用另一个 Skill**
```
# 错误
完成后调用 <another-skill> skill 进行验证...

# 正确
在 references/ 中打包审查标准，在本 Skill 内完成验证
```

**错误 3：依赖 Agent 的配置**
```
# 错误
读取 <agents-config>.json 获取模型配置...

# 正确
Skill 不关心 Agent 配置，只提供能力
```
