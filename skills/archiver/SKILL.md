---
name: archiver
description: Archive experimental analysis and intermediate work into long-lived Jupyter notebooks with HTML exports before data removal or major pipeline changes. Cleans up working directories to maintain only current state. Use when completing experiments that will become unreproducible due to data removal or when major analytical decisions need to be permanently documented.
---

# Archiver

## Overview

Archive experimental analysis and intermediate research work into stable, long-lived Jupyter notebooks before removing data or making breaking pipeline changes. This skill creates comprehensive archival notebooks documenting experiments, analysis decisions, and findings that won't be part of final publications but must be preserved for research integrity and process documentation.

**Core principle:** Distinguish between reproducible research (final analysis) and process documentation (intermediate experiments). Both matter, but they require different archival approaches.

## When to Use This Skill

Invoke this skill when:

1. **Before data removal** - Removing old scorer data, deprecated datasets, or experimental tables
2. **After major experiments** - Proven quality improvements, validation studies, A/B tests
3. **When retiring analysis code** - Streamlit pages, investigation scripts, or exploratory notebooks being removed
4. **Major pipeline transitions** - Format changes, schema updates, or methodology shifts
5. **Documenting decisions** - Why we chose approach X over Y, with supporting analysis

**Key indicators:**
- User says "archive this before we remove..."
- Major experiment just completed with significant findings
- About to clean up working directory
- Analysis code exists that won't be reproducible after changes
- Need permanent record of intermediate work

## Archival vs. Reproducible Research

### Reproducible Research (Production)
- **Location:** `dbt/models/`, `streamlit/`, `methods/`
- **Purpose:** Final analysis for publication
- **Quality:** Production-ready, fully documented
- **Reproducibility:** MUST be reproducible
- **Maintenance:** Active, version-controlled, tested

### Process Documentation (Archives)
- **Location:** `experiments/YYYYMMDD-archive-description/`
- **Purpose:** Research decisions, intermediate findings
- **Quality:** Complete and honest, not polished
- **Reproducibility:** May NOT be reproducible (data might be removed)
- **Maintenance:** Static snapshot, historical reference only

**Critical distinction:** Archives document THE JOURNEY. Final analysis documents THE DESTINATION.

## Archival Workflow

### Step 1: Identify What to Archive

**Ask user to confirm:**
- What experiment or analysis is being archived?
- What findings need to be preserved?
- What data will be removed/unavailable after this?
- Where is the current analysis code? (Streamlit, Python scripts, dbt diagnostics)
- What charts/visualizations exist?
- What decisions were made based on this work?

**Review existing artifacts:**
```bash
# Find Streamlit pages
ls -1 streamlit/*.py

# Find analysis scripts
ls -1 analyses/*.py

# Find diagnostic dbt models or investigation files
find . -name "*investigation*.md" -o -name "*diagnostic*.sql"

# Check for existing experiment notebooks
ls -1 experiments/*.ipynb
```

**STOP. Confirm with user the scope of archival.**

### Step 2: Create Archive Directory

```bash
# Create archive directory with today's date
mkdir -p experiments/$(date +%Y%m%d)-archive-description
```

**Naming convention:** `YYYYMMDD-archive-short-description`

Examples:
- `20251029-archive-scorer-transition`
- `20251105-archive-quality-experiment`
- `20251110-archive-old-schema`

**STOP. Show user the archive directory name for approval.**

### Step 3: Generate Comprehensive Jupyter Notebook

Create a Jupyter notebook documenting the entire experiment. Use the structure from `@reference _CHUNKS/notebook-template.md`

**Notebook sections:**
1. Executive Summary - What was done, key findings, decision made
2. Background/Problem - Why this work was needed
3. Approach/Solution - How it was done
4. Data & Methods - Sources, transformations, analysis approach
5. Results - Charts, tables, metrics (re-create from Streamlit/scripts)
6. Interpretation - What it means
7. Conclusions & Next Steps - Decisions made, what happens now
8. Appendix - Technical details, code references, data locations

**Key principles:**
- **Run all code cells** - Save outputs in the notebook
- **Include all charts** - Re-create visualizations from Streamlit/scripts
- **Document data sources** - Where data came from (even if being removed)
- **Link to code** - Reference git commits of analysis code
- **Timestamp everything** - When experiment ran, when archived
- **Mark as non-reproducible** - If data will be removed, say so explicitly

