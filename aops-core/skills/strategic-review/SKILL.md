---
name: strategic-review
type: skill
category: instruction
description: Unified multi-agent review of any artifact — a document, plan, proposal, or pull request. The calling agent deploys rbg, pauli, and marsha in parallel, then @james reconciles their findings into one verdict. Pass `comment` and/or `fix` to write the result back to the review surface. Use `--critic` for a fast pauli-only pre-hoc critique.
triggers:
  - "strategic review"
  - "review this document"
  - "review this proposal"
  - "review this plan"
  - "review this PR"
  - "review PR"
  - "review a pull request"
  - "adversarial review"
  - "/strategic-review"
  - "/strategic-review --critic"
  - "critic review"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
  - quality-assurance
allowed-tools: Agent, Bash, Read, Glob, Grep, AskUserQuestion
version: 3.0.0
permalink: skills-strategic-review
---

# /strategic-review — Unified Multi-Agent Review

Review any artifact — a document, plan, proposal, or pull request — from several expert
perspectives and return **one reconciled verdict**. Owned by **james** (reconciliation), but
**you, the invoking agent, own the orchestration**: you deploy the reviewers yourself, because a
subagent cannot spawn its own subagents. James is called only at the end, to reconcile.

## Modes

- **Default** — full review: deploy `rbg` + `pauli` + `marsha` in parallel, then `@james` reconciles.
- **`--critic`** — solo `pauli`: one fast adversarial critique, no reconciliation. For a pre-hoc
  sanity check on a plan or proposal before work starts.
- **`--premise`** — pre-dispatch premise clearance: deploy `rbg` + `pauli` in parallel on a **task**
  (not a diff or transcript), each briefed with the task body and asked to return **CLEAR** or
  **BOUNCE `<reason>`**. No marsha, no james. Both must CLEAR to dispatch; any BOUNCE refuses it.
  This is the clearance `/pull`, `/dispatch`, and `/supervisor` dispatch run before spending compute
  — see [§ `--premise` mode](#--premise-mode--pre-dispatch-premise-clearance).

## Inputs

- **The artifact**: a file path, a PKB id, pasted text, or a pull request (an `owner/repo#N` ref or URL).
- **Action flags (optional)**: `comment`, `fix`, or both. With no flag the review is **advisory** —
  you return the verdict to the caller and change nothing.

---

## Procedure (default mode)

### 1. Gather context

Identify and load the artifact. If it is a **PR**, load the diff, description, and any prior
unresolved review comments (`gh pr view`, `gh pr diff`). Select the matching review-context
descriptor from `review-contexts/` and pass it to every reviewer:

- `review-contexts/pr-code.md` — code PRs.
- `review-contexts/pr-framework.md` — framework PRs (skills, agents, hooks, specs).

### 2. Deploy the three reviewers — in parallel

Spawn all three in a **single message** (concurrent `Agent` calls). Give each the artifact, the
context, and the descriptor. **You spawn them — not james.** Subagents cannot spawn subagents, so
this fan-out must happen here, at the top level.

- **rbg** — axiom & rule compliance. **Always runs.**
- **pauli** — strategic critique: the premise test, then the _"is this in the right place, or a
  workaround for a root cause that belongs elsewhere?"_ architectural-fit lens (the 10 cognitive
  moves). **Always runs.** Discipline and the worked specimen live in [[references/premise-test.md]].
- **marsha** — runtime / verification QA. Runs **whenever code or executable behaviour changed**;
  skip for pure-prose artifacts.

