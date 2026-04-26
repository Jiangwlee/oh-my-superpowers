# web-operator 开发指南

> 这份 README 写给**开发者**（要新增/修改 SOP 的人），不是 LLM。LLM 看的是 [SKILL.md](SKILL.md)。

## 三条铁律

1. **无调查不设计**：动手设计前必须把页面结构、业务逻辑、网络流量摸清。研究文档/技术笔记里"跑通了 UI"只是"功能可达"的证据，**不是**实现该这么走的契约。
2. **无设计不编码**：CLI 命令名 / 输出 schema / 实现路径必须先定下来，再写代码。命名按 PROJECT.md「omp CLI 架构」公约（动词跨站点 vs 站点子组）。
3. **无测试不提交**：T1（bash -n / py_compile / --help）+ 至少一次 T2 真实 tab E2E。导出/写盘/网络类一定要在真实环境跑，不要只静态检查。

## 默认路径：纯 HTTP，不是 UI 自动化

**模仿浏览器点击是最后兜底，不是第一选择。**

绝大多数后台 SaaS（飞书 admin / kdocs / 雪球 / 知乎 / GitHub web 等）的前端是 SPA + 内部 REST API。把 API 抓出来直接调，比模拟 UI 快、稳、可读 100 倍：

| 维度 | UI 自动化 | 纯 HTTP（站点内部 API）|
|------|----------|----------------------|
| datepicker / 复杂控件 | 极脆弱（React state vs DOM value） | 一个时间戳参数搞定 |
| 文件下载 | CDP 拦截不一定支持，依赖文件系统轮询 | `fetch().arrayBuffer()` 直接拿二进制 |
| 异步任务（导出/计算）| snap 轮询页面文本/进度条 | 调 status/list 接口看 `progress`/`status` 字段 |
| 跨 navigation | hook 丢失，逻辑割裂 | 状态全在 server，无关页面 |
| 失败诊断 | "为什么按钮没响应" 玄学 | HTTP 状态码 + JSON code/msg 直接读 |

UI 自动化只在以下情况退回使用：
- 站点没有 HTTP 接口（纯前端计算 / WebSocket / 复杂签名）
- 接口需要交互式 challenge（图形验证码 / 二步验证）
- 客户端做了关键安全签名（JS 加密 body / time-based nonce）

## 调查清单（**必做，按顺序**）

### Phase 1: 看 Network（先于一切）

装 fetch + XHR hook 到目标页面：

```js
omp web-operator page eval <TARGET> "
(() => {
  if (window.__capInstalled) return 'already';
  window.__capInstalled = true;
  window.__cap = [];
  const orig = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const headers = {};
    if (init && init.headers) {
      if (init.headers instanceof Headers) init.headers.forEach((v,k)=>headers[k]=v);
      else Object.assign(headers, init.headers);
    }
    const r = await orig.apply(this, arguments);
    let resp=null; try { resp=(await r.clone().text()).slice(0,1500); } catch{}
    window.__cap.push({url, method:init?.method||'GET', headers, body:init?.body?String(init.body).slice(0,800):null, status:r.status, response:resp});
    return r;
  };
  const xo = XMLHttpRequest.prototype.open, xs = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m,u){ this.__c={method:m,url:u}; return xo.apply(this,arguments); };
  XMLHttpRequest.prototype.send = function(b){
    if (this.__c) {
      this.__c.body = b ? String(b).slice(0,800) : null;
      this.addEventListener('loadend', () => { this.__c.status=this.status; window.__cap.push(this.__c); });
    }
    return xs.apply(this,arguments);
  };
  return 'installed';
})()
"
```

触发目标业务操作（点 Search / Submit / Export），等几秒，读 `window.__cap`，过滤掉 monitor/tracking 域名（`slardar`、`collect`、`/monitor_browser/`），只看业务 API。

**跨 navigation 兜底**：hook 因 nav 丢失时，用 `omp web-operator page net <TARGET>`（背后是 `performance.getEntriesByType('resource')`）拿所有请求的 URL（无 body 但够定位接口名），再回头主动 fetch 探 body。

### Phase 2: 重放 + 鉴权诊断

直接 fetch 重放找到的接口：

```js
omp web-operator page eval <TARGET> "
(async () => {
  const r = await fetch('https://example.com/api/xxx', {
    method:'POST', credentials:'same-origin',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({...})
  });
  return JSON.stringify({status: r.status, body: (await r.text()).slice(0, 500)});
})()
"
```

