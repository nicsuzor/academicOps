---
description: Sequence asks requiring grounded investigation, specification, independent review, route selection, and test-first implementation delivered on one PR.
id: wf-research-and-implement
tags:
  - wf-template
  - composite
  - research
  - spec
  - implementation
title: Research and Implementation Workflow
type: template
---

## What this step does

Sequences work that requires upfront investigation and a reviewed design before engineering begins. Composing agents fill each stage with components matching its input/output contract.

## Stages

1. **Research**: Grounded findings on the problem space, constraints, and candidate approaches with primary citations and a recommended direction, recorded in the knowledge base.
2. **Spec**: Complete design, interface contracts, and falsifiable acceptance criteria mapped to verification, drafted in a knowledge-base note referenced by the implementation task. Stage 1 commits no standalone plan/design file and opens no PR.
3. **Independent review**: Verdicts on both research and spec from non-authoring agents covering factual claims, rule compliance, and proportionality. Resolve defects before advancing; never release as `review` or send a standalone spec for user approval.
4. **Route decision (when alternatives compete)**: Evaluate options on the record and select the recommended route to unblock implementation; assign a decision to the user only when the user explicitly reserved that choice.
5. **Implementation**: Separate dependent task (`needs` the research/spec task) executing test-first for code. Opens one draft PR onto the base branch carrying both the build and editable spec, and marks it ready for review only after independent verification passes and review verdicts are posted to the PR thread.

## Composition

Structure either as a single task with subtasks (one continuous session) or as a dedicated epic with `needs`-chained child tasks (never loose siblings). Requested spec revisions return to Stage 2 before implementation proceeds.

## Output contract

- Research findings with primary citations and, where alternatives competed, the selected route rationale recorded in the knowledge base.
- Full specification drafted in a knowledge-base note referenced by the implementation task, with no pre-build PR opened.
- Independent review verdicts on research and spec recorded on the task or note.
- Implementation and spec committed together on a single PR onto the base branch, marked ready once independent verification and review verdicts are posted.

## When to include

Asks to research, design, and build a capability where the design must be verified before implementation effort is committed.
