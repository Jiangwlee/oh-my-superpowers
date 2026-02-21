# x-research-skill 架构深度分析

来源：`github_cache/skills_repos/x-research-skill/`

---

## 一、整体架构：LLM 策略层 + CLI 执行层分离

```
用户请求
  ↓
LLM（SKILL.md 策略）
  ↓ 决定查什么、怎么过滤、按什么排序
bun run x-search.ts [command] [options]
  ↓ CLI 实际执行
X API  ←→  File Cache (data/cache/)
  ↓
格式化输出（Telegram / Markdown）→ 可选 Save 到 drafts/
```

**设计哲学**：LLM 不直接调用 API，通过 CLI 这一层隔离，好处是：
- CLI 可以独立维护（缓存、限流、格式化）
- LLM 只需关心"搜什么"，不需要关心"怎么搜"
- 成本可追踪、执行可调试

---

## 二、文件结构

```
x-research-skill/
├── SKILL.md           # 研究策略 + CLI 用法（LLM 读）
├── x-search.ts        # CLI 入口，命令路由 + arg 解析
├── lib/
│   ├── api.ts         # X API 封装：search / thread / profile / getTweet
│   ├── cache.ts       # 文件缓存，MD5 键，可配 TTL
│   └── format.ts      # 输出格式化：Telegram / Markdown / Profile
├── data/
│   ├── watchlist.json  # 监控账号列表（持久化）
│   └── cache/          # 缓存文件目录（自动管理）
└── references/
    └── x-api.md        # X API 端点文档（不放在 SKILL.md 里）
```

---

## 三、实时数据获取（`lib/api.ts`）

### 认证机制（双层兜底）

```typescript
function getToken(): string {
  // 优先读环境变量
  if (process.env.X_BEARER_TOKEN) return process.env.X_BEARER_TOKEN;
  // 兜底：从 ~/.config/env/global.env 读取
  const envFile = readFileSync(`${HOME}/.config/env/global.env`, "utf-8");
  const match = envFile.match(/X_BEARER_TOKEN=["']?([^"'\n]+)/);
  if (match) return match[1];
  throw new Error("X_BEARER_TOKEN not found");
}
```

不硬编码、不写进 skill 配置。env var → 全局配置文件 两级兜底。

### 速率限制保护

```typescript
const RATE_DELAY_MS = 350; // 保持在 X API 450 req/15min 以下

// 多页翻页：每页之间自动 sleep
if (page < pages - 1) await sleep(RATE_DELAY_MS);

// 429 处理：读 header 精准告知等待时间
if (res.status === 429) {
  const reset = res.headers.get("x-rate-limit-reset");
  const waitSec = reset
    ? Math.max(parseInt(reset) - Math.floor(Date.now() / 1000), 1)
    : 60;
  throw new Error(`Rate limited. Resets in ${waitSec}s`);
}
```

### 时间过滤：人类可读 → API 格式自动转换

```typescript
function parseSince(since: string): string | null {
  // 支持简写："30m" / "1h" / "3d"
  const match = since.match(/^(\d+)(m|h|d)$/);
  if (match) {
    const ms = unit === "m" ? num * 60_000 :
               unit === "h" ? num * 3_600_000 :
               num * 86_400_000;
    return new Date(Date.now() - ms).toISOString();
  }
  // 支持完整 ISO 8601 字符串直接传入
  if (since.includes("T") || since.includes("-")) { ... }
}
```

LLM 使用 `"3h"` / `"1d"` 等人类可读格式，CLI 负责转成 API 需要的 ISO 8601。

### 数据拍平（parseTweets）

X API 的 tweet 和用户信息是分离的（tweet 有 `author_id`，用户信息在 `includes.users[]`）：

```typescript
function parseTweets(raw: RawResponse): Tweet[] {
  // 建立 userId → user 查找表
  const users: Record<string, any> = {};
  for (const u of raw.includes?.users || []) { users[u.id] = u; }

  return raw.data.map((t) => ({
    id: t.id,
    text: t.text,
    username: users[t.author_id]?.username || "?",
    metrics: {
      likes: t.public_metrics.like_count,
      impressions: t.public_metrics.impression_count,
      ...
    },
    tweet_url: `https://x.com/${username}/status/${t.id}`,
    ...
  }));
}
```

**输出给 LLM 的是已组装好的 `Tweet[]`**，LLM 无需理解 API 的嵌套关系。

---

## 四、文件缓存系统（`lib/cache.ts`）

### 缓存键设计

```typescript
function cacheKey(query: string, params: string = ""): string {
  return createHash("md5")
    .update(`${query}|${params}`)  // 查询 + 参数（sort/pages/since）
    .digest("hex")
    .slice(0, 12);                  // 12位哈希，避免文件名过长
}
```

缓存文件：`data/cache/{hash}.json`，内容包含原始查询、时间戳、推文数组。

### 差异化 TTL

```typescript
// Quick 模式：1小时（适合频繁查同一话题，节省 API 费用）
// 普通模式：15分钟（深度研究，需要较新数据）
const cacheTtlMs = quick ? 3_600_000 : 900_000;

