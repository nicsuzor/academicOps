---
name: health-check
category: analysis
description: Semi-automatic framework health check - evaluates how well each aops framework component is doing its job.
allowed-tools: Task,Read,Glob,Grep,Write,mcp__plugin_aops-core_memory__store_memory
version: 1.0.0
permalink: skills-health-check
---

# /health-check Command Skill

Triggered, slow, expensive health check process that evaluates how well each aops framework component is doing its job. NOT a success metric - a qualitative deep-dive.

## Purpose

When triggered, the agent reviews recent transcripts and evaluates each component in detail, producing a structured report with improvement recommendations.

## Usage

```
/health-check
```

Or with specific component:

```
/health-check hydrator
/health-check custodiet
/health-check gates
/health-check qa
```

## When to Use

- After a series of sessions to assess framework performance
- When suspecting a component is underperforming
- Periodic framework maintenance (weekly/monthly)
- After significant framework changes to validate behavior

## Components Evaluated (v1)

| Component       | What It Does                                  | Health Check Focus                                                      |
| --------------- | --------------------------------------------- | ----------------------------------------------------------------------- |
| **Hydrator**    | Transforms terse prompts into execution plans | Is it getting enough information? Too much? Quality of execution plans? |
| **Gate System** | Blocks/warns on policy violations             | Are gates blocking appropriately? Over-blocking? Under-blocking?        |
| **Custodiet**   | Ultra vires detection                         | Accurate detection? False positives? Missed violations?                 |
| **QA Agent**    | Independent verification before completion    | Thoroughness? Catching real issues?                                     |

## Workflow

### Step 1: Locate Recent Transcripts

Find the 5 most recent session transcripts:

```bash
TRANSCRIPTS=$(find "$ACA_DATA/../sessions/claude" -name "*.md" -type f -mtime -7 | sort -r | head -5)
```

If fewer than 5 transcripts exist, use what's available.

### Step 2: Run Component Checks

For each component, spawn an evaluator agent:

```
Task(subagent_type="general-purpose", model="sonnet",
     description="Health check: [component]",
     prompt="[COMPONENT_CHECK_PROMPT with transcript paths]")
```

**CRITICAL**: Run checks sequentially (not in parallel) to preserve context and allow cross-referencing.

### Step 3: Component Check Prompts

Each component check follows this structure:

1. **Load context**: Read 5 recent transcripts (or portions relevant to the component)
2. **Identify instances**: Find where the component was invoked or should have been
3. **Assess quality**: Evaluate each instance against criteria
4. **Synthesize findings**: Produce structured assessment

#### Hydrator Check

See [[checks/hydrator]] for the full evaluation prompt.

Key assessment areas:

- Prompt-to-plan transformation quality
- Context gathering completeness
- Workflow selection accuracy
- Task routing appropriateness
- Deferred work capture

#### Gate System Check

See [[checks/gates]] for the full evaluation prompt.

Key assessment areas:

- Gate trigger accuracy (fired when should, didn't when shouldn't)
- Block vs warn mode appropriateness
- User friction vs protection balance
- False positive rate
- Missed violations

#### Custodiet Check

See [[checks/custodiet]] for the full evaluation prompt.

Key assessment areas:

- Ultra vires detection accuracy
- Principle citation correctness
- False positive impact (blocked legitimate work)
- Missed violations (allowed scope creep)
- Output format compliance

#### QA Agent Check

See [[checks/qa]] for the full evaluation prompt.

Key assessment areas:

- Verification thoroughness
- Issue detection accuracy
- False confidence (approved broken work)
- Red flag detection
- Report quality

### Step 4: Aggregate Report

See [[output/aggregation]] for detailed aggregation instructions.

Combine component assessments into a unified health report following this structure:

```markdown
# Framework Health Check Report

**Date**: [ISO date]
**Transcripts Analyzed**: [count]
**Session Range**: [oldest] to [newest]

## Executive Summary

[3-5 sentences on overall framework health]

## Component Assessments

### Hydrator

**Health**: [Healthy | Needs Attention | Critical]
**Summary**: [2-3 sentences]
**Key Findings**:

- [Finding with transcript evidence]
  **Recommendations**:
- [Actionable improvement]

### Gate System

[Same structure]

### Custodiet

[Same structure]

### QA Agent

[Same structure]

## Cross-Component Patterns

[Patterns that span multiple components]

## Prioritized Recommendations

1. [P0] **Critical**: [recommendation]
2. [P1] **High**: [recommendation]
3. [P2] **Medium**: [recommendation]

## Evidence Summary

| Session | Component | Finding | Severity |
| ------- | --------- | ------- | -------- |
| [id]    | [name]    | [brief] | [H/M/L]  |
```

Key aggregation rules:

- **Overall Health**: All Healthy = Healthy; 2+ Needs Attention or 1 Critical = Needs Attention; 2+ Critical = Critical
- **Prioritization**: P0 (Critical), P1 (High), P2 (Medium) - limit to top 5-7 recommendations
- **Cross-Component**: Look for patterns spanning multiple components, handoff issues, common root causes

### Step 5: Persist Report

See [[output/aggregation#Persistence]] for detailed persistence instructions.

Save the report to the health-checks directory:

```bash
REPORT_PATH="$ACA_DATA/projects/aops/health-checks/$(date +%Y-%m-%d)-health-check.md"
mkdir -p "$(dirname "$REPORT_PATH")"
```

Use Write tool to save the report.

### Step 6: Sync Key Findings to Memory

Store executive summary and critical findings in memory server:

```python
mcp__plugin_aops-core_memory__store_memory(
    content=f"Health check {date}: {executive_summary}. Critical findings: {critical_list}",
    tags=["health-check", "framework-assessment", date],
    metadata={
        "date": date,
        "components": ["hydrator", "gates", "custodiet", "qa"],
        "overall_health": overall_rating,
        "report_path": report_path
    }
)
```

### Step 7: Create Tasks for Critical Findings

For P0 (Critical) and P1 (High) recommendations, create tasks:

```python
mcp__plugin_aops-core_task_manager__create_task(
    task_title=f"[Health Check] {recommendation_summary}",
    type="task",
    project="aops",
    priority=1,  # P1 for Critical, P2 for High
    tags=["health-check", component_name, date],
    body=f"""From health check on {date}:

## Finding
{finding_details}

## Evidence
{transcript_references}

## Recommendation
{actionable_recommendation}
"""
)
```

## Single Component Mode

When invoked with a specific component (`/health-check hydrator`):

1. Skip other component checks
2. Use deeper analysis (10 transcripts instead of 5)
3. Include more detailed evidence
4. Still produce full report format (other sections marked "Not evaluated")

## Output

The skill produces:

1. **Console summary**: Brief health status for each component
2. **Persisted report**: Full markdown report in `$ACA_DATA/projects/aops/health-checks/`
3. **Memory entry**: Searchable summary in memory server
4. **Tasks**: For actionable findings

## Success Criteria

1. **Evidence-based**: Every assessment cites specific transcript evidence
2. **Actionable**: Recommendations are concrete and implementable
3. **Comprehensive**: All v1 components are evaluated
4. **Persisted**: Report is saved for historical tracking
5. **Tracked**: Critical findings become tasks

## Limitations

- Requires recent transcripts (at least 3 sessions in past week)
- Qualitative assessment, not quantitative metrics
- Slow and expensive (spawns multiple agents, reads full transcripts)
- Best used periodically, not after every session

## See Also

- [[../audit/SKILL.md|audit skill]] - Structural framework audit
- [[../audit/workflows/session-effectiveness.md|session effectiveness]] - Single session evaluation
- [[../../agents/qa.md|qa agent]] - QA agent being evaluated
- [[../../agents/custodiet.md|custodiet agent]] - Custodiet agent being evaluated
- [[../../agents/prompt-hydrator.md|hydrator agent]] - Hydrator agent being evaluated
