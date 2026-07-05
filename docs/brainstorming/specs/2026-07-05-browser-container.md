# 浏览器自动化容器 — 设计文档

> 日期：2026-07-05 · 来源：mindora ADR 0056（交付物 3）· 需求单：`/tmp/omp-browser-container-requirements.md`
> 状态：已定方案，待实现

## 1. 定位与边界

把 omp 浏览器自动化能力封装成**常驻容器**（per-成员、跑在其工作站上），对外提供 **REST + MCP** 接口和 **noVNC** 直播/接管，供 **mindora daemon** 消费。数据/登录态留在成员信任域内。单用户，不做多租户/pool。

**责任边界**

| 归属 | 内容 |
|------|------|
| omp 实现 | 容器 + X 环境 + 浏览器 + indexed 自动化引擎 + REST/MCP + noVNC + 契约文档 |
| mindora 消费 | browser Capability、preview renderer、`ask(browser_takeover)` 接管、System Config 连接项 —— **不在本仓库** |

**关键澄清：本地 skill 不改道走容器。** `omp web-operator` 本地 CLI（宿主 Chrome + `cdp.mjs` + 站点 SOP）保持原样。容器是**并行新增的远端能力**，消费者是 mindora daemon（HTTP/MCP），不是本仓库的 Agent。两条路独立。

## 2. 决策记录

| 项 | 裁决 | 归属 |
|----|------|------|
| §1 indexed 底座 | 必建。编号 **per-snapshot**（非永恒），act 撞失效元素返 `stale`/`not-found` | mindora 硬需求 |
| index 映射机制 | `backendNodeId` + `DOM.resolveNode`，每次 `/dom` 刷新映射表 | omp 内部 |
| 引擎语言 | **Python 直连 CDP**（单语言）；移植 `cdp.mjs` 踩坑知识而非代码 | omp 内部 |
| REST vs MCP | REST 为唯一真实接口；**FastMCP** 薄封装自动转出 MCP，同一套语义 | mindora 已定 |
| VNC 只读↔交互 | **方案 A**：`x11vnc -viewonly` 端口 + 交互端口，双可达，mindora 按状态切 | mindora 表态 |
| auth-state 端点 | **首版不做**。登录墙检测归 mindora agent（读 DOM 自判） | mindora 已定 |
| 容器生命周期 CLI | 新顶层 `omp container`，统一管 `html-serve` + `browser`；从 `omp html-serve` **移除** `start/stop/restart` | mindora 已定 |

### indexed 编号语义（钉死，防过度设计）

- 一次 `GET /dom` 返回内，每个可交互元素编号稳定。
- `POST /act {index:7}` 解析的是「该 session **最近一次** `/dom`」的编号表。
- 下一次 `GET /dom` 允许重新编号（每次 observe 重抽）。
- agent 每步 act 前都会重读 `/dom`——编号只需**快照内稳定**，不需跨快照稳定。
- act 撞失效编号（元素已变/消失/导航后 backendNodeId 失效）→ 返回明确 `stale`/`not-found` → agent 重抽。
- **不追求永久稳定编号**（做不到，也没必要）。

## 3. 红线清单

触及子系统：web-operator CDP 层（复用）· 新建容器 · 新建 session 引擎 · 新建 REST+FastMCP · noVNC · omp CLI（新 `container` tool + 收窄 html-serve）· skill 打包。

