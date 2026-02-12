---
id: non-interactive-agent-workflow-spec
title: "Non-Interactive Agent Workflow Specification"
permalink: non-interactive-agent-workflow-spec
type: spec
status: draft
created: '2026-02-12'
modified: '2026-02-12'
parent: aops-core-1dcb461d
tags:
- framework
- agent-automation
- specification
- workflow
---

# Non-Interactive Agent Workflow Specification

Complete lifecycle for non-interactive agent operation: task selection through PR merge and knowledge capture.

> **ARCHITECTURE PIVOT (2026-02-12)**: This spec has been revised from programmatic infrastructure to agent-based prompts. The lifecycle phases below remain valid as *concepts*, but their implementation is prompt-driven, not code-driven. Agents make all decisions; code is limited to hooks (triggers) and MCP tools (task state). See project task `aops-core-e89cdca4` for the revised plan.

## Design Principles — Revised

1. **Agents decide, code triggers** - Hooks start agent work; agents make all substantive decisions via prompts
2. **Minimal code surface** - A few hooks, a few MCP tools, everything else is prompt text
3. **Fail loudly** - No silent failures; every error surfaces to observable state
4. **Human-in-the-loop gates** - Automation proposes, humans approve (at PR, not at plan)
5. **Task body is the audit trail** - No separate observability infrastructure; agents append to task bodies as they work

## What Is Code vs What Is Prompt

| Concern | Implementation | Rationale |
|---|---|---|
| Task state transitions | Code (MCP tools + guards) | Deterministic, already built |
| Trigger: "check for ready tasks" | Code (shell hook / cron) | Mechanical trigger |
| Trigger: "post-merge capture" | Code (git hook) | Mechanical trigger |
| Decomposition strategy | Prompt (supervisor skill) | Requires judgment |
| Reviewer selection & synthesis | Prompt (supervisor skill) | Requires judgment |
| Worker selection & dispatch | Prompt (supervisor skill) | Requires judgment |
| Knowledge extraction | Prompt (/remember skill) | Already exists |
| Consensus & debate | Prompt (supervisor skill) | Requires judgment |
| Decision surfacing | Prompt (/daily skill) | Already exists |
| PR lifecycle monitoring | Prompt (agent uses `gh` CLI) | On-demand, not infrastructure |

---

## Original Design Principles (Superseded)

1. **Fail loudly** - No silent failures; every error surfaces to observable state
2. **Idempotent by default** - All state transitions include idempotency keys
3. **Timeout everything** - No operation can block indefinitely
4. **Human-in-the-loop gates** - Automation proposes, humans approve
5. **Observable at every step** - Audit log captures all transitions

---

## Task State Machine

### States

| Status        | Phase | Meaning                                     |
| ------------- | ----- | ------------------------------------------- |
| `pending`     | -     | In queue, not claimed                       |
| `active`      | 1     | Agent claimed, beginning work               |
| `decomposing` | 1     | Effectual planner iterating                 |
| `consensus`   | 2     | Multi-agent review in progress              |
| `waiting`     | 3     | Awaiting user decision                      |
| `in_progress` | 4     | Worker executing approved plan              |
| `review`      | 5     | PR filed, awaiting review consensus         |
| `merge_ready` | 5     | Reviews done, awaiting merge approval       |
| `done`        | 6     | Merged, knowledge captured                  |
| `blocked`     | any   | External dependency, with unblock condition |
| `dormant`     | -     | User-initiated backburner                   |
| `failed`      | any   | Unrecoverable error, with diagnostic        |
| `cancelled`   | -     | Abandoned, with reason                      |

### Transition Table

All transitions require idempotency key and timestamp.

