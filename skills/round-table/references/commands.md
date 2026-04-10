# Round Table CLI 命令参考

## Session 子命令

### `session init <topic> [options]`

创建新的圆桌讨论 session。

| 参数 | 说明 |
|------|------|
| `<topic>` | 讨论议题（必填） |
| `--roles <id1,id2,...>` | 内置角色 ID，逗号分隔 |
| `--participants <json>` | 自定义角色 JSON 数组 |
| `--context <text\|file>` | 背景信息（文本或文件路径） |

内置角色 ID：`steve-jobs`、`elon-musk`、`linus-torvalds`、`alan-kay`、`andrej-karpathy`、`richard-stallman`

输出：session-id（时间戳格式，如 `20260328T074441`）

```bash
omp round-table session init "是否需要独立Agent框架" \
  --roles linus-torvalds,alan-kay,elon-musk \
  --context "当前项目使用 Pi + Claude Code 双运行时"
```

### `session status`

显示当前 session 的状态（session-id、议题、轮次、参与者数）。

### `session context [brief|detail]`

读取 session 的 `context.md`。`brief` 返回前 10 行，`detail` 返回全文。默认 `brief`。

### `session messages [msg-id]`

无参数时：历史摘要 + 最近一轮完整消息。指定 `msg-id` 时：该消息详情。

### `session end --output-dir <path>`

结束讨论，生成 Markdown 文档到指定目录。

---

## Round 子命令

所有 round 子命令自动取 `meta.json` 中的 `current_round`，无需传轮次号。

### `round run`

**一条命令完成一轮讨论。** 内部流程：

1. 构建四层 prompt（角色身份 + 背景 + 历史 + 本轮指令）
2. 在 tmux 中并行启动所有参与者
3. 等待全部完成（超时 5 分钟）
4. 解析 response 文件，自动 post-message

输出 JSON：

```json
{
  "round": 2,
  "collected": [
    {"role_id": "linus-torvalds", "name": "Linus Torvalds", "action": "质疑", "summary": "..."}
  ],
  "failed": []
}
```

### `round spawn`

只启动参与者，不自动收集。轮次自动 `current_round + 1`。

### `round collect`

解析当前轮的 `responses/round-N-*.md` 文件：
- 提取 `【Name】【action】` 和 `**简言之**：summary`
- 自动调用 post-message 写入 `messages.jsonl`
- 输出 JSON 结果

### `round watch [-f] [-n lines]`

实时查看当前轮参与者的输出状态。`-f` 持续跟踪。

### `round attach`

连接 tmux session，直接观看参与者运行过程。`Ctrl+B D` 退出。

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ROUND_TABLE_SESSION` | 指定 session-id | 自动使用最新 |
| `RT_DATA_DIR` | 数据存储根目录 | `~/.local/share/oh-my-superpowers/round-table` |
| `RT_TIMEOUT` | 单参与者超时秒数 | `300` |
| `OMP_HOME` | oh-my-superpowers 安装路径 | `~/.oh-my-superpowers` |

## 典型工作流

```bash
# 1. 初始化
export ROUND_TABLE_SESSION=$(omp round-table session init "议题" --roles linus-torvalds,alan-kay,elon-musk)

# 2. 每轮讨论
result=$(omp round-table round run)

# 3. Orchestrator 综述后 post
omp round-table post-message moderator summary.md \
  --round 1 --name "主持人" --action "综合" --summary "本轮一句话摘要"

# 4. 重复 2-3，直到结束

# 5. 生成文档
omp round-table session end --output-dir ./docs/round-table
```
