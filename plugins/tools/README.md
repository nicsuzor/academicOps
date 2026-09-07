# tools

Domain research skills for academicOps: data analysis, document conversion, diagramming, peer review, and project scaffolding. Skills operate independently; agents select individual skills by frontmatter description.

## Skills

| Skill           | Description                                                                   |
| --------------- | ----------------------------------------------------------------------------- |
| `analyst`       | Principles for reproducible empirical research pipelines.                     |
| `dbt`           | SQL transformation layer implementation for `analyst`.                        |
| `streamlit`     | Display-only dashboard presentation layer for `analyst`.                      |
| `python-viz`    | Python visualization and statistics (`matplotlib`, `seaborn`, `statsmodels`). |
| `pdf`           | Typeset PDF generation via `generate_pdf.py`.                                 |
| `extract`       | Document, email, and review extraction workflows.                             |
| `diagram`       | Mermaid and Excalidraw diagram authoring and sync.                            |
| `peer-review`   | Academic peer review for manuscripts and grant proposals.                     |
| `deep-research` | Deep research prompt generation and PKB integration.                          |
| `style`         | Writing style guide generation from sample texts.                             |
| `new-project`   | End-to-end research project repository scaffolding.                           |

## Environment variables and secrets

| Variable / Secret         | Source      | Purpose                                                         |
| ------------------------- | ----------- | --------------------------------------------------------------- |
| `ACA_DATA`                | Environment | Root for personal research data, signatures, and review rounds. |
| `AOPS`                    | Environment | Root of the academicOps repository.                             |
| `AOPS_SRC_DIR`            | Environment | Parent directory for checked-out project repositories.          |
| `AOPS_SESSIONS`           | Environment | Sessions repo containing `polecat.yaml` and scoped secrets.     |
| `POLECAT_HOME`            | Environment | Host-local polecat configuration overrides (`local.yaml`).      |
| `AOPS_BOT_GH_TOKEN`       | Repo secret | GitHub token for automated bot pushes.                          |
| `CLAUDE_CODE_OAUTH_TOKEN` | Repo secret | OAuth token for `@claude` GitHub Actions workflows.             |

## External dependencies

- `uv`: Python execution for `pdf`, `extract`, and `deep-research`.
- `pandoc`, `weasyprint`, `pdftotext`: Document rendering and conversion.
- `gh`: Repository, secret, and issue label management.
- `rclone`, `unzip`: Fetching and extracting research artifacts.
- PKB MCP server: Knowledge base graph search and persistence.
