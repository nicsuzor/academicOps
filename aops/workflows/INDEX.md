---
id: workflows-index
title: Workflow Template Library Index
type: index
description: Peer library of process and gate templates, consumed equally by hydrate, decompose, and brief
permalink: workflows-index
---

# Workflow Template Library

The shared substrate the pipeline composes from (spec `10-workflow-library.md`).
Templates are short markdown files read and composed **in-context, by
comprehension** — never parsed or solved. Two kinds:

- **Process templates** (`process/`) — how a class of work proceeds. Carry
  routing signals, NOT-this signals, unique steps, exit routing.
- **Workflow templates (formerly Gate templates)** (living in the PKB as `wf-*` templates) — reusable QA/vetting/approval obligations.
  _Door-type (two-way vs. one-way) is expressed as which templates get
  composed in_ — one vocabulary for proportionate process everywhere.

Frontmatter dependency hints (`requires` / `pairs-with` / `conflicts` /
`recommends`) are the only vocabulary a composer reasons over — no solver, no
richer ontology. `requires` = fragments this template always pulls in;
`pairs-with` = templates/gates composed proportionate to stakes, not always;
`recommends` = soft suggestion; `conflicts` = mutually exclusive with.

**Project-local extension**: a project's `.agent/workflows/*.md` and
`.agent/WORKFLOWS.md` override/extend this library the same way they always
have — project-scoped procedures win over the generic template for that
project.

## Routing (the surviving decision tree)

Multiple intents in one prompt → split and route each independently, one
template per intent.

```
Request
  |
  +-- Framework-modification intent (checked FIRST, always)? -> [[framework-gate]]
  |
  +-- Explicit skill mentioned? -----------------------------> [[simple-question]] + invoke skill directly
  +-- Simple question only? ---------------------------------> [[simple-question]]
  +-- Continuation of active session work? -------------------> [[interactive-followup]]
  +-- New idea / fragment / constraint? -----------------------> strategic-intake (situate stage)
  +-- Break down a goal/epic? ----------------------------------> decompose (pipeline stage, not this library)
  +-- Multiple similar items? -----------------------------------> [[batch]] (or [[burst]] if multi-session)
  +-- Email/communications? -------------------------------------> [[email-triage]]
  |       +-- Extracting a ready-to-work task from an email? ---> [[email-capture]]
  |       +-- Drafting a reply? ---------------------------------> [[email-reply]]
  +-- Academic/research task?
  |       +-- Review a submission? -------------------------------> [[peer-review]]
  |       +-- Reference letter? -----------------------------------> [[reference-letter]]
  |       +-- Finalize a report after feedback? ---------------------> [[finalize-report]]
  |       +-- Reply to docx review comments? ----------------------> [[review-response]]
  +-- Bug or issue?
  |       +-- Cause unknown -----------------------------------------> [[investigation]]
  |       +-- Cause known, clear fix -------------------------------> [[feature-dev]]
  +-- Planning/designing known work? -------------------------------> [[feature-dev]] or [[develop-specification]]
  +-- Sharing/sending/publishing externally? -----------------------> [[wf-outbound-review]] (workflow template)
  +-- Need QA verification? -----------------------------------------> [[wf-qa]] or [[wf-verification]] (workflow templates)
  +-- Human corrected an agent assumption? --------------------------> [[correction-capture]]
  +-- Decision needed to unblock work? ------------------------------> [[decision-briefing]]
  +-- Testing a new framework approach? -----------------------------> [[experiment-design]]
  +-- Checking for framework bloat/duplication? ---------------------> [[monitor-prevent-bloat]]
  +-- PRs need triage/review? ----------------------------------------> [[pr-review]] -> [[worktree-merge]]
  +-- Framework self-improvement session? ----------------------------> [[dogfooding]]
  +-- Post-session transcript review? --------------------------------> [[session-effectiveness]]
  +-- Framework governance/structure audit? --------------------------> [[audit]]
  +-- No branch matched? ----------------------------------------------> ask the user to clarify
```

## Process Templates

### Development & Investigation

| Template                     | Routing description                              | Requires           | Pairs-with                     |
| ---------------------------- | ------------------------------------------------ | ------------------ | ------------------------------ |
| [[feature-dev]]              | Test-first feature/known-cause-bug, idea to ship | task-tracking, tdd | [[wf-verification]], [[wf-handover]] |
| [[investigation]] (fragment) | Hypothesis→probe→conclude for unknown-cause work | —                  | memory-capture                 |

### Email & Communications

| Template          | Routing description                            | Requires      | Pairs-with     |
| ----------------- | ---------------------------------------------- | ------------- | -------------- |
| [[email-triage]]  | Classify inbox into Task/FYI/Skip/Uncertain    | task-tracking | [[wf-handover]] |
| [[email-capture]] | Extract a ready-to-work task with attachments  | task-tracking | [[wf-handover]] |
| [[email-reply]]   | Draft (never send) a reply in the user's voice | task-tracking | [[wf-handover]] |

### Academic

