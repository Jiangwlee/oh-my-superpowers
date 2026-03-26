# Researcher / WPS Migration
#
# 用途：Fast 模式设计文档模板（轻量版）
# 与 Normal 模式的差异：
#   - 无多方案对比，直接给推荐方案
#   - 行动计划为粗粒度步骤列表，无代码示例和精确行号
#   - 行动原则只列 2-3 条最相关原则，不展开禁止项
# 目录：设计方案 / 行动原则 / 行动计划

> 将 `chrome-cdp-skill` 中的 `web-researcher` 和 `wps-assistant` 迁入当前项目，并将前者重构为通用研究员 `researcher`。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 目标

将现有浏览器型 agent 纳入 `oh-my-superpowers` 的统一 agent 管理入口，保持角色边界清晰，并避免把外部仓库路径和 wrapper 逻辑一起带入当前项目。

### 方案

新增两个 agent：`researcher` 和 `wps-assistant`。`researcher` 由 `web-researcher` 演化而来，职责收敛为通用研究员，保留多轮研究框架，并为未来的分领域 SOP 渐进式加载预留入口；`wps-assistant` 保持为 WPS 文档助理，专注模糊问题下的文档定位、阅读和结果交付。两个 agent 均注册到 `agents/agents.json`，运行入口统一为 `omp run`，不迁移源仓库的 `pi-*` wrapper。`chrome-cdp` 视为全局可发现依赖，不作为 agent-specific skill 写入注册表。

---

## 行动原则

> 最相关的 2-3 条原则（完整库见 `references/principles-library.md`）

- **Break Don't Bend**：保留 `media-editor` 的 AI 媒体编辑定位，不把通用研究职责硬塞进去。
- **Explicit Contract**：通过清晰的角色、输入模式、工作流和输出模板定义 `researcher` 与 `wps-assistant` 的边界。
- **Minimum Blast Radius**：仅新增 agent 文件和注册项，不改现有 agent 与 skill 结构。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `docs/brainstorming/specs/2026-03-26-researcher-wps-migration-design.md` | 记录本次迁移设计 |
| 新增 | `agents/researcher.md` | 通用研究员定义 |
| 新增 | `agents/wps-assistant.md` | WPS 文档助理定义 |
| 修改 | `agents/agents.json` | 注册两个新 agent |

### 任务步骤

- [ ] 编写迁移设计文档并固化角色边界
- [ ] 迁入并改写 `researcher` 与 `wps-assistant`
- [ ] 更新 `agents/agents.json` 注册表
- [ ] 运行最小静态校验与 `reviewer` 审查
