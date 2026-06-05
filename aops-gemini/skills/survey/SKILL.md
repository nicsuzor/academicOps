---
name: survey
type: skill
category: instruction
description: "Survey a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to junior/jr to keep main context clean."
triggers:
  - "survey"
  - "retro"
  - "transcript review"
  - "session review"
  - "trend review"
  - "performance trends"
  - "issue sweep"
  - "triage issues"
modifies_files: true
needs_task: false
mode: orchestration
domain:
  - framework
  - quality-assurance
  - operations
allowed-tools: Agent, Bash, Read, Grep, Glob, Edit, Write, Skill, AskUserQuestion, mcp_pkb_list_tasks, mcp_pkb_get_task, mcp_pkb_create_task, mcp_pkb_update_task, mcp_pkb_append, mcp_pkb_task_search
owner: junior
version: 1.0.0
tags:
  - retro
  - trend
  - sweep
  - quality
  - consolidation
---

# /survey — Unified Survey Skill

Survey a corpus, classify findings, and dispatch outputs according to the selected mode.

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Privacy Rule**: Anonymize all findings. Do not expose real names, emails, student details, or raw session dumps.

---

## Dispatch Model

This skill delegates execution to keep the main context clean:

- **`retro` / `trend` mode**: Dispatch `junior` with access to PKB and system tools.
- **`sweep` mode**: Dispatch `jr` to handle interactive triage and confirmation gates.

---

## Mode: retro

Perform a critical, forensic review of a single session transcript.

### 1. Transcript Selection & Quality Gate

- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists. If not, stop and ask the user.
- Resolve target session ID to `$AOPS_SESSIONS/transcripts/YYYY-MM/*-${SID}-*-claude-full.md`. Use `-abridged.md` only as a fallback.
- **Quality Gate**: Stop and alert the user if the transcript is:
  - _Absent_: No matching markdown file — but first confirm the month-shard dir (`$AOPS_SESSIONS/transcripts/YYYY-MM/`) exists and is non-empty. A zero-hit glob in a wrong or missing directory is a lookup error, not an absent transcript.
  - _Truncated_: File stops mid-turn or is drastically smaller than the raw JSONL line count.
  - _Stripped_: Tool calls/results are missing from a `-full.md` file.
- On any gate failure, name the failed condition and stop. Never silently fall back to the raw `.jsonl` — a forensic review on a degraded transcript yields false findings; proceed on raw JSONL only with explicit user confirmation.

### 2. Forensic Analysis & Recusal

- Read the entire transcript. Look for structural causes, architectural alignment, pattern recognition, and instruction-quality failures (e.g. `/craft` defects: compliance framing, missing artifact chain, etc.).
- **Recusal Rule**: Limit findings to forensic facts (what failed, how the framework contributed, concrete impact). Do not suggest or author remediation rules (e.g., "we should add an axiom").

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

### 4. File Issues

- Search existing issues/PRs using `gh issue list` and `gh pr list` to avoid duplication.
- If a match exists, comment with a concise delta comment (new date, facts, and impact). Edit structurally using `gh issue edit`.
- If no match, create a bug issue (cap at 3 per session). Title must be `Bug: <brief-slug>`.
- Issue body must contain only forensic fields: **Incident facts**, **Structural shape**, and **Impact**. Do not propose solutions.
- Stamp the transcript frontmatter with the `reviewed_by` block.

---

## Mode: trend

Review multiple sessions to identify systemic effectiveness and trends.

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

Save the report to `~/.aops/sessions/reviews/<component>-trend-<date>.md`.

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
| `fix-epic`              | Multi-step, multi-file, or design-required work.      | Create epic task and decompose, leave queued.                                            | `triaged-epic`          |
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
4. Default to the cheapest tier (L1 propagation). Flag missing `specs/ENFORCEMENT-MAP.md` rows as a pipeline gap.

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

- **Task Creation**: Omit `severity` (or set `severity=0`) on tasks created during the sweep.
- **Verification**: Verify closed issues are successfully set to `state: closed`.
- **Log Instance**: Create a datestamped task instance under template `epic-a0523a25` and append the cycle log details.
- **Handoff**: Run verification after completing the cycle:
  `activate_skill(name="verify", args="Verify cycle <N> of /issue-sweep on epic-a0523a25.")`
- **Halt**: Exit after completing exactly one cycle.
