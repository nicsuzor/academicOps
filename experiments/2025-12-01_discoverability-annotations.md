---
title: Discoverability Annotations Experiment
date: 2025-12-01
status: in-progress
tags:
  - axiom-22
  - discoverability
  - docs-update
---

# Experiment: Discoverability Annotations

## Hypothesis

Strengthening the docs-update skill to MANDATE annotations on all entries (especially nested README files) will cause agents to produce README.md updates that make information discoverable just-in-time, not just "existing."

## Background

Advocate failure: Accepted that skills/README.md "exists" and contains framework skill documentation, but failed to notice it has NO annotation in the main README.md:

```
├── skills/                  # Agent skills (invoke via Skill tool)
│   ├── README.md            # <-- NO ANNOTATION
```

This violates AXIOM #22: "The framework provides all required information for agents to succeed first-time."

Information EXISTING ≠ information being DISCOVERABLE.

## Changes Made

Modified `skills/docs-update/SKILL.md`:

1. Made annotations MANDATORY with "NO EXCEPTIONS"
2. Added explicit rule for nested README files
3. Added AXIOM #22 enforcement note

## Test Prompt

Run this in a NEW session to test whether the updated skill produces discoverable documentation:

```
Use the docs-update skill to update README.md. Focus especially on ensuring every entry has an annotation that explains its purpose and makes the content discoverable.
```

## Success Criteria

1. Agent invokes docs-update skill (not editing README directly)
2. Agent adds annotation to `skills/README.md` entry explaining it contains skill catalog/details
3. Agent checks ALL other entries for missing annotations
4. Final README.md has zero unannotated entries

## Failure Criteria

1. Agent edits README directly without skill
2. Agent leaves any entries without annotations
3. Agent adds generic/useless annotations that don't aid discoverability

## Results

**PARTIAL SUCCESS** - Initial hypothesis validated, but follow-up revealed deeper issues.

**Process observations:**
1. Agent invoked docs-update skill correctly (read SKILL.md first)
2. Agent followed 8-step workflow with TodoWrite tracking
3. Agent verified file existence before documenting
4. Agent removed non-existent files (log_session_stop.py, update_hooks.py)

**README.md result:**
- `skills/README.md # Skill catalog and usage` ✓ (the specific failure case)
- `hooks/README.md # Hook documentation` ✓
- `tests/README.md # Test documentation` ✓
- All commands have descriptions ✓
- All agents have descriptions ✓
- 236 lines (under 300 limit) ✓

## Lessons Learned

**The fix worked because it made implicit expectations explicit.**

When agents fail to do something, check if the instruction is:
1. **Present but weak** → strengthen with MANDATORY + NO EXCEPTIONS language
2. **Implicit** → make explicit with specific examples (nested README rule)
3. **Disconnected from axioms** → link to foundational principles (AXIOM #22 reference)

**Generalizable pattern**: Skill instructions that say "should" or "must" without enforcement context get treated as suggestions. Adding:
- Explicit MANDATORY markers
- Specific edge case rules
- Connection to axioms

...causes agents to follow through.

## Follow-up: Additional Failures Found (same day)

The initial experiment was marked success too early. Manual review revealed:

1. **Scripts hidden**: Skills shown at directory level only. `task_viz_layout.py` was in wrong location (`framework/scripts/` instead of `excalidraw/scripts/`) and this was INVISIBLE in README
2. **Useless annotations**: "Task visualization" vs "Task graph visualization" don't distinguish `commands/task-viz.md` from `agents/task-viz.md`

**Additional fixes applied to docs-update skill**:
- Principle #3: SHOW ALL SCRIPTS (expanded with annotations)
- Principle #4: SHOW ALL REFERENCES (expanded with annotations)
- "Distinction test" for annotations
- Line limit increased 300 → 400

**Deeper lesson**: Discoverability has layers:
- Layer 1: Annotation presence ✓ (this experiment)
- Layer 2: Internal structure visible ✗ (missed)
- Layer 3: Annotations distinguish similar files ✗ (missed)

See: [[projects/aops/learning/readme-discoverability-failure-hidden-scripts]]
