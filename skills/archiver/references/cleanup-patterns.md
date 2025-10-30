# Cleanup Patterns for Working Directories

Guide to identifying experimental/temporary files that should be archived and removed vs. production code that should be kept.

## File Categories

### REMOVE After Archiving

Files that served the experiment but are no longer needed once archived:

#### Experimental Analysis Code

**Streamlit pages for experiments:**
```
streamlit/experimental_*.py
streamlit/*_test.py
streamlit/*_investigation.py
streamlit/old_*.py
```

**Characteristics:**
- Created specifically for one experiment
- Not part of ongoing dashboards
- Functionality superseded by new approach
- Named with "experimental", "test", "old", "investigation"

**Example:** `streamlit/scorer_reliability_investigation.py` - Created to investigate scorer issues, no longer needed after QualScore deployed

#### Investigation Scripts

**Analysis investigation scripts:**
```
analyses/investigate_*.py
analyses/debug_*.py
analyses/explore_*.py
analyses/*_experiment.py
```

**Characteristics:**
- One-off investigative code
- Created to diagnose specific issue
- Findings now documented in archive
- Not reusable for future analysis

**Example:** `analyses/investigate_scorer_false_negatives.py` - Diagnosed template matching problem, findings in archive

#### Diagnostic Documentation

**Investigation markdown files:**
```
data/*_investigation.md
data/*_diagnosis.md
data/*_fix_summary.md
tjadbt/data/*_investigation.md
```

**Characteristics:**
- Temporary documentation of issues
- Created during problem diagnosis
- Findings now in archive or proper docs
- No longer needed for reference

**Example:** `tjadbt/data/scorer_assessments_investigation.md` - Documented problem, now archived in notebook

#### Experimental dbt Models

**Diagnostic dbt models:**
```
dbt/models/diagnostics/*.sql  (if no longer needed)
dbt/models/experiments/*.sql
```

**Characteristics:**
- Created to investigate data issues
- Not part of production pipeline
- Results captured in archive
- Can be removed after archive

**Note:** Only remove dbt models after confirming they're not referenced by production models

#### Temporary Test Data

**Sample/test data files:**
```
data/*_sample.csv
data/test_*.json
data/*_experiment.parquet
```

**Characteristics:**
- Created for specific experiment
- Not used by production pipeline
- Can be regenerated if needed
- Taking up space

### KEEP (Production Code)

Files that are part of ongoing production system:

#### Active Streamlit Dashboards

```
streamlit/main_dashboard.py
streamlit/overview.py
streamlit/quality_metrics.py
```

**Characteristics:**
- Used by team regularly
- Part of ongoing monitoring
- Not specific to one experiment
- Maintained and updated

#### Production Analysis Scripts

```
analyses/calculate_metrics.py
analyses/generate_report.py
scripts/refresh_data.py
```

**Characteristics:**
- Reusable for multiple analyses
- Part of standard workflow
- Called by other systems
- General-purpose tools

#### Production dbt Models

```
dbt/models/staging/*.sql
dbt/models/marts/*.sql
dbt/models/intermediate/*.sql
```

**Characteristics:**
- Part of active data pipeline
- Referenced by other models
- Tested and documented
- In regular use

#### Core Documentation

```
README.md
METHODOLOGY.md
methods/*.md
data/README.md
```

**Characteristics:**
- Documents current system
- Referenced by team
- Kept up-to-date
- Part of research documentation

## Decision Process

For each file, ask:

### 1. Was this created for a specific experiment?

**YES → Consider for removal**
- Check if findings are in archive
- Verify not used elsewhere
- Remove after archiving

**NO → Keep**
- Part of general workflow
- Used by multiple projects

### 2. Is this still being used?

**YES → Keep**
- Active in workflow
- Referenced by other code
- Used in dashboards

**NO → Consider for removal**
- Check git history for last use
- Verify not a dependency
- Remove if experiment-specific

### 3. Could this be reused for future work?

**YES → Keep**
- General-purpose tool
- Reusable functions
- Part of standard toolkit

