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

This skill **is** the framework's supervision process at every scale. The discipline below is
identical across all three contexts; only the unit of state changes: **Epic** (one PKB epic,
cross-tick state in the body), **Portfolio/Release** (many epics, state in release task body),
and **Conversational orchestration** (background `Agent()` workers, ledger still opened). There
are no deterministic halt brakes: halt, escalate, and promote by **judgment** on the proof
discipline below — not by row counters.

## When to Invoke (mandatory)

Junior and any orchestrator **MUST run supervision through this skill** — never hand-rolled in
the main conversation — whenever delegating work and verifying it gets done. This includes
`/goal` "delegate this, don't get involved yourself, make sure it actually gets done", `/dogfood`
runs, and any delegate-and-verify loop over background workers. "I'm just the conversational
orchestrator" is **not** an exemption.

For universal dispatch rules (expand terse instructions, pre-dispatch gates, surface variants):
see [[references/dispatch-rules]] and [[instructions/worker-dispatch]].

## Holding Delegated Work to Proof

Core discipline — applies **in every mode, on every tick**. Your value is not trusting any
single agent: proof claims, isolate confounds, never relay a conclusion you have not made
falsifiable. Posture: **supervise, don't do.** Hold the conclusion, not the file dumps; hand
bulk reading to the cheap summariser agent (§7) — never absorb a 30k narrative to lift a
one-line verdict.