**401 诊断流程**：
- 看 captured 那一次成功的 fetch 的 `headers` 字段，找你漏掉的 header
- 常见缺失：`X-Csrftoken`（取自某个 `*_csrf_token` cookie）、网关 session header（飞书 `X-Larkgw-Use-Lark-Session: 1`、其他站点同理）
- 用 `document.cookie` 反查 token 来源（用 token 值字符串 grep cookie value）

### Phase 3: 业务语义确认

找到 API 后**不要急着下结论说 X 可以替代 Y**。同名接口可能字段差很多：
- 列表接口（list / queryList）通常只给元信息
- 详情接口（detail / get）才给完整字段
- 导出接口（export / batchExport）的字段集可能比详情还广（含表单数据）

**真实跑一次**，对比响应字段集，再决定哪个接口符合业务需求。

### Phase 4: DOM 调查（仅在 Phase 1-3 都不通时）

退到 UI 路径才需要：
- `omp web-operator page snap <TARGET>` 读 accessibility tree
- 短 `page eval` probe 试 selector / 文本 / 时间格式
- 详细方法见 [references/core/sop-development.md](references/core/sop-development.md)

## 设计阶段

**命名公约**（PROJECT.md「omp CLI 架构」章节）：
- 跨站点动词 → 顶层（`search <site>` / `read-url`）
- 站点专属动词 → 站点子组（`feishu approval export` / `kdocs ask-ai`）

**输出 schema**：JSON to stdout，键固定，每个字段语义明确。schema 写进 `references/sites/<site>/workflows.md`。

**实现位置**：
- typer 注册 → `cli/web-operator/main.py`
- 主流程 → `scripts/sites/<site>/<verb>.sh`
- 共享 helper → `scripts/sites/<site>/common.sh`（site-specific）+ `scripts/core/common.sh`（跨站）
- LLM 文档 → `references/sites/<site>/workflows.md`
- 同步 SKILL.md：`When To Load References` + `Preferred Command Map` + `Core Rules`

## 已知陷阱

- **`SCRIPT_DIR` 被链式 source 覆盖**：sites/`<site>`/common.sh 重置 `SCRIPT_DIR`，再 source core/common.sh 又重置一次。主脚本要找自己目录下的文件（如辅助 .py），用独立变量名（如 `MYSITE_DIR`），不要依赖 `SCRIPT_DIR`。
- **fileName 含路径分隔符**：服务端返回的下载文件名可能含 `/`（如飞书 `Clock-in/out Correction`），bash 写盘前要 `${name//\//_}` 替换。
- **`page nav` 重置 React state**：`Page.navigate` 即使 URL 相同也是 hard reload，吞掉所有页面态（input.value、JS 变量、hook）。**不要假设页面状态跨 nav 保留**。
- **CLI 必须自包含**：禁止"先让用户在浏览器做 X 再跑 CLI"——这违背 CLI 的根本价值。`page nav` 不可控时优先纯 HTTP；datepicker 自动化失败时优先抓 API。
- **monitor / tracking 噪音**：抓 network 时永远要 filter 掉 `slardar` / `collect` / `monitor_browser` / `tea` / `applog` 等监控域名，业务 API 通常在主域下。

## 反模式

- ❌ "研究文档跑通了 UI 流程，我直接抄成脚本就行" — 没 Phase 1-3 调查的"抄"会掉进 React 控件死胡同
- ❌ "datepicker 自动化太脆弱，让用户预先在浏览器设好" — CLI 自包含原则，禁止把工作塞回 GUI
- ❌ "queryList 也返回了数据，那就不需要 export 了" — 接口字段集可能差很大，**业务语义先确认再下结论**
- ❌ 不抓 headers 就开始猜 401 原因 — captured fetch 的 headers 摆在那里，对照差异即可

## 参考资料

- [SKILL.md](SKILL.md) — 给 LLM 用户的命令文档
- [references/core/sop-development.md](references/core/sop-development.md) — 既有的 UI 路径详细开发流程（DOM/selector/readiness）
- [references/core/cli-reference.md](references/core/cli-reference.md) — `omp web-operator page` 各子命令详细语义
- [references/core/common-library.md](references/core/common-library.md) — `scripts/core/common.sh` API 参考
- [references/core/troubleshooting.md](references/core/troubleshooting.md) — CDP 连接 / 认证 / DevToolsActivePort 排障
- 项目根 `PROJECT.md` 的「omp CLI 架构」章节 — 命名公约 + Checklist
- 项目根 `CLAUDE.md` — 通用 LLM 编码原则
