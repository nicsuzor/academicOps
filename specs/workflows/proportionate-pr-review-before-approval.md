---
title: Proportionate PR Review Before Approval
status: ready
---

# Proportionate PR Review Before Approval

This specification establishes the requirement and delivery contract ensuring that any pull request requiring user approval carries an agent-generated review, proportionate to the change's risk and operational blast radius, posted visibly on the pull request thread before the pull request is made available to the user for approval. It eliminates unreviewed approval requests across all workflow tiers and repository lifecycles.

## User stories

### US-1 Pre-Approval Review Gating

As the user, I want every pull request that requires my approval to carry a posted agent-generated review before it is presented to me, so that I can evaluate the change against substantive review findings rather than an unreviewed diff.

- **AC-1.1** Given a pull request whose progression or merge requires user approval, when the pull request is marked ready for review or surfaced for user sign-off, then a completed agent-generated review is already posted on the pull request thread.
- **AC-1.2** Given a pull request awaiting completion of required reviews, when an agent workflow evaluates pull request status, then the pull request remains in draft or un-escalated status without triggering user review notifications.
- **AC-1.3** Given an open pull request requiring user approval that currently lacks a posted review, when a PR sweep or move-along workflow inspects it, then the workflow coordinates or queues a review step rather than classifying the pull request as awaiting user approval.

### US-2 Proportion Calibrated by Risk Tier

As a reviewing agent, I want the depth and formality of the pre-approval review to be proportionate to the risk tier and operational blast radius of the change, so that critical modifications receive rigorous multi-perspective scrutiny while low-risk changes avoid superfluous overhead.

- **AC-2.1** Given a Tier 1 change (low-risk documentation, formatting, typing stubs, or specification drafts), when reviewed, then a single verification pass verifying acceptance criteria and passing checks is posted as a concise receipt.
- **AC-2.2** Given a Tier 2 change (code, workflows, tools, skills, rules, agent definitions, or tests), when reviewed, then a focused dual-lens review covering rule compliance and functional verification against literal acceptance criteria is posted with an explicit verdict.
- **AC-2.3** Given a Tier 3 change (host infrastructure, credentials, public releases, or broad architectural modifications), when reviewed, then a full multi-lens dialectical review covering strategic direction, rule compliance, and runtime quality is posted with structured findings and premise-check receipts.

### US-3 Uniform Workflow Contract Across Tiers

As a workflow author and executor, I want the pre-approval review requirement to apply consistently across universal, project-local, and personal workflow tiers and across all repositories where agents file pull requests, so that no execution path bypasses the review gate.

- **AC-3.1** Given a task finishing via pull request under any finish or handover template, when the deliverable requires user approval, then the workflow posts the proportionate review to the pull request before signaling completion or requesting reviewer sign-off.
- **AC-3.2** Given a PR sweep workflow triaging pull requests across repositories, when an evaluated pull request requires user approval but lacks a posted review, then the sweep categorizes the pull request as queued for review and queues a review task, rather than reporting it as blocked on approval.
- **AC-3.3** Given a PR move-along or merge-prep workflow progressing a pull request, when checks pass but no review is posted, then the workflow coordinates and posts the proportionate review before updating disposition or advancing to approval gates.

## Design

### 1. The Core Invariant

The framework enforces a strict ordering invariant across all pull request lifecycles:

$$\text{Review Generated} \longrightarrow \text{Review Posted to PR Thread} \longrightarrow \text{PR Marked Ready / User Approval Requested}$$

Under no circumstances is a pull request submitted for user approval, tagged for user review, or reported in an awaiting-approval disposition without an agent-generated review already present on the pull request thread.

### 2. Gating Mechanisms

To guarantee this invariant across all execution paths while respecting headless worker boundaries:

