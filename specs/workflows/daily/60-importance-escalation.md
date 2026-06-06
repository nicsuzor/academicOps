---
title: Importance-to-Visibility Escalation Model
type: spec
permalink: importance-visibility-escalation
description: Defines the model mapping computed task importance to proportional cross-surface visibility, ensuring high-consequence immovable deadlines escalate to unmissable prominence.
tags:
  - surfacing
  - focus-score
  - visibility
  - daily-note
  - overwhelm-dashboard
---

# Importance-to-Visibility Escalation Model

## User Story

**As** an academic with ADHD managing complex research and administrative workloads,\
**I want** high-consequence immovable deadlines to visibly climb in prominence and become visually unmissable as they approach,\
**So that** I never miss critical external grant/university deadlines (like the ARC DP27 assessor deadline) due to them being buried in long, flat lists.

> **Coherence check**: This feature connects to the academicOps narrative by ensuring that computed task importance (focus_score, severity, urgency) is translated into proportional visual prominence. Without this, important tasks carry a high computed score but lack the visibility needed to drive action, defeating the purpose of the tracking system.

## Acceptance Criteria

**CRITICAL**: These criteria are USER-OWNED and define what "done" means. Agents CANNOT modify, weaken, or reinterpret these criteria.

### Success Criteria (ALL must pass)

1. [ ] **Multi-Dimensional Importance Metric**: The escalation calculation combines:
   - Base `focus_score` (representing graph-propagated priority)
   - Consequence severity (`severity` label SEV1–SEV4)
   - Deadline proximity (days until due)
   - Immovability (external hard deadlines vs. internal soft goals)
   - Effort-to-complete (effort estimation vs. remaining time window)
2. [ ] **Monotonic Escalation Curve**: Proportional visibility must climb monotonically as a deadline approaches and remain prominent until completed:
   - A SEV3/SEV4 immovable deadline for a multi-hour/multi-day task must start rising in visibility _at the start of the week at the latest_ (4–5 days out).
   - The task must become visually _unmissable_ in the final 1–2 days.
3. [ ] **Concretely Defined Visibility Tiers**:
   - **Tier 1 (Standard)**: Rendered in standard lists without special highlighting.
   - **Tier 2 (Elevated)**: Rendered with warning badges and high-focus grouping.
   - **Tier 3 (Prominent)**: Hoisted to the top of surfaces (e.g., above the calendar in the daily note; highlighted on the dashboard).
   - **Tier 4 (Unmissable)**: Renders a blockquote/alert card with verbatim consequence prose, blocks CLI session start, and flashes prominently on the dashboard.
4. [ ] **Satisfies ARC DP27 Assessor case study**: Replaying the Mon–Fri trace of the DP27 deadline (SEV3 consequence, immovable, 1-day effort) must trigger the following states:
   - **Monday (4 days out)**: Tier 2 (Elevated) — highlighted with an inline warning badge in the high-focus table.
   - **Tuesday (3 days out)**: Tier 3 (Prominent) — hoisted to `## 🚨 ESCALATED DEADLINES` at the very top of the daily note.
   - **Wednesday (2 days out)**: Tier 4 (Unmissable) — hoisted at the top of the daily note with a red alert block showing the verbatim consequence prose, and causing a terminal session warning.

### Failure Modes (If ANY occur, implementation is WRONG)

1. [ ] **Silence by Status Filtering**: High-focus tasks with deadlines are filtered out because they are in `blocked` or `in_progress` status (violating H91).
2. [ ] **Paraphrased Consequences**: Consequence text is editorialized or paraphrased rather than printed verbatim from the task's metadata.
3. [ ] **Flat List Surfacing**: The deadline is presented as a single row in a large table, requiring manual scanning rather than structural hoisting.
4. [ ] **False Urgency Inflation**: Short, low-consequence, or movable tasks escalate to Tier 3/4, creating visual noise that dilutes the signal of true terminal obligations.

---

## Context

**Date**: 2026-06-05\
**Status**: approved\
**Priority**: P1

## Problem Statement

Computed importance (`focus_score`) currently fails to map to proportional visual visibility. A task like the ARC DP27 assessor deadline carries a high and rising focus score all week, but remains one row among many in the daily's deadline and high-focus tables. Because there is no visual escalation curve, the user can easily miss high-consequence immovable deadlines. Furthermore, the consequence dimension has not been structurally factored into the visibility logic.

## Scope

### In Scope

- Mathematical and logical model defining four Visibility Tiers based on computed importance.
- Concrete visual/structural rules for each Visibility Tier on three surfaces:
  1. **Daily Note**: Hoisting logic, warning badges, and verbatim consequence alert blocks.
  2. **Overwhelm Dashboard**: Visual sizing, coloring, and alert overlays.
  3. **Shell/CLI Interlocks**: Login/session-start warnings.
