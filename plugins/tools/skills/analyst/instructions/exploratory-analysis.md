---
title: Exploratory Analysis
type: note
category: instruction
permalink: analyst-chunk-exploratory-analysis
description: Pattern for collaborative, iterative data exploration that yields to user guidance at each step
---

# Exploratory Analysis

When exploring data to understand patterns, follow collaborative discovery process.

**NOTE:** If you find yourself running multiple queries to investigate a DATA ISSUE (missing values, unexpected nulls, join problems), switch to the Data Investigation Workflow and create a reusable script.

Exploratory analysis is for understanding PATTERNS and RELATIONSHIPS in clean data. Data investigation is for diagnosing DATA QUALITY problems.

## Exploration Pattern

**Step 1: Load data and show basic statistics**

```python
import duckdb

conn = duckdb.connect("data/warehouse.db")
df = conn.execute("SELECT * FROM fct_cases").df()

print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print("\nSummary statistics:")
print(df.describe())
```

**STOP. Share findings with user. Ask: "What would you like to explore?"**

**Step 2: Create single visualization based on user direction**

```python
import plotly.express as px

fig = px.scatter(
    df,
    x="submission_date",
    y="processing_days",
    color="status",
    title="Processing Time Over Time",
)
fig.show()
```

**STOP. Discuss findings. Ask: "What pattern should we investigate next?"**

**Step 3: Follow user guidance for next exploration**

Continue one step at a time, yielding to user after each finding.

## Exploratory Analysis Anti-Patterns

❌ **Don't** create comprehensive analysis notebook without user input ❌ **Don't** generate 10 charts at once ❌ **Don't** make assumptions about what's interesting ❌ **Don't** query upstream data sources directly

✅ **Do** take one analytical step at a time ✅ **Do** explain each finding and ask for direction ✅ **Do** use dbt models for all data access ✅ **Do** document interesting findings in code comments
