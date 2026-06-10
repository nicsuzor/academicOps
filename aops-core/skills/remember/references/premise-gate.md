---
name: premise-gate
title: The Premise Gate — judge the idea before spending compute on it
type: reference
category: framework
description: Source-level agent-judgment gate that kills the class of dumb ideas at task promotion (→ queued) and refuses to dispatch a task whose premise was never judged.
permalink: premise-gate
tags: [framework, enforcement, premise-gate, agent-judgment, judgment-non-delegable]
---

# The Premise Gate

> **One line.** Before a task crosses into the dispatchable set (`→ queued`) the promoter records a one-sentence, principal-voice judgment of the **premise**; `/pull` and the dispatch step of `/supervisor` and `/program` **refuse to dispatch** a task whose body shows no genuine premise judgment. The aim is to kill the whole class of dumb ideas at the universal source — task promotion — before any compute is spent building good code for a bad idea.

This gate is the first-ever enforcement surface for the axiom **[[../../../../.agents/rules/AXIOMS.md#judgment-non-delegable]]** (`judgment-non-delegable`). It is itself judgment, not a mechanism: an agent reads a sentence and decides. There is no regex, no field check, no classifier, no threshold, no checklist anywhere in it — building one of those to police "is this a dumb idea?" would itself be the disease (a deterministic rig standing in for a qualitative call), so it is forbidden by construction.

## 1. What the promoter records (at `→ queued`)

When you promote a task into the dispatchable set, answer **one open question** and record the answer as **one sentence of prose in the task body**:

> _As a sharp principal seeing only this task: is this worth doing, and is the shape right — or would you bounce it?_

That sentence is the whole artifact. Promote with it, or bounce the task with a one-line reason instead.

### HARD RULE — one open sentence, never a checklist, never a field

- It is **one open prose sentence in the body**. It is **never** a frontmatter field, a form, or a `- [ ]` checklist.
- A checklist re-commits the exact sin this gate exists to stop: it abdicates the judgment to a mechanical rig you tick rather than a call you make. The moment "is this worth doing?" becomes `[ ] worth doing? [ ] shape right? [ ] duplicates?` you have rebuilt the rubric and the judgment is gone. A **form invites mechanical completion; a sentence demands a judgment.**
- The sentence must show you actually looked at _this_ task. "Looks fine" / "ok to dispatch" / "approved" is vacuous — it records no premise assessment and the gate treats it as absent.

### What a sharp principal notices (illustrative priming — NOT a checklist)

These are examples of what a good premise judgment catches. **Do not enumerate them as required boxes** — judge the task holistically; this list is priming, not a rubric:

- Is this worth doing at all, for a real consumer with a real need?
- Is the _shape_ right, or is it over-built for what it does?
- Is a qualitative judgment call being mechanised into a deterministic rig (regex / keyword match / magic threshold / bespoke parser / classifier) when a smart agent reading once would just _decide_?
- Does it duplicate work that already exists?
- Does it actually serve a real goal?

**Canonical specimen (illustrative, NOT a checklist).** PR #1723 proposed a **978-line SHA-parsing freshness tool with magic thresholds** (`STALE ≥ 20 commits` / `≥ 30 days`) and brittle prose-fallback parsing — an entire deterministic machine built to answer a one-read staleness call that a smart agent would simply _judge_ by reading the doc and the repo. A sharp principal's one-sentence reaction — _"why 978 lines of machine for a question I'd answer by reading?"_ — bounces it before a line is written. Over-engineering (a deterministic rig for a judgment call) is **one instance** of the broader class of dumb ideas this gate kills; it is the worked example, not the definition.

## 2. What the dispatcher does (at `/pull` and supervisor/program dispatch)

The dispatch surfaces — `/pull`, the Dispatch phase of `/supervisor`, and the dispatch step of `/program` — are the last moment before compute is spent. Before dispatching a queued task:

1. **Read the body and judge** whether it contains a genuine premise assessment — a real sentence from someone who looked at this task and decided it is worth doing and rightly shaped. **This is an agent judgment, not a presence check.** Do not grep for a keyword, a heading, or a field; a string/field/regex presence-check would itself be the deterministic rig this gate forbids (`judgment-non-delegable`). You read it, you decide.
2. **If a genuine premise judgment is present → dispatch** as normal.
3. **If it is absent, empty, or vacuous** (no premise sentence; a rubber-stamp like "looks fine"; or a checklist instead of a judgment) → **HARD REFUSE.** Do **not** dispatch, do **not** spend compute. Bounce the task back to the promoter: leave it out of `in_progress`, record a one-line reason (e.g. a body note), and route it back (e.g. status `ready` and/or assign to the promoter) so a real premise judgment is recorded before it is queued again.

Hard refuse, not soft warn — a soft warning degrades to advisory and gets sailed past. The refusal is the spend-stopper.

## 3. Honest scope

This gate binds **only the coordinated / `/pull` dispatch path** — everything that flows through `/pull`, `/supervisor`, or `/program`. That is the bulk of agent compute-spend and all polecat dispatch, and it is repo-agnostic (any project, any repo that dispatches through these surfaces). It is **not** universal: a human who opens an editor and hand-codes, or fires a worker by hand, never touches `queued` and this gate cannot see them. The **review backstop** (the generalized premise test in `/strategic-review` arch-fit and `/verify`, plus `/learn` recurrence scoring) is the catch for premises that arrive as direct hand-coded PRs. The pair is surface-agnostic; this source gate alone is not. Do not overclaim it.

## Referenced by

- [[TAXONOMY.md#status-values-and-transitions]] — the `queued` promotion gate
- [[commands/pull]] — dispatch-time refusal
- [[../../supervisor/instructions/worker-dispatch.md]] — pre-dispatch gate
- [[../../program/SKILL.md]] — program-loop dispatch
- [[../../planner/SKILL.md]] — promoter-side recording
- [[../../../../specs/ENFORCEMENT-MAP.md]] — `judgment-non-delegable` enforcement row
