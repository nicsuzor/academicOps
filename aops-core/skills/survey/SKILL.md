---
name: survey
type: skill
category: instruction
description: "Survey a corpus, classify, and dispatch outputs. Three modes: retro (transcript review → issues), trend (longitudinal performance analysis), sweep (GitHub issue triage → fix-epics). Delegates execution to pauli/jr to keep main context clean."
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
owner: pauli
version: 1.0.0
tags:
  - retro
  - trend
  - sweep
  - quality
  - consolidation
---

# /survey — Unified Survey Skill

One abstract pattern, three modes: **survey a corpus, classify findings, dispatch outputs**.

| Mode    | Corpus                              | Primary output                 |
| ------- | ----------------------------------- | ------------------------------ |
| `retro` | Session transcripts (one at a time) | GitHub issues filed via `gh`   |
| `trend` | Many sessions / audit files         | Trend report + recommendations |
| `sweep` | Open GitHub issues                  | PKB tasks, fix-epics, closures |

**Privacy rule**: Anonymise all findings before filing. No real names, emails, student details, session dumps.

**See also**: [[../AXIOMS.md]] · [[../HEURISTICS.md]]

## Dispatch Model

This skill delegates execution to keep the main context window clean. The invoking agent dispatches, passes this skill as the execution spec, and exits.

```python
# retro or trend mode — pauli has transcript/knowledge access
Agent(
  subagent_type='aops-core:pauli',
  prompt='Read aops-core/skills/survey/SKILL.md. Execute in [retro|trend] mode. [user context]',
  tools=['Bash','Read','Grep','Glob','Edit','Write','Skill',
         'mcp__plugin_aops-core_pkb__search',
         'mcp__plugin_aops-core_pkb__task_search',
         'mcp__plugin_aops-core_pkb__get_document',
         'mcp__plugin_aops-core_pkb__pkb_context',
         'mcp__plugin_aops-core_pkb__append',
         'mcp__plugin_aops-core_pkb__create_task',
         'mcp__plugin_aops-core_pkb__update_task'],
)

# sweep mode — jr handles interactive confirmation gates
Agent(
  subagent_type='aops-core:jr',
  prompt='Read aops-core/skills/survey/SKILL.md. Execute in sweep mode. [user context]',
  tools=['Bash','Read','Grep','Glob','Skill','AskUserQuestion',
         'mcp__plugin_aops-core_pkb__get_task',
         'mcp__plugin_aops-core_pkb__create_task',
         'mcp__plugin_aops-core_pkb__update_task',
         'mcp__plugin_aops-core_pkb__append',
         'mcp__plugin_aops-core_pkb__task_search'],
)
```

---

## Mode: retro

**Purpose**: Read a recent transcript through a framework-development lens. Provide a brutal, concise critical review identifying problems. File every finding as a GitHub issue. We are aiming for EXCELLENCE, not "running code".

### 1. Select transcript

```bash
# List recent transcripts, newest first
ls -lt ~/.aops/sessions/transcripts/*.md | head -20

# Show unreviewed transcripts (missing reviewed_by in frontmatter)
for f in $(ls -t ~/.aops/sessions/transcripts/*.md | head -20); do
  grep -q "^reviewed_by:" "$f" || echo "$f"
done | head -10
```

If the user specified a path or session ID, use that. If no unreviewed transcripts exist, report and stop.

### 2. Read the full transcript

Read every line. Do not skim. For large files, read in chunks:

```
Read(file_path="<path>", offset=1, limit=500)
Read(file_path="<path>", offset=500, limit=500)
# continue until EOF
```

### 3. Critical review — structural over symptomatic

Evaluate the transcript critically. We are aiming for EXCELLENCE, not "running code".

Rather than prescribing a mandatory list of lenses or enforcing independent findings, you are trusted to find what matters. Read the transcript. Find what's worth fixing. Write it up however makes most sense. Flag your own biases.

