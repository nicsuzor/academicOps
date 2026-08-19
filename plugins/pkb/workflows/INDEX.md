---
id: workflows-index
title: Workflow Template Library
type: index
description: The process templates this plugin ships, and how to route to them.
permalink: workflows-index
---

# Workflow Template Library

Short markdown files describing how a class of work proceeds. They are read and
composed **in context, by comprehension** — never parsed, never solved. The
composition procedure is [`../skills/brief/SKILL.md`](../skills/brief/SKILL.md)
§5; this file is the catalogue and the routing tree.

**Routing and composition are different jobs.** The tree below routes an ask to
the template for its class of work, and most of what it routes never reaches
composition — a simple question is answered and halted, a follow-up continues
the session, an email is triaged. Any agent reads the tree directly; no skill
stands between them and it. Only work released for dispatch gets a full process
assembled around it, and that is `brief`'s job.

Two kinds: **process templates** in `process/` — how a class of work proceeds —
and the `wf-*` obligation templates, which are not files at all (see "Obligation
templates" below). Every name in this library is written as it resolves: a
`process/` template by its bare filename, an obligation by its `wf-` permalink.

## Routing

Multiple intents in one prompt split and route independently, one template each.

```
Request
  |
  +-- Framework-modification intent (checked FIRST, always)? --> [[framework-gate]]
  |
  +-- Explicit skill named? -----------------------------------> [[simple-question]] + invoke the skill
  +-- Simple question only? -----------------------------------> [[simple-question]]
  +-- Continuation of active session work? --------------------> [[interactive-followup]]
  +-- New idea, fragment, or constraint? ----------------------> capture it; `brief` works it out
  +-- Break down a goal or epic? ------------------------------> `brief` (it sizes and cuts)
  +-- Multiple similar items? ---------------------------------> [[batch]], or [[burst]] across sessions
  +-- Email or communications? --------------------------------> [[email-triage]]
  |       +-- Extracting a ready-to-work task from an email? --> [[email-capture]]
  |       +-- Drafting a reply? -------------------------------> [[email-reply]]
  +-- Academic or research task?
  |       +-- Paper from idea to submission? ------------------> [[academic-paper]]
  |       +-- Review a submission? ----------------------------> the `peer-review` skill
  |       +-- Reference letter? -------------------------------> [[reference-letter]]
  |       +-- Finalise a report after feedback? ---------------> [[finalize-report]]
  |       +-- Reply to docx review comments? ------------------> [[review-response]]
  +-- Bug or issue?
  |       +-- Cause established by a read, not assumed --------> [[feature-dev]]
  |       +-- Anything else (a trigger is not a cause) --------> [[investigation]]
  +-- Planning or designing known work? -----------------------> [[feature-dev]] or [[develop-specification]]
  +-- Submitting an external batch API job? -------------------> [[external-batch-submission]]
  +-- Sharing, sending, or publishing externally? -------------> [[wf-outbound-review]]
  +-- Need QA verification? -----------------------------------> [[wf-qa]] or [[wf-verification]]
  +-- Decision needed to unblock work? ------------------------> [[decision-briefing]]
  +-- PRs need triage or review? ------------------------------> [[pr-review]] -> [[worktree-merge]]
  +-- Framework self-improvement, or a mid-session correction? -> the `dogfood` skill
  +-- Post-session transcript review? -------------------------> the `triage` skill, retro mode
  +-- Framework governance or structure audit? ----------------> [[audit]]
  +-- Nothing matched? ----------------------------------------> ask the user to clarify
```

## Process templates

### Development and investigation

| Template          | Routes                                              | Requires           | Pairs with                           |
| ----------------- | --------------------------------------------------- | ------------------ | ------------------------------------ |
| [[feature-dev]]   | Test-first feature or known-cause bug, idea to ship | task-tracking, tdd | [[wf-verification]], [[wf-handover]] |
| [[investigation]] | Hypothesis, probe, conclude — unknown cause         | —                  | [[wf-verification]]                  |

### Email and communications

| Template          | Routes                                           | Requires      | Pairs with      |
| ----------------- | ------------------------------------------------ | ------------- | --------------- |
| [[email-triage]]  | Classify an inbox into task, FYI, skip, unsure   | task-tracking | [[wf-handover]] |
| [[email-capture]] | Extract a ready-to-work task with attachments    | task-tracking | [[wf-handover]] |
| [[email-reply]]   | Draft — never send — a reply in the user's voice | task-tracking | [[wf-handover]] |

### Academic

| Template             | Routes                                                     | Requires      | Pairs with                                    |
| -------------------- | ---------------------------------------------------------- | ------------- | --------------------------------------------- |
| [[academic-paper]]   | Academic paper lifecycle from idea through submission      | task-tracking | [[wf-outbound-review]], [[wf-human-approval]] |
| [[reference-letter]] | Request, draft, review, send                               | task-tracking | [[wf-handover]]                               |
| [[finalize-report]]  | Revise a report after reviewer or stakeholder feedback     | task-tracking | [[wf-outbound-review]]                        |
| [[review-response]]  | Threaded docx replies showing how each comment was handled | task-tracking | —                                             |

Reviewing a submission is the `peer-review` skill's job, not a template's — it
owns the scheme criteria and the platform mechanics both.

### Operations and batch

| Template                      | Routes                                                | Requires                           | Pairs with                            |
| ----------------------------- | ----------------------------------------------------- | ---------------------------------- | ------------------------------------- |
| [[batch]]                     | Parallel processing of independent items, one session | —                                  | task-tracking                         |
| [[burst]]                     | Multi-session stateful batch lifecycle                | task-tracking                      | —                                     |
| [[external-batch-submission]] | Submit, monitor, retrieve external batch API jobs     | task-tracking, [[wf-verification]] | —                                     |
| [[worktree-merge]]            | Merge a merge-ready worktree branch                   | —                                  | [[wf-handover]]                       |
| [[pr-review]]                 | Triage PRs, dispatch reviewers, synthesise verdicts   | batch                              | worktree-merge, [[wf-human-approval]] |

### Session and routing

| Template                 | Routes                                              | Requires            | Pairs with                                   |
| ------------------------ | --------------------------------------------------- | ------------------- | -------------------------------------------- |
| [[simple-question]]      | Pure information request — answer and halt          | —                   | —                                            |
| [[interactive-followup]] | Bounded follow-up in an active session              | [[wf-verification]] | —                                            |
| [[framework-gate]]       | Detect framework-modification intent, checked first | —                   | develop-specification, [[wf-human-approval]] |

### Decision support

| Template                  | Routes                                                 | Requires      | Pairs with            |
| ------------------------- | ------------------------------------------------------ | ------------- | --------------------- |
| [[decision-briefing]]     | Structured consequence briefing for a blocked decision | task-tracking | [[wf-human-approval]] |
| [[develop-specification]] | Spec a feature or automation before building it        | task-tracking | [[wf-human-approval]] |

### Framework governance

| Template  | Routes                                               | Requires        | Pairs with |
| --------- | ---------------------------------------------------- | --------------- | ---------- |
| [[audit]] | Governance audit — structure, indices, tests, report | [[wf-handover]] | —          |

The self-improvement loop, mid-session correction capture, experiment
pre-registration, and post-session transcript review are all owned by skills —
`dogfood` and `triage` — not by templates. Route to the skill.

### Fragments

Composed into other templates; never routed to directly.

| Fragment          | Does                                                  |
| ----------------- | ----------------------------------------------------- |
| [[task-tracking]] | Duplicate-check, resolve parent, claim, log, complete |
| [[tdd]]           | Red, green, refactor                                  |

## Obligation templates

The `wf-*` review and gate obligations are read from the PKB, not from here: the
current set is enumerated by the `pkb-workflow-index` MoC
(`get_document("pkb-workflow-index")`), with `list_documents(tag="wf-template")`
as the reconciliation sweep. This file does not list them — a second copy of that
table drifts.

`wf-human-approval` is where [[framework-gate]], `wf-outbound-review`,
[[pr-review]], and [[decision-briefing]] all hand off at their one-way crossing.
