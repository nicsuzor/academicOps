---
title: Data Investigation Workflow
type: reference
permalink: skills-analyst-data-investigation
description: Patterns for creating reusable investigation scripts for data quality, coverage, and root cause analysis
tags: [data-analysis, investigation, scripting, dbt, reference]
---

# Data Investigation Workflow

**🚨 CRITICAL: Axiom #15 - WRITE FOR THE LONG TERM**

When investigating data issues (missing values, unexpected patterns, data quality problems), create REUSABLE investigation scripts in the `analyses/` directory. NEVER use throwaway `python -c` one-liners for data investigation.

## When to Create Investigation Scripts

Create reusable scripts for:

- ✅ **Root cause analysis** - Tracing why data is missing or incorrect
- ✅ **Coverage analysis** - Checking how much data satisfies conditions
- ✅ **Data quality checks** - Investigating completeness, accuracy
- ✅ **Schema exploration** - Understanding structure of complex JSON/struct fields
- ✅ **Join validation** - Checking coverage of joins between tables

Use throwaway queries ONLY for:

- ❌ Quick calculations (simple arithmetic, counts)
- ❌ Checking if single command worked
- ❌ One-time data fixes

## Investigation Script Structure

Save scripts in `analyses/` directory within the dbt project:

```
dbt_project/
├── analyses/
│   ├── investigate_missing_record_ids.py
│   ├── check_ground_truth_coverage.py
│   └── validate_scorer_completeness.py
├── models/
└── tests/
```

**Script template:**

```python
"""
Investigation: [Brief description of what this investigates]

Context: [Why this investigation is needed]
Date: [YYYY-MM-DD]
Issue: [Link to GitHub issue if applicable]
"""

import duckdb
from google.cloud import bigquery
import pandas as pd


def investigate_missing_values(table_name: str, column_name: str):
    """Check what proportion of records have missing values."""
    conn = duckdb.connect("data/warehouse.db")

    query = f"""
    SELECT
        COUNT(*) as total_rows,
        COUNTIF({column_name} IS NOT NULL) as with_value,
        COUNTIF({column_name} IS NULL) as missing_value,
        ROUND(100.0 * COUNTIF({column_name} IS NOT NULL) / COUNT(*), 2) as pct_complete
    FROM {table_name}
    """

    result = conn.execute(query).df()
    print(f"=== {column_name} completeness in {table_name} ===")
    print(result)
    return result


if __name__ == "__main__":
    # Example investigation
    investigate_missing_values("judge_scores", "expected_violating")
```

## Follow Investigation Workflow

**Step 1: Create investigation script**

```bash
touch dbt_project/analyses/investigate_issue.py
```

Add docstring explaining WHAT you're investigating and WHY.

**STOP. Show script to user.**

**Step 2: Run investigation**

```bash
cd dbt_project
uv run python analyses/investigate_issue.py
```

**STOP. Share findings with user.**

**Step 3: Commit investigation script**

After investigation is complete and fix is implemented, commit the script:

```bash
git add analyses/investigate_issue.py
git commit -m "chore: Add investigation script for [issue]

Documents investigation into [problem]. Found [key finding].
Used to diagnose issue #[number].
"
```

**Why This Matters:**

- **Reproducibility** - Can rerun after data changes
- **Documentation** - Shows how issue was diagnosed
- **Testing** - Can validate fix by running investigation again
- **Learning** - Future analysts understand the problem
- **Verification** - Can compare before/after metrics

## When NOT to Create Scripts

For simple one-time checks, throwaway queries are fine:

```bash
# Quick count - OK as one-liner
uv run python -c "import duckdb; print(duckdb.connect('data/warehouse.db').execute('SELECT COUNT(*) FROM fct_cases').fetchone())"

# Checking if column exists - OK as one-liner
uv run python -c "import duckdb; conn = duckdb.connect('data/warehouse.db'); print(conn.execute('PRAGMA table_info(fct_cases)').df())"
```

But if you run MORE THAN ONE query to investigate something, that's a signal to create a script.
