---
name: analyst
description: Run academic research data analysis reproducibly -- research data immutability, canonical absolute path resolution, source-derived parity checks, transformation vs presentation layer separation, and defensible statistical methodology. Use for empirical research pipelines, modifying models/marts, data-quality testing, or result documentation. Engine details in dbt, streamlit, and python-viz skills.
---

# Analyst

Core principles for reproducible empirical research pipelines. Pair with `dbt`, `streamlit`, or `python-viz` for engine-specific commands.

**Checkpoint discipline**: Take ONE action at a time (chart, model, test), report results and interpretation, and yield to the user before continuing.

## Academic research floor

- **Data immutability**: Source datasets, ground-truth labels, and `records/` are immutable. Never alter or "fix" raw data to fit infrastructure; report gaps instead.
- **Design integrity**: Research questions drive methods. Justify every model, variable, or exclusion by research design, not computational convenience.
- **Pilot before full scale**: Audit sample outputs across all conditions for face validity and edge cases before scaling execution.
- **Fail fast on quality**: Treat data quality anomalies as findings to investigate, not nuisances to smooth over.
- **Report as argument**: State assumptions, limitations, and uncertainties. Align every figure and metric to a specific substantive claim.

## Canonical path resolution

Always resolve database, cache, and data connections from absolute project roots. Never use bare cwd-relative paths (`duckdb.connect("data/...")`).

```python
from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = (PROJECT_ROOT / "dbt" / "data" / "local_cache.duckdb").resolve()
if not DB_PATH.is_file():
    raise FileNotFoundError(f"Canonical database not found at {DB_PATH}")
conn = duckdb.connect(str(DB_PATH), read_only=True)
```

Keep `data/` completely separate from build output directories (`output/`, `_book/`, `_site/`).

### Troubleshooting "table does not exist"

1. Verify query used the absolute canonical path.
2. Check file size and timestamp (`ls -lh <canonical_path>`).
3. Scan for duplicate databases (`find . -name "*.duckdb"`) and remove them.
4. Verify the model was built into the target database (`dbt run --select <model>`).

## Source-derived parity

Before drawing conclusions or rendering figures from derived tables:

- Assert row counts and key parity between canonical sources (`records/*.yaml`, CSVs) and derived marts.
- Verify content equality on ground-truth columns. Halt on any divergence.

## Layer boundaries

| Layer                                     | Allowed                                                                             | Prohibited                                                                   |
| ----------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Transformation** (e.g. dbt)             | Cleaning, joins, aggregations, business logic (`stg_*`, `int_*`, `fct_*`, `dim_*`). | Unversioned, ad-hoc execution.                                               |
| **Presentation** (e.g. Streamlit, Quarto) | Reading pre-computed marts, display formatting, widget filtering, rendering charts. | In-line aggregations (`SUM`), joins, `CASE WHEN` logic, metric calculations. |

Never query unmodelled raw sources directly; promote staging models to marts for presentation.

## Testing and validation

- **Schema tests**: Column nullability, uniqueness, accepted values, and foreign keys.
- **Parity tests**: Assert derived tables match canonical source records verbatim with zero dropped keys.
- **Singular tests**: Multi-column assertions, date bounds, and domain logic.
- For LLM outputs: Test content-length minimums and section existence, not brittle error strings.

## Exploration and context discovery

- Read context first: `README.md`, `data/README.md`, and transformation models. See `references/context-discovery.md`.
- Explore clean patterns interactively (one step at a time); isolate data quality issues into reusable scripts in `analyses/`. See `instructions/exploratory-analysis.md`.
- Follow documentation structure in `instructions/research-documentation.md`.

## Statistical methodology

- **Pre-specify tests**: Align statistical tests to research questions before running models to prevent p-hacking.
- **Verify assumptions**: Run `scripts/assumption_checks.py` (`comprehensive_assumption_check()` or components `check_normality`, `check_homogeneity_of_variance`, `check_linearity`, `detect_outliers`) before reporting results.
- **Report completely**: Provide effect sizes and confidence intervals in substantive units; never report p-values in isolation.
- **Label exploratory passes**: Clearly distinguish confirmatory tests from exploratory subgroup analyses.
- **Halt on ambiguities**: Clarify unstated covariates, model parameters, or missing-data strategies with the researcher.
