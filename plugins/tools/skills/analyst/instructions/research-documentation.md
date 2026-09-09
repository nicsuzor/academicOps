---
title: Research Project Documentation Structure
type: note
category: instruction
permalink: analyst-chunk-research-documentation
description: Required documentation hierarchy, prohibited ad-hoc files, and data/build separation.
---

# Research Project Documentation Structure

Maintain a fixed documentation layout so project context, methods, and evidence remain discoverable and versioned without ad-hoc document sprawl.

## Directory hierarchy

```
project_root/
├── README.md               # Overview, research questions, quick start
├── METHODOLOGY.md          # Research design (see instructions/methodology-files.md)
├── methods/                # Technical implementation specs (instructions/methods-vs-methodology.md)
│   └── <method_name>.md
├── experiments/            # Exploratory analysis (instructions/experiment-logging.md)
│   └── YYYYMMDD-<description>/
├── data/                   # Local cache (gitignored, re-extractable)
│   └── README.md           # Provenance, schemas, refresh procedures, known caveats
├── <transformation_layer>/ # Versioned models (e.g., dbt/models/, schema.yml)
├── <presentation_layer>/   # Dashboards, reports (e.g., streamlit/dashboard.py)
└── output/ or _book/       # Build artifacts only (gitignored, expendable)
```

Do not generate ad-hoc analysis reports, weekly summary markdowns, or temporary notes files. Place all durable context into the designated structures above or in code comments and commits.

## Data directory separation (critical)

Never place data inside build output directories (`output/`, `_book/`, `_site/`, `dist/`). Build systems routinely purge output directories during rendering and will delete contained data.

- Keep raw and cached data strictly within `data/` or tracked via DVC.
- Configure output directories explicitly in tool settings (`_quarto.yml`, `dbt_project.yml`).

## Currency standard

Documentation reflects the actual current codebase. Never leave `TODO` or `TK` placeholders in committed research documentation. When code diverges from documentation, update documentation in the same commit.
