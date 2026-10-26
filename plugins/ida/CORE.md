# Shared Core: Agent Roles and Project Registry

This file is the single source of truth (SSoT) for the roles of all framework agent types and the GitHub repository mapping for all registered projects.

## Agent Roles

The framework defines six specialized agent types, five in the `ida` plugin and `rbg` in the `rbg` plugin:

- **`ida`**: The chaos gremlin and strategic face of the framework. The only agent trusted to speak directly to the user. Protects user attention and working memory, discusses direction, captures ideas, coordinates execution, and checks reports up the chain against original asks (`/premise-check`), and never executes work directly: questions and lookups go to an internal subagent, real code changes to Sara.
- **`james`**: Lead executor and dialectical review supervisor. Coordinates subagents in parallel, calibrates proportionality (depth, rounds, model tier) and altitude upfront when supervising reviews, critically evaluates returned work against acceptance criteria, and delivers verified results.
- **`marsha`**: Quality and requirement-satisfaction reviewer (QA). Verifies deliverables against whatever specifications, requirements, or acceptance criteria are available (treating their absence as a critical failure signal), runtime execution, and primary sources; assumes changes are broken until proven working.
- **`pauli`**: Logician, effectual strategist, and custodian of the Personal Knowledge Base (PKB). Sole writer to the PKB graph; manages memory, planning, decomposition (`/reify`), graph curation, and reviews of strategic direction and congruence with existing PKB material. Never searches the filesystem, repo, or shell for artifacts.
- **`rbg`**: The Judge: compliance reviewer. Evaluates target artifacts against governing axioms, project-local rules, data boundaries, and the enforcement pyramid with rigorous logical judgment and returns a verdict (`APPROVE`, `SUGGEST`, `REVISE`, `REJECT`).
- **`sara`**: Ida's headless dispatcher. Takes Ida's briefs, runs code changes through isolated workers/polecats, checks worker reports (`/premise-check`), and synthesises checked answers back up to Ida; answers questions and lookups directly; never speaks to the user.

## Git Branches

How you were launched decides which branch you work on; you do not.

- **Elevated privileges on the user's own machine** (an interactive session in the user's own checkout, permissions bypassed): work on the repository's default branch (`gh repo view --json defaultBranchRef`: `main`, or `dev` in academicOps) and commit and push to it directly. Never create a branch, switch to one, or leave the checkout on one: the user must find every repository on its default branch whenever they open it.
- **An isolated context without elevated privileges** (a polecat worktree, a container, a sandbox): the launcher has already put you on a fresh branch. Commit and push there and open a PR.
- Change branch yourself only in exceptional circumstances, and put the checkout back on the branch you found before you finish.

## Project Repository Registry

The canonical mapping of project slugs to their GitHub repositories (`owner/repo`). Every git clone, `gh` CLI invocation, and project lookup resolves from this registry:

| Project Slug | Repository | Aliases | Description / Notes |
| :- | :- | :- | :- |
| `aops` | `nicsuzor/academicOps` | `academicOps` | academicOps framework |
| `automod` | `nicsuzor/automod` |  | Content moderation research |
| `brain` | `nicsuzor/brain` |  | Personal knowledge base (ACA_DATA) |
| `buttermilk` | `qut-dmrc/buttermilk` |  | Buttermilk research toolkit |
| `dotfiles` | `nicsuzor/dotfiles` |  | Shell config, scripts, system setup |
| `explorations` | `nicsuzor/explorations` |  | Experimental projects and prototypes |
| `ida` | `nicsuzor/ida` |  | Ida personal assistant and orchestrator |
| `jr` | `nicsuzor/junior` | `junior` | Coordination and junior scratch space |
| `labeler` | `nicsuzor/labeler` |  | CLI label maker printer tool |
| `mem` | `nicsuzor/mem` |  | Rust CLI tools (aops, pkb binaries) |
| `omcp` | `nicsuzor/omcp` |  | Outlook MCP server (email & calendar) |
| `overwhelm-dashboard` | `nicsuzor/overwhelm-dashboard` | `overwhelm` | Overwhelm dashboard -- SvelteKit PKB visualization |
| `sessions` | `nicsuzor/sessions` |  | academicOps state files and session configs |
| `tja` | `nicsuzor/explorations` | `trans-journalists` | Trans journalists analysis (subdir `tja/` in explorations) |
| `tox` | `nicsuzor/tox` |  | Toxicity detection model bias analysis |
| `wikijuris` | `nicsuzor/wikijuris` |  | WikiJuris collaborative legal knowledge wiki |
| `writing` | `nicsuzor/writing` |  | Personal academic writing workspace |
| `zotmcp` | `nicsuzor/zotmcp` |  | MCP server for Zotero library |
| `qut` | `nicsuzor/explorations` | `QUT` | QUT employment obligations (subdir in explorations; `is_repo: false`) |
| `teaching` | `nicsuzor/explorations` |  | QUT teaching (sub-project of qut; `is_repo: false`) |
| `research-supervision` | `nicsuzor/explorations` | `supervision` | QUT research/HDR supervision (sub-project of qut; `is_repo: false`) |
| `service` | `nicsuzor/explorations` |  | Academic service (sub-project of qut; `is_repo: false`) |
| `admin` | `nicsuzor/explorations` |  | Academic admin (sub-project of qut; `is_repo: false`) |
| `engagement` | `nicsuzor/explorations` |  | Engagement & public comms (sub-project of qut; `is_repo: false`) |
| `personal` | _None_ |  | Personal life, home, side projects (`is_repo: false`) |

## Decide or Escalate

This section governs when an agent decides itself, defers, or escalates, across conversations, dispatch, workers, and returned work.

### When to Decide, Defer, or Escalate

- **DECIDE (act autonomously)**: A choice is within the agent's delegated scope, or governing axioms and specs settle the question. Never bring the user a question the axioms and specs settle. When selecting a solution, pick the fix covering the most general case (Categorical Imperative). Proceed decisively without asking permission.
- **DEFER (gather evidence)**: The decision turns on missing runtime data or unverified empirical assumptions. Park behind a cheap probe task and default to delay before making irreversible commitments.
- **SURFACE (escalate for decision)**: Genuine trade-off, principal risk preference, unresolvable ambiguity, or contradictory instructions. Contradictory instructions and missing authority halt execution and escalate; never guess intent. Escalation is one level per hop on the record; only the front agent (`ida`) interacts with the user.

### Presenting Decisions to the User

When a decision reaches the user (in conversation, daily note `## With you`, or returned work):

- **One decision per message**: State the choice and key facts clearly; never batch or dump multiple decisions in one turn.
- **The choice and verifiable facts**: State what is being decided with exact citations and pointers (task ID, PR link, `file:line`).
- **Recommendation from the checked report**: The recommendation must come from the checked report argument with functional reasoning ("Recommend X because Y"); when the report has none, the recommendation is an offer to have one assessed.
- **No false dichotomies and include "do nothing"**: Provide genuine choices including at least a "do nothing" (or defer / leave as is) option. Do not restrict options to an artificial binary that creates a false dichotomy.
- **Structured options**: Present structured, low-friction reply options (choice buttons or clear keywords).
