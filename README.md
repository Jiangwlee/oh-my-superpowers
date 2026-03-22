# OpenclawSkills

<p align="center">
  <strong>Openclaw Agent Skills Repository</strong><br>
  A collection of specialized AI agent skills for financial data collection, analysis, and research.
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a>
</p>

---

## Overview

This repository contains a suite of **Agent Skills** developed for the Openclaw platform. Each skill is a self-contained module that enables AI agents to perform specialized tasks, from financial market analysis to multi-agent collaboration.

All skills follow the [Agent Skills specification](https://github.com/agentskills/agentskills) and leverage Openclaw's built-in tools for browser automation, code execution, and data processing.

## Repository Layout

```
packages/                          # Shared infrastructure packages
└── ashare-data/                   # A-share data collection library (pip install -e)

skills/                            # Agent Skills (each is autonomous)
├── ashare-assistant/              # A-share trading assistant
├── agent-roundtable/              # Multi-agent collaboration framework
├── github-researcher/             # GitHub trending research
├── markdown-to-anything/          # Markdown conversion utilities
└── openclaw-github-tracker/       # GitHub project intelligence

deployment/                        # Deployment documentation and Docker configs
├── README.md                     # ashare-platform deployment entry
└── docker/
    └── ashare-platform/
        └── docker-compose.yml
```

`packages/` contains standalone Python packages used as infrastructure by skills. `skills/` contains the agent skills themselves—each skill is independent and autonomous. `deployment/` now contains the deployment entrypoint and Docker configuration for `ashare-platform`.

---

## Available Skills

### 📈 A-Share Assistant (`ashare-assistant`)

**Purpose**: Daily A-share market review and next-day trading plan generation.

**Dependency (Required)**:
- `ashare-assistant` depends on `packages/ashare-data` at runtime.
- `ashare-data` provides the `ashare-collect` CLI and writes data into `~/.ashare-assistant/data/{DATE}/`.
- `ashare-assistant` reads that shared data directory and does not replace data collection.

**Key Features**:
- Automated data collection via `ashare-data` package (news, funding flows, sentiment, trend scanning, broker account)
- 5-stage LLM pipeline: sentiment → review → candidates → deep research → trading plan
- Risk checking and decision logging
- Strategy evolution tracking

**Trigger Keywords**: 复盘, 今日回顾, 明日计划, 选股, 大盘分析, 板块, 涨停

**Architecture**:
- `packages/ashare-data/` — data collection infrastructure (runs as a cron job)
- `skills/ashare-assistant/` — LLM workflow (market review, stock picking, trading plan)

Data flows from `ashare-data → ~/.ashare-assistant/data/{DATE}/filtered/ → ashare-assistant`.

Deployment order: install/deploy `ashare-data` first, then deploy `ashare-assistant`.

---

### 🔄 Agent Roundtable (`agent-roundtable`)

**Purpose**: Multi-agent collaborative discussion framework.

**Key Features**:
- Coordinate external agents (codex, opencode, etc.) around shared topics
- Durable session logs with JSONL format
- Background injection for context-rich discussions
- Automatic orchestration with convergence detection

**Trigger Keywords**: "roundtable", "agent roundtable", "multi-agent discussion"

---

### 🔍 GitHub Researcher (`github-researcher`)

**Purpose**: GitHub trending analysis and repository deep research.

**Key Features**:
- Daily GitHub Trending collection via browser automation
- User-approved watchlist management
- Multi-engine deep analysis (claude → codex → Openclaw)
- Repository update tracking over time
- Local code caching for offline analysis

---

### 📊 OpenClaw GitHub Tracker (`openclaw-github-tracker`)

**Purpose**: GitHub project intelligence workflow for OpenClaw.

**Key Features**:
- Daily trending discovery from GitHub Trending page
- Watchlist management with user-driven additions
- First-time deep project dossier generation
- Meaningful update tracking across followed repositories
- Machine-friendly index for memory systems

---

## Quick Start

### Prerequisites

- Python 3.10+
- Openclaw platform or compatible agent runtime

### Project Installer

Use the project-level installer to install only the packages, apps, or skills you need:

```bash
./install.sh --list
./install.sh --package ashare-data --app ashare-platform
./install.sh --skill ashare-assistant,unified-memory
./install.sh --all-skills --project-skills
```

Skill install targets:

- `--project-skills`: install to `./.agents/skills/` (default)
- `--global-skills`: install to `~/.agents/skills/`

### Install shared packages

```bash
pip install -e packages/ashare-data
```

### Using a Skill

Each skill includes a `SKILL.md` with detailed documentation:

```bash
cat skills/<skill-name>/SKILL.md
```

### Running Tests

```bash
# All tests
python -m unittest discover -s skills/ashare-assistant/tests -p "test_*.py"

# Syntax check
python -m py_compile <file.py>
```

---

## Development

### Technology Stack

- **Language**: Python 3.10+ (standard library preferred)
- **Testing**: unittest / pytest
- **HTML Parsing**: html.parser (regex forbidden)

### Code Style

- Import ordering: stdlib → third-party → local modules
- Type annotations: Use `str | None` instead of `Optional[str]`
- Naming: snake_case for modules/functions, PascalCase for classes
- Docstrings: Google style
- Error handling: Return empty collections on failure, never raise

### Adding a New Skill

1. Create a new directory under `skills/<skill-name>/`
2. Follow the structure: `scripts/`, `tests/`, `references/`, `SKILL.md`
3. Write comprehensive tests
4. Update this README

### Adding a New Package

1. Create a new directory under `packages/<package-name>/`
2. Add `pyproject.toml` with `[project.scripts]` if CLI is needed
3. Install with `pip install -e packages/<package-name>`

---

## GitHub Research

When developing new skills, avoid reinventing the wheel. Research existing solutions:

```bash
gh search repos <topic> --sort stars
```

Research findings are stored in `github_cache/` with an `INDEX.md` for quick reference.

---

## Deployment

See [Deployment.md](Deployment.md) for full instructions.

```bash
# Deploy a skill locally
cp -r skills/<skill-name>/ .claude/skills/<skill-name>/

# Deploy to remote server
scp -r skills/<skill-name>/ root@tencent-vps:/path/to/skills/
```

**Note**: Always modify source in `skills/` or `packages/` directories only. Deployment directories are read-only copies.

---

## References

- [Agent Skills Specification](https://github.com/agentskills/agentskills)
- [Openclaw Tools Documentation](https://docs.openclaw.ai/tools/browser)
- [Skills Development Guide](Skills-Dev-Guide.md)
- [ashare-data Package](packages/ashare-data/README.md)

---

<p align="center">
  Built for the Openclaw platform
</p>
