# aops-tools: Academic Domain Skills

This package provides **fungible** academic domain skills for the academicOps framework. These skills are optional and designed to be replaced when better external tools become available.

## Path Discovery (CRITICAL)

To discover project locations, read `.agents/context-map.json` in the relevant repo. If the map is missing or any path it references does not exist, STOP and report.

## Fail-Fast / Halt Rule (ENFORCED)

If you cannot do what was asked, **STOP and report** — do NOT search broadly, do NOT invent workarounds.

- **Missing Paths**: If a documented path does not exist, STOP and report.
- **No Broad Grep**: Never grep `$HOME` or `/` to find source repos or documents. Use `.agents/INDEX.md` for discovery.
- **Tool Failures**: If a tool doesn't work as documented, report the failure — do not invent alternatives.
- **Ambiguity**: If instructions conflict or are ambiguous, ask for clarification.

## What's here

- `analyst` — Research data analysis (dbt, Streamlit, statistics)
- `pdf` — PDF generation with academic typography
- `extract` — General extraction and ingestion routing (includes document-to-markdown: DOCX, PDF, XLSX → markdown via `/extract` or `/convert-to-md`)
- `diagram` — Diagram creation (Mermaid or Excalidraw, via `style` parameter)

## Design principle

These skills exist only because no better external solution exists yet. They are explicitly designed to be retired when the external landscape improves. Install `aops-core` for the non-fungible epistemic infrastructure.

## Installation

```bash
command claude plugin install aops-tools@aops
```
