# Deep Research Skill
#
# 用途：Fast 模式设计文档模板（轻量版）
# 与 Normal 模式的差异：
#   - 无多方案对比，直接给推荐方案
#   - 行动计划为粗粒度步骤列表，无代码示例和精确行号
#   - 行动原则只列 2-3 条最相关原则，不展开禁止项
# 目录：设计方案 / 行动原则 / 行动计划

> 为 `researcher` 提供一个可审计、可落盘、可压缩上下文的 deep-research 执行框架 skill。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 目标

新增 `deep-research` skill，将多轮研究中的 workspace 管理、状态持久化、source note 归档、round 审计与双层报告生成从 `researcher` agent 中下沉，避免主上下文被网页正文和中间状态污染。

### 方案

`deep-research` 采用 `Pipeline + Inversion` 模式。开始研究前先收敛研究目标和子问题，再进入标准研究流程。每次研究创建一个独立 workspace，默认根目录为 `~/.local/share/oh-my-superpowers/deep-research/`，目录名格式为 `YYYY-MM-DDTHH-mm-<slug>/`。skill 通过统一 CLI `omp-deep-research` 管理工作区一致性：`init` 创建 workspace，`save-source` 保存原始网页与元信息，`update-state` 维护 JSON research state 与 round log，`build-report` 生成 `brief` 与可审计的 `full report`。LLM 负责 source note、轮次 reasoning 与报告内容，脚本负责结构、落盘和格式一致性。

---

## 行动原则

> 最相关的 2-3 条原则（完整库见 `references/principles-library.md`）

- **Explicit Contract**：用稳定的 workspace 结构、JSON state 和最小 CLI 约束研究流程，避免主 agent 随意拼装文件。
- **Break Don't Bend**：把研究执行框架从 `researcher` 中抽离出来，不再让 agent 同时承担策略与持久化职责。
- **Minimum Blast Radius**：先实现最小闭环，仅覆盖 workspace、state、source、report 四类核心能力。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `docs/brainstorming/specs/2026-03-26-deep-research-skill-design.md` | 记录 deep-research 设计 |
| 新增 | `skills/deep-research/` | 新 skill 目录 |
| 新增 | `skills/deep-research/SKILL.md` | 触发边界与 CLI 文档 |
| 新增 | `skills/deep-research/scripts/` | 最小 CLI 实现 |
| 新增 | `skills/deep-research/references/` | SOP、workspace 结构、状态格式 |
| 新增 | `skills/deep-research/tests/` | T1 静态检查 |
| 修改 | `agents/researcher.md` | 接入 deep-research workflow |
| 修改 | `agents/agents.json` | 为 researcher 注入 deep-research skill |

### 任务步骤

- [ ] 创建 deep-research 设计文档并固化边界
- [ ] 建立 skill 目录、references、tests 和最小 CLI 骨架
- [ ] 更新 researcher 以使用 deep-research skill
- [ ] 运行静态检查，确认 workspace/state/report 闭环成立
