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

It also includes **`omp serve`**, a project-local web workbench for Skill development: browse the current repository, preview or edit Markdown/HTML files, and talk to a Pi Agent from the same UI.

## Repository Layout

```
skills/                       # Skill units (each independent)
├── brainstorming/            # Scenario router: S1 open / S2 skill-agent / S3 feature
├── skill-review/             # Skill quality audit
├── agent-review/             # Pi Agent markdown audit
├── code-review/              # Local uncommitted/unpushed code review
├── debug/                    # Systematic debugging for reproducible bugs
├── handoff/                  # Pre-/compact context handoff helper
├── insight/                  # Project memory: recall / capture / evaluate / list
├── evolution/                # Evolve project skills + CLAUDE.md from usage data
├── deep-research/            # Multi-round, multi-source research workflow
├── omp-agents/               # Delegate work to a registered Pi Agent via omp run
├── team/                     # Stateless one-shot tmux dispatch (claude/codex/pi)
├── round-table/              # Multi-runtime persona-driven roundtable debate
├── web-operator/             # Chrome CDP browsing, search, content extraction
├── media-editor/             # Archive / query / promote items for media-editor agent
├── llm-wiki/                 # Karpathy-style markdown wiki on top of omp wiki
├── markdown-to-anything/     # Convert Markdown to PDF/PNG
└── docs-contract/            # Documentation skeleton + maintenance contract for MVP projects

agents/                       # Pi Agent definitions (+ agents.json registry)
├── reviewer.md               # Universal Quality Reviewer (auto-routes review path)
├── researcher.md             # General Researcher (multi-round investigation)
├── oss-researcher.md         # OSS Research Analyst (open-source code deep dives)
├── media-editor.md           # AI Media Editor (X.com / Reddit AI digests)
├── ux-engineer.md            # UX Engineer (frontend audit + design)
└── wps-assistant.md          # WPS Document Assistant

cli/                          # typer CLI modules (one per tool, routed via omp <tool>)
└── <tool>/main.py

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
# "Add feature X" / "Refactor Y"   → routes to S3 (produces a design doc and implementation plan)
# "Let's discuss / explore ..."    → routes to S1 (open discussion)
```

### Open the Skill Workbench

```bash
# Start the local web workbench for the current project
omp serve start --workspace . --no-open

# Restart or stop it
omp serve restart --workspace . --no-open
omp serve stop
```

Open `http://localhost:8765/` or the machine's LAN/Tailscale address. Each browser page creates a fresh Pi session; multiple prompts in the same page continue that page-local conversation.

## Available Skills

| Skill | Pattern | Purpose |
|-------|---------|---------|
| `brainstorming` | Router + Pipeline | Scenario router (S1 open / S2 skill-agent / S3 feature); S3 produces the design doc and implementation plan for feature work |
| `skill-review` | Reviewer + Pipeline | Quality audit for Skill directories |
| `agent-review` | Reviewer | Spec/design audit for a Pi Agent markdown file |
| `code-review` | Reviewer | Review uncommitted or unpushed local code changes |
| `debug` | Pipeline | Systematic root-cause debugging for reproducible failures |
| `handoff` | Pipeline | Generate `.handover.md` + `/compact` instruction before compaction |
| `insight` | Pipeline | Project memory: recall / capture / evaluate / list |
| `evolution` | Pipeline | Evolve skills and CLAUDE.md from cross-project usage data |
| `deep-research` | Pipeline | Multi-round, multi-source research with validation |
| `omp-agents` | Router | Delegate matching tasks to a registered Pi Agent via `omp run` |
| `team` | Tool Wrapper | Stateless one-shot tmux dispatch to claude/codex/pi |
| `round-table` | Tool Wrapper | Multi-runtime persona-driven roundtable debate |
| `web-operator` | Tool Wrapper | Chrome CDP browser automation, search, content extraction |
| `media-editor` | Pipeline | Archive / query / promote helpers for the media-editor agent |
| `llm-wiki` | Pipeline + Tool Wrapper | Karpathy-style markdown wiki workflow on top of `omp wiki` |
| `markdown-to-anything` | Pipeline | Convert Markdown to PDF, PNG, and other formats |
| `docs-contract` | Inversion + Generator + Reviewer | Build a documentation skeleton with maintenance contracts and 3-layer lint for MVP-stage projects |

## Available Agents

Defined in `agents/` and registered in `agents/agents.json` (binds default model + skill set).

| Agent | Role | Purpose |
|-------|------|---------|
| `reviewer` | Universal Quality Reviewer | Auto-routes to skill-review / agent-review / code-review based on the target file |
| `researcher` | General Researcher | Multi-round cross-source investigation, fact synthesis, opinion review |
| `oss-researcher` | OSS Research Analyst | Answers open-source implementation questions, builds layered Obsidian KB |
| `media-editor` | AI Media Editor | Discovers AI content on X.com / Reddit, archives and produces digests |
| `ux-engineer` | UX Engineer | Frontend UI audit and design (powered by impeccable skill set) |
| `wps-assistant` | WPS Document Assistant | Locates and answers questions about documents in WPS / 金山文档 |

## omp CLI

```
omp install <skill|agent> <name> [--global]   Install a skill or agent (symlink)
omp remove  <skill|agent> <name> [--global]   Remove an installation
omp list    [skill|agent] [--global]          List installed skills and agents
omp run     <agent> [--model M] [--mode …] <prompt>
                                              Run a Pi Agent (text/stream/json/interactive)
omp test    skill <name>                      Run T1 static tests for a skill
omp upgrade                                   Pull latest version and re-register commands
```

Tool subcommands (each routes to `cli/<tool>/main.py`; run `omp <tool> --help`):

```
omp deep-research         Initialize and build deep-research workspaces
omp evolution             Scan sessions and view evolution history
omp handoff               Context handoff helpers for compaction lifecycle
omp insight               Extract memories from AI conversations and distill insights
omp media-editor          Archive, query, and promote media items
omp round-table           Multi-AI round table discussions
omp serve                 Project-local Skill workbench with file tree, Markdown/HTML preview, editor, and Pi chat
omp skill-review          Mechanical consistency checks on a skill directory
omp dispatch              Tmux dispatch primitive (claude/codex/pi spawn/wait/tail)
omp web-operator          Browser automation, search, and content extraction
omp wiki                  Karpathy-style markdown wiki management
omp docs-contract         Build a documentation skeleton with maintenance contracts (scaffold/lint/inventory)
```

Skills install as symlinks to both `.agents/skills/` (Pi) and `.claude/skills/` (Claude Code).
Agents install via `omp install agent <name>` (also symlink-based).

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
