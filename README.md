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

## Available Skills

### 📈 A-Share Review Planner (`a-share-review-planner`)

**Purpose**: Daily A-share market review and next-day trading plan generation.

**Key Features**:
- Multi-source data collection (news, sector flows, sentiment, trend scanning)
- 5-stage structured analysis workflow
- Automated PDF report generation and Telegram delivery
- Risk checking and decision validation
- Strategy evolution tracking

**Trigger Keywords**: "复盘", "今日回顾", "明日计划", "选股", "大盘分析", "板块", "涨停"

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

## Quick Start

### Prerequisites

- Python 3.10+
- Openclaw platform or compatible agent runtime

### Directory Structure

```
skills/
├── a-share-review-planner/    # A-share market analysis
├── agent-roundtable/          # Multi-agent collaboration
├── github-researcher/         # GitHub research workflow
└── openclaw-github-tracker/   # GitHub project intelligence
```

### Using a Skill

Each skill includes a `SKILL.md` file with detailed documentation:

```bash
# Read skill documentation
cat skills/<skill-name>/SKILL.md

# Run skill tests
python -m unittest discover -s skills/<skill-name>/tests -p "test_*.py"
```

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

### Testing

```bash
# Run all tests
python -m unittest discover -s skills -p "test_*.py"

# Run specific skill tests
python -m unittest skills.a_share_review_planner.tests.test_taoguba_fetchers

# Syntax check
python -m py_compile <file.py>
```

### Adding a New Skill

1. Create a new directory under `skills/<skill-name>/`
2. Follow the structure: `scripts/`, `tests/`, `references/`, `SKILL.md`
3. Write comprehensive tests
4. Update this README

## GitHub Research

When developing new skills, avoid reinventing the wheel. Research existing solutions:

```bash
# Search for related projects
gh search repos <topic> --sort stars

# Cache projects for deep analysis
# (See github-researcher skill for workflow)
```

Research findings are stored in `github_cache/` with an `INDEX.md` for quick reference.

## Deployment

Skills are deployed to agent-specific directories:

```bash
# Local deployment
cp -r skills/<skill-name>/ .claude/skills/<skill-name>/
cp -r skills/<skill-name>/ .agents/skills/<skill-name>/

# Remote deployment
scp -r skills/<skill-name>/ user@host:/path/to/skills/
```

**Note**: Always modify source in `skills/` directory only. Deployment directories are read-only copies.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the coding conventions in `AGENTS.md`
4. Write tests for new functionality
5. Submit a pull request

## License

[Add your license information here]

## References

- [Agent Skills Specification](https://github.com/agentskills/agentskills)
- [Openclaw Tools Documentation](https://docs.openclaw.ai/tools/browser)
- [Skills Development Guide](Skills-Dev-Guide.md)

---

<p align="center">
  Built for the Openclaw platform
</p>