- Low-risk implementation for the daily note compiler (`SKILL.md` and `note-template.md`).
- Formulation of follow-up implementation subtasks for the Overwhelm Dashboard and CLI shell hooks.

### Out of Scope

- Modifying the underlying Rust `compute_focus_scores` algorithm inside the `mem` PKB codebase.
- Implementing the dashboard frontend changes in Svelte (spun out as a separate task).
- Implementing the shell profile scripts/hooks (spun out as a separate task).

---

## The Escalation Model

To map a task's absolute state to a Visibility Tier, we define a two-stage process: computing the **Slack Ratio** (effort vs. remaining time) and determining the **Visibility Tier** using explicit logic gates.

### 1. Inputs

Let a task $T$ carry the following properties:

- $FS \in \mathbb{N}_0$: The base `focus_score` computed by the PKB.
- $S \in \{0, 1, 2, 3, 4\}$: The consequence severity (SEV0–SEV4).
- $M \in \{\text{true}, \text{false}\}$: Immovability (whether the deadline is set by an external agency and cannot be moved).
- $T_{\text{due}} \in \mathbb{Z}$: Days until the due date ($t_{\text{due}} - t_{\text{now}}$).
- $E \in \mathbb{R}^+$: Effort estimation in days. For task efforts:
  - `XS` / `2h` = 0.25 days
  - `S` / `4h` = 0.5 days
  - `M` / `1d` = 1.0 day
  - `L` / `3d` = 3.0 days
  - `XL` / `5d` = 5.0 days
  - Default (if unspecified): 0.1 days (1 hour).

### 2. Slack Ratio (SR)

The **Slack Ratio** represents the portion of the remaining time window that must be spent working to complete the task. The overdue case is a separate branch — it is not derived from the formula:

$$SR = \begin{cases} 1.0 & \text{if } T_{\text{due}} \le 0 \ \text{(overdue, critical)} \\[4pt] \dfrac{E}{\max(0.5,\, T_{\text{due}})} & \text{otherwise} \end{cases}$$

A higher $SR$ indicates a closing window. For example, a 1-day task due in 2 days has $SR = 1.0 / 2.0 = 0.5$ (high pressure).

### 3. Visibility Tier Gate Logic

Tasks are mapped to one of four **Visibility Tiers** based on their properties and urgency. The highest matching tier applies:

```
         ┌───────────────────────────────┐
         │      Start: Evaluate Task     │
         └───────────────┬───────────────┘
                         ▼
Is T_due <= 0 AND S >= SEV2?             ──(Yes)──>  [ Tier 4: Unmissable ]
Or S >= SEV3 AND T_due <= 2?             ──(Yes)──>  [ Tier 4: Unmissable ]
Or S >= SEV2 AND M == True AND T_due <= 2? ──(Yes)──>  [ Tier 4: Unmissable ]
Or SR >= 0.5 AND T_due <= 2 AND S >= SEV2? ──(Yes)──>  [ Tier 4: Unmissable ]
                         │
                       (No)
                         ▼
Is S >= SEV3 AND T_due <= 3?             ──(Yes)──>  [ Tier 3: Prominent ]
Or S >= SEV2 AND M == True AND T_due <= 3? ──(Yes)──>  [ Tier 3: Prominent ]
Or SR >= 0.35 AND T_due <= 5 AND S >= SEV2? ──(Yes)──>  [ Tier 3: Prominent ]
                         │
                       (No)
                         ▼
Is S >= SEV2 AND T_due <= 7?             ──(Yes)──>  [ Tier 2: Elevated ]
Or S >= SEV1 AND M == True AND T_due <= 5? ──(Yes)──>  [ Tier 2: Elevated ]
Or SR >= 0.20 AND T_due <= 7 AND S >= SEV2? ──(Yes)──>  [ Tier 2: Elevated ]
                         │
                       (No)
                         ▼
              [ Tier 1: Standard ]
```

---

## Surface-Specific Definitions of "Unmissable"

### 1. Daily Note Surface

A new section `## 🚨 ESCALATED DEADLINES` is introduced at the **very top** of the daily note (above `## Today's calendar`). This section is rendered dynamically:

- **Tier 3 (Prominent)** tasks are listed at the top of this section:
  ```markdown
  - [ ] **[task-id]** [[Title]] — due YYYY-MM-DD (Nd away) — **[⚠ SEV3 IMMOVABLE]** (Effort: E)
  ```
- **Tier 4 (Unmissable)** tasks are rendered as callout alert blocks containing the verbatim `consequence` text:
  ```markdown
  > [!CAUTION]
  >
  > ### 🚨 CRITICAL DEADLINE: [task-id] [[Title]]
  >
  > **Consequence if missed**: <Verbatim consequence prose>\
  > **Due**: YYYY-MM-DD (Nd away / today) | **Effort**: E\
  > [ ] **Action Required**: Resolve or progress this task immediately.
  ```

