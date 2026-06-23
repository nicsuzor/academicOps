---
name: premise-test
title: The Premise Test — judge the idea before you review the code
type: reference
category: framework
description: Review-time agent-judgment backstop that catches bad premises that bypassed the source gate. Forced step-0 in /verify and arch-fit; a bad premise fails the review regardless of test coverage.
permalink: premise-test
tags: [framework, enforcement, premise-gate, premise-test, agent-judgment, judgment-non-delegable]
---

# The Premise Test

> **One line.** Before a reviewer reads a single line of the diff, they judge the **premise** from the task + diffstat alone and write the sharp principal's one-sentence snap reaction — _"was this a good idea, in this shape?"_ A bad premise fails the review **regardless of test coverage**. This is the review-time **backstop** for the source premise gate (`premise-gate.md`, sibling PR #1733): it catches bad premises that never crossed the `→ queued` source gate (direct hand-coded PRs, work that bypassed the queue) because every PR hits review no matter how it was created.

This test is the review-surface counterpart of the source-level premise gate (`premise-gate.md`), enforcing the same axiom — **[[../../../../.agents/rules/AXIOMS.md#judgment-non-delegable]]** (`judgment-non-delegable`). Like the source gate, it is itself judgment, not a mechanism: a reviewer reads a sentence and decides. There is no regex, no field check, no classifier, no threshold, no checklist anywhere in it — a deterministic rig standing in for "is this premise sound?" would itself be the disease it guards against, so it is forbidden by construction.

## 1. What the reviewer writes (step 0, before reading the diff)

The first move of the review — before you reconstruct the task, read the diff, or trace call sites — is to answer **one open question** from the task + diffstat alone and record the answer as **one sentence of prose** in the review output:

> _Seeing only the task and the diffstat (NOT the code): is this worth doing, and is the shape right — or would a sharp principal bounce it?_

That sentence is the whole step-0 artifact. You write it first; only then do you read the code.

### HARD RULE — one open sentence, never a checklist, never a field

- It is **one open prose sentence**, written first. It is **never** a form, a field, or a `- [ ]` checklist.
- A checklist re-commits the exact sin this test exists to stop: it abdicates the judgment to a mechanical rig you tick rather than a call you make. The moment _"was this a good idea?"_ becomes `[ ] worth doing? [ ] shape right?` you have rebuilt the rubric and the judgment is gone. A **form invites mechanical completion; a sentence demands a judgment.**
- The sentence must show you actually looked at _this_ premise. "Looks fine" / "ships clean" is vacuous — it records no premise assessment.

### Why diffstat-first ordering is mandatory

Reading the code first is exactly what lets a clean, well-tested surface **launder** a bad premise. Engage the diffstat and the task before the code, while the question _"should this exist at all?"_ is still askable without the pull of polished implementation. **You cannot emit an approving verdict without first writing the step-0 sentence** — that bind is the forcing function; it must remain item 0 in each skill's output schema.

## 2. A bad premise fails — regardless of test coverage

If a sharp principal would bounce the premise, the verdict is a **rejection even with green CI, clean code, and satisfied AC**. The skill-local rejection token:

| Surface       | Skill                       | Approving token (blocked by a bad premise) | Rejecting verdict |
| ------------- | --------------------------- | ------------------------------------------ | ----------------- |
| `/verify` QA  | `verify/SKILL.md`           | `PASS`                                     | `FAIL`            |
| arch-fit lens | `strategic-review/SKILL.md` | ✅ MERGE                                   | 🔴 REJECT         |

Test-passing is the **expected surface** of a bad-premise artifact, not a mitigant — _"but it's tested / it works / it's clean"_ is precisely the rationalisation this test closes.

## 2a. A negative verdict needs a held falsifier

A rejecting verdict (`FAIL` / 🔴 REJECT) requires a falsifying observation the reviewer actually holds — not merely a gap in the record. Where ground truth is unobservable, downgrade to an ADVISORY flag. Full rules: [§Epistemic humility → SKILL.md](../SKILL.md#epistemic-humility--absence-of-evidence-is-not-a-negative-result).

## 3. Generalised framing — overengineering is one worked example

The question is _"was this worth building at all, in this shape?"_ — **not** an overengineering-only check. _Deterministic-rig-for-a-judgment-call_ (a regex / threshold / NLP / bespoke parser / checklist substituting for a call a smart agent should just make — see `judgment-non-delegable`, `exercise-authority` Edge 3) is **one named instance** of the broader "dumb idea" class, not the definition.

**Worked specimen (illustrative, NOT a checklist).** PR #1723 proposed a **978-line SHA-parsing freshness tool with magic thresholds** (`STALE ≥ 20 commits` / `≥ 30 days`) and brittle prose-fallback parsing — an entire deterministic machine built to answer a one-read staleness call a smart agent would simply _judge_. Green tests and clean code do not save it: the premise is wrong, so the verdict is `FAIL` / 🔴 REJECT. A reviewer's step-0 sentence — _"why 978 lines of machine for a question I'd answer by reading?"_ — bounces it before the diff is even read.

## 4. Honest scope — the backstop half of a pair

This review-time test and the source-level premise gate (`premise-gate.md`) are a **pair**, and only the pair is surface-agnostic. The source gate binds the coordinated spend path (`/pull` / `/dispatch` / `/supervisor`); it cannot see a human who hand-codes and opens a PR directly. This test is the catch for exactly those premises — **every PR hits review regardless of how it was created.** When a bad premise nonetheless passes review, `/learn` retro (`survey/SKILL.md` §2a) scores the miss **against the approving reviewer/surface**, not just the author — making the slipped-through premise a logged, attributed miss. Do not overclaim either half alone.

## Referenced by

- [[../../verify/SKILL.md]] — forced step-0 Premise Test before the QA diff read
- [[../SKILL.md]] — forced step-0 Premise Test in the arch-fit lens
- [[../../survey/SKILL.md]] — `/learn` retro §2a, bad-premise-approval recurrence scoring
- `premise-gate.md` (sibling PR #1733) — the source-level counterpart at `→ queued`; upgrade to a wikilink once both land on `dev`
- [[../../../../specs/ENFORCEMENT-MAP.md]] — `judgment-non-delegable` enforcement row
