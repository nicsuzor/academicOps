---
name: reminders
category: reference
title: Skill Triggers & Operational Reminders
type: reference
description: Static knowledge for skill invocation and operational guidance. Companion to AXIOMS (principles) and HEURISTICS (patterns).
permalink: reminders
tags: [framework, skills, routing]
---

## Skill Invocation Triggers

When you see these domain signals, invoke the corresponding skill BEFORE starting work.

| Domain Signal                                                             | Skill                         | When to Invoke                         |
| ------------------------------------------------------------------------- | ----------------------------- | -------------------------------------- |
| Python code, pytest, type hints, mypy                                     | `python-dev`                  | Any Python coding work                 |
| Framework files (skills/, hooks/, agents/, commands/, AXIOMS, HEURISTICS) | `framework`                   | Changes to framework infrastructure    |
| Debug test failures, find session logs, investigate framework issues      | `framework`                   | Debugging (see workflow 02)            |
| New functionality, "add", "create", feature requests                      | `feature-dev`                 | Building new features with TDD         |
| Claude Code hooks, PreToolUse, PostToolUse, hook events                   | `plugin-dev:hook-development` | Hook development                       |
| MCP servers, .mcp.json, tool integration                                  | `plugin-dev:mcp-integration`  | MCP server integration                 |
| "Remember", persist knowledge, save to memory                             | `remember`                    | Knowledge persistence to memory server |
| dbt, Streamlit, data analysis, statistics                                 | `analyst`                     | Research data work                     |
| Mermaid diagrams, flowcharts                                              | `flowchart`                   | Creating Mermaid flowcharts            |
| Excalidraw, visual diagrams, mind maps                                    | `excalidraw`                  | Hand-drawn style diagrams              |
| Review academic work, papers, dissertations                               | `review`                      | Academic review assistance             |
| Convert documents to markdown                                             | `convert-to-md`               | Document conversion (DOCX, PDF, etc.)  |
| Generate PDF from markdown                                                | `pdf`                         | PDF generation with academic styling   |
| Session insights, accomplishments, daily note, daily summary              | `session-insights`            | Extract learnings from sessions        |
| Daily briefing, morning routine, task recommendations, email triage       | `daily`                       | Daily note lifecycle management        |
| Fact-check claims, verify sources                                         | `fact-check`                  | Verify factual claims                  |

## Operational Reminders

### Plan-Mode Triggers

Invoke `EnterPlanMode()` before:

- Modifying skills/, hooks/, agents/, commands/
- Changes to AXIOMS.md, HEURISTICS.md, FRAMEWORK-PATHS.md
- Multi-file refactors or architectural changes
- Any change requiring user approval

### Skill-First Workflow (See [[HEURISTICS.md#H2]])

1. Identify domain from task description
2. Match domain to skill trigger above
3. Invoke skill BEFORE starting implementation
4. Follow skill guidance

### Knowledge Persistence

After learning something worth preserving:

```python
Skill(skill="remember")
```

### Commit Checkpoints (See [[AXIOMS.md#A15]])

After completing logical work units:

- Commit changes
- Push to remote
- Don't batch up commits

### TodoWrite for Multi-Step Work

For any work with 3+ steps:

1. Create TodoWrite with all steps
2. Mark steps in_progress as you work
3. Mark completed immediately when done

### Verification Before Assertion (See [[HEURISTICS.md#H3]])

Before claiming success:

- Run the verification command
- Quote evidence in your response
- Don't claim success based on "should work"

### Session End Requirements

**Before ending any session**, complete these steps:

1. **Commit all work**: `git add <files> && git commit -m "..."` + push
2. **Output Framework Reflection**: Structured summary for session-insights parsing

See [[aops-core/commands/dump.md]] for the exact Framework Reflection format (search "## Framework Reflection").

Stop hooks will remind you if you forget, but it's better to do this proactively.

## What This File Is NOT

- **Not principles**: Those are in [[AXIOMS.md]]
- **Not patterns**: Those are in [[HEURISTICS.md]]
- **Not procedures**: Those are in [[WORKFLOWS.md]]

This file is a quick-reference for skill routing and operational habits.
