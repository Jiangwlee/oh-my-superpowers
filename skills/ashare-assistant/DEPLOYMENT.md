# ashare-assistant 部署指南

## 架构概览

```
本机 / VPS
├── ashare-data（定时任务，每日盘后自动采集）
│   └── cron: ashare-collect → ~/.ashare-assistant/data/{DATE}/filtered/
└── ashare-assistant（OpenClaw Agent，按需触发）
    └── 读取 filtered/ 数据 → LLM 分析 → trading_plan.md
```

`ashare-assistant` **运行时依赖** `ashare-data`（`packages/ashare-data`）：
- `ashare-data` 提供 `ashare-collect` CLI，负责采集并写入 `~/.ashare-assistant/data/{DATE}/`
- `ashare-assistant` 读取上述目录中的 `raw/filtered/analysis/report` 数据并执行 LLM 工作流

两个组件通过固定默认目录 `~/.ashare-assistant` 共享数据目录，**分别独立部署**，但部署顺序必须是：**先 `ashare-data`，后 `ashare-assistant`**。

---

## 一、前置要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | ashare-data 包运行时 |
| Node.js | 22+ | OpenClaw Gateway 运行时 |
| OpenClaw | 最新版 | `openclaw` CLI |
| OpenCode | 最新版 | `opencode` CLI（子代理调用） |

---

## 二、首次部署

> 部署顺序（必须）：先完成 `2.2 安装 ashare-data 包`，确认 `ashare-collect --help` 正常，再部署/触发 `ashare-assistant`。

### 2.1 安装环境依赖

```bash
# 在 OpenclawSkills 项目根目录执行
bash skills/ashare-assistant/setup.sh
```

支持：macOS、Ubuntu/Debian、RHEL/CentOS/Rocky/AlmaLinux/Fedora。

### 2.2 安装 ashare-data 包

```bash
python3 -m pip install -e packages/ashare-data --break-system-packages
```

验证：

```bash
ashare-collect --help
```

### 2.3 配置 JVQuant 账户（可选，券商持仓功能）

创建 `~/.openclaw/jvquant.json`：

```json
{
  "token": "<your-token>",
  "account": "<account-id>",
  "password": "<password>"
}
```

> 无此配置时，采集仍可正常运行，但不会采集券商账户数据，后续无法生成持仓分析和交易复盘。

---

## 三、本地部署（macOS 开发机）

### 3.1 部署 Skill

```bash
mkdir -p ~/clawd/skills/ashare-assistant
cp -R skills/ashare-assistant/. ~/clawd/skills/ashare-assistant/
openclaw gateway restart
```

### 3.2 设置定时采集

编辑 crontab（`crontab -e`）：

```cron
# 每个交易日 15:35 采集
35 15 * * 1-5 /usr/local/bin/ashare-collect --date $(date +\%Y-\%m-\%d) >> ~/.ashare-assistant/collect.log 2>&1
```

> 时间选择 15:35 而非 15:00，避免盘后数据还未更新完毕。

### 3.3 手动验证

```bash
# 1) 手动触发一次采集（ashare-data）
ashare-collect --date $(date +%Y-%m-%d) --verbose

# 2) 检查共享数据目录（ashare-assistant 依赖这些输入）
ls ~/.ashare-assistant/data/$(date +%Y-%m-%d)/filtered/
cat ~/.ashare-assistant/data/$(date +%Y-%m-%d)/filtered/index.md

# 3) 再在 OpenClaw 中触发 ashare-assistant（复盘/交易计划）
```

---

## 四、远端部署（Tencent VPS）

Agent 绑定关系：`ashare-assistant` 绑定 `smartrader`，工作目录 `workspace-smartrader`。

### 4.1 部署 Skill

```bash
# 整个 skill 目录
scp -r skills/ashare-assistant/ \
    root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/

# 仅更新单个脚本（增量更新）
scp skills/ashare-assistant/scripts/run_analysis.py \
    root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/ashare-assistant/scripts/

# 重启 Gateway
ssh root@tencent-vps "source ~/.nvm/nvm.sh && openclaw gateway restart"
```