// 关键：quick 标志不计入缓存键（quick/普通模式共享缓存）
const cacheParams = `sort=${sortOpt}&pages=${pages}&since=${since || "7d"}`;
```

| 模式 | TTL | 适用场景 |
|------|-----|---------|
| `--quick` | 1 小时 | 日常粗筛，避免重复计费 |
| 普通 | 15 分钟 | 深度研究，需要较新数据 |

### 成本追踪

```typescript
const rawTweetCount = tweets.length; // 过滤前记录 API 实际读取量

// 后置过滤不影响成本（API 按读取量计费，非展示量）
const filtered = rawTweetCount !== tweets.length ? ` → ${tweets.length} after filters` : "";
const cost = (rawTweetCount * 0.005).toFixed(2);

// 输出到 stderr（不污染正文输出）
console.error(`📊 ${rawTweetCount} tweets read · est. cost ~$${cost}`);
```

---

## 五、Watchlist + Heartbeat 定期任务模式

### Watchlist 数据结构

```json
// data/watchlist.json
{
  "accounts": [
    { "username": "frankdegods", "note": "NFT founder", "addedAt": "2026-01-15T08:23:00Z" }
  ]
}
```

### 批量检查实现

```typescript
async function cmdWatchlist() {
  if (sub === "check") {
    for (const acct of wl.accounts) {
      try {
        const { user, tweets } = await api.profile(acct.username, { count: 5 });
        // 每个账号展示最新3条
        for (const t of tweets.slice(0, 3)) { console.log(fmt.formatTweetTelegram(t)); }
      } catch (e: any) {
        // 单账号失败不中断整体（try-catch 在循环内部）
        console.error(`Error checking @${acct.username}: ${e.message}`);
      }
    }
  }
}
```

**容错设计**：单账号 API 报错不中断整个批量检查。

### Heartbeat 集成策略

SKILL.md 中的设计原则：

```markdown
## Heartbeat Integration
On heartbeat, can run `watchlist check` to see if key accounts posted
anything notable. Flag to Frank only if genuinely interesting/actionable
— don't report routine tweets.
```

**核心原则**：定期执行 ≠ 定期汇报。由 LLM 判断内容是否"真正有价值"，不是规则过滤。

---

## 六、Agentic 研究循环（6 步）

```
1. 分解问题
   将研究问题拆成 3-5 个不同角度的查询：
   - 核心查询：直接关键词
   - 专家视角：from:<username>
   - 痛点：(broken OR bug OR issue OR migration)
   - 正面信号：(shipped OR love OR fast OR benchmark)
   - 链接维度：url:github.com

2. 执行搜索 + 评估信噪比 → 调整参数

3. 追踪线程（thread 命令）
   高互动 / 线程起始推文 → 获取完整对话

4. 深挖链接内容
   多条推文引用同一链接 → web_fetch 获取原文

5. 按主题（而非查询）分组综合

6. 存档
   --save 存到 ~/clawd/drafts/x-research-{slug}-{date}.md
```

### 噪音过滤启发式规则

```markdown
太多噪音 → 加 -is:reply，用 --sort likes，缩窄关键词
太少结果 → 用 OR 扩展，去掉限制性操作符
加密垃圾 → 加 -$ -airdrop -giveaway -whitelist
只要专家 → from: 或 --min-likes 50
只要实质 → has:links
```

---

## 七、格式化层（`lib/format.ts`）

同一套数据适配不同下游渠道：

```typescript
// Telegram：信息密集，适合消息推送
"@username (5.2K❤️ 120K👁 · 3h)\n推文内容...\n🔗 链接"

// Markdown：适合研究文档，可被下一个会话读取
"- **@username** (5200L 120000I) [Tweet](url)\n  > 推文内容"
```

**量化替代评价**：数字（5.2K❤️）替代"评价很高"等空泛描述。

---

## 八、对 OpenclawSkills A 股监控的借鉴

| x-research 概念 | A 股场景对应 |
|----------------|-------------|
| `watchlist.json`（账号列表） | 自选股池（人气榜前200） |
| `watchlist check`（批量拉最新） | 批量获取自选股资金流向/涨跌 |
| Heartbeat（定时触发） | 盘中轮询（每30分钟） |
| `--quick` 快速模式 | 快速扫描（只看涨跌幅，不抓详情） |
| 文件缓存（15分钟 TTL） | 分时数据缓存（避免重复请求行情接口） |
| `--save` 存档 drafts/ | 日盘后复盘报告保存 |
| "只汇报真正有价值的" | 异动过滤（只推送超阈值的资金流入/涨停） |
| 成本追踪（stderr 输出） | API 调用量统计（防超限） |
| 人类可读时间格式（"3h"） | 交易时间段表达（"开盘1h"） |
