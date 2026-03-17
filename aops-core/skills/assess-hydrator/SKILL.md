---
name: assess-hydrator
type: skill
category: analysis
description: Assess hydrator quality using real session data
triggers:
  - "assess hydrator"
  - "hydrator quality"
  - "evaluate hydration"
modifies_files: true
needs_task: false
mode: execution
domain:
  - quality-assurance
allowed-tools: Bash,Read,Write,Glob,Grep
version: 1.0.0
tags:
  - v0.3
  - hydrator
  - quality-assurance
---

# Assess Hydrator Quality

Evaluate how well the prompt-hydrator is performing by examining real interactions from recent sessions.

## Tools

### Extract Agent Interactions

```bash
cd "$AOPS"
PYTHONPATH=aops-core uv run python \
  aops-core/skills/assess-hydrator/scripts/extract_agent_interactions.py \
  --recent 10 --agent-type prompt-hydrator --pretty
```

This outputs JSON with one record per hydrator invocation:

- `user_prompt` trigger that started the session
- `delegation_prompt` sent to the hydrator (usually a context file path)
- `agent_output` — the hydrator's full response including `<hydration_result>`
- `context_file_path` — the assembled context file (use `--include-context` to inline its contents)

The tool works for any agent type — use `--agent-type custodiet` or omit the filter to see all subagent interactions.

### Options

```bash
# Specific Claude session
--hooks-log PATH

# Specific Gemini session
--gemini-session PATH

# Recent sessions (both clients)
--recent N --client all

# Include context file contents in output
--include-context
```

## What to Look For

When reviewing hydrator output, consider:

- **Intent accuracy** — did the hydrator understand what the user actually wanted?
- **Workflow selection** — were the right workflows identified for the task?
- **Context relevance** — was the curated context useful, or bloated with irrelevant sections?
- **Plan quality** — are execution plan steps actionable, correctly ordered, and specific enough?
- **Anti-patterns** — delegating file reads to downstream agent, hallucinated file paths, generic filler steps, or copy-pasting workflow file contents verbatim

## Evidence

Write assessment findings to `$ACA_DATA/hydrator-assessments/` with date-stamped filenames. These accumulate over time to build a body of evidence about hydrator quality trends. Mutable state must live in `$ACA_DATA`, not in the framework repo.
