---
alias:
  - wf-review
  - wf-multi-agent-review
description: Universal composite review workflow -- orchestrates independent parallel review across strategic fit, rule compliance, and quality assurance, and defines the shared review briefing used across all review dispatches.
id: wf-review
tags:
  - wf-template
  - review
  - composite
  - briefing
  - gate
title: Multi-Agent Review Workflow
type: template
---

## What this step does

Universal review workflow: coordinates parallel, independent review across three non-overlapping review roles -- strategic fit, rule compliance, and runtime quality assurance -- and defines the one shared review briefing drawn on by all review dispatches.

## Shared Review Briefing

All three review roles (`rbg`, `marsha`, `pauli`), whether dispatched as subagents in `/strategic-review`, minted as review tasks in `/reify`, or composed in workflow templates, receive their briefing drawn from this shared structure. The brief presents the originating request before the artifact or diff under review, so reviewers evaluate intent and proportion before inspecting implementation details.

### Structure of the Brief

1. **Originating Request (Read First)**:
   The originating request is quoted verbatim with its source identifier, before any link to the pull request, branch name, or diff:
   ```markdown
   ## Originating Request

   > [The verbatim text of the user request, commission, or parent task ask authorizing this work]

   - **Source**: `<source-id-or-task-id>`
   ```

2. **Target Artifact**:
   The candidate change or deliverable under review (read only after the originating request):
   - **Repository**: `<owner/repo>`
   - **Pull Request**: `<PR URL and number>`
   - **Branch / Head Commit**: `<branch-name> / <commit-sha>`
   - **Diff / Content**: `<diff or artifact reference>`

3. **Review Role & Instructions**:
   The review criteria and obligations specific to the assigned role, drawn from its workflow template:
   - **Rule Compliance (`rbg`)**: Evaluates against governing axioms and project rules per `wf-rbg`. From the quoted request alone, state the smallest proportionate mechanism before reading the diff.
   - **Quality Assurance (`marsha`)**: Verifies runtime execution, tests, probes, and empirical claims against primary sources per `wf-qa`.
   - **Strategic Fit (`pauli`)**: Evaluates objective alignment, parsimony, necessity, and lifecycle coherence across the task graph per `wf-strategic-fit`.

## Input contract

The invoking workflow provides:

1. **Originating request** -- the commissioning ask with its source id, quoted verbatim.
2. **Target artifact** -- the file, diff, PR reference, or specification under review.
3. **Acceptance criteria** -- explicit requirements and constraints from the commissioning task.
4. **Strategic context** -- parent task, target objectives, or problem definition.

## Composite Stages

A composite review workflow specifies its stages by contract expectations in order:

1. **Strategic fit evaluation**: An independent strategic evaluation situating the artifact against parent objectives, parsimony, and precedent, returning an explicit `FIT` or `MISFIT` verdict (per `wf-strategic-fit`).
2. **Rule compliance evaluation**: An independent rule-compliance evaluation testing mechanisms and decisions against governing axioms and rules without running test suites or probes, returning `APPROVE`, `SUGGEST`, `REVISE`, or `REJECT` (per `wf-rbg`).
3. **Quality assurance evaluation**: An independent runtime quality evaluation executing test suites, verifying red-to-green failure traces, running live probes, and auditing empirical evidence, returning `PASS`, `REVISE`, or `FAIL` (per `wf-qa`).
4. **Reconciliation and write-back**: Synthesis of findings into a unified findings table and final verdict (`APPROVE`, `MINOR CHANGES`, `REVISE`, or `REJECT`), recorded persistently to the artifact's tracking record.

## Output contract

A unified review report containing:

- The itemized findings table mapping issues to reviewer roles, feedback, and severities.
- The reconciled overall verdict.
- Persistent write-back to the artifact's task record or review surface.

## When to include

Any major milestone, specification, design proposal, or pull request requiring independent multi-perspective verification prior to merge or release.
