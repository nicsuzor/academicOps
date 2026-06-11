---
id: supervisor-c41c35d6
name: supervisor
description: >
  The single authoritative supervision process for any delegate-and-verify
  work — epic-level task supervision (stateless tick driven by `/loop`, state
  in the epic body) AND conversational orchestration of background workers
  (`/goal` "don't get involved yourself, make sure it gets done", `/dogfood`).
  Junior MUST invoke this skill for supervision; never hand-roll it inline.
triggers:
  - "supervise"
  - "supervisor"
  - "shepherd"
  - "coordinate epic"
  - "get these done"
  - "make sure it gets done"
  - "don't get involved yourself"
  - "delegate this and verify"
  - "supervise these agents"
  - "dogfood"
modifies_files: true
needs_task: false
mode: iterative
domain:
  - operations
---

# Supervisor — The Supervision Process

This skill **is** the framework's supervision process. There are two modes; the discipline below
is identical across both.

- **Epic-tick mode** — own a PKB epic across `/loop` ticks; cross-tick state lives in the epic body.
- **Conversational orchestration mode** — run as the main conversation agent delegating to
  background workers (`/goal` "don't get involved yourself, make sure it gets done", `/dogfood`),
  with no epic/polecat; state lives in the conversation thread.

## When to Invoke (mandatory)

Junior (and any orchestrator) **MUST run supervision through this skill** — never hand-rolled in
the main conversation — whenever delegating work and verifying it gets done. This includes the
conversational orchestrator case: a `/goal` that says "delegate this, don't get involved
yourself, make sure it actually gets done", a `/dogfood` run, or any delegate-and-verify loop
over background `Agent()` workers. "I'm just the conversational orchestrator" is **not** an
exemption — that is exactly when this skill is required. Hand-rolling supervision inline is how
confident-but-unproofed verdicts and single-part PRs reach the user.

## Holding Delegated Work to Proof (read first)

Whatever the mode — an epic tick here, a program tick, or running as the main conversation
agent who delegates everything and verifies it — the supervisor's value is **not trusting any
single agent**: proof claims, isolate confounds, and never relay a conclusion you have not made
falsifiable. The full discipline is canonical in
[[instructions/holding-work-to-proof.md]]. The non-negotiables:

- **Proof, not claims.** A change is not a fix until a runtime observation confirms the
  user-facing behaviour against an acceptance gate you stated _before_ dispatch. "Tests pass"
  is never the gate for a behaviour bug.
- **The confound rule.** A verdict that blames anything you don't own ("platform bug",
  "upstream", "external blocker") is not believable — and you must not relay it — until a
  clean-room differential control (vanilla setup + positive control) has ruled out our own
  code/config. Convergent confidence from several agents is **not** that control. This applies
  to your _own_ relayed conclusions most of all.
- **Don't trust convergence.** Cross-check each worker's strongest evidence (not its summary);
  when agents contradict, adjudicate with methodology-independent evidence instead of picking a
  side.
- **Structured handback.** Every brief requires a capped verdict (`VERDICT / CLAIM / GATE /
  EVIDENCE-pointers / CONFIDENCE / CONFOUND CHECK`); read that, not the narrative dump — your
  context is the bottleneck.

## Conversational Orchestration Mode

When you reach this skill from a `/goal` / `/dogfood` "delegate this, don't get involved
yourself, make sure it gets done" — there is no epic task or polecat. The mechanics differ from
the epic tick; the discipline above does not.

- **Workers**: background `Agent(subagent_type=…, run_in_background=True)` calls (general-purpose
  for build/investigate, `marsha` for runtime QA). Results arrive as `<task-notification>`.
- **State lives in the conversation thread**, not an epic body. Keep a running ledger in your
  messages: each work item, its acceptance gate, and its current verdict. `needs_task` is off for
  this mode — do not invent an epic just to satisfy a precondition.
- **You cannot steer a running background worker** (no live message channel). So **front-load
  every brief**: the falsifiable acceptance gate (§1), the known PKB/prior intelligence so it
  doesn't re-derive (§4), the explicit "escalate, don't fake-pass" instruction (§5), and the
  structured handback contract (§6). A good brief is your only steering wheel; if a worker is
  mis-briefed mid-flight, **stop it and relaunch** rather than letting it burn its context.
