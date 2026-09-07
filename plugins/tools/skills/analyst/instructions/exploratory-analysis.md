---
title: Exploratory Analysis
type: note
category: instruction
permalink: analyst-chunk-exploratory-analysis
description: Pattern for iterative data exploration yielding to user guidance at each step.
---

# Exploratory Analysis

Exploratory analysis investigates patterns and relationships in clean data. For data quality issues (missing values, unexpected nulls, join defects), switch to the data investigation workflow and produce reusable scripts in `analyses/`.

## Iterative exploration workflow

1. **Load data via canonical path and show summary statistics**:
   ```python
   from pathlib import Path
   import duckdb

   PROJECT_ROOT = Path(__file__).resolve().parent
   DB_PATH = (PROJECT_ROOT / "dbt" / "data" / "local_cache.duckdb").resolve()
   conn = duckdb.connect(str(DB_PATH), read_only=True)
   df = conn.execute("SELECT * FROM fct_cases").df()
   print(df.describe())
   ```
2. **Stop and report**: Share findings with the user. Ask: _"What would you like to explore?"_
3. **Generate a single visualization or model**: Render output and interpret findings.
4. **Stop and discuss**: Confirm next question with user before proceeding.

## Discipline checklist

- Take one analytical step at a time; never generate multi-chart dumps unprompted.
- Access data exclusively via modelled marts or staging models; never query raw upstream sources.
- Always resolve absolute canonical database paths; never use cwd-relative strings.
- Verify canonical-source parity before drawing substantive conclusions.
- Record notable findings in code comments or experiment READMEs.
