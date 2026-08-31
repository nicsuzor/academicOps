---
name: analyst
description: Run academic research data analysis reproducibly — research-data immutability, canonical absolute path resolution, canonical-vs-derived parity checks, a versioned and tested transformation layer kept strictly separate from a display-only presentation layer, defensible statistical methodology, and self-documenting research. Use for any computational research project with an empirical data pipeline — analysing a dataset, adding or changing a model/mart, producing a chart or dashboard, adding data-quality tests, investigating a data anomaly, or writing up results. Works one action at a time, checkpointing with the user. Engine-specific how-to lives in the `dbt`, `streamlit` and `python-viz` skills; not for general software engineering or non-research data work.
---

# Analyst

Technology-agnostic principles for reproducible research pipelines. When the
tooling is settled, pair this with the `dbt`, `streamlit`, or `python-viz`
skill for concrete commands.

**Take ONE action at a time** — generate a chart, add a model, write a test —
then show the result, say what it means, and yield to the user before
continuing. Never run a workflow end to end without checkpoints, and offer the
options rather than assuming the next step.

## Academic research floor

Non-negotiable for all academic work; the pipeline rules below extend it.

- **Research data is immutable.** Source datasets, ground-truth labels,
  `records/`, and research configs are sacred: never modify, reformat, or "fix"
  them. HALT and report rather than reshaping data to fit infrastructure —
  reshaping it is scholarly misconduct.
- **Research questions drive design.** Restate the question, confirm the method
  fits it, and refuse convenience shortcuts that compromise validity. A result
  that does not answer the question is worthless however technically sound.
- **Justify every methodological choice by the research design**, not by
  computational convenience. Keep all theoretically meaningful distinctions:
  do not drop variables, models, or conditions, or simplify an experimental
  design, without an explicit methodological reason.
- **Pilot before full-scale execution.** Audit representative samples of actual
  outputs for content substance, completeness across every condition,
  edge-case behaviour, and face validity. Error-free execution and healthy
  aggregate statistics are not a successful dry run.
- **Fail fast on data quality.** Stop and report quality problems rather than
  patching around them; the discovery IS the result.
- **State assumptions and limitations** a result rests on, and flag uncertainty
  rather than smoothing it over.
- **Report as argument.** Every chapter, section and figure supports a specific
  claim, and every metric is interpreted for its practical and theoretical
  implications. Refine the narrative section-by-section with the user.

## Canonical path resolution

Resolve every analytical database, cache, and data-store connection against an
absolute path rooted at the project root. A bare cwd-relative path
(`duckdb.connect("data/warehouse.db")`) is prohibited: an agent's working
directory shifts between the project root and subdirectories, so a relative
path silently connects to whichever confusable duplicate matches cwd, serves
stale data into published findings, or raises a false "table does not exist"
alarm.

1. **One canonical location** per database or cache, documented; delete
   confusable duplicates across subdirectories.
2. **Absolute resolution** from the project root via `Path(__file__).resolve()`
   or an explicit root locator.
3. **Pre-connection validation**: the file exists, its size and mtime are
   plausible, and the connection is read-only where applicable.

```python
from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent  # or project root locator
DB_PATH = (PROJECT_ROOT / "dbt" / "data" / "local_cache.duckdb").resolve()

if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"Canonical database not found at {DB_PATH}. Do not fall back to cwd-relative paths."
    )

conn = duckdb.connect(str(DB_PATH), read_only=True)
```