- **Read each deliverable through its output file** (Read/grep the parts you need); never absorb
  a multi-thousand-token narrative into your turn just to lift a one-line verdict.
- **Preload predictable tool schemas once** (task get/update, memory create, `TaskStop`,
  `Monitor`) — repeated `ToolSearch` and parameter-shape retries are pure context waste.
- **When the work produces code/PRs**, the [Draft PR Lifecycle Contract](#draft-pr-lifecycle-contract-firm-policy)
  still applies: one shared-branch draft PR, promoted to ready only when all the delegated work
  has landed.
- **Reporting**: every status to the user is sourced and confidence-rated; correct your own prior
  conclusions out loud; escalate genuine frontiers (auth-gated checks, human judgment) instead of
  manufacturing a pass.

## Reporting Posture

Operate in **decide-and-report** mode. Exit in one of three states:

- **Silent**: No user-facing output. Commit/push checkpoint advances the tick.
- **`[ATTN]` block**: Emit a single YAML block (see [User Attention Notification](#user-attention-notification)) for decisions requiring explicit user authorization.
- **Halt summary**: Terminal state reached. Emit a one-line summary in plain English.

### Escalation Criteria

Escalate only if:

1. Action is irreversible or modifies external systems without authorization.
2. Involves methodology, citation, or claims published under the user's name.
3. No defensible default exists.
4. The Emergency Brake fires.

## Per-Tick Checklist

Execute the loop exactly once per tick:

1. **ORIENT**: Retrieve epic task body using `mcp__pkb__get_task(<epic-id>)`.
2. **BRAKE**: Apply [Emergency Brake](#emergency-brake) to `## Pattern Memory` and `## Work Items`. If triggered, halt epic and exit.
3. **DECIDE**: Invoke subagent(s) to obtain a structured verdict. Chaining is permitted only for compose-then-dispatch (compose-agent followed by fresh dispatch-agent).
4. **ACT**: Validate verdict shape. Execute Bash command, file task via `mcp__pkb__create_task`, or exit. If verdict is malformed, append `verdict_fail` to Pattern Memory and exit.
5. **CHECKPOINT**: Append new Pattern Memory row(s) to the epic body, commit, and push.

## Prohibited Main Agent Actions

Do not:

- Proactively scan files, diffs, transcripts, or run test probes (rely on subagent verdicts; only cheap local environment status checks like `gh auth status` are permitted).
- Author code edits or fixes.
- Persist state outside the epic body.
- Prompt the user if a defensible default exists.
- Modify or expand the verification brief.
- Evaluate visual or QA artifacts directly (delegate to `marsha`).

## Subagent Contracts

### Egress Constraints

Anonymize PKB-derived information (titles, IDs, project names) before writing to public PRs, commits, issues, or verification briefs. Use priority class, due-date bucket, status, count, or masked identifiers (`task-XXXX`).

### pauli — Preflight & React

- **Role**: Determine next action, handle worker exits, and react to verification failures.
- **Verdict Shape**: A single paragraph specifying exactly one action:
  - `dispatch <worker> on <task-id> in <project>`
  - `brief composed on <task-id>`
  - `file fix-task <title> under <parent>`
  - `halt: <reason>`
- **Verification Brief Assembly**:
  - Read original brief/spec and `## Fitness Rubric`.
  - Output one paragraph containing: artifact location/link + goal + spec link.
  - Do not include history, reviewer notes, dimensions, or manual check steps.
  - Halt if `## Fitness Rubric` is missing for user-facing artifacts.

### marsha — Verify (Review Surface)

- **Role**: Review deliverables for work items.
- **Review Surface Shift**:
  - **Cohesive Single-PR-Epic (Default)**: The supervisor review surface shifts from PR-per-task to **single-PR-at-end**. The supervisor does **NOT** run `marsha` verification on separate PRs or individual work items as each intermediate worker finishes. Instead, intermediate tasks are verified using local outcome-based verification (checking remote commit existence and inspecting the diff on the shared branch). Once verified, they are transitioned to `merge_ready` to unblock dependent tasks. The supervisor invokes `marsha` to review exactly **ONE** cumulative PR when the final stage promotes it.
  - **Standalone / Independent Tasks**: Keep the legacy branch-per-task behavior and verify each task's PR individually.
- **Verdict**: PASS, FAIL <reason>, or REVISE <reason>.

| Verdict    | Action                                                     |
| :--------- | :--------------------------------------------------------- |
| **PASS**   | Mark item `merge_ready`; checkpoint                        |
| **FAIL**   | Call pauli (`role=react`, context=`marsha-fail: <reason>`) |
| **REVISE** | File verification subtask; checkpoint                      |

## Compose-then-Dispatch Separation

- The agent authoring a brief must not dispatch against it (agent-identity separation).
- If the brief was modified during the tick, Pauli must output `brief composed on <task-id>`. The main agent must persist the brief, then invoke a fresh subagent context (dispatch-agent) to validate and emit the `dispatch` verdict.
- If the brief is stable PKB content, Pauli emits `dispatch` directly.

### Verdict Structural Guard

Verify verdicts satisfy:

- Contains exactly one action.
- Internally consistent (no conflicting status/action).
- Grounded in epic body states.
  If validation fails, append `verdict_fail` to Pattern Memory and exit.

## Cohesive Single-PR-Epic Pattern (Default)

The framework defaults to the **cohesive single-PR-epic pattern** for all epics whose subtasks are meant to land together. The only exception is when subtasks must genuinely ship and be deployed independently, in which case they keep the legacy branch-per-task behavior. This default pattern coordinates development on **ONE shared branch backing ONE draft PR**.

### Live Mechanism (PR #1749 / aops-613690b5)

This pattern is executable today via the live shared-branch mechanism:

- **`is_shared_branch` Detection**: The manager automatically detects shared branches by looking for custom branch overrides. If the branch name does not match the default `polecat/task-<task-id>` pattern (e.g. `polecat/epic-<epic-id>`), it is treated as a shared branch.
- **Cooperative Sync**: Workers on a shared branch perform cooperative pulls and rebases (`git fetch` followed by `git rebase origin/<branch-name>`) to integrate other workers' in-flight commits rather than resetting to main.
- **Force-with-lease**: Push operations use `--force-with-lease` to push changes to the shared branch, accepting a low-concurrency contract.
- **No Deletion**: Shared branches bypass staleness and nuke-delete cleanup sequences, preserving in-flight contributions.

### Dispatch and Concurrency Rules

1. **Shared Branch Default**: Every worker dispatched for a subtask of a cohesive epic must use the exact same branch name via the override flag: `--branch polecat/epic-<epic-id>`.
2. **Decomposition Structure**:
   - The epic must be decomposed into **parallel-able units** (which have no inter-dependency and can execute concurrently on the shared branch) and **sequential-dependency units** (which carry explicit `depends_on: [<id>]` edges).
   - The supervisor dispatches parallel units concurrently, while sequential units are blocked until their predecessor tasks are marked complete.

### Draft PR Lifecycle Contract (firm policy)

**One epic ships as ONE pull request, and it stays a DRAFT until every task on the shared branch has landed its commits. Only then does the supervisor flip it to ready (live).** No per-task / single-part PRs reach the merge pipeline or the user's attention — they consume review attention and CI resources for a fraction of an epic. This is policy now, not an aspiration.

1. **Draft until all commits are up**: The single shared-branch PR remains a draft for the entire life of the epic. Every work item must be `done` (its commits present on `polecat/epic-<epic-id>`) before the supervisor promotes. A draft PR with outstanding work items is the **normal, expected** mid-epic state — do not promote early to "show progress".
2. **Final-stage promotion is the only flip**: The supervisor's sole PR-state action is `gh pr ready` at the final-stage promotion, gated on: all work items `done`, the cumulative diff verified by exactly one `marsha` pass (see [marsha — Verify](#marsha--verify-review-surface)), and no open blockers. Promotion is a supervisor decision, never a worker action.
3. **No Worker-Created PR**: Workers never create PRs. The single PR materialises automatically when the first worker on the shared branch finishes (`gh pr create --head polecat/epic-<epic-id>`, NOT a worker call); the supervisor neither hand-creates it nor instructs a worker to. The merge gate throughout is **branch protection** — the PR cannot merge without Nic's per-SHA `APPROVED` review regardless of draft/ready status, and no agent ever simulates that signal.
4. **Enforce draft on creation (known mechanism gap)**: Polecat appends `--draft` only `if is_partial` (`polecat/finalize.py:642-645`), so the auto-finish FULL-completion path (`cli.py:5366-5372`) can create the PR **READY**. Until [[aops-9f07c557]] lands the `is_shared` draft carve-out, the supervisor MUST compensate: immediately after the PR first materialises, assert it is a draft (`gh pr ready --undo` / re-create as draft if it came up ready), and keep it draft until the final-stage promotion. A shared-epic PR that is live before all work items are `done` is a policy violation to be corrected, not left.
5. **Push Conflicts and Failures**: If a worker's push fails (e.g. `--force-with-lease` rejected due to concurrent pushes on the shared branch), the worker must run `git pull --rebase` to integrate cooperative changes and retry. If a rebase or push conflict cannot be resolved automatically, the supervisor must transition the task to `blocked` and escalate to Pauli.

## Canonical Dispatch Commands

```bash
# Local dispatch
uv run --project ~/src/academicOps polecat run -t <task-id> -p <project> --branch polecat/epic-<epic-id> --model <name>
```

- `--model <name>` is the canonical flag. Use `--model claude` (config-default), `--model opus` (Claude family alias), or `--model gemini-3.1-pro-preview` for Gemini. `--opus` is not a valid flag and will error — use `--model opus`.

## Emergency Brake

Evaluate `## Pattern Memory` (last 8 rows) and `## Work Items`:

| Rule                  | Trigger Condition                                          | Action                                                  |
| :-------------------- | :--------------------------------------------------------- | :------------------------------------------------------ |
| **Recurring failure** | Same `*_fail` or `*_halt` class appears ≥3× in last 8 rows | Halt epic; status `review`; reason `recurring: <class>` |
| **Stalled workers**   | ≥2 work items `in_progress` with last activity > 4h ago    | Halt epic; status `review`; reason `stalled workers`    |

Halt resets only when epic status is set back to `queued`. `partial` releases do not trigger the stalled worker rule.

## Pattern Memory Format

Append one row per tick, capped at last 16 rows.

```markdown
## Pattern Memory

| Tick (ISO)           | Decision                    | Class       | Notes               |
| :------------------- | :-------------------------- | :---------- | :------------------ |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | dispatch_ok | preflight clean     |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | verify_fail | tests red on docker |
```

Valid Classes: `dispatch_ok`, `dispatch_halt`, `verify_pass`, `verify_fail`, `react_filed_fix`, `react_halt`, `brake_fired`, `verdict_fail`.

## Design Principles

- **Task File Is the Only State**: Persist all status inside the epic body (`## Pattern Memory`, `## Work Items`, `## Supervisor Log`).
- **Halt-on-Substitute**: Halt if worker type, deliverable type, target repository, or scope limits change. Do not auto-substitute.
- **Drive-by Fix Policy**: Bundle unrelated trivial fixes only if blocking, obvious, and describable in one sentence. Otherwise, file a separate task.
- **Keep the Pipe Flowing**: Delegate decomposition and planning to workers. Restrict supervisor concurrency dynamically based on rate limits.
- **Intent Authority**: When filing or decomposing tasks, leave `priority` at the uncurated default band — never originate a non-default band from importance or urgency. Only Nic sets intent, by express per-request instruction. Canonical rule: [[framework-conventions-summary#intent-authority]].
- **PR Body Hygiene**: PR bodies describe the change for the reviewer — never carry do-not-merge / merge-gate / "awaiting Nic" banners. Branch protection is the enforced gate. Canonical rule: [[framework-conventions-summary#pr-body-conventions]].
- **Engineering Integrity**: Failing tests/validations must be resolved, not bypassed.
- **Confound Rule**: Never relay an "external blocker / not our code" verdict until a clean-room differential control has ruled out our own code as the confound. Canonical: [[instructions/holding-work-to-proof.md]].
- **Critic Gate**: High-risk tasks must undergo preflight validation by Pauli before dispatch.
- **Academic Integrity**: surfaced decisions published under the user's name require human confirmation.

## Phases

| Phase          | Subagent | Execution                                                                   |
| :------------- | :------- | :-------------------------------------------------------------------------- |
| **Orient**     | (none)   | Read epic body, run brake, select phase.                                    |
| **Decompose**  | pauli    | Propose subtasks; run RBG axiomcheck. Set `superseded_by` on retired tasks. |
| **Review**     | (none)   | Halt; await human promotion to `queued`.                                    |
| **Dispatch**   | pauli    | Preflight brief, execute dispatch or chain compose/dispatch.                |
| **Pre-verify** | pauli    | Assemble minimal brief (artifact, goal, spec link).                         |
| **Verify**     | marsha   | Run validation. Return PASS, FAIL, or REVISE.                               |
| **React**      | pauli    | Recommend fix-task or halt after FAIL.                                      |
| **Halt**       | (none)   | Terminal state reached; emit summary and exit.                              |

## Deliverable Subworkflows

| Deliverable Type | Subworkflow                       | Status |
| :--------------- | :-------------------------------- | :----- |
| **Code change**  | [[instructions/code-deliverable]] | active |

## Status Display Surfaces

Read-only projections. Do not write local JSON tracking files.

- `gh pr list` / `gh pr checks`
- `gh run list`
- `$AOPS_SESSIONS/tasks.json`
- `$AOPS_SESSIONS/state/pr-state.json`
- GitHub Issues with `halt` label
- `docker events`

## User Attention Notification

Emit a single fenced YAML block for user attention when escalation conditions are met.

```
[ATTN]
---
id: <epic-id>:<tick-sequence>
urgency: now | today | whenever
action_required: decision | review | info
one_line: <=80-char summary
context_ref: <task-id | PR-url | issue-url>
dismiss_if: <one-line condition under which this no longer needs attention>
suggested_response: <the supervisor's default if user says "you decide">
---
```

All text fields (`one_line`, `suggested_response`) must use plain English. Push `one_line` to slack/discord/email only if `urgency` is `now` or `today` and `action_required` is `decision`.

## Multi-Tick Supervision (notify-watch)

In interactive sessions, arm the Docker events Monitor on the first polecat dispatch to tick on event exits.

### Local Monitor Command

```
Monitor(
  description: "polecat exits",
  persistent: true,
  command: "while true; do docker events --filter event=die --filter 'name=polecat-' --format '{{.Time}} {{.Actor.Attributes.name}} exit={{.Actor.Attributes.exitCode}}'; sleep 2; done"
)
```

Filter out crew containers by checking container env for `POLECAT_CREW_NAME`. Stop the monitor using `TaskStop` once in-flight tasks resolve.

### Mechanism Selection

| Situation             | Mechanism                                  |
| :-------------------- | :----------------------------------------- |
| Single worker outcome | Bash `run_in_background` with polling loop |
| Async PR states       | `Monitor` on `gh pr checks`                |
| Idle / fallback       | `ScheduleWakeup` (>= 1800s)                |
| Interactive session   | `Monitor` on `docker events`               |

## Lifecycle Trigger Hooks

| Hook          | Trigger       | What it does                             |
| :------------ | :------------ | :--------------------------------------- |
| `queue-drain` | cron / manual | Starts supervisor session.               |
| `stale-check` | cron / manual | Resets timed-out tasks.                  |
| `pr-merge`    | James         | James closes completed tasks post-merge. |

## Task Assignment & Handover

- Assign tasks to appropriate worker; never to humans unless deciding a binary choice.
- Always leave a follow-up task when releasing mid-flow (`mcp__pkb__append` / `mcp__pkb__release_task`).

## Known Limitations

- Gemini `429 QUOTA_EXHAUSTED` is treated as a transient rate-limit (typically a 45-minute timeout), not a hard quota lockout.
- Pauli diagnosis tree for Gemini code 1 exits:
  1. Task ran > 45 minutes -> Decompose.
  2. Stuck in loop -> File fix-task, re-dispatch.
  3. Real 429 rate limit -> Wait and re-dispatch.
  4. Other -> Re-dispatch immediately.
- Do not substitute Gemini with Claude automatically (Halt-on-substitute).