```
FROM          -> TO           | TRIGGER                      | GUARD
pending       -> active       | polecat claims               | lock acquired
pending       -> cancelled    | user cancels                 | -
active        -> decomposing  | begin breakdown              | -
active        -> blocked      | dependency discovered        | unblock_condition set
active        -> failed       | claim timeout (30s)          | -
decomposing   -> decomposing  | iteration complete           | depth < MAX_DEPTH (10)
decomposing   -> consensus    | proposal ready               | all subtasks PR-sized
decomposing   -> blocked      | external dependency found    | unblock_condition set
decomposing   -> failed       | depth >= MAX_DEPTH           | diagnostic: "irreducible"
decomposing   -> failed       | exception                    | diagnostic: error message
decomposing   -> cancelled    | user cancels                 | -
consensus     -> waiting      | all reviewers APPROVE        | -
consensus     -> decomposing  | any reviewer BLOCK           | feedback attached
consensus     -> waiting      | timeout (30min)              | escalate: unresolved concerns
consensus     -> failed       | all reviewers unavailable    | diagnostic: "no reviewers"
consensus     -> cancelled    | user cancels                 | -
waiting       -> in_progress  | user approves                | -
waiting       -> decomposing  | user requests changes        | feedback attached
waiting       -> pending      | user sends back              | assignee cleared
waiting       -> dormant      | user backburners             | -
waiting       -> cancelled    | user cancels                 | reason attached
waiting       -> failed       | timeout (7 days)             | diagnostic: "approval timeout"
in_progress   -> review       | PR filed                     | pr_url set
in_progress   -> blocked      | dependency discovered        | unblock_condition set
in_progress   -> failed       | worker crash                 | diagnostic: crash report
in_progress   -> failed       | timeout (24h no progress)    | diagnostic: "stalled"
in_progress   -> cancelled    | user cancels                 | cleanup triggered
review        -> merge_ready  | review consensus reached     | all APPROVE
review        -> in_progress  | changes requested            | pr_comments attached
review        -> blocked      | dependency discovered        | unblock_condition set
review        -> failed       | timeout (7 days no activity) | diagnostic: "review timeout"
review        -> cancelled    | PR closed without merge      | -
merge_ready   -> done         | user approves merge          | merged = true
merge_ready   -> review       | last-minute concern          | -
merge_ready   -> cancelled    | user declines                | reason attached
blocked       -> [prior]      | unblock_condition met        | restore prior state
blocked       -> failed       | timeout (14 days)            | diagnostic: "blocked timeout"
blocked       -> cancelled    | user cancels                 | -
dormant       -> pending      | user reactivates             | priority recalculated
dormant       -> cancelled    | user cancels                 | -
done          -> [terminal]   | -                            | knowledge extraction complete
failed        -> pending      | user retries                 | reset with diagnostic
failed        -> cancelled    | user abandons                | -
cancelled     -> [terminal]   | -                            | -
```

### State Invariants

- `blocked` must have `unblock_condition` field set
- `failed` must have `diagnostic` field set
- `cancelled` must have `reason` field set
- `in_progress` must have `worker_id` field set
- `review` must have `pr_url` field set

---

## Phase 1: Pull and Decompose

### Trigger

Polecat worker calls `claim_next_task()` with atomic lock.

### Timeout Policy

| Operation                      | Timeout | On Timeout                        |
| ------------------------------ | ------- | --------------------------------- |
| Lock acquisition               | 30s     | Retry 3x, then skip task          |
| Hydration                      | 60s     | -> `failed`                       |
| Single decomposition iteration | 10min   | -> `failed`                       |
| Total decomposition            | 2h      | Force checkpoint, surface to user |

### PR-Sized Definition

A task is PR-sized when ALL of:

- Estimated effort ≤ 4 hours (agent time)
- Touches ≤ 10 files
- Single logical unit (one "why")
- Testable in isolation
- Reviewable by human in ≤ 15 minutes

### Decomposition Depth Limit

MAX_DEPTH = 10 iterations. If exceeded:

- Task -> `failed` with diagnostic "irreducible after 10 iterations"
- Surfaces to user with full decomposition history
- User can: manually decompose, mark as `blocked`, or `cancel`

### Output Format

Appended to task body:

```markdown
## Decomposition Proposal v{iteration}

### Subtasks

| ID        | Title       | Estimate | Confidence |
| --------- | ----------- | -------- | ---------- |
| subtask-1 | Description | 2h       | medium     |
| subtask-2 | Description | 1h       | high       |

### Dependency Graph

subtask-1 -> subtask-2 (blocks)
subtask-1 ~> subtask-3 (informs)

### Information Spikes (must resolve first)

- [ ] spike-1: Question we need answered

### Assumptions (load-bearing, untested)

- Assumption 1
- Assumption 2

### Risks

- Risk 1 (mitigation: ...)
```

---

## Phase 2: Multi-Agent Review (Consensus Protocol)

### Reviewers

| Reviewer          | Role                                                        | Mandatory                                 |
| ----------------- | ----------------------------------------------------------- | ----------------------------------------- |
| Custodiet         | Authority check: is task within granted scope?              | Yes                                       |
| Critic            | Pedantic review: assumptions, logical errors, missing cases | Yes                                       |
| Domain specialist | Subject matter expertise                                    | If task.tags intersect specialist.domains |

### Specialist Registry

Configured in `data/aops-core/config/specialist-registry.yaml`:

```yaml
specialists:
  security-reviewer:
    domains: [auth, crypto, permissions]
    model: claude
  research-methodology:
    domains: [empirical, statistics, methods]
    model: opus
```

### Execution: Parallel with Short-Circuit on BLOCK

1. All reviewers invoked simultaneously
2. If ANY returns BLOCK: short-circuit, cancel pending reviewers, return to `decomposing`
3. Else wait for all (with individual 10min timeouts)
4. Aggregate responses

### Response Format

Each reviewer returns:

```yaml
verdict: APPROVE | CONCERN | BLOCK | ESCALATE
rationale: "Why this verdict"
concerns: []  # List of specific issues
suggestions: []  # Optional improvements
```

### Aggregation Rules

| Condition                | Result                           |
| ------------------------ | -------------------------------- |
| All APPROVE              | -> `waiting`                     |
| Any BLOCK                | -> `decomposing` (with feedback) |
| Any ESCALATE             | -> `waiting` (escalated: true)   |
| Mixed CONCERN (no BLOCK) | -> Debate round                  |

### Debate Protocol

Max 2 rounds. Each round:

1. Reviewers see all concerns from previous round
2. Each reviewer has 5 minutes to respond: WITHDRAW (concede) or MAINTAIN (defend)
3. If all concerns WITHDRAWN -> `waiting`
4. After round 2, any unresolved concerns synthesized for user

Debate timeout: 10 minutes per round. On timeout: assume MAINTAIN, proceed to synthesis.

### Synthesized Summary

When debate doesn't resolve:

```markdown
## Unresolved Review Concerns

### Critic says:

[concern text]
Response: [defender text]
Resolution: UNRESOLVED - user must decide

### Custodiet says:

...
```

---

## Phase 3: User Approval Gate

### Decision States

Task in `waiting` has:

- `approval_type`: `standard` | `escalated`
- `decision_deadline`: timestamp (7 days from entering `waiting`)
- `concerns`: list of unresolved concerns (if any)

### Batch Interface: Daily Note Section

Primary interface. Updated by `/daily` skill:

```markdown
## Pending Decisions (3)

### Standard Approvals

| Task                 | Summary               | Risk | Age |
| -------------------- | --------------------- | ---- | --- |
| [[aops-core-abc123]] | Decompose auth module | Low  | 2d  |

### Escalated (requires attention)

| Task                 | Summary           | Concern                            | Age |
| -------------------- | ----------------- | ---------------------------------- | --- |
| [[aops-core-def456]] | Refactor DB layer | Critic/Custodiet disagree on scope | 1d  |
```

### Alternative: `/decisions` Command

<!-- NS: let's just have one CLI -- merge this and polecat and task together into 'task' -->

```bash
aops decisions                    # List all pending
aops decisions --escalated        # Only escalated
aops decisions approve abc123     # Approve
aops decisions approve abc123 --note "proceeed with caution"
aops decisions changes abc123 "need spike on X first"
aops decisions back abc123        # Send back to pending
aops decisions backburner abc123  # Move to dormant
aops decisions cancel abc123 "out of scope"
```

