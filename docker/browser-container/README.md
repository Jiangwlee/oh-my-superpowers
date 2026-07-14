# omp browser-container — 对接契约（交付给 mindora）

常驻、单用户浏览器自动化容器。自带 Chromium + Xvfb + noVNC，对外提供 **indexed** 的 REST/MCP 接口和 VNC 直播/接管。容器**无脑**：只做「读结构化 DOM → 按编号执行动作」，登录墙检测、接管决策归调用方 agent。

对应 mindora ADR 0056 交付物 3。mindora 收到后按本文档逐条核对，再落 browser Capability + preview renderer + ask 接管。

---

## 1. 启动 / 生命周期

```bash
omp container up browser        # 构建镜像并启动（首次构建约需数分钟）
omp container health browser    # compose ps + /health 探活
omp container logs browser --tail 200
omp container down browser
```

端口（默认，可在 `.env` 改）：

| 端口 | 用途 |
|------|------|
| 8080 | REST 门面 |
| 9223 | MCP（FastMCP over HTTP，与 REST 同一套语义自动转出） |
| 6080 | noVNC **只读**（viewonly） |
| 6081 | noVNC **交互**（takeover） |

鉴权：若 `.env` 设置了非空 `OMP_BROWSER_TOKEN`，则除 `/health` 外每个请求须带 `Authorization: Bearer <token>`。

## 2. Endpoint 清单

Base URL：`http://<container-host>:8080`

| Method | Path | 请求体 | 响应 |
|--------|------|--------|------|
| GET  | `/health` | — | `{ok, browser}` — `browser` 为浏览器 CDP 可达性 |
| POST | `/session` | — | `{sessionId}` — 建或复用（单用户复用同一浏览器上下文） |
| GET  | `/session/{id}/dom` | `?q=&role=`（可选） | `{ok, count, total, dom}` — `dom` 为带编号的可交互元素文本 |
| POST | `/session/{id}/act` | `{action, args}` | 动作结果，见下 |
| GET  | `/session/{id}/shot` | — | `{ok, format:"png", base64}` — 可选，多模态用 |
| GET  | `/session/{id}/downloads` | — | `{ok, count, downloads}` — 浏览器触发过的下载清单 |
| GET  | `/session/{id}/download/{downloadId}` | — | 裸字节（`application/octet-stream`），支持 Range |
| DELETE | `/session/{id}/download/{downloadId}` | — | `{ok, deleted}` — 取回后清理 |

### 下载取回（容器只下载，抽取归 mindora）

浏览器点下载后，Chromium 以 `allowAndName` 落盘到容器 tmpfs `/data/downloads/{guid}`，容器经
`Browser.downloadWillBegin/downloadProgress`（**Browser 域**，不绑 tab，避免单焦点 tab 回收丢记录）记账。

- `GET /downloads` 返回 `[{ downloadId, filename, totalBytes, receivedBytes, state, sha256? }]`；
  `state ∈ inProgress|completed|canceled`，`sha256` 仅 completed 时给出。
- `GET /download/{id}`：`application/octet-stream` + `Accept-Ranges: bytes`。
  带 `Range: bytes=start-end` → `206` + `Content-Range`；不带 → `200` 全量流。响应头 `X-Content-SHA256`
  供完整性校验。**未完成**下载取回返回 `not-ready`(409)，**未知** id 返回 `no-download`(404)。
- `DELETE /download/{id}`：mindora 取回后删除文件与记录（tmpfs 本就瞬态，保留期归容器侧）。
- **传输为裸字节 + Range，非 base64-JSON**：下载物可达数百 MB，`/shot` 的 base64 只适合小截图；
  两端内存均有界。抽取（unzip/pdf/office→text）一律在 mindora 侧，容器保持"无脑"。

