# Task <NN>: <Title>

<!--
Three sections only.
This file is the task contract: what to build, the outward protocol, and what counts as done.

Do NOT add sections like Read First / File Scope / Worker Refs.
Those belong in the dispatch prompt, not here.
-->

## Objective

<一段话说明本任务要完成什么；必要时补一句为什么。保持 action-oriented。>

## Protocol

<写对外契约。按任务类型选择最合适的形式：

- HTTP API：method, path, request schema, response schema, status codes
- Function：signature、inputs、outputs、side effects、errors
- Data：schema、fields、indexes、migration steps
- Event：event name、payload schema、producer、consumer

如果任务只是接线 / 重构 / 复用既有 API，写“沿用现有 X，无新增”即可。
这里必须具体到 reviewer 不必再翻别的文件就能判断接口是否合理。>

## Acceptance Checklist

<!--
每一项都必须可独立验证。
典型维度：功能实现、数据变更、跨模块接线、测试覆盖、E2E 或手动验证。
不要写“完成开发”这类不可验证的空话。
-->

- [ ] <具体可验证项 1>
- [ ] <具体可验证项 2>
- [ ] <具体可验证项 3>