### User Actions

| Action          | Task State       | Notes                                |
| --------------- | ---------------- | ------------------------------------ |
| Approve         | -> `in_progress` | Subtasks created, first claimed      |
| Request Changes | -> `decomposing` | Feedback attached                    |
| Send Back       | -> `pending`     | Assignee cleared, ready for re-claim |
| Backburner      | -> `dormant`     | Preserved but inactive               |
| Cancel          | -> `cancelled`   | Reason required                      |

### Timeout Behavior

If 7 days pass without user action:

- Standard approvals: -> `failed` with diagnostic "approval timeout"
- Escalated: Daily reminder on day 3, 5, 7; then `failed`

---

## Phase 4: Worker Execution

### Worker Registry

Configured in `data/aops-core/config/worker-registry.yaml`:

```yaml
workers:
  polecat-claude:
    capabilities: [code, docs, refactor, test]
    cost: 3  # relative scale 1-5
    speed: 5  # relative scale 1-5
    max_concurrent: 4

  polecat-gemini:
    capabilities: [code, docs, analysis]
    cost: 1
    speed: 3
    max_concurrent: 8

  github-actions:
    capabilities: [ci, build, deploy, lint]
    cost: 1
    speed: 5
    max_concurrent: 10

  jules:
    capabilities: [deep-code, architecture, complex-refactor]
    cost: 5
    speed: 1
    max_concurrent: 1
```

### Selection Algorithm

```python
def select_worker(task):
    required = set(task.tags) & CAPABILITY_TAGS
    candidates = [w for w in workers if required <= w.capabilities]
    if not candidates:
        return None  # -> blocked, unblock: "add worker with capabilities"

    # Sort by: cost ASC, speed DESC, name ASC (deterministic tie-break)
    candidates.sort(key=lambda w: (w.cost, -w.speed, w.name))

    for worker in candidates:
        if worker.current_tasks < worker.max_concurrent:
            return worker

    return None  # -> wait and retry
```

### No Worker Available

If no worker available after 3 attempts (1 hour apart):

- Task -> `blocked` with `unblock_condition: "worker availability"`
- Alert in daily note
- Auto-retry when any worker becomes available

### Worker Execution Flow

