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

**Reconciliation must not harden inference into fact.** When a reviewer flagged a claim as
_unverifiable from the available evidence_ (an unobservable event/intent/state), james carries that
uncertainty **through to the verdict** — it does not let the single QA seal launder a guess into a
confident negative. Such a finding lands as **ADVISORY (needs primary-source confirmation)**, never
as a REJECT/REVISE "this is false." See [§ Epistemic humility](#epistemic-humility--absence-of-evidence-is-not-a-negative-result).

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

> **One line.** Missing evidence licenses _"not supported by the available evidence"_ — it never
> licenses _"false / failed / did not happen / was a misstep / was a loss."_ Inherits via review
> orchestration: **pauli**, **marsha**, and the **james** reconciliation carry it by brief; **rbg**
> inherits it the same way (not yet via its own axiom load — see follow-up to add the clause to
> `honest-epistemics` in AXIOMS.md).

When an artifact concerns a **real-world event, intent, or state the reviewer cannot directly
observe** — what happened in a meeting, what a person was trying to achieve, whether a thing
succeeded, whether a contribution landed — any reconstruction of it is **inference, and must be
labelled as inference**, never asserted as fact.

**Testable rules a reviewer can self-check against:**

1. **Distinguish the two claims.** _"Not supported by the available evidence"_ (licensed by a gap) is
   not _"false / failed / a misstep"_ (licensed only by a falsifying observation you actually hold).
   Only the first follows from missing information.
2. **A "this is false" verdict needs a held falsifier.** A **REJECT/REVISE "this is false / failed"**
   requires the falsifying basis to be **observable in evidence the reviewer actually holds.** If the
   claim depends on unobservable ground truth (room dynamics, intent, off-record events), **downgrade
   to an ADVISORY flag requesting primary-source confirmation** — not a negative verdict.
3. **Silence is not failure.** Do **not** infer failure, defeat, or the absence of a contribution from
   silence or absence in a record (a transcript, log, or doc) — the record may simply not capture it.
   A number floated in a room may be a tactic, not a goal; a commitment confirmed in a meeting may have
   been secured earlier; a contribution may have happened off-record.
4. **Default to unverifiable, not negative.** Where ground truth is unobservable, the verdict is
   **"unverifiable from available evidence — flag for primary-source confirmation,"** not a confident
   negative conclusion.
5. **Calibrate symmetrically.** Apply the same uncertainty discount to **flattering and unflattering
   claims alike** — never discount only the claims that happen to read as failures.

**The failure mode this closes.** A confident **over-correction is as damaging as the original
inflation — worse, because it inherits review authority.** A reviewer who recasts a transcript-derived
inference as a ground-truth _"FALSE / failed / corrected-misstep"_ verdict has fabricated an
observation it never made; the QA seal then makes the fabrication authoritative. Source incident:
**#1891** (a review of an agent-authored synthesis of real-world meeting transcripts issued confident
negative verdicts about events it could not observe; later reversed by the human primary source). This
is the over-correction sibling of the inference-as-observation failure family (`mem-ff013263`,
issue #1540).

## `--critic` mode

Deploy **pauli alone** for a fast pre-hoc critique (premise test + the 10 cognitive moves). No
parallel roster, no james reconciliation. Return pauli's verdict directly to the caller. Use this
to pressure-test a plan or proposal _before_ committing effort to it.
