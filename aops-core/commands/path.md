---
name: path
category: retrieval
description: Show narrative path reconstruction (what happened across sessions)
allowed-tools: Bash, RunShellCommand
permalink: commands/path
---

# /path - Narrative Path Reconstruction

**Purpose**: Display a human-friendly narrative timeline of recent work across sessions, solving the "Mechanical Narrative" problem.

## Workflow

Run the `show_path.py` script to generate the narrative timeline.

```bash
uv run python3 aops-core/scripts/show_path.py --hours 24
```

To see further back (e.g. 48 hours):

```bash
uv run python3 aops-core/scripts/show_path.py --hours 48
```

## Output Interpretation

The output solves the "Mechanical Narrative" problem by:

1. **Prioritizing Intent**: Showing hydrated intent or task titles instead of raw IDs.
2. **Grouping by Project**: Categorizing abandoned work and timeline threads.
3. **Narrative Sentences**: "Started working on: [Title]" instead of "CLAIM: ID".

Present the output directly to the user.
