# A-Share Assistant Deployment

Purpose: Deploy and update `ashare-assistant` with deterministic runtime dependencies.
Audience: AI agents and developers operating local or VPS environments.
Input:   Source files under `skills/ashare-assistant/` and `packages/ashare-data/`.
Output:  A running skill plus scheduled data collection to `~/.ashare-assistant/`.
Sections: Prerequisites | First Deployment | Local Deployment | VPS Deployment | Update Flow | Guardrails

## Prerequisites

1. Read repo-level `Deployment.md` before executing any deploy command.
2. Install Python 3.10+ and Node.js 22+.
3. Ensure `openclaw` CLI is available.

## First Deployment

1. Install environment dependencies.

```bash
bash skills/ashare-assistant/setup.sh
```

2. Install the data package.

```bash
python3 -m pip install -e packages/ashare-data --break-system-packages
ashare-collect --help
```

3. Deploy skill files.

```bash
mkdir -p "$HOME/clawd/skills/ashare-assistant"
cp -R skills/ashare-assistant/. "$HOME/clawd/skills/ashare-assistant/"
openclaw gateway restart
```

## Local Deployment (macOS)

Configure crontab (`crontab -e`):

```cron
*/30 * * * * /opt/homebrew/bin/ashare-collect --date $(date +\%Y-\%m-\%d) >> $HOME/.ashare-assistant/logs/collect.log 2>&1
0 16 * * * /opt/homebrew/bin/ashare-diagnose >> $HOME/.ashare-assistant/logs/diagnose.log 2>&1
*/10 9-15 * * 1-5 /opt/homebrew/bin/ashare-wl-monitor >> $HOME/.ashare-assistant/logs/wl-monitor.log 2>&1
```

Manual validation:

```bash
DATE=$(date +%Y-%m-%d)
ashare-collect --date "$DATE" --verbose
ls "$HOME/.ashare-assistant/data/$DATE/filtered/"
```

## VPS Deployment (Tencent VPS)

1. Copy skill source to VPS workspace.

```bash
scp -r skills/ashare-assistant/ \
  root@tencent-vps:/root/.openclaw/workspace-smartrader/skills/
```

2. Install or update `ashare-data` on VPS.

```bash
# 注意：scp 传目录时以父目录为目标，避免嵌套
scp -r packages/ashare-data root@tencent-vps:/root/
ssh root@tencent-vps "python3 -m pip install -e /root/ashare-data --break-system-packages"
```

> **每次在 `pyproject.toml` 中新增 CLI entry point（如 `ashare-em-collect`）后，
> 必须重新执行上述两条命令，否则新命令在 VPS 上不存在。**
> 验证：`ssh root@tencent-vps "ashare-em-collect --help"`

3. Expose `opencode` to system PATH.

`opencode` 安装在 nvm 环境下，cron 和非交互式 SSH 会话不 source `~/.nvm/nvm.sh`，
导致 `deep_research` 和 `sentiment` 步骤报 `No such file or directory: 'opencode'`。
必须创建软链接使其对所有进程可见：

```bash
# 查找实际路径
ssh root@tencent-vps "ls ~/.nvm/versions/node/*/bin/opencode"

# 创建软链接（路径按上一步输出填写）
ssh root@tencent-vps "ln -sf /root/.nvm/versions/node/v22.22.0/bin/opencode /usr/local/bin/opencode"

# 验证（不 source nvm 也能找到）
ssh root@tencent-vps "which opencode"
```

> **升级 Node 版本后，软链接指向的旧路径会失效，需重新执行上述命令。**

4. Restart gateway.

```bash
ssh root@tencent-vps "source ~/.nvm/nvm.sh && openclaw gateway restart"
```

4. Configure cron on VPS.

```cron
*/30 * * * * /usr/local/bin/ashare-collect --date $(date +\%Y-\%m-\%d) >> /root/.ashare-assistant/logs/collect.log 2>&1
0 16 * * * /usr/local/bin/ashare-diagnose >> /root/.ashare-assistant/logs/diagnose.log 2>&1
*/10 9-15 * * 1-5 /usr/local/bin/ashare-wl-monitor >> /root/.ashare-assistant/logs/wl-monitor.log 2>&1
```

> `ashare-wl-monitor` 自动判断交易时段（9:30–15:00）和节假日（同花顺 `trade_status`），
> 非交易日即使 cron 触发也会直接退出，无需另行维护节假日日历。

## Update Flow

1. Update `packages/ashare-data` and reinstall on target host.
   - **新增 CLI entry point 时必须触发此步骤**，否则新命令在目标机器上找不到。
2. Run one manual `ashare-collect` to validate output files.
3. Copy updated `skills/ashare-assistant/` files.
4. Restart `openclaw` gateway.

## Guardrails

1. Edit only source files under `skills/ashare-assistant/`; do not edit deployed copies directly.
2. Use `cp`/`scp`; do not use `rsync`.
3. If data collection is unavailable, stop deployment verification and report missing dependency.