- **Look for structural causes**: If you find yourself listing the same proximate cause across multiple findings, the deeper cause is upstream. Say so explicitly. Instead of listing four separate errors, articulate the structural mis-design that caused them.
- **Is the shape right?**: Instead of just asking "what went wrong against the framework as-is", ask "is the framework's shape correct?"
- **Pattern recognition**: Before filing issues, look for patterns across your findings. Are these discrete bugs, or symptoms of a single misaligned rule?

### 3b. Forensic scope (A17 Recusal)

**The retro is a forensic instrument. It does not legislate.** Per AXIOMS.md § A17, the agent that just read the transcript is normatively recused from proposing framework change motivated by that transcript. Cross-incident judgment about adding/escalating/propagating rules happens in the detached `sweep` mode (a separate context, no prior exposure to this incident).

However, **what counts as forensic includes structural articulation.** You may articulate structural shape factually (e.g., "design X is impossible because Y", "the rule forces the agent into an impossible loop"). You may flag: "this looks structural; sweep should ask whether the rule shape is right, not just whether the rule fired".

For each finding, the retro report must include — and must stop at:

1. **The facts.** What happened, quoted from the transcript.
2. **The most general category.** Pick one from the Root Cause Categories vocabulary (Discovery Gap, Detection Failure, Instruction Weighting, Index Lag, Cross-workflow Gap, Enforcement Gap, Dropped Thread, Design Inversion, Wrong Layer of Abstraction, Rule Should Not Exist) OR use a free-form framing if these do not fit.
3. **Structural shape / Rule context.** Describe factually how the framework's shape contributed to this. Name any rule that fired or should have fired. **Do not propose what should be added, escalated, or propagated. That is the sweep agent's job, not yours.**
4. **Impact statement.** What did this failure cost — agent turns, user time, downstream cleanup, trust? One paragraph. Concrete.

You may flag the finding as severe; you may not author the legislation that severity might motivate. If you find yourself writing "we should add…", "the framework needs…", "an axiom against… would prevent this," strike it. The detached reviewer reading this report later, with the enforcement map and the incident register open, is the agent allowed to write that sentence.

### 4. Produce the review

```markdown
## Transcript Review: <filename>

**Session**: <session_id> **Date**: <date> **Project**: <project>
**Verdict**: [EXCELLENT | GOOD | ADEQUATE | POOR | FAILING]

### Findings

[Free-form description of what went wrong, what went well, and what could be improved. You may use lists, paragraphs, or whatever structure best articulates the issues. Group symptoms under structural causes if applicable.]

### Patterns (Optional)

[If you notice a pattern across findings, articulate the single upstream/structural cause here.]
```

### 5. File issues

For every **Finding** that requires action, file or update a GitHub issue. Group findings that share a structural cause into a single issue.

**Search for existing issues first** — add volume to existing ones rather than duplicating:

```bash
gh issue list --repo nicsuzor/academicOps --search "<failure keywords>"
```

If an existing issue matches, comment to bump its volume:

```bash
gh issue comment <N> --repo nicsuzor/academicOps --body "<anonymised context>"
```

If no existing issue, perform root cause analysis and file:

```bash
# Write root-cause report to /tmp/issue-<slug>.md, then:
gh issue create --repo nicsuzor/academicOps \
  --title "Bug: <brief-slug>" \
  --body-file /tmp/issue-<slug>.md \
  --label "bug" --label "criticality:<level>"
```

**Issue body must include — and must stop at — these forensic fields. Factual structural articulation is allowed, but no remediation proposals (A17 Recusal):**

```yaml
## Incident report (forensic)
**Failure**: [1-sentence description]
**Causal chain**: [trigger → expected → actual → root cause]
**Root cause category**: [Discovery Gap | Detection Failure | Instruction Weighting | Index Lag | Cross-workflow Gap | Enforcement Gap | Dropped Thread | Design Inversion | Wrong Layer of Abstraction | Rule Should Not Exist | Other]
**Framework layer**: Component: [name] / File: [path]
**Expected vs Actual**: Expected: [...] / Actual: [...]

## Structural shape / Rule context
[Describe factually how the framework's shape contributed to this. Name any rule that fired or should have fired. Do NOT propose what should change — only document what existed at the time of the incident and the structural realities of why it failed.]

## Impact statement
[Concrete cost: agent turns burned, user time consumed, downstream actions that had to be reverted (PRs closed, commits reverted), trust impact. One paragraph.]
```

