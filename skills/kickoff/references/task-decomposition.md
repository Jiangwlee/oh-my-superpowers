# Task Decomposition

在两个时机读取本文件：

1. Phase 3 做任务分解时
2. 每个 wave 开头写 JIT spec 时

## Job of This File

本文只定义两类约束：

| 主题 | 内容 |
|---|---|
| Breakdown skeleton | `tasks.yaml` 在 Phase 3 必须先写什么、不能先写什么 |
| Decomposition rules | `test_layer`、API wiring、vertical slice、wave packing 的硬规则 |

## JIT Spec Protocol

spec 必须**按 wave 编写**，不能在 story 一开始全部写完。

| 阶段 | 必须产出 |
|---|---|
| **Phase 3 - Breakdown** | 只写 `tasks.yaml` 骨架：`id / title / wave / depends_on / files_modified / est_loc / test_layer / spec: null` |
| **Phase 4 - JIT Spec** | 复制 `skills/kickoff/templates/task.md` 到 `<PROJECT_ROOT>/stories/<YYYY-MM-DD>-<slug>/tasks/task-NN.md`，填写 `Objective / Protocol / Acceptance Checklist`，并把 `spec: tasks/task-NN.md` 写回 `tasks.yaml` |

硬规则：

- `spec` 为空时，`omp kickoff task update --status executing` 会被 CLI 拒绝
- 所以先写 JIT spec，再切到 `executing`

写每个 wave 的 spec 前，按这个顺序做：

1. 读 `story-memory.md`
2. 回看前一 wave 的 reviewer 报告，确认没有延迟生效的决策
3. 再写本 wave 的 spec

## tasks.yaml Skeleton Fields

每个 task 都必须包含以下字段：

- `id`
- `title`
- `wave`
- `depends_on`
- `spec`（Phase 3 时必须为 `null`）
- `files_modified`
- `est_loc`
- `test_layer`

补充规则：

| 规则 | 要求 |
|---|---|
| `test_layer` | 选择**最早能证伪 acceptance** 的层级；默认 `e2e` |
| `est_loc` | 估算代码改动行数；供 wave 打包使用 |
| 直接编辑字段 | task 的增删改排是直接改 `tasks.yaml`；CLI 只维护高频状态字段 |
| sizing | 一个 task = 一个 vertical slice |
| wave packing | 依赖排序后，把相邻 task 打包到累计 `<= 500 LOC` 的 wave；一旦超出就开新 wave；单 task `> 500` 时独占一 wave |

## Rule 1: Test Layer Match

**第一个 red test 必须出现在 acceptance 能被证伪的最高层。**

| Acceptance 描述 | 首选 first-red-test layer |
|---|---|
| 纯函数输入 / 输出 | unit |
| React hook 状态转换 | hook test |
| 组件渲染 / 交互 | component test |
| 用户可观察到 URL / store / UI / async 的协同 | integration |
| 浏览器专属行为（focus / scroll / animation / lifecycle） | E2E |

默认值：**E2E first**。

只有当 acceptance 是 E2E 无法到达的纯数据变换时，才降到更低层。

## Rule 2: Cross-Layer API Wiring (No Orphans)

**新增共享 API，与接线到首个 consumer，必须放在同一个 task 里。**

共享 API 指任何跨模块边界的函数、状态或事件，例如：
- store action
- hook return value
- context provider
- event emitter

硬规则：

1. 禁止把“新增 API”与“接入第一个 consumer”拆成两个 task
2. 必须在同一个 task 中完成 API + consumer + 对应测试
3. 例外：当 API 有 2 个以上 consumer 时，可把“API + 第一个 consumer + 测试”放在首 task，其余 consumer 各自独立成 vertical slice

做 breakdown 前，主动扫一遍 task list：
- 如果出现“add X to module”但同 task 里没有“consume X” -> 合并

## Rule 3: Vertical Slice Sizing

一个 task 必须是一个 vertical slice，通常横跨：

- model / store / state
- API / hook / transport
- component / view
- 与 acceptance 对应的测试层

如果一个 task 触及文件数 **> 5**：
- 要拆
- 但必须**纵向拆**
- 不能按 layer 水平拆

水平拆分会直接违反 Rule 2。

## Self-Check Before Dispatch

- [ ] 每个 task 的 first red test 都匹配 acceptance layer
- [ ] 没有孤儿 API task
- [ ] 每个 task 都是 `<= 5` 文件的 vertical slice
- [ ] 每个 wave 的累计 `est_loc <= 500`，或单 task `> 500` 时独占一 wave
- [ ] 写本 wave spec 前已经读过 `story-memory.md`
