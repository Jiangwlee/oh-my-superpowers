# Task <NN>: <Title>

<!--
Three sections only. This file is the task contract: what to build, what
the interface looks like, what counts as done.

Do NOT add Read First / File Scope / Worker Refs sections. In multi_wave
mode that context goes in the dispatch prompt, not here. Keeping task.md
stable means it doubles as the acceptance record.
-->

## Objective

<一段话描述本任务要做什么。Action-oriented，可以包含简短的为什么。>

## Protocol

<对外契约。视任务类型选择：

- **HTTP API**：method, path, request schema, response schema, status codes
- **Function**：function signature(s), inputs, outputs, side effects, errors
- **Data**：table/collection schema, columns/fields, indexes, migration steps
- **Event**：event name, payload schema, producer, consumer

如果任务是纯接线/重构、复用既有 API：写 "沿用现有 X，无新增" 即可。
设计应足够具体，让 reviewer 不必再去读其他文件就能判断接口是否合理。>

## Acceptance Checklist

<!--
典型维度：函数/模块开发、数据模型或迁移、模块间接线（API → consumer 都到位，无 orphan）、
测试覆盖（按 tasks.yaml 的 test_layer）、E2E 或手动验证。
每项必须可独立勾选验证，不要写"完成开发"这种空泛项。
-->

- [ ] <具体可验证项 1>
- [ ] <具体可验证项 2>
- [ ] <...>
