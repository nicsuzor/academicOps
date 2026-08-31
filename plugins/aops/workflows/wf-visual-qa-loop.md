---
alias:
- wf-visual-qa-loop-wf-visual-qa-loop
- wf-visual-qa-loop
created: 2026-08-19T12:21:20.658336284+00:00
id: wf-visual-qa-loop
last_modified: 2026-08-26T04:00:06.588756103+00:00
modified: 2026-08-26T04:00:06.588752275+00:00
permalink: wf-visual-qa-loop
status: ready
tags:
- wf-template
- workflow
- visual-qa
- marsha
- failsafe
- image-judging
- refine-loop
title: wf-visual-qa-loop
type: template
---

# wf-visual-qa-loop — visual screenshot → judge → revise convergence loop with hard failsafes

**Sequence position**: Stage-2 composite workflow template. Composes [[wf_qa_b4b7f9c5]] (`wf-qa-around`) and [[wf_refine_6ef85da2]] (`wf-refine-loop`) into an automated visual QA and revision cycle.

## Purpose

A portable, closed-loop visual QA cycle for visual and UI components (graphs, dashboards, views, pages). Automates the cycle of rendered screenshot capture, independent multimodal quality evaluation against a verbatim acceptance specification, and targeted code revision until all visual criteria achieve PASS or a hard failsafe terminates the run.

Designed to fail fast, loudly, and legibly: halts with named error signals rather than grinding silently or producing false passes.

---

## Inherited Foundations (Composed by Reference)

This template composes two foundational Stage-2 workflow fragments without duplicating their core definitions:

1. **[[wf_qa_b4b7f9c5]] (`wf-qa-around`)**: Supplies the **Marsha lens** — evaluating whether the rendered artifact achieves excellence and fitness-for-purpose (world-class / outstanding / impossibly good), assuming the artifact is broken until proven otherwise, demanding concrete empirical evidence (rendered screenshots, not source diffs or passing test suites), and requiring explicit failure reasons when evidence is missing.
2. **[[wf_refine_6ef85da2]] (`wf-refine-loop`)**: Supplies the **convergence discipline and identity separation** — structuring the interaction between drafter and reviewer, requiring reviewers to provide actionable feedback, preventing infinite iteration via safety caps, and enforcing strict identity separation between drafter and judge.

---

## Execution Sequence

```
[Round 0: Baseline Capture] 
         │
         ▼
┌───► [Step 1: Drafter Revision] (Pluggable: Claude/Polecat/Agy)
│        │
│        ▼
│     [Step 2: Live Render & Artifact Capture] (Assert Path & Size > 75KB)
│        │
│        ▼
│     [Step 3: Fresh-Context Visual QA Evaluation] (Marsha Lens, Verbatim Spec, Multi-view)
│        │
│        ▼
│     [Step 4: Convergence & Failsafe Gate]
│        ├── All Criteria MET ───────────► [PASS & Merge/Ship]
│        ├── Failsafe 1/2/3/4 Triggered ─► [HALT with Named Failsafe Handback]
└────────┴── Criteria UNMET & Progress ──► (Next Round)
```

### Step 0: Baseline Capture & Referent Anchoring

- **Action**: Before any source code modification is drafted or applied, execute the project capture harness against the baseline environment to generate reference screenshots.
- **Rule**: Source code is not evidence of rendered state. The baseline screenshot set is the permanent comparative referent for regression testing throughout all iteration rounds.

### Step 1: Drafter Revision (Pluggable Drafter)

- **Role**: Specialized coding agent (e.g. Claude Polecat worker, Antigravity/Agy worker).
- **Input**: The unmet binary criteria from the previous round (or baseline gaps for Round 1), accompanied by the exact visual defect descriptions and reference screenshots.
- **Agy Dispatch Invariants**:
  - Any headless `agy` CLI dispatch **MUST** feed its prompt via standard input (`stdin`), e.g., `timeout 30m agy -p < prompt.txt` or `echo "$PROMPT" | timeout 30m agy -p`. Never supply prompts as positional arguments (which blocks indefinitely on open stdin).
  - Any agent execution **MUST** be wrapped in an **external OS `timeout`**, not relying solely on internal flags (e.g., `--print-timeout`).
- **Pluggability & Fallback**: If the chosen drafter hits tool-execution denials or crashes (Failsafe 4b), the harness halts immediately and names the harness failure, allowing operator reconfiguration or fallback to an alternate drafter backend.

### Step 2: Rendered Artifact Capture & Output Path Verification

