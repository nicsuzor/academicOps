---
name: trend-review
type: command
category: instruction
description: Multi-session performance trend analysis — review many transcripts/audit files to assess how well a framework component is working over time.
triggers:
  - "trend review"
  - "performance trends"
  - "how well is X working"
  - "assess effectiveness"
  - "review many sessions"
modifies_files: true
needs_task: false
mode: execution
domain:
  - quality-assurance
  - framework
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Agent, mcp__pkb__task_search
model: opus
permalink: commands/trend-review
---

# /trend-review — Multi-Session Performance Trend Analysis

**Purpose**: Review many sessions/audit files to assess how well a framework component is performing over time. Produces an evidence-based trend report with specific recommendations.

**Distinction from /retro**: `/retro` reviews individual sessions for agent behavior quality. `/trend-review` reviews MANY sessions to assess whether a SYSTEM (gate, agent, skill, workflow) is achieving its goals across the population.

## Workflow

### 1. Define the Review Question

The user specifies what to assess. Examples:

- "How well is custodiet + RBG catching axiom violations?"
- "Is the hydration gate reducing context-free starts?"
- "Are /retro reviews finding real issues or producing noise?"
- "How effective is the daily skill at surfacing urgent tasks?"

If the user's question is vague, ask for specifics:

- **Component**: What system/feature is being evaluated?
- **Success criteria**: What would "working well" look like?
- **Time window**: How far back to look?
- **Concern**: Is there a specific worry or hypothesis?

### 2. Identify Data Sources

**Read the relevant framework workflows first.** Before mapping data sources, check the `/framework` skill's workflow router (`.agents/skills/framework/SKILL.md`). If the review touches hooks/gates, read `09-session-hook-forensics.md` — it documents exactly where each type of data lives and how to extract it. Do not skip this step.

Map the review question to available data. For any framework component, there are typically MULTIPLE data sources at different levels of detail:

| Data Source                                    | What It Contains                                                                                                                | Location                                     |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **Markdown transcripts** (your primary source) | Full conversation pre-rendered in readable markdown. Both abridged (`*-abridged.md`) and full (`*-full.md`) forms. ~10K+ files. | `~/.aops/sessions/transcripts/`              |
| **Raw session logs** (JSONL/JSON)              | Same content as markdown transcripts but in raw format. Use only if markdown isn't available.                                   | `~/.aops/sessions/client-logs/`              |
| **Hook event logs** (JSONL)                    | Every hook event with full context: PreToolUse, PostToolUse, SubagentStart/Stop, verdicts                                       | `~/.aops/sessions/hooks/*-hooks.jsonl`       |
| **Subagent transcripts**                       | Full output of subagents (e.g., RBG verdicts, Marsha QA) — referenced by `agent_transcript_path` in SubagentStop events         | Paths in hook JSONL SubagentStop events      |
| **Audit files**                                | INPUT documents sent to review agents (e.g., custodiet context sent to RBG). These are INPUT, NOT output.                       | `~/.aops/sessions/hooks/*-custodiet.md` etc. |
| **Session metadata**                           | Gate state, ops counts, blocked status                                                                                          | `~/.aops/sessions/polecats/*/`               |
| **Session summaries**                          | High-level session overviews                                                                                                    | `~/.aops/sessions/summaries/`                |
| **PKB tasks**                                  | Task lifecycle data                                                                                                             | Via `mcp__pkb__task_search`                  |

**Critical distinction**: Audit files are INPUT to a review agent, not its output. To find what a review agent (e.g., RBG) actually concluded, look in:

1. **Hook JSONL**: `SubagentStop` events with the agent type contain `last_assistant_message` (the verdict) and `agent_transcript_path` (the full transcript)
2. **Session transcripts**: The full conversation shows what happened before and after the agent fired

**Verify data exists** before proceeding:

```bash
ls -lt <data-path> | head -5
ls <data-path> | wc -l
```

If the data source is empty or doesn't exist, report that and stop — don't fabricate analysis from missing data.

**Understand the data's limitations upfront.** Before reading any files, determine:

- Does this data source capture INPUT, OUTPUT, or both? (e.g., custodiet audit files are input to RBG, not RBG's verdict)
- What ISN'T in this data? What would you need to answer the review question fully?
- State these limitations in the report's executive summary, not buried in a confidence section at the end. If the data cannot answer the review question, that IS the primary finding.

### 3. Build the Corpus Index

Understand the shape of the data before sampling:

```bash
# Volume over time (files per day)
ls <data-path> | sed 's/.*\///' | cut -c1-8 | sort | uniq -c | sort -rn

# Size distribution (bigger files often = more interesting sessions)
ls -lS <data-path> | head -20

# Unique sessions (if naming includes session hashes)
ls <data-path> | <extract-hash> | sort -u | wc -l
```

Record: total file count, date range, volume per day, size distribution. This goes in the report.

**Format evolution warning**: Data formats change as the framework develops. Note the date of each file and don't penalize older files for format differences. Evaluate substance, not format.

### 4. Sample Strategically

Reviewing everything is wasteful. Sample for diversity and coverage:

**Minimum sample**: 8 files (enough for patterns, small enough for deep reading)
**Maximum sample**: 15 files (beyond this, diminishing returns — you'll be skimming)

**Selection criteria**:

- **Temporal spread**: At least 2 from the earliest available period, 2 from the most recent
- **Size diversity**: At least 1 large file, 1 small file
- **Session diversity**: Different session hashes (different agents/contexts)
- **Platform diversity**: If the system serves multiple platforms (e.g., Claude Code + Gemini CLI), sample from each. Platform-specific integration bugs can contaminate aggregate conclusions if not isolated.
- **Repeat sessions**: At least 2 where the same session had multiple data points (shows within-session dynamics)
- **Random fill**: After satisfying the above, pick the rest randomly to avoid cherry-picking

**Record your sample** with filenames and selection rationale. This is part of the report.

### 5. Deep-Read Each Sample

For each selected file, read it IN FULL. No skimming. Extract:

#### A. Context

- What was the agent doing?
- What was the user trying to accomplish?
- What triggered this data point?

#### B. Component Behavior

- What did the component under review actually do?
- Was its output/behavior correct given the context?
- Was it proportionate (not too aggressive, not too lenient)?

#### C. Accuracy Assessment

For each component action/finding:

- **True positive**: Component correctly identified a real issue
- **False positive**: Component flagged something that wasn't actually a problem
- **True negative**: Component correctly let normal work proceed (implicit — you won't see these directly)
- **False negative**: Component missed something it should have caught (requires your own independent assessment of the narrative)

#### D. Impact Assessment

- Did the component's action change the session's trajectory?
- If it intervened, did the intervention improve the outcome?
- If it didn't intervene, should it have?

### 6. Synthesize Across Samples

After individual assessments, aggregate into trends.

**Before aggregating**: Define what observable success looks like for this component. What would a "true positive" look like in the data? What would "course correction" look like? If these things aren't observable in the available data, that's the primary finding — state it upfront and qualify everything downstream as provisional.

#### Signal Quality

- True positive rate across the sample
- False positive rate (noise)
- Estimated false negative rate (what was missed)
- Is the component producing actionable output or just ceremony?
- **Distinguish absence of evidence from evidence of absence.** "No false positives observed" may mean the data doesn't capture false positives, not that they don't occur.

#### Platform Isolation

- If the sample spans multiple platforms, do findings hold for each platform independently?
- A platform-specific integration bug used as evidence for a general conclusion is a methodological error. Flag platform-specific findings clearly.

#### Temporal Trends

- Compare early-period samples to late-period samples
- Is accuracy improving, declining, or stable?
- Are the TYPES of findings changing?

#### Coverage Map

- What categories of issues does the component reliably detect?
- What categories does it consistently miss?
- Are there systematic blind spots?

#### Cost-Benefit

- What's the overhead (tokens, latency, interruption)?
- Is the overhead justified by the quality improvement?
- Where is the component clearly wasteful vs clearly valuable?
- **Is the component self-undermining?** If users or agents learn to route around the component (disable it, skip checks, dismiss warnings), that's a system integrity failure, not just a UX issue.

### 7. Produce the Report

```markdown
# Trend Review: <Component Name>

**Question**: <The review question>
**Date**: <today>
**Data source**: <path>
**Corpus**: <N> total files, <date range>
**Sample**: <N> files reviewed (selection criteria: ...)
**Reviewer**: <model name>

## Executive Summary

[3-5 sentences. Is the component working? What's the trend? What's the biggest issue? If the data cannot answer the review question, say so here — that IS the primary finding.]

## Objectives Verdict

[For each objective stated in the review question, deliver an explicit verdict:]

| Objective     | Verdict                                      | Evidence |
| ------------- | -------------------------------------------- | -------- |
| [Objective 1] | ANSWERED / PARTIALLY ANSWERED / UNANSWERABLE | [Why]    |
| ...           | ...                                          | ...      |

[Do not abandon objectives silently. If the data doesn't support an answer, say "UNANSWERABLE — [reason]" rather than substituting a proxy finding.]

## Corpus Overview

[Volume distribution, date range, any notable patterns in the raw data]

## Individual Assessments

### <filename> (<date>)

- **Context**: ...
- **Component behavior**: ...
- **Accuracy**: [TP/FP/FN counts with specifics]
- **Impact**: ...
- **Notable**: [anything surprising]

[Repeat for each sample]

## Aggregate Analysis

### Signal Quality

[Quantified: X/Y true positives, Z false positives, estimated W false negatives]

### Temporal Trends

[Early vs late comparison with specific evidence]

### Coverage Map

| Issue Category | Detection Rate         | Evidence              |
| -------------- | ---------------------- | --------------------- |
| ...            | reliable/spotty/missed | cite specific samples |

### Cost-Benefit

[Evidence-based assessment of overhead vs value]

## Recommendations

[Specific, actionable, prioritized. Each must cite evidence from the sample.]

## Confidence and Limitations

[What you're certain about, what you're uncertain about, what data would help]
```

### 8. Save the Report

```bash
mkdir -p ~/.aops/sessions/reviews
```

Save to `~/.aops/sessions/reviews/<component>-trend-<date>.md`

## Anti-patterns

| Anti-pattern                                      | Why it's wrong                                                      | What to do instead                                                                         |
| ------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Reviewing all files                               | Token waste, shallow reads                                          | Sample strategically, read deeply                                                          |
| Skimming samples                                  | Misses subtle issues                                                | Read every line of each sample                                                             |
| No temporal comparison                            | Can't assess trends                                                 | Always compare early vs late                                                               |
| Claims without citations                          | Unfalsifiable                                                       | Every claim cites a specific file                                                          |
| Over-indexing on one session                      | Anecdote, not trend                                                 | Synthesize across the whole sample                                                         |
| Counting without qualifying                       | "3 false positives" means nothing without context                   | Describe WHAT was false and WHY                                                            |
| Reviewing format, not substance                   | Format evolves; substance is what matters                           | Evaluate the interaction, not the template                                                 |
| Fabricating outcomes                              | Audit files often don't show what happened after                    | State uncertainty, don't invent narratives                                                 |
| Treating absence of data as evidence              | "No false positives observed" ≠ "false positive rate is low"        | Distinguish measurement gaps from findings                                                 |
| Using platform-specific bugs for general claims   | A Gemini integration failure ≠ a systemic concept failure           | Isolate platform variables in aggregate claims                                             |
| Keyword-matching recommendations                  | "Detect 'should work' as a signal" violates P#49                    | Recommendations must use semantic agent evaluation, not pattern matching                   |
| Burying the primary finding                       | If the data can't answer the question, that's finding #1            | Lead with structural limitations, not session-level details                                |
| Substituting proxy findings for actual objectives | "Format improved" ≠ "system is getting better"                      | Deliver explicit verdicts per objective, mark unanswerable ones                            |
| Unreproducible counts                             | "68 events" when there were 15 — wrong grep scope                   | Document the exact command that produced each aggregate number. Include it in an appendix. |
| Keyword-classifying free-text output              | Counting "WARN" keyword hits in analytical text that concluded "OK" | If classification requires judgment, document the rules and acknowledge error margin       |

## What This Command Does NOT Do

- **Does not fix the component** — it assesses effectiveness. Fixes are separate work.
- **Does not review individual agent behavior** — use `/retro` for that.
- **Does not produce a score** — qualitative assessment with evidence, not a number.
- **Does not require the component to be perfect** — the question is whether it's trending in the right direction and whether the ROI is positive.
