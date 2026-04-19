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
├── brainstorming/            # Scenario router: S1 open / S2 skill-agent / S3 feature
├── coding-orchestrator/      # Spec-driven sub-agent orchestration for S3 handoffs
├── llm-wiki/                 # Karpathy-style markdown wiki SOP + omp wiki scripts
├── skill-review/             # Skill quality audit tool
└── markdown-to-anything/     # Convert Markdown to PDF/PNG

agents/                       # Pi Agent definitions
└── skill-review.md           # Skill Quality Auditor

bin/
└── omp                       # oh-my-superpowers CLI

docs/
├── specs/                    # Development specs (stable, long-lived)
│   ├── 00_skills/            # Skills spec, best practices, patterns
│   ├── 01_agents/            # Pi Agent framework reference
│   └── 02_framework/         # Architecture, installation design
└── brainstorming/            # S3 design docs (specs/) + S1 discussions
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
# "I need to design a new skill"   → routes to S2 (skill-agent scenario)
# "I need to design a new agent"   → routes to S2 (skill-agent scenario)
# "Add feature X" / "Refactor Y"   → routes to S3 (hands off to coding-orchestrator)
# "Let's discuss / explore ..."    → routes to S1 (open discussion)
```

## Available Skills

| Skill | Pattern | Purpose |
|-------|---------|---------|
| `brainstorming` | Router + Pipeline | Scenario router (S1 open / S2 skill-agent / S3 feature); S3 outputs a story skeleton for `coding-orchestrator` |
| `coding-orchestrator` | Orchestrator + Sub-agent | Spec-driven sub-agent orchestration; consumes S3 handoff, runs JIT wave-by-wave task execution |
| `llm-wiki` | Pipeline + Tool Wrapper | Karpathy-style markdown wiki workflow on top of `omp wiki` |
| `skill-review` | Reviewer + Pipeline | Quality audit for Skill directories |
| `markdown-to-anything` | Pipeline | Convert Markdown to PDF, PNG, and other formats |

## Available Agents

| Agent | Role | Purpose |
|-------|------|---------|
| `skill-review` | Skill Quality Auditor | Full audit of a Skill directory: spec compliance, design quality, evidence quality |

## omp CLI

```
omp run   agent <name> --model <m> <prompt>   Run a Pi Agent (streaming)
omp list  [--global]                          List skills and available agents
omp install skill <name> [--global]           Install a skill (local or global)
omp remove  skill <name> [--global]           Remove a skill installation
omp test skill <name>                         Run T1 tests for a skill
omp help                                      Show help
```

Skills install as symlinks to both `.agents/skills/` (Pi) and `.claude/skills/` (Claude Code).
Agents run directly from source — no install step needed.

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
