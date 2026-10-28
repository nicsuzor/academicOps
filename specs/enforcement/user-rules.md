---
id: spec-user-rules
title: User-Scoped Rules
type: spec
status: ready
tags: [enforcement, rules, rbg, cope, configuration]
---

# User-Scoped Rules

The user-scoped rule tier enables operators and developers to define cross-project behavioral constraints and policies that apply across workspaces without committing user-specific configurations to shared or public repository codebases.

## User stories

### US-1 Sourcing User Rules Across Workspaces

As an operator working across multiple projects and repositories, I want to define user-scoped rules in a dedicated local directory, so that my personal behavioral constraints and operational rules apply to review and evaluation without committing personal preferences to public or shared project repositories.

- **AC-1.1** Given `COPE_USER_RULES_DIR` is set to a valid directory containing Markdown files with `trigger: always_on`, when rule evaluation or loading occurs, then all valid user-scoped rules are loaded as layer 3.
- **AC-1.2** Given `COPE_USER_RULES_DIR` is unset, when rule evaluation or loading occurs, then the operation proceeds silently with zero user-scoped rules and emits no degradation warnings.
- **AC-1.3** Given `COPE_USER_RULES_DIR` is set to a non-existent or unreadable directory, when rule evaluation or loading occurs, then the loader emits a diagnostic warning to standard error indicating degraded rule evaluation and proceeds with baseline axiom and project rules.
- **AC-1.4** Given a user rule in `COPE_USER_RULES_DIR` shares a slug with a shipped axiom or a project-local rule, when rules are loaded, then the shipped axiom or project rule takes precedence and the user rule cannot override or shadow it.

### US-2 Consistent Documentation and Review Briefings

As a reviewer or agent evaluating artifacts, I want all agent definitions, review templates, and plugin documentation to name the exact same source for user-scoped rules, so that rule compliance reviews are deterministic and never search non-existent paths or undefinable database queries.

- **AC-2.1** Given any agent inspecting the rule hierarchy in agent definitions (`plugins/rbg/agents/rbg.md`), review templates (`plugins/ida/skills/workflow-library/workflows/wf-rbg.md`), or plugin documentation (`plugins/rbg/README.md`), when looking up the source of user-scoped rules, then every surface points to `$COPE_USER_RULES_DIR/*.md` and no surface references knowledge base queries or retired repository paths.
- **AC-2.2** Given an agent checking stop-gate instructions or evaluation prompts (`plugins/rbg/hooks/messages/rule-check.md`, `plugins/rbg/hooks/messages/ruleset.md`), when reviewing active rule scopes, then prompts state `$COPE_USER_RULES_DIR` (when set) and omit legacy paths.

## Design

### 1. Problem Statement & Root Cause Evidence

Across `release/v1.0-rc0` and `dev`, the source of the third (user-scoped) rule tier was documented inconsistently and rendered unreachable in practice:

1. **Three-Way Contradiction (Issue #3133):**
   - `plugins/rbg/agents/rbg.md` stated: `3. PKB contains user-scoped rules.`
   - `plugins/ida/skills/workflow-library/workflows/wf-rbg.md` stated: `Account-scoped rules: read from active PKB rules.`
   - `plugins/rbg/README.md` and `plugins/rbg/hooks/rules.py` stated: `$ACA_DATA/.agents/rules/*.md`.
   - The first two referred to an undefined knowledge-base query (no active rule query mechanism exists for synchronous hook execution). The third referred to a filesystem path.
2. **Unreachable Runtime Path (Issue #3134):**
   - The user-rules directory historically residing under `$ACA_DATA/.agents/rules/` was retired and deleted.
   - Worker container entrypoints unset `ACA_DATA` whenever external data volumes are unmounted, leaving the path completely absent.
   - The rule loader (`rules.py`) treated unset `ACA_DATA` as a silent absence, causing the layer to quietly vanish without indication.

### 2. Settled Architecture: Single SSoT via `$COPE_USER_RULES_DIR`

The single authoritative source for the user-scoped rule tier is the local filesystem directory designated by the environment variable `COPE_USER_RULES_DIR`.

- **Retirement of Legacy Paths:** `ACA_DATA` is completely removed as a configuration variable for rule loading.
- **Rejection of PKB Query Sourcing:** Rule evaluation runs in synchronous, low-latency hook subprocesses without access to asynchronous MCP tool infrastructure. Moreover, knowledge base notes are informational and hold no binding governance power over compliance reviews.
- **Format and Invariants:** User-scoped rules follow the identical standard as project-local rules: Markdown files (`*.md`) containing YAML frontmatter. Files declaring `trigger: always_on` are loaded into active policy memory. Files declaring `trigger: off` are deliberately parked and skipped without warning. Files lacking a known trigger marker are treated as non-policy reference material and flagged as skipped on standard error.
- **Precedence:** Rule merging maintains strict immutable hierarchy (`setdefault` semantics):
  1. Universal Axioms (`skills/axioms/`)
  2. Project Rules (`.agents/rules/`)
  3. User Rules (`$COPE_USER_RULES_DIR/`)
     An axiom always overrides a project or user rule; a project rule always overrides a user rule. Narrower scopes may add obligations but can never weaken or shadow an existing rule.

### 3. Enforcement Spec Alignment (One-Step Move)

Per `specs/enforcement/enforcement.md`, changes to behavior-shaping mechanisms default to the least-invasive option at the bottom of the enforcement pyramid.

- **Mechanism Level:** Configuration via environment variable (`COPE_USER_RULES_DIR`) paired with clear instruction text.
- **Proportionality:** Eliminates the fictional database queries and non-existent legacy paths in a single step without introducing custom daemons, complex query engines, or heavy hook machinery.
- **Failure Semantics:** Unset variable represents ordinary absence (silent no-op). A configured path that does not exist represents an operational fault and emits an explicit `DEGRADED: cope-rules` diagnostic to standard error, ensuring broken configurations are not silently swallowed.

### 4. Reachability & Deployment Matrix

The settled source is reachable across all three execution environments:

| Deployment Surface | Reachability & Configuration | Behavior When Unset / Unconfigured |
| - | - | - |
| **Interactive Host Session** | Configured by the user in shell configuration, `.envrc`, or `.env.local` pointing to a local directory (e.g., `~/.config/cope/rules/` or custom workspace directory). | When unset: silent no-op (0 user rules). When invalid path: emits `DEGRADED: cope-rules` to stderr. |
| **Polecat Container Worker** | The host polecat runner mounts the host-configured `rules_dir` read-only into `/etc/cope/rules`, and the container environment exports `ENV COPE_USER_RULES_DIR=/etc/cope/rules`. | If the host specifies no `rules_dir`, no mount occurs and `/etc/cope/rules` is absent, cleanly evaluating to 0 user rules. |
| **Continuous Integration (CI)** | `COPE_USER_RULES_DIR` remains unset in CI test harnesses. | Evaluates Tiers 1 and 2 deterministically with 0 user rules, ensuring reproducible CI runs. |

### 5. Surfaces and Required Modifications

The following 9 surfaces reference the user-scoped rule tier and require updating during implementation:

1. **`plugins/rbg/agents/rbg.md`**: Update line 15 from `3. PKB contains user-scoped rules.` to `3. $COPE_USER_RULES_DIR/*.md: User-scoped rules (optional; read when $COPE_USER_RULES_DIR is set).`
2. **`plugins/ida/skills/workflow-library/workflows/wf-rbg.md`**: Update line 29 from `- Account-scoped rules: read from active PKB rules.` to `- User-scoped rules: read from $COPE_USER_RULES_DIR/*.md (when set).`
3. **`plugins/rbg/README.md`**:
   - Replace line 26 (`$ACA_DATA/.agents/rules/*.md`) with `$COPE_USER_RULES_DIR/*.md`.
   - Update line 43 in the Configuration table, replacing `ACA_DATA` with `COPE_USER_RULES_DIR` (`Directory containing user-scoped rules (*.md)`).
4. **`plugins/rbg/hooks/rules.py`**:
   - Update docstrings referencing `ACA_DATA` to `COPE_USER_RULES_DIR`.
   - Update `_layers()` to read `os.environ.get("COPE_USER_RULES_DIR")` and construct `_Layer(3, Path(user_rules_dir), report_skips=True, absent_note="COPE_USER_RULES_DIR is set, so this layer was expected")`.
5. **`plugins/rbg/hooks/messages/rule-check.md`**: Update line 3 from `and user rules in $ACA_DATA/.agents/rules/.` to `and user rules in $COPE_USER_RULES_DIR (when set).`
6. **`plugins/rbg/hooks/messages/ruleset.md`**: Update line 3 from `and user rules ($ACA_DATA/.agents/rules/).` to `and user rules ($COPE_USER_RULES_DIR, when set).`
7. **`specs/ENFORCEMENT-MAP.md`**: Update line 12 from `user $ACA_DATA/.agents/rules/` to `user $COPE_USER_RULES_DIR`.
8. **`specs/polecat/polecat-system.md`**: Update lines 88-89 from `$ACA_DATA/.agents/rules/` (`/data/.agents/rules` -- `ENV ACA_DATA=/data`) to `$COPE_USER_RULES_DIR` (`/etc/cope/rules` -- `ENV COPE_USER_RULES_DIR=/etc/cope/rules`).
9. **`tests/test_shipped_hooks.py`**: Update line 884 from `monkeypatch.delenv("ACA_DATA", raising=False)` to `monkeypatch.delenv("COPE_USER_RULES_DIR", raising=False)`.

### 6. Build Acceptance Criteria

Implementation task `aops_bd7a0d1f` must satisfy the following outcome-level criteria:

- **AC-BUILD-1 (Valid User Rules Load):** Given `COPE_USER_RULES_DIR` points to an existing directory containing Markdown files with `trigger: always_on`, when `rules.load()` runs, then all such rules are returned with `layer=3`.
- **AC-BUILD-2 (Silent Absent Loader):** Given `COPE_USER_RULES_DIR` is unset, when `rules.load()` runs, then zero layer-3 rules are returned and stderr contains no degradation warnings.
- **AC-BUILD-3 (Degraded Diagnostics):** Given `COPE_USER_RULES_DIR` is set to a non-existent path, when `rules.load()` runs, then stderr contains `DEGRADED: cope-rules` and `rules.load()` returns loaded axioms and project rules without raising exceptions.
- **AC-BUILD-4 (Precedence Invariant):** Given a rule file in `COPE_USER_RULES_DIR` has the same slug as an axiom or a project-local rule, when `rules.load()` runs, then the axiom or project rule is returned and the user rule does not override it.
- **AC-BUILD-5 (Zero Legacy References):** A recursive search across `plugins/rbg/`, `specs/enforcement/`, `specs/ENFORCEMENT-MAP.md`, and `plugins/ida/skills/workflow-library/workflows/wf-rbg.md` returns zero occurrences of `ACA_DATA`.
- **AC-BUILD-6 (Test Suite Green):** `make test` and `make lint` pass completely.

## Open questions

None. The single source and deployment model are fully resolved.
