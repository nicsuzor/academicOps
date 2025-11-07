# Jupyter Notebook Archive Template

This template provides the standard structure for archiving experimental analysis in Jupyter notebooks.

## Notebook Header (Markdown Cell)

```markdown
# [Experiment Title]: [Short Description]

**Date:** Month DD, YYYY **Experiment ID:** [identifier if applicable] **Status:** ✅ [SUCCESS / PARTIAL SUCCESS / ARCHIVED]

---

## Executive Summary

[2-4 paragraphs summarizing:]

- **The Problem:** What issue or question prompted this work
- **The Solution:** What approach was tested
- **The Results:** Key quantitative findings
- **The Impact:** What changed in production as a result

**Key Findings:**

- Finding 1 with specific metrics
- Finding 2 with specific metrics
- Finding 3 with specific metrics

**Decision Made:** [What decision or action resulted from this work]
```

## Standard Section Structure

### Part 1: Problem/Background (Markdown Cell)

```markdown
---

## Part 1: The Problem - [Descriptive Title]

### Background

[Context explaining why this work was needed]

### Discovery Process

[How the problem was discovered or identified]

**Pattern Observed:**

- Symptom 1
- Symptom 2

**Evidence:**

- Quantitative evidence (numbers, percentages)
- Sample cases or examples
- Affected systems/models/criteria

### Why This Matters

[Why solving this problem is important] [Impact if left unaddressed]
```

### Part 2: Solution/Approach (Markdown Cell)

```markdown
---

## Part 2: The Solution - [Solution Name/Description]

### Overview

[High-level description of the solution approach]

### Design Details

[Detailed explanation of the solution]

**Key Design Principles:**

1. Principle 1 - Explanation
2. Principle 2 - Explanation
3. Principle 3 - Explanation

### Implementation

[How the solution was implemented] [Code patterns, configurations, model changes]
```

### Part 3: Experiment Design (Markdown Cell)

```markdown
---

## Part 3: Experiment Design

### Sample Selection

[How data/cases were selected for the experiment]

### Treatment Groups

- **BASELINE (Control):** [Description of baseline/control]
- **TREATMENT:** [Description of treatment/intervention]

### Success Criteria

**Minimum Success:**

- Criterion 1 with threshold
- Criterion 2 with threshold

**Strong Success:**

- Criterion 1 with higher threshold
- Criterion 2 with higher threshold

### Models/Conditions Tested

[List models, configurations, or conditions being compared]
```

### Setup Code (Code Cell)

```python
# Setup
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import duckdb
from pathlib import Path

# Configure plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('colorblind')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11

# Load data
# Option 1: From DuckDB warehouse
conn = duckdb.connect('data/warehouse.db', read_only=True)

# Option 2: From cached DuckDB
cache_db = Path('path/to/local_cache.duckdb')
conn = duckdb.connect(str(cache_db), read_only=True)

# Option 3: From CSV/Parquet
# df = pd.read_csv('data/experiment_results.csv')

print("✅ Setup complete")
print(f"📊 Data source: [describe source]")
```

### Part 4: Results (Markdown Cell)

```markdown
---

## Part 4: Results

### Overall Metrics
```

### Load Results (Code Cell)

```python
# Load experiment results
results_df = conn.execute("""
    SELECT *
    FROM experiment_results_table
    ORDER BY experiment_name, model
""").df()

print("📊 Results Loaded")
print(f"Total rows: {len(results_df)}")
print(f"Experiments: {results_df['experiment_name'].unique()}")

# Display results
results_df.head()
```

### Results Visualization 1 (Markdown + Code Cells)

```markdown
### [Metric Name] Comparison
```

```python
# Chart 1: Primary Metric Comparison
fig, ax = plt.subplots(figsize=(12, 6))

# Create visualization
[visualization code]

# Labels and formatting
ax.set_xlabel('[X Label]', fontsize=12, fontweight='bold')
ax.set_ylabel('[Y Label]', fontsize=12, fontweight='bold')
ax.set_title('[Chart Title]\n[Subtitle]', fontsize=14, fontweight='bold')

# Add target lines if applicable
ax.axhline(target_value, color='green', linestyle='--', linewidth=2,
           alpha=0.7, label='Target: X%')

# Format axes
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
ax.legend(loc='upper right')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()

print("\n📊 Chart 1: [Description]")
print("[What this chart shows]")
```

### Key Findings by Subgroup (Markdown + Code Cell)

```markdown
### Key Findings by [Dimension]

Break down results for each [model/condition/group]:
```

```python
# Calculate and display results for each subgroup
for group in results_df['group_column'].unique():
    group_data = results_df[results_df['group_column'] == group]

    print(f"\n{'='*60}")
    print(f"GROUP: {group}")
    print(f"{'='*60}")

    # Display metrics
    print(f"Sample size: {len(group_data):,}")
    print(f"\nMetric 1: {group_data['metric1'].mean():.1%}")
    print(f"Metric 2: {group_data['metric2'].mean():.1%}")

    # Success criteria check
    print(f"\nSuccess Criteria:")
    if group_data['metric1'].mean() < threshold:
        print(f"  ✅ SUCCESS: Metric 1 {group_data['metric1'].mean():.1%} meets threshold")
    else:
        print(f"  ❌ MISS: Metric 1 {group_data['metric1'].mean():.1%} above threshold")
```

### Part 5: Interpretation (Markdown Cell)