If no tasks meet Tier 3 or Tier 4 criteria, the `## 🚨 ESCALATED DEADLINES` section is omitted entirely.

### 2. Overwhelm Dashboard Surface

- **Tier 1 (Standard)**: Standard node size ($r$), default node coloring.
- **Tier 2 (Elevated)**: Node size increased to $1.5r$. Node border color set to orange.
- **Tier 3 (Prominent)**: Node size increased to $2.5r$. Node border color set to red with a glowing/pulsing box-shadow. Hoisted to the dashboard's "High Focus" panel list with a warning icon.
- **Tier 4 (Unmissable)**: Node size set to $4.0r$ (maximum scaling limit). Flashing red background. On dashboard load, a blocking **Modal Alert Overlay** is shown, forcing the user to acknowledge the consequence before proceeding to view the rest of the workspace.

### 3. CLI / Shell Interlock Surface

An automated check is injected into the shell prompt initialization or tool-use hooks (`PreToolUse`):

- If any task is in **Tier 4 (Unmissable)**, the terminal outputs a high-contrast ASCII block on start:
  ```
  ======================================================================
  🚨 UNMISSABLE DEADLINE TODAY / TOMORROW 🚨

  Task ID:     [task-id]
  Title:       [[Title]]
  Due Date:    YYYY-MM-DD (due today / 1d away) [IMMOVABLE]
  Effort:      E
  Consequence: <Verbatim consequence prose>

  Please acknowledge or perform work on this task immediately.
  ======================================================================
  ```

---

## Integration Test Design

### Test Setup

Prepare a mock PKB with three tasks:

1. `task-dp27`: `severity: 3`, `due: <today+2 days>`, `effort: M` (1.0 day), `consequence: "SEV3 consequence if missed"`, `goals: [target-dp27]`, where `target-dp27` is `severity: 3`, `immovable: true`.
2. `task-routine`: `severity: 0`, `due: <today+2 days>`, `effort: XS` (0.25 days), no consequence.
3. `task-overdue`: `severity: 2`, `due: <yesterday>`, `effort: S` (0.5 days), `consequence: "SEV2 overdue consequence"`.

### Test Execution & Validation

1. Run the daily note generation script.
2. **Verify Tier 4 hoisting**: Assert that `task-dp27` and `task-overdue` are rendered in a `## 🚨 ESCALATED DEADLINES` section at the top of the note (above calendar).
3. **Verify Consequence Verbatim**: Assert that the string `"SEV3 consequence if missed"` appears verbatim inside a `[!CAUTION]` block for `task-dp27`, and `"SEV2 overdue consequence"` appears verbatim for `task-overdue`.
4. **Verify Tier 1 exclusion**: Assert that `task-routine` does NOT appear in the `## 🚨 ESCALATED DEADLINES` section (remains in the standard list).

---

## Implementation Plan & Tasks

To execute this specification across all surfaces, the work is divided into the following tasks:

### Task 1: Core Daily Note Surfacing [Shipped — simplified]

The daily note (`aops-core/skills/daily/SKILL.md` + `references/note-template.md`) hoists
urgent deadlines into `## 🚨 ESCALATED DEADLINES` with verbatim consequence text. To keep
the composer free of arithmetic, the daily skill uses a **single judgment rule** rather than
the full Slack-Ratio/tier computation: hoist when a task is overdue or due within ~2 days
**and** is ≥ SEV2 or on an immovable external deadline. The detailed model in this spec is
the authoritative source for the next task.

### Task 1b: Move escalation-tier computation upstream into the PKB tool [Subtask]

- File a task: the PKB tool emits a computed escalation tier (this spec's Slack-Ratio and
  gate logic) as task metadata, so the daily note and other surfaces consume a field instead
  of re-deriving it. The LLM never does the math.

### Task 2: Overwhelm Dashboard Focus→Size Curve [Subtask]

- File task `mem-overwhelm-dashboard-escalation` to implement the $1.5r \to 2.5r \to 4r$ node-size scaling and the modal overlay for Tier 4 tasks in the Svelte dashboard.

### Task 3: CLI Shell Login Hook [Subtask]

- File task `aops-cli-login-interlock` to implement the `PreToolUse` shell prompt warning block when a Tier 4 task is active in the current workspace.

---

## Completion Checklist

- [ ] Spec document committed and linked in MOC.
- [ ] Daily note template updated to include the `## 🚨 ESCALATED DEADLINES` section.
- [ ] Daily note composer uses the simple judgment rule (no LLM math); tier computation deferred to the PKB tool.
- [ ] Dashboard, CLI interlock, and PKB-tier implementation subtasks created in the PKB.
- [ ] No regression introduced; all existing tests pass.
- [ ] Verified against the ARC DP27 assessor Mon–Fri timeline trace.
