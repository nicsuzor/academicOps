---
title: User-Scoped Rules
status: ready
---

# User-Scoped Rules

The user-scoped rule tier enables operators and developers to define cross-project behavioral constraints and policies that apply across workspaces without committing user-specific configurations to shared or public repository codebases.

## User stories

### US-1 Sourcing Runtime Tool-Call Evaluator Rules

As a developer running automated tool-call evaluation during an interactive session, I want user-scoped rules loaded from a dedicated local directory, so that personal operational constraints apply to automated tool checks without committing personal policies to repository code.

- **AC-1.1** Given `COPE_USER_RULES_DIR` is set to a valid directory containing Markdown files with `trigger: always_on`, when rule loading occurs, then all valid user-scoped rules are loaded as layer 3.
- **AC-1.2** Given `COPE_USER_RULES_DIR` is unset, when rule loading occurs, then rule loading proceeds silently with zero layer-3 rules and emits no degradation warnings.
- **AC-1.3** Given `COPE_USER_RULES_DIR` is set to a non-existent or unreadable directory, when rule loading occurs, then the loader emits a diagnostic warning to standard error indicating degraded rule evaluation and proceeds with baseline axiom and project rules.
- **AC-1.4** Given a user rule in `COPE_USER_RULES_DIR` shares a slug with a shipped axiom or a project-local rule, when rules are loaded, then the shipped axiom or project rule takes precedence and the user rule cannot override or shadow it.

### US-2 Sourcing Qualitative Compliance Review Rules

As a compliance reviewer evaluating artifacts across host, container, or remote sandbox environments, I want user-scoped rules sourced from the knowledge base by document type, so that personal governance constraints are reachable and evaluable everywhere the reviewer runs.

- **AC-2.1** Given an active knowledge base containing documents with `type: rule`, when compliance review gathers active rules, then all such documents are evaluated as user-scoped rules.
- **AC-2.2** Given a knowledge base with no documents matching `type: rule`, when compliance review gathers active rules, then review proceeds with universal axioms and project rules without error.
- **AC-2.3** Given a knowledge base document with `type: rule` sharing a slug or title with an axiom or project-local rule, when compliance review evaluates rules, then the axiom or project-local rule takes precedence and the user rule cannot override or weaken it.
- **AC-2.4** Given a compliance reviewer evaluating rule sources, when identifying user-scoped rules, then the reviewer queries the knowledge base for documents with `type: rule` and evaluates any matches as user-scoped rules.

## Design

### 1. Dual Operational Subsystems

User-scoped rules operate across two distinct enforcement subsystems with separate reachability boundaries and execution models:

1. **In-Session Runtime Evaluator (COPE):** Automated turn-by-turn tool-call classification. The evaluator runs in low-latency hook subprocesses without asynchronous tool execution capabilities. It sources user-scoped rules from local Markdown files (`*.md`) located in the directory specified by `COPE_USER_RULES_DIR`.
2. **Qualitative Compliance Reviewer (RBG):** Deliberative compliance review of specifications, code, and pull requests. RBG operates in sandboxed execution environments, worker containers, and headless agent sessions where arbitrary host filesystem paths are unmounted and unreachable. RBG reads only plugin distribution assets (`skills/axioms/`), the current repository (`.agents/rules/`), and the knowledge base. Consequently, RBG sources user-scoped rules from the knowledge base via its `type: rule` document attribute.

### 2. Knowledge Base Sourcing Contract for Compliance Review

Knowledge base notes and general documents carry no binding governance authority. To establish an unambiguous single source of truth for user-scoped compliance review rules:

- **Explicit Type Attribute:** User-scoped rules in the knowledge base are identified by the frontmatter attribute `type: rule`.
- **Query Discovery:** Reviewing agents retrieve active user-scoped rules by listing or searching documents with `type: rule`.
- **Content Structure:** A rule document contains descriptive Markdown defining the normative policy obligation.

### 3. Filesystem Sourcing Contract for Runtime Evaluation

For the runtime hook evaluator:

- **Directory Configuration:** Specified by environment variable `COPE_USER_RULES_DIR`.
- **File Format:** Markdown files (`*.md`) with YAML frontmatter. Only files declaring `trigger: always_on` are loaded into active policy memory. Files declaring `trigger: off` are deliberately parked and skipped without warning. Files lacking a recognised trigger marker are treated as non-policy reference material and flagged as skipped on standard error.
- **Failure Semantics:** Unset environment variable is an ordinary absence (silent no-op). A configured path that cannot be read is an operational fault that emits `DEGRADED: cope-rules` on standard error and proceeds with axioms and project rules.

### 4. Rule Precedence and Invariants

Across both subsystems, rule merging enforces strict immutable precedence (`setdefault` semantics):

1. Universal Axioms (Tier 1, inviolable baseline)
2. Project-Local Rules (Tier 2)
3. User-Scoped Rules (Tier 3)

An axiom always overrides a project or user rule; a project rule always overrides a user rule. Narrower scopes add obligations without weakening or shadowing baseline rules.

### 5. Reachability & Deployment Matrix

| Deployment Surface | Runtime Evaluator (COPE) | Compliance Reviewer (RBG) |
| - | - | - |
| **Interactive Host Session** | Reads `COPE_USER_RULES_DIR/*.md`. Silent no-op when unset. | Queries knowledge base documents with `type: rule`. |
| **Polecat Container Worker** | Reads container mount `/etc/cope/rules` (`ENV COPE_USER_RULES_DIR=/etc/cope/rules`). | Queries knowledge base documents with `type: rule`. |
| **Continuous Integration (CI)** | Deterministic run with `COPE_USER_RULES_DIR` unset (0 user rules). | Evaluates universal axioms and project rules (0 user rules when no PKB configured). |

## Open questions

None. Sourcing contracts across both operational subsystems are fully resolved.