| # | 红线 | 来源 |
|---|------|------|
| R1 | CLI 命名/设计前必须跑 `omp --help`+读 `cli/*/main.py`（已执行） | IRON RULE 3 |
| R2 | 不要兼容性：正确设计 > 兼容 | IRON RULE 4 |
| R3 | 交付后必须真实验证，未验证不能说"已完成" | IRON RULE 5 |
| R4 | SKILL.md 禁止相对路径脚本调用，一律 CLI 化 | 禁止事项1 |
| R5 | 禁止正则解析 HTML | 禁止事项2 |
| R6 | 禁止硬编码敏感信息（token/登录态走 env/secret） | 禁止事项3 |
| R7 | 禁止直接改 `~/.oh-my-superpowers/`，只改源码目录 | 禁止事项4 |
| R8 | tests 不得放 skill 目录，统一 `tests/skills/<name>/` | 禁止事项6 |
| R9 | 接口必须自包含，禁止把步骤塞回 GUI | web-operator README §131 |
| R10 | 无调查不设计 / network-first | web-operator README §7 |
| M1 | 接口层不嵌 LLM，认知工作归调用 Agent | feedback_llm_belongs_to_agent |
| M5 | 测试清理绝不 rm 生产路径，隔离 HOME/端口/目录 | feedback_no_destructive_test_on_prod_paths |
| C1 | indexed 编号 per-snapshot（非永恒），act 撞失效返 stale/not-found | 本轮 mindora 钉死 |
| C2 | dom 返回编号 与 act 用编号 同一套 | 需求单 §1 |
| C3 | 容器无脑，不主动发"撞登录墙"信号，登录墙检测归 agent | 需求单 §3/§5 |
| C4 | 登录态持久化到 volume；给高层 act/dom，非裸 CDP | 需求单 §0/§1 |
| C5 | VNC 直播 = 自动化的同一浏览器会话；接管后登录态即刻生效 | 需求单 §2 |
| C6 | VNC 方案 A：viewonly + 交互双端口 | 本轮敲定 |
| C7 | 错误契约可区分：超时/元素不存在/导航失败 | 需求单 §1 |
| C8 | 单用户，不做多租户/pool | 需求单 §0 |
| **C-SoT** | **同一容器不得有两个启动入口**：加 `omp container` 就必须从 `omp html-serve` 移除 `start/stop/restart` | 本轮收拢 SoT + IRON RULE 4 |

## 4. 架构

```
容器（常驻，per-成员，照搬 auto-wechat/docker 骨架）
├── supervisor 管：xvfb + openbox + Chrome(固定CDP端口)
│                  + x11vnc-viewonly + x11vnc-interactive + websockify/noVNC + restserver
├── engine/        indexed 底座：CDP 直连 + 可交互元素抽取 + index→backendNodeId 映射 + act 解析
├── rest/          FastAPI：§1/§4 端点，无 LLM
├── mcp/           FastMCP 包 rest → MCP
└── volume         浏览器 profile / cookie / session 持久化
```

## 5. 代码结构变化

```
oh-my-superpowers/
├── docker/
│   ├── html-serve/                         (不动)
│   └── browser-container/                   ★新增
│       ├── Dockerfile                       Ubuntu24+xvfb+openbox+Chrome+x11vnc+noVNC+websockify+supervisor
│       ├── supervisord.conf                 chrome / x11vnc-viewonly / x11vnc-interactive / websockify / restserver
│       ├── entrypoint.sh
│       ├── compose.yaml                     常驻；挂 profile volume；映射 REST+VNC 端口
│       ├── env.example                      baseURL / token / 端口 / volume 路径
│       ├── README.md                        ★§5 交付物：endpoint 清单 + 生命周期 + VNC A + volume + curl 序列
│       └── app/
│           ├── engine/
│           │   ├── cdp_client.py            直连 CDP WebSocket（移植 cdp.mjs 踩坑：mouseWheel 无响应、nav hard-reload）
│           │   ├── dom_index.py            可交互元素抽取→backendNodeId→per-snapshot 编号
│           │   ├── session.py              per-session 状态 + index→backendNodeId 映射表
│           │   └── act.py                  index→DOM.resolveNode→click/type/scroll，失效返 stale
│           ├── rest/
│           │   ├── main.py                  POST /session · /act · GET /dom · /shot · /health
│           │   └── errors.py                timeout / not-found / nav-failed 可区分
│           ├── mcp/
│           │   └── server.py                FastMCP 包 rest → MCP
│           └── pyproject.toml
│
├── cli/
│   ├── container/main.py                    ★新增：omp container ls/up/down/restart/logs/health <name>
│   │                                          name ∈ html-serve | browser；复用 run_compose
│   ├── html-serve/main.py                   ✎移除 start/stop/restart（迁至 omp container）
│   └── web-operator/main.py                 (不动)
│
├── skills/web-operator/
│   ├── SKILL.md                             ✎补一小段容器说明，指向 omp container up browser（无相对路径）
│   ├── scripts/cdp.mjs                      (不动)
│   └── references/                          (不动)
│
├── skills/html-serve 相关文档                ✎排查 grep `omp html-serve start`→改 `omp container up html-serve`
│
├── tests/skills/web-operator/browser-container/   ★新增
│   ├── test_dom_index.py                    T1：编号 per-snapshot、stale 契约
│   └── e2e_curl_sequence.sh                 T2：真实容器 建session→nav→dom→act→看VNC
│
└── docs/brainstorming/specs/2026-07-05-browser-container.md   ★本文档
```

