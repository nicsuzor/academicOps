---
name: learning-log
description: Log agent performance patterns to thematic learning files. Categorizes
  observations, matches to experiments, and routes to appropriate tracking files.
permalink: academic-ops/skills/learning-log/skill
---

# Learning Log Skill

Document agent behavior patterns with appropriate abstraction level routing. Creates chronological log entries, matches to active experiments, and routes to bugs/patterns/experiments based on issue type.

## Three-Phase Workflow

### Phase 1: Append to LOG.md

**Always first**: Create append-only entry in `$ACA_DATA/projects/aops/learning/LOG.md`

```markdown
### YYYY-MM-DD HH:MM | [session-id-prefix or "manual"]

**Error**: [brief description]
**Root Cause**: [why it happened - your analysis]
**Abstraction Level**: component | pattern | systemic
**Related**: [file path if matched, "pending" if creating new]
```

### Phase 2: Match to Active Experiments

Search `$ACA_DATA/projects/aops/experiments/` for experiments that:
- Are not marked complete/decided (check Decision section)
- Have hypothesis related to the observed behavior

**If match found**:
1. Append observation to experiment's Results section with date
2. Update LOG.md entry's "Related" field

### Phase 3: Route by Abstraction Level

Determine the appropriate level and route accordingly:

| Level | Criteria | Action |
|-------|----------|--------|
| `component` | Specific, reproducible bug in named script/file | Create/update `bugs/[component].md` |
| `pattern` | Behavioral pattern across agents/sessions | Append to `learning/[theme].md` |
| `systemic` | Infrastructure issue needing investigation | Create/update experiment |

#### Component-Level (bugs/)

For specific script errors (e.g., task_view.py fails, hook crashes):
- Check if `$ACA_DATA/projects/aops/bugs/[component].md` exists
- If yes: append new observation
- If no: create with bmem frontmatter
- **Delete when fixed** (per framework conventions)

#### Pattern-Level (learning/)

For behavioral patterns (e.g., agents ignoring instructions):
- Route to existing thematic file based on tags
- Use standard entry format (see below)

#### Systemic-Level (experiments/)

For issues needing investigation:
1. **Search first**: Look for thematically similar experiments
2. **If related experiment exists**: Update that experiment, don't create new
3. **If no match**: Create `experiments/[date]-[topic].md`
4. **Consolidation rule**: When creating new, actively look for experiments to merge. Rename/consolidate as understanding improves.

## Abstraction Level Judgment

**Key principle**: Match abstraction to likely intervention specificity.

Examples:
- "task_view.py throws KeyError" → `component` (fix that script)
- "Two agents both ignored explicit user request" → `pattern` (instruction presentation issue)
- "Hooks seem to not be loading context" → `systemic` (needs investigation)

**Don't**:
- Create separate bug files for instances of the same pattern
- Lump specific script bugs into general categories

## Pattern Tags and Thematic Routing

| Tags | Target File |
|------|-------------|
| #verify-first, #overconfidence, #validation, #incomplete-task | `verification-discipline.md` |
| #instruction-following, #scope, #literal, #user-request | `instruction-following.md` |
| #git-safety, #no-verify, #validation-bypass, #pre-commit | `git-and-validation.md` |
| #skill-invocation, #tool-usage, #mcp, #bmem-integration | `skill-and-tool-usage.md` |
| #tdd, #testing, #test-contract, #fake-data | `test-and-tdd.md` |
| #success, #tdd-win, #workflow-success | `technical-wins.md` |

**Default**: `verification-discipline.md` if no clear match.

## Entry Formats

### LOG.md Entry (Phase 1)

```markdown
### YYYY-MM-DD HH:MM | session-prefix

**Error**: [brief description]
**Root Cause**: [analysis]
**Abstraction Level**: component | pattern | systemic
**Related**: bugs/component.md | learning/theme.md | experiments/file.md
```

### Learning File Entry (Pattern Level)

```markdown
## [Brief Title]

**Date**: YYYY-MM-DD | **Type**: Success/Failure | **Pattern**: #tag1 #tag2

**What**: [One sentence - what happened]
**Why**: [One sentence - significance]
**Lesson**: [One sentence - actionable takeaway]
```

### Bug File Format (Component Level)

```markdown
---
title: [Component] Errors
type: bug
permalink: bugs-[component]
tags:
  - bug
  - [component]
---

# [Component] Errors

## Observations

### YYYY-MM-DD
- [fact] [error description] #bug
- [context] [when it occurred]
- [status] open | investigating | fixed
```

### Experiment Entry (Systemic Level)

Follow `$ACA_DATA/projects/aops/experiments/TEMPLATE.md`

## Input Types

1. **Verbal description** - User describes what happened
2. **Transcript file(s)** - Path to transcript markdown
3. **Session JSONL** - First invoke `transcript` skill, then analyze
4. **Heuristic adjustment** - `adjust-heuristic H[n]: [observation]`

## Heuristic Adjustment Mode

When input contains `adjust-heuristic H[n]:`:

1. Parse heuristic ID and observation
2. Read `$AOPS/HEURISTICS.md`
3. Add dated evidence to heuristic
4. Adjust confidence if warranted
5. Also log to LOG.md and appropriate thematic file

## Constraints

**DO ONE THING**: Document observations only. Do NOT:
- Fix reported issues
- Implement solutions
- Debug problems

**VERIFY-FIRST**: Review observation carefully before categorizing.

## Example

```
User: /log agent ignored my explicit request to run ALL tests, only ran 3

Phase 1 - LOG.md:
### 2025-12-14 08:45 | abc123

**Error**: Agent ran only 3 tests when explicitly asked to run ALL
**Root Cause**: Agent not attending to explicit scope instruction
**Abstraction Level**: pattern
**Related**: learning/instruction-following.md

Phase 2 - Experiment Match:
Search experiments/ for "instruction following" → no active experiment

Phase 3 - Route:
- Level: pattern (behavioral, not script-specific)
- Tags: #instruction-following #scope
- Target: instruction-following.md
- Append entry

Report: "Logged to instruction-following.md - recurring pattern of agents not attending to explicit scope instructions"
```
