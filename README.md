# OpenclawSkills

<p align="center">
  <strong>Openclaw Agent Skills Repository</strong><br>
  A collection of specialized AI agent skills for various automation and research tasks.
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a>
</p>

---

## Overview

This repository contains a suite of **Agent Skills** developed for the Openclaw platform. Each skill is a self-contained module that enables AI agents to perform specialized tasks.

All skills follow the [Agent Skills specification](https://github.com/agentskills/agentskills) and leverage Openclaw's built-in tools for browser automation, code execution, and data processing.

## Repository Layout

```
skills/                            # Agent Skills (each is autonomous)
├── agent-roundtable/              # Multi-agent collaboration framework
├── bb-browser/                    # Browser automation utilities
├── code-insight/                  # Code analysis and insights
├── explore-project/               # Project exploration tools
├── github-researcher/             # GitHub trending research
├── markdown-to-anything/          # Markdown conversion utilities
├── openclaw-browser/              # Openclaw browser integration
├── openclaw-github-tracker/       # GitHub project intelligence
├── skill-review/                  # Skill review and audit
├── unified-memory/                # Unified memory management
└── website-operator/              # Website operation utilities
```

Each skill in `skills/` is independent and autonomous.

---

## Available Skills

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

### 🌐 Other Skills

| Skill | Purpose |
|-------|---------|
| `bb-browser` | Browser automation utilities |
| `code-insight` | Code analysis and insights |
| `explore-project` | Project exploration tools |
| `markdown-to-anything` | Markdown conversion utilities |
| `openclaw-browser` | Openclaw browser integration |
| `skill-review` | Skill review and audit |
| `unified-memory` | Unified memory management |
| `website-operator` | Website operation utilities |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Openclaw platform or compatible agent runtime

### Project Installer

Use the project-level installer to install only the skills you need:

```bash
./install.sh --list
./install.sh --skill agent-roundtable,unified-memory
./install.sh --all-skills --project-skills
```

Skill install targets:

- `--project-skills`: install to `./.agents/skills/` (default)
- `--global-skills`: install to `~/.agents/skills/`

### Using a Skill

Each skill includes a `SKILL.md` with detailed documentation:

```bash
cat skills/<skill-name>/SKILL.md
```

### Running Tests

```bash
# Run tests for a specific skill
python -m unittest discover -s skills/<skill-name>/tests -p "test_*.py"

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

---

## Related Projects

- **ashare-platform**: A-share data collection and platform services (migrated to `~/Projects/ashare-data`)

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

**Note**: Always modify source in `skills/` directory only. Deployment directories are read-only copies.

---

## References

- [Agent Skills Specification](https://github.com/agentskills/agentskills)
- [Openclaw Tools Documentation](https://docs.openclaw.ai/tools/browser)
- [Skills Development Guide](Skills-Dev-Guide.md)

---

<p align="center">
  Built for the Openclaw platform
</p>
