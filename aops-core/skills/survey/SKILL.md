---
name: survey
type: skill
category: instruction
description: "Survey a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to pauli (retro/trend) or jr (sweep) to keep main context clean."
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
allowed-tools: Agent, Bash, Read, Grep, Glob, Edit, Write, Skill, AskUserQuestion, mcp__pkb__list_tasks, mcp__pkb__get_task, mcp__pkb__create_task, mcp__pkb__update_task, mcp__pkb__append, mcp__pkb__task_search
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

- **`retro` / `trend` mode**: Dispatch `pauli` with access to PKB and system tools.
- **`sweep` mode**: Dispatch `jr` to handle interactive triage and confirmation gates.

---

## Mode: retro

Perform a critical, forensic review of a single session transcript, apply immediate fixes where appropriate, and file the tracking GitHub issues.

### 1. Transcript Selection & Quality Gate

- **Explicit Target Requirement**: You must only review the specified session ID, transcript path, or current session context passed in the prompt. Do NOT fall back to selecting a random unreviewed transcript. If no session context, ID, or path is provided, halt and report an error.
- **Same-Session Review Allowed**: Reviewing the current active session (self-review) by a fresh reviewer subagent (like `pauli` dispatched within the session) is explicitly allowed and structurally sound because the subagent executes in a clean, detached context.
- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists. If not, stop and ask the user.
- Resolve target session ID to `$AOPS_SESSIONS/transcripts/YYYY-MM/*-${SID}-*-claude-full.md`. Use `-abridged.md` only as a fallback.
- **Quality Gate**: Stop and alert the user if the transcript is:
  - _Absent_: No matching markdown file — but first confirm the month-shard dir (`$AOPS_SESSIONS/transcripts/YYYY-MM/`) exists and is non-empty. A zero-hit glob in a wrong or missing directory is a lookup error, not an absent transcript.
  - _Truncated_: File stops mid-turn or is drastically smaller than the raw JSONL line count.
  - _Stripped_: Tool calls/results are missing from a `-full.md` file.
- On any gate failure, name the failed condition and stop. Never silently fall back to the raw `.jsonl` — a forensic review on a degraded transcript yields false findings; proceed on raw JSONL only with explicit user confirmation.

### 2. Forensic Analysis & Immediate Fixes (Fix AND File)

- Read the entire transcript. Look for structural causes, architectural alignment, pattern recognition, and instruction-quality failures (e.g., `/craft` defects: compliance framing, missing artifact chain, etc.).
- **Immediate Fixes Policy**:
  - **Minor Tweaks**: You are authorized to fix minor issues immediately (e.g., typos, wrong paths, simple one-line instruction updates, formatting, or obvious logic bugs) directly in the source files, without seeking user permission.
  - **Framework-Caused Defects**: Problems caused by the framework itself (bugs in hooks, gates, skills, tools) MUST be fixed immediately. Fixing it is the job.
  - **First-Class Invocation: `/learn that last task should have been xyz`**: When Nic invokes this style with a description of what _should_ have happened, treat it as a directive to perform a **dual action**:
    1. **Fix the immediate problem now**: Edit the codebase, rules, or instruction surfaces to enforce the correct behavior immediately.
    2. **File the RCA issue in the background**: Run the standard retro analysis to file a forensic GitHub issue.
       Never pick one and drop the other; you must perform both actions.
  - **Complex Fixes**: If a fix is too complex, large, or requires unavailable permissions/runtime setups, file a follow-up task instead of attempting a partial fix that degrades system reliability.
  - **The "Fix AND File" Invariant**: An immediate fix NEVER replaces the GitHub issue. You must STILL file the issue carrying the root-cause analysis. Do both: **Fix AND File**. The systemic lesson must survive even if the local symptom is already patched.
- **Issue Report Rigor**: Limit the contents of the _GitHub issue report_ to forensic facts (what failed, how the framework contributed, concrete impact). Do not write/propose speculative solutions in the issue description or body (keep them out of the report to keep the data clean). This formatting rule for the issue body must NOT be misread as a prohibition on the agent actually modifying the codebase to fix the live problem.

### 2a. Classified recurrence — bad-premise approval (attribute the miss to the reviewer)

When the transcript shows an artifact whose **premise** a sharp principal would have bounced — _"was this a good idea?"_ answered no; good, working, well-tested work done for a bad idea (canonical instance: a deterministic rig — regex/threshold/NLP/checklist — built for a call a smart agent should just make, `judgment-non-delegable`) — that nonetheless passed review, classify it as a **bad-premise approval** and score the miss **against the reviewer who approved it**, not only the author:

- Identify the review surface that emitted PASS / MERGE / APPROVE on the bad premise (arch-fit / `/verify` / rbg / pauli). Each of those carries a forced step-0 **Premise Test** (canonical definition: [[premise-test.md]]); an approval means that forcing function was skipped or rationalised past — a reviewer failure, with test-passing as its expected surface, never an excuse.
- The filed issue names the **approving reviewer/surface as the locus of the miss** (anonymised per the Privacy Rule) alongside the premise that should have been bounced — not just the authoring agent.
- Generalised framing: this is "was this worth building at all, in this shape?", **not** an overengineering-only pattern. Overengineering (deterministic-rig-for-a-judgment-call) is one worked instance of the broader "dumb idea" class.

This makes the reviewer's miss visible and attributed — the compounding fix for floor-optimisation (#1585): a slipped-through bad premise becomes a logged, attributed miss instead of an invisible one, so the cost lands on the surface that should have caught it.

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
- Stamp the transcript frontmatter with the `reviewed_by` block.
- **Execution & Validation**:
  - For any immediate fixes applied to the codebase, run the test suite (e.g., `uv run pytest`) to verify no regressions were introduced.
  - Commit the changes and open a PR with a description referencing both the fix and the filed GitHub issue(s).

### 5. Retro Anti-Patterns

| Anti-pattern                                                                                                                                    | What to do instead                                                                                                                                                                                                                   |
| :---------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Same-context self-grading (the same agent reviewing their own work within the same conversation/turn context without a fresh reviewer boundary) | Review by a fresh subagent (like `pauli` dispatched within the same session) or a separate reviewer, ensuring a detached/clean review context. Same-session review by a fresh subagent is structurally sound and explicitly allowed. |
| Including remediation proposals in the report (`recusal`)                                                                                       | Stop at facts, structural context, and impact. Propose fixes directly in the codebase (if permitted) but keep the filed issue strictly forensic.                                                                                     |
| Citing a single session as justification for a new mechanism                                                                                    | Recurrence is the evidence base for framework change, not the salience of a single transcript.                                                                                                                                       |

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

- **Task Creation**: Omit `severity` (or set `severity=0`) on tasks created during the sweep. Assigning non-zero severity to ordinary tasks is prohibited; severity belongs exclusively on target milestones (see [[../remember/references/TAXONOMY.md#severity-target-boundary]]).
- **Priority P0 Calibration**: Do not set `priority=0` (P0) on swept tasks unless it is deliberately calibrated under canonical rules (see [[../remember/references/TAXONOMY.md#p0-calibration-bar]]) and explicitly requested/justified.
- **Verification**: Verify closed issues are successfully set to `state: closed`.
- **Log Instance**: Create a datestamped task instance under template `epic-a0523a25` and append the cycle log details.
- **Handoff**: Run verification after completing the cycle:
  `Skill(skill="verify", args="Verify cycle <N> of /issue-sweep on epic-a0523a25.")`
- **Halt**: Exit after completing exactly one cycle.
