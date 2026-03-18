---
title: METHODS vs. METHODOLOGY - Critical Distinction
type: note
category: instruction
permalink: analyst-chunk-methods-vs-methodology
description: Clear separation between research design (methodology) and technical implementation (methods)
---

# METHODS vs. METHODOLOGY: Critical Distinction

## The Fundamental Difference

**METHODOLOGY** (singular) = Research design, philosophical approach, overall strategy **METHODS** (plural) = Specific techniques, tools, and procedures for implementation

Think of it this way:

- **METHODOLOGY** = "What kind of study is this and why?"
- **METHODS** = "How exactly do you do each step?"

## Where Each Lives

| Documentation      | Purpose                                | Location             |
| ------------------ | -------------------------------------- | -------------------- |
| **METHODOLOGY.md** | Research design, theoretical framework | Project root         |
| **methods/*.md**   | Technical implementation details       | `methods/` directory |

## Visual Distinction

```
METHODOLOGY.md (ONE file)
    │
    ├─ Research Question
    ├─ Theoretical Framework
    ├─ Research Design
    ├─ Variables & Measures
    └─ Analysis Strategy (conceptual)
         │
         └─── REFERENCES ───> methods/ (MANY files)
                              │
                              ├─ scoring_algorithm.md
                              ├─ diff_in_diff.md
                              ├─ qualitative_coding.md
                              └─ data_cleaning.md
```

## Side-by-Side Examples

### Example 1: Measuring Content Moderation Effectiveness

| METHODOLOGY.md                                                                                                                                                               | methods/effectiveness_scoring.md                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "We operationalize 'effectiveness' using three dimensions: speed (time to resolution), accuracy (alignment with policy), and consistency (similar cases decided similarly)." | "The effectiveness score is calculated as a weighted average: `score = 0.4*speed_score + 0.4*accuracy_score + 0.2*consistency_score` where each component is normalized to [0,1]. See `analyses/calculate_scores.py` for implementation." |

**Key difference**: METHODOLOGY explains WHAT you're measuring and WHY. METHODS explains HOW to calculate it.

### Example 2: Causal Inference Strategy

| METHODOLOGY.md                                                                                                                                                                                                                                                                                              | methods/diff_in_diff.md                                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "We use a quasi-experimental difference-in-differences design to estimate the causal effect of policy change X on outcome Y. Treatment group is cases after policy (n=1,247), control group is cases one year prior (n=1,189). We assume parallel trends and control for case type and seasonal variation." | "The DiD estimator is implemented using `PanelOLS` from `linearmodels`: `model = PanelOLS(Y, X, entity_effects=True, time_effects=True)`. Standard errors are clustered at case level. Pre-treatment parallel trends validated using `plot_parallel_trends()` function. See `analyses/did_estimation.py` for full code." |

**Key difference**: METHODOLOGY justifies the design choice and assumptions. METHODS documents the implementation.

### Example 3: Qualitative Analysis

| METHODOLOGY.md                                                                                                                                                                                                                                                                  | methods/qualitative_coding.md                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "We employ thematic analysis to identify patterns in moderation decisions. Two coders independently code a random sample of 200 decisions using an emergent coding scheme. We assess inter-rater reliability using Cohen's kappa and resolve disagreements through discussion." | "Coding conducted in NVivo. Initial codebook had 15 codes (see `codebooks/initial.md`). After first pass, merged 3 codes and split 2 others (see `codebooks/final.md`). Cohen's kappa = 0.78 before reconciliation. Reconciliation process: coders discussed each disagreement, referred to examples in codebook, reached consensus. Final coded dataset: `data/coded_decisions.csv`." |

**Key difference**: METHODOLOGY describes the analytical strategy. METHODS documents the specific tools and process.

## Detailed Comparison Table

| Aspect                 | METHODOLOGY.md            | methods/*.md                  |
| ---------------------- | ------------------------- | ----------------------------- |
| **Focus**              | Research design           | Technical implementation      |
| **Audience**           | Academic peers, reviewers | Implementers, replicators     |
| **Language**           | Conceptual, theoretical   | Technical, procedural         |
| **Level**              | High-level strategy       | Step-by-step details          |
| **Questions answered** | "Why this approach?"      | "How exactly do you do this?" |
| **Code included**      | No                        | Yes (or references to code)   |
| **Changes when**       | Research design changes   | Implementation changes        |
| **File count**         | One                       | Many (one per method)         |

## What Goes Where: Decision Guide

### Goes in METHODOLOGY.md

✅ Research questions ✅ Theoretical frameworks ✅ Research design type (experimental, observational, etc.) ✅ Variable definitions (conceptual) ✅ Measurement strategy (conceptual) ✅ Analysis strategy (high-level) ✅ Validity considerations ✅ Limitations ✅ Justifications for design choices

### Goes in methods/*.md

✅ Algorithm specifications ✅ Code examples ✅ Package/library usage ✅ Parameter values ✅ Step-by-step procedures ✅ Data transformations ✅ Statistical test specifications ✅ Tool configurations ✅ File formats and schemas ✅ Computational requirements

## Common Confusion Points

### Confusion 1: "Analysis strategy"

**Question**: "I'm describing my analysis strategy. Where does it go?"

**Answer**: Depends on level of detail:

**METHODOLOGY.md**: "We use regression analysis to examine the relationship between X and Y, controlling for Z."

**methods/regression_analysis.md**: "Model specification: `Y ~ X + Z1 + Z2 + Z3`. Estimated using OLS with robust standard errors. Model diagnostics checked using: (1) residual plots, (2) VIF for multicollinearity, (3) Breusch-Pagan test for heteroscedasticity. See `analyses/run_regression.py`."

### Confusion 2: "Data sources"

**Question**: "Where do I document my data sources?"

**Answer**:

**METHODOLOGY.md**: High-level overview: "We use three data sources: administrative records, public decisions, and appeal data (see `data/README.md`)."

**data/README.md**: Detailed documentation: connection strings, schema, access methods, update frequency, known issues.

**methods/*.md**: Only if method is specifically about data extraction: "See `methods/bigquery_extraction.md` for query to extract cases."

### Confusion 3: "Variable definitions"

**Question**: "I'm defining my variables. METHODOLOGY or methods/?"

**Answer**: Both!

**METHODOLOGY.md**: "Dependent variable is 'processing time' measured as days from submission to final decision."

**dbt/schema.yml** or **methods/variables.md**: "`processing_days`: Calculated as `date_diff('day', submission_date, decision_date)`. NULL when no decision yet. Range: 0-365. Outliers (>365 days) flagged for review."

## Creating methods/ Files

### File Naming

**Format**: `method_name.md`

**Rules**:

- ✅ Lowercase
- ✅ Underscores separate words
- ✅ Descriptive noun or verb phrase
- ✅ One method per file

**Examples**:

- ✅ `scoring_algorithm.md`
- ✅ `diff_in_diff.md`
- ✅ `qualitative_coding.md`
- ✅ `data_cleaning.md`
- ❌ `method1.md` (not descriptive)
- ❌ `everything.md` (too broad)

### methods/ File Structure

```markdown
# Method: [Method Name]

## Purpose

[What is this method for? What does it accomplish?]

## Overview

[High-level description of the approach]

## Implementation

[Step-by-step details, code examples, algorithms]

## Parameters

[If applicable, list parameters and their meanings]

## Example

[Concrete example showing method in use]

## Validation

[How to validate this method is working correctly]

## References

[Academic papers, documentation, related methods]

## Related Files

- Code: `analyses/script_name.py`
- Tests: `tests/test_method.py`
- Data: `data/input_file.csv`
```

### Example methods/ File

**File**: `methods/scoring_algorithm.md`

````markdown
# Method: Content Moderation Quality Scoring

## Purpose

Calculate a quality score (0-100) for content moderation decisions based on speed, accuracy, and consistency.

## Overview

Quality score combines three normalized dimensions:

- Speed (40%): Time to resolution
- Accuracy (40%): Alignment with policy
- Consistency (20%): Similar cases decided similarly

## Implementation

### Formula

```python
quality_score = (
    0.4 * speed_component + 0.4 * accuracy_component + 0.2 * consistency_component
)
```
````

### Speed Component

Normalized inverse of processing time:

```python
speed_component = 100 * (1 - min(processing_days / 30, 1))
```

Range: 0 (30+ days) to 100 (instant)

### Accuracy Component

Determined by appeal outcomes:

```python
accuracy_component = 100 * (1 - upheld_appeals / total_appeals)
```

Range: 0 (all appeals upheld) to 100 (no appeals upheld)

### Consistency Component

Measured by coefficient of variation in processing time for similar cases:

```python
consistency_component = 100 * (1 - min(cv / 2, 1))
```

Range: 0 (highly variable) to 100 (perfectly consistent)

## Parameters

- `processing_days`: Days from submission to decision
- `total_appeals`: Number of appeals filed
- `upheld_appeals`: Number of appeals that reversed decision
- `cv`: Coefficient of variation for case type

## Example

```python
# Case with 5-day processing, 2/10 appeals upheld, CV=0.3
speed = 100 * (1 - 5/30) = 83.3
accuracy = 100 * (1 - 2/10) = 80.0
consistency = 100 * (1 - 0.3/2) = 85.0

quality_score = 0.4*83.3 + 0.4*80.0 + 0.2*85.0 = 82.3
```

## Validation

Test cases in `tests/test_scoring.py`:

- Edge case: 0 days processing → speed = 100
- Edge case: >30 days processing → speed = 0
- Edge case: no appeals → accuracy = 100
- Edge case: CV > 2 → consistency = 0

## References

- Similar approach: Smith et al. (2020) "Measuring Moderation Quality"
- Speed normalization: Johnson (2019) "Time-based Performance Metrics"

## Related Files

- Implementation: `analyses/calculate_quality_scores.py`
- Tests: `tests/test_scoring.py`
- dbt model: `dbt/models/marts/fct_quality_scores.sql`

````
## Integration Pattern

METHODOLOGY.md should **reference** methods/ files:

```markdown
# METHODOLOGY.md excerpt

## Analysis Approach

We calculate quality scores for each decision using three dimensions:
speed, accuracy, and consistency (see `methods/scoring_algorithm.md`
for technical details).

We then use these scores as the dependent variable in a
difference-in-differences analysis (see `methods/diff_in_diff.md`)
to estimate the effect of policy change X.
````

## Maintenance Rules

### Update METHODOLOGY.md When

- Research question changes
- Research design changes
- Conceptual definitions change
- Theoretical framework evolves

### Update methods/*.md When

- Algorithm changes
- Code implementation changes
- Parameters adjusted
- Validation approach changes
- Bug fixes in implementation

### Update BOTH When

- Changing what you're measuring (update METHODOLOGY for concept, methods/ for calculation)
- Adding new analytical approach (update METHODOLOGY for justification, methods/ for implementation)

## Quality Checklist

### METHODOLOGY.md Complete When

- [ ] Research question clearly stated
- [ ] Research design justified
- [ ] Variables conceptually defined
- [ ] Analysis strategy outlined
- [ ] All technical details referenced to methods/
- [ ] No code or implementation details present

### methods/*.md Complete When

- [ ] Purpose clearly stated
- [ ] Implementation fully documented
- [ ] Code examples provided
- [ ] Parameters explained
- [ ] Validation approach documented
- [ ] Related files listed
- [ ] No justification of research design (that's in METHODOLOGY.md)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Implementation in METHODOLOGY.md

❌ **WRONG**:

```markdown
# METHODOLOGY.md

We calculate the difference-in-differences estimator using: Y_it = β₀ + β₁*Treatment_i + β₂*Post_t + β₃*(Treatment_i × Post_t) + ε_it Implemented in Python using PanelOLS with entity fixed effects...
```

✅ **CORRECT**:

```markdown
# METHODOLOGY.md

We use a difference-in-differences design to estimate causal effects (see `methods/diff_in_diff.md` for implementation).

# methods/diff_in_diff.md

Model specification: Y_it = β₀ + β₁*Treatment_i + β₂*Post_t + β₃*(Treatment_i × Post_t) + ε_it Implemented using PanelOLS with entity fixed effects...
```

### Anti-Pattern 2: Justification in methods/

❌ **WRONG**:

```markdown
# methods/diff_in_diff.md

We chose difference-in-differences over regression discontinuity because we don't have a clear threshold cutoff. DiD allows us to leverage temporal variation while controlling for time-invariant confounders...
```

✅ **CORRECT**:

```markdown
# METHODOLOGY.md

We chose difference-in-differences over regression discontinuity because we don't have a clear threshold cutoff...

# methods/diff_in_diff.md

DiD estimator implementation using temporal variation in treatment status...
```

### Anti-Pattern 3: Duplicate Information

❌ **WRONG**: Same paragraph in both METHODOLOGY.md and methods/file.md

✅ **CORRECT**: Conceptual explanation in METHODOLOGY.md, technical details in methods/, cross-reference between them

## Summary

**One sentence rule:**

If a sentence justifies WHY → METHODOLOGY.md If a sentence explains HOW → methods/*.md

**Still confused?** Ask: "Does this sentence help a peer reviewer evaluate my research design, or does it help a programmer reimplement my analysis?"

- Reviewer → METHODOLOGY.md
- Programmer → methods/*.md
