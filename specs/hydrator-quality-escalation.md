---
title: Hydrator Quality Escalation Process
type: spec
status: active
tier: process
tags: [spec, hydrator, quality, escalation, feedback-loop, jit-context]
created: 2026-03-17
parent: aops-fa32b8ad
permalink: hydrator-quality-escalation
---

# Hydrator Quality Escalation Process

## Problem Statement

The hydration/JIT context system repeatedly fails to deliver information that agents need, causing them to waste time, make wrong assumptions, or require human correction in-session. These failures are not one-off bugs -- they are a systemic quality problem that requires ongoing ownership, not just individual fixes.

Two failure modes recur:

1. **Architecture knowledge gaps**: The hydrator does not surface how the system actually works (e.g., that `.env.local` gate mode env vars are injected at session launch via `CLAUDE_ENV_FILE`, not sourced inside hook subprocesses).
2. **Existing-work blindness**: The hydrator fails to surface existing test suites, specs, or implementations before the agent proposes building something that already exists (e.g., proposing a "gate simulator" CLI tool when `tests/hooks/test_gate_verdicts.py` already covers exactly that).

## Ownership

**Owner**: The Hydrator agent (Curia member) owns hydration quality as an ongoing concern, not a one-time fix. Every session that involves hydrator work should include a quality check against this spec.

**Human escalation**: When an agent cannot diagnose why context was missing (the hydrator's own context about itself may be insufficient), the agent must create a task under `aops-fa32b8ad` with the `hydrator-quality` tag and flag it for human review.

## The Escalation Chain

### Level 1: In-Session Correction (Immediate)

When a human corrects an agent's understanding during a session:

1. The correction is a **signal** that the hydrator failed to deliver needed context.
2. The agent receiving the correction must:
   a. Record the correction as a PKB memory with tags `["hydrator-quality", "in-session-correction"]`
   b. Create a task under epic `aops-fa32b8ad` titled "Hydrator gap: [what was missing]"
   c. Classify the gap (see Gap Taxonomy below)
   d. If the fix is obvious and localized (e.g., adding a file path to a context-map), fix it inline
   e. If the fix requires investigation, leave the task for a future session

**Key principle**: The corrected agent does the filing, not the human. The human's correction is the input; the task creation is automatic.

### Level 2: Diagnosis (Next Available Session)

A session working on hydrator quality tasks must:

1. Read the gap task body
2. Reproduce the failure: what prompt would trigger this gap? What context should have been surfaced?
3. Identify the root cause (see Root Cause Categories below)
4. Propose a fix with acceptance criteria
5. If the fix is cross-cutting (affects multiple workflows), escalate to Level 3

### Level 3: Structural Improvement (Release-Gated)

When diagnosis reveals a structural problem (not just a missing fact):

1. Create a spec or spec amendment describing the structural change
2. Wire it as a dependency of the current release milestone
3. Include regression tests (add scenarios to `tests/hooks/test_gate_verdicts.py` or create new test files)
4. QA verification required before closing

## Gap Taxonomy

| Gap Type                   | Description                                                                     | Example                                                                      | Typical Fix                                           |
| -------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------- |
| **Missing fact**           | A specific fact about the system is not in any context the hydrator can access  | "env vars are injected via CLAUDE_ENV_FILE"                                  | Add to relevant reference doc or memory               |
| **Missing file reference** | The hydrator does not know to surface a specific file when context matches      | "test_gate_verdicts.py exists and covers gate simulation"                    | Add to context-map.json or workflow reference section |
| **Wrong assumption**       | The hydrator (or agent) assumes something that contradicts how the system works | "hooks source .env.local in subprocess"                                      | Correct the reference doc; add to guardrails          |
| **Stale context**          | Context exists but is outdated                                                  | "test file moved from old location"                                          | Update reference; add staleness check                 |
| **Missing workflow step**  | A workflow omits a step that would have prevented the error                     | "feature-dev workflow should check existing tests before proposing new ones" | Update workflow file                                  |

## Root Cause Categories

| Root Cause                    | Description                                                              | Systemic Fix                                                       |
| ----------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| **Hydrator skill gap**        | SKILL.md does not instruct the hydrator to look for this type of context | Update `aops-core/skills/hydrator/SKILL.md`                        |
| **Workflow gap**              | The selected workflow does not include a relevant step                   | Update the workflow file in `aops-core/skills/hydrator/workflows/` |
| **Context map gap**           | The context-map.json does not route this type of work to relevant files  | Update `.agents/context-map.json`                                  |
| **Memory gap**                | No PKB memory exists for this knowledge                                  | Create memory with appropriate tags                                |
| **Reference doc gap**         | The reference document exists but omits critical information             | Update the reference doc                                           |
| **Hook architecture doc gap** | The hooks reference (`hooks.md`) does not explain this behavior          | Update `.agents/skills/framework/references/hooks.md`              |

## Feedback Loop: Correction to Improvement

```
Human corrects agent in session
        |
        v
Agent records correction as PKB memory
        |
        v
Agent creates task under aops-fa32b8ad
   (title: "Hydrator gap: [description]")
   (tags: hydrator-quality, gap-type)
        |
        v
Next hydrator-quality session picks up task
        |
        v
Diagnose: reproduce gap, identify root cause
        |
        v
Fix: update reference/workflow/context-map/memory
        |
        v
Verify: confirm the fix would have prevented the original failure
        |
        v
Close task with verification evidence
```

## Quality Metrics (Per Release)

Track these across releases to measure improvement:

1. **Gap count**: Number of new hydrator-quality tasks created per release
2. **Gap resolution time**: Days from creation to verified fix
3. **Recurrence rate**: How often the same gap type recurs after a fix
4. **Coverage**: Proportion of workflows that have been tested with realistic prompts

## Hydrator Self-Check (Mandatory)

When the hydrator is enriching a task that involves hooks, gates, or the framework itself, it MUST:

1. Search for existing test files: `tests/hooks/`, `tests/integration/`, `tests/e2e/`
2. Check if `test_gate_verdicts.py` scenarios cover the relevant gate behavior
3. Surface the hooks reference doc (`hooks.md`) architecture section
4. Note that gate mode env vars are injected at session launch (not sourced in hook subprocesses)
5. Check for related open tasks under `aops-fa32b8ad`

This self-check should be added to the hydrator's detection patterns in SKILL.md.

## Integration Points

- **Epic**: `aops-fa32b8ad` (Hydration Gate Reliability)
- **Existing tasks**: `aops-1bf76d85` (env var architecture gap)
- **Test suite**: `tests/hooks/test_gate_verdicts.py` (gate verdict regression tests)
- **Hydrator skill**: `aops-core/skills/hydrator/SKILL.md`
- **Context map**: `.agents/context-map.json`
- **Hooks reference**: `.agents/skills/framework/references/hooks.md`
- **Dogfooding workflow**: `aops-core/skills/hydrator/workflows/dogfooding.md`
- **Session insights**: `.agents/skills/session-insights/SKILL.md` (post-hoc gap detection)

## Acceptance Criteria

1. Every in-session correction creates a tracked task (not just a log entry)
2. Gap tasks are diagnosed within 2 sessions of creation
3. Fixes include verification that the original failure would not recur
4. The hydrator's SKILL.md includes a self-check for framework/hook tasks
5. Gap count per release trends downward over 3 releases

## Related

- [[dogfooding]] -- The execute/observe/codify loop that this process builds on
- [[meta-improvement]] -- General framework self-improvement workflow
- [[base-memory-capture]] -- How findings flow into PKB
- [[hooks]] -- Technical reference for the hook system
