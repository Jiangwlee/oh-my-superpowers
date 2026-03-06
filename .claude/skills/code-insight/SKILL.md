---
name: code-insight
description: >-
  Produces a comprehensive implementation investigation report for a third-party
  or open-source codebase. Use when (1) user asks to analyze or investigate an
  external or open-source project, (2) target is under a github/ or vendor/
  directory, (3) user says "研究这个开源项目", "分析这个库", "deep dive into this repo".
  Do NOT trigger for the user's own development project.
---

# Code Insight

## Prerequisite Check

Verify the target codebase path before proceeding.

If the target path is NOT under a `github/`, `vendor/`, or equivalent third-party directory:
> Confirm: is this an external or open-source codebase — not your own development project?
> If the answer is no or uncertain: stop immediately. Do not proceed.

If the target path is not provided at all, ask:
> Which codebase should I investigate? Please provide the root directory path.

## Overview

Write a comprehensive implementation investigation report for every production code file. Document what engineers need to understand: Architecture, Features, Data Schemas, Data Flows, Interfaces, etc.

Write for a skilled developer who has zero context about this codebase and no prior exposure to its design decisions or conventions.

**Announce at start:** "I'm using the code-insight skill to create the implementation investigation report." Then create `code-insight` directory as root of the investigation reports.

**Save results to:** `code-insight/`

## Workflow

1. Go through the code base, identify the code base structure and core modules
2. Create `code-insight/` structure. It should be identical to the code base structure. For example:
```
# Code Repo Structure
repo_root:
    - src
        - code_file_a.py
        - code_file_b.py

# Corresponding code-insight structure
code-insight:
    - Architecture.md
    - src
        - code_file_a.md  # code file a's code investigation report
        - code_file_b.md  # code file b's investigation report
```
3. Identify the module dependencies. Make an investigation plan. Start from down (infrastructure layer) to top (application layer).
4. Follow the plan, investigate modules one by one. Create investigate report for every code file.
5. Create `Architecture.md` as the final task.

## Investigation Report Structure

```markdown
# [File Name] Investigation Report

**Overview:** [One sentence describing what this code file does]

**Architecture:** [2-3 sentences about approach]

**Core function:** [Investigate the most critical 50 code lines deeply]

---
```

## Done Criteria

Investigation is complete when:
- One `.md` report exists for every production code file in the codebase.
- `code-insight/Architecture.md` has been created.
- No production code file is left undocumented.

## Failure Handling

- If a file cannot be read: note it as unreadable in the report, continue with remaining files.
- If the codebase exceeds 50 files: ask the user whether to investigate the full codebase
  or a specific subset before proceeding.

## Guardrails

NO investigation report for test files. No exceptions. Only investigate production code files.
NO report written in any language other than Simplified Chinese. No exceptions.

- Use exact file paths in every report.
- Do not repeat explanations across reports. If module A's report explains a concept,
  subsequent reports reference it rather than re-explain.

## Execution Mode

**REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development

