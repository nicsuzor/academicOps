---
name: triage
type: skill
category: instruction
description: "Triage a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to pauli for all three modes to keep main context clean."
---

# /triage — triage a corpus, classify, dispatch

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Read [`references/forensic-scope.md`](references/forensic-scope.md) before
starting any mode.** Its in-scope/out-of-scope split and its anonymisation clause
bind all three modes, not `retro` alone.

Every mode dispatches to `pauli` (`plugins/aops/agents/pauli.md`): the premise
test these reviews turn on, and the graph mutation `sweep` performs, are both
hers.

## Mode: retro

Forensic review of a single session transcript — apply the immediate fixes, file
the tracking issues.

### 1. Select the transcript and gate on its quality

- **Review only the session ID, transcript path, or session context passed in the
  prompt.** Never fall back to a random unreviewed transcript. With no target
  supplied, halt and report.
- The current session may be reviewed by a fresh subagent, whose detached context
  is what makes the review honest. What is never allowed is the same agent
  grading its own work in the same context.
- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists; if not,
  stop and ask the user.
- Resolve the session ID against `$AOPS_SESSIONS/transcripts/YYYY-MM/` and read
  the markdown. Each session also has HTML and JSON sidecars — see
  [`specs/transcript-pipeline.md`](../../../specs/transcript-pipeline.md#4-output-formats).
- **Verify the transcript is complete and usable before analysing it.** If it is
  not, name the failed condition and stop. A forensic review on a degraded
  transcript yields false findings, so never silently fall back to the raw
  `.jsonl`; proceed on raw JSONL only with explicit user confirmation.

### 2. Analyse and fix

Read the entire transcript. Apply `references/forensic-scope.md` as written: the
forensic read, the split between fixing the reviewed session and changing the
framework, and the fix-and-route invariant all come from there. In retro, the
record that routing names is the filed GitHub issue.

**Bad-premise approval.** Good, working, well-tested work done for a bad idea is
a bad-premise approval, and the miss is scored against the reviewer who passed
it, not only the author. Every review surface (arch-fit, `/verify`, rbg, pauli)
carries a forced step-0 premise test — _was this worth building at all, in this
shape?_ — so a PASS on a bad premise means that test was skipped or rationalised
past, and test-passing is never the excuse. The filed issue names the approving
surface as the locus of the miss, alongside the premise that should have been
bounced. A deterministic rig — regex, threshold, NLP, checklist — built for a
call a smart agent should just make (`judgment-non-delegable`) is one worked
instance, not the whole class.

### 3. Output

```markdown
## Transcript Review: <filename>

**Session**: <session_id> **Date**: <date> **Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Findings

[Concise description of failures/successes, grouped by structural cause.]

### Patterns (Optional)

[Upstream/structural root cause spanning multiple findings.]
```

### 4. File issues and land the changes

- Search `gh issue list` and `gh pr list` for an existing match. If one exists,
  comment the delta (new date, facts, impact) and edit structurally with
  `gh issue edit`.
- Otherwise create a bug issue titled `Bug: <brief-slug>`, capped at 3 per
  session. The body carries only forensic fields — **Incident facts**,
  **Structural shape**, **Impact**. Propose no solutions in the issue.
- Stamp review provenance in the daily note as one self-contained semantic chunk
  so the PKB indexes it: a heading `### Retro review stamp: session <SID>
  (<project>)`, tagged `#retro #reviewed #triage-retro #<project-tag>`, carrying
  the verbatim `reviewed_by` block (agent, date, verdict, issues_filed, session
  ID, transcript path). This indexed entry is the durable already-reviewed signal
  that prevents re-triaging the same transcript.
- Run the test suite (`uv run pytest`) over any fix applied, then commit and open
  a PR referencing both the fix and the filed issues.

## Mode: trend

Review many sessions for systemic effectiveness and trends.

**Corpus selection.** To extract what the user typed — prompts, `/command`
invocations, skill usage — start with the per-session JSON sidecars at
`$AOPS_SESSIONS/transcripts/YYYY-MM/*.json`: read the top-level `user_prompts`
array (`[{timestamp, text}]`), which holds out harness-injected text into the
sibling `injected_prompts` array across all clients, and narrow to human-driven
sessions with `has_user_context`. Read the field set off a sidecar itself; there
is no schema doc. Fall back to the rendered `*.full.md` beside them only for what
the sidecars do not capture (agent reasoning, tool calls).

### 1. Sample and read

Select 8 to 15 files spanning both early and recent periods, with size and
project diversity. Extract context, component behaviour, accuracy (TP/FP/FN), and
trajectory impact.

### 2. Synthesise

Analyse aggregate true/false rates, temporal trends, coverage, and cost-benefit.
Save the report to `$AOPS_SESSIONS/reviews/<component>-trend-<date>.md` in this
format:

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

## Mode: sweep

Triage open issues on `nicsuzor/academicOps`, at most 20 per cycle.

### 1. Classify and dispose

Fetch the open issues, taking the focal issue first where one is named, and
classify each:

| Disposition             | Criterion                                             | Action                                                                                   | Label                   |
| ----------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------- |
| `close-as-stale`        | >90d old, no activity, or describes retired behavior. | Close issue with explanatory comment.                                                    | `triaged-stale`         |
| `consolidate-duplicate` | Describes the same underlying problem.                | Merge details into canonical issue; close duplicate with cross-link comment (`#N`).      | `triaged-duplicate`     |
| `aggregate`             | Multiple issues sharing one root cause/fix surface.   | Fold into one `fix-epic` task (leave queued); close source issues with pointer comments. | `triaged-aggregate`     |
| `evidence-bump`         | Accumulates evidence for a related open issue/epic.   | Leave open; add comment citing canonical issue (`#N`).                                   | `triaged-evidence-bump` |
| `single-task`           | Atomic task (AC clear, ≤3 files, obvious fix).        | File polecat task with `Closes #N`.                                                      | `triaged-single`        |
| `fix-epic`              | Multi-step, multi-file, or design-required work.      | Create epic task, leave at `inbox` for the user to brief.                                | `triaged-epic`          |
| `defer`                 | Real but blocked or low-criticality.                  | Apply defer label and revisit-by date.                                                   | `triaged-defer`         |

Apply low blast-radius dispositions autonomously. Gate only on an ambiguous
classification, an add-or-escalate enforcement proposal (step 2 below), or a hard
halt (locked merge gate, irreversible operation).

### 2. Enforcement-escalation review

Before assigning a disposition to any proposal that **adds or escalates** a rule:

1. Generalise the failure into a root-cause category.
2. Map it to existing mechanisms in the enforcement map and the axioms.
3. Classify it as a _propagation failure_ (fix via L1 propagation) or an
   _escalation candidate_ (requires cost-benefit analysis and ≥3 recurrence
   links).
4. Default to the cheapest tier, L1 propagation. Flag any enforcement change not
   reflected in `specs/enforcement/enforcement.md` as a pipeline gap.

### 3. Report the cycle

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

### 4. Execution rules

- **Task creation**: omit `severity` — it belongs on target milestones, not
  ordinary tasks. Created tasks default to `inbox`; `ready` is computed
  downstream, never hand-written.
- **Priority**: leave `priority` at its default. Never infer, estimate, or
  propagate a band — only the principal sets intent. To make a swept task more
  important, raise the `stated_weight` of its `contributes_to` edge.
- **Verification**: confirm closed issues actually reached `state: closed`.
- **Handoff**: `Skill(skill="verify", args="Verify cycle <N> of the issue sweep.")`
- **Halt**: exit after exactly one cycle.
