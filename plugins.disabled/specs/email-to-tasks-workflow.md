---
title: Email to Tasks Workflow
type: spec
category: spec
status: draft
permalink: email-to-tasks-workflow
tags:
  - spec
  - email
  - task-capture
---

# Email to Tasks Workflow

Unbuilt. Nothing in this repository implements it.

## Problem

Asked to "check my email for tasks", the agent queries the mailbox, presents a
summary of action items, and stops. Nothing is filed. The context that made each
item legible — which project, why urgent, what it relates to — is lost between
the mailbox and the task graph, and items drop. Email is a primary source of
hard-deadline work (board votes, peer reviews, travel), and manual filing after
reading breaks flow, which is exactly the friction the capture path exists to
remove.

## US1 — Email to tasks

**As** an academic receiving action-heavy mail, **I want** action items
extracted and filed as categorised tasks, **so that** context survives the trip
from mailbox to task graph and nothing is dropped.

Acceptance:

- "Check my email for tasks" creates tasks without further prompting; the skill
  activates on the intent, not on an explicit invocation.
- Each task links back to its source message by `entry_id`, subject, sender, and
  received date, so the original is always recoverable.
- Priority is inferred from message signals — explicit action markers, stated
  deadlines, sender importance.
- Confidence bands govern filing: **>80%** auto-applies the category, **50–80%**
  applies it but flags for review, **<50%** files to inbox tagged
  `#needs-categorization`. Conservative bands are the point — over-extraction is
  recoverable by deleting a task; a missed action is not.
- One message may yield several tasks. Duplicate suppression keys on the source
  `entry_id`, and each message in a thread is treated independently.
- Mail access failure or task-creation failure halts with the error surfaced
  ([`halt-on-failure`](../../lib/axioms/halt-on-failure.md)). Missing context is
  not a failure: file to inbox with `#needs-categorization` and continue.

## US2 — Interactive completion

**As** someone clearing a task list, **I want** every inbox task shown with a
checkbox, **so that** I can archive a batch of finished work in one interaction
rather than one at a time.

Acceptance:

- The task list is read as structured data and presented through the harness's
  own multi-select prompt.
- Selected tasks archive in a single batched operation, and the messages they
  came from archive with them.
- The user is told what was archived.

## Design decisions

**Orchestration, not capability.** This is connective tissue between a mail
source, a knowledge store, and a task backend, each of which stays independent
and usable alone. It owns no data and no storage of its own, and addresses the
task backend through one narrow interface — create a task from a fixed field
set — so it can run against whatever backend is installed without knowing which.

**Categorisation is semantic, not keyword.** Matching a message to a project
goes through semantic search over the knowledge store, because keyword rules
cannot see that a message about a review deadline belongs to the project that
commissioned the review.

**Confirm before creating, until it earns trust.** The first deployment asks
before writing tasks. Auto-creation is unlocked by measured accuracy on real
mail — >80% high-confidence categorisations and <10% false positives over a
sample — not by a date.

## Scope

In: action extraction, context-aware categorisation, priority inference, task
creation through the backend abstraction, source-message metadata linking, and
the batch-archive completion pass.

Out: calendar-deadline integration; auto-archiving mail on task creation as a
standing behaviour (US2 archives only on explicit selection); task dependencies;
non-English mail; attachment extraction — tasks link to the message instead.

## Monitoring

Log every task-creation event with the source subject, the extracted action, the
confidence score, and the assigned project. That log is the only way to answer
the questions that decide whether the workflow is working: is the confidence
distribution healthy, and how often does a categorisation get corrected by hand?
Failed extractions log separately so a human can recover them.

Targets: >60% of categorisations high-confidence, <20% manually recategorised,
<5% false positives. False negatives are not measurable from the log and need
user report.
