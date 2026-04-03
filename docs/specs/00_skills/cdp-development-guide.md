# CDP 开发指南

web-operator skill 的 Chrome DevTools Protocol 开发参考。记录架构设计、开发模式和踩坑经验，供后续 SOP 脚本开发参照。

## 架构概览

```
omp-web-operator (bin/omp-web-operator)     ← CLI 入口，dispatcher
  └── cdp.mjs (scripts/cdp.mjs)             ← CDP 核心，所有浏览器原语
        ├── CDP class                        ← WebSocket 客户端
        ├── Per-tab daemon                   ← 每个 tab 一个持久进程
        └── CLI ↔ daemon IPC                 ← Unix socket NDJSON 协议
  └── core/common.sh                         ← Shell helpers（tab 管理、CDP 封装）
  └── sites/<site>/                          ← 站点 SOP 脚本
        ├── common.sh                        ← 站点专用 helpers
        ├── search.sh                        ← 搜索工作流
        └── open-post.sh                     ← 帖子+评论提取
```

### 三层模型

| 层 | 职责 | 文件 |
|---|---|---|
| **Core** | Chrome 连接、tab 路由、CDP 命令原语 | `cdp.mjs`, `core/common.sh` |
| **Sites** | 站点 SOP（搜索、帖子提取等） | `sites/<site>/*.sh` |
| **CLI** | 子命令分发 | `bin/omp-web-operator` |

### Daemon 机制

cdp.mjs 为每个 tab 维护一个 **持久 daemon 进程**：

1. 首次访问 tab → spawn daemon 子进程 → daemon attach 到 tab → 监听 Unix socket
2. 后续命令 → 直接连 socket → 复用已建立的 CDP session
3. daemon 在 20 分钟空闲或 tab 关闭后自动退出

```
CLI (cdp eval <target> <expr>)
  → Unix socket → daemon 进程
    → WebSocket → Chrome browser
      → Target session → 页面执行
    ← 结果返回
  ← stdout
```

**关键约束**：daemon 缓存的是启动时的 cdp.mjs 代码。修改 cdp.mjs 后必须 `cdp stop` 杀掉旧 daemon，否则新代码不生效。

### IPC 协议

请求/响应均为 NDJSON（一行一个 JSON 对象）：

```json
// Request
{"id": 1, "cmd": "eval", "args": ["document.title"]}

// Response (success)
{"id": 1, "ok": true, "result": "Page Title"}

// Response (error)
{"id": 1, "ok": false, "error": "No main article found"}
```

## 核心开发模式

### 1. 短 eval 原则

**cdp.mjs 的 `send()` 方法有 15 秒超时**（`TIMEOUT = 15000`）。`Runtime.evaluate` 的 `awaitPromise: true` 会等 Promise 完成，但 daemon 端在 15 秒后就会 reject。

```javascript
// ❌ 长时间运行的 async eval — 会超时
(async () => {
  for (let i = 0; i < 500; i++) {
    window.scrollBy(0, 3000);
    await new Promise(r => setTimeout(r, 1500)); // 每轮 1.5 秒
    // ... 提取数据
  }
  return results; // 永远到不了这里
})()

// ✅ 短 eval — 毫秒级完成，由 shell 驱动循环
(() => {
  const items = [];
  document.querySelectorAll('article').forEach(a => { /* extract */ });
  return items;
})()
```

**规则**：eval 表达式必须在秒级内完成。长时间任务拆成 shell 循环 + 多次短 eval。

### 2. Shell 驱动循环 vs JS 内循环

需要滚动加载内容时（无限滚动页面），用 **shell 驱动循环**：

```bash
for (( round=0; round<MAX_ROUNDS; round++ )); do
  cdp scroll "$TARGET" down 3 >/dev/null 2>&1   # 1. 滚动
  sleep 1.5                                       # 2. 等渲染
  NEW="$(cdp_eval "$TARGET" "$EXTRACT_EXPR")"     # 3. 短 eval 提取
  # 4. shell 端累加和判停
done
```

