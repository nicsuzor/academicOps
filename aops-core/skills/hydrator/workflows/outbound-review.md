---
id: outbound-review
name: outbound-review
category: quality-assurance
bases: [base-task-tracking, base-qa, base-handover]
description: Multi-agent review gate for any deliverable before it leaves the team (reports, emails, publications, presentations)
permalink: workflows/outbound-review
tags: [workflow, review, quality, outbound, publication]
version: 1.0.0
---

# Outbound Review Workflow

**Purpose**: Ensure that anything shared externally (reports, emails, publications, presentations) passes independent review on three dimensions: alignment, quality, and voice. Each dimension is reviewed by a separate agent to prevent groupthink.

**When to invoke**: Task involves sharing, sending, publishing, or circulating a deliverable to external stakeholders. Routing signals: "send to", "share with", "circulate", "publish", "submit draft".

**Composes**: [[base-qa]] for each review pass.

## Core Principle

**Three independent lenses, then human judgment.** No single reviewer can catch everything. Alignment catches strategic drift, quality catches technical errors, voice catches tone mismatch. The human makes the final call.

## Decomposition Pattern

When a "share/send/publish" task is identified, decompose it into these subtasks:

### 1. Alignment Review (agent)

Does the deliverable serve its stated purpose?

**Criteria to lock** (per [[base-qa]]):

- Research questions / objectives are answered
- Findings are framed correctly for the audience and context
- Methodology decisions are justified and limitations honestly stated
- Nothing could mislead decisions downstream
- Scope matches what was promised (no silent omissions, no scope creep)

**Evidence**: Read the deliverable end-to-end. Cross-reference against the task/epic that commissioned it. Check for claims without supporting evidence.

**Output**: Structured verdict (PASS/FAIL/ESCALATE) per section, with specific citations.

### 2. Quality Review (agent)

Is the deliverable technically correct and internally consistent?

**Criteria to lock**:

- Statistics, numbers, and figures match source data / code outputs
- Tables are internally consistent (rows sum correctly, labels match)
- No stale content from earlier versions
- Figures are legible, labeled, and referenced correctly in text
- Citations and cross-references resolve
- No broken formatting, rendering artifacts, or orphaned content

**Evidence**: Compare claims against code/data. Spot-check representative figures. Verify internal cross-references.

**Output**: Structured verdict per section, with specific error citations.

### 3. Voice Review (agent)

Is the tone appropriate for the audience?

**Criteria to lock**:

- Accessible to the target audience (no unexplained jargon)
- Neutral framing (not advocacy, unless advocacy is the purpose)
- Consistent terminology throughout
- Appropriate hedging on uncertain claims (especially classifier limitations, statistical caveats)
- Professional but not stilted
- No AI-generated filler or excessive qualifications

**Evidence**: Read for tone. Flag jargon, inconsistent terms, unsupported confidence, or unnecessary hedging.

**Output**: Structured verdict with specific passages cited.

### 4. Verify and Send (human)

Review agent findings. Address any FAIL/ESCALATE items. Make final send decision.

**This step is always assigned to the human** — agents do not send external communications autonomously.

## Task Creation

See [[outbound-review-details]] for the full subtask creation template and scaling options.

Key rules:

- Each review is a separate subtask under the share task
- Verify-and-send depends on all three reviews, assigned to human
- Reviews identify issues; they don't rewrite (rewriting is a separate task)
- The agent that produced the deliverable must NOT review it
