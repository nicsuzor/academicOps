---
name: qa-check
description: Health check evaluation prompt for the QA Agent component
---

# QA Agent Health Check

Evaluation prompt for assessing the QA Agent's performance.

## Component Overview

The QA Agent (`agents/qa.md`) provides independent end-to-end verification before task completion. It verifies output quality, process compliance, and semantic correctness with a "cynical verification mindset."

## Evaluation Prompt

You are evaluating the **QA Agent** component's performance across recent session transcripts.

### What to Look For

Search transcripts for:

- `aops-core:qa` agent invocations
- `QA Verification Report` outputs
- `VERIFIED` or `ISSUES` verdicts
- Red flag detection mentions
- Work approved by QA that later failed

### Assessment Criteria

#### 1. Verification Thoroughness

| Rating         | Criteria                                                                                |
| -------------- | --------------------------------------------------------------------------------------- |
| **Good**       | All three dimensions checked (Output Quality, Process Compliance, Semantic Correctness) |
| **Acceptable** | Dimensions checked but some areas cursory                                               |
| **Poor**       | Dimensions skipped or superficially checked                                             |

**Evidence to cite**: Check QA reports. Were all dimensions addressed with real analysis?

#### 2. Issue Detection Accuracy

| Rating         | Criteria                                                   |
| -------------- | ---------------------------------------------------------- |
| **Good**       | Real issues found, no phantom issues, appropriate severity |
| **Acceptable** | Most issues caught, occasional severity misclassification  |
| **Poor**       | Major issues missed or trivial issues flagged as critical  |

**Evidence to cite**: Compare QA findings to actual work state. Were issues real?

#### 3. False Confidence Prevention

| Rating         | Criteria                                |
| -------------- | --------------------------------------- |
| **Good**       | Never approves broken work as VERIFIED  |
| **Acceptable** | Rare false approvals, minor issues      |
| **Poor**       | Approves work that clearly has problems |

**Evidence to cite**: Find VERIFIED verdicts. Was the work actually complete and correct?

#### 4. Red Flag Detection

| Rating         | Criteria                                                 |
| -------------- | -------------------------------------------------------- |
| **Good**       | Catches placeholders, empty sections, template artifacts |
| **Acceptable** | Catches most red flags                                   |
| **Poor**       | Red flags slip through (TODO, FIXME, empty content)      |

**Evidence to cite**: Look for red flag patterns in approved work.

#### 5. Report Quality

| Rating         | Criteria                                         |
| -------------- | ------------------------------------------------ |
| **Good**       | Clear verdict, specific issues, actionable fixes |
| **Acceptable** | Verdict clear but recommendations vague          |
| **Poor**       | Unclear verdict or unhelpful recommendations     |

**Evidence to cite**: Check QA report structure. Is it actionable?

### Output Format

```markdown
## QA Agent Health Assessment

**Overall Health**: [Healthy | Needs Attention | Critical]

### Verification Analysis

**Total invocations**: [N]
**VERIFIED verdicts**: [N]
**ISSUES verdicts**: [N]

#### Instance Analysis

##### Instance 1: [Session ID, Turn N]

**Work being verified**: [brief description]
**QA verdict**: [VERIFIED/ISSUES]
**Dimensions checked**:

- Output Quality: [Yes/No/Partial]
- Process Compliance: [Yes/No/Partial]
- Semantic Correctness: [Yes/No/Partial]
  **Assessment**: [Correct verdict / False positive / False negative]
  **Evidence**: [what supports this assessment]

[Repeat for notable instances]

### False Confidence Cases

Cases where QA said VERIFIED but work had problems:

| Session | Turn | What Was Approved | Actual Problem   |
| ------- | ---- | ----------------- | ---------------- |
| [id]    | [N]  | [description]     | [what was wrong] |

### Missed Issues

Issues that QA should have caught:

| Session | Turn | Issue Missed  | Severity       |
| ------- | ---- | ------------- | -------------- |
| [id]    | [N]  | [description] | [High/Med/Low] |

### Red Flag Detection

**Red flags detected**: [N]
**Red flags missed**: [N]

Missed examples:

- [Session ID]: [what was missed]

### Report Quality Analysis

**Well-structured reports**: [N] ([%])
**Actionable recommendations**: [N] ([%])

Quality issues:

- [Pattern of poor reports]

### Aggregate Findings

**Strengths**:

- [Pattern that works well]

**Weaknesses**:

- [Pattern that needs improvement]

### Recommendations

1. [Specific actionable recommendation]
2. [...]
```

## Red Flags

Immediate attention needed if:

- QA approves work with obvious problems (VERIFIED when broken)
- Red flags (TODO, placeholders) consistently missed
- All three verification dimensions not checked
- Reports lack actionable recommendations
- QA adds caveats to VERIFIED ("mostly works", "should be fine")
