---
name: strategic-review
description: Multi-agent review of any artifact — a document, plan, proposal, or pull request. James deploys rbg, pauli, and marsha in parallel, then reconciles their findings into one verdict. Pass `comment` and/or `fix` to write the result back to the review surface.
agent: "orchestrate:james"
---

# Strategic Review

Review an artifact from several expert perspectives and return **one reconciled verdict**.

James runs this skill end to end: assembles the standards, deploys the three reviewers, interrogates their output, and reconciles it into one verdict. Reviewer independence comes from the reviewers working blind to each other, and from james treating their output as input rather than truth — not from splitting who deploys them from who reconciles them. Never substitute your own reading of the artifact for the review — a verdict from an agent that reviewed itself is the thing this skill exists to prevent.

This requires a subagent surface. If you hold none, you cannot run this skill: hand the artifact to a context that can spawn, and say so.

## Inputs

- **The artifact** — a file path, a knowledge-base id, pasted text, or a pull request (`owner/repo#N` or a URL).
- **Action flags**, optional — `comment`, `fix`, or both. With no flag the review is advisory: return the verdict and change nothing.

## 1. Gather context

Load the artifact. For a pull request, load the diff, the description, and any unresolved prior review comments.

Assemble the standards the artifact must meet: the owning project's local rules, plus the quality standard for this artifact _type_ (coding standards for code, peer-review norms for scholarship, instruction-quality standards for agent instructions). Pass the same context to every reviewer.

If the work was dispatched from a brief, the brief's evidence contract is the primary evidence source — load it alongside the artifact. **Missing or thin emitted evidence is itself a blocking defect**, never a licence to reconstruct what should have been emitted.

## 2. The premise test — before anyone reads the diff

Judge the **premise** from the task and the diffstat alone, and write the sharp principal's one-sentence reaction: _was this worth doing, and is the shape right — or would a sharp principal bounce it?_

- **One open prose sentence, written first.** Never a form, a field, or a checklist. A form invites mechanical completion; a sentence demands a judgment. "Looks fine" records nothing.
- **Diffstat before code.** A clean, well-tested surface launders a bad premise. Ask "should this exist at all?" while it is still askable.
- **A bad premise fails the review regardless of test coverage.** Green CI on a bad premise is the expected surface of the failure, not a mitigant.

For anything that **adds or changes a mechanism** — a gate, env var, builder, classifier, schema, dispatch path — establish two things from live code and the decision record before judging the premise:

- **Does this already run?** A second path beside an existing one is itself a premise defect.
- **Was this already decided?** Re-raising a settled call as novel, or contradicting a prior decision without engaging it, fails the premise however reasonable it reads.

A deterministic rig standing in for a judgment call is one named instance of a bad premise — and it fails whether it makes the call or merely decides whether the judgment fires at all. A cheap filter in front of a judging agent owns the recall; "a smart model still makes the final call" is a laundering move, not a mitigant.

## 3. Deploy the three reviewers, in parallel

Spawn all three in a **single message**, each with the artifact, the assembled standards, and an explicit model. Dispatches are neutral — never pre-state an expected verdict.

- **rbg** — axiom and rule compliance. Always runs.
- **pauli** — strategic critique: the premise test above, then architectural fit. Is this in the right place, or a workaround for a root cause belonging elsewhere? Always runs.
- **marsha** — runtime and content quality against our standards. Always runs.

Reviewers select **three or four** lenses from this registry rather than sweeping all of them; breadth kills depth. Self-consistency runs as a background check throughout.

| Lens                        | Applies to         | Core question                                         |
| --------------------------- | ------------------ | ----------------------------------------------------- |
| **Self-consistency**        | Everything         | Does it practise what it preaches?                    |
| Strategic alignment         | Specs, designs     | Does this fit the larger vision?                      |
| Assumption hygiene          | Plans, proposals   | Are load-bearing assumptions identified and testable? |
| Scope discipline            | Everything         | Is it building for now or for a hypothetical future?  |
| Cross-reference consistency | Specs, docs        | Does it contradict existing work?                     |
| Attribution                 | Intellectual work  | Is the intellectual debt acknowledged?                |
| Methodological coherence    | Research, analysis | Does the method match the question?                   |
| Literature awareness        | Research, academic | Is it building on or reinventing existing work?       |
| Ethics and governance       | Research, data     | Are ethical obligations addressed?                    |
| Feasibility                 | Plans, proposals   | Can this be done with the resources available?        |

## 4. Reconcile

With the artifact and all three reviewer outputs in hand, synthesise one verdict plus a synthesis table:

| Agent | Issue | Feedback | Severity |

Two reviewers reaching the same defect from different lenses is agreement, not contradiction: collapse it into a single row naming every concurring reviewer and their distinct rationale. Reserve separate rows for genuinely distinct issues, and hold real disagreement in tension.

Severity: **REJECT** (fundamental — close or redesign) · **REVISE** (substantial rework, in scope) · **FIX** (a clear correct resolution exists) · **TRIVIAL** (cosmetic) · **ADVISORY** (non-blocking follow-up). Overall verdict: **APPROVE / MINOR CHANGES / REVISE / REJECT**.

On REVISE or REJECT for brief-sourced work, address the synthesis to the brief — name which element failed, in the vocabulary the `dispatch` skill's brief doctrine defines (goal, constraints, evidence bar, and the subordinate elements under each), so re-dispatch is a brief edit, not a fresh plan.

## 5. Act on the verdict

- **No flag** — return the verdict and table to the caller. Change nothing.
- **`comment`** — post the synthesis to the artifact's natural review surface: a PR comment for a PR, an inline note or knowledge-base entry for a document. Scrub personal names and private paths.
- **`fix`** — apply every FIX- and TRIVIAL-grade finding directly. Re-run the affected reviewer on any substantial fix and fold new findings into the table. REVISE and REJECT findings are reported, never silently reworked.

**Whatever the flags say**, a reviewed artifact that has a task record gets the verdict written onto that record too. The evidence contract makes the task record the message bus every handback crosses; a verdict that lives only in this turn is one nothing downstream can read.

Never exit silently: if a write-back fails, report it and print the full verdict.

## A negative verdict needs a held falsifier

Missing evidence licenses _"not supported by the available evidence"_ — never _"false"_ or _"did not happen."_ Where ground truth is unobservable — intent, off-record events, room dynamics — downgrade to **ADVISORY (needs primary-source confirmation)**. Silence in a record is not failure. Apply the discount symmetrically to flattering and unflattering claims alike.
