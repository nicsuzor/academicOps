---
name: ground-truth
description: Establish and refine ground truth labels for evaluation datasets. Use when creating, reviewing, or updating labels for any judgment/reasoning task.
allowed-tools: Read,Grep,Glob,Edit,Write
version: 1.0.0
permalink: skills-ground-truth
---

# Ground Truth Labeling

## Purpose

Establish rigorous, defensible ground truth labels for evaluation datasets. Ensures labels derive from authoritative sources rather than intuition, and documents reasoning for reproducibility and auditability.

## When to Use

Invoke when:
- Creating ground truth labels for a new dataset
- Reviewing records with high scorer/judge disagreement
- Refining existing labels based on new understanding
- Auditing label consistency across a dataset

## Core Principle: Guidelines Are Authoritative

**Ground truth derives from explicit guidelines, not intuition.**

When labeling, the answer must come from the **established criteria themselves**, not from general judgment about what "should" be the case.

```
❌ "This seems like good journalism, so it shouldn't be flagged"
✅ "Guideline X permits quoting harmful language when [condition]. This article meets that condition."
```

## Workflow

### 1. Load Relevant Guidelines

Before labeling any record, load and review the authoritative criteria:
- What rules apply?
- What are the explicit conditions for violation/non-violation?
- What edge cases does the guideline address?

### 2. Analyze the Record

For each record:
1. Identify potential issues (terminology, framing, sources, etc.)
2. For each issue, find the **specific guideline provision** that applies
3. Determine if the guideline's conditions for violation are met

### 3. Construct the Label

**Label structure:**
```yaml
ground_truth:
  violating: true/false
  reasons:
  - Primary reason with guideline reference
  - 'OPTIONAL: Secondary observation that scorers need not require'
```

**Reason categories:**
- **Primary**: Scorers should expect judges to identify this
- **OPTIONAL**: Valid observation that reasonable judges might not mention

### 4. Document Ambiguity

High disagreement signals:
- Ambiguity in the guidelines themselves
- Cases where guidelines conflict or don't clearly apply
- Need to consult authoritative sources

When encountering genuine ambiguity, document it - don't force a label.

## OPTIONAL Reasons

Prefix with "OPTIONAL:" for secondary observations:
- Scorers should **not require** judges to mention these
- If a judge **does** comment, scorers should expect correctness
- Captures edge cases or nuanced guideline applications

**Example:**
```yaml
reasons:
- Article provides critical framing and therefore DOES NOT VIOLATE quote attribution rules.
- 'OPTIONAL: Uses "activists" - guidelines discourage this when implying negative connotations, but usage here is neutral.'
```

## Common Labeling Pitfalls

| Pitfall | Correction |
|---------|------------|
| Labeling by intuition | Find explicit guideline provision |
| Assuming guidelines agree | Check each criterion separately |
| Over-strict interpretation | Guidelines often permit with conditions |
| Ignoring context | Most guidelines consider framing/purpose |
| Binary thinking | Use OPTIONAL for nuanced observations |

## Consistency Checks

When refining labels:
1. **Same reasoning → same label**: If two records have the same characteristic, they should have the same label
2. **Document changes**: Log all label changes with rationale
3. **Test edge cases**: Does this label imply changes to similar records?

## Output

For each labeling decision, provide:
1. The label (violating: true/false)
2. Primary reason(s) with guideline references
3. Any OPTIONAL observations
4. Rationale connecting guideline text to record content