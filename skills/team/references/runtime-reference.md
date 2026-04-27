# Runtime Reference

> 三种 AI runtime 的 CLI 差异速查。omp dispatch run 内部使用这些命令驱动 agent 执行任务。

## Claude

| 参数 | 值 |
|------|---|
| 调用方式 | `cat prompt.md \| claude -p --no-session-persistence --dangerously-skip-permissions --model <model>` |
| Prompt 传递 | stdin 管道 |
| 模型指定 | `--model <model>` (支持别名如 `sonnet`、`opus`，也支持全名如 `claude-sonnet-4-6`) |
| 工作目录 | 在目标目录下执行即可（`cd <dir> && cat prompt.md \| claude -p`） |
| 输出格式 | `--output-format text` (默认), `json`, `stream-json` |
| 超时控制 | 无内置 timeout 参数，需外部 `timeout` 命令包裹 |
| 权限跳过 | `--dangerously-skip-permissions` (仅限沙箱环境) |
| 已知限制 | 无原生 `--output-file` 参数，需 shell 重定向；`-p` 模式跳过工作区信任对话框 |

### 调用模板

```bash
cd {working_directory} && \
  cat {prompt_file} | claude -p --no-session-persistence --dangerously-skip-permissions --model {model} > {output_file} 2>{log_file}
```

## Codex

| 参数 | 值 |
|------|---|
| 调用方式 | `cat prompt.md \| codex exec - --dangerously-bypass-approvals-and-sandbox` |
| Prompt 传递 | stdin，`-` 显式声明从 stdin 读取 |
| 模型指定 | `-m <model>` / `--model <model>` |
| 工作目录 | 在目标目录下执行（Codex 操作当前工作目录） |
| 沙箱模式 | `-s read-only` / `workspace-write` / `danger-full-access` |
| 超时控制 | 无内置 timeout 参数，需外部 `timeout` 命令包裹 |
| 已知限制 | 无 `--output-file` 参数，stdout 是主输出；沙箱模式限制文件写入范围 |

### 调用模板

```bash
cd {working_directory} && \
  cat {prompt_file} | codex exec - --dangerously-bypass-approvals-and-sandbox -m {model} > {output_file} 2>{log_file}
```

## Pi

| 参数 | 值 |
|------|---|
| 调用方式 | `pi --no-session -p @prompt.md --model <model>` |
| Prompt 传递 | `@file` 原生语法（Pi 直接读取文件内容作为消息） |
| 模型指定 | `--model <model>` (支持 `provider/model-id` 格式，如 `anthropic/sonnet`) |
| 工作目录 | 在目标目录下执行 |
| Session 控制 | `--no-session` 必须 — 防止污染用户 session 历史 |
| 超时控制 | 无内置 timeout 参数，需外部 `timeout` 命令包裹 |
| 已知限制 | `@file` 语法要求文件路径存在；无 `--output-file` 参数，需 shell 重定向 |

### 调用模板

```bash
cd {working_directory} && \
  pi --no-session -p @{prompt_file} --model {model} > {output_file} 2>{log_file}
```

## Prompt 传递安全性对比

| 方式 | 特殊字符处理 | 长度限制 | 推荐度 |
|------|-------------|---------|--------|
| stdin 管道 (`cat file \| cmd`) | 安全，文件内容原样传递 | 无实际限制 | 推荐 (claude, codex) |
| `@file` 原生语法 | 安全，runtime 直接读文件 | 无实际限制 | 推荐 (pi) |
| 命令行参数 (`cmd "prompt"`) | 不安全，shell 转义问题 | 受 ARG_MAX 限制 | 不推荐 |
| `$(cat file)` 命令替换 | 不安全，含 `$`/`` ` ``/`\` 时会被 shell 展开 | 受 ARG_MAX 限制 | 不推荐 |

## omp dispatch run 内部映射

`omp dispatch run <runtime> [prompt] [--prompt-file <path>] [--model <model>] [--timeout <sec>] [--output-file <path>] [--cwd <dir>]`

各参数到 runtime CLI 的映射：

| omp dispatch 参数 | claude | codex | pi |
|--------------|--------|-------|-----|
| `--prompt-file` | stdin 管道 | stdin 管道 + `-` | `@file` |
| `--model` | `--model` | `-m` | `--model` |
| `--timeout` | 外部 `timeout` | 外部 `timeout` | 外部 `timeout` |
| `--output-file` | `> file` 重定向 | `> file` 重定向 | `> file` 重定向 |
| `--cwd` | `cd dir &&` | `cd dir &&` | `cd dir &&` |