### 4.2 安装 ashare-data 包

```bash
ssh root@tencent-vps
# 在 VPS 上执行：
cd /path/to/OpenclawSkills
python3 -m pip install -e packages/ashare-data --break-system-packages
```

或直接复制包目录再安装：

```bash
scp -r packages/ashare-data/ root@tencent-vps:/root/ashare-data/
ssh root@tencent-vps "python3 -m pip install -e /root/ashare-data --break-system-packages"
```

### 4.3 设置定时采集（VPS crontab）

```bash
ssh root@tencent-vps "crontab -e"
```

```cron
# 每个交易日 15:35 采集
35 15 * * 1-5 /usr/local/bin/ashare-collect --date $(date +\%Y-\%m-\%d) >> /root/.ashare-assistant/collect.log 2>&1
```

---

## 五、更新部署

修改 skill 脚本后，重新部署并重启 Gateway：

```bash
# 1. 仅更新脚本（推荐，避免覆盖 VPS 上的配置文件）
scp skills/ashare-assistant/scripts/<changed-file>.py \
    root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/ashare-assistant/scripts/

# 2. 重启 Gateway
ssh root@tencent-vps "source ~/.nvm/nvm.sh && openclaw gateway restart"
```

若 `packages/ashare-data` 有更新：

```bash
scp -r packages/ashare-data/ root@tencent-vps:/root/ashare-data/
ssh root@tencent-vps "python3 -m pip install -e /root/ashare-data --break-system-packages"
```

说明：`ashare-data` 的更新可能改变 `ashare-assistant` 的输入文件内容/结构。生产更新建议顺序为：
1. 更新并安装 `packages/ashare-data`
2. 手动运行一次 `ashare-collect` 验证数据产出
3. 再更新 `skills/ashare-assistant`

---

## 六、目录结构说明

```
~/.ashare-assistant/
├── data/
│   └── {DATE}/
│       ├── raw/                 # ashare-collect 输出的原始 JSON
│       │   └── deep_research/   # 个股深研原始数据（dr_*_em/tgb.json）
│       ├── filtered/            # 格式转换后的 Markdown（ashare-assistant 读取）
│       ├── analysis/            # 结构化分析产物（JSON）
│       │   ├── candidates.json  # 候选股
│       │   ├── trade_review.json # 交易复盘
│       │   ├── holding_insight.json # 持仓洞察
│       │   └── deep_research/   # 个股深研结构化中间产物（compact/timing）
│       ├── report/              # 子代理中间报告
│       ├── market_review.md     # 复盘报告
│       ├── trading_plan.md      # 交易计划
├── cache/                       # HTTP 请求缓存
├── broker_data/
│   ├── positions/{DATE}.json    # 盘后持仓快照
│   └── orders/{DATE}.json       # 当日委托记录
└── memory/
    └── decision_log.jsonl       # 历史决策日志
```

---

## 七、常见问题

**Q: `ashare-collect` 命令找不到**

```bash
python3 -m pip install -e packages/ashare-data --break-system-packages
which ashare-collect  # 确认 PATH 中有 pip bin 目录
```

`ashare-assistant` 依赖 `ashare-collect` 产出的共享数据目录；若未安装 `ashare-data` 或 cron 未产出数据，Skill 会因缺少 `~/.ashare-assistant/data/{DATE}/filtered/` 输入而无法正常完成复盘流程。

**Q: 盘后采集到空的 broker_account（订单为 0）**

已通过盘后缓存短路机制自动处理：15:00 后若当日持仓缓存存在则直接复用，不会触发 API 重新查询。

**Q: VPS 上 cron 不执行**

检查 PATH：cron 环境没有 `~/.bashrc`，需在 crontab 中显式指定路径：

```cron
35 15 * * 1-5 /usr/local/bin/ashare-collect --date $(date +\%Y-\%m-\%d) >> /root/.ashare-assistant/collect.log 2>&1
```