Issues that include a "suggested axiom," "proposed gate," or any remediation are out-of-scope under A17 and will be edited down to the forensic core by the sweep agent. Volume bumps on existing issues (`gh issue comment`) follow the same discipline — facts and impact only.

**Why this discipline:** the sweep agent (or a strategic review) reads many incident reports against the enforcement map and the axiom set, and decides what to add, propagate, escalate, or leave alone. That cross-incident judgment is undermined when each incident report ships pre-packaged with the legislation its author thought it implied. The detached reviewer needs facts; the framework needs coherence; the recused incident agent provides one and protects the other by withholding the second.

In batch mode: cap at **3 issues per session**.

### 6. Stamp the transcript as reviewed

```yaml
reviewed_by:
  - agent: "<model-name>"
    date: "<ISO 8601 datetime>"
    machine: "<hostname via bash>"
    verdict: "<EXCELLENT|GOOD|ADEQUATE|POOR|FAILING>"
    issues_filed: <count>
```

Append (do not replace) if `reviewed_by` already exists.

### 7. Framework reflection

```
## Framework Reflection
**Prompts**: /survey retro [transcript path]
**Outcome**: [success/partial/failure]
**Accomplishments**: Reviewed <transcript>, filed <N> issues, stamped as reviewed.
**Issues filed**: [GitHub Issue URLs]
```

### Retro anti-patterns

| Anti-pattern                                                                               | What to do instead                                                                              |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Skimming                                                                                   | Read every line                                                                                 |
| "Overall good with minor issues"                                                           | Quote specifically                                                                              |
| Filing four separate issues for symptoms of the same structural flaw                       | Identify the structural flaw and file one issue mapping the symptoms back to it                 |
| Inventing praise                                                                           | Only genuine strengths                                                                          |
| Reviewing your own session                                                                 | Review a DIFFERENT session                                                                      |
| Filing > 3 issues per session                                                              | Triage first; group structural causes; cap at 3 issues                                          |
| New issue for known pattern                                                                | Comment on existing issue                                                                       |
| Including "suggested axiom", "add a gate", or any remediation proposal in the report (A17) | Stop at facts + structural-context + impact. The sweep agent legislates from a detached context |
| "We should change Y because I just hit X"                                                  | The agent that hit X is recused (A17). Surface the incident; leave the change proposal to sweep |
| Citing a single session as justification for a new mechanism                               | Recurrence is the evidence base for framework change, not the salience of one transcript        |

---

## Mode: trend

**Purpose**: Review many sessions to assess whether a SYSTEM (gate, agent, skill, workflow) is achieving its goals across the population. Produces an evidence-based trend report with recommendations.

**Distinction from retro**: retro reviews individual sessions for agent behavior. trend reviews MANY sessions to assess systemic effectiveness.

### 1. Define the review question

If vague, clarify: what component, what success criteria, what time window, what specific concern?

### 2. Identify data sources

| Source               | Contents                            | Location                        |
| -------------------- | ----------------------------------- | ------------------------------- |
| Markdown transcripts | Full conversations (primary source) | `~/.aops/sessions/transcripts/` |
| Session summaries    | High-level overviews                | `~/.aops/sessions/summaries/`   |
| PKB tasks            | Task lifecycle data                 | Via `mcp__pkb__task_search`     |

Read relevant framework workflows first. For hook/gate reviews, check `09-session-hook-forensics.md`.

### 3. Sample strategically

- **Min sample**: 8 files **Max sample**: 15 files
- At least 2 from earliest period, 2 from most recent
- Size diversity (1 large, 1 small), session hash diversity
- Platform diversity if applicable (platform-specific bugs contaminate general conclusions)
- Random fill after satisfying structural criteria

