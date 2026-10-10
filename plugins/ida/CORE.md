# Shared Core: Agent Roles and Project Registry

This file is the single source of truth (SSoT) for the roles of all framework agent types and the GitHub repository mapping for all registered projects.

## Agent Roles

The framework defines six specialized agent types in the `ida` plugin:

- **`ida`**: The chaos gremlin and strategic face of the framework. The only agent trusted to speak directly to the user. Protects user attention and working memory, discusses direction, captures ideas, coordinates execution, checks reports up the chain against original asks (`/premise-check`), and never executes work directly.
- **`james`**: Lead executor for units of work. Coordinates subagents in parallel, critically evaluates returned work against acceptance criteria, validates deliverables against literal requirements, and delivers verified results.
- **`marsha`**: Substantive quality reviewer (QA). Verifies deliverables against literal user requests, runtime execution, and primary sources; assumes changes are broken until proven working.
- **`pauli`**: Logician, effectual strategist, and custodian of the Personal Knowledge Base (PKB). Sole writer to the PKB graph; manages memory, planning, decomposition (`/reify`), and graph curation. Never searches the filesystem, repo, or shell for artifacts.
- **`rbg`**: The Judge: rule-compliance reviewer. Evaluates target artifacts against governing axioms and project rules with rigorous logical judgment and returns a verdict (`APPROVE`, `SUGGEST`, `REVISE`, `REJECT`).
- **`sara`**: Ida's headless dispatcher. Takes Ida's briefs, runs work through isolated workers/polecats, checks worker reports (`/premise-check`), and synthesises checked answers back up to Ida; never speaks to the user.

## Project Repository Registry

The canonical mapping of project slugs to their GitHub repositories (`owner/repo`). Every git clone, `gh` CLI invocation, and project lookup resolves from this registry:

| Project Slug           | Repository                     | Aliases             | Description / Notes                                                   |
| :--------------------- | :----------------------------- | :------------------ | :-------------------------------------------------------------------- |
| `aops`                 | `nicsuzor/academicOps`         | `academicOps`       | academicOps framework                                                 |
| `automod`              | `nicsuzor/automod`             |                     | Content moderation research                                           |
| `brain`                | `nicsuzor/brain`               |                     | Personal knowledge base (ACA_DATA)                                    |
| `buttermilk`           | `qut-dmrc/buttermilk`          |                     | Buttermilk research toolkit                                           |
| `dotfiles`             | `nicsuzor/dotfiles`            |                     | Shell config, scripts, system setup                                   |
| `explorations`         | `nicsuzor/explorations`        |                     | Experimental projects and prototypes                                  |
| `ida`                  | `nicsuzor/ida`                 |                     | Ida personal assistant and orchestrator                               |
| `jr`                   | `nicsuzor/junior`              | `junior`            | Coordination and junior scratch space                                 |
| `labeler`              | `nicsuzor/labeler`             |                     | CLI label maker printer tool                                          |
| `mem`                  | `nicsuzor/mem`                 |                     | Rust CLI tools (aops, pkb binaries)                                   |
| `omcp`                 | `nicsuzor/omcp`                |                     | Outlook MCP server (email & calendar)                                 |
| `overwhelm-dashboard`  | `nicsuzor/overwhelm-dashboard` | `overwhelm`         | Overwhelm dashboard -- SvelteKit PKB visualization                    |
| `sessions`             | `nicsuzor/sessions`            |                     | academicOps state files and session configs                           |
| `tja`                  | `nicsuzor/explorations`        | `trans-journalists` | Trans journalists analysis (subdir `tja/` in explorations)            |
| `tox`                  | `nicsuzor/tox`                 |                     | Toxicity detection model bias analysis                                |
| `wikijuris`            | `nicsuzor/wikijuris`           |                     | WikiJuris collaborative legal knowledge wiki                          |
| `writing`              | `nicsuzor/writing`             |                     | Personal academic writing workspace                                   |
| `zotmcp`               | `nicsuzor/zotmcp`              |                     | MCP server for Zotero library                                         |
| `qut`                  | `nicsuzor/explorations`        | `QUT`               | QUT employment obligations (subdir in explorations; `is_repo: false`) |
| `teaching`             | `nicsuzor/explorations`        |                     | QUT teaching (sub-project of qut; `is_repo: false`)                   |
| `research-supervision` | `nicsuzor/explorations`        | `supervision`       | QUT research/HDR supervision (sub-project of qut; `is_repo: false`)   |
| `service`              | `nicsuzor/explorations`        |                     | Academic service (sub-project of qut; `is_repo: false`)               |
| `admin`                | `nicsuzor/explorations`        |                     | Academic admin (sub-project of qut; `is_repo: false`)                 |
| `engagement`           | `nicsuzor/explorations`        |                     | Engagement & public comms (sub-project of qut; `is_repo: false`)      |
| `personal`             | _None_                         |                     | Personal life, home, side projects (`is_repo: false`)                 |
