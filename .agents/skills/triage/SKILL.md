---
name: triage
type: skill
category: instruction
description: "Triage a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to pauli for all three modes to keep main context clean."
triggers:
  - "triage"
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
allowed-tools: Agent, Bash, Read, Grep, Glob, Edit, Write, Skill, AskUserQuestion, mcp__services__pkb__list_tasks, mcp__services__pkb__get_task, mcp__services__pkb__create_task, mcp__services__pkb__update_task, mcp__services__pkb__append, mcp__services__pkb__task_search
version: 1.0.0
tags:
  - retro
  - trend
  - sweep
  - quality
  - consolidation
---

# /triage — Unified Triage Skill

Triage a corpus, classify findings, and dispatch outputs according to the selected mode.

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Privacy Rule**: Anonymize all findings. Do not expose real names, emails, student details, or raw session dumps.

---

## Dispatch Model

This skill delegates execution to keep the main context clean. Both dispatch targets below are **personality-bound to `pauli`**, for two distinct reasons — this is not merely "delegate somewhere to save context":

- **`retro` / `trend` mode — earmarking.** §2a's bad-premise attribution ("was this a good idea, in this shape?") and the architectural-fit read of structural causes are pauli's premise-test / architectural-fit judgment register (`specs/agents/pauli.md`), the same lens she applies in `/strategic-review`. A generic subagent could mechanically follow the output format without holding that disposition, which is exactly the failure mode §2a exists to catch — so the judgment, not just the context-hygiene delegation, is why this is pauli's.
- **`sweep` mode — permission-control.** Issue consolidation, single-task filing, and fix-epic decomposition are graph-mutation work requiring the PKB tool surface only pauli's frontmatter grants (Modes 2/3 in `specs/agents/pauli.md`, "sole graph-shaper" — see also `planner/SKILL.md`'s identical binding). Ambiguous classifications are flagged in the cycle report rather than blocking, matching pauli's flag-don't-resolve posture.

---

## Mode: retro

Perform a critical, forensic review of a single session transcript, apply immediate fixes where appropriate, and file the tracking GitHub issues.

### 1. Transcript Selection & Quality Gate

