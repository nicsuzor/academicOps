---
name: premise-gate
title: The Premise Gate — what the promoter records and what the dispatcher does
type: reference
category: framework
description: Operative procedure for the source-level premise gate — the sentence the promoter records at → queued, and the read-and-judge / hard-refuse the dispatcher runs at /pull, /dispatch, /supervisor.
permalink: premise-gate
tags: [framework, enforcement, premise-gate, agent-judgment, judgment-non-delegable]
---

# The Premise Gate — operative procedure

> **This file is the procedure, not the rationale.** For the design statement — what the gate is, the axiom it enforces, its pyramid/pipeline position, and its scope — see [[../../../../specs/enforcement/premise-gate.md]]. This file is what the agent actually _does_ at the gate.
>
> **One line.** Every task should carry a one-sentence, principal-voice **premise** in its body; before spending compute, `/pull`, `/dispatch`, and the dispatch step of `/supervisor` **ensure that premise is legibly recorded and then clear it through two independent judges** (`rbg` for axiom/rig compliance, `pauli` for worth/shape) via `/strategic-review --premise` — any BOUNCE hard-refuses the dispatch.
>
> **Why the clearance runs at dispatch, not at `→ queued`.** `queued` is set **manually by the human**, with no hook on the transition — a hand-promoted task leaves no premise sentence and nothing fires to solicit one. So enforcement cannot attach to the promotion; it attaches at the **agent dispatch step**, the first point where machinery actually intercepts. The dispatcher makes the premise legible there and hands it to the two judges.

## 1. The premise — what a good one looks like

A task's premise is the answer, in **one sentence of prose in the task body**, to **one open question**:

> _As a sharp principal seeing only this task: is this worth doing, and is the shape right — or would you bounce it?_

That sentence is the whole artifact. When an **agent** promotes a task it records it directly; when a **human** hand-queues a task and leaves none, the dispatcher makes it legible at §2 step 1 before the judges rule. Either way the premise must be present and real before compute is spent.

**Precondition for any new-mechanism task — establish current state first.** Before you record the premise sentence on a task that proposes a **new or changed mechanism** (gate, env var, context builder, classifier, schema, dispatch path), first establish whether **it already exists** or **was already decided**. To do this you MUST actually look — run the PKB searches and the `rg`/`git`/`gh` reads against live code and the PR/issue/memory record; do not judge from memory or from the task body's own claims. A premise judged without knowing the current state is a guess, not a judgment; "adds a second path beside an existing one" and "re-raises a settled decision as novel" are both premise defects that bounce the task. This is cheap judgment-driven discovery (a few searches and reads), not a mechanism — full rationale in the review-time twin ([[../../strategic-review/references/premise-test.md]] §"Establish current state and prior decisions FIRST").

### HARD RULE — one open sentence, never a checklist, never a field

- It is **one open prose sentence in the body**. It is **never** a frontmatter field, a form, or a `- [ ]` checklist. _Why:_ a form invites mechanical completion; a sentence demands a judgment. The moment "is this worth doing?" becomes `[ ] worth doing? [ ] shape right? [ ] duplicates?` the judgment is gone and you have rebuilt the rubric this gate exists to kill — a deterministic rig standing in for the call, which is the exact violation of `judgment-non-delegable`.
- The sentence must show you actually looked at _this_ task. "Looks fine" / "ok to dispatch" / "approved" is vacuous — it records no premise assessment, and the dispatcher treats it as absent.

### What a sharp principal notices (illustrative priming — NOT a checklist)

Examples of what a good premise judgment catches. **Do not enumerate them as required boxes** — judge the task holistically; this list is priming, not a rubric:

- Is this worth doing at all, for a real consumer with a real need?
- Is the _shape_ right, or is it over-built for what it does?
- Is a qualitative judgment call being mechanised into a deterministic rig (regex / keyword match / magic threshold / bespoke parser / classifier) when a smart agent reading once would just _decide_?
- Does it duplicate work that already exists, or re-open a settled decision?

## 2. What the dispatcher does — at `/pull`, `/dispatch`, and `/supervisor` dispatch

The spend surfaces — `/pull` (inline claim), `/dispatch`, and the dispatch step of `/supervisor` (single epic or portfolio) — are the last moment before compute is spent. Before acting on a queued task, the dispatching agent runs **two mandatory steps** and does not dispatch until both pass:

**Step 1 — ensure the premise is legibly recorded in the task body.** Read the task. If it already carries a real, principal-voice premise sentence (per §1), keep it. If it does not — the common case for a hand-queued task — **make the premise legible**: if the task's intent is clear enough to state one, record a one-sentence premise from the task's actual intent (not an oversell); if the task is too vague to state a premise at all, **bounce it** to the promoter with that reason. Do not fabricate a rosy premise to get past step 2 — step 2's judges read the whole task, so an oversell is caught.

**Step 2 — clear it through the two judges.** Invoke `/strategic-review --premise <task>`. This deploys **`rbg`** (axiom / rig compliance — chiefly `judgment-non-delegable`) and **`pauli`** (worth and shape — the premise test), each briefed with the **task** and asked to return **CLEAR** or **BOUNCE `<reason>`**. This is the single home for "run the two judges" — do not re-author their briefs here (DRY; the mode owns the procedure).

- **Both CLEAR → dispatch** as normal.
- **Any BOUNCE → HARD REFUSE.** Do NOT dispatch and do NOT spend compute. Return the task to the promoter: keep it out of `in_progress`, record the bouncing reviewer's one-line reason on the task body, and route it back (set status `ready` and/or assign to the promoter) so the premise is fixed before it is queued again.

Hard refuse, not soft warn — a soft warning degrades to advisory and gets sailed past. The two-judge clearance is the spend-stopper.

> **After the work, not just before it.** The pre-dispatch clearance judges the premise on paper; it does not vouch for the built result. `pauli` (strategic alignment) and the rest of the review roster run **again** on the completed work at the review surface (`/strategic-review`, `/verify`) — the review-time twin. Pre-dispatch and post-work are two trigger points of the **same** judgment, not two mechanisms.

## Referenced by

- [[../../../../specs/enforcement/premise-gate.md]] — the design statement / pyramid position (this file is its operative half)
- [[../../strategic-review/references/premise-test.md]] — the review-time twin (same axiom, review surface)
- [[TAXONOMY.md#status-values-and-transitions]] — the `queued` promotion gate
- [[commands/pull]] — inline claim-time refusal
- [[commands/dispatch]] — dispatch-time refusal
- [[../../supervisor/instructions/worker-dispatch.md]] — pre-dispatch gate (epic + portfolio)
- [[../../planner/SKILL.md]] — promoter-side recording
- [[../../../../specs/ENFORCEMENT-MAP.md]] — `judgment-non-delegable` enforcement row
