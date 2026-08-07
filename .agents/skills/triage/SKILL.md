---
name: triage
type: skill
category: instruction
description: "Triage a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to pauli for all three modes to keep main context clean."
---

# /triage — Unified Triage Skill

Triage a corpus, classify findings, and dispatch outputs according to the selected mode.

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Privacy Rule**: the anonymisation clause in [`.agents/skills/debug/forensic-scope.md`](../debug/forensic-scope.md) binds every mode here, not only `retro`.

---

## Dispatch Model

Every mode dispatches to `pauli`: the premise test these reviews turn on, and the graph mutation `sweep` performs, are both hers (`plugins/pkb/agents/pauli.md`).

---

## Mode: retro

Perform a critical, forensic review of a single session transcript, apply immediate fixes where appropriate, and file the tracking GitHub issues.

### 1. Transcript Selection & Quality Gate

- **Explicit Target Requirement**: You must only review the specified session ID, transcript path, or current session context passed in the prompt. Do NOT fall back to selecting a random unreviewed transcript. If no session context, ID, or path is provided, halt and report an error.
- **Same-Session Review Allowed**: the current session may be reviewed by a fresh subagent, whose detached context is what makes the review honest. What is never allowed is the same agent grading its own work in the same context.
- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists. If not, stop and ask the user.
- Resolve the target session ID against `$AOPS_SESSIONS/transcripts/YYYY-MM/`. Each session has a markdown, an HTML, and a JSON sidecar artifact — see [`specs/transcript-pipeline.md`](../../../specs/transcript-pipeline.md#3-output-formats). Read the markdown.
- **Quality Gate**: Verify the transcript is complete and usable before analyzing it. If it isn't, name the failed condition and stop. Never silently fall back to the raw `.jsonl` as a workaround — a forensic review on a degraded transcript yields false findings; proceed on raw JSONL only with explicit user confirmation.

### 2. Forensic Analysis & Immediate Fixes (Fix AND File)

- Read the entire transcript.
- The forensic read, the in-scope/out-of-scope split between fixing the reviewed session and changing the framework, and the "fix and route" invariant are stated in [`.agents/skills/debug/forensic-scope.md`](../debug/forensic-scope.md). Apply it as written. In retro, "route the lesson" means the destination chosen in §4, and the record it names is the filed GitHub issue.

### 2a. Classified recurrence — bad-premise approval (attribute the miss to the reviewer)

Good, working, well-tested work done for a bad idea is a **bad-premise approval**, and the miss is scored against the reviewer who passed it, not only the author. Every review surface (arch-fit / `/verify` / rbg / pauli) carries a forced step-0 premise test — _was this worth building at all, in this shape?_ — so a PASS on a bad premise means that test was skipped or rationalised past, and test-passing is never the excuse.

The filed issue names the approving surface as the locus of the miss, alongside the premise that should have been bounced. A deterministic rig — regex/threshold/NLP/checklist — built for a call a smart agent should just make (`judgment-non-delegable`) is one worked instance, not the whole class.

### 2b. Framework/behavioral changes are never a retro fix

Retro's job stops at naming the gap precisely in the filed issue. Deciding on a framework change — including which mechanism carries it and the spec update `.agents/rules/RULES.md` requires — is a separate, deliberate pass outside retro.

### 3. Output Requirements

Produce a review in this exact format. Keep text concise:

```markdown
## Transcript Review: <filename>

**Session**: <session_id> **Date**: <date> **Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Findings

[Concise description of failures/successes, grouped by structural cause.]

### Patterns (Optional)

[Upstream/structural root cause spanning multiple findings.]
```

### 4. File Issues & Apply Changes

- Search existing issues/PRs using `gh issue list` and `gh pr list` to avoid duplication.
- If a match exists, comment with a concise delta comment (new date, facts, and impact). Edit structurally using `gh issue edit`.
- If no match, create a bug issue (cap at 3 per session). Title must be `Bug: <brief-slug>`.
- Issue body must contain only forensic fields: **Incident facts**, **Structural shape**, and **Impact**. Do not propose solutions in the issue report.
- Record review provenance in the daily note as a single, self-contained semantic chunk (e.g., an H3 heading or list item) to allow the PKB to index it. Write the full verbatim text including the reviewed_by block (fields: agent, date, verdict, issues_filed, session ID, transcript path) under a heading like ### Retro review stamp: session <SID> (<project>) with tags #retro #reviewed #triage-retro #<project-tag>. This indexed entry serves as the durable already reviewed signal that prevents re-triaging the same transcript.
- **Execution & Validation**:
  - For any immediate fixes applied to the codebase, run the test suite (e.g., `uv run pytest`) to verify no regressions were introduced.
  - Commit the changes and open a PR with a description referencing both the fix and the filed GitHub issue(s).

---

## Mode: trend

Review multiple sessions to identify systemic effectiveness and trends.

> **Corpus selection — prompt mining vs trend reading.**
> If the goal is to extract _what the user typed_ (prompts, `/command` invocations, skill usage patterns), start with the **structured summaries corpus** at `$AOPS_SESSIONS/summaries/YYYY-MM/*.json`. Read the top-level `user_prompts` array (`[{timestamp, text}]`) or filter `timeline_events[type="user_prompt"]` to `system_injected=false` — across ALL clients, no client-name filter needed. This is faster and more reliable than grepping raw transcripts. Read the field set off a sidecar itself; there is no schema doc. Raw transcripts (`$AOPS_SESSIONS/transcripts/`) are the fallback for content the sidecars don't capture (agent reasoning, tool calls).

### 1. Sampling & Reading

- Select 8 to 15 files spanning both early and recent periods, including size and project diversity.
- Extract: Context, component behavior, accuracy (TP/FP/FN), and trajectory impact.

### 2. Synthesis & Output

Analyze aggregate true/false rates, temporal trends, coverage, and cost-benefit. Produce a report in this format:

```markdown
# Trend Review: <Component Name>

**Question**: <review question> **Date**: <today>
**Corpus**: <N> files, <date range> **Sample**: <N> files (criteria: ...)

## Executive Summary

[3-5 sentences summarizing if the system is working and the main trend/issues.]

## Objectives Verdict

| Objective | Verdict                                      | Evidence |
| --------- | -------------------------------------------- | -------- |
| [obj 1]   | ANSWERED / PARTIALLY ANSWERED / UNANSWERABLE | [why]    |

## Individual Assessments

### <filename> (<date>)

- **Context**: ... **Component behavior**: ... **Accuracy**: [TP/FP/FN] **Impact**: ...

## Aggregate Analysis

[Signal Quality / Temporal Trends / Coverage Map / Cost-Benefit]

## Recommendations

[Actionable, prioritized recommendations with evidence citations.]

## Confidence and Limitations
```

Save the report to `$AOPS_SESSIONS/reviews/<component>-trend-<date>.md`.

---

## Mode: sweep

Triage and process open issues on `nicsuzor/academicOps` (batch limit: ≤20 issues).

### 1. Issue Triage & Dispositions

Fetch open issues, focusing on the focal issue first if a directed focus is provided. Classify using this rubric:

| Disposition             | Criterion                                             | Action                                                                                   | Label                   |
| ----------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------- |
| `close-as-stale`        | >90d old, no activity, or describes retired behavior. | Close issue with explanatory comment.                                                    | `triaged-stale`         |
| `consolidate-duplicate` | Describes the same underlying problem.                | Merge details into canonical issue; close duplicate with cross-link comment (`#N`).      | `triaged-duplicate`     |
| `aggregate`             | Multiple issues sharing one root cause/fix surface.   | Fold into one `fix-epic` task (leave queued); close source issues with pointer comments. | `triaged-aggregate`     |
| `evidence-bump`         | Accumulates evidence for a related open issue/epic.   | Leave open; add comment citing canonical issue (`#N`).                                   | `triaged-evidence-bump` |
| `single-task`           | Atomic task (AC clear, ≤3 files, obvious fix).        | File polecat task with `Closes #N`.                                                      | `triaged-single`        |
| `fix-epic`              | Multi-step, multi-file, or design-required work.      | Create epic task, leave at `inbox` for the user to brief.                                | `triaged-epic`          |
| `defer`                 | Real but blocked or low-criticality.                  | Apply defer label and revisit-by date.                                                   | `triaged-defer`         |

- **Execution**: Apply low blast-radius dispositions autonomously. Gate ONLY on:
  - Ambiguous classification (Needs human triage).
  - Add-or-escalate enforcement proposals (requires step 2b review).
  - Hard halts (locked merge gates, irreversible operations).

### 2b. Enforcement-Escalation Review (Legislative Role)

For proposals that **add or escalate** a rule, perform this review before assigning the disposition:

1. Generalize the failure into a Root Cause Category.
2. Map to existing mechanisms in the enforcement map and axioms.
3. Classify: _Propagation failure_ (fix via L1 propagation) vs. _Escalation candidate_ (requires CBA: ≥3 recurrence links).
4. Default to the cheapest tier (L1 propagation). Flag enforcement changes not reflected in `specs/enforcement/enforcement.md` as a pipeline gap.

### 2c. Output Cycle Report

Log results in the following format:

```markdown
## Cycle <N> — applied (open before: <K>; batch: <M>)

### Applied autonomously (done)

- Consolidate-duplicate: #R → unique detail merged into #S, #R verified state:closed
- Aggregate: #A, #B, #C → folded into fix-epic <id> (queued)
- Evidence bump: #T → bumped #U
- Close (stale): #P
- Defer: #Q (revisit-by YYYY-MM-DD)
- Single-task: #X → "<title>"
- Fix-epic (queued): <title> ← #D, #E

### Needs human triage / decision (waiting)

- #Z (rubric ambiguous: <reason>)
- <add-or-escalate proposal>: cost-ladder reasoning + ≥3 recurrence links
```

### 3. Execution Rules

- **Task creation**: Omit `severity` on tasks created during the sweep — severity belongs on target milestones, not ordinary tasks. Created tasks default to `inbox`; `ready` is computed downstream, never hand-written.
- **Priority**: Leave `priority` at its default on swept tasks. Never infer, estimate, or propagate a band — only the principal sets intent. To make a swept task more important, raise the `stated_weight` of its `contributes_to` edge, never the priority.
- **Verification**: Confirm closed issues actually reached `state: closed`.
- **Handoff**: After the cycle, `Skill(skill="verify", args="Verify cycle <N> of the issue sweep.")`
- **Halt**: Exit after completing exactly one cycle.
