---
title: Learning Log Workflow
type: instruction
category: instruction
permalink: workflow-learning-log
description: Document agent behavior patterns as bd issues for later synthesis
---

# Workflow 7: Learning Log

**When**: After observing agent behavior patterns, errors, or framework gaps that should be tracked.

**Key principle**: Per AXIOMS #28 (Current State Machine) - episodic observations go to bd issues, not direct file edits. Analysis happens later via workflow 05 (QA Verification).

**CRITICAL**: If you need to read session JSONL files, invoke `Skill(skill='transcript')` FIRST to convert to markdown. Raw JSONL wastes 10-70K tokens; transcripts are 90% smaller.

## Workflow

### Phase 1: Search for Existing Issue

**First**: Search for existing issue that matches this observation:

```bash
bd list --label "[category]" --status open
bd search "[keywords]"
```

Categories/labels:

- `bug` - Component-level bugs (script errors, hook crashes)
- `learning` - Pattern-level observations (agent behavior patterns)
- `experiment` - Systemic investigations (infrastructure issues)
- `devlog` - Development observations

### Phase 2: Create or Update Issue

**If matching issue exists**: Update with new observation (append to description)

```bash
bd show [ISSUE_ID]  # Get current description
bd update [ISSUE_ID] --description "$(cat <<'EOF'
[existing description]

## Observation [DATE]

**What**: [description]
**Context**: [when/where]
**Evidence**: [specifics]
EOF
)"
```

**If no matching issue**: Create new issue

```bash
bd create --title "[category]: [descriptive-title]" \
  --label "[category]" \
  --type task \
  --description "$(cat <<'EOF'
## Initial Observation

**Date**: YYYY-MM-DD
**Session ID**: [session-id if available]
**Category**: bug | learning | experiment
**Proximate Cause**: [what agent did wrong]
**Root Cause**: [deferred - will be analyzed via qa workflow]
**Root Cause Category**: Clarity | Context | Blocking | Detection | Gap

## Evidence

[details]

## Queued Analysis

- [ ] Generate transcript (session_id above)
- [ ] Root cause analysis
- [ ] Reflection on framework component failure
- [ ] Create proposal issues for changes
EOF
)"
```

### Phase 3: Link to User Stories (if applicable)

Read `$AOPS/ROADMAP.md` for User Stories table.

If observation relates to a user story, add to issue body:

```
**User Story**: [story-name]
```

### Phase 4: Report and Exit

Report to user:

1. Issue ID created/updated
2. Category assigned
3. Next step: "Run `/qa [issue-id]` to perform full analysis"

**DO NOT perform root cause analysis immediately.** The `/qa` command (workflow 05) handles transcript generation, analysis, and proposal creation.

## Issue Labels (Categories)

| Label        | Use For                  | Example Title                                 |
| ------------ | ------------------------ | --------------------------------------------- |
| `bug`        | Component-level bugs     | `bug: task_view.py KeyError on missing field` |
| `learning`   | Agent behavior patterns  | `learning: agents ignoring explicit scope`    |
| `experiment` | Systemic investigations  | `experiment: hook context injection timing`   |
| `devlog`     | Development observations | `devlog: session-insights workflow`           |
| `decision`   | Architectural choices    | `decision: bd issues for episodic storage`    |

**Default**: `learning` if unclear.

## Root Cause Categories (for reference)

We don't control agents - they're probabilistic. Root causes must be framework component failures:

| Category          | Definition                                         | Fix Location                              |
| ----------------- | -------------------------------------------------- | ----------------------------------------- |
| Clarity Failure   | Instruction ambiguous or insufficiently emphasized | AXIOMS, skill text, guardrail instruction |
| Context Failure   | Component didn't provide relevant information      | Intent router, hydration                  |
| Blocking Failure  | Should have blocked but didn't                     | PreToolUse hook, deny rule                |
| Detection Failure | Should have caught but didn't                      | PostToolUse hook                          |
| Gap               | No component exists for this case                  | Create new enforcement                    |

## Constraints

**DO ONE THING**: Document observations only. Do NOT:

- Fix reported issues
- Perform root cause analysis (deferred to /qa)
- Implement solutions
- Debug problems

**VERIFY-FIRST**: Review observation carefully before categorizing.

## Example

```
User: /log agent ignored my explicit request to run ALL tests, only ran 3

Phase 1 - Search:
bd list --label learning --status open
bd search "instruction scope"
→ Found: aops-42 "learning: agents ignoring explicit scope instructions"

Phase 2 - Update existing issue:
bd show aops-42  # Get current description
bd update aops-42 --description "[existing + new observation]"

Report: "Added observation to aops-42 - recurring pattern. Run `/qa aops-42` to perform full analysis."
```

### Example: New Issue

```
User: /log hook crashed with TypeError in prompt_router.py

Phase 1 - Search:
bd list --label bug --status open
bd search "prompt_router TypeError"
→ No matching issues

Phase 2 - Create new issue:
bd create --title "bug: prompt_router.py TypeError on None response" \
  --label bug --type bug --description "## Initial Observation

**Date**: 2025-12-26
**Session ID**: abc123
**Category**: bug
**Proximate Cause**: Hook returned None, code expected dict
**Root Cause**: [deferred to qa workflow]

## Evidence

Stack trace:
[error details]

## Queued Analysis

- [ ] Generate transcript
- [ ] Root cause analysis
- [ ] Create fix proposal"

Report: "Created aops-47 for prompt_router bug. Run `/qa aops-47` to analyze."
```
