# File Header Spec

Purpose: Define file header conventions so AI agents understand any file
         by reading only the first 20 lines.
Audience: AI agents authoring or consuming skill files.
Sections: Principles | Python Files | Markdown Files | Writing Rules | Sync Rules

---

## Principles

### 1. 20-Line Rule

The first 20 lines of every file must answer:

- **What** does this file do? (Purpose)
- **What** goes in and comes out? (Input / Output)
- **What** public interface does it expose? (Public API / Sections)

If 20 lines are not enough, the header is too verbose or the file does too much.

### 2. English-First

Write all file headers in English. Chinese is allowed only where
unavoidable — trigger phrases, Chinese field names in data, etc.

### 3. Sync-or-Delete

A stale header is worse than no header. When you change code or content,
update the header. If you cannot update it accurately, delete the stale
parts. Never leave false information.

---

## Python Files

### Script (executable, under scripts/)

Full header — Purpose, Input, Output, Public API:

```python
#!/usr/bin/env python3
"""Portfolio risk checker.

Purpose: Scan positions against risk rules, flag violations.
Input:   positions.json via stdin or --file flag
Output:  JSON to stdout with fields: violations[], score (0-100)

Public API:
    check_risk(positions) -> dict  -- run all risk rules
    load_rules(path) -> list       -- load custom rule definitions
"""
from __future__ import annotations
```

A second example — a CLI data fetcher:

```python
#!/usr/bin/env python3
"""Taoguba hot post fetcher.

Purpose: Fetch top posts from Taoguba forum, extract titles and stats.
Input:   --count flag (default 20)
Output:  JSON to stdout with fields: posts[], fetched_at

Public API:
    fetch_hot(count) -> list[dict]  -- fetch top posts by popularity
"""
from __future__ import annotations
```

### Library module (imported, not executed directly)

No Input/Output — callers decide those. Keep Purpose and Public API:

```python
"""HTTP client with retry and caching.

Purpose: Provide a shared HTTP client for all fetchers.
         Handles retry, timeout, and disk caching.

Public API:
    get(url, timeout) -> Response  -- GET with auto-retry
    post(url, data) -> Response    -- POST with auto-retry
    clear_cache() -> None          -- purge disk cache
"""
from __future__ import annotations
```

A second example — a parser utility:

```python
"""HTML table extractor.

Purpose: Extract rows from HTML tables into list-of-dicts.

Public API:
    parse_table(html, table_id) -> list[dict]  -- extract one table
    parse_all_tables(html) -> list[list[dict]]  -- extract every table
"""
from __future__ import annotations
```

### Test file

Minimal — state what is tested and what is covered:

```python
"""Tests for risk_check module.

Covers: check_risk() edge cases, rule loading, score calculation.
"""
from __future__ import annotations
```

A second example:

```python
"""Tests for html_table_extractor.

Covers: parse_table() with missing columns, empty tables, nested tags.
"""
from __future__ import annotations
```

---

## Markdown Files

### SKILL.md (skill entry point)

YAML frontmatter is already required. Add a structured summary as the
first paragraph after the heading:

```markdown
---
name: github-researcher
description: >
  Analyze GitHub repos and track project updates.
  Use when user says "研究一下", "分析这个项目", or asks
  about a GitHub repository.
---
# GitHub Researcher

Purpose: Automate GitHub repo analysis and maintain a watchlist.
Input:   GitHub repo URL or search query from user
Output:  Project profile (markdown) saved to reports/
Sections: Prerequisite Check | Workflow | Output Formats | Constraints
```

A second example:

```markdown
---
name: markdown-to-anything
description: >
  Convert markdown to PDF, PNG, or other formats.
  Use when user says "转成PDF", "生成图片", or asks to
  export markdown content.
---
# Markdown To Anything

Purpose: Convert markdown files to PDF, PNG, or DOCX via HTML intermediate.
Input:   Markdown file path or text from user
Output:  Rendered file (PDF/PNG/DOCX) saved to output/
Sections: Prerequisite Check | Conversion Pipeline | CLI Params | Fonts
```

### Reference doc (under references/)

No frontmatter. Heading + summary paragraph immediately after:

```markdown
# Trading Plan Execution

Purpose: Guide the agent to generate a daily trading plan.
Input:   6 data files (candidates.json, positions.json, etc.)
Output:  trading-plan.md with buy/sell signals and position sizing
Sections: Required Inputs | Execution Flow | Output Format | Rules
```

A second example:

```markdown
# Chrome CDP Reference

Purpose: Document Chrome DevTools Protocol usage for screenshot capture.
Sections: Connection Setup | Screenshot API | Error Handling | Examples
```

### Project-level doc (guides/, docs/)

Longer documents — state audience and usage up front:

```markdown
# Skills Development Guide

Purpose: Searchable handbook of skill authoring patterns.
Audience: AI agents and developers building new skills.
Usage:   Look up a section by scenario; each section is self-contained.
Sections: Metadata | Content Structure | References | Scripts | Workflow
          | LLM Control | Output Format | Cross-Skill | Validation
```

A second example:

```markdown
# Deployment Guide

Purpose: Define deployment targets and commands for each skill.
Audience: AI agents executing deployment tasks.
Usage:   Read the skill-specific section before running any deploy command.
Sections: General Rules | ashare-assistant | unified-memory | VPS Access
```

---

## Writing Rules

### Be specific, start with a verb

Every Purpose line starts with an action verb: Parse, Scan, Generate,
Convert, Fetch, Guide, Define, Automate.

```
GOOD:  Purpose: Parse Taoguba forum HTML into structured post lists.
BAD:   Purpose: This module handles various data processing tasks
       related to forum content.
```

### Name concrete formats and fields

```
GOOD:  Output: JSON to stdout with fields: posts[], fetched_at
BAD:   Output: Returns some data in JSON format.
```

### Describe behavior, not the name

Public API comments explain what the function does, not restate its name.

```
GOOD:  fetch_hot(count) -> list[dict]  -- top posts sorted by popularity
BAD:   fetch_hot(count) -> list[dict]  -- fetches hot data from the platform
```

### Keep each field to one line

One line per field, 80 characters max. If a Purpose needs two lines,
indent the continuation:

```
Purpose: Scan positions against risk rules and flag violations
         that exceed the configured thresholds.
```

---

## Sync Rules

### When to update the header

| Change made                          | Header field to sync |
|--------------------------------------|----------------------|
| Add / remove / rename public function | Public API          |
| Change function signature             | Public API          |
| Change input source or output target  | Input / Output      |
| Change file responsibility            | Purpose             |
| Add / remove / reorder sections (md)  | Sections            |

### When in doubt, delete

If you cannot write an accurate header after a change, remove the stale
field entirely. An incomplete header is acceptable; a false one is not.

```python
# Acceptable: stale API listing removed, rest stays accurate
"""Portfolio risk checker.

Purpose: Scan positions against risk rules, flag violations.
Input:   positions.json via stdin or --file flag
Output:  JSON to stdout with fields: violations[], score (0-100)
"""
```
