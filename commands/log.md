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

## Usage

**User provides**: Brief description of observation

**Example**: `/log Agent bypassed python-dev skill for Python edits`

The skill will search for existing Issues, create/update as appropriate.

## Heuristic Updates

For heuristic evidence updates, use automated session reflection instead:

```
Skill(skill="session-insights", args="current")
```

This runs automatically at session end. It mines the session for patterns, maps them to heuristics, and presents approve/dismiss options. Much less friction than manual `/log adjust-heuristic` calls.