- **Action**: Execute the visual screenshot test harness against the live running server.
- **Output Integrity Invariants**:
  - The capture step **MUST NOT** rely on the test harness process exit code alone.
  - The harness **MUST** verify:
    1. **Resolved output directory**: Confirm files exist in the designated session artifact path (warning: guard against environment variable fallback traps such as unset `$AOPS_SESSIONS` redirecting output to unexpected local paths).
    2. **File existence & non-trivial size threshold**: Assert that expected screenshot files exist and exceed minimum non-trivial byte size thresholds (e.g. files <= 75KB typically represent blank error pages; valid UI renders typically measure >= 180KB).

### Step 3: Fresh-Context Visual QA Evaluation (Marsha Lens)

- **Role**: Independent verifier (`marsha`).
- **Isolation Contract**:
  - The judge **MUST** run in a completely **fresh context** with zero accumulated iteration history, transcript logs, or prior conversational contamination.
  - The judge receives only:
    1. The visual quality specification containing the **verbatim acceptance bar**.
    2. The current round's rendered screenshot artifacts.
    3. The Round 0 baseline screenshot artifacts.
- **Evaluation Contract**:
  - The judge's brief **MUST quote the user's standing acceptance bar verbatim** (never paraphrased or summarized).
  - One judge evaluates all in-scope views concurrently in the round to detect cross-view regressions and global coherence.
  - The judge returns a **structured binary verdict** (MET / UNMET) per criterion per view, citing specific visual coordinates/regions as checkable evidence.
  - Anti-criteria apply strictly: "I changed the code", "unit tests pass", "diff is non-zero but sub-perceptible", or evaluation against an outdated referent are automatic failures.

### Step 4: Convergence & Failsafe Evaluation

- Calculate the total count of unmet criteria across all views.
- If all views satisfy all criteria -> **PASS** (individual views that pass can be shipped/merged independently).
- If any unmet criteria remain -> check Failsafes 1 through 4. If any failsafe triggers, **HALT immediately** with the corresponding named handback. Otherwise, proceed to Round N+1.

---

## The Four Mandatory Failsafes

Every visual QA run enforces exactly four deterministic failsafes. When a failsafe fires, execution terminates loudly with a structured handback identifying the exact failure mode.

| #     | Failsafe Name                             | Threshold / Trigger Rule                                                                                                                                                                                                                                                                                                                                                                                                                      | Purpose & Failure Classification                                                                                                                                                                                       |
| ----- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Iteration Cap**                         | **Hard limit: N = 5 rounds** (Round 0 baseline + 5 revision cycles max).                                                                                                                                                                                                                                                                                                                                                                      | Prevents unbounded iteration loops and token/time exhaustion. Class: `FAILSAFE_ITERATION_CAP_EXCEEDED`.                                                                                                                |
| **2** | **No-Improvement Detector**               | Stop if `Count(Unmet Criteria in Round R) >= Count(Unmet Criteria in Round R-1)`.                                                                                                                                                                                                                                                                                                                                                             | Detects stagnation, thrashing, or cyclic oscillation across consecutive rounds. Uses the raw integer count of unmet criteria from the structured binary verdict. Class: `FAILSAFE_NO_IMPROVEMENT`.                     |
| **3** | **Wall-Clock Cap**                        | **Max 30m per drafter round, 10m per capture/judge step, cumulative workflow timeout of 120m.** The cumulative cap is authoritative and **binds before** the iteration cap (see precedence note below).                                                                                                                                                                                                                                       | Enforced by external OS `timeout` commands wrapping all process dispatches. Class: `FAILSAFE_WALLCLOCK_TIMEOUT`.                                                                                                       |
| **4** | **Capability Failsafe (Harness Failure)** | Triggers immediately upon detecting any of:<br>**(a) `HARNESS_JUDGE_IMAGE_UNREADABLE`**: Judge model cannot ingest/render PNG images.<br>**(b) `HARNESS_DRAFTER_TOOLS_DENIED`**: Drafter tool calls denied (e.g. `invalid tool call error (invalid_args) Tool call denied with reason:`).<br>**(c) `HARNESS_CAPTURE_BLANK_OR_MISSING`**: Screenshot capture produced 0 images, missing target paths, or files below size threshold (<= 75KB). | **CRITICAL**: Distinguishes harness/tooling defects from visual quality defects. These are classified as Harness Failures, NEVER as visual QA failures of the views. Prevents revising valid code to fix broken tools. |

### Failsafe precedence — the caps do not compose, and that is intended

Failsafes 1 and 3 are not independent budgets. Five drafter rounds at the 30m per-round maximum is 150m of drafter time alone, before capture and judging, which exceeds the 120m cumulative cap. **The cumulative wall-clock cap therefore binds first whenever rounds run long**, and the effective ceiling is roughly four full-length rounds, not five. N = 5 is the ceiling only when rounds finish well inside their per-round budget.