**Every reviewer brief carries the epistemic-humility constraint below** ([§ Epistemic humility](#epistemic-humility--absence-of-evidence-is-not-a-negative-result)): a reviewer may not issue a "this is false / failed / was a misstep" verdict about a real-world event, intent, or state it cannot directly observe — it downgrades to an ADVISORY primary-source flag instead.

### 3. Reconcile via @james

When all three return, dispatch **@james** with the original artifact plus all three reviewer
outputs. **James does not re-spawn anyone — it reconciles only.** It carries the contradictions,
resolves them honestly, and returns **one verdict** with a synthesis table:

| Agent | Issue | Feedback | Severity |

Severity ladder: **REJECT** (fundamental — close/redesign) · **REVISE** (substantial rework, in
scope) · **FIX** (clear correct resolution exists) · **TRIVIAL** (cosmetic) · **ADVISORY**
(non-blocking follow-up). Overall verdict: **APPROVE / REVISE / REJECT**.

```
Agent(subagent_type="aops-core:james",
      prompt="Reconcile these three reviews into one verdict. Do NOT spawn subagents — synthesise only. [artifact + rbg/pauli/marsha outputs]")
```

**Reconciliation must not harden inference into fact.** Unverifiable claims carry through as **ADVISORY (needs primary-source confirmation)** — the QA seal must not launder a guess into a confident negative. See [§ Epistemic humility](#epistemic-humility--absence-of-evidence-is-not-a-negative-result).

### 4. Act on the verdict — only if asked

- **No flag (default)**: return james's verdict and table to the caller. Change nothing.
- **`comment`**: post james's synthesis to the artifact's natural review surface — a PR comment for
  a PR, an inline note or PKB entry for a document. Scrub all personal info (names, private paths).
- **`fix`**: apply every **FIX**- and **TRIVIAL**-grade finding directly, without returning to the
  author. If a fix is substantial, re-run the affected reviewer(s) and fold any new findings into
  the table. **REVISE/REJECT** findings are reported, not silently reworked.
- **Both**: comment _and_ fix.

Whatever the flags, **never silently exit**: if a write-back action fails, report it and print the
full verdict to chat.

---

## Epistemic humility — absence of evidence is not a negative result

Missing evidence licenses _"not supported by the available evidence"_ — never _"false / failed / did not happen."_ A negative verdict requires a held falsifier the reviewer actually holds; where ground truth is unobservable (intent, off-record events, room dynamics), downgrade to **ADVISORY (needs primary-source confirmation)**. Silence in a record is not failure. Apply the same discount symmetrically to flattering and unflattering claims alike. (Source incident: #1891.)

## `--critic` mode

Deploy **pauli alone** for a fast pre-hoc critique (premise test + the 10 cognitive moves). No
parallel roster, no james reconciliation. Return pauli's verdict directly to the caller. Use this
to pressure-test a plan or proposal _before_ committing effort to it.

## `--premise` mode — pre-dispatch premise clearance

The pre-dispatch premise gate, expressed as a two-judge clearance rather than a bespoke solo read.
Called by the dispatch spine — `/pull`, `/dispatch`, and the `/supervisor` dispatch step — before
any queued task is dispatched (wired in [[../remember/references/premise-gate.md]] §2). It is the
same two judges the default review deploys, scoped down to a task and a binary verdict.

**Input:** a queued **task** (id or body). No diff, no transcript — nothing is built yet, so the
artifact under judgment is the task itself.

1. **Deploy `rbg` + `pauli` in parallel** — a single message, two concurrent `Agent` calls. Brief
   **each** with the **task body only** and one instruction: _judge this task's premise and return
   **CLEAR** or **BOUNCE `<one-line reason>`**._ Do **not** pass a session transcript or a diff.
   - **rbg** — does the task's premise violate an axiom? Chiefly `judgment-non-delegable` (is it a
     deterministic rig standing in for a call a smart agent would just make?) and `exercise-authority`
     Edge 3. Apply the axioms to the task as written.
   - **pauli** — is the premise worth doing and rightly shaped? The premise test + arch-fit lens
     ([[references/premise-test.md]]), read against the task. A fluent-but-ungrounded new-mechanism
     premise (no sign current state was established) is a BOUNCE, not a CLEAR.
     Both read the **task body**, not just its premise sentence — a premise that oversells the task is
     caught because the judge sees the task it claims to describe.
2. **Both CLEAR → dispatch.** **Any BOUNCE → refuse:** do not dispatch, do not spend compute; return
   the task to the promoter with the bouncing reviewer's reason.
3. **No james reconciliation** — two independent CLEAR/BOUNCE verdicts, AND-gated (a BOUNCE always
   wins). The point is a cheap binary spend-stopper, not a synthesised report.

Return the two verdicts (and any bounce reason) to the caller. This mode never writes anything back
itself — the dispatch spine that called it owns the refuse-and-bounce action.
