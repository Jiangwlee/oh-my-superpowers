# browser-container `/dom` 有界子集返回 — 设计

- 日期：2026-07-06
- 状态：待评审
- 范围：`docker/browser-container/`（容器侧）+ mindora-ui browser 工具契约（连带，跨仓）
- 锚点契约：`docker/browser-container/README.md`（对应 mindora ADR 0056 交付物3）

## 1. 问题

`/dom` 把整页所有可交互元素一次性返回。聚合类页面（tophub：3354 元素 / 271KB）导致：

1. 单条工具结果撑爆模型 context（198k token 爆窗 bug 的根）。
2. mindora 侧 `tool-output-cap` 对编号清单做字节盲截 → 砍中段、`[1500]` 类索引悬空、点击 not-found。兜底救了大小、坏了可用性。

真正该修的是**容器别一次吐整页**，而不是靠下游盲截。

## 2. 目标 / 非目标

**目标**：`/dom` 能返回有界子集，默认永不返回整页；编号一致性、响应兼容、给 agent 明确"拿更多"的路径。

**非目标**（红线 R4/R7）：
- 容器不做 LLM 摘要 / 登录墙判断。
- 不改 `click/type/navigate/scroll` 语义。
- 不新增 tab 端点。
- `tool-output-cap` 保留为纯最后兜底，正常路径下不再触发。

## 3. 核心设计决策

### 3.1 职责切分：JS 只做可见性收集，筛选/重编号在 Python 纯函数（R2 + 可测性）

**关键修订（实现期定）**：不把视口/查询过滤塞进浏览器内 JS，而是切成两层——

- **JS 收集器（浏览器内）**：保留可见性/零尺寸/`disabled` 过滤（R5，需 computed style），额外让每个 descriptor 带上 `rect{top,bottom,left,right}`，并返回页面 `viewport{w,h}`。它输出**全部可见候选**并按序存入 `window[global]`。
- **Python 选择器（`select_survivors`，纯函数）**：从 descriptors 上做视口/`q`/`role` 过滤 + 硬上限，产出一个**幸存者原始下标的有序列表**。该列表**同时**驱动重编号 descriptor（`i=0..k-1`）与 `index_map` 的 key —— 仍是单一源头。

为何不放 JS（放弃原 §3.1 方案）：
1. **可测性**——筛选+重编号是纯 Python，可对红线 R2（编号对齐）写真实单测；放 JS 则只能靠 FakeCDP 返回预设子集，测的是替身不是逻辑。
2. **效率**——`describeNode` 只对幸存者调用；现状对全页 3354 个元素逐个 `describeNode`，正是慢因。`getProperties` 列 objectId 是一次调用（廉价），昂贵的 per-node `describeNode` 被限到幸存者。
3. 编号仍单一源头（幸存有序列表），R2 不破。

### 3.2 默认视口过滤（R1）

`rect` 是视口相对坐标。`select_survivors` 默认保留与视口相交者：

```python
top < viewport_h and bottom > 0 and left < viewport_w and right > 0
```

agent 用**已有的** `scroll` 揭开更多（不新增端点，R7）。

### 3.3 查询过滤（R2 能力，非红线）

`/dom?q=<关键词>`：按 descriptor 的 `name` 子串（大小写不敏感）过滤。
`/dom?role=<role|tag>`：按 `role`/`tag`（其一相等）过滤。

**语义**：给了 `q`/`role` 就**搜全页**（不限视口，因目标控件可能在视口外）；否则默认视口。二者是"或选其一"的作用域。

### 3.4 硬上限兜底（R4）

作用域过滤后再截前 `N`（默认 200，`OMP_DOM_MAX` 可调）。这是容器自身最后兜底，与 mindora 的 `tool-output-cap` 无关。

### 3.5 不做的：分页（R3）

需求列了 `offset/limit` 分页。**v1 不做**（简单优先）：
- 视口场景，"拿更多"= `scroll`；
- `q`/`role` 场景，"拿更多"= 缩小关键词；
- 硬上限 + 末尾提示已覆盖 runaway。

分页作为后续扩展点保留，当且仅当出现"单视口内 >200 元素且无法用 q 收窄"的真实场景再加。

## 4. 契约变更（R1/R8）

### 4.1 响应体（向后兼容）

保持 `{ok, count, dom}`，**新增** `total`：

```json
{ "ok": true, "count": 42, "total": 3354, "dom": "[0] <a> \"首页\"\n…" }
```

- `count`：本次返回子集元素数（= `len(index_map)`，语义不变）。
- `total`：**全页可见可交互元素总数**（作用域无关），让 agent 知道页面整体规模。
- 忽略 `total` 的旧 daemon 仍能正常解析 `count`/`dom`。

