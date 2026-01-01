---
name: log
description: Log agent performance patterns to GitHub Issues (per AXIOMS #28)
allowed-tools: Skill
permalink: commands/log
---

**IMMEDIATELY** invoke the `[[skills/learning-log/SKILL.md|learning-log]]` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging observations to GitHub Issues, where patterns can accumulate and later synthesize to HEURISTICS.md.

## Workflow (GitHub Issues)

Per [[AXIOMS]] #28 and [[HEURISTICS]] H26: episodic content → GitHub Issues.

1. **Search** for existing Issue matching the observation
2. **Update** existing Issue with comment, OR **create** new Issue
3. **Synthesize** to HEURISTICS.md when patterns emerge across Issues

## Issue Labels

| Label | Use For |
|-------|---------|
| `bug` | Component-level bugs |
| `learning` | Agent behavior patterns |
| `experiment` | Systemic investigations |
| `devlog` | Development observations |

## Future Direction

`/log` may become more concise: simply log a failure + evidence to GitHub Issues. Use `/reflect` for deeper process analysis and workflow compliance checking.

## Modes

### Standard Mode (default)
Log observation to GitHub Issue.

**User provides**: Brief description of observation

### Heuristic Adjustment Mode
Adjust heuristic confidence based on new evidence.

**User provides**: `adjust-heuristic H[n]: [observation]`

**Example**: `/log adjust-heuristic H3: Agent claimed success without running tests - confirms H3`