优点：
- 每个 eval 都是短操作，不会超时
- shell 端可以 stderr 输出进度
- 可以在循环中穿插其他 cdp 命令（scroll、click 等）

### 3. 浏览器端状态跨 eval 共享

多轮 eval 之间需要共享状态（如去重集合）时，用 `window.__omp_*` 全局变量：

```bash
# 初始化
cdp_eval "$TARGET" "window.__omp_seen = new Set(); 'ok'" >/dev/null

# 每轮使用
cdp_eval "$TARGET" '(() => {
  const seen = window.__omp_seen;
  // ... seen.has(id) / seen.add(id) ...
})()'

# 清理
cdp_eval "$TARGET" "delete window.__omp_seen; 'done'" >/dev/null
```

**命名约定**：`window.__omp_<name>`，避免与页面自身变量冲突。用完必须清理。

### 4. heredoc 传递 JS 表达式

用 `<<'EOF'`（**带引号**）防止 shell 变量替换和特殊字符转义：

```bash
read -r -d '' EXPR <<'EOF' || true
(() => {
  const price = document.querySelector('.price');
  return { value: price?.innerText || '' };  // $ 不会被 shell 解释
})()
EOF

# 需要注入 shell 变量时，用字符串替换
EXPR="${EXPR/PLACEHOLDER_VALUE/${SHELL_VAR}}"
```

**注意**：`|| true` 是必须的，因为 `read -r -d ''` 在读到 EOF 时返回非零退出码，会被 `set -e` 捕获。

### 5. 大数据输出用文件传递

当 eval 返回的 JSON 很大时（数百条评论），不能用 shell 变量或 `--argjson` 传给 jq，会碰到 `ARG_MAX` 限制：

```bash
# ❌ 超过 ARG_MAX
HUGE_JSON="$(cdp_eval ...)"
jq --argjson data "$HUGE_JSON" '...'  # Argument list too long

# ✅ 通过文件传递
cdp_eval ... > "$TMPFILE"
jq -s '.[0] + {comments: .[1]}' "$MAIN_FILE" "$COMMENTS_FILE"
```

## 踩坑记录

### 1. Page.bringToFront — 非前台 tab 无法滚动

**现象**：`window.scrollBy()` 在非活跃 tab 上不生效，scroll 循环看似在运行但页面没动。

**根因**：x.com（以及部分其他 SPA）会检测 tab 是否在前台，背景 tab 上的 programmatic scroll 被忽略。

**解决**：在 scroll 前调用 `Page.bringToFront`：

```bash
cdp_bring_to_front() {
  cdp evalraw "$target" "Page.bringToFront" '{}' >/dev/null 2>&1 || true
}
```

已封装在 `core/common.sh` 中。任何需要 scroll 的 SOP 都应在导航后调用此函数。

### 2. Input.dispatchMouseEvent mouseWheel — Chrome 不返回响应

**现象**：`cdp.send('Input.dispatchMouseEvent', { type: 'mouseWheel', ... })` 永远不返回，daemon 超时。

**根因**：Chrome 对 `mouseWheel` 类型的 `Input.dispatchMouseEvent` 是 fire-and-forget，不发送 CDP 响应。daemon 的 `send()` 等待一个永远不会来的响应，15 秒后超时。

**解决**：scroll 命令改用 `window.scrollBy()` via eval 实现：

```javascript
async function scrollStr(cdp, sid, direction, amount) {
  const multiplier = parseFloat(amount) || 3;
  const sign = dir === 'down' ? 1 : -1;
  const expr = `(() => {
    const dy = window.innerHeight * ${multiplier} * ${sign};
    window.scrollBy({ top: dy, behavior: 'instant' });
    return dy;
  })()`;
  const dy = await evalStr(cdp, sid, expr);
  return `Scrolled ${dir} ${multiplier} viewport(s) (${dy}px)`;
}
```

### 3. x.com 虚拟化列表 — article 元素动态增删