- **Explicit Target Requirement**: You must only review the specified session ID, transcript path, or current session context passed in the prompt. Do NOT fall back to selecting a random unreviewed transcript. If no session context, ID, or path is provided, halt and report an error.
- **Same-Session Review Allowed**: Reviewing the current active session (self-review) by a fresh reviewer subagent (like `pauli` dispatched within the session) is explicitly allowed and structurally sound because the subagent executes in a clean, detached context.
- Verify `$AOPS_SESSIONS` is set and `$AOPS_SESSIONS/transcripts` exists. If not, stop and ask the user.
- Resolve the target session ID against `$AOPS_SESSIONS/transcripts/YYYY-MM/`. Each session has a markdown, an HTML, and a JSON sidecar artifact — see [`specs/transcript-pipeline.md`](../../../specs/transcript-pipeline.md#3-output-formats). Read the markdown.
- **Quality Gate**: Verify the transcript is complete and usable before analyzing it. If it isn't, name the failed condition and stop. Never silently fall back to the raw `.jsonl` as a workaround — a forensic review on a degraded transcript yields false findings; proceed on raw JSONL only with explicit user confirmation.

### 2. Forensic Analysis & Immediate Fixes (Fix AND File)

- Read the entire transcript. Look for structural causes, architectural alignment, pattern recognition, and instruction-quality failures (e.g., `/craft` defects: compliance framing, missing artifact chain, etc.).
- **Immediate Fixes Policy — retro fixes the reviewed session, never the framework's future behavior**:
  - **In scope, fix immediately**: the concrete mistake or leftover bad state _this session_ produced — a wrong file it wrote, a task it left mis-filed, a broken reference or typo it introduced or tripped over, an actual code bug in a hook/gate/skill/tool. Fix these directly in the source files, without seeking permission.
  - **Out of scope, always**: adding, editing, or strengthening any rule, axiom, persona instruction, gate, hook, or agent-definition text so that _future_ sessions behave differently — even one line, even when you're confident it's correct and well-scoped. That is a framework change, not a fix to the reviewed session (see §2b). One incident is never sufficient warrant for it, no matter how salient; it belongs to a separate, deliberate pass informed by recurrence across multiple filed issues, not to this one. File the gap in the RCA issue and stop there.
  - **First-Class Invocation: `/learn that last task should have been xyz`**: When Nic invokes this style with a description of what _should_ have happened, treat it as a directive to perform a **dual action**:
    1. **Fix the immediate problem now**: correct the reviewed session's own mistake or leftover state, per the in-scope/out-of-scope split above — never the instructions that govern future sessions.
    2. **File the RCA issue in the background**: Run the standard retro analysis to file a forensic GitHub issue, including the "should have been xyz" framing as directive context.
       Never pick one and drop the other; you must perform both actions. Never substitute a framework change for either.
  - **Complex Fixes**: If an in-scope fix is too complex, large, or requires unavailable permissions/runtime setups, file a follow-up task instead of attempting a partial fix that degrades system reliability.
  - **The "Fix AND File" Invariant**: An immediate fix NEVER replaces the GitHub issue. You must STILL file the issue carrying the root-cause analysis. Do both: **Fix AND File**. The systemic lesson must survive even if the local symptom is already patched.
- **Issue Report Rigor**: Limit the contents of the _GitHub issue report_ to forensic facts (what failed, how the framework contributed, concrete impact). Do not write/propose speculative solutions in the issue description or body (keep them out of the report to keep the data clean). This formatting rule for the issue body must NOT be misread as a prohibition on fixing the reviewed session's own mistakes — nor, in the other direction, as license to fix the framework's future behavior; see the scope split above.

### 2a. Classified recurrence — bad-premise approval (attribute the miss to the reviewer)

When the transcript shows an artifact whose **premise** a sharp principal would have bounced — _"was this a good idea?"_ answered no; good, working, well-tested work done for a bad idea (canonical instance: a deterministic rig — regex/threshold/NLP/checklist — built for a call a smart agent should just make, `judgment-non-delegable`) — that nonetheless passed review, classify it as a **bad-premise approval** and score the miss **against the reviewer who approved it**, not only the author:

- Identify the review surface that emitted PASS / MERGE / APPROVE on the bad premise (arch-fit / `/verify` / rbg / pauli). Each of those carries a forced step-0 premise test — _was this worth building at all, in this shape?_ An approval means that forcing function was skipped or rationalised past — a reviewer failure, with test-passing as its expected surface, never an excuse.
- The filed issue names the **approving reviewer/surface as the locus of the miss** (anonymised per the Privacy Rule) alongside the premise that should have been bounced — not just the authoring agent.
- Generalised framing: this is "was this worth building at all, in this shape?", **not** an overengineering-only pattern. Overengineering (deterministic-rig-for-a-judgment-call) is one worked instance of the broader "dumb idea" class.

This makes the reviewer's miss visible and attributed: a slipped-through bad premise becomes a logged, attributed miss instead of an invisible one, so the cost lands on the surface that should have caught it rather than compounding silently across future reviews.

### 2b. Framework/behavioral changes are never a retro fix

A fix that changes what an agent is directed to do — an instruction, persona edit, axiom, rule, hook, gate, or chokepoint — is a framework change, not a fix to the reviewed session. Retro does not apply these, at any tier, no matter how minor, obviously-correct, or narrowly-scoped to the one incident it looks from inside the review. This holds even under the `/learn that last task should have been xyz` invocation: "fix the immediate problem" there still means the reviewed session's own mistake, never the instructions that govern future sessions.

Recurrence across multiple filed issues, not the salience of one transcript, is the evidence base for a framework change — and deciding on one — including which mechanism carries it and the spec update `.agents/rules/RULES.md` requires — is a separate, deliberate pass outside retro. Retro's job stops at naming the gap precisely in the filed issue.

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

### 5. Retro Anti-Patterns

| Anti-pattern                                                                                                                                                                | What to do instead                                                                                                                                                                                                                    |
| :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Same-context self-grading (the same agent reviewing their own work within the same conversation/turn context without a fresh reviewer boundary)                             | Review by a fresh subagent (like `pauli` dispatched within the same session) or a separate reviewer, ensuring a detached/clean review context. Same-session review by a fresh subagent is structurally sound and explicitly allowed.  |
| Including remediation proposals in the report                                                                                                                               | Stop at facts, structural context, and impact — a detached cross-incident pass decides on rule changes. Fix the reviewed session's own mistake directly in the codebase if in scope (§2), but keep the filed issue strictly forensic. |
| Citing a single session as justification for a new mechanism                                                                                                                | Recurrence is the evidence base for framework change, not the salience of a single transcript.                                                                                                                                        |
| Editing an agent's instructions, persona, rules, hooks, or gates directly from retro because the fix looks small, obviously correct, or narrowly scoped to the one incident | Apply §2b: that is a framework change regardless of size. File it in the RCA issue and stop — closing it is a separate, deliberate, cross-incident pass, never this one.                                                              |

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
