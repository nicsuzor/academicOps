---
id: non-interactive-agent-workflow-spec
title: "Non-Interactive Agent Workflow Specification"
permalink: non-interactive-agent-workflow-spec
type: spec
status: active
tier: polecat
depends_on: []
created: '2026-02-12'
modified: '2026-03-12'
parent: aops-core-1dcb461d
tags:
- framework
- agent-automation
- specification
- workflow
---

# Non-Interactive Agent Workflow Specification

Complete lifecycle for non-interactive agent operation: task selection through PR merge and knowledge capture.

> **ARCHITECTURE PIVOT (2026-02-12)**: This spec has been revised from programmatic infrastructure to agent-based prompts. The lifecycle phases below remain valid as _concepts_, but their implementation is prompt-driven, not code-driven. Agents make all decisions; code is limited to hooks (triggers) and MCP tools (task state). See project task `aops-core-e89cdca4` for the revised plan.

## Design Principles — Revised

1. **Agents decide, code triggers** - Hooks start agent work; agents make all substantive decisions via prompts
2. **Minimal code surface** - A few hooks, a few MCP tools, everything else is prompt text
3. **Fail loudly** - No silent failures; every error surfaces to observable state
4. **Human-in-the-loop gates** - Automation proposes, humans approve (at PR, not at plan)
5. **Task body is the audit trail** - No separate observability infrastructure; agents append to task bodies as they work

## User Expectations

### Phase 1: Decomposition & Review

- **Accuracy**: Users can rely on the supervisor to decompose large tasks into logical, PR-sized units that follow project conventions.
- **Transparency**: Users can see the full rationale for decomposition and any reviewer concerns directly in the task body before approving.
- **Fail-Fast**: If a task cannot be decomposed within 10 iterations, the system must escalate it to the user with a diagnostic rather than continuing indefinitely.

### Phase 2: Approval & Dispatch

- **Control**: No code-modifying worker will start until a human has explicitly approved the plan in the daily note or via CLI.
- **Isolation**: Every worker session is isolated in its own git worktree with a fresh `uv` environment, preventing cross-task contamination.
- **Observability**: Users can see which worker is claiming a task and track its progress (current step, files touched) in real-time via the task body.

### Phase 3: PR & Merge

- **Quality**: All PRs submitted by workers must pass automated CI checks and a multi-agent review (Custodiet + Critic) before being marked as `merge_ready`.
- **Merge Gate**: Users retain the final decision to merge any PR; auto-merge is only used for clean, pre-approved maintenance tasks.
- **Lifecycle Sync**: Merging a PR on GitHub automatically marks the associated task as `done` and triggers knowledge capture.

### Phase 4: Knowledge & Follow-up

- **Retention**: Structured learnings (decisions, mistakes, patterns) are extracted from every completed task and persisted to the knowledge base.
- **Continuity**: Technical debt or required improvements identified during execution are automatically captured as follow-up tasks in the `inbox` queue.

## What Is Code vs What Is Prompt

| Concern                          | Implementation               | Rationale                     |
| -------------------------------- | ---------------------------- | ----------------------------- |
| Task state transitions           | Code (MCP tools + guards)    | Deterministic, already built  |
| Trigger: "check for ready tasks" | Code (shell hook / cron)     | Mechanical trigger            |
| Trigger: "post-merge capture"    | Code (git hook)              | Mechanical trigger            |
| Decomposition strategy           | Prompt (supervisor skill)    | Requires judgment             |
| Reviewer selection & synthesis   | Prompt (supervisor skill)    | Requires judgment             |
| Worker selection & dispatch      | Prompt (supervisor skill)    | Requires judgment             |
| Knowledge extraction             | Prompt (/remember skill)     | Already exists                |
| Consensus & debate               | Prompt (supervisor skill)    | Requires judgment             |
| Decision surfacing               | Prompt (/daily skill)        | Already exists                |
| PR lifecycle monitoring          | Prompt (agent uses `gh` CLI) | On-demand, not infrastructure |

---

## Original Design Principles (Superseded)

1. **Fail loudly** - No silent failures; every error surfaces to observable state
2. **Idempotent by default** - All state transitions include idempotency keys
3. **Timeout everything** - No operation can block indefinitely
4. **Human-in-the-loop gates** - Automation proposes, humans approve
5. **Observable at every step** - Audit log captures all transitions

---

## Task State Machine

