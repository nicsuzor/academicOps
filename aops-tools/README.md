# aops-tools: Academic Domain Skills

`aops-tools` provides **fungible** academic domain skills for the academicOps framework. These skills are optional, specialized tools for data analysis, diagramming, document ingestion, and PDF rendering designed to be swappable when external tooling improves.

## Control Flow & Architecture

```mermaid
flowchart TD
    subgraph Triggers ["Skill Invocations"]
        T1["/diagram (Mermaid / Excalidraw)"]
        T2["/pdf (Typography & Formatting)"]
        T3["/extract (DOCX, PDF, XLSX -> MD)"]
        T4["/analyst, /dbt, /python-viz, /streamlit"]
        T5["/project (Project Scaffolding)"]
        T6["/deep-research (Research Prompts)"]
    end

    subgraph Processing ["Skill Execution"]
        P1["Render SVG/PNG via Mermaid CLI or Excalidraw"]
        P2["Compile Markdown via Typst / Pandoc / Weasyprint"]
        P3["Route document to pandoc/markitdown converter"]
        P4["Execute data pipeline transformations & charts"]
        P5["Create project directory structure & defaults"]
        P6["Prompt authoring & PKB research ingestion"]
    end

    subgraph Emits ["Deliverables & Artifacts"]
        E1["Diagram Figures (SVG/PNG)"]
        E2["Academic PDFs"]
        E3["Markdown Document Output"]
        E4["dbt Models, Plots, Dashboards"]
        E5["Project Repositories"]
        E6["Ingested Research Documents"]
    end

    T1 --> P1 --> E1
    T2 --> P2 --> E2
    T3 --> P3 --> E3
    T4 --> P4 --> E4
    T5 --> P5 --> E5
    T6 --> P6 --> E6
```

## Customisation Surface

### Plugin Configuration (`userConfig`)

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `default_diagram_style` | `string` | `"mermaid"` | Default rendering style for the `/diagram` skill (`mermaid` or `excalidraw`). |
| `pdf_engine` | `string` | `"typst"` | Preferred PDF rendering backend for the `/pdf` skill (`typst`, `pandoc`, `weasyprint`). |
| `src_dir` | `string` | Auto-resolved | Search root for project repository discovery (`AOPS_SRC_DIR`). |

### Environment Variables

| Variable | Required | Description | Default |
| :--- | :--- | :--- | :--- |
| `ACA_DATA` | Optional | Path to personal knowledge base data root. | None |
| `AOPS_SRC_DIR` | Optional | Root path for project discovery. | `~/src` |

## Discovery & Path Discipline

- **Path Discovery**: To discover project locations, read `.agents/INDEX.md` in the relevant repo.
- **Fail-Fast Rule**: If documented paths or tools are missing, **STOP and report** — do not invent broad search workarounds.

## Installation

### Claude Code

```bash
claude plugin install aops-tools@academicOps
```

### Antigravity (`agy`)

```bash
agy plugin install ./dist/aops-tools-antigravity
```

## Contents

- `analyst` — Research data analysis (dbt, Streamlit, statistics).
- `dbt` — Data build tool transformation models.
- `deep-research` — Author deep-research prompts & ingest results into PKB.
- `diagram` — Diagram creation (Mermaid or Excalidraw via `style` parameter).
- `extract` — General extraction and ingestion routing (DOCX, PDF, XLSX → markdown).
- `new-project` — Scaffold research project repo structure.
- `pdf` — PDF generation with academic typography.
- `peer-review` — Peer review of grant applications & submissions.
- `python-viz` — Publication-quality figures (Matplotlib, Seaborn, Statsmodels).
- `streamlit` — Streamlit presentation dashboard design.
- `style` — Analyze writing samples and build style guides.