Record your sample with filenames and selection rationale.

### 4. Deep-read each sample

Read every line. Extract:

- **Context**: what was the agent doing, what triggered this?
- **Component behavior**: did it behave correctly and proportionately?
- **Accuracy**: TP / FP / FN classification with specifics
- **Impact**: did the component's action change the session's trajectory?

### 5. Synthesize

Before aggregating, define what observable success looks like. If it's not observable in the data, state that upfront.

- True positive rate, false positive rate, estimated false negative rate
- Temporal trends: early vs late comparison
- Coverage map: what categories reliably detected vs missed?
- Cost-benefit: overhead vs quality improvement; is the component self-undermining?
- Platform isolation: do findings hold per platform independently?

### 6. Produce the report

```markdown
# Trend Review: <Component Name>

**Question**: <review question> **Date**: <today>
**Corpus**: <N> files, <date range> **Sample**: <N> files (criteria: ...)

## Executive Summary

[3-5 sentences. Is it working? Trend? Biggest issue? If data can't answer, say so — that IS the finding.]

## Objectives Verdict

| Objective | Verdict                                      | Evidence |
| --------- | -------------------------------------------- | -------- |
| [obj 1]   | ANSWERED / PARTIALLY ANSWERED / UNANSWERABLE | [why]    |

## Individual Assessments

### <filename> (<date>)

- **Context**: ... **Component behavior**: ... **Accuracy**: [TP/FP/FN] **Impact**: ...

## Aggregate Analysis

### Signal Quality / Temporal Trends / Coverage Map / Cost-Benefit

## Recommendations

[Specific, actionable, prioritised. Each cites evidence.]

## Confidence and Limitations
```

### 7. Save the report

```bash
mkdir -p ~/.aops/sessions/reviews
# Save to: ~/.aops/sessions/reviews/<component>-trend-<date>.md
```

### Trend anti-patterns

| Anti-pattern                             | What to do instead                         |
| ---------------------------------------- | ------------------------------------------ |
| Reviewing all files                      | Sample strategically, read deeply          |
| Claims without citations                 | Every claim cites a specific file          |
| No temporal comparison                   | Always compare early vs late               |
| Treating absence as evidence             | Distinguish measurement gaps from findings |
| Platform-specific bugs as general claims | Isolate platform variables                 |
| Burying the primary finding              | Lead with structural limitations           |
| Substituting proxy findings              | Deliver explicit verdicts per objective    |

---

## Mode: sweep

**Purpose**: Run ONE cycle of the open-issue sweep on `nicsuzor/academicOps`. Classify ≤ 20 open issues, present the proposed dispatch plan, wait for sign-off, execute confirmed actions, log the cycle. **HALT after one cycle.** Fix-epics are left `queued` for `/supervisor` in a later session.

**Detached judgment role (A17)**: sweep is the framework's _legislative_ phase. The agents that diagnosed each incident are recused; the sweep agent reads their forensic reports together with the enforcement map and the axiom set, and is the one allowed to propose adding, propagating, escalating, or retiring rules. Recency exposure is what makes this work — sweep enters with no prior context on any individual incident, so the cross-incident pattern (not the salience of any one report) drives the call.

**Hard halts**: No silent dispatch. No improvised dispositions. No cursor in task body (labels ARE the cursor). No framework-change recommendation without ≥3 cited recurrences (the CBA bar in ENFORCEMENT-MAP.md).

### Disposition rubric

| Disposition      | Criterion                                                                                                                | Action                                                           | Label             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- | ----------------- |
| `close-as-stale` | > 90d + no recent comments + root cause fixed, OR describes behaviour framework no longer has (verifiable by cheap grep) | `gh issue close` with comment citing fix                         | `triaged-stale`   |
| `comment-only`   | Volume bump on duplicate or related open issue                                                                           | Comment on canonical, close duplicate                            | `triaged-comment` |
| `single-task`    | Atomic: AC clear, ≤ 3 files, one obvious implementation, no cross-component coordination                                 | File polecat task with `Closes #N`                               | `triaged-single`  |
| `fix-epic`       | Multi-step, multi-file, or design-required                                                                               | Propose to user; on `y`: create epic + decompose, leave `queued` | `triaged-epic`    |
| `defer`          | Real but blocked or low-criticality                                                                                      | Apply `triaged-defer` + `revisit-by-YYYY-MM-DD` comment          | `triaged-defer`   |

