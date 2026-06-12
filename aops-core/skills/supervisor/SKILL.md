---
id: supervisor-c41c35d6
name: supervisor
description: >
  The single authoritative supervision process for any delegate-and-verify
  work — at every scale: one epic, a release spanning many epics (portfolio),
  or conversational orchestration of background workers (`/goal` "don't get
  involved yourself, make sure it gets done", `/dogfood`). Stateless tick driven
  by `/loop`; cross-tick state lives in the task body. Junior MUST invoke this
  skill for supervision; never hand-roll it inline.
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
  - "ready the release"
  - "drive the release"
  - "portfolio supervision"
modifies_files: true
needs_task: false
mode: iterative
domain:
  - operations
---

# Supervisor — The Supervision Process

This skill **is** the framework's supervision process, at every scale. The discipline below is
identical across all three contexts; only the unit of state changes:

- **Epic** — own one PKB epic across `/loop` ticks; cross-tick state lives in the epic body.
- **Portfolio / release** — drive a release-level goal spanning many epics: advance ONE epic per
  tick, surface escalations, file missing epics. State lives in the release task body
  (`## Constituent Epics`, `## Escalations`). See [Portfolio / Release Supervision](#portfolio--release-supervision).
- **Conversational orchestration** — run as the main conversation agent delegating to background
  workers (`/goal` "don't get involved yourself, make sure it gets done", `/dogfood`); still open
  a task node for the ledger (chat is not durable state).

There are no deterministic halt brakes or merge-gate mechanics in this process: you are a trusted
agent. Halt, escalate, and promote by **judgment**, on the proof discipline below — not by row
counters. Merge gating is owned by infrastructure (branch protection + Nic's per-SHA approval);
you never simulate or manage it.

## When to Invoke (mandatory)

Junior (and any orchestrator) **MUST run supervision through this skill** — never hand-rolled in
the main conversation — whenever delegating work and verifying it gets done. This includes the
conversational orchestrator case: a `/goal` that says "delegate this, don't get involved
yourself, make sure it actually gets done", a `/dogfood` run, or any delegate-and-verify loop
over background `Agent()` workers. "I'm just the conversational orchestrator" is **not** an
exemption — that is exactly when this skill is required. Hand-rolling supervision inline is how
confident-but-unproofed verdicts and single-part PRs reach the user.

## Holding Delegated Work to Proof

This is the supervisor's core discipline, and it applies **in every mode, on every tick** — a
single epic, a release of many epics, or running as the main conversation agent who delegates
everything and verifies it. It is not an optional extra and not a separate read. Your value is **not trusting
any single agent**: proof claims, isolate confounds, and never relay a conclusion you have not
made falsifiable — applied to the workers' claims **and to your own**. It is **dispatch-surface
independent** — identical whether workers are polecat containers or Agent-tool background
subagents; polecat mechanics elsewhere in this skill are one surface's implementation of the
generic step.

**Posture: supervise, don't do.** "Don't get involved yourself" is literal — delegate the work
(investigate, code, QA) to workers; your context is a scarce, principal-facing resource. Hold the
**conclusion**, not the file dumps: read a deliverable through its output file (grep/Read the
parts you need) and hand anything bulky to the cheap summarizer agent (§7) — never absorb a
30k-token narrative to lift a one-line verdict. This is the single biggest context leak.

**§1 — Orient before the FIRST dispatch (mandatory, no exceptions).** Dispatching before you
have the map costs full QA cycles and gets briefs killed and re-issued. Four steps:

1. **PKB semantic search** — prior diagnoses, recorded harnesses, related tasks, known confounds.
2. **Prior-art sweep** — open _and_ merged PRs/branches (`gh pr list --state all --search
   "<terms>"` + the branch list); a merged fix or in-flight branch rewrites the brief.
3. **Identify the SANCTIONED QA harness** and require it in the brief — refuse ad-hoc
   substitutes. It is recorded in the epic ledger's ORIENT output, populated from (i) the PKB
   search, (ii) the artifact's task/spec body, (iii) memory notes. **If that chain yields no
   designated harness, HALT and `[ATTN]` Nic to designate one** — a worker never invents the
   gate it is judged by.
4. **Cross-vendor surface → FETCH THE VENDOR'S AUTHORITATIVE DOCS first.** Reverse-engineering
   binaries/configs/strace is a fallback only. (The motivating bug was a deviation from a public
   docs page nobody had fetched for days.)

**§2 — Proof, not claims; state the acceptance gate up front.** A change is not a fix until a
**runtime observation** confirms the user-facing behaviour; code edits, green unit tests, "the
router emits X" are floor, not ceiling. Before dispatching, state the **falsifiable acceptance
gate** in the brief — the observable that must be true in a real run, and what would prove it
false. "Tests pass" is never the gate for a behaviour bug. A worker that reports success without
exercising the gate has not finished.

**§2a — Capstone = done.** Final acceptance is ONE check with all clauses true at once: the
**exact previously-failing user-facing runtime check** (the supervisor supplies it from the epic
ledger — the capstone agent does not reconstruct "what failing meant"); on a **fresh
instance/session**; by an agent who is **NOT the implementer**; with the **sanctioned harness**;
**hallucination ruled out** by byte-matching observed output to source (content that could only
come from the system under test, not echoed from the prompt). On the single-PR-epic surface this
is the one cumulative `marsha` pass at promotion (brief composition: [marsha — Verify](#marsha--verify-review-surface); marsha's own [[../verify/SKILL.md]] enforces the
fresh-instance / non-implementer / source-trace posture). Only this justifies promoting the PR to
ready; a miss means it is not done — record it in the ledger and send it back, never promote.

**§3 — The confound rule (the headline).** A verdict that blames anything you don't own —
"platform," "upstream," "external blocker," "agy/library/OS does X" — is **not believable and
must not be relayed** until a differential control has ruled out our own code/config:

- The control is a **clean-room isolation**: reproduce with _our_ contribution removed (vanilla,
  plugin-free, stock) plus a **positive control** in the same harness to prove it can detect
  success. Vanilla works ⇒ the fault is ours.
- **Derive the control from the AUTHORITATIVE SPEC, never by copying the suspect.** A control
  that imitates the suspect's config replicates its bug and "confirms" it. (Motivating incident:
  an adjudicator's sentinel hook copied our plugin's broken registration shape and _falsely
  confirmed a platform bug_; only the vanilla, docs-derived repro overturned it.)
- **Convergent confidence is not the control** — N agents sharing one confound is worth nothing.
  (Two workers + one QA agent agreed "platform no-op" with strace + sentinel proof, all wrong:
  every one tested _with our plugin installed_; the bug was our `hooks.json` shape. One vanilla
  control flipped it instantly.)
- This applies to your **own** relayed conclusions most of all. A worker verdict that blames what
  we don't own and arrives `CONFOUND CHECK: NOT RUN` is **not relayed** — note it in the ledger
  and commission the control first.

**§4 — Don't trust convergence.** Independently QA each worker's strongest claim, not its summary
— a "green" journal of the wrong evidence (PreToolUse `allow` records) does not prove the thing
in question (PreInvocation injection). When two agents contradict, **do not pick one**;
adjudicate with methodology-independent evidence (sentinel files + `strace -f` follow-forks),
naming the exact trap (`strace` without `-f` misses forked children). Treat a tidy, confident
narrative as a prompt to find the missing control, not as closure.

**§5 — Catch mis-briefed workers early; never pre-seed skip permission.** A worker re-deriving
known intelligence (a recorded harness, a merged fix) is wasted context — stop it and relaunch
with a surgical brief. You usually **cannot steer a running background worker**, so front-load
the brief (gate + known intelligence + "escalate, don't fake-pass" + handback contract); the
brief is your only steering wheel. State every assumption as a **testable hypothesis** ("check
whether X; if yes, run the check") — never as licence to skip ("you likely can't test X, so
escalate"). A stale "no-auth" assumption once made a worker punt the one check that mattered.

**§6 — Report up honestly.** Every claim to the principal carries a **source and confidence
level** — "high confidence" is a promise you proofed it (spend it only after §3–§4). **Correct
your own prior conclusions out loud** and supersede the record (PKB note/memory) so no agent
inherits a stale verdict. **Escalate genuine frontiers; never fake-pass** — hand over the exact
one-line check instead of manufacturing a green.

**§7 — Context-economy contract (mandatory, every mode).** The orchestrator's context is the
bottleneck (the motivating interactive session burned ~170k tokens):

- **Capped structured handback, every brief** — the worker ends with this and you read _that_,
  not the narrative:

  ```
  VERDICT: <PASS | FAIL | BLOCKED | NEEDS-PRINCIPAL>
  CLAIM: <one sentence — the conclusion>
  GATE: <the acceptance gate, and the observed result against it>
  EVIDENCE: <pointers — session id, log path, line refs — NOT pasted dumps>
  CONFIDENCE: <high|med|low> + <what single control/test would falsify this>
  CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
  ```

  `CONFOUND CHECK` is mandatory whenever the verdict blames what we don't own; `NOT RUN` ⇒ do not
  relay, commission the control (§3).
- **Cheap summarizer agent** for all bulk reading (large bodies, transcripts, log dumps): a
  haiku/sonnet general-purpose Agent-tool dispatch (or its `jr`/polecat equivalent), briefed
  _"read `<pointer>`, return the ≤N facts relevant to `<question>`."_ It reads the bulk so your
  context never does.
- **The ledger lives in the epic body — always open an epic node**, even when supervising from an
  interactive conversation with no pre-existing epic (chat context is not durable state).
  Mechanics: `mcp__pkb__create_task type=epic` seeded with the `## Work Items` / `## Pattern
  Memory` / `## Ledger` skeleton (see [Pattern Memory Format](#pattern-memory-format)); capture
  ORIENT findings into `## Ledger` and the failing observable into `## Work Items` on tick 1 —
  that is where the capstone (§2a) later reads the "exact previously-failing check."
- **Capped chat updates** — one short paragraph (verdict + next action) between phases, never a
  transcript replay. Preload predictable tool schemas once (task get/update, memory create,
  stop/monitor) to avoid `ToolSearch` / parameter-retry churn.

**One-line test before you report a conclusion:** _Have I proofed this against a falsifiable
gate, and — if it blames anything I don't own — has a clean-room control ruled out our code as
the confound? If not, I am relaying a claim, not a finding._

## Conversational Orchestration Mode

When you reach this skill from a `/goal` / `/dogfood` "delegate this, don't get involved
yourself, make sure it gets done" — there is no epic task or polecat. The **discipline above is
unchanged**; only these mechanics differ:

- **Workers** are background `Agent(subagent_type=…, run_in_background=True)` calls
  (general-purpose for build/investigate, `marsha` for runtime QA); results arrive as
  `<task-notification>`. The §7 context-economy contract still binds — front-load every brief
  (§5) because you cannot steer a running worker, and require the capped handback.
- **Still open an epic node for the ledger** (§7) — `needs_task` being off means you are not
  _required_ to be handed one, not that state may live in chat. Chat context is not durable
  state.
- **When the work produces code/PRs**, the [one-epic-one-PR pattern](#cohesive-single-pr-epic-pattern-default)
  applies unchanged: one shared-branch PR, promoted only when all delegated work has landed and
  the capstone passes.

## Portfolio / Release Supervision

When the goal spans **many epics** ("ready the release", "drive `<project>`"), you are the
top-level coordinator. The proof discipline above is unchanged; you simply operate one level up,
and you do **not** micromanage leaves — each epic runs its own supervision.

- **One epic per tick.** Each tick, advance the single most-blocking epic by one decision (its own
  supervision step). Never run two workers on the same task-id — concurrent worktree creation
  races the worktree-lock and container-name. Grow concurrency with more ticks, not more
  dispatches per tick.
- **State lives in the release task body** under `## Constituent Epics` (each epic + its status)
  and `## Escalations` (pending approvals, blocked epics, merge-ready PRs). Commit and push each
  tick. Surface only actionable items there — never worker threads or tool-call play-by-play.
- **File missing epics.** If a release requirement has no epic, create one parented under the
  release task and add it to `## Constituent Epics`.
- **Premise gate still binds** at every dispatch (here and in the epic step it drives): read the
  leaf body and judge whether it carries a genuine premise judgment; if not, bounce it to the
  promoter and spend no compute. This is an agent judgment by reading, never a field check
  ([[../remember/references/premise-gate.md]]).
- **Terminal: done-pending-Nic.** When every epic is at its review surface and the only remaining
  work is decisions/approvals/merges that are structurally Nic's, you are **autonomously complete
  — N items surfaced for Nic.** Set the release task to `review`, write the N items to
  `## Escalations`, and stop. This is not a failure; it is the correct end of an autonomous loop.

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
4. **Your judgment says stop** — the same failure keeps recurring, workers are stalled, or you
   cannot proof a verdict. There is no row counter; if it smells stuck, halt and escalate rather
   than burning more compute.

## Per-Tick Checklist

Execute the loop exactly once per tick:

1. **ORIENT**: Retrieve the task body (`mcp__pkb__get_task(<id>)`) and read the ledger. Before the _first_ dispatch on a problem, run the orient-before-dispatch checklist ([Holding Delegated Work to Proof §1](#holding-delegated-work-to-proof)): PKB search, prior-art PR/branch sweep, sanctioned-harness identification, and vendor-docs fetch for cross-vendor surfaces. Don't dispatch blind; if you can't complete orient, note it and escalate.
2. **JUDGE**: Read the ledger. If the same failure keeps recurring, workers are stalled, or the premise no longer holds, **halt and escalate** — your call, not a counter.
3. **DECIDE**: Invoke subagent(s) to obtain a structured verdict. Chaining is permitted only for compose-then-dispatch (compose-agent followed by fresh dispatch-agent).
4. **ACT**: Sanity-check the verdict (one coherent action, consistent with the body); if it doesn't hold up, don't act on it — note why and exit. Otherwise execute the action (Bash, file task via `mcp__pkb__create_task`, promote, or exit).
5. **CHECKPOINT**: Append a ledger row to the task body, commit, and push.

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
  - **Cohesive Single-PR-Epic (Default)**: The supervisor review surface shifts from PR-per-task to **single-PR-at-end**. The supervisor does **NOT** run `marsha` verification on separate PRs or individual work items as each intermediate worker finishes. Instead, intermediate tasks are verified using local outcome-based verification (checking remote commit existence and inspecting the diff on the shared branch). Once verified, they are transitioned to `merge_ready` to unblock dependent tasks. The supervisor invokes `marsha` to review exactly **ONE** cumulative PR when the final stage promotes it. That single cumulative pass IS the **capstone verification** ([Holding Delegated Work to Proof §2a](#holding-delegated-work-to-proof)). The marsha brief the supervisor composes MUST carry the three capstone specifics from §2a — the **sanctioned QA harness** (identified at ORIENT, never invented; if none is recorded, HALT and `[ATTN]`), the **exact previously-failing user-facing check** (supplied by the supervisor from the epic ledger, not reconstructed by marsha), and the **byte-match hallucination rule-out** — while `marsha`'s own [[../verify/SKILL.md]] enforces the fresh-instance / non-implementer / source-trace posture. A capstone the prompt could have produced without the system running is not a pass; record any miss in the ledger and send it back.
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

### Verdict Sanity Check

Before acting on a subagent's verdict, satisfy yourself it holds up: one coherent action,
internally consistent, grounded in the actual task-body state. If it doesn't, don't act on it —
note why in the ledger and exit. This is a read-and-judge, not a shape-validator.

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

### One Epic, One PR — promote at the capstone

**One epic ships as ONE pull request.** No per-task / single-part PRs reach the merge pipeline or
the user — they spend review attention and CI for a fraction of an epic. Your single PR-state
action is the **promotion at the end**: flip it ready once all work items are `done` and the
[capstone](#holding-delegated-work-to-proof) (the one cumulative `marsha` pass) is green. A PR
with outstanding work items is the normal mid-epic state — do not promote early to "show
progress".

You do **not** manage merge mechanics. The single PR materialises automatically when the first
worker on the shared branch finishes; workers never create PRs, and you never hand-create one.
Draft-vs-ready enforcement and the merge gate are **infrastructure's job** — branch protection
holds the line (no merge without Nic's per-SHA `APPROVED`), polecat handles draft creation. Don't
re-draft PRs, don't simulate approvals, don't add merge-gate banners to PR bodies. If a worker's
push conflicts on the shared branch it rebases and retries; if that can't resolve, set the task
`blocked` and escalate.

## Canonical Dispatch Commands

The discipline is dispatch-surface independent (see [Holding Delegated Work to Proof](#holding-delegated-work-to-proof)). The commands below are the
**polecat surface's** implementation; on the Agent-tool surface the same generic step (dispatch
a worker against a task on the shared epic branch with a capped-handback brief) is a background
subagent launch instead.

```bash
# Local dispatch (polecat surface)
uv run --project ~/src/academicOps polecat run -t <task-id> -p <project> --branch polecat/epic-<epic-id> --model <name>
```

- `--model <name>` is the canonical flag. Use `--model claude` (config-default), `--model opus` (Claude family alias), or `--model gemini-3.1-pro-preview` for Gemini. `--opus` is not a valid flag and will error — use `--model opus`.

## Pattern Memory Format

The ledger is your cross-tick memory, not a trigger. Append one row per tick (cap ~16, drop
oldest): the decision and its outcome, in plain terms, so the next tick — or a fresh you after a
`/loop` gap — can read what happened and judge what to do next. There is no fixed class
vocabulary and no row-counting brake; if a pattern of failure is building, **you** notice it on
read (Per-Tick step 2) and halt by judgment.

```markdown
## Pattern Memory

| Tick (ISO)           | Decision                    | Outcome / Notes                          |
| :------------------- | :-------------------------- | :--------------------------------------- |
| 2026-05-08T02:14:00Z | dispatch task-abc to claude | preflight clean                          |
| 2026-05-08T02:43:11Z | marsha FAIL on task-abc     | tests red on docker — re-dispatching fix |
```

## Design Principles

- **Task File Is the Only State**: Persist all status inside the epic body (`## Pattern Memory`, `## Work Items`, `## Supervisor Log`).
- **Halt-on-Substitute**: Halt if worker type, deliverable type, target repository, or scope limits change. Do not auto-substitute.
- **Drive-by Fix Policy**: Bundle unrelated trivial fixes only if blocking, obvious, and describable in one sentence. Otherwise, file a separate task.
- **Keep the Pipe Flowing**: Delegate decomposition and planning to workers. Restrict supervisor concurrency dynamically based on rate limits.
- **Intent Authority**: When filing or decomposing tasks, leave `priority` at the uncurated default band — never originate a non-default band from importance or urgency. Only Nic sets intent, by express per-request instruction. Canonical rule: [[framework-conventions-summary#intent-authority]].
- **PR Body Hygiene**: PR bodies describe the change for the reviewer — never carry do-not-merge / merge-gate / "awaiting Nic" banners. Branch protection is the enforced gate. Canonical rule: [[framework-conventions-summary#pr-body-conventions]].
- **Engineering Integrity**: Failing tests/validations must be resolved, not bypassed.
- **Confound Rule**: Never relay an "external blocker / not our code" verdict until a clean-room differential control has ruled out our own code as the confound. Full rule: [Holding Delegated Work to Proof §3](#holding-delegated-work-to-proof).
- **Critic Gate**: High-risk tasks must undergo preflight validation by Pauli before dispatch.
- **Academic Integrity**: surfaced decisions published under the user's name require human confirmation.

## Phases

| Phase          | Subagent | Execution                                                                   |
| :------------- | :------- | :-------------------------------------------------------------------------- |
| **Orient**     | (none)   | Read task body and ledger; judge whether to advance or halt; select phase.  |
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
