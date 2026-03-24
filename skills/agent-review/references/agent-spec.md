# Pi Agent Spec

Purpose: Define the valid format for Pi agent markdown files.
Input:   Used by agent-review during frontmatter compliance checks.

---

## File Format

A Pi agent file is a single markdown file with YAML frontmatter followed by a system prompt.

```
---
name: agent-name
description: >-
  One-line description of what this agent does.
tools: read, bash
model: claude-sonnet-4-6
---

System prompt starts here...
```

---

## Frontmatter Fields

### `name` (required)

- Type: string
- Rules:
  - Must match the filename without `.md` extension (e.g., file `foo.md` → `name: foo`)
  - 1–64 characters
  - Lowercase letters, digits, hyphens only
  - No leading, trailing, or consecutive hyphens

### `description` (required)

- Type: string (use `>-` for multi-line)
- Rules:
  - Non-empty
  - Under 1024 characters
  - Should describe what the agent does and when to use it
  - Agents are explicitly invoked — description is for human readability, not auto-triggering

### `tools` (required)

- Type: comma-separated string
- Valid values (exhaustive list):

| Tool | Purpose |
|------|---------|
| `read` | Read file contents |
| `bash` | Execute shell commands |
| `edit` | Precise file edits |
| `write` | Create or overwrite files |
| `grep` | Search file contents |
| `find` | Find files by pattern |
| `ls` | List directory contents |
| `subagent` | Spawn a Pi subagent |

- Rules:
  - Only list tools the agent actually uses
  - Minimum necessary tools (principle of least privilege)
  - No tools outside this list are valid

### `model` (required)

- Type: string
- Recommended values:

| Model ID | Use case |
|----------|----------|
| `claude-sonnet-4-6` | Default — balanced quality and speed |
| `claude-opus-4-6` | Complex reasoning tasks |
| `claude-haiku-4-5-20251001` | Fast, lightweight tasks |

- Other provider/model strings (e.g., `litellm-local/qwen3.5-27b`) are valid but non-standard.

---

## System Prompt

Everything after the closing `---` frontmatter delimiter is the system prompt. No required format, but see `rubric.md` for quality standards.
