# Web Operator Migration
#
# 用途：Fast 模式设计文档模板（轻量版）
# 与 Normal 模式的差异：
#   - 无多方案对比，直接给推荐方案
#   - 行动计划为粗粒度步骤列表，无代码示例和精确行号
#   - 行动原则只列 2-3 条最相关原则，不展开禁止项
# 目录：设计方案 / 行动原则 / 行动计划

> 将外部 `chrome-cdp` 浏览器 skill 全量迁入当前项目，并以能力名 `web-operator` 作为统一入口。

## 目录

- [设计方案](#设计方案)
- [行动原则](#行动原则)
- [行动计划](#行动计划)

---

## 设计方案

### 目标

把浏览器自动化基础设施纳入 `oh-my-superpowers` 的 skill 体系，消除跨仓库 skill 依赖，并为 `researcher`、`wps-assistant`、`media-editor` 提供统一、显式的浏览器能力入口。

### 方案

将源仓库中的 `chrome-cdp` skill 全量迁入当前项目，落地为 `skills/web-operator/`，保留 `core + sites + references + tests` 结构，但统一改名为能力导向的 `web-operator`。不保留 `chrome-cdp` 兼容层，不保留旧目录名，不依赖外部仓库运行时路径。所有需要浏览器工作流的 agent 在 `agents/agents.json` 中显式声明依赖 `@skills/web-operator/SKILL.md`，并将 prompt 中的旧 skill 名称替换为新名称。

---

## 行动原则

> 最相关的 2-3 条原则（完整库见 `references/principles-library.md`）

- **Break Don't Bend**：直接切换到 `web-operator`，不保留旧名兼容层，保持边界清晰。
- **Explicit Contract**：通过 skill 名称、description 和 agent 显式依赖声明，强化触发和调用路径。
- **Minimum Blast Radius**：只迁移浏览器 skill 本体及相关 agent 引用，不额外重构站点脚本结构。

---

## 行动计划

### 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新增 | `docs/brainstorming/specs/2026-03-26-web-operator-migration-design.md` | 记录 `web-operator` 迁移设计 |
| 新增 | `skills/web-operator/` | 全量迁入浏览器基础设施 skill |
| 修改 | `agents/agents.json` | 显式声明依赖 `web-operator` 的 agent |
| 修改 | `agents/researcher.md` | 将 skill 引用改为 `web-operator` |
| 修改 | `agents/wps-assistant.md` | 将 skill 引用改为 `web-operator` |
| 修改 | `agents/media-editor.md` | 将浏览器 skill 路径改为 `web-operator` |

### 任务步骤

- [ ] 写入 `web-operator` 迁移设计文档
- [ ] 全量迁入并重命名浏览器 skill
- [ ] 更新依赖该 skill 的 agent 定义与注册表
- [ ] 运行最小静态校验，确认无旧名残留