### 4.2 给 agent 的"拿更多"提示（R6，红线③）

当 `count < total`（发生了视口限域或硬截断），在 `dom` 文本**末尾**追加一行引导，使旧 daemon（只读 `dom` 文本）也不至于走进死路：

```
— 视口内 42 项，全页共 3354 项。scroll 向下揭开更多，或 /dom?q=<关键词> 精确定位 —
```

`q`/`role` 场景的提示相应改为"共 N 项匹配，截断显示前 200，缩小关键词"。文案是纯字符串拼接，无语义判断，不违反 R4。

### 4.3 入参

`GET /session/{id}/dom` 新增可选 query：`q`、`role`。（`view` 参数不引入——默认视口、给 `q`/`role` 即全页，已覆盖需求。）

## 5. 实现改动

### 5.1 容器侧

| 文件 | 改动 |
|---|---|
| `app/engine/dom_index.py` | 收集器 JS 返回 `{viewport, elements[{…,rect}]}` 并存全部候选；新增纯函数 `select_survivors(elements, viewport, q, role, cap)→有序原始下标列表`；`extract()` 签名加 `*, q, role, max_elements`，只对幸存者 `describeNode`，返回 `(listing, index_map, total)`；`_format()` 末尾按 `count<total` 追加提示行 |
| `app/rest/main.py` | `get_dom()` 读 `q`/`role` query 参数透传；响应加 `total` |
| `docker/browser-container/README.md` | §2 端点表 `/dom` 响应改 `{ok, count, total, dom}`，新增 `q`/`role` 入参说明与"视口默认+scroll 揭更多"用法 |
| `docker/browser-container/tests/test_dom_index.py`（**新建**，R9） | 用例：视口过滤命中/排除、`q`/`role` 过滤、cap 截断、`total` 正确、编号 `0..k-1` 与 `index_map` key 一一对应、空结果提示 |

### 5.2 mindora 侧（跨仓，连带，R8）

> 本仓库改不到，作为交付说明列出，实现前另走 ADR 0056 契约同步。

- `src/server/browser/container-client.ts:readDom`：透传 `q`/`role`，解析 `total`。
- `src/server/browser/tool-service.ts:read_dom`：把 `total`/"更多"提示带给 agent。
- browser 工具 `promptSection`/`description`：教 agent "默认返回视口，用 `scroll` 揭开更多、用 `q` 定位具体控件"。

## 6. 红线对账

**PR-1（容器侧过滤 + 契约）** — Touches: `dom_index.py`, `main.py`, `README.md`, `tests/test_dom_index.py`

| 红线 | 遵守？ | 方式 |
|---|---|---|
| R1 响应形状 `{ok,count,dom}` | ✅ | 仅**新增** `total`，旧字段语义不变 |
| R2 编号 per-snapshot / 子集同源 | ✅ | 过滤在 JS 收集器内，`els`/descriptor `i`/`index_map` 同源子集，`0..k-1` |
| R3 不注入页面属性 | ✅ | 仍走 `backendNodeId`+`resolveNode`，过滤只读 `rect`/descriptor |
| R4 无脑 / LLM-free | ✅ | 过滤是纯几何/子串判断；提示是字符串拼接，无语义决策 |
| R5 保留现有过滤 | ✅ | 可见性/零尺寸/`disabled` 判断原样保留，视口判断叠加其后 |
| R6 错误契约 | ✅ | 子集外 index 仍 `not-found`→重读 `/dom`，不变 |
| R7 单焦点 tab / 不新增端点 | ✅ | 仅给 `/dom` 加 query，不加 tab 端点；"拿更多"复用现有 `scroll` |
| R8 两端同步 | ⚠️ | 容器先行且兼容；mindora 侧改动本设计已列，需另 PR + ADR 0056 同步 |
| R9 测试镜像 | ✅ | 新建 `tests/test_dom_index.py` 同 PR 提交 |

**风险**：`total` 语义（视口作用域 vs 全页）若 agent 误读会低估页面规模——由 4.2 提示行显式区分"视口内 N / 全页共 M"消解。

## 7. 决议

1. **交付节奏（已定）**：容器先行且向后兼容，mindora 侧随后另 PR + 回 ADR 0056 核契约。
2. **R3 分页（已定）**：v1 不做，仅保留为扩展点；出现"单视口 >200 且无法用 `q` 收窄"的真实场景再加。
3. 视口默认硬上限 `N` 取值（暂定 200，`OMP_DOM_MAX` 可调）—— 实现时定。
4. `q` 暂定仅匹配 `name` 子串，`role` 走独立参数。
