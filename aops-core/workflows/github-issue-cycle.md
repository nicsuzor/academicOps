---
id: github-issue-cycle
category: operations
bases: [base-task-tracking]
status: draft
---

# GitHub Issue Cycle

Async, decentralized work coordination via GitHub issues.

## Design Principle

**Agent-agnostic**: We don't care WHO does a step, only that it's done. Any agent (local Claude, Gemini, Jules, Copilot) can pick up work. The issue is the single source of truth.

**Async-first**: Sessions are independent. Each session:

1. Fetches current state from GitHub
2. Does one step of work
3. Updates GitHub with results
4. Hands over cleanly

## Routing Signals

- Work tracked in a GitHub issue
- Responding to reviewer/critic comments
- Decentralized team coordination
- Testing bazaar model

## NOT This Workflow

- Pure local work → [[design]] or [[debugging]]
- One-shot task → [[direct-skill]]
- Goal-level planning → [[decompose]]

## The Cycle

```
┌─────────────────────────────────────────────────────────┐
│                    GITHUB ISSUE                          │
│  (SSoT: current plan, audit tables, acceptance criteria) │
└─────────────────────────────────────────────────────────┘
         ▲                                    │
         │ 6. UPDATE                          │ 1. TRIGGER
         │    - Edit issue body               │    - Manual: /pull or claim task
         │    - Leave completion comment      │    - Future: webhook on comment
         │                                    ▼
┌────────┴────────┐                  ┌─────────────────┐
│   5. HANDOVER   │                  │    2. FETCH     │
│   - Clean exit  │                  │    - gh issue   │
│   - Next agent  │                  │    - comments   │
│     can resume  │                  │    - task body  │
└─────────────────┘                  └────────┬────────┘
         ▲                                    │
         │                                    ▼
┌────────┴────────┐                  ┌─────────────────┐
│   4. EXECUTE    │◄─────────────────│   3. HYDRATE    │
│   - Do the work │                  │   - Determine   │
│   - One step    │                  │     approach    │
│   - Document    │                  │   - What's the  │
└─────────────────┘                  │     next step?  │
                                     └─────────────────┘
```

## Steps

### 1. Trigger

**Current**: Manual invocation

- User says "claim task X" or runs `/pull`
- Agent claims task in task manager

**Future**: Automated trigger (see task at end)

- GitHub webhook fires on issue comment
- Hook matches pattern (e.g., "ready for review", "@polecat")
- Agent spawns to handle

### 2. Fetch Context

```bash
# Get issue with full body
gh issue view <NUMBER> --repo <OWNER/REPO>

# Get comments (critic feedback, discussion)
gh issue view <NUMBER> --repo <OWNER/REPO> --comments
```

Parse from issue body:

- Current plan/decomposition
- Acceptance criteria
- Audit tables (what's been checked)
- Previous session notes

### 3. Hydrate

Run through prompt-hydrator to determine:

- What work phase are we in? (planning, implementing, reviewing)
- What's the specific next step?
- What context does the agent need?

Key questions:

- Is there unaddressed feedback in comments?
- Is the plan complete or needs revision?
- Are we ready to implement or still designing?

#### Verification Pattern (when critic requested audits)

If critic comments include verification commands (e.g., "run grep to verify"):

1. Execute the verification commands
2. Compare results against issue audit tables
3. If gaps found → revise plan, add missing items
4. If complete → signal ready for implementation

Example from bug #394:

```bash
# Critic requested: verify all GateResult call sites
grep -rn "GateResult" aops-core/ --include="*.py"

# Compare output against issue's "Complete Audit of GateResult Call Sites" table
# All lines match → plan is verified complete
```

### 4. Execute

Do ONE logical unit of work:

- If feedback exists → revise plan
- If plan approved → implement one piece
- If implementation done → update tests
- If tests pass → prepare for review

**Rule**: Complete the step, document results, stop. Don't chain into next step.

### 5. Update GitHub

Update the issue to reflect work done:

```bash
# Update issue body with revised plan
gh issue edit <NUMBER> --body-file <UPDATED_BODY.md>

# Leave comment signaling completion
gh issue comment <NUMBER> --body "Plan revised per critic feedback. Ready for next phase."
```

Comment conventions:

- `[PLAN REVISED]` - Plan updated based on feedback
- `[READY FOR REVIEW]` - Work complete, needs human/critic review
- `[BLOCKED: reason]` - Cannot proceed, needs input
- `[IMPLEMENTED: description]` - Code changes made, PR linked

### 6. Handover

Clean session exit:

- Task status updated (in_progress → active, or → review)
- All changes committed and pushed
- GitHub issue reflects current state
- Next agent can pick up without context loss

## Constraints

### Single Source of Truth

- **GitHub issue body** = current plan, acceptance criteria, audit tables
- **GitHub comments** = discussion, feedback, status signals
- **Local task** = pointer to issue + local execution state

Never let local task body diverge from GitHub issue. If you update the plan, update BOTH.

### Atomic Updates

Each session should leave the issue in a valid state:

- Plan is internally consistent
- No partial edits
- Clear signal of what was done and what's next

### Comment Hygiene

Don't spam comments. One comment per session summarizing:

- What you did
- What's next
- Any blockers

## Integration with Existing Workflows

This workflow composes with:

- [[design]] - For the planning phase within the cycle
- [[critic-fast]] - For plan review between cycles
- [[base-tdd]] - For implementation phases
- [[dogfooding]] - Meta-layer for observing the cycle itself

## Example Session

```
1. TRIGGER: User says "claim aops-84c88881"
2. FETCH: gh issue view 394 --comments
3. HYDRATE: Critic left feedback on missing call sites → need to revise plan
4. EXECUTE: Grep for additional call sites, update audit table
5. UPDATE: gh issue edit 394 --body-file revised.md
           gh issue comment 394 --body "[PLAN REVISED] Added 3 call sites to audit table"
6. HANDOVER: Task stays active, next session can implement
```

## Future: Automated Trigger

**Task to create**: Hook that responds to GitHub issue comments

Trigger conditions:

- Comment contains "@polecat" or "ready for agent"
- Comment from authorized reviewer
- Issue has "agent-ready" label

Action:

- Spawn agent with issue context
- Run through this workflow
- Post completion comment

---

## Dogfooding Notes

This workflow is being developed through use on bug #394 (hook system_message/context_injection separation).

### Session log

**2026-02-11 Session 1**: Workflow creation + plan verification

- Created this workflow file
- Demonstrated hydration process: fetch issue → check comments → verify audit tables
- Posted `[PLAN VERIFIED]` comment to issue #394
- Created task `aops-e103b512` for future automated trigger
- **Learning**: Verification step is critical — agent must run critic-requested greps and compare against audit tables before declaring plan complete
- **Next**: Implementation phase (Step 1: Fix custom_actions.py)

### Open Questions

1. **Comment conventions**: Are `[PLAN VERIFIED]`, `[READY FOR REVIEW]`, `[BLOCKED]` sufficient? What other signals needed?
2. **Handover granularity**: Should each decomposition step be a separate session, or batch related steps?
3. **Failure modes**: What happens if agent can't complete a step? How to signal partial progress?
