# oh-my-superpowers

<p align="center">
  <strong>Pi Agent + Skills Development Kit</strong><br>
  A framework for building, reviewing, and deploying Agent Skills for Pi and Claude Code.
</p>

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh.md">简体中文</a>
</p>

---

## Overview

oh-my-superpowers is a development framework focused on two things:

1. **Skills** — Self-contained tool wrappers that give agents real capabilities
2. **Agents** — Role-based task executors driven by Skills

It provides the meta-skills, specs, and CLI tooling needed to design, build, review, and install Skills and Agents for Pi and Claude Code.

## Repository Layout

```
skills/                       # Skill units (each independent)
├── agent-brainstorming/      # Workflow for designing new Agents
├── skill-brainstorming/      # Workflow for designing new Skills
├── skill-review/             # Skill quality audit tool
└── markdown-to-anything/     # Convert Markdown to PDF/PNG

agents/                       # Pi Agent definitions
└── <name>.md                 # Pi frontmatter + system prompt

bin/
└── omp                       # oh-my-superpowers CLI

docs/
├── specs/                    # Development specs (stable, long-lived)
│   ├── 00_skills/            # Skills spec, best practices, patterns
│   ├── 01_agents/            # Pi Agent framework reference
│   └── 02_framework/         # Architecture, installation design
└── design/                   # Design docs output from brainstorming
```

## Quick Start

### Install

```bash
# Bootstrap: symlinks project to ~/.oh-my-superpowers and registers omp
./install.sh
```

### Install a Skill

```bash
# Local install (current project)
omp install skill skill-review
omp install skill agent-brainstorming

# Global install (available in all projects)
omp install skill skill-review --global
```

### List Installed Skills

```bash
omp list           # local
omp list --global  # global
```

### Design a New Skill or Agent

```bash
# In Claude Code or Pi — triggers the brainstorming workflow
# "I need to design a new skill"   → skill-brainstorming activates
# "I need to design a new agent"   → agent-brainstorming activates
```

## Available Skills

| Skill | Pattern | Purpose |
|-------|---------|---------|
| `agent-brainstorming` | Inversion + Pipeline | Design workflow for new Agents (identity audit gate) |
| `skill-brainstorming` | Inversion + Pipeline | Design workflow for new Skills (pattern selection gate) |
| `skill-review` | Reviewer + Pipeline | Quality audit for Skill directories |
| `markdown-to-anything` | Pipeline | Convert Markdown to PDF, PNG, and other formats |

## omp CLI

```
omp install skill <name> [--global]   Install a skill
omp install agent <name> [--global]   Install an agent
omp remove  skill <name> [--global]   Remove a skill installation
omp remove  agent <name> [--global]   Remove an agent installation
omp list [--global]                   List installed skills and agents
omp test skill <name>                 Run T1 tests for a skill
omp help                              Show help
```

Skills install as symlinks to both `.agents/skills/` (Pi) and `.claude/skills/` (Claude Code).

## Architecture

Four layers, clear separation of concerns:

```
Tools/Scripts   CLI-ified executables (bash/python/node)
    ↑
Skills          SKILL.md + references/ — tells agent WHEN and WHAT
    ↑
Agents          Pi frontmatter + system prompt — role-based orchestration
    ↑
CLI             omp — install, remove, test
```

**Agent Identity Rule**: An Agent must map to a clear role (a job title). If you can't answer "who are you?" with a professional description, it's a Skill, not an Agent.

See [docs/specs/02_framework/architecture.md](docs/specs/02_framework/architecture.md) for full details.

## Development

Read before designing anything:
- Skills: [docs/specs/00_skills/README.md](docs/specs/00_skills/README.md)
- Agents: [docs/specs/01_agents/README.md](docs/specs/01_agents/README.md)
- Framework: [docs/specs/02_framework/README.md](docs/specs/02_framework/README.md)

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Scripts | Bash / Python 3.10+ / Node.js or Bun |
| Testing | unittest/pytest (T1) · `pi -p` / `claude -p` (T2 E2E) · LLM-as-judge (T3) |
| Package mgmt | uv (Python) · npm or bun (Node) |
| Agent runtime | Pi (core) · Claude Code (development) |
| Install | symlinks via omp |