**现象**：x.com 评论区使用虚拟化渲染，只有视口附近的 article 元素存在于 DOM 中。滚出视口的 article 会被移除。

**影响**：
- 不能一次性 `querySelectorAll('article')` 拿到所有评论
- 必须在每次 scroll 后立即提取当前可见的 article
- 需要跨轮次去重（用 status URL 作为唯一标识）

**模式**：
```
scroll → wait → extract visible articles → deduplicate → accumulate
```

### 4. x.com "Show probable spam" 折叠按钮

**现象**：大量评论的帖子中，x.com 会在评论流中插入 "Show probable spam" 按钮，不点击则后续评论无法加载。

**解决**：每轮 scroll 后检测并点击折叠按钮：

```javascript
(() => {
  const btns = [...document.querySelectorAll('button, [role="button"]')];
  for (const btn of btns) {
    const label = (btn.innerText || '').trim();
    if (/^Show\s+(probable\s+spam|additional\s+repl)/i.test(label)) {
      btn.click();
      return true;
    }
  }
  return false;
})()
```

### 5. reply_count 与实际可加载评论数不一致

**现象**：x.com reply 按钮的 aria-label 显示 748 条回复，实际只能加载约 430 条。

**根因**：`reply_count` 包含已删除、被隐藏、被 spam 过滤的回复。这些回复在 API 层面存在但不会被渲染到页面上。

**处理**：将 `reply_count` 作为参考值返回给调用方，但不以它作为"全部加载完成"的判断标准。用连续空轮次（`emptyRounds >= 5`）作为实际停止条件。

### 6. Daemon 缓存旧代码

**现象**：修改 cdp.mjs 后，执行命令仍然是旧行为。

**根因**：daemon 是 detached 子进程，启动时加载的是当时的代码。修改源文件不影响已运行的 daemon。

**解决**：开发时修改 cdp.mjs 后必须执行：

```bash
node skills/web-operator/scripts/cdp.mjs stop
# 或
omp-web-operator page stop
```

### 7. DevToolsActivePort 过期

**现象**：`No DevToolsActivePort found` 或连接失败。

**根因**：Chrome 重启后 `DevToolsActivePort` 文件可能包含旧的 WebSocket 路径。

**解决**：cdp.mjs 优先从 `/json/version` 获取实时 WebSocket URL，仅在 HTTP 请求失败时 fallback 到文件内容。如果仍然失败，需要确认 Chrome 已启用 `chrome://inspect/#remote-debugging`。

## 新增 CDP 命令的标准流程

1. **在 cdp.mjs 中添加实现函数**（参考 `scrollStr`、`clickXyStr` 等同类命令）
2. **注册到 daemon switch-case**（`handleCommand` 函数内）
3. **添加到 `NEEDS_TARGET` set**（如果命令需要 target 参数）
4. **更新 USAGE 文档**（cdp.mjs 内的 `USAGE` 常量）
5. **更新 Public interface 注释**（文件顶部）
6. **更新 daemon IPC 文档**（USAGE 中的 DAEMON IPC 段）
7. **如果需要 shell wrapper**，在 `core/common.sh` 中添加
8. **`cdp stop` 重启 daemon 后测试**

## SOP 脚本编写清单

编写新的站点 SOP 脚本时检查：

- [ ] 使用 `find_or_create_tab` 复用已有 tab，而非每次 `cdp open`
- [ ] 导航用 `cdp_nav`（URL），不用模拟点击
- [ ] 需要 scroll 前调用 `cdp_bring_to_front`
- [ ] 每个 eval 表达式在秒级内完成
- [ ] 长任务用 shell 驱动循环
- [ ] 跨 eval 状态用 `window.__omp_*`，用完清理
- [ ] heredoc 用 `<<'EOF'`（带引号），加 `|| true`
- [ ] 大 JSON 输出用临时文件传递，不用 shell 变量
- [ ] 进度信息输出到 stderr，数据输出到 stdout
- [ ] 连续空轮次容忍（至少 5 轮），不要一轮空就退出
