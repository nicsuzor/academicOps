---
id: finalize-report
type: template
kind: process
category: academic
description: Finalize/revise an academic report after reviewer or stakeholder feedback — discovery before any edits
requires: [task-tracking]
pairs-with: [wf-outbound-review]
conflicts: []
version: 1.0.0
permalink: workflows-process-report-finalization
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---
> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Academic Report Finalization

**Trigger**: finalize, revise, or prepare a research report for release,
especially after reviewer/stakeholder feedback. **Principle**: front-load all
information gathering — never begin editing until the full picture of what
needs to change, and why, is known.

## Phase 1: Discovery (before ANY edits)

Search for existing artifacts, reviewer comments, tracked changes, and prior
session decisions already settled. Read the current draft end-to-end. Assess
the evidence base: what claims are made, what supports each, where are the
weakest claims. Consolidate ALL feedback into one actionable list, grouped
must-do / should-do / future-work, cross-referenced against prior decisions.
**Gate**: user reviews the consolidated feedback and confirms the approach for
genuine decision points before Phase 2.

## Phase 2: Planning

Build a task tree organised by report section, each task citing the specific
reviewer items it addresses. Link related PKB artifacts. Mark data-dependent
items. **Gate**: user approves the task tree; execute autonomously after.

## Phase 3: Implementation

Execute the approved task tree.

## Phase 4: Verification

Consistency check (numbers, cross-references, terminology). Walk the
consolidated feedback list — verify every must-do addressed, note deferred
should-dos with rationale. Commit, update tasks, summarize what changed/
deferred/needs review. Before external release, compose [[wf-outbound-review]].

## Anti-patterns

Don't build the task tree before searching PKB. Don't present metrics without
connecting them to the report narrative. Don't ask permission at every phase
transition once the plan is approved. Don't start editing before all feedback
is gathered.
