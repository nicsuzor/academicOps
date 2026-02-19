---
name: custodiet-check
description: Health check evaluation prompt for the Custodiet agent component
---

# Custodiet Health Check

Evaluation prompt for assessing the Custodiet agent's performance.

## Component Overview

The Custodiet agent (`agents/custodiet.md`) enforces workflow integrity (premature termination, scope explosion, plan-less execution). It outputs OK, WARN, or BLOCK decisions.

## Evaluation Prompt

You are evaluating the **Custodiet** agent's performance across recent session transcripts.

### What to Look For

Search transcripts for:

- `aops-core:custodiet` agent invocations
- `OK`, `WARN`, or `BLOCK` outputs from custodiet
- `custodiet_block.py` script invocations
- Block records in `$ACA_DATA/custodiet/blocks/`
- Workflow violations (premature exit, scope drift) that custodiet should have caught

### Assessment Criteria

#### 1. Workflow Integrity Detection Accuracy

| Rating         | Criteria                                                        |
| -------------- | --------------------------------------------------------------- |
| **Good**       | Correctly identifies workflow violations, no false accusations |
| **Acceptable** | Occasional misclassification, but major violations caught       |
| **Poor**       | Misses clear violations or flags legitimate work                |

**Evidence to cite**: Compare agent workflow to requests and plans. Did custodiet correctly assess?

#### 2. Principle Citation Correctness

| Rating         | Criteria                                                       |
| -------------- | -------------------------------------------------------------- |
| **Good**       | Cites correct axiom/heuristic (A#N, H#N, P#N) for each finding |
| **Acceptable** | Principle cited is related but not most specific               |
| **Poor**       | Wrong principles cited or no citation                          |

**Evidence to cite**: Check WARN/BLOCK outputs. Is the cited principle actually violated?

#### 3. False Positive Impact

| Rating         | Criteria                                                |
| -------------- | ------------------------------------------------------- |
| **Good**       | No false positives blocking legitimate work             |
| **Acceptable** | Rare false positives, quickly resolved                  |
| **Poor**       | False positives cause significant rework or frustration |

**Evidence to cite**: Find BLOCK decisions. Were they justified? Did they stop valid work?

#### 4. Missed Violation Detection

| Rating         | Criteria                                           |
| -------------- | -------------------------------------------------- |
| **Good**       | No clear workflow violations go undetected         |
| **Acceptable** | Minor violations missed, major caught              |
| **Poor**       | Significant workflow anti-patterns go unchallenged |

**Evidence to cite**: Look for premature exits or scope explosions. Did custodiet catch them?

#### 5. Output Format Compliance

| Rating         | Criteria                                                      |
| -------------- | ------------------------------------------------------------- |
| **Good**       | Outputs follow exact format (OK / WARN+fields / BLOCK+fields) |
| **Acceptable** | Minor format deviations that don't break parsing              |
| **Poor**       | Format errors causing parsing failures                        |

**Evidence to cite**: Check custodiet outputs against spec. Any preamble, extra text, or format errors?

### Output Format

```markdown
## Custodiet Health Assessment

**Overall Health**: [Healthy | Needs Attention | Critical]

### Decision Analysis

**Total invocations**: [N]
**OK decisions**: [N]
**WARN decisions**: [N]
**BLOCK decisions**: [N]

#### Notable Decisions

##### Decision 1: [Session ID, Turn N]

**Context**: [brief description of what agent was doing]
**Custodiet output**: [OK/WARN/BLOCK]
**Assessment**: [Correct/Incorrect] - [reason]
**Principle cited**: [if any] - [correct/incorrect]

[Repeat for notable decisions]

### Missed Violations

| Session | Turn | Agent Action  | Should Have Been |
| ------- | ---- | ------------- | ---------------- |
| [id]    | [N]  | [description] | [WARN/BLOCK]     |

### False Positives

| Session | Turn | Decision     | Why False Positive |
| ------- | ---- | ------------ | ------------------ |
| [id]    | [N]  | [WARN/BLOCK] | [reason]           |

### Format Compliance

**Compliant outputs**: [N] ([%])
**Non-compliant outputs**: [N]

Non-compliance examples:

- [Session ID]: [what was wrong]

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

- BLOCK decisions on clearly legitimate work
- Major workflow violations (like premature exit) consistently missed
- Principle citations frequently wrong
- Output format errors breaking hook parsing
