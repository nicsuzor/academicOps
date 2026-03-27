---
title: Experiment Logging Structure
type: note
category: instruction
permalink: research-chunk-experiment-logging
description: Standards for organizing, documenting, and managing experimental work in research projects
---

# Experiment Logging Structure

## What Are Experiments?

**Experiments** in academic research are exploratory investigations that:

- Test analytical approaches before committing to them
- Explore data patterns to generate hypotheses
- Validate measurement strategies
- Compare alternative analytical methods
- Investigate unexpected findings
- Prototype visualizations or models

Experiments are **work-in-progress** that may or may not make it into final analysis.

## Experiments vs. Production Analysis

| Aspect              | Experiments                            | Production Analysis                                                           |
| ------------------- | -------------------------------------- | ----------------------------------------------------------------------------- |
| **Location**        | `experiments/YYYYMMDD-description/`    | `dbt/models/`, `streamlit/`, `methods/`                                       |
| **Purpose**         | Exploration, testing, validation       | Final analysis for publication                                                |
| **Quality**         | Can be messy, incomplete               | Must be production-quality                                                    |
| **Documentation**   | Inline notes, README in experiment dir | Full documentation in [[methodology-files.md]], [[methods-vs-methodology.md]] |
| **Git tracking**    | May or may not be committed            | Always committed and reviewed                                                 |
| **Reproducibility** | Best effort                            | Mandatory                                                                     |

## Mandatory Experiment Directory Structure

**🚨 CRITICAL: All experiments MUST use this structure. No exceptions.**

```
experiments/
├── YYYYMMDD-short-description/
│   ├── README.md                 # Experiment purpose and findings
│   ├── notebook.ipynb            # Exploratory analysis
│   ├── data/                     # Experiment-specific data (if needed)
│   ├── outputs/                  # Charts, tables, intermediate results
│   └── scripts/                  # Throwaway or prototype scripts
├── 20241105-test-diff-in-diff/
│   ├── README.md
│   ├── did_exploration.ipynb
│   └── outputs/
│       ├── basic_model.png
│       └── results_table.csv
└── 20241108-validate-scoring/
    ├── README.md
    ├── scoring_tests.ipynb
    └── outputs/
```

### Directory Naming Convention

**Format**: `YYYYMMDD-short-description`

**Rules**:

- ✅ **Date first** - Always start with ISO date (YYYYMMDD)
- ✅ **Lowercase** - All lowercase letters
- ✅ **Hyphens** - Separate words with hyphens
- ✅ **Descriptive** - 2-5 words describing what you're testing
- ✅ **Specific** - "test-did-specification" not "analysis"

**Examples**:

- ✅ `20241105-test-diff-in-diff`
- ✅ `20241108-validate-scorer-coverage`
- ✅ `20241110-explore-appeal-patterns`
- ❌ `experiment1` (no date, not descriptive)
- ❌ `Testing_DID` (wrong format, capitals)
- ❌ `stuff` (not descriptive)

### Why Date-First Naming?

- **Chronological sorting** - `ls experiments/` shows experiments in order
- **Context** - Know when experiment was conducted
- **Reproducibility** - Match experiment to code/data state at that time
- **Cleanup** - Easy to identify old experiments for archival

## Required README.md in Each Experiment

Every experiment directory MUST contain a README.md with:

```markdown
# Experiment: [Short Description]

**Date**: YYYY-MM-DD **Status**: [In Progress / Completed / Abandoned] **Related Issue**: [Link to GitHub issue if applicable]

## Purpose

[What are you testing? What question are you trying to answer?]

## Approach

[What methods/techniques are you using?]

## Key Findings

[What did you discover? Leave blank if in progress, update when done]

## Outcome

[What happened as a result of this experiment?]

- [ ] Integrated into production analysis (location: ___)
- [ ] Abandoned (reason: ___)
- [ ] Needs further work
- [ ] Results documented in GitHub issue #___

## Files

- `notebook.ipynb` - [Description]
- `outputs/chart.png` - [Description]
```

### Why README.md Is Mandatory

Without README.md:

- ❌ Future you won't remember what the experiment was for
- ❌ Collaborators can't understand your work
- ❌ Can't trace how production analysis was developed
- ❌ Waste time re-running dead-end approaches

With README.md:

- ✅ Clear record of what was tested and why
- ✅ Documents findings even if experiment fails
- ✅ Enables picking up where you left off
- ✅ Shows evolution of analytical thinking

## Experiment Lifecycle

### Phase 1: Start Experiment

```bash
# Create new experiment directory
mkdir -p experiments/$(date +%Y%m%d)-test-new-method

# Create README template
cat > experiments/$(date +%Y%m%d)-test-new-method/README.md << 'EOF'
# Experiment: Test New Method

**Date**: $(date +%Y-%m-%d)
**Status**: In Progress

## Purpose

[TODO: Fill this in]

## Approach

[TODO: Fill this in]
EOF
```

**Start Jupyter notebook or script**:

```bash
cd experiments/$(date +%Y%m%d)-test-new-method
jupyter notebook notebook.ipynb
```

### Phase 2: Work on Experiment

- Run analyses
- Generate charts/tables in `outputs/`
- Document findings in notebook markdown cells
- Update README.md as you learn