**Code loading pattern:**
```python
# Load from DuckDB cache or dbt warehouse
import duckdb
conn = duckdb.connect('data/warehouse.db')
df = conn.execute("SELECT * FROM analysis_table").df()

# Or from cached DuckDB
cache_path = Path('tjadbt/data/local_cache.duckdb')
conn = duckdb.connect(str(cache_path), read_only=True)
```

**STOP. Show user the notebook structure and first few cells for approval.**

### Step 4: Populate Notebook with Analysis

**Transfer analysis from existing code:**

If analysis is in Streamlit:
- Copy data loading logic
- Re-create charts using matplotlib/plotly
- Extract metrics calculations
- Document findings from dashboard text

If analysis is in Python scripts:
- Copy investigation functions
- Run and capture outputs
- Document findings

If analysis is in dbt diagnostics:
- Query results tables
- Document issue and resolution
- Show before/after metrics

**Execute all cells to save outputs:**
```python
# Ensure all visualizations are shown
import matplotlib.pyplot as plt
plt.show()  # This saves output in notebook

# Document findings in markdown cells
```

**STOP. Execute notebook and verify all outputs are captured.**

### Step 5: Export to HTML

Create static HTML export for long-term viewing:

```bash
jupyter nbconvert --to html \
    experiments/YYYYMMDD-archive-description/notebook.ipynb \
    --output archive_YYYYMMDD.html
```

**Why HTML?**
- ✅ Stable - Won't break with Python/library updates
- ✅ Portable - Viewable in any browser without Jupyter
- ✅ Complete - Includes all outputs, charts, formatting
- ✅ Archival-quality - Can be stored long-term

**Verify HTML export:**
```bash
# Open in browser to verify
xdg-open experiments/YYYYMMDD-archive-description/archive_YYYYMMDD.html
```

**STOP. Show user the HTML export for approval.**

### Step 6: Create Archive README

Write `experiments/YYYYMMDD-archive-description/README.md`:

```markdown
# Archive: [Short Description]

**Date Archived:** YYYY-MM-DD
**Status:** ✅ COMPLETE - Historical Reference Only
**Reproducible:** No (data removed on YYYY-MM-DD)

## Why This Archive Exists

[Explain what change made this necessary - data removal, schema change, etc.]

## Key Findings

- Finding 1
- Finding 2
- Decision made based on this work

## What Was Archived

- [Description of what analysis is preserved]
- Original code location: `path/to/file.py` at commit `abc123`
- Data sources: [List sources that will be unavailable]

## Files

- `notebook.ipynb` - Full analysis with outputs
- `archive_YYYYMMDD.html` - Static HTML export (primary reference)

## Related Documentation

- See `METHODOLOGY.md` for [relevant section]
- See GitHub issue #XXX for decision discussion
- See `methods/new_method.md` for production approach that replaced this

## Impact

[What changed in production as a result of this work?]
```

**STOP. Show user the README for approval.**

### Step 7: Clean Up Working Directory

**After archive is complete and verified, clean up:**

Identify files to remove:
- Streamlit pages only for this experiment
- Investigation scripts in `analyses/`
- Diagnostic markdown files in `data/`
- Old experimental code
- Temporary diagnostic dbt models

**Pattern:**
```bash
# Example: Remove experimental Streamlit page
git rm streamlit/experimental_scorer_page.py

# Example: Remove investigation markdown
git rm tjadbt/data/scorer_investigation.md

# Example: Remove diagnostic scripts
git rm analyses/investigate_scorer_issue.py
```

**DO NOT REMOVE:**
- Production code
- dbt models in use
- Active Streamlit dashboards
- Current documentation
- Ongoing experiments

**Ask user before removing each file:**
"I've identified these files as experiment-specific and ready for removal:
- `file1.py`
- `file2.md`

Should I remove these? Or should any be kept?"

**STOP. Get user approval before any deletions.**

### Step 8: Commit Everything

**Two commits: Archive first, cleanup second**

Commit 1 - Archive:
```bash
git add experiments/YYYYMMDD-archive-description/
git commit -m "archive: [Experiment description]

Archived analysis of [what was studied] before [what's changing].

Key findings:
- Finding 1
- Finding 2

Decision: [What decision was made based on this]

Archive includes full Jupyter notebook with outputs and HTML export.
Data will be removed in next commit, making this analysis unreproducible.

Issue: #XXX"
```