1. Worker claims task (atomic lock)
2. Creates feature branch
3. Implements changes (following worker's standard workflow)
4. Runs tests locally
5. Files PR with standardized description
6. Task -> `review` with `pr_url`

### Progress Tracking

Worker must update task every 30 minutes with:

- Current step
- Files touched
- Any blockers discovered

If no update for 60 minutes: ping worker. If no response for 24 hours: -> `failed`.

---

## Phase 5: PR Review and Merge

### GitHub Webhook Integration

| Event                              | Action                |
| ---------------------------------- | --------------------- |
| `pull_request.opened`              | Trigger review agents |
| `pull_request.synchronize`         | Re-trigger review     |
| `pull_request_review.submitted`    | Aggregate verdict     |
| `check_suite.completed`            | Update CI status      |
| `pull_request.closed` (merged)     | -> Phase 6            |
| `pull_request.closed` (not merged) | -> `cancelled`        |

### Webhook Reliability

GitHub webhooks are not guaranteed. Mitigation:

- Reconciliation job runs hourly
- Compares PR state to task state
- Triggers missed transitions

### Review Agents

| Agent         | Trigger              | Timeout |
| ------------- | -------------------- | ------- |
| lgtm-bot      | Always               | 5min    |
| code-reviewer | Always               | 30min   |
| sme-reviewer  | If domain tags match | 30min   |

### Consensus: Same Protocol as Phase 2

- All APPROVE -> `merge_ready`
- Any BLOCK -> `in_progress` (changes requested, feedback in PR comments)
- Mixed CONCERN -> Debate in PR comments (max 2 rounds)
- Timeout (7 days no activity) -> `failed`

### Merge Approval

Human gate. Daily note shows:

```markdown
## Ready to Merge (2)

| PR          | Task         | Tests | Reviews     | Summary           |
| ----------- | ------------ | ----- | ----------- | ----------------- |
| [#123](url) | [[task-abc]] | Pass  | 3/3 APPROVE | Added auth module |
```

User actions: merge (via GitHub) | request changes | close

---

## Phase 6: Post-Merge Knowledge Capture

### Trigger

GitHub webhook `pull_request.closed` where `merged = true`, OR reconciliation job detects merged PR.

### Idempotency

Knowledge extraction uses `pr_number` as idempotency key. Re-running is safe.

### Data Collection

Sources (with fallbacks):

1. PR description and comments (GitHub API)
2. Commit messages (git log)
3. Task body (local markdown)
4. Review comments (GitHub API)
5. CI logs (if relevant)

If GitHub API fails: retry 3x with exponential backoff, then proceed with local data only.

### Extraction Process

```python
def extract_knowledge(task, pr):
    # 1. Collect all text
    corpus = gather_corpus(task, pr)

    # 2. Extract structured learnings (LLM)
    learnings = extract_learnings(corpus)
    # Returns: decisions_made, alternatives_rejected,
    #          patterns_discovered, mistakes_caught, estimate_accuracy

    # 3. Validate (no hallucination check)
    validated = [l for l in learnings if l.evidence_in(corpus)]

    # 4. Deduplicate against existing knowledge
    novel = [l for l in validated if not l.exists_in(knowledge_graph)]

    return novel
```

### Knowledge Schema

Stored in `data/aops-core/knowledge/`:

```yaml
# data/aops-core/knowledge/2026-02-12-auth-module-learnings.yaml
source_task: aops-core-abc123
source_pr: 123
extracted: 2026-02-12T10:30:00Z

learnings:
  - type: pattern
    title: "Auth middleware should be stateless"
    evidence: "PR comment by reviewer at line 45"
    tags: [auth, architecture]

  - type: mistake_caught
    title: "Missing rate limit on login endpoint"
    caught_by: security-reviewer
    evidence: "Review comment"

  - type: estimate_accuracy
    estimated: 4h
    actual: 6h
    variance_reason: "Unexpected test fixture setup"
```

### Follow-up Task Creation

Rules for auto-creating follow-ups:

| Condition                     | Follow-up Type                     | Requires Approval |
| ----------------------------- | ---------------------------------- | ----------------- |
| TODO comment in merged code   | `task` with `tech-debt` tag        | No                |
| Reviewer suggests improvement | `task` with `enhancement` tag      | Yes               |
| Estimate >50% off             | `learn` task to improve estimation | No                |
| Pattern discovered            | Link to knowledge, no task         | N/A               |

Follow-ups created in `pending` with `parent` set to original task.

Infinite loop prevention: Follow-ups have `depth` field. Max depth = 2. Beyond that, log but don't create.

### Output Locations

| Artifact           | Location                       | Purpose           |
| ------------------ | ------------------------------ | ----------------- |
| Full execution log | Task body                      | Audit trail       |
| Learnings          | `data/aops-core/knowledge/`    | Knowledge graph   |
| Follow-up tasks    | Task queue                     | Future work       |
| Summary            | Daily note "Completed" section | User visibility   |
| Metrics            | Overwhelm dashboard            | Progress tracking |

### Daily Note Summary Format

```markdown
## Completed Today

### [[aops-core-abc123]] Auth Module Implementation

- **PR**: [#123](url) merged at 10:30
- **Effort**: 6h (estimated 4h)
- **Learnings**: 2 patterns, 1 mistake caught
- **Follow-ups**: 1 tech-debt task created
```

---

## Error Recovery

### Retry Policies

| Operation           | Max Retries | Backoff            | On Exhaustion   |
| ------------------- | ----------- | ------------------ | --------------- |
| Lock acquisition    | 3           | 10s, 30s, 60s      | Skip task       |
| GitHub API          | 3           | 1s, 5s, 30s        | Proceed without |
| Reviewer invocation | 2           | 30s, 60s           | Timeout verdict |
| Worker ping         | 3           | 5min, 15min, 30min | -> `failed`     |

### Cleanup on Failure/Cancellation

When task -> `failed` or `cancelled` from `in_progress`:

1. If branch exists: delete branch (or mark for cleanup)
2. If PR exists: close PR with comment explaining
3. Release worker lock
4. Log final state to task body

### Recovery from `failed`

User can retry a failed task:

1. Task -> `pending`
2. `diagnostic` from failure preserved in body
3. `retry_count` incremented
4. If `retry_count` >= 3: require user confirmation with explanation

---

## Observability

### Audit Log

Every state transition logged to `data/aops-core/audit/transitions.jsonl`:

```json
{
  "ts": "2026-02-12T10:30:00Z",
  "task": "abc123",
  "from": "consensus",
  "to": "waiting",
  "trigger": "all_approve",
  "actor": "system",
  "idempotency_key": "abc123-consensus-1707734400"
}
```

### Metrics (for dashboard)

- Tasks by state (current)
- State transition times (p50, p95)
- Approval wait times
- Worker utilization
- Failure rates by phase

### Alerts

| Condition            | Severity | Channel            |
| -------------------- | -------- | ------------------ |
| Task stuck > 24h     | Warning  | Daily note         |
| Task stuck > 72h     | Error    | Daily note + email |
| Failure rate > 20%   | Error    | Immediate          |
| No workers available | Warning  | Daily note         |

---

## Migration

### New States

Add to task schema: `decomposing`, `consensus`, `merge_ready`, `dormant`, `failed`

### New Fields

- `unblock_condition`: string (for `blocked`)
- `diagnostic`: string (for `failed`)
- `pr_url`: string (for `review`, `merge_ready`)
- `worker_id`: string (for `in_progress`)
- `approval_type`: enum (for `waiting`)
- `decision_deadline`: timestamp (for `waiting`)
- `retry_count`: int
- `depth`: int (for decomposition tracking)

### Backward Compatibility

Existing tasks in `active`, `in_progress`, `review`, `done` continue to work.
New states only apply to tasks entering workflow after migration.

---

## Open Questions (Deferred)

1. **Auto-approve for low-risk?** - Currently: No. All require human approval. Revisit after 30 days of data.
2. **Priority/preemption** - Not in v1. Tasks processed FIFO within priority band.
3. **Resource limits** - v1: No limits. Monitor and add if needed.
4. **Knowledge graph integration** - v1: Flat files. Graph database integration deferred.

---

## Implementation Sequence

1. Add new states and fields to task schema
2. Implement state transition guards and logging
3. Build consensus aggregator (parallel reviewer invocation)
4. Build debate facilitator
5. Implement decision queue (daily note integration)
6. Build worker router with capability matching
7. Add webhook handlers for PR lifecycle
8. Build knowledge extractor
9. Add reconciliation job for webhook reliability
10. Integration tests for full lifecycle
11. Observability: audit log, metrics, alerts

---

## Appendix: Example Walkthrough

### Task: "Add rate limiting to API endpoints"

1. **Pull**: Polecat claims task `aops-core-xyz789`
2. **Decompose** (2 iterations):
   - Iteration 1: Too big (15 files)
   - Iteration 2: Split into 3 subtasks, each PR-sized
3. **Consensus**:
   - Custodiet: APPROVE
   - Critic: CONCERN ("no spike for Redis vs in-memory")
   - Security: APPROVE
   - Debate: Critic withdraws after noting Redis already in use
4. **User Approval**: User approves in daily note (day 2)
5. **Worker**: polecat-claude claims subtask-1, implements, files PR #456
6. **Review**:
   - lgtm-bot: APPROVE
   - code-reviewer: CONCERN ("missing test for edge case")
   - Round 2: PR updated, reviewer changes to APPROVE
7. **Merge**: User clicks merge in GitHub
8. **Knowledge Capture**:
   - Extracts: "Rate limit config should be per-environment"
   - Creates follow-up: "Add staging environment rate limit config"
   - Summary in daily note: "PR #456 merged, 1 learning captured"