**No quality requirements yet** - This is exploration!

### Phase 3: Conclude Experiment

**When experiment is done (whether successful or not), update README.md:**

1. **Status**: Change to "Completed" or "Abandoned"
2. **Key Findings**: Document what you learned
3. **Outcome**: Check the appropriate box and add details

### Phase 4: Integration or Archival

**If experiment was successful:**

1. **Extract production code** to appropriate location:
   - New analytical method → `methods/method_name.md` (see [[methods-vs-methodology.md]])
   - New dbt model → `dbt/models/*/model_name.sql`
   - New visualization → `streamlit/dashboard.py`

2. **Update experiment README** with location of production code
3. **Commit experiment to git** as historical record
4. **Reference in production documentation**: "Approach validated in experiments/20241105-test-did"

**If experiment failed:**

1. **Document why in README** - This is valuable! Don't repeat failed approaches
2. **Commit to git** - Negative results are results
3. **Close related GitHub issue** with explanation

**If experiment is stale (>3 months, not finished):**

1. **Decide**: Revive, abandon, or archive
2. **Update README** with decision
3. **Archive if abandoned**: Move to `experiments/_archive/` or delete if truly throwaway

## What Goes in Experiments vs. Production

### ✅ Experiments Directory

- Jupyter notebooks exploring data
- Prototype scripts testing approaches
- Throwaway visualizations
- Failed analyses (document why they failed!)
- Quick data quality checks
- Method validation tests

### ❌ NOT Experiments (Goes in Production)

- dbt models (go in `dbt/models/`)
- Production dashboards (go in `streamlit/`)
- Documented methods (see [[methods-vs-methodology.md]])
- Reusable analysis scripts (go in `scripts/` or `analyses/`)

**Rule of thumb**: If it works and you'll use it again, move it out of experiments.

## Experiment Documentation Quality

Experiments don't need production-quality code, but they MUST have:

- ✅ **Clear purpose** - Why are you doing this?
- ✅ **Documented findings** - What did you learn?
- ✅ **Outcome** - What happened as a result?

Experiments CAN be:

- Messy code
- Incomplete analyses
- Dead ends
- Failed approaches

But they CANNOT be:

- Undocumented
- Purpose unknown
- Findings unrecorded

## Integration with Git

### Committing Experiments

**When to commit:**

- ✅ When experiment reaches milestone (findings documented)
- ✅ When integrating results into production
- ✅ When abandoning (document failure for others)

**When NOT to commit:**

- ❌ Every single exploratory step
- ❌ Partial notebooks with no findings
- ❌ Before README.md is filled in

### Commit Message Format

```bash
git add experiments/20241105-test-diff-in-diff
git commit -m "experiment: Test difference-in-differences specification

Validated parallel trends assumption holds for our data.
Found treatment effect of X (95% CI: [Y, Z]).

Outcome: Integrated into methods/diff_in_diff.md
Issue: #123"
```

## Common Mistakes

### Mistake 1: No date in directory name

❌ `experiments/test-scoring/` ✅ `experiments/20241105-test-scoring/`

**Fix**: Always use date-first naming.

### Mistake 2: Missing README.md

❌ Experiment directory with only notebooks and no explanation ✅ Every experiment has README.md explaining purpose and findings

**Fix**: Create README.md immediately when starting experiment.

### Mistake 3: Not documenting failed experiments

❌ Deleting experiment directory because approach didn't work ✅ Documenting why approach failed in README.md

**Why**: Prevent others (and future you) from trying same failed approach.

### Mistake 4: Keeping production code in experiments/

❌ Running production analysis from `experiments/20241105-*/notebook.ipynb` ✅ Moving successful methods to `methods/`, `dbt/models/`, or `streamlit/`

**Fix**: Promote successful experiments to production locations.

### Mistake 5: Experiments folder becomes junk drawer

❌ 50 undocumented experiment directories with unclear purpose ✅ Each experiment documented, outdated ones archived

**Fix**: Regular cleanup, enforce README.md requirement.

## Experiment Hygiene

### Monthly Cleanup

Once per month, review `experiments/`:

```bash
# List experiments older than 3 months
find experiments/ -maxdepth 1 -type d -mtime +90
```

For each old experiment:

1. **Has findings?** → Commit if not already committed
2. **Integrated to production?** → Update README.md with location
3. **Abandoned?** → Document why, commit, consider archiving
4. **Still in progress?** → Update status or finish it

### Archive Pattern

```
experiments/
├── _archive/                    # Old experiments (optional)
│   └── 2024/
│       └── Q1/
│           └── YYYYMMDD-*/
└── [active experiments]/
```

## Experiments in Research Workflow

```
Research Question
    ↓
METHODOLOGY.md (research design)
    ↓
Experiments (test approaches)
    ↓
    ├─ Success → Production (methods/, dbt/, streamlit/)
    ├─ Failure → Document in experiment README
    └─ Partial → Iterate in new experiment
```

## Enforcement

Experiment structure is MANDATORY:

- **No undocumented experiments**
- **No experiments without dates**
- **No experiments without README.md**
- **No production code in experiments/**

Violations are bugs. Report them.
