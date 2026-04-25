# Writing the Unified Document

## Template map

| Use case | Template |
|---|---|
| Normal feature / refactor design | `assets/design-doc-template-normal.md` |
| Fast feature / refactor design | `assets/design-doc-template-fast.md` |
| Skill design | `assets/skill-design-template.md` |
| Agent design | `assets/agent-design-template.md` |

Save to: `docs/brainstorming/specs/<YYYY-MM-DD>-<slug>.md`

## Required structure

1. One-line summary
2. Table of contents
3. 设计方案 (Design)
4. 假设与风险登记 (Assumptions & Risks) — see `references/risk-and-spike.md`
5. Spike 计划 (Spike Plan) — only when 🔴 risks exist; Normal mode only
6. Spike 结果 (Spike Results) — filled after spikes run; Normal mode only
7. 行动原则 (Principles) — selected from `references/principles-library.md`
8. 行动计划 (Action Plan) — file structure + task steps

The document MUST contain a table of contents so agents can navigate directly to any section without scanning the full file.

**Hard rule on risks**: Section 4 must list every assumption the design bets on. Section 5/6 must be present (Normal) and resolved before the document moves to spec review. Fast mode skips 5/6 only when zero 🔴 risks exist.

## Action plan constraints

行动计划必须达到"agent 拿到文档可直接执行"的质量。遵守以下约束：

1. **Scope Check** — 如果方案涉及多个独立子系统，必须拆分为独立 plan。每个 plan 产出可独立测试的软件。不要在一个 plan 里混合无关子系统。
2. **File Structure First** — 先设计文件结构（每个文件的职责和边界），再定义任务。任务分解基于文件结构，而非反过来。
3. **粒度约束** — 每步 2-5 分钟。如果一步超过 5 分钟，拆分它。
4. **接口级描述** — 实现步骤给出函数签名 + 关键逻辑描述 + 边界情况，不要求完整代码。避免重复劳动（plan 写一遍、实现再写一遍）。

## Completion check task

Every action plan MUST include a **完成核查** task as the **last task** (before 文档更新 if that also applies). This task exists to prevent agents from falsely reporting completion while steps remain unfinished.

The task must:
1. Check every Task/Step in the plan is done (checkbox ticked or output verified)
2. Re-read the spec 设计方案 and confirm implementation matches — no silent deviations
3. Report to the user: tasks completed (X/X), any unfinished steps, any spec deviations, and a final ✅/⚠️ conclusion

The normal template includes a ready-made task for this. Always include it.

## Document update task

For significant changes (architecture changes, interface changes, directory restructuring, adding/removing core modules), the action plan MUST include a **文档更新** task as the final task. Skip this for small iterative changes or bug fixes. The template includes a ready-made task for this. Use it when applicable.

## Normal mode presentation rules

- Propose 2-3 different approaches with trade-offs
- Lead with your recommended option and explain why
- Be conversational, not exhaustive

## Presenting the design

- Present section by section, get confirmation after each
- Scale detail to complexity: a few sentences if straightforward, up to 200-300 words if nuanced
- Cover: architecture, components, data flow, key decisions

## Spec review loop (Normal mode only)

派遣规则与命令模板见 `dispatch.md`；reviewer prompt 全文位于 `../assets/spec-document-reviewer-prompt.md`。最多 3 轮，超出停止并报用户。

## Working in existing codebases

- Explore current structure before proposing changes. Follow existing patterns.
- Include targeted improvements if a file you're modifying has grown unwieldy.
- Don't propose unrelated refactoring.