Keep local data (`data/`) out of any build output directory (`output/`,
`_book/`): build tools clean their output directories and will destroy it. Full
convention: [[instructions/research-documentation.md#data-directory-separation-critical]].

### When a query raises "table does not exist"

Do not conclude the database was clobbered. Work the ladder:

1. Confirm the query used the absolute canonical path, not a stale duplicate.
2. Inspect file size and mtime (`ls -lh <canonical_path>`); tiny or stale means
   wrong or unpopulated cache.
3. Scan for rogue duplicates (`find . -name "*.duckdb"`) and remove them.
4. Verify the model was actually built into the target database (e.g.
   `dbt run --select <model_name>`).

## Canonical-source vs derived-copy parity

Ground truth (per-record YAML in `records/`, benchmark configs, expert
annotations) is loaded into warehouse tables by sync scripts and out-of-band
loaders that bypass the transformation DAG, so a source edit without a re-run
leaves the derived copy quietly stale. Freshness checks (e.g. `dbt source
freshness`) validate timestamps, not content equality.

Before producing any figure, table, or conclusion from derived data:

1. **Assert count and key parity** between canonical source files and derived
   marts.
2. **Assert content equality** on ground-truth fields (e.g. mart
   `expected_violating` equals the label in `records/*.yaml`).
3. **HALT on any divergence** and report the synchronisation failure. Never
   analyse diverged data.

## Transformation layer vs presentation layer

All transformation happens in a versioned, tested, reproducible transformation
layer; the presentation layer only displays pre-computed data. This is a
property of the architecture, not of any tool — the transformation layer may be
a dbt project, a SQL pipeline, or version-controlled scripted notebooks; the
presentation layer may be a dashboard, static report, or notebook viewer. It
holds because anyone re-running the transformation layer must get identical
results, and reviewers must be able to read and test exactly how data was
processed.

| Layer              | Allowed                                                                                                                                                                       | Prohibited                                                                                                                                 |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Transformation** | All transformations, joins, aggregations, filtering, business logic                                                                                                           | —                                                                                                                                          |
| **Presentation**   | Reading pre-computed outputs; filtering on existing columns; formatting numbers and dates; interactive widgets over existing data; rendering charts from pre-computed metrics | Aggregation (`SUM(...) GROUP BY`), joins, `CASE WHEN` business logic, inline derived metrics, any formula that changes the meaning of data |

Tempted to transform in the presentation layer? Add the transformation as a
versioned model, add tests proving it works, build the transformation layer,
then read the pre-computed output. The extra scrutiny is the point.

## Data access

All data access goes through the modelled transformation layer — never a direct
query against a raw upstream source (raw BigQuery tables, raw schemas, live
APIs), because unmodelled reads are untested, unversioned, and unreproducible.

- Data exists in a mart → read it.
- Only in staging → use it for exploratory work, or promote it to a mart via
  the transformation-model workflow.
- Not modelled at all → ask the user whether to create a model. If not, stop;
  you cannot proceed without a modelled source.

## Transformation models

Layers: **staging (`stg_*`)** cleans and standardises raw data with no business
logic; **intermediate (`int_*`)** holds business logic and may be ephemeral;
**marts (`fct_*`, `dim_*`)** are materialised, analysis-ready datasets.

Check for a duplicate model before creating a new one. Engine-specific workflow
and file layout: the `dbt` skill.

## Testing

| Test type             | Use for                     | Example                                        |
| --------------------- | --------------------------- | ---------------------------------------------- |
| **Schema tests**      | Column-level checks         | not_null, unique, accepted_values              |
| **Singular tests**    | Multi-column logic          | Date range validation, cross-table consistency |
| **Parity tests**      | Canonical source sync check | Derived copy matches canonical source YAML/CSV |
| **Package tests**     | Common patterns             | Recency checks, multi-column uniqueness        |
| **Diagnostic models** | Quality monitoring          | Aggregated metrics for manual review           |

Work one step at a time, stopping between each: agree the test plan (which
columns must never be null, must be unique, carry accepted-value lists or
range logic, or need canonical-source parity) → add declarative schema tests
and parity assertions and show them → run them and report, discussing failures
before fixing → add singular tests for logic a column-level test cannot express.

Parity tests assert that mart ground-truth columns match canonical source
records verbatim and that every canonical source ID survives into the derived
dataset with zero dropped records. Run them before any statistical evaluation
or falsification suite.

When testing LLM pipelines or templated content, validate substantive content
rather than error strings, whose form is unpredictable: check content-length
minimums (e.g. a criteria block over 100 chars), verify required sections exist
_and_ carry content, and use position-based length for multiline content
(regex `.*?` does not cross newlines).

Engine-specific syntax (test declarations, severity levels, run commands): the
`dbt` skill.

## Investigation and exploration

Write data-quality investigations (missing values, unexpected patterns, join
coverage) as reusable scripts in `analyses/`, because the finding has to be
re-runnable by someone else and shell history is not.

For pattern and relationship exploration, take one analytical step at a time
and yield after each finding. Read
[[instructions/exploratory-analysis.md]] before starting an exploratory pass.

## Context discovery

Before any analysis task, read the project context: `README.md` in the working
directory and every parent up to the project root, `data/README.md`, and
`data/projects/[project-name].md`. Extract the research questions, data sources
and access patterns, existing models, conventions, testing strategy, and the
transformation/presentation engines in use. Read
[[references/context-discovery.md]] for the full procedure.

Summarise findings to the user — research topic and questions, model counts by
layer, existing work areas — then ask what to help with.

## Documentation

Do not create standalone analysis reports or ad-hoc documentation files. Read
[[instructions/research-documentation.md]] before creating any research
document: it is the complete requirement, including which files are mandatory
and which are forbidden. Per-file detail: [[instructions/methodology-files.md]],
[[instructions/methods-vs-methodology.md]],
[[instructions/experiment-logging.md]].

Analysis documentation lives in the dashboard, notebooks (in `experiments/` if
exploratory), GitHub issues, code comments in transformation models, commit
messages, transformation-layer schema docs, and `methods/*.md` specifications.
Update documentation in the same commit as the code it describes, and give each
fact exactly one home.

## Statistical methodology

Formulas, test-selection trees and APA reporting shapes are public knowledge.
What binds is methodology, and it is the researcher's call before it is yours.

- **The question picks the test, not the data.** Choosing a test after seeing
  which gives a significant result is p-hacking. Where the analysis plan was
  not fixed in advance, say so in the write-up.
- **State and check the assumptions the test rests on** — independence,
  distributional form, homogeneity of variance, whatever it requires — and
  report what you found, including a failed assumption you proceeded past and
  why.
- **Report effect sizes and intervals always**, interpreted in the units the
  research question is asked in. A p-value alone is not a result.
- **Label exploratory passes as exploratory in the write-up.** Multiple
  comparisons, subgroup hunts and post-hoc contrasts are corrected or flagged;
  they never migrate into the confirmatory frame.
- **HALT on a methodological choice nobody made** — which model, which
  covariates, which exclusions, how to handle missing data. Ask.

Library APIs: the `python-viz` skill.