**NO → Consider for removal**
- One-off investigation
- Specific to past issue
- Not generalizable

### 4. Is functionality superseded?

**YES → Remove**
- New approach implemented
- Old code no longer needed
- Kept in archive for reference

**NO → Keep**
- Still relevant
- No replacement
- Current approach

## Cleanup Workflow

### Step 1: Identify Candidates

```bash
# Find files with experimental naming patterns
find . -name "*experiment*" -o -name "*test*" -o -name "*investigation*" -o -name "*old*"

# Find recently modified analysis files
find analyses/ -type f -mtime -30

# Find Streamlit pages
ls -la streamlit/*.py

# Find investigation docs
find . -name "*investigation*.md" -o -name "*diagnosis*.md"
```

### Step 2: Review Each File

For each candidate file:

```bash
# Check last modification
ls -l path/to/file

# Check git history
git log --oneline path/to/file | head -5

# Search for references
grep -r "filename" . --exclude-dir=.git
```

### Step 3: Create Removal List

Organize files into categories:

**Definitely Remove:**
- Experiment-specific
- Functionality in archive
- No dependencies
- Superseded by new approach

**Maybe Remove:**
- Created for experiment but possibly reusable
- Not sure if still referenced
- Need user confirmation

**Definitely Keep:**
- Production code
- Active use
- General-purpose
- Referenced by other systems

### Step 4: Confirm with User

Present the removal list:

```
I've identified these files for removal (experiment-specific, archived):

DEFINITELY REMOVE:
- streamlit/scorer_investigation.py (superseded by archive)
- analyses/debug_scorer.py (findings in archive)
- data/scorer_diagnosis.md (documented in archive)

MAYBE REMOVE (need confirmation):
- analyses/calculate_overlap.py (used in experiment, but seems general?)
- streamlit/comparison_page.py (experiment-specific, but useful?)

KEEP (production/active):
- streamlit/main_dashboard.py (active use)
- dbt/models/marts/fct_quality.sql (production model)

Should I proceed with removing the DEFINITELY REMOVE files?
Should any of the MAYBE REMOVE files be kept?
```

### Step 5: Remove Files

```bash
# Remove files using git rm (preserves history)
git rm path/to/file1.py
git rm path/to/file2.md

# Commit cleanup
git commit -m "chore: Remove archived experiment code

Removed experimental analysis code archived in experiments/YYYYMMDD-archive-description/.

Files removed:
- file1.py - Experimental scorer investigation
- file2.md - Diagnostic documentation
- file3.py - One-off analysis script

Working directory now contains only production code.

Follows archive: [commit hash]"
```

## Common Patterns by Project Area

### Streamlit Cleanup

**Remove:**
- Pages created for specific investigation
- "Test" or "experimental" pages
- Superseded visualizations
- One-off comparison pages

**Keep:**
- Main dashboard
- Ongoing monitoring pages
- Production visualization tools
- Reusable components

### Analysis Scripts Cleanup

**Remove:**
- Scripts that investigate specific issues
- One-time data exploration
- Debugging scripts
- Experiment-specific calculations

**Keep:**
- Reusable utility functions
- Standard reporting scripts
- Data pipeline scripts
- General analysis tools

### Documentation Cleanup

**Remove:**
- Investigation markdown files
- Diagnostic summaries
- Issue-specific documentation
- Temporary notes