```markdown
---

## Part 5: Interpretation & Conclusions

### Success Criteria Met

[List which success criteria were met or not met with checkmarks]

**✅ MINIMUM/STRONG SUCCESS:**

- Criterion 1: [Status with evidence]
- Criterion 2: [Status with evidence]

**⚠️ PARTIAL SUCCESS / ❌ MISSED:**

- Criterion X: [Status with evidence]

### Key Insights

1. **[Insight title]:** [Explanation with supporting evidence]

2. **[Insight title]:** [Explanation with supporting evidence]

3. **[Insight title]:** [Explanation with supporting evidence]

### What This Means

**For the pipeline:**

- Implication 1
- Implication 2

**For research integrity:**

- Implication 1
- Implication 2

**For future work:**

- Next step 1
- Next step 2

### Next Steps

1. **✅ [Action taken]** - [Description]
2. **[Planned action]** - [Description]
3. **[Future consideration]** - [Description]

---

## Conclusion

[2-3 paragraphs summarizing:]

- What the experiment demonstrated
- Key quantitative results
- Impact and implications
- Current status

**Experiment Status:** ✅ COMPLETE - [SUCCESS LEVEL]
```

### Part 6: Appendix (Markdown Cell)

```markdown
---

## Appendix: Technical Details

### Data Sources

- **Database:** [Path/connection details]
- **Tables:** [List tables used]
- **Query Filters:** [Any important filters]

### Code References

- **Analysis Code:** `path/to/file.py` at commit `abc123`
- **dbt Models:** [List models]
- **Configuration:** `path/to/config.yaml`

### Execution

- **Run Command:** [How to execute]
- **Dependencies:** [Required packages/tools]
- **Runtime:** [How long it takes]

### Related Documentation

- `docs/METHODOLOGY.md` - [Relevant section]
- `methods/method_name.md` - [Production implementation]
- GitHub Issue #XXX - [Related discussion]

---

**Archive Date:** [Month DD, YYYY] **Notebook Version:** 1.0 **Reproducible:** [Yes/No] [(If No: data removed on YYYY-MM-DD)] **Status:** [Final - For Historical Reference Only / Active]
```

### Cleanup Code (Code Cell)

```python
# Close connections
conn.close()
print("\n✅ Analysis complete. Connection closed.")
print("\n📚 This notebook is archived as a historical record of [experiment name].")
```

## Code Patterns

### Loading Data from Multiple Sources

```python
# Pattern 1: DuckDB warehouse
conn = duckdb.connect('data/warehouse.db', read_only=True)
df = conn.execute("SELECT * FROM mart_name").df()

# Pattern 2: BigQuery (if still accessible)
from google.cloud import bigquery
client = bigquery.Client(project='project-id')
query = "SELECT * FROM dataset.table WHERE date = '2025-10-29'"
df = client.query(query).to_dataframe()

# Pattern 3: Cached results
df = pd.read_parquet('cache/experiment_results.parquet')

# Pattern 4: Multiple sources joined
baseline = pd.read_csv('results/baseline.csv')
treatment = pd.read_csv('results/treatment.csv')
combined = pd.concat([baseline, treatment], ignore_index=True)
```

### Creating Comparison Charts

```python
# Grouped bar chart comparing baseline vs treatment
fig, ax = plt.subplots(figsize=(12, 6))

groups = df['group'].unique()
x = np.arange(len(groups))
width = 0.35

baseline_values = [df[(df['group']==g) & (df['type']=='baseline')]['metric'].mean()
                   for g in groups]
treatment_values = [df[(df['group']==g) & (df['type']=='treatment')]['metric'].mean()
                    for g in groups]

bars1 = ax.bar(x - width/2, baseline_values, width, label='Baseline', alpha=0.8)
bars2 = ax.bar(x + width/2, treatment_values, width, label='Treatment', alpha=0.8)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1%}',
                ha='center', va='bottom', fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(groups)
ax.legend()
plt.tight_layout()
plt.show()
```

### Statistical Comparisons

```python
from scipy import stats

# T-test comparing two groups
baseline = df[df['type'] == 'baseline']['metric']
treatment = df[df['type'] == 'treatment']['metric']

t_stat, p_value = stats.ttest_ind(baseline, treatment)

print(f"T-statistic: {t_stat:.3f}")
print(f"P-value: {p_value:.4f}")
if p_value < 0.05:
    print("✅ Statistically significant difference (p < 0.05)")
else:
    print("⚠️ Not statistically significant (p >= 0.05)")
```

## HTML Export Configuration

After completing the notebook, export to HTML:

```bash
# Basic export
jupyter nbconvert --to html notebook.ipynb

# With custom output name
jupyter nbconvert --to html notebook.ipynb --output archive_20251029.html

# With embedded images (recommended for archival)
jupyter nbconvert --to html notebook.ipynb --no-input --output archive.html
```

## Quality Checklist

Before finalizing the archive notebook:

- [ ] Executive summary at top with key findings
- [ ] All imports in setup cell
- [ ] All cells executed (outputs visible)
- [ ] Charts have clear titles and labels
- [ ] Axes formatted appropriately (%, dates, etc.)
- [ ] Statistical tests included where appropriate
- [ ] Key findings highlighted with emphasis
- [ ] Success criteria explicitly checked
- [ ] Conclusions section summarizes implications
- [ ] Appendix documents technical details
- [ ] Reproducibility status clearly marked
- [ ] Archive date and version documented
- [ ] All connections closed in final cell
- [ ] Notebook exports to HTML successfully
- [ ] HTML export verified in browser