| Template             | Routing description                                                                                                                    | Requires      | Pairs-with             |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------------------- |
| [[peer-review]]      | Grant/fellowship/paper review, read to submit                                                                                          | task-tracking | [[wf-handover]]        |
| [[reference-letter]] | Request → draft → review → send a reference letter                                                                                     | task-tracking | [[wf-handover]]        |
| [[finalize-report]]  | Revise a report after reviewer/stakeholder feedback (id: `report-finalization`; filename avoids the harness's report-file write guard) | task-tracking | [[wf-outbound-review]] |
| [[review-response]]  | Threaded docx replies showing how each comment was addressed                                                                           | task-tracking | —               |

### Operations & Batch

| Template                      | Routing description                                   | Requires                      | Pairs-with                            |
| ----------------------------- | ----------------------------------------------------- | ----------------------------- | ------------------------------------- |
| [[batch]] (fragment)          | Parallel processing of independent items, one session | —                             | task-tracking                         |
| [[burst]] (fragment)          | Multi-session stateful batch lifecycle                | task-tracking                 | —                                     |
| [[external-batch-submission]] | Submit/monitor/retrieve external batch API jobs       | task-tracking, [[wf-verification]] | —                                     |
| [[worktree-merge]]            | Merge a `merge_ready` worktree branch to main         | —                             | [[wf-handover]]                       |
| [[pr-review]]                 | Triage PRs, dispatch reviewers, synthesize verdicts   | batch                         | worktree-merge, [[wf-human-approval]] |

### Session & Routing

| Template                 | Routing description                                       | Requires           | Pairs-with                                    |
| ------------------------ | --------------------------------------------------------- | ------------------ | --------------------------------------------- |
| [[simple-question]]      | Pure information request — answer and halt                | —                  | —                                             |
| [[interactive-followup]] | Bounded follow-up in an active session, skip re-hydration | [[wf-verification]] | —                                             |
| [[framework-gate]]       | Detect framework-modification intent, checked first       | —                  | develop-specification, [[wf-human-approval]] |

### General & Decision Support

| Template                  | Routing description                                       | Requires      | Pairs-with           |
| ------------------------- | --------------------------------------------------------- | ------------- | -------------------- |
| [[decision-briefing]]     | Structured consequence briefing for a blocked decision    | task-tracking | [[wf-human-approval]] |
| [[experiment-design]]     | Design/run/evaluate a discrete framework experiment       | task-tracking | [[wf-verification]]   |
| [[develop-specification]] | Collaboratively spec a feature/automation before building | task-tracking | [[wf-human-approval]] |

### Meta & Framework Governance

| Template                  | Routing description                                                              | Requires       | Pairs-with            |
| ------------------------- | --------------------------------------------------------- | -------------- | --------------------- |
| [[monitor-prevent-bloat]] | Detect and remove doc/skill bloat and duplication                                | —              | [[wf-verification]]   |
| [[session-effectiveness]] | Qualitative transcript assessment of framework performance                       | —              | dogfooding            |
| [[dogfooding]]            | Execute→reflect→codify self-improvement loop (supersedes duplicate `reflect.md`) | memory-capture | session-effectiveness |
| [[correction-capture]]    | Capture a human's mid-session correction as a durable fix                        | memory-capture | —                     |
| [[audit]]                 | Framework governance audit — structure, indices, tests, report                   | [[wf-handover]] | monitor-prevent-bloat |

### Fragments (composed, not routed to directly)

| Fragment           | What it does                                          |
| ------------------ | ----------------------------------------------------- |
| [[task-tracking]]  | Duplicate-check, resolve parent, claim, log, complete |
| [[tdd]]            | Red-green-refactor cycle                              |
| [[memory-capture]] | Store durable findings to the PKB                     |

## Workflow Templates (formerly Gate Templates)

| Template             | Door-type            | Stakes                                                                       | Skip-when                                                                    |
| -------------------- | -------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [[wf-verification]]  | two-way              | Shifting goalposts / "looks done" on routine work                            | Trivial changes                                                              |
| [[wf-qa]]            | two-way              | Feature-complete/user-facing work ships without independent evidence         | Trivial, or user waives                                                      |
| [[wf-outbound-review]] | one-way            | External deliverable ships with an uncaught strategic/factual/tonal error    | Still an internal draft, or audience already trusted                         |
| [[wf-handover]]      | two-way (asymmetric) | Session abandoned with no PR/commit/task-update — traceability lost          | No file modifications made                                                   |
| [[wf-constraint-check]] | two-way            | A composed plan silently violates its own templates' rules                   | No declared constraints, or single atomic action                             |
| [[wf-human-approval]] | one-way             | An irreversible/highly consequential action executes on agent judgment alone | Action is two-way-door, or already covered by a named standing authorisation |

`wf-human-approval` is a **newly authored** template — it did not exist in the
migrated library; it was a flagged gap this migration fills, and is the template
[[framework-gate]], [[wf-outbound-review]], [[pr-review]], and
[[decision-briefing]] all hand off to at their one-way-door crossing.
