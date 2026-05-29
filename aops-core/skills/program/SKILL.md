---
name: program
type: skill
category: instruction
description: >
  Program / portfolio supervision — the autonomous top loop above /supervisor.
  "Ready the release" → discover and decompose the constituent epics → run
  /supervisor on each → surface only escalations + merge-ready PRs. Stateless
  tick driven by /loop; all cross-tick state lives in the program task body.
triggers:
  - "ready the release"
  - "get <project> ready"
  - "drive the release"
  - "program supervision"
  - "portfolio supervision"
  - "supervise the program"
modifies_files: true
needs_task: true
mode: iterative
domain:
  - operations
owner: junior
---

# Program / Portfolio Supervision — Stateless Tick

This is junior's **autonomous top loop**, one scope above `/supervisor`. Where `/supervisor` owns a single epic (one goal tree) from decomposition to the review surface, the program loop owns a **release-level goal that spans many epics**. Nic says "get aops ready for v0.4"; this loop discovers and decomposes the constituent epics, runs `/supervisor` on each, manages the portfolio, and surfaces **only escalations + merge-ready PRs** — never worker threads.

It is the resolution to the binding constraint (retro MF6, validated): the per-epic supervisor loop works end-to-end across an overnight run, but stops being useful the moment leaf tasks run out — it has historically emitted a hand-curated epic list for Nic to re-feed. The program loop removes that ceiling: **when leaves exhaust, the loop discovers and decomposes the next epic itself. Nic does not hand-feed.**

## Profile selection (WS1 contract)

This loop runs under the **`autonomous`** mode profile (`agents/junior.md` Layer 2). The profile selector is **who is the gate**: a program/portfolio drive is dispatched/overnight work where a review surface — not a person watching — catches mistakes. The loop therefore inherits the autonomous-profile bindings verbatim and does not restate them:

- **Surface only escalations + merge-ready PRs** to a durable digest, not worker threads to chat. (autonomous profile: "checkpoint to a durable store, not to chat".)
- **Never block on a question you can resolve yourself.** (autonomous profile.)
- **Recognise the legitimate stop** — "autonomously complete; N items surfaced for Nic" (the [done-pending-Nic terminal state](#terminal-states), below). (autonomous profile: "recognise a legitimate stop".)
- **Leave a cheap durable record** — the program body's `## Program Log` + per-epic `## Work Items`, committed at meaningful granularity.

When Nic is **live** in the chat, this is no longer a program-loop session — it is interactive supervision, and the `interactive` profile applies (delegate the execute/test loop, short turns, lead with the decision). The program loop is the _autonomous-profile_ embodiment specifically.

## How it sits above `/supervisor`

```
Nic: "ready the aops release"
        │
        ▼
   /program <program-task-id>        ← this skill (portfolio scope)
        │  discover constituent epics
        │  decompose when leaves exhaust
        ├──▶ /supervisor <epic-A>    ← per-epic loop (existing skill, unchanged)
        ├──▶ /supervisor <epic-B>
        └──▶ /supervisor <epic-C>
        │
        ▼
   digest: escalations + merge-ready PRs only
```

The program loop **never does epic-scope work itself** — it routes each epic to `/supervisor`, exactly as `/supervisor` never does worker-scope work itself but routes to polecat. Same routing decision, one scope up (`agents/junior.md` Layer 1: "supervisor / polecat / subagent are the same routing decision at different scopes").

## Per-tick checklist

The program is a **stateless tick** (same discipline as `/supervisor`). The main agent runs this loop **once** and exits. All cross-tick state lives in the program task body — no in-memory continuity is assumed.

**Canonical invocation:** `/loop 30m /program <program-task-id>`

1. **ORIENT** — `get_task(<program-task-id>)`. Read the body only: `## Program Log`, `## Constituent Epics`, and `## Escalations`.
2. **BRAKE** — apply the [Program Brake](#program-brake) against `## Program Log` (last 8 rows). If a rule fires, halt the program and exit.
3. **ASSESS PORTFOLIO** — determine the tick's single action by walking the [Tick Decision Order](#tick-decision-order). Exactly one action per tick.
4. **ACT** — execute that one action (advance an epic, decompose, discover, escalate, or reach a terminal state).
5. **CHECKPOINT** — append one `## Program Log` row, update `## Constituent Epics`, commit and push.

That is the whole loop. The next tick fires with a fresh context and re-reads the program body.

## Tick Decision Order

Walk these in order; take the **first** that applies; that is the tick's one action.

1. **Brake fired?** → halt the program (see [Program Brake](#program-brake)).
2. **An epic has a worker outcome to process** (a dispatched worker exited, a PR is merge-ready, a verify is pending)? → run **one `/supervisor` tick** on that epic. The per-epic loop owns the orient→decompose→dispatch→verify→react→halt cycle; the program loop just selects which epic gets the tick. This is the **dispatch trigger** — see [WS4 seam](#dispatch-trigger--the-ws4-seam).
3. **An epic is escalation/`review`/`blocked`** with a decision only Nic can make? → record it in `## Escalations` (do not re-run it) and move to the next epic. Surface via the digest, never inline.
4. **A constituent epic has exhausted its ready leaves** (all children done/merge-ready, but the epic goal is not met)? → **auto-decompose** it (see [Auto-decompose on leaf exhaustion](#auto-decompose-on-leaf-exhaustion)). This is the named critical-gap capability.
5. **The portfolio has no constituent epic for a known release sub-goal** (a release requirement with no epic tracking it)? → **discover and create** that epic (see [Epic discovery](#epic-discovery)).
6. **Every constituent epic is at its review surface or escalated, and the release goal is met or fully surfaced?** → reach a [terminal state](#terminal-states).

One action per tick keeps the loop lean (north star: junior's context is the scarce resource). Never chain epics in one tick; never run two `/supervisor` ticks in one program tick.

## Auto-decompose on leaf exhaustion

The critical capability (retro MF6, confirmed not optional): **when a constituent epic's ready leaves run out but its goal is not met, junior decomposes it itself rather than emitting a list for Nic to re-feed.**

Mechanism — this is supervisor-grade decomposition, delegated, not inlined:

1. Recognise exhaustion: `get_task_children(<epic-id>)` shows all children `done` / `merge_ready` / `cancelled`, yet the epic status is not `done` and its goal (epic body's stated outcome) is unmet.
2. **Do not decompose in the program main context.** Run **one `/supervisor` tick on that epic in its `Decompose` phase** — pauli proposes subtasks, RBG runs the mandatory axiom-check, the plan halts at the `Review` surface for human promotion (`ready` → `queued`). The program loop's job is to _trigger_ the decomposition tick, not to author the subtasks. (`agents/junior.md` Layer 3: re-decomposing epics when scope shifts is junior's to own; the _authoring_ is pauli's.)
3. If `/supervisor`'s decompose tick returns a plan that awaits human promotion, record it in `## Escalations` as `action_required: review` — the new subtasks are `ready`, and Nic promotes them to `queued` (the human-gated dispatch boundary, per `/pull` and TAXONOMY §Status Values). The program loop does **not** self-promote `ready` → `queued`; that boundary is Nic's.

So "Nic does not hand-feed epics" is true at the _discovery + decomposition_ level — junior finds the next epic and triggers its decomposition — while the `ready` → `queued` promotion gate stays human, preserving the existing dispatch boundary. This is the deliberate seam: auto-decompose removes the _re-feed_ tax without removing the _approval_ gate.

## Epic discovery

A release-level goal ("ready the aops release") rarely arrives with all its epics enumerated. The loop discovers them:

1. Probe the graph for release sub-goals not yet tracked by an epic: `task_search` on the release theme, `list_tasks(project=<project>, status=ready|queued|in_progress)`, and the program body's stated release criteria.
2. Where a release requirement has no epic, **file one** (`create_task` with `type: epic`, parented under the program task) and record it in `## Constituent Epics`.
3. Discovery is itself a tick action (decision-order step 5). Do not discover _and_ decompose _and_ dispatch in one tick — one action per tick.

Discovery uses the same graph-probe surface as the `autonomous`-profile state probe (`agents/junior.md` Layer 3: "probe before asking" — read the graph, don't ask Nic).

## Dispatch trigger — the WS4 seam

**The dispatch trigger lives at [Tick Decision Order](#tick-decision-order) step 2.** When a constituent epic has a ready leaf and a free concurrency slot, the program loop's action is to run one `/supervisor` tick that _chooses and dispatches_ that leaf to the right surface (polecat for shippable, subagent for triage). The program loop selects **which epic** gets the tick; `/supervisor` + pauli select **which leaf** and dispatch it.

This is the "advance the queue" residue the spec's `/pull` rework (WS4) folds in. The v0.4 claim that "polecats auto-claim queued work" was overstated (James #2): a polecat claims + runs a _dispatched_ task and ships a PR — something must still _choose and dispatch_ the next task. That chooser is this step.

**WS4 attachment (landed):** WS4 retired `/pull`'s self-execution semantics and folded its "choose the next ready task and dispatch it" residue here. `/pull` (`commands/pull.md`) is now a **thin one-shot alias** that performs exactly this decision — select the next ready task and route it to a surface — and then stops; it never executes the task inline. The program loop runs this trigger continuously across the portfolio; `/pull` runs it once by hand for a solo session. Both only ever _dispatch_.

## Fleet-concurrency primitives

A high-dispatch loop needs these immediately (retro thread 2 hit container-name + worktree-lock collisions when two workers took one task-id):

- **Distinct task-ids per worker.** Each dispatched leaf is a distinct PKB task with a distinct id; never dispatch two workers against the same task-id concurrently. The program loop tracks in-flight task-ids in `## Constituent Epics` (one row per epic, naming the in-flight leaf). Before triggering a dispatch tick on an epic, check that the target leaf's id is not already in-flight elsewhere in the portfolio.
- **Serialised worktree creation.** Polecat worktree creation must be serialised — two dispatches firing in the same instant race on worktree-lock and container-name. The program loop dispatches **one leaf per tick** (decision-order step 2 is a single action), which serialises creation by construction. Do not batch-dispatch multiple leaves in one tick to "save ticks" — that re-introduces the race. Concurrency is grown by _more ticks_, not _more dispatches per tick_ (`/supervisor`: "concurrency is the supervisor's discretion … one call at a time, with PKB writes between").
- **Concurrency cap is program judgment.** How many workers run concurrently across the portfolio is the program loop's judgment (same as `/supervisor`'s per-epic discretion), expressed as how aggressively it fills free slots across ticks. It does not belong in a CLI flag or a swarm wrapper (`/supervisor`: "dispatch is supervisor judgment — not a wrapper or a swarm").

## Terminal states

The program loop has a **legitimate stop** distinct from "done" and from "not done" (retro thread 2 F4 / thread 10: without it the goal-hook forces retries of things junior structurally cannot finish). Three terminal states:

| State                | Meaning                                                                                                                                                                                                                                            | Program status set |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| **complete**         | Release goal met; every constituent epic `done` or `merge_ready`.                                                                                                                                                                                  | `done`             |
| **done-pending-Nic** | Junior has done everything it can autonomously; the only remaining work is decisions/approvals/merges that are structurally Nic's (gated-repo approvals, genuine judgment calls). The loop is **autonomously complete; N items surfaced for Nic.** | `review`           |
| **halt**             | The [Program Brake](#program-brake) fired, or an epic returned a terminal infeasibility.                                                                                                                                                           | `blocked`          |

**done-pending-Nic is the load-bearing addition.** It is _not_ "not done" — junior is not failing to finish; it is _finished with its own scope_, and the residue is irreducibly human (the locked single approval is never junior's — see [Trust gate](#trust-gate-hardened--autonomous-shipping)). When the loop reaches done-pending-Nic it records `## Escalations` (the N surfaced items) and sets the program to `review`, then exits. It does **not** keep re-ticking to retry the human-only residue.

> **WS7 boundary.** This WS _defines_ the done-pending-Nic **state** and the conditions that reach it. The _exit mechanism_ — how the loop is permitted to terminate against the `/goal` continuation Stop hook without wedging at the handover gate — is **WS7 (gate composition & exit semantics)**. Until WS7 lands, a program loop reaching done-pending-Nic sets the program to `review` and stops ticking; if the Stop hook re-fires it, that is the WS7 deadlock, not a program-loop bug. Record it and surface; do not paper over it with retries.

## Trust gate (hardened — autonomous shipping)

Every shippable change the portfolio produces funnels to a **fully-green PR**, gated by the locked trust gate. This loop never merges on any trigger other than the single literal one below. The five sub-properties and where each is enforced:

### 1. Literal auto-merge trigger (mechanism: branch protection)

On a **gated repo** (see [per-repo merge policy](#per-repo-merge-policy)), auto-merge fires on **exactly one signal: a GitHub `APPROVED` review event from Nic's own account, on the specific PR SHA.** Not chat assent. Not green CI. Not review-chain endorsement. Not a timeout. **Junior never produces, stands in for, or simulates that signal, and merges on no other trigger.**

This is held by **branch protection requiring Nic's review** — a mechanism on the repo, not prose in this skill — because an autonomous junior on a repo _without_ that protection could otherwise merge its own green PR (retro thread 2: junior reached for `gh pr merge --admin` at Turn 22; the repo's review rule, not doctrine, is what stopped it). The program loop's behavioural rule is: **never run `gh pr merge` (with or without `--admin`) on a gated repo.** The enforcement that makes this safe even under a bug is the branch protection itself.

### 2. Per-SHA reviewer attestation (mechanism: presence check, absence = FAIL)

A merge-ready PR carries a documented review-agent chain (rbg/pauli/marsha) with **positive per-SHA attestation that each named reviewer actually executed against that SHA.** **Absence of a named reviewer's verdict is a FAILURE, not a pass** (retro thread 5: deep-review sat in `startup_failure` for ~a week and absence read as pass). Before the loop records a PR as merge-ready in the digest, it checks each required reviewer has a verdict _for the current head SHA_; a missing verdict makes the PR **not** merge-ready — it is surfaced as a blocked item, never silently passed. "Endorsed" means the chain ran and found no reason to block — not a rubber stamp (James #7).

### 3. Clean-build green (mechanism: clean-checkout CI, not incremental)

"Fully-green" is pinned to a **clean-checkout / clean-build run, not a cached or incremental one** (retro thread 2 shipped a build-breaking Dockerfile that passed against an incremental build). The loop treats a green status as authoritative only when the green came from a clean checkout. The mechanism is the CI pipeline's clean-build configuration; the loop's rule is to not treat an incremental-only green as merge-ready.

### 4. Red-CI posture (mechanism: GHA self-heal first, then /daily loop-closer)

Red CI is **not** routed around review and **not** simply blocked-and-surfaced. **The GHA merge pipeline self-heals first** — it is tasked with fixing the CI failure. **If it cannot, the `/daily` loop-closer files + enqueues a follow-up fix-task** (`/daily` → [Red-CI / stuck-PR loop-closer](../daily/SKILL.md)). So a stuck-red PR degrades to a queued, owned fix-task — never a silent stall, never a route-around. The program loop's role: when it sees a constituent PR red and not self-healing, it confirms the `/daily` loop-closer will catch it (or records the stuck PR in `## Escalations` so the next `/daily` does); it does **not** route around the failure or merge despite red.

> **Dependency flagged (not assumed).** The red-CI backstop relies on a `/daily` loop-closer that converts a stuck-red PR into an enqueued follow-up task. The spec marks this "a capability to confirm/build". **WS2 adds the loop-closer to `/daily` (see `../daily/SKILL.md` → "Red-CI / stuck-PR loop-closer").** The GHA-pipeline self-heal first-line posture is a separate capability that the merge pipeline owns; if it is not yet wired, that is a surfaced gap, not something this loop fabricates.

### 5. Per-repo branch-protection enforcement (mechanism: per-repo gate config)

The no-merge-without-Nic invariant is per-repo, not global (Nic 2026-05-29). Each launch dir's `CLAUDE.md` (layer 3, WS3) carries its repo's merge policy. The loop reads the active repo's policy and behaves accordingly. **WS2 does not edit `CLAUDE.md` (that is WS3's lane); it relies on the policy being present and defaults to the most conservative posture (gated, never merge) when the policy is absent or unreadable.**

#### Per-repo merge policy

| Repo           | Policy                                        | Gate status / action (Nic 2026-05-29)                         |
| -------------- | --------------------------------------------- | ------------------------------------------------------------- |
| **aops**       | Nic-review required (never merge without Nic) | Branch protection present + current ✓                         |
| **buttermilk** | Nic-review required                           | Gated, but **not on current gate code** → action: update gate |
| **mem**        | Nic-review required                           | **Gate NOT installed** → action: install gates                |
| **brain**      | Agent-managed (history only)                  | No merge gate; agents may merge                               |
| **sessions**   | Agent-managed (history only)                  | No merge gate; agents may merge                               |
| **overwhelm**  | **Auto-merge enabled**                        | No gate; auto-merge → action: enable                          |
| _others_       | TBD                                           | Decide as encountered; default to gated                       |

The buttermilk/mem/overwhelm **actions** (install/update/enable gate config) are infrastructure tasks the program loop _surfaces and tracks_ but does not perform inline — they are gated-repo config changes that belong to a worker, and the action items are recorded in the spec ([[note-36c15a69]] Action items). The loop's behaviour is policy-driven: `gated` → never merge, surface for Nic's approval; `agent-managed` → agents may merge; `auto-merge` → no gate.

## Program Brake

The brake catches terminal loops; it does not gate the golden path. Apply against `## Program Log` (last 8 rows):

| Rule              | Trigger                                                                                                      | Action                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Recurring failure | Same `*_fail` / `*_halt` class ≥3× in last 8 rows                                                            | Halt program; status `blocked`; reason `recurring: <class>`                                           |
| Stalled portfolio | ≥2 constituent epics `in_progress` with no Program Log advance > 4h                                          | Halt program; status `review`; reason `stalled portfolio`                                             |
| No-progress quiet | ≥3 consecutive ticks with no advanceable action AND release goal unmet AND nothing decomposable/discoverable | Reach **done-pending-Nic** (not a hard halt — the loop is structurally blocked on human-only residue) |

The no-progress-quiet rule is the field fix for the empty-turn loop (retro thread 10: 10+ empty turns after Nic went quiet, each re-firing the Stop hook). When there is genuinely nothing junior can advance, the correct terminal state is done-pending-Nic — not another empty retry.

## Program Log format

One row per tick, capped at 16 (drop oldest). Lives in the program body under `## Program Log`:

```markdown
## Program Log

| Tick (ISO)           | Action                                   | Class            | Notes                        |
| -------------------- | ---------------------------------------- | ---------------- | ---------------------------- |
| 2026-05-29T09:00:00Z | supervisor tick on epic-A (dispatch)     | epic_advanced    | leaf task-abc → polecat      |
| 2026-05-29T09:30:00Z | auto-decompose epic-B (leaves exhausted) | decomposed       | plan at review; Nic promotes |
| 2026-05-29T10:00:00Z | discover + file epic-C                   | epic_discovered  | release sub-goal untracked   |
| 2026-05-29T10:30:00Z | all epics at surface; 3 items for Nic    | done_pending_nic | see ## Escalations           |
```

Class values: `epic_advanced`, `decomposed`, `epic_discovered`, `escalated`, `done_pending_nic`, `complete`, `brake_fired`, `epic_halt`. Keep class names stable — the brake matches on them.

## Escalations & the digest

`## Escalations` is the **durable record** of items surfaced for Nic — the autonomous-profile digest, not chat threads. Each entry is one decision/approval/merge that is structurally Nic's, written in plain English (no framework taxonomy — same vocabulary boundary as `/supervisor`'s `[ATTN]` block). The program loop's user-facing output is this digest plus merge-ready PRs; it emits **no worker threads, no tool-call play-by-play** (north star: protect Nic's attention).

Where a push channel is configured, the digest pairs with a push of the highest-urgency line (same pairing rule as `/supervisor`'s `[ATTN]` push). The program loop does not configure push channels.

## What the program loop owns vs. delegates

**Owns** (program scope — don't bounce to Nic, don't push down to `/supervisor`):

- Discovering and decomposing constituent epics (decision-order steps 4–5).
- Selecting which epic gets each `/supervisor` tick, and pacing portfolio concurrency.
- Binning the portfolio's PRs by merge-ready / needs-Nic / stuck, and maintaining the digest.
- Reaching the done-pending-Nic terminal state when the residue is human-only.

**Delegates to `/supervisor`** (epic scope): the entire orient→decompose→dispatch→verify→react→halt cycle for any single epic. The program loop never reads PR diffs, task bodies, transcripts, or polecat output — that prohibition (`agents/junior.md` Layer 3 "forbidden in your main context") holds one scope up.

**Escalates to Nic** (digest only): the single locked pre-merge approval (never junior's), genuine judgment/strategy/scope calls, gated-repo merges, and the infrastructure action-items (mem/buttermilk/overwhelm gate config) as tracked tasks.

## Relationship to other skills

- **`/supervisor`** — the epic-scope loop this skill drives. Unchanged by WS2; the program loop calls it one tick at a time.
- **`/q`** — frictionless capture (delegates to planner capture mode). Captures land in the queue; the program loop discovers them as constituent work where they bear on the release.
- **`/pull`** — the thin one-shot **dispatch alias** over this loop's [dispatch trigger](#dispatch-trigger--the-ws4-seam) (decision-order step 2). WS4 retired its old self-execution semantics: `/pull` now selects the next ready task and routes it to a surface (polecat / subagent), exactly once, then stops — it never executes inline. Use it for a single manual dispatch in a solo session; use this program loop for continuous advancement.
- **`/daily`** — reports state and runs the [Red-CI / stuck-PR loop-closer](../daily/SKILL.md) that backstops the red-CI trust-gate posture. The program loop relies on it; it does not duplicate its sweep.