This is a deliberate ordering, not an oversight: the run should end on elapsed time rather than grind out a fifth round it cannot afford. An implementation **MUST** report `FAILSAFE_WALLCLOCK_TIMEOUT` when the cumulative cap is what actually stopped it, and **MUST NOT** report it as an iteration-cap exhaustion — the two say different things about whether the loop was converging.

---

## Structured Verdict & Handback Specification

### 1. Judge Structured Verdict Format (Per Round)

The judge must emit a structured verdict table with binary criteria to enable mechanical parsing by the no-improvement detector:

```markdown
### Visual QA Verdict — Round [R]

| View   | Criterion ID | Description                                | Status | Image Evidence & Region Citation                                                               |
| ------ | ------------ | ------------------------------------------ | ------ | ---------------------------------------------------------------------------------------------- |
| View A | C1           | High-focus elements prominent on cold load | MET    | Dominant central node at (x=450, y=300), 4x radius of background nodes                         |
| View A | C2           | Low-focus elements (<30) suppressed        | UNMET  | 70+ low-focus nodes still rendered with full opacity and legible labels in peripheral quadrant |
| View B | C1           | Spatial separation across severity tiers   | MET    | Clear separation between tier-1 clusters and tier-2 clusters                                   |

**Summary Metric**:

- Total In-Scope Criteria: [Total]
- Met Criteria: [MetCount]
- Unmet Criteria: [UnmetCount]
```

### 2. Terminal Handback Contract

When the loop terminates (either on full PASS or on a triggered failsafe), the output report must include:

1. **Terminal Status**: `SUCCESS_ALL_PASS` or the exact triggered failsafe (`FAILSAFE_ITERATION_CAP_EXCEEDED`, `FAILSAFE_NO_IMPROVEMENT`, `FAILSAFE_WALLCLOCK_TIMEOUT`, or `HARNESS_*`). Failsafe class names are parsed mechanically — emit them exactly as spelled here.
2. **Per-View Verdict Summary**: Final MET/UNMET status for each view.
3. **Unmet Criteria Roster**: Full list of remaining unmet criteria with their image citations.
4. **Round History & Trajectory**: Table showing round-by-round count of unmet criteria.
5. **Artifact Inventory**: File paths and sizes of all generated screenshots (baseline and final).
6. **Identity Attestation**: Confirmation of drafter vs judge model identities.

---

## Rigorous Quality Guarantees

### 1. Regression Guard

Prior rounds' passed criteria are re-verified on every subsequent round. A code revision that resolves View B while breaking View A is an immediate regression, registered as an increase or stagnation in unmet criteria.

### 2. Baseline Referent Anchoring

Visual changes are evaluated strictly against the Round 0 baseline referent at the user's actual viewport. A visual diff that is sub-perceptible, or evaluated against an out-of-date/post-revert tree where the referent is missing, is an automatic FAIL (`REFERENT_MISSING_OR_SUBPERCEPTIBLE`).

### 3. Identity Separation (Binding)

The drafter agent and the judging agent **MUST** be distinct model instances (`Drafter != Judge`). If exceptional environment constraints force a single agent to execute both roles, this identity collapse must be explicitly attested and highlighted in the terminal handback. Silent self-approval is forbidden.

### 4. Portability & Scope Boundary

This template defines the universal mechanics of visual test loops. Domain-specific configurations (target URLs, application ports, specific screenshot scripts, and view names) are supplied by the instantiating task parameters, preserving this template's clean portability across repositories.

---

## Amendment log

- **2026-08-20** — Two defects found on the read that prepared this template for Nic's approval, repaired here rather than filed: the iteration-cap class name was spelled `FAILSAVE_ITERATION_CAP_EXCEEDED` (SAVE, not SAFE) in both the failsafe table and the handback contract, in a contract that is parsed mechanically and whose sibling classes are all `FAILSAFE_*`; and the wall-clock and iteration caps were stated as if independent when 5 × 30m exceeds the 120m cumulative budget. Precedence is now stated explicitly. Both were surfaced to Nic in the approval brief before he approved. Record: [[visualqa_design_findings]].

## Related Documents

- [[wf_qa_b4b7f9c5]] (`wf-qa-around`) — Marsha lens and excellence QA doctrine
- [[wf_refine_6ef85da2]] (`wf-refine-loop`) — Drafter-reviewer convergence and identity separation
- [[workflow-library-moc]] — PKB Tier Workflow Registry
- [[aops-843a7e38]] — Fresh-context evaluation principle (anti-contamination)
- [[aops-58e00a87]] — Baseline referent anchoring and anti-stale-diff doctrine
- [[mem_b867906c]] — Marsha excellence standard (quality over compliance)
- [[mem-861f1591]] — Headless worker tool-denial failure signature
- [[mem-6b49534e]] — Verbatim acceptance bar requirement and anti-bar-substitution
