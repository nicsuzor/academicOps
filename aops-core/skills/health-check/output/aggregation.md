---
name: report-aggregation
description: Instructions for aggregating component health assessments into a unified report
---

# Report Aggregation Module

This module describes how to aggregate individual component health assessments into a unified framework health report.

## Input

You will have completed assessments for each component:
- Hydrator Health Assessment
- Gate System Health Assessment
- Custodiet Health Assessment
- QA Agent Health Assessment

Each assessment includes:
- Overall Health rating (Healthy | Needs Attention | Critical)
- Instance/activation analysis
- Aggregate findings (strengths, weaknesses)
- Recommendations

## Aggregation Process

### 1. Determine Overall Framework Health

Calculate from component ratings:

| Component Ratings | Framework Health |
|------------------|------------------|
| All Healthy | **Healthy** |
| 1 Needs Attention, rest Healthy | **Healthy** (with notes) |
| 2+ Needs Attention OR 1 Critical | **Needs Attention** |
| 2+ Critical | **Critical** |

### 2. Write Executive Summary

Synthesize 3-5 sentences covering:
1. Overall assessment (one sentence)
2. Strongest component performance (one sentence)
3. Weakest component performance (one sentence)
4. Primary recommendation (one sentence)
5. Context about transcript coverage (optional)

Example:
> The aops framework is performing well overall, with all components rated Healthy or Needs Attention. The Gate System showed excellent accuracy with only 2 false positives across 47 activations. The Hydrator needs attention due to context gathering issues in 30% of sampled instances. Priority recommendation: improve hydrator's file discovery heuristics to catch relevant context earlier.

### 3. Extract Cross-Component Patterns

Look for patterns that span multiple components:

**Integration Issues**
- Does hydrator output trigger appropriate gates?
- Do gate blocks get properly handled by subsequent agents?
- Does QA verify what custodiet allowed through?

**Common Root Causes**
- Same transcript showing issues in multiple components
- Patterns suggesting systemic problems (e.g., poor context everywhere)

**Handoff Problems**
- Information loss between components
- Redundant checking (same thing verified multiple times)
- Gaps (something no component checks)

### 4. Prioritize Recommendations

Collect all recommendations from component assessments and prioritize:

**Prioritization Criteria**:
1. **Impact**: How many sessions/users affected?
2. **Severity**: Critical > Needs Attention > Enhancement
3. **Actionability**: Can we fix this now vs needs research?
4. **Dependencies**: Does fixing X enable fixing Y?

**Output Format**:
1. [P0] Critical: [recommendation] - [which component] - [expected impact]
2. [P1] High: [recommendation] - [which component] - [expected impact]
3. [P2] Medium: [recommendation] - [which component] - [expected impact]

Limit to top 5-7 recommendations to maintain focus.

### 5. Compile Evidence Summary

Create a quick-reference table of all transcript evidence cited:

| Session | Component | Finding | Severity |
|---------|-----------|---------|----------|
| 20260205-session-abc | Hydrator | Missed context file | Med |
| 20260204-session-xyz | Gates | False positive block | Low |

This enables future auditors to quickly locate specific evidence.

## Output Format

The final aggregated report follows this structure:

```markdown
# Framework Health Check Report

**Date**: YYYY-MM-DD
**Transcripts Analyzed**: N
**Session Range**: YYYYMMDD to YYYYMMDD

## Executive Summary

[3-5 sentence synthesis]

---

## Component Assessments

### Hydrator
**Health**: [Healthy | Needs Attention | Critical]
**Summary**: [2-3 sentences from component assessment]
**Key Findings**:
- [Most important finding with evidence reference]
- [Second finding]
**Recommendations**:
- [Top recommendation for this component]

### Gate System
**Health**: [rating]
**Summary**: [summary]
**Key Findings**:
- [finding]
**Recommendations**:
- [recommendation]

### Custodiet
**Health**: [rating]
**Summary**: [summary]
**Key Findings**:
- [finding]
**Recommendations**:
- [recommendation]

### QA Agent
**Health**: [rating]
**Summary**: [summary]
**Key Findings**:
- [finding]
**Recommendations**:
- [recommendation]

---

## Cross-Component Patterns

[Patterns that span multiple components]

---

## Prioritized Recommendations

1. [P0] **Critical**: [recommendation]
   - Component: [name]
   - Evidence: [session refs]
   - Expected Impact: [description]

2. [P1] **High**: [recommendation]
   ...

---

## Evidence Summary

| Session | Component | Finding | Severity |
|---------|-----------|---------|----------|
| [id] | [name] | [brief] | [H/M/L] |

---

## Metadata

- Report generated: [ISO timestamp]
- Generator: /health-check skill v1.0.0
- Components evaluated: hydrator, gates, custodiet, qa
```

## Persistence

After generating the report:

### 1. Save to health-checks directory

```bash
REPORT_PATH="$ACA_DATA/projects/aops/health-checks/$(date +%Y-%m-%d)-health-check.md"
mkdir -p "$(dirname "$REPORT_PATH")"
```

Use the Write tool to save the report.

### 2. Sync to Memory Server

Store executive summary and critical findings:

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

### 3. Create Tasks for Actionable Findings

For P0 (Critical) and P1 (High) recommendations, create tasks:

```python
mcp__plugin_aops-core_task_manager__create_task(
    task_title=f"[Health Check] {recommendation_summary}",
    type="task",
    project="aops",
    priority=1 if severity == "Critical" else 2,
    tags=["health-check", component_name, date],
    body=f"""From health check on {date}:

## Finding
{finding_details}

## Evidence
{transcript_references}

## Recommendation
{actionable_recommendation}

## Context
Report: {report_path}
"""
)
```

## Single Component Mode

When `/health-check [component]` is invoked:

1. Only that component's assessment is performed
2. Report structure remains the same, but:
   - Other component sections show "Not evaluated"
   - Cross-component patterns section is omitted
   - Recommendations focus on the single component
3. Use 10 transcripts instead of 5 for deeper analysis
4. Include more detailed evidence excerpts

Example for single-component:

```markdown
### Gate System
**Health**: Needs Attention
**Summary**: [detailed assessment]
**Key Findings**:
- [finding 1 with full evidence]
- [finding 2 with full evidence]
- [finding 3 with full evidence]
**Recommendations**:
- [recommendation 1]
- [recommendation 2]

### Hydrator
*Not evaluated in this run*

### Custodiet
*Not evaluated in this run*

### QA Agent
*Not evaluated in this run*
```

## Quality Checklist

Before finalizing the report, verify:

- [ ] Executive summary is 3-5 sentences, not longer
- [ ] Every finding cites specific transcript evidence
- [ ] Recommendations are actionable (not vague)
- [ ] Prioritization uses P0/P1/P2 consistently
- [ ] Cross-component patterns are actually cross-component
- [ ] Evidence table includes all cited sessions
- [ ] Report saved to correct path
- [ ] Memory entry created
- [ ] Tasks created for P0/P1 findings