Task statuses are canonical — see [[aops-core/skills/remember/references/TAXONOMY.md#status-values-and-transitions]] for definitions and the authoritative transition graph. The phase labels in this spec (Phase 1 Decomposition, Phase 2 Review, Phase 3 Approval, Phase 4 Execution, Phase 5 Merge, Phase 6 Capture) describe workflow stages within a single canonical status, not separate status values.

### Phase → Status Mapping

| Workflow Phase                   | Canonical Status                                            |
| -------------------------------- | ----------------------------------------------------------- |
| Not yet claimed                  | `queued`                                                    |
| Phase 1: decomposition & review  | `in_progress` (supervisor phase: decomposing)               |
| Phase 2: multi-agent consensus   | `in_progress` (supervisor phase: consensus)                 |
| Phase 3: awaiting human approval | `review`                                                    |
| Phase 4: worker executing plan   | `in_progress`                                               |
| Phase 5: PR filed, CI / reviews  | `merge_ready` (post-filing) or `review` (changes requested) |
| Phase 6: merged, capture         | `done`                                                      |
| External dependency              | `blocked`                                                   |
| Deferred by human                | `paused` (resume intended) or `someday` (parked)            |
| Unrecoverable error              | `blocked` (with diagnostic) or `cancelled`                  |
| Abandoned                        | `cancelled`                                                 |

Internal phase tracking (decomposing / consensus / etc.) lives in the task body as supervisor phase annotations, not as status values.

### State Invariants

- `blocked` must have `unblock_condition` field set
- `in_progress` must have `worker_id` field set
- `merge_ready` / `review` (post-filing) must have `pr_url` or `pr` field set
- `cancelled` must have a reason recorded in the task body or `summary` field
- Unrecoverable execution errors are recorded as a `diagnostic` in the task body before transitioning to `blocked` or `cancelled`

---

## Phase 1: Pull and Decompose

### Trigger

Polecat worker calls `claim_next_task()` with atomic lock.

### Timeout Policy

| Operation                      | Timeout | On Timeout                        |
| ------------------------------ | ------- | --------------------------------- |
| Lock acquisition               | 30s     | Retry 3x, then skip task          |
| Hydration                      | 60s     | -> `blocked` with diagnostic      |
| Single decomposition iteration | 10min   | -> `blocked` with diagnostic      |
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

- Task -> `blocked` with diagnostic "irreducible after 10 iterations"
- Surfaces to user with full decomposition history
- User can: manually decompose, keep as `blocked`, or `cancel`

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
2. If ANY returns BLOCK: short-circuit, cancel pending reviewers, return to decomposition phase (stays `in_progress`)
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

| Condition                | Result                                                            |
| ------------------------ | ----------------------------------------------------------------- |
| All APPROVE              | -> `review` (awaiting human)                                      |
| Any BLOCK                | -> stay `in_progress`, decomposition phase re-run (with feedback) |
| Any ESCALATE             | -> `review` (escalated: true)                                     |
| Mixed CONCERN (no BLOCK) | -> Debate round                                                   |

### Debate Protocol

Max 2 rounds. Each round:

1. Reviewers see all concerns from previous round
2. Each reviewer has 5 minutes to respond: WITHDRAW (concede) or MAINTAIN (defend)
3. If all concerns WITHDRAWN -> `review` (awaiting human)
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

Task in `review` (Phase 3, awaiting user decision) has:

- `approval_type`: `standard` | `escalated`
- `decision_deadline`: timestamp (7 days from entering `review`)
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
aops decisions back abc123        # Send back to queued
aops decisions backburner abc123  # Move to paused
aops decisions cancel abc123 "out of scope"
```

### User Actions

| Action          | Task State                      | Notes                                |
| --------------- | ------------------------------- | ------------------------------------ |
| Approve         | -> `in_progress`                | Subtasks created, first claimed      |
| Request Changes | -> `in_progress` (re-decompose) | Feedback attached                    |
| Send Back       | -> `queued`                     | Assignee cleared, ready for re-claim |
| Backburner      | -> `paused`                     | Preserved but inactive; resume later |
| Cancel          | -> `cancelled`                  | Reason required                      |

### Timeout Behavior

If 7 days pass without user action:

- Standard approvals: -> `blocked` with diagnostic "approval timeout"
- Escalated: Daily reminder on day 3, 5, 7; then `blocked`

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

If no update for 60 minutes: ping worker. If no response for 24 hours: -> `blocked` with diagnostic.

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
- Timeout (7 days no activity) -> `blocked` with "review timeout" diagnostic

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

Follow-ups created in `inbox` (or `queued` if immediately dispatchable) with `parent` set to original task.

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

## Phase 6b: Protocol Retrospection (Self-Improvement)

### Purpose

Phase 6 captures **task-specific** knowledge (patterns from the work itself).
Phase 6b captures **process-level** knowledge (friction in how the system operated).

This is how the supervisor improves its own protocol over time — conservatively.

### Trigger

`retrospect.sh` lifecycle hook, typically:

- Cron: daily end-of-day
- Manual: after a batch of merges
- Post-merge: chained from Phase 6

### Design Constraint: Flexibility Over Optimization

Agents are eager optimizers. A supervisor that learns from one successful writing
workflow might force all workflows into that shape. Guard against this:

- **Observe, don't fix** — the retrospector logs observations, not recommendations
- **Flexibility gate** — changes must benefit 2+ workflow types (code, writing, analysis)
- **Pattern threshold** — single observations don't trigger changes; need 3+ occurrences
- **Human gate** — all protocol changes create `status: review` tasks
- **Scope limit** — retrospector proposes changes to supervisor behavior only,
  not to worker skills or task schema

### Process

```
1. GATHER
   - Read recent session transcripts (abridged)
   - Read task completion notes (task bodies of recently done tasks)
   - Read PR comments (gh pr view --comments)

2. SCAN for friction signals
   - Explicit: "had to retry", "misunderstood", "wrong file"
   - Structural: review→revision loops, blocked→unblocked churn
   - Timing: unusually long phases, repeated state transitions

3. EXTRACT observations (NOT fixes)
   For each friction signal:
   - What happened (factual, 1-2 sentences)
   - Which workflow type (code | writing | analysis | admin)
   - Which phase it occurred in (decompose | review | execute | merge)

4. FLEXIBILITY GATE
   For each observation, ask:
   - Would a fix help code workflows?
   - Would a fix help writing workflows?
   - Would a fix help analysis workflows?

   If ≥2 workflow types: proceed to step 5
   If <2: append to pattern accumulator, wait for more data

5. PATTERN ACCUMULATOR CHECK
   Read $WRITING/data/aops/patterns/pending.md
   - If this observation matches an existing pending pattern:
     increment count, add workflow type
   - If count ≥ 3 AND workflow types ≥ 2:
     → Invoke /learn with the accumulated observation
   - Otherwise: log and wait

6. DELEGATE TO /learn
   When threshold met, invoke /learn with:
   - The accumulated observation (all instances)
   - The workflow types affected
   - The phase where friction occurs
   /learn handles: root cause analysis, intervention level,
   experiment tracking, fix application, regression tests
```

### What Retrospector Owns vs What /learn Owns

| Concern                          | Retrospector | /learn              |
| -------------------------------- | ------------ | ------------------- |
| Transcript aggregation           | Yes          | No (single-session) |
| Cross-workflow pattern detection | Yes          | No                  |
| Flexibility gate                 | Yes          | No                  |
| Pattern accumulator              | Yes          | No                  |
| Root cause analysis              | No           | Yes                 |
| Graduated intervention ladder    | No           | Yes                 |
| Experiment tracking              | No           | Yes                 |
| Fix application + tests          | No           | Yes                 |

### Pattern Accumulator

File: `$WRITING/data/aops/patterns/pending.md`

Simple append-only log. Each entry:

- Date, session ID, workflow type, observation text, count

When an entry hits threshold (3+ occurrences, 2+ workflow types),
it gets handed to /learn and marked as `DELEGATED` in the log.

### Output

The retrospector produces no direct framework changes. It either:

- Logs an observation to the pattern accumulator (most runs), or
- Invokes /learn when a pattern crosses threshold (rare)

This deliberate indirection prevents over-reaction to single incidents.

---

## Error Recovery

### Retry Policies

| Operation           | Max Retries | Backoff            | On Exhaustion   |
| ------------------- | ----------- | ------------------ | --------------- |
| Lock acquisition    | 3           | 10s, 30s, 60s      | Skip task       |
| GitHub API          | 3           | 1s, 5s, 30s        | Proceed without |
| Reviewer invocation | 2           | 30s, 60s           | Timeout verdict |
| Worker ping         | 3           | 5min, 15min, 30min | -> `blocked`    |

### Cleanup on Failure/Cancellation

When task -> `blocked` (with diagnostic) or `cancelled` from `in_progress`:

1. If branch exists: delete branch (or mark for cleanup)
2. If PR exists: close PR with comment explaining
3. Release worker lock
4. Log final state to task body

### Recovery from a blocked/diagnosed failure

User can retry a task that halted with a diagnostic:

1. Task -> `queued`
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
  "from": "in_progress",
  "to": "review",
  "phase": "consensus -> awaiting_approval",
  "trigger": "all_approve",
  "actor": "system",
  "idempotency_key": "abc123-review-1707734400"
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

### Status Alignment

All statuses referenced in this spec are canonical — see [[aops-core/skills/remember/references/TAXONOMY.md#status-values-and-transitions]]. The workflow uses: `inbox`, `queued`, `in_progress`, `merge_ready`, `review`, `done`, `blocked`, `paused`, `someday`, `cancelled`. Supervisor sub-phases (decomposing, consensus, debate) live in the task body as annotations, not as status values.

### New Fields

- `unblock_condition`: string (for `blocked`)
- `diagnostic`: string (for tasks that halted on unrecoverable error)
- `pr`: int (for `merge_ready`)
- `issue`: int (for linking GitHub issues)
- `pr_url`: string (for `merge_ready`)
- `worker_id`: string (for `in_progress`)
- `approval_type`: enum (for `review` phase-3 tasks)
- `decision_deadline`: timestamp (for `review` phase-3 tasks)
- `retry_count`: int
- `depth`: int (for decomposition tracking)

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
