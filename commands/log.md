---
name: log
description: Log agent performance (successes and failures) to framework learning system
allowed-tools: Skill
permalink: commands/log
---

**IMMEDIATELY** invoke the `[[skills/learning-log/SKILL.md|learning-log]]` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging patterns at the appropriate abstraction level, matching to active experiments, and routing to bugs/patterns/experiments.

## Three-Phase Workflow

The skill executes:

1. **LOG.md entry** - Append-only chronological record with session ID, error, root cause, abstraction level
2. **Experiment matching** - Search active experiments, update if related
3. **Abstraction routing** - Route to bugs/ (component), learning/ (pattern), or experiments/ (systemic)

## Abstraction Levels

| Level | When | Example |
|-------|------|---------|
| `component` | Specific script/file bug | "task_view.py throws KeyError" |
| `pattern` | Behavioral pattern across agents | "Agent ignored explicit ALL instruction" |
| `systemic` | Infrastructure issue needing investigation | "Hooks not loading context" |

**Key principle**: Don't create separate bug files for instances of the same pattern. Don't lump specific bugs into general categories.

## Modes

### Standard Mode (default)
Log observation with abstraction routing.

**User provides**: Brief description of observation (success or failure)

### Heuristic Adjustment Mode
Adjust heuristic confidence based on new evidence.

**User provides**: `adjust-heuristic H[n]: [observation]`

**Example**: `/log adjust-heuristic H3: Agent claimed success without running tests - confirms H3`

## Output Files

- `$ACA_DATA/projects/aops/learning/LOG.md` - Chronological append-only log
- `$ACA_DATA/projects/aops/learning/*.md` - Thematic pattern files
- `$ACA_DATA/projects/aops/bugs/*.md` - Component-specific bugs (delete when fixed)
- `$ACA_DATA/projects/aops/experiments/*.md` - Systemic investigations
- `$AOPS/[[HEURISTICS.md]]` - Heuristic evidence (when adjusting)
