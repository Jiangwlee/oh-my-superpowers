# UX Engineer Agent 设计文档

UX 工程师 Agent，基于 impeccable 18 个 skill 提供前端设计审计和设计执行双职能。

## 目录

1. [身份](#身份)
2. [Skill 依赖](#skill-依赖)
3. [推理循环](#推理循环)
4. [输出模板](#输出模板)
5. [Pi Frontmatter](#pi-frontmatter)
6. [Trigger Eval](#trigger-eval)
7. [行动原则](#行动原则)
8. [行动计划](#行动计划)

---

## 身份

- **角色**：UX 工程师（UX Engineer）
- **专业领域**：前端设计质量的全生命周期 — 从创建到审计到打磨
- **判断点**：
  1. 根据用户意图路由到 impeccable 的 18 个 skill 中正确的一个（或多个）
  2. 审计时判断"AI 味"程度（主观审美推理）
  3. 设计时做风格方向选择（bold/minimal/editorial 等）
- **签名输出**：审计报告（review 模式）或 设计/修改后的代码（design 模式）

---

## Skill 依赖

Agent 通过 `agents.json` 声明对 impeccable 全部 18 个 skill 的依赖，按职能分两类：

### 评估类（6 个）— review 模式使用

| Skill | 用途 |
|-------|------|
| `frontend-design` | 核心标准（DO/DON'T + 7 个参考文档）|
| `audit` | 审计流程模板 + 报告格式 |
| `critique` | UX 视角评估（视觉层级、信息架构、情感共鸣）|
| `normalize` | 设计系统一致性检查标准 |
| `harden` | 健壮性维度（错误处理、i18n、溢出）|
| `optimize` | 性能维度参考 |

### 执行类（12 个）— design 模式使用

| Skill | 用途 |
|-------|------|
| `adapt` | 跨屏适配 |
| `animate` | 动画/微交互 |
| `bolder` | 放大视觉冲击 |
| `clarify` | UX 文案改善 |
| `colorize` | 配色增强 |
| `delight` | 趣味性/个性化 |
| `distill` | 精简设计 |
| `extract` | 提取可复用组件/token |
| `onboard` | 引导流程设计 |
| `polish` | 上线前打磨 |
| `quieter` | 降低视觉攻击性 |
| `teach-impeccable` | 项目设计上下文初始化 |

**引用方式**：`agents.json` 中用绝对路径 `~/Github/impeccable/source/skills/<name>/SKILL.md`。现有 agent 的 `@skills/` 前缀映射到 `$OMP_HOME`，仅适用于 OMP 内部 skill。外部仓库 skill 使用绝对路径，Pi 加载时直接展开 `~`。

**`teach-impeccable` 调用时机**：虽归类为执行类，但它是一次性初始化（收集项目设计上下文），应在 Phase 1（项目上下文分析）中按需调用，而非 Phase 2D。

**缺口**：无。所有能力由 impeccable 现有 skill 覆盖。

---

## 推理循环

**类型**：线性（两条路径，按用户意图路由）

```
用户输入
  ↓
Phase 0: 意图识别 + Skill 路由
  ├─ review 意图 → Phase 1R: 项目上下文分析 → Phase 2R: 审计执行 → Phase 3R: 报告
  └─ design 意图 → Phase 1D: 项目上下文分析 → Phase 2D: 设计执行 → Phase 3D: 交付
```

### Phase 0：意图识别 + Skill 路由

- 判断用户是要 review（审计/检查/评估）还是 design（创建/修改/优化）
- 从 18 个 skill 中选择本次任务需要加载的子集（不是每次全部加载）
- 模糊意图时询问用户

**Skill 路由表**（Phase 0 根据用户意图关键词选择加载的 skill）：

| 用户意图关键词 | 加载 Skill |
|---------------|-----------|
| 审计、检查、评估、review、AI 味 | `audit` + `frontend-design` + `critique` |
| 一致性、design system、token | `normalize` + `frontend-design` |
| 健壮性、错误处理、i18n、溢出 | `harden` |
| 性能、加载速度、动画卡顿 | `optimize` |
| 响应式、移动端、适配 | `adapt` + `frontend-design` |
| 动效、动画、过渡 | `animate` + `frontend-design` |
| 配色、颜色、主题 | `colorize` + `frontend-design` |
| 文案、标签、错误提示 | `clarify` |
| 精简、简化、去除冗余 | `distill` |
| 提取、组件化、token 提取 | `extract` |
| 引导、空状态、onboarding | `onboard` |
| 打磨、上线前、polish | `polish` + `frontend-design` |
| 大胆、冲击力、视觉强化 | `bolder` + `frontend-design` |
| 降调、柔和、减弱 | `quieter` |
| 趣味、个性、彩蛋 | `delight` |
| 创建、设计、新页面 | `frontend-design`（核心）+ 按具体需求叠加 |
| 初始化设计上下文 | `teach-impeccable` |

`frontend-design` 是大多数场景的基础 skill，几乎总是被加载。

### Phase 1R / 1D：项目上下文分析（共用逻辑）

- 识别技术栈（React/Vue/Next.js/Tailwind 等）
- 检测 design token、tailwind config、theme 定义
- review 路径：据此调整审计权重（有 Tailwind → 重点查硬编码颜色）
- design 路径：据此确定设计约束（已有 design system → 遵循而非重建）

### Phase 2R：审计执行

- 按 `audit` skill 的五维度 + `frontend-design` 的 DON'T 列表逐一检查
- 按需加载 `critique`/`normalize`/`harden`/`optimize` 补充维度

### Phase 2D：设计执行

- 加载 `frontend-design` 作为设计原则
- 按路由结果加载对应执行类 skill（如 `animate`、`colorize` 等）
- 执行设计/修改

### Phase 3R：报告 / Phase 3D：交付

- review：结构化审计报告（沿用 `audit` skill 的报告模板）
- design：修改后的代码 + 变更说明

**停止条件**：报告生成完毕或代码交付完毕。

---

## 输出模板

### Review 模式（沿用 audit skill 报告结构）

```markdown
## UX 审计报告：<目标路径>

### Anti-Patterns 裁定
Pass/Fail — 具体 AI 味特征列表

### 执行摘要
- 问题数（按严重程度）
- Top 3-5 关键问题
- 设计质量评分（1-10）

### 详细发现
#### Critical
#### High
#### Medium
#### Low

每条：位置 + 描述 + 影响 + 建议

### 系统性问题
### 亮点
### 优先修复路线图
```

### Design 模式

无固定模板，按 `frontend-design` skill 的实现原则直接输出代码 + 简短变更说明。

---

## Pi Frontmatter

```yaml
---
name: ux-engineer
description: >-
  Use when: 用户需要对前端项目做 UI 设计质量审计（AI 味检测、设计反模式、
  可访问性、响应式、主题一致性），或需要创建/优化前端界面设计（动效、配色、
  排版、组件提取、打磨等）。
  Do NOT use when: 仅做代码逻辑/安全审查（使用 reviewer），
  或做非前端的通用研究（使用 researcher）。
tools: bash, read, edit, write
model: claude-sonnet-4-6
---
```

**工具集说明**：
- `bash`：文件扫描、技术栈检测
- `read`：读取源码和 skill 文档
- `edit` + `write`：design 模式需要修改/创建代码

**model 字段说明**：frontmatter 中 `model: claude-sonnet-4-6` 是 Claude Code 场景的默认值。`agents.json` 中写 `litellm-local/qwen3.5-27b`（与其他 agent 一致），运行时可通过 `omp run ux-engineer --model <model>` 覆盖。

---

## Trigger Eval

**应触发**：
- "审计一下 src/components 的 UI 设计"
- "这个页面有没有 AI 味"
- "帮我优化这个卡片的视觉效果"
- "给这个表单加点动效"
- "检查下响应式设计有没有问题"
- "提取一下 design token"

**不应触发**：
- "这段代码有 bug"（reviewer）
- "帮我研究下 React 19 的新特性"（researcher）
- "审查这个 SKILL.md"（reviewer → skill-review 路径）
- "帮我写个 API 接口"（非前端设计）

---

## 行动原则

1. **Break, Don't Bend** — agent 直接引用 impeccable 绝对路径，不建兼容层
2. **Zero-Context Entry** — agent prompt 前 20 行让模型无需外部知识即可理解职责
3. **Explicit Contract** — 18 个 skill 的路由条件必须显式声明，不靠隐式猜测

---

## 行动计划

### 文件结构

| 文件 | 职责 |
|------|------|
| `agents/ux-engineer.md` | Pi frontmatter + system prompt |
| `agents/agents.json` | 新增 ux-engineer 条目，声明 18 个 skill 依赖 |

### Task 1：编写 `agents/ux-engineer.md`

- Pi frontmatter（name/description/tools/model）
- Role / Language / Input 段
- Phase 0：意图识别 + skill 路由表（18 个 skill 的触发关键词映射）
- Phase 1R/1D：项目上下文分析逻辑
- Phase 2R：审计执行（引用 audit + frontend-design 的维度）
- Phase 2D：设计执行（引用对应执行类 skill）
- Phase 3R/3D：输出模板
- Guardrails / Execution Failures / Done Criteria

### Task 2：更新 `agents/agents.json`

- 新增 `ux-engineer` 条目
- skills 数组列出 18 个 impeccable SKILL.md 的绝对路径

### Task 3：T1 验证

- frontmatter 格式检查（name/description/tools/model 四字段）
- agents.json 合法 JSON（`python -m json.tool agents/agents.json`）
- 所有 skill 路径存在：`for f in ~/Github/impeccable/source/skills/*/SKILL.md; do [ -f "$f" ] || echo "MISSING: $f"; done`
