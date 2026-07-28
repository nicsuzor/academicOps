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
composition procedure is [`../skills/workflow/SKILL.md`](../skills/workflow/SKILL.md);
this file is the catalogue and the routing tree.

Two kinds:

- **Process templates** — `process/`. How a class of work proceeds: routing
  signals, NOT-this signals, the steps unique to it, and where it exits to.
- **Workflow templates** — the `wf-*` obligations. These are **not files**. They
  live in the PKB as documents tagged `wf-template`; enumerate them with
  `list_documents(tag="wf-template")` and read one with `get_document(id)`. The
  table below is a catalogue, not the source — the PKB is authoritative, and a
  template must be read from it before it is composed in.

Templates in `$ACA_DATA/.agents/workflows/` override a shipped template of the
same filename and extend the library with any new one. `$ACA_DATA` comes from the
environment; if it is unset the user layer simply does not exist.

Four frontmatter hints are the entire vocabulary a composer reasons over:
`requires` (always pulled in), `pairs-with` (composed proportionate to stakes),
`recommends` (a soft suggestion), `conflicts` (mutually exclusive). Door type —
one-way versus two-way — is expressed as which templates get composed in, not as
a separate mechanism.

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
  +-- New idea, fragment, or constraint? ----------------------> the situate skill
  +-- Break down a goal or epic? ------------------------------> the decompose skill
  +-- Multiple similar items? ---------------------------------> [[batch]], or [[burst]] across sessions
  +-- Email or communications? --------------------------------> [[email-triage]]
  |       +-- Extracting a ready-to-work task from an email? --> [[email-capture]]
  |       +-- Drafting a reply? -------------------------------> [[email-reply]]
  +-- Academic or research task?
  |       +-- Review a submission? ----------------------------> [[peer-review]]
  |       +-- Reference letter? -------------------------------> [[reference-letter]]
  |       +-- Finalise a report after feedback? ---------------> [[finalize-report]]
  |       +-- Reply to docx review comments? ------------------> [[review-response]]
  +-- Bug or issue?
  |       +-- Cause unknown -----------------------------------> [[investigation]]
  |       +-- Cause known, fix clear --------------------------> [[feature-dev]]
  +-- Planning or designing known work? -----------------------> [[feature-dev]] or [[develop-specification]]
  +-- Sharing, sending, or publishing externally? -------------> [[wf-outbound-review]]
  +-- Need QA verification? -----------------------------------> [[wf-qa]] or [[wf-verification]]
  +-- Human corrected an agent assumption? --------------------> [[correction-capture]]
  +-- Decision needed to unblock work? ------------------------> [[decision-briefing]]
  +-- Testing a new framework approach? -----------------------> [[experiment-design]]
  +-- Checking for framework bloat or duplication? ------------> [[monitor-prevent-bloat]]
  +-- PRs need triage or review? ------------------------------> [[pr-review]] -> [[worktree-merge]]
  +-- Framework self-improvement session? ---------------------> [[dogfooding]]
  +-- Post-session transcript review? -------------------------> [[session-effectiveness]]
  +-- Framework governance or structure audit? ----------------> [[audit]]
  +-- Nothing matched? ----------------------------------------> ask the user to clarify
```

## Process templates

### Development and investigation

| Template          | Routes                                              | Requires           | Pairs with                           |
| ----------------- | --------------------------------------------------- | ------------------ | ------------------------------------ |
| [[feature-dev]]   | Test-first feature or known-cause bug, idea to ship | task-tracking, tdd | [[wf-verification]], [[wf-handover]] |
| [[investigation]] | Hypothesis, probe, conclude — unknown cause         | —                  | memory-capture                       |

### Email and communications

| Template          | Routes                                           | Requires      | Pairs with      |
| ----------------- | ------------------------------------------------ | ------------- | --------------- |
| [[email-triage]]  | Classify an inbox into task, FYI, skip, unsure   | task-tracking | [[wf-handover]] |
| [[email-capture]] | Extract a ready-to-work task with attachments    | task-tracking | [[wf-handover]] |
| [[email-reply]]   | Draft — never send — a reply in the user's voice | task-tracking | [[wf-handover]] |

### Academic

| Template             | Routes                                                     | Requires      | Pairs with             |
| -------------------- | ---------------------------------------------------------- | ------------- | ---------------------- |
| [[peer-review]]      | Grant, fellowship, or paper review, read to submit         | task-tracking | [[wf-handover]]        |
| [[reference-letter]] | Request, draft, review, send                               | task-tracking | [[wf-handover]]        |
| [[finalize-report]]  | Revise a report after reviewer or stakeholder feedback     | task-tracking | [[wf-outbound-review]] |
| [[review-response]]  | Threaded docx replies showing how each comment was handled | task-tracking | —                      |

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
| [[experiment-design]]     | Design, run, evaluate a discrete experiment            | task-tracking | [[wf-verification]]   |
| [[develop-specification]] | Spec a feature or automation before building it        | task-tracking | [[wf-human-approval]] |

### Framework governance

| Template                  | Routes                                                  | Requires        | Pairs with            |
| ------------------------- | ------------------------------------------------------- | --------------- | --------------------- |
| [[monitor-prevent-bloat]] | Detect and remove doc and skill bloat                   | —               | [[wf-verification]]   |
| [[session-effectiveness]] | Qualitative transcript assessment of performance        | —               | dogfooding            |
| [[dogfooding]]            | Execute, reflect, codify — the self-improvement loop    | memory-capture  | session-effectiveness |
| [[correction-capture]]    | Capture a mid-session human correction as a durable fix | memory-capture  | —                     |
| [[audit]]                 | Governance audit — structure, indices, tests, report    | [[wf-handover]] | monitor-prevent-bloat |

### Fragments

Composed into other templates; never routed to directly.

| Fragment           | Does                                                  |
| ------------------ | ----------------------------------------------------- |
| [[task-tracking]]  | Duplicate-check, resolve parent, claim, log, complete |
| [[tdd]]            | Red, green, refactor                                  |
| [[memory-capture]] | Store durable findings to the PKB                     |

## Workflow templates

Read from the PKB, not from here: the current set is enumerated by the
`pkb-workflow-index` MoC (`get_document("pkb-workflow-index")`), with
`list_documents(tag="wf-template")` as the reconciliation sweep. This file
does not list them — a second copy of that table drifts.

`wf-human-approval` is where [[framework-gate]], [[wf-outbound-review]],
[[pr-review]], and [[decision-briefing]] all hand off at their one-way crossing.