Commit 2 - Cleanup:
```bash
git rm [files to remove]
git commit -m "chore: Remove archived experiment code

Removed experimental analysis code archived in experiments/YYYYMMDD-archive-description/.

Files removed:
- [file1]
- [file2]

Working directory now contains only current/production code.

Follows archive: [commit hash of archive commit]"
```

**STOP. Show user the commit messages for approval.**

## Archive Quality Checklist

Before considering archive complete, verify:

- [ ] Jupyter notebook has executive summary at top
- [ ] All analysis code is in notebook cells
- [ ] All cells executed successfully with outputs saved
- [ ] Charts and visualizations are visible in notebook
- [ ] HTML export generated and verified in browser
- [ ] README.md documents why archive exists
- [ ] README.md lists what data will be unavailable
- [ ] README.md links to related production code/docs
- [ ] Archive committed to git before cleanup
- [ ] Cleanup committed separately with reference to archive
- [ ] Working directory contains only current code
- [ ] User confirms archive captures everything needed

## Common Patterns

### Pattern 1: Archiving Streamlit Analysis

**Source:** Existing Streamlit page with charts and metrics

**Process:**
1. Copy data loading code to notebook
2. Re-create charts using matplotlib/plotly
3. Extract text explanations to markdown cells
4. Document findings
5. Remove Streamlit page after archiving

### Pattern 2: Archiving Investigation Scripts

**Source:** Python scripts in `analyses/` directory

**Process:**
1. Copy investigation functions to notebook
2. Run functions and capture outputs
3. Document what was discovered
4. Add interpretation in markdown
5. Remove investigation scripts after archiving

### Pattern 3: Archiving dbt Diagnostics

**Source:** Diagnostic dbt models or investigation markdown

**Process:**
1. Query diagnostic results
2. Document issue and resolution
3. Show before/after metrics
4. Link to production fix
5. Remove diagnostic models/docs after archiving

### Pattern 4: Archiving Before Data Removal

**Critical case:** Analysis depends on data that will be deleted

**Process:**
1. Run all analysis while data still exists
2. Save ALL outputs in notebook (no external dependencies)
3. Mark clearly as "Non-Reproducible" in notebook header
4. Document exactly what data is being removed and why
5. Export HTML as primary long-term reference
6. Only remove data after archive is committed

## Integration with Research Documentation

Archives complement but don't replace standard research documentation:

- **METHODOLOGY.md** - Research design (updated if approach changed based on archive)
- **methods/*.md** - Production methods (may reference "validated in experiments/YYYYMMDD-archive-X")
- **experiments/YYYYMMDD-archive-X/** - Process documentation (this archive)

**Cross-reference pattern:**

In METHODOLOGY.md:
```markdown
We chose QualScore over template matching based on validation
experiments (see experiments/20251029-archive-scorer-transition/).
```

In archive README.md:
```markdown
This work led to production implementation documented in
methods/qualScore_scoring.md and updated methodology in METHODOLOGY.md.
```

## Error Recovery

If archival process is interrupted:

1. **Before cleanup:** Archive exists but cleanup not done
   - **Safe:** Just complete cleanup steps
   - Working directory still has old code but archive is preserved

2. **During notebook creation:** Partial notebook
   - **Safe:** Continue editing notebook or start over
   - No permanent changes yet

3. **After cleanup but found missing content:**
   - **Recovery:** `git revert` cleanup commit
   - Re-run archival process
   - Clean up again when complete

**Key safety:** Always commit archive BEFORE cleanup. This allows recovery if something was missed.

## Resources

### Notebook Template

See `_CHUNKS/notebook-template.md` for complete Jupyter notebook template with:
- Standard section structure
- Code patterns for loading data
- Chart creation examples
- Markdown cell templates
- HTML export configuration

### Example Archive

See TJA project: `experiments/20251029_scorer_validation_experiment.ipynb`
- Comprehensive structure
- Executive summary with key findings
- Visual results with charts
- Technical appendix
- HTML export

## Quick Reference Commands

```bash
# Create archive directory
mkdir -p experiments/$(date +%Y%m%d)-archive-description

# Export notebook to HTML
jupyter nbconvert --to html notebook.ipynb --output archive.html

# Commit archive
git add experiments/YYYYMMDD-archive-description/
git commit -m "archive: Description"

# Clean up (after archive committed)
git rm old_experimental_file.py
git commit -m "chore: Remove archived experiment code"
```