Every disposition must be decidable in < 30 seconds by a fresh agent. If longer: "Needs human triage."

### Cursor strategy

```bash
gh issue list --repo nicsuzor/academicOps --state open --limit 100 \
  --search 'sort:created-asc -label:triaged-stale -label:triaged-comment -label:triaged-single -label:triaged-epic -label:triaged-defer' \
  --json number,title,labels,createdAt,updatedAt,comments,body \
  > /tmp/issue-sweep-batch.json
# Client-side sort: criticality-desc, age-asc. Take top 20.
```

### 1. Pre-flight

```bash
gh issue list --repo nicsuzor/academicOps --state open --limit 1 --json totalCount
gh label list --repo nicsuzor/academicOps --limit 200 | grep -E '^(triaged-|criticality:)'
```

Create missing labels, then read the loop epic:

```
mcp__pkb__get_task(id="epic-a0523a25")  # halt if not in_progress
```

### 2. Pull batch (≤ 20 issues) and classify

For each issue: read body + ≤ 3 recent comments. Apply rubric. Group `fix-epic` candidates by root cause (cap 5 issues per proposed epic). Note one-line rationale per issue.

### 2b. Cost-ladder review for framework-change candidates (A17 — sweep's legislative role)

For every issue whose remediation would touch an axiom, gate, hook, skill instruction, or any row of `.agents/ENFORCEMENT-MAP.md`, run this sequence before assigning a disposition. This is the work that retro is forbidden to do; sweep is the only mode allowed to author it.

1. **Read the forensic reports.** The issue body should be a clean incident report (per A17). If it carries a "suggested axiom" or "proposed gate," strip that from your reasoning — the proposal was authored under prejudicial recency and is evidence of urgency, not of the right answer. Edit the issue to remove the stripped section and leave a comment explaining the A17 split.
2. **Generalise the failure.** Name the most general Root Cause Category from the documented vocabulary (Discovery Gap, Detection Failure, Instruction Weighting, Index Lag, Cross-workflow Gap, Enforcement Gap, Dropped Thread). One per issue.
3. **Map to existing mechanisms.** Read `.agents/ENFORCEMENT-MAP.md` end-to-end (it is short by design). Grep AXIOMS.md and HEURISTICS.md for prior framing of the rule. List every existing mechanism that should plausibly have caught this failure, with its tier (L0–L7).
4. **Classify the failure shape**:
   - **Propagation failure** — rule exists at the right tier but didn't reach this surface. Fix is L1 propagation: edit the specific skill / agent / CORE.md text that needs to carry the rule. Same tier, more callsites.
   - **Escalation candidate** — rule exists but at a tier too cheap to beat the trained reflex. Apply the CBA from ENFORCEMENT-MAP.md (≥3 recurrence links, named cheaper levels already tried with evidence, ongoing cost estimate, reversibility criterion). If you can't satisfy the CBA, the disposition is `defer` with a `needs-more-recurrences` comment, not an escalation.
   - **Rule absent** — name the rule before naming the mechanism. Phrase it as a sentence the user could quote. Then ask which tier it belongs at, defaulting to L0/L1 unless the CBA forces a higher placement.
5. **Default cheap, escalate reluctantly.** ENFORCEMENT-MAP.md:27 names the dominant failure mode: jumping to L3+ when the actual fix is L1 propagation. Most A7 recurrences are L1 propagation failures; assume the same here unless evidence contradicts.
6. **Cite the row.** The disposition proposal must name either the row of ENFORCEMENT-MAP.md the fix propagates from, or the new row it would add. "Add a gate" is not a disposition; "L1 propagation into `aops-core/agents/marsha.md` lines XX–YY, citing existing axiom A8" is.
7. **No-change is a valid outcome.** If the rule exists at the right tier and the failure was a single agent slip, the disposition is `close-as-stale` (or `comment-only` to track volume) — not a framework change. Recurrence count is the evidence base; one slip is not.