**§1 — Orient before the FIRST dispatch (mandatory, no exceptions).** Four steps: (1) PKB
semantic search — prior diagnoses, recorded harnesses, related tasks, known confounds; (2)
prior-art sweep — open and merged PRs/branches; (3) identify the **SANCTIONED QA harness** —
refuse ad-hoc substitutes; HALT and `[ATTN]` Nic if none designated (a worker never invents the
gate it's judged by); (4) cross-vendor surface → **fetch vendor's authoritative docs first** —
reverse-engineering is a fallback only.

**§2 — Proof, not claims; state the acceptance gate up front.** A change is not a fix until a
**runtime observation** confirms user-facing behaviour. State the falsifiable acceptance gate
before dispatching — the observable that must be true in a real run. "Tests pass" is never the
gate for a behaviour bug.

**§2a — Capstone = done.** Final acceptance is ONE check with all clauses true at once: the
**exact previously-failing user-facing check** (supervisor supplies it from the ledger — capstone
agent does not reconstruct it); on a **fresh instance**; by a **non-implementer**; with the
**sanctioned harness**; **hallucination ruled out** by byte-matching observed output to source.
See [[references/subagent-contracts#marsha--verify-review-surface]] for brief composition.

**§3 — The confound rule.** A verdict blaming anything you don't own — "platform," "upstream,"
"external" — is not believable until a **clean-room isolation** proves it: reproduce with _our_
contribution removed (vanilla, plugin-free) plus a **positive control** in the same harness.
Derive the control from the **authoritative spec, never by copying the suspect**. Convergent
confidence is not the control — N agents sharing one confound is worth nothing.

**§4 — Don't trust convergence.** Independently QA each worker's strongest claim. When workers
contradict, adjudicate with methodology-independent evidence; treat a tidy, confident narrative
as a prompt to find the missing control, not as closure.

**§5 — Catch mis-briefed workers early; never pre-seed skip permission.** A worker re-deriving
known intelligence is wasted context — stop and relaunch with a surgical brief. Front-load every
brief (gate + known intelligence + "escalate, don't fake-pass" + handback contract) — you usually
**cannot steer a running background worker**. State every assumption as a **testable hypothesis**
("check whether X"), never as licence to skip ("you likely can't test X, so escalate").

**§6 — Report up honestly.** Every claim carries a source and confidence level — "high
confidence" is a promise you proofed it. Correct your own prior conclusions out loud and supersede
the PKB record. Escalate genuine frontiers; **never fake-pass**.

**§7 — Context-economy contract (mandatory, every mode).** (a) **Capped structured handback,
every brief** — require the worker to end with VERDICT/CLAIM/GATE/EVIDENCE/CONFIDENCE/CONFOUND
CHECK; read _that_, not the narrative (format: [[references/subagent-contracts#worker-handback-format]]).
`CONFOUND CHECK: NOT RUN` blocks relay — commission the control first (§3). (b) **Cheap
summariser agent** for all bulk reading — never absorb a 30k narrative to lift a one-line verdict.
(c) **Ledger lives in the epic body — always open an epic node**, even in conversational mode;
chat is not durable state.

**One-line test before reporting:** _Have I proofed this against a falsifiable gate? If it blames
anything I don't own — has a clean-room control ruled out our code? If not, I'm relaying a claim,
not a finding._

## Conversational Orchestration Mode

Same proof discipline; mechanics differ: workers are background
`Agent(subagent_type=…, run_in_background=True)` calls; results arrive as `<task-notification>`.
Front-load every brief (§5) — you cannot steer a running worker. Still open an epic node for the
ledger. When work produces code/PRs, the one-epic-one-PR pattern applies unchanged:
see [[references/cohesive-pr-epic]].

## Portfolio / Release Supervision

When the goal spans **many epics**: advance **ONE epic per tick** — never two workers on the
same task-id (concurrent worktree creation races the worktree-lock). State lives in the release
task body under `## Constituent Epics` and `## Escalations`. File missing epics. The premise gate
still binds at every dispatch. **Terminal**: when every epic is at its review surface — set
release task to `review`, write N items to `## Escalations`, stop. That is the correct end of an
autonomous loop. See [[references/supervision-mechanics#phases]] for per-phase mechanics.

## Reporting Posture

Operate in **decide-and-report** mode. Exit in one of three states:

- **Silent**: No user-facing output. Commit/push checkpoint advances the tick.
- **`[ATTN]` block**: Emit a single YAML block (see [[references/supervision-mechanics#user-attention-notification]]) for decisions requiring explicit user authorisation.
- **Halt summary**: Terminal state reached. Emit a one-line summary in plain English.

### Self-Arming the Loop

Supervision is a **stateless tick** — one invocation does one tick, by design, so
context stays small (the cross-tick state lives in the task body, not in a
long-running context). The recurrence is supplied externally by `/loop`. But a
user who types `/supervisor <id>` once should not get one tick and silence — so
**when invoked interactively and the tick did not reach a terminal state, arm the
next tick yourself**:

- After the CHECKPOINT step, if the exit state is **Silent** or **`[ATTN]`**
  (i.e. work remains and you are not halting), call `ScheduleWakeup` with the same
  `/supervisor <id>` invocation as the `prompt` so the loop continues. Use a
  delay in the idle range (≈1200–1800s) — see
  [[references/supervision-mechanics#mechanism-selection]], where `ScheduleWakeup`
  is the sanctioned idle/fallback wait mechanism.
- **Stop self-arming at the terminal state** (Halt summary): omit the
  `ScheduleWakeup` call so the loop ends cleanly. This is the correct end of an
  autonomous run — do not keep scheduling once every epic is at its review
  surface.
- **Do not double-arm.** If this invocation was already fired by an external
  `/loop` or a cron schedule, that mechanism re-fires the next tick — do not also
  schedule one, or ticks will stack.

### Escalation Criteria

Escalate only if: (1) action is irreversible or modifies external systems without authorisation;
(2) involves methodology or claims published under the user's name; (3) no defensible default
exists; (4) **your judgment says stop** — same failure keeps recurring, workers are stalled, or
you cannot proof a verdict. No row counter; if it smells stuck, halt and escalate.

## Per-Tick Checklist

Execute exactly once per tick:

1. **ORIENT**: Read task body (`mcp__pkb__get_task(<id>)`) and ledger. Before the _first_
   dispatch: run the §1 orient checklist — PKB search, prior-art sweep, sanctioned-harness
   identification, vendor-docs fetch for cross-vendor surfaces. Escalate if orient is incomplete.
2. **JUDGE**: If the same failure recurs, workers are stalled, or the premise no longer holds —
   **halt and escalate**. Your call, not a counter.
3. **DECIDE**: Invoke subagent(s) for a structured verdict. Chaining: compose-then-dispatch only
   (see [[references/subagent-contracts#compose-then-dispatch-separation]]).
4. **ACT**: Sanity-check the verdict (one coherent action, consistent with the body). If it
   doesn't hold up — note why in the ledger and exit. Otherwise execute.
5. **CHECKPOINT**: Append a ledger row to the task body, commit, and push. Then,
   if invoked interactively and not at a terminal state, self-arm the next tick
   (see [[#self-arming-the-loop]]).

## Prohibited Main Agent Actions

Do not:

- Proactively scan files, diffs, transcripts, or run test probes (only cheap local env checks
  like `gh auth status` are permitted).
- Author code edits or fixes.
- Persist state outside the epic body.
- Prompt the user if a defensible default exists.
- Modify or expand the verification brief.
- Evaluate visual or QA artifacts directly (delegate to `marsha`).

## References

- **Dispatch rules** (dispatch reflex, pre-dispatch gates, surface variants): [[references/dispatch-rules]] + [[instructions/worker-dispatch]]
- **Subagent contracts** (pauli, marsha, handback format, compose-then-dispatch): [[references/subagent-contracts]]
- **Cohesive single-PR-epic** (shared branch, concurrency, one-epic-one-PR, dispatch commands): [[references/cohesive-pr-epic]]
- **Supervision mechanics** (multi-tick, status surfaces, hooks, pattern memory, ATTN template, design principles, phases): [[references/supervision-mechanics]]
