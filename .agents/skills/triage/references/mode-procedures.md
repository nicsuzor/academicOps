# Triage Mode Procedures

Detailed selection, analysis, classification, output templates, and landing procedures for `retro`, `trend`, and `sweep`. Apply [references/forensic-scope.md](forensic-scope.md) across all three modes.

## Mode: retro

Forensic review of a single session transcript -- apply immediate in-scope fixes and file tracking issues.

### 1. Select the Transcript and Verify Its Quality

- **Review only the session ID, conversation ID, transcript path, or session context passed in the prompt.** Never fall back to a random unreviewed transcript; halt and report if no target is supplied.
- A fresh detached subagent may review the current session; the same agent never grades its own work in the same context.
- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists; if not, stop and ask the user.
- Resolve the session/conversation ID against `$AOPS_SESSIONS/transcripts/YYYY-MM/` and read the markdown (sidecar formats: [`specs/transcript-pipeline.md`](../../../../specs/transcript-pipeline.md#4-output-formats)).
- **Verify transcript completeness before analysis.** If degraded or incomplete, name the failed condition and stop; proceed on raw `.jsonl` only with explicit user confirmation.

### 2. Analyse and Fix

Read the entire transcript and apply [references/forensic-scope.md](forensic-scope.md) (session mistake fixes in-scope; framework/behavioural changes routed, never applied inline). In `retro`, the routing record is the filed GitHub issue.

**Bad-premise approval.** Good, well-tested work for a bad idea is a bad-premise approval, scored against the reviewer that passed it as well as the author. Every review surface carries a forced step-0 premise test -- _was this worth building at all, in this shape?_ -- so passing tests never excuse skipping it. Name the approving surface alongside the unrejected premise (for example, a deterministic rig built for a call an agent should make under `judgment-non-delegable`).

### 3. Output Format

```markdown
## Transcript Review: <filename>

**Session**: <session_id> **Date**: <date> **Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Findings

[Concise description of failures/successes, grouped by structural cause.]

### Patterns (Optional)

[Upstream/structural root cause spanning multiple findings.]
```

### 4. File Issues and Land Changes

- Search `gh issue list` and `gh pr list` for an existing match; if found, comment the delta (date, facts, impact) and update structurally with `gh issue edit`.
- Otherwise file `Bug: <brief-slug>`, capped at 3 per session, carrying only forensic fields (**Incident facts**, **Structural shape**, **Impact**) with no proposed solutions.
- Stamp review provenance in the daily note as one semantic chunk for PKB indexing: heading `### Retro review stamp: session <SID> (<project>)`, tags `#retro #reviewed #triage-retro #<project-tag>`, and verbatim `reviewed_by` fields (agent, date, verdict, issues_filed, session/conversation ID, transcript path).
- Run `uv run pytest` over any in-scope fix applied, then commit and open a PR referencing both the fix and the filed issues.

## Mode: trend

Review many sessions for systemic effectiveness and trends.

**Corpus selection.** Extract user inputs (`/command` invocations, skill usage, prompts) from per-session JSON sidecars at `$AOPS_SESSIONS/transcripts/YYYY-MM/*.json`: read `user_prompts` (`[{timestamp, text}]`, separated from `injected_prompts`) and filter to human-driven sessions via `has_user_context`. Inspect the sidecar's live keys directly; fall back to `*.full.md` only for agent reasoning and tool calls.

### 1. Sample and Read

Select 8 to 15 files spanning early and recent periods with size and project diversity. Extract context, component behaviour, accuracy (TP/FP/FN), and trajectory impact.

### 2. Synthesise

Analyse true/false rates, temporal trends, coverage, and cost-benefit, and save to `$AOPS_SESSIONS/reviews/<component>-trend-<date>.md`:

```markdown
# Trend Review: <Component Name>

**Question**: <review question> **Date**: <today>
**Corpus**: <N> files, <date range> **Sample**: <N> files (criteria: ...)

## Executive Summary

[3-5 sentences summarizing system effectiveness and main trends/issues.]

## Objectives Verdict

| Objective | Verdict | Evidence |
| - | - | - |
| [obj 1] | ANSWERED / PARTIALLY ANSWERED / UNANSWERABLE | [why] |

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

Triage open issues on the `academicOps` repository, at most 20 per cycle.

### 1. Classify and Dispose

Fetch open issues, taking the focal issue first where one is named, and classify each:

| Disposition | Criterion | Action | Label |
| - | - | - | - |
| `close-as-stale` | >90d old, no activity, or describes retired behaviour. | Close issue with explanatory comment. | `triaged-stale` |
| `consolidate-duplicate` | Describes the same underlying problem. | Merge details into canonical issue; close duplicate with cross-link comment (`#N`). | `triaged-duplicate` |
| `aggregate` | Multiple issues sharing one root cause/fix surface. | Fold into one composite `type: task` node with child tasks (leave queued); close source issues with pointer comments. | `triaged-aggregate` |
| `evidence-bump` | Accumulates evidence for a related open issue or parent task. | Leave open; add comment citing canonical issue (`#N`). | `triaged-evidence-bump` |
| `single-task` | Atomic task (AC clear, <=3 files, obvious fix). | File polecat task (`type: task`) with `Closes #N`. | `triaged-single` |
| `fix-epic` | Multi-step, multi-file, or design-required work. | Create a composite parent task (`type: task` with child tasks, never `type: epic`), leave at `inbox` for briefing. | `triaged-epic` |
| `defer` | Real but blocked or low-criticality. | Apply defer label and revisit-by date. | `triaged-defer` |

Apply low blast-radius dispositions autonomously. Escalate only on an ambiguous classification, an enforcement proposal (Step 2), or a hard block (locked merge check, irreversible operation).

### 2. Enforcement Review

Before assigning a disposition to any proposal that **adds or modifies** a rule or mechanism:

1. Generalise the failure into a root-cause category.
2. Map it to existing mechanisms in the enforcement map and the axioms.
3. Classify it as a _propagation failure_ (fix via instruction propagation) or a _mechanism candidate_ (requires proportionality analysis and >=3 recurrence links).
4. Default to instruction propagation unless context, frequency, and risk justify stronger intervention; flag any enforcement change absent from `specs/enforcement/enforcement.md` as a pipeline gap.

### 3. Cycle Report Format

```markdown
## Cycle <N> -- applied (open before: <K>; batch: <M>)

### Applied autonomously (done)

- Consolidate-duplicate: #R -> unique detail merged into #S, #R verified state:closed
- Aggregate: #A, #B, #C -> folded into composite task <id> (queued)
- Evidence bump: #T -> bumped #U
- Close (stale): #P
- Defer: #Q (revisit-by YYYY-MM-DD)
- Single-task: #X -> "<title>"
- Composite fix task (queued): <title> <- #D, #E

### Needs human triage / decision (waiting)

- #Z (rubric ambiguous: <reason>)
- <enforcement proposal>: proportionality reasoning + >=3 recurrence links
```

### 4. Execution Rules

- **Task creation**: Omit `severity` (belongs on target milestones). Created tasks default to `inbox`; `ready` is computed downstream, never hand-written.
- **Priority**: Leave `priority` at its default -- only the principal sets intent (add a row to the next densify batch to raise importance).
- **Verification**: Confirm closed issues reached `state: closed`.
- **Handoff**: `Skill(skill="verify", args="Verify cycle <N> of the issue sweep.")`
- **Halt**: Exit after exactly one cycle.