```bash
# 列出下载 → 取第一个的 id
curl -s $BASE/session/$SID/downloads
# 分块拉取前 8MB
curl -s -H "Range: bytes=0-8388607" $BASE/session/$SID/download/<downloadId> -o part0.bin
# 取回后清理
curl -s -X DELETE $BASE/session/$SID/download/<downloadId>

### act 动作

| action | args | 说明 |
|--------|------|------|
| `navigate` | `{url}` | 导航（hard reload，清空编号表） |
| `click` | `{index}` | 点击最近一次 `/dom` 的第 `index` 号元素 |
| `type` | `{index, text}` | 聚焦并替换输入第 `index` 号元素的内容 |
| `scroll` | `{dy}` | 垂直滚动 `dy` 像素（默认 600） |

成功响应形如 `{"ok": true, "action": "click", "index": 7}`。

### `/dom` 有界返回（永不一次吐整页）

`/dom` 只返回**有界子集**，避免聚合页（如 tophub 3000+ 元素）撑爆调用方 context：

- **默认作用域 = 当前视口**：只返回与视口相交的元素；agent 用 `act scroll` 揭开更多。
- **`?q=<关键词>`**：改为**全页**搜索，按元素名做大小写不敏感子串过滤（目标控件可能在视口外）。
- **`?role=<role|tag>`**：改为全页搜索，按 `role` 或标签名过滤。`q`、`role` 同时给出则须都命中。
- **硬上限**：作用域过滤后截前 `OMP_DOM_MAX`（默认 200）个，容器自身最后兜底。

响应新增 `total` = **全页可见可交互元素总数**（作用域无关），`count` = 本次返回数。当有元素未展示时，`dom` 文本**末尾附一行提示**告诉 agent 如何拿更多（scroll / 缩小关键词），不留死路。忽略 `total` 的旧消费端仍可正常解析 `count`/`dom`。

### `/dom` 输出样例

```
[0] <a> "首页"
[1] <input:text> "搜索"
[2] <button> "登录"
[3] <button> role=tab "消息"
— 视口内 4 项，全页共 42 项。scroll 向下揭开更多，或 /dom?q=<关键词> 定位具体控件 —
```

> 编号在返回子集内**连续重排为 `0..k-1`**，`act {index}` 即按此编号解析；`total`/提示行只是元数据，不参与编号。

## 3. 编号契约（关键，务必按此实现消费端）

- 编号是 **per-snapshot**，不是永恒：一次 `/dom` 返回内每个编号稳定。
- `act {index:N}` 解析的是「该 session **最近一次** `/dom`」的编号表。
- 下一次 `/dom` 允许重新编号——**agent 每步 act 前应重读 `/dom`**。
- 底层用 `backendNodeId` + `DOM.resolveNode` 映射，不往页面注入属性。
- 导航 / 元素消失后编号失效 → 返回明确错误（见 §4），agent 重抽即可。

## 4. 错误契约

失败响应统一 `{"ok": false, "error_type": "...", "message": "..."}`，HTTP 状态随类型：

| error_type | HTTP | 含义 / 下一步 |
|------------|------|---------------|
| `not-found` | 409 | 编号不在最近 `/dom` 表中 → 重读 `/dom` |
| `stale` | 409 | 元素/页面已变，编号不再解析 → 重读 `/dom` |
| `nav-failed` | 502 | 导航未完成 |
| `timeout` | 504 | 浏览器未在时限内响应 |
| `no-session` | 404 | 未知 sessionId |
| `cdp-error` | 502 | 其它 CDP 层错误 |

## 5. Session 生命周期语义

- **新建**：`POST /session` 时若无活动 session，绑定到浏览器的 page target。
- **复用**：单用户模型下所有调用复用同一 page target，不每次开新 tab。
- **失效**：`navigate` 是 hard reload，吞掉页面态（input 值、JS 变量、注入全局），并清空编号表——导航前的编号一律作废。
- 编号表随每次 `/dom` 刷新；不追求跨快照永久稳定（做不到，也无必要）。

### 单焦点 tab 不变量（容器内部，无需 agent 感知）

容器任何时刻只维护**一个焦点 tab**，`/dom` 读的、`/act` 作用的、VNC 前台显示的始终是同一个：

- 每次 `navigate` / `act` 执行后，对焦点 tab 调 `Page.bringToFront`——VNC 立即显示 agent 刚操作的页面。
- 某次 `click` 触发浏览器新开 tab（`target=_blank` / `window.open`，淘宝/京东常见）时，容器**自动收养**新 tab 为焦点：下一次 `/dom` 自然读到新页面，agent 无需感知。
- 焦点切走后，非焦点 tab 由容器**关闭回收**，存活 tab 数保持 ≈1，不随点击线性增长。

这些全是容器内部行为，REST 契约**不新增** list/switch/close tab 端点。可调 `OMP_NEW_TAB_WAIT`（秒，默认 0.8）调整点击后等待新 tab 出现的时长。

## 6. VNC 只读↔交互（方案 A：服务端强制）

两个端口各自对应一路 x11vnc，连**同一个** Chromium 会话（用户接管后登录态即刻对自动化生效）：

```
默认（自动化运行中）：preview 连 6080（-viewonly）→ 用户只能看，误碰不影响自动化
       ↓ agent 判定需登录 → 调 ask(browser_takeover)
接管态：             mindora 前端切到 6081（交互）→ 用户扫码/登录
       ↓ 用户点完成 → ask resolve
恢复：               切回 6080，自动化继续
```

只读由服务端 `x11vnc -viewonly` 物理保证，不依赖前端 overlay。

## 7. 登录态持久化

- Chromium profile（cookie / session / storage）在容器内 `/data/profile`，挂载到命名卷 `omp-browser-profile`。
- 清除登录态：`docker volume rm <project>_omp-browser-profile`（容器需先 `omp container down browser`）。

## 8. 可跑 curl 序列

```bash
BASE=http://localhost:8080
# 0) 探活
curl -s $BASE/health

# 1) 建 session
SID=$(curl -s -X POST $BASE/session | python3 -c 'import sys,json;print(json.load(sys.stdin)["sessionId"])')

# 2) 导航
curl -s -X POST $BASE/session/$SID/act \
  -H 'content-type: application/json' \
  -d '{"action":"navigate","args":{"url":"https://example.com"}}'

# 3) 读带编号的 DOM
curl -s $BASE/session/$SID/dom

# 4) 点第 0 号元素（编号取自上一步 /dom）
curl -s -X POST $BASE/session/$SID/act \
  -H 'content-type: application/json' \
  -d '{"action":"click","args":{"index":0}}'

# 5) 看 VNC（浏览器打开）
#    只读： http://localhost:6080/vnc.html
#    交互： http://localhost:6081/vnc.html
```

> 若设置了 `OMP_BROWSER_TOKEN`，每条 curl 加 `-H "Authorization: Bearer $OMP_BROWSER_TOKEN"`。

## 9. 不在范围

- `GET /auth-state`：首版不做，登录墙检测归 mindora agent（读 `/dom` 自判）。
- 站点专属 SOP（x/xueqiu/taoguba 等）：留在本地 `omp web-operator`，不进容器。
- 多租户 / 连接池：不做（单用户单容器）。