The output of this step feeds the disposition decision in the rubric below (most often `fix-epic` for L1 propagation work, `defer` for "needs more recurrences," or `close-as-stale` for "no change warranted"). Surface every framework-change proposal to the user gate in step 3 with the cost-ladder reasoning visible.

### 3. Present cycle plan and gate

```
## Cycle <N> — proposed dispatches  (open before: <K>; batch: <M>)

### Fix-epic 1: <title>
- Issues: #A, #B  - Why grouped: ...  - Proposed scope: ...  - Estimated effort: S/M/L
- Confirm? [y / edit / defer / split]

### Single-tasks
- #X → "<title>" (XS)
Confirm batch? [y / edit / defer all]

### Close / comment-only
- Close (stale): #P  - Comment + close duplicate: #R → bumps #S
Confirm? [y / edit]

### Needs human triage
- #Z (rubric ambiguous: <reason>)
```

Use `AskUserQuestion` for each gate. Halt cleanly on decline — re-emit and gate again.

### 4. Execute (low blast-radius first)

Order: comment-only → close-stale → defer → single-task → fix-epic.

- **single-task**: `mcp__pkb__create_task` with issue body, AC, and `Closes #N` instruction.
- **fix-epic**: create epic + subtasks + `verify-parent` task. Leave `queued`. Do NOT invoke `/supervisor`.
- Stamp `triaged-*` label after each confirmed action.

### 5. Append cycle log to loop epic

```
mcp__pkb__get_task(id="epic-a0523a25")  # read body for schema
mcp__pkb__append(id="epic-a0523a25", content="<cycle entry per schema>")
```

Log must include: cursor=label-based; batch size; issues processed; per-disposition lists; open count after; triaged-* totals; stopping condition met (y/n with evidence).

### 6. Hand off to /qa

```
Skill(skill="qa", args="Verify cycle <N> of /issue-sweep on epic-a0523a25. Sample 20% (min 3). Reviewers: Pauli (cohesion) + RBG (axiom compliance). Add Marsha if single-tasks dispatched.")
```

### 7. HALT

Do not start the next cycle. Re-invoke `/survey sweep` (or `/issue-sweep`) for cycle N+1.

### Stopping condition

Loop stops only when ALL open issues are either: < 7 days old, stamped `triaged-defer` with revisit comment, linked to an in-progress fix-epic, or closed. PLUS: zero `criticality:critical` open without active fix-epic, zero `criticality:high` open > 14 days without active fix-epic.

### Sweep anti-patterns

| Anti-pattern                                                         | What to do instead                                                               |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Skipping user-confirmation gate                                      | Always present and wait                                                          |
| Stamping `triaged-epic` before user `y`                              | All stamps live after gate returns `y`                                           |
| Invoking `/supervisor` inline                                        | Leave fix-epics `queued`; user dispatches later                                  |
| Inventing a sixth disposition                                        | Surface under "Needs human triage"                                               |
| Storing numeric cursor in task body                                  | Labels are the cursor                                                            |
| Parenting fix-epics under `epic-a0523a25`                            | Parent under relevant component epic                                             |
| Bundling > 5 issues into one fix-epic                                | Split or surface as human-triage                                                 |
| Re-running cycle without halting                                     | Halt; re-invoke for next cycle                                                   |
| Adopting a "suggested axiom" from an incident report verbatim        | Strip per A17; redo the cost-ladder reasoning from the detached vantage          |
| Proposing escalation from one incident                               | Need ≥3 cited recurrences (CBA); otherwise `defer` with `needs-more-recurrences` |
| "Add a gate" / "add an axiom" without naming the ENFORCEMENT-MAP row | Cite the specific row the fix propagates from or would add; default L0/L1        |
