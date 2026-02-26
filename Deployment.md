# 部署

> **禁止使用 rsync 部署**，只允许使用 `cp`（本机）或 `scp`（远端）。

## 0. 部署至当前项目

只有以下`skill`需要部署到当前项目：
- agents-roundtable
- explore-project

```bash
cp -r skills/<skill-name>/ .agents/skills/
cp -r skills/<skill-name>/ .claude/skills/
```

## 1. 部署至本机

只有以下`skill`需要部署到当前项目：
- ashare-assistant
- openclaw-github-tracker
- markdown-to-anything

```bash
cp -r skills/<skill-name>/ ~/clawd/skills/
openclaw gateway restart
```

## 2. 部署至远端 VPS（Tencent VPS）

Skill与Agent绑定关系：
- ashare-assistant: 绑定`smartrader`，工作目录为`workspace-smartrader` 
- openclaw-github-tracker: 绑定`researcher`，工作目录为`workspace-researcher` 
- markdown-to-anything: 同时部署至`smartrader`和`researcher`

```bash
# 整个 skill 目录
scp -r skills/<skill-name>/ root@tencent-vps:/root/.openclaw/<agent-workspace>/skills/

# 单个文件（如只更新脚本）
scp skills/<skill-name>/scripts/foo.py root@tencent-vps:/root/.openclaw/<agent-workspace>/skills/<skill-name>/scripts/

# 重启 Gateway
ssh root@tencent-vps "source ~/.nvm/nvm.sh && openclaw gateway restart"
```