## 6. CLI 结构

```
omp container                        ★新顶层 tool
├── ls                     列出受管容器 + 状态
├── up   <name>            name ∈ html-serve | browser
├── down <name>
├── restart <name>
├── logs <name>
└── health <name>

omp html-serve                       ✎收窄为纯内容操作
└── publish / url / list / reindex / status   （移除 start/stop/restart）
```

判断依据（CLI 公约）：容器生命周期是跨目标的通用概念 → 动词作顶层（`up <name>`），容器名作参数。

## 7. PR 拆分 + 逐 PR 红线核对

**PR1 — 容器骨架**（照搬 auto-wechat/docker）
Touches: `docker/browser-container/{Dockerfile,supervisord.conf,entrypoint.sh,compose.yaml,env.example}`
- C5 单一 Chrome，VNC 与自动化同一 CDP 目标 · C6 x11vnc 双端口 · C4 profile volume · C8 单容器无 pool
- R2 丢弃宿主 systemd `up` 逻辑 · R6/M5 token 走 secret、volume 隔离 · R7 只写源码目录

**PR2 — session 引擎（indexed 底座，load-bearing）** ⭐
Touches: `docker/browser-container/app/engine/**`
- C1 per-snapshot 编号 + stale · C2 dom/act 共用映射表 · R5 用 CDP DOM/AX API 不正则 · M1 零 LLM · R10 indexed 属 LLM 驱动兜底

**PR3 — REST 门面**
Touches: `docker/browser-container/app/rest/**`
端点：`POST /session` · `POST /session/{id}/act` · `GET /session/{id}/dom` · `GET /session/{id}/shot` · `GET /health`（**无** auth-state）
- C3 不推登录墙信号 · C7 error schema 三类可区分 · C4/R9 高层非裸 CDP、自包含 · M1 零 LLM

**PR4 — FastMCP 适配**
Touches: `docker/browser-container/app/mcp/server.py`
- 同一语义自动转出，无新契约 · M1 零 LLM

**PR5 — VNC 接线 + 集成交付**
Touches: supervisord noVNC 接线 + `docker/browser-container/README.md`
- C5/C6 双端口直播同一会话 · R3 交付可跑 curl 序列，真实容器跑通才算完成

**PR6 — CLI 收拢**
Touches: `cli/container/main.py`（新）· `cli/html-serve/main.py`（移除 start/stop/restart）· SKILL/文档同步
- **C-SoT** 收拢后同一容器单一启动入口 · R1 已过事实核对 · R4 SKILL.md 无相对路径

## 8. §5 交付物（给 mindora，落 `docker/browser-container/README.md`）

- 完整 endpoint 清单（method + path + 请求/响应 schema）
- session 生命周期语义（何时新建、复用、失效；注意 nav 是 hard reload 吞页面态）
- VNC 只读↔交互最终方案（A：双端口）
- 可跑 curl 序列：建 session → navigate → dom → act → 看 VNC
- 登录态持久化行为（volume 路径、清除方式）

## 9. 暂缓/超出范围

- `GET /auth-state`：首版不做，agent 读 DOM 自判登录墙。
- 站点 SOP（x/xueqiu/taoguba）不进容器，留在本地 `omp web-operator`。
- 多租户/连接池：不做。
- 本地 skill 改道走容器：不做。
