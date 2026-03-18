# aops-tools: Academic Domain Skills

This package provides **fungible** academic domain skills for the academicOps framework. These skills are optional and designed to be replaced when better external tools become available.

## What's here

- `analyst` — Research data analysis (dbt, Streamlit, statistics)
- `pdf` — PDF generation with academic typography
- `convert-to-md` — Batch document conversion (DOCX, PDF, XLSX → markdown)
- `excalidraw` — Hand-drawn diagram creation
- `flowchart` — Mermaid flowchart generation
- `extract` — General extraction and ingestion routing

## Design principle

These skills exist only because no better external solution exists yet. They are explicitly designed to be retired when the external landscape improves. Install `aops-core` for the non-fungible epistemic infrastructure.

## Installation

```bash
command claude plugin install aops-tools@aops
```