1. **Draft Pull Request Gating for Asynchronous Verification**:
   - Any pull request requiring user approval is initially created in draft state.
   - Draft pull requests natively suppress user review notifications, prevent premature merges, and signal incomplete readiness.
   - A subsequent verification or review worker conducts the proportionate review, posts the review receipts to the pull request thread, and only then converts the pull request to ready for review.
   - Headless workers do not pause or block interactively for approval: implementation and review workers release their task claims upon posting deliverables and updating pull request readiness, allowing truth maintenance and scheduled triage to surface ready items to the user asynchronously.

2. **Synchronous In-Task Review for Atomic Deliverables**:
   - Where a task is structured as a self-contained unit completing both authoring and verification in a single run, the worker coordinates an independent subagent dispatch to conduct the review.
   - To eliminate self-review hazard, the task author never evaluates its own diff; review execution is delegated to an isolated review subagent.
   - The review findings are posted to the pull request thread before the pull request is converted from draft state or released.

3. **Progression and Sweep Guardrails**:
   - Progression workflows auditing open pull requests inspect the pull request thread for completed reviews. If required reviews are absent, the workflow initiates or coordinates the review before advancing merge gates.
   - Sweep workflows categorize unreviewed pull requests requiring approval as queued for review with a designated review step, strictly forbidding classification as awaiting user approval.

### 3. Review Depth and Presentation Standards

The depth, composition, and presentation of the pre-approval review are calibrated directly against the three-tier risk taxonomy:

| Risk Tier | Scope & Characteristics | Review Composition | Review Lenses | Output on PR |
| :- | :- | :- | :- | :- |
| **Tier 1: Low Risk** | Documentation, specs, formatting stubs, non-functional edits. | Single verification pass. | Verification lens. | Verification receipt citing green checks and verified acceptance criteria. Autonomous merge where authorized. |
| **Tier 2: Medium Risk** | Code, workflows, tools, skills, rules, agent definitions, or tests. | Dual-lens focused review. | Compliance lens + Verification lens. | Structured review comment with PASS/FAIL verdict, rule compliance checklist, and acceptance verification receipts. |
| **Tier 3: High Risk** | Infrastructure, security, credentials, public releases, breaking changes. | Multi-lens dialectical review. | Supervisor coordination across Strategic Congruence, Compliance, and Verification lenses. | Comprehensive dialectical review with synthesis table, formal premise checks, and explicit risk boundary audit. |

### 4. Per-Workflow Delivery Guarantees

The pre-approval review gate applies across all inventoried workflow classes:

1. **Finish-Type Workflows** (Universal, Project, and Personal Finish Templates):
   - When the change falls under Tier 2, Tier 3, or repository policies requiring user approval, the worker opens a draft pull request.
   - The independent verification task or subagent conducts the proportionate review, posts findings to the pull request thread, and converts the pull request to ready status.

2. **Move-Along and Merge-Preparation Workflows** (Move-Along and Merge-Prep Templates):
   - Workflows preparing pull requests for user sign-off audit the pull request thread for existing proportionate reviews.
   - If a review is absent, the workflow executes or coordinates the review and posts the verdict to the pull request before advancing to the sign-off gate.

3. **Sweep and Triage Workflows** (Universal PR Sweep Template):
   - Triaging pull requests across repositories evaluates check status and review presence concurrently.
   - Pull requests requiring approval that lack posted reviews are categorized as queued for review and assigned a discrete review step, ensuring the user is never prompted for unreviewed pull requests.

4. **Approval Gate and Sign-Off Loops** (Escalated Approval and Sign-Off Loop Templates):
   - Tasks structured around explicit approval boundaries verify that the linked pull request carries a posted review before filing the artifact for user decision.

5. **Composite and Spec Workflows** (Specification and Framework Change Templates):
   - Multi-stage specifications opening draft pull requests for design review ensure that independent multi-lens reviews are posted to the pull request before human approval is requested.

6. **Session Handover and Exit Surfaces** (Session Handover and Dump Templates):
   - Automated pull request creation during session exit defaults to draft status whenever the deliverable requires subsequent review or user approval.