**Keep:**
- README files
- METHODOLOGY.md
- methods/*.md files
- data/README.md
- Ongoing documentation

### dbt Models Cleanup

**Remove:**
- Diagnostic models for specific issues
- Experimental transformations
- Superseded models (after migration)
- Test models

**Keep:**
- All production staging models
- All production marts
- Intermediate models in use
- Documented, tested models

**CRITICAL:** Always check dependencies before removing dbt models:

```bash
# Check if model is referenced
grep -r "ref('model_name')" dbt/models/

# Check dbt documentation
dbt docs generate
# Look for downstream dependencies
```

## Safety Rules

### ALWAYS

1. **Archive first, clean later** - Never remove files before archive is committed
2. **Use git rm** - Preserves history, enables recovery
3. **Commit separately** - Archive commit separate from cleanup commit
4. **Ask before removing** - Get user confirmation for non-obvious files
5. **Check dependencies** - Search for references before removing
6. **Test after cleanup** - Verify production systems still work

### NEVER

1. **Don't rm without git** - Use `git rm`, not `rm` (preserves history)
2. **Don't remove production code** - Only experiment-specific files
3. **Don't remove without archive** - Findings must be preserved first
4. **Don't remove dependencies** - Check references first
5. **Don't batch blindly** - Review each file individually
6. **Don't delete data without backup** - Ensure archive captures needed data

## Recovery Patterns

### If Removed Too Much

```bash
# Find what was removed
git log --stat | grep "delete"

# Restore specific file
git checkout HEAD~1 -- path/to/file

# Or revert entire cleanup commit
git revert [cleanup-commit-hash]
```

### If Cleanup Incomplete

```bash
# Add more files to cleanup
git rm additional/file.py

# Amend cleanup commit
git commit --amend

# Or create follow-up cleanup commit
git commit -m "chore: Additional experiment cleanup"
```

## Verification After Cleanup

### Check Production Systems

```bash
# Run dbt pipeline
dbt run
dbt test

# Start Streamlit dashboard
streamlit run streamlit/main_dashboard.py

# Run production scripts
python scripts/generate_report.py
```

### Verify Archive Accessibility

```bash
# Confirm archive exists
ls experiments/YYYYMMDD-archive-description/

# Verify HTML export
xdg-open experiments/YYYYMMDD-archive-description/archive.html

# Check git history
git log experiments/YYYYMMDD-archive-description/
```

### Confirm Clean State

```bash
# List remaining files
ls streamlit/
ls analyses/
ls data/

# Verify only production code remains
git status

# Check for leftover experimental files
find . -name "*experiment*" -o -name "*test*" -o -name "*investigation*"
```

## Cleanup Quality Checklist

- [ ] Archive committed before cleanup started
- [ ] Each file reviewed individually
- [ ] User confirmed removal list
- [ ] Dependencies checked (grep search)
- [ ] dbt model references verified
- [ ] Files removed using `git rm`
- [ ] Cleanup commit references archive commit
- [ ] Production systems tested after cleanup
- [ ] Archive still accessible after cleanup
- [ ] No experimental files remain
- [ ] Working directory contains only production code
- [ ] Git history preserves removed files

## Example Cleanup Sessions

### Example 1: Scorer Validation Cleanup

**After archiving scorer validation experiment:**

Remove:
- `streamlit/scorer_reliability.py` - Investigation dashboard
- `analyses/investigate_false_negatives.py` - Diagnostic script
- `tjadbt/data/scorer_assessments_investigation.md` - Issue doc
- `data/test_samples_false_negatives.json` - Test data

Keep:
- `streamlit/main_dashboard.py` - Production dashboard
- `dbt/models/marts/fct_scorer_results.sql` - Production model
- `methods/qualScore_scoring.md` - Production documentation

### Example 2: Schema Migration Cleanup

**After archiving old schema analysis:**

Remove:
- `analyses/compare_old_new_schema.py` - Migration comparison
- `streamlit/schema_migration_check.py` - Migration dashboard
- `dbt/models/diagnostics/old_schema_coverage.sql` - Diagnostic
- `data/schema_migration_summary.md` - Migration notes

Keep:
- `dbt/models/staging/stg_*.sql` - Production staging (new schema)
- `data/README.md` - Updated with new schema docs
- `methods/data_extraction.md` - Updated for new schema

### Example 3: A/B Test Cleanup

**After archiving A/B test results:**

Remove:
- `analyses/ab_test_analysis.py` - Test-specific analysis
- `streamlit/ab_comparison.py` - Test dashboard
- `experiments/test_results_*.csv` - Raw test data (in archive)

Keep:
- `streamlit/production_metrics.py` - Ongoing monitoring
- `methods/treatment_allocation.md` - General A/B methodology
- `dbt/models/marts/fct_experiments.sql` - Experiment infrastructure
