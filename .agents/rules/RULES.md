---
description: Project-specific process rules for the academicOps repository. Loaded by rbg (the Judge) alongside global axioms, and by the GHA QA agent for process compliance.
---

# Project Rules

These rules are **project-specific** — they apply to the `academicOps` repository in addition to (not in place of) the universal axioms in [[AXIOMS]]. Each rule targets a **class** of cases, not a single instance (Categorical-Imperative discipline, [[AXIOMS#categorical-imperative]]).

Identity scheme: each rule has a durable **slug** (`{#slug}` heading anchor). Cite by slug, never by ordinal. Rules may be added, merged, retired, or reordered without invalidating cross-references.

A rule lives here when it (a) governs how this repo's enforcement / authority / governance surfaces operate, AND (b) cannot be derived from the universal axioms alone — it states a project-level commitment whose violation is concrete enough that a reviewer can name the breach from the diff. Anything that is a universal claim belongs in [[AXIOMS]] instead.

## Enforcement-Map Currency — every mechanism change updates the map in the same PR {#enforcement-map-currency}

Any PR that **adds, modifies, escalates, or retires** an enforcement mechanism (a gate, hook, chokepoint, classifier rule, review agent, branch-protection check, or any other surface enumerated in [`specs/ENFORCEMENT-MAP.md`](../../specs/ENFORCEMENT-MAP.md)) MUST update `specs/ENFORCEMENT-MAP.md` in the **same change** — the row that names the mechanism, its trigger, and its workflow impact.

- The map is the routing table for "how is each rule currently enforced?" — a mechanism that ships without a row is an unmapped surface, and an unmapped surface degrades to silent state drift the next time someone reads the map and trusts it.
- This rule is **derivative of [[AXIOMS#single-source-of-truth]] applied to enforcement state**: the map is the single authoritative copy; a mechanism not listed there exists in two contradictory states (the source + the absent map row).
- The map's own header states the rule: _"Any PR that adds, escalates, or retires a mechanism updates a row here in the same change (P#65); `rbg` blocks on currency."_ This rule operationalises that header.
- "Same change" means same PR, not "follow-up PR". A follow-up has the same failure mode the rule is designed to prevent.
- _E.g._ PR #1824 (`feat(junior): replace PKB wildcard with explicit allowlist`) changed an agent's `tools:` list — a chokepoint/funnel (L4) enforcement-mechanism change per the Pyramid in `ENFORCEMENT-MAP.md`. It shipped without a row update. Under this rule, `rbg` returns `REVISE`: "missing enforcement-map row for chokepoint change to junior PKB scope".

_When applying:_ if the diff touches any agent persona's `tools:` frontmatter, any file under `aops-core/hooks/`, `.github/workflows/agent-*.yml`, `.github/agents/*.agent.md`, `.github/rulesets/`, `templates/*.plugin.json` `autoMode`, or `specs/enforcement/`, check whether `specs/ENFORCEMENT-MAP.md` was updated in the same diff. If not → `REVISE`.

## Agent Tool-Scope Changes Are Enforcement-Mechanism Changes {#agent-tool-scope}

Changes to an agent persona's `tools:` frontmatter list are **chokepoint/funnel (L4) enforcement-mechanism changes** per the Pyramid in `ENFORCEMENT-MAP.md` — they redistribute architecturally-unforgeable authority. They MUST update both `specs/ENFORCEMENT-MAP.md` and `specs/audit/AGENT-TOOLS.md` in the same PR.

- The agent × tool matrix in `specs/audit/AGENT-TOOLS.md` is the **authoritative state** for "which agent can call which tool". An agent file diverging from the matrix is the SSoT failure mode this rule prevents.
- "Tools" here means anything in the `tools:` frontmatter array, including wildcard expansions (`mcp__*__*` patterns) and explicit per-tool entries — narrowing, widening, replacing a wildcard with an allowlist, or restoring a removed tool all qualify.
- This rule is **a strict subset of [[#enforcement-map-currency]]**, restated separately because the failure mode is concrete and frequent enough to warrant a named rule: a `tools:` diff looks small and editorial, so the map update is easy to forget.
- _E.g._ replacing `mcp__plugin_aops-core_pkb__*` with 28 explicit allowed entries (PR #1824) is a chokepoint change — it pulls graph-shaping authority from junior and concentrates it on pauli. The new shape is the new enforcement surface; the diff must record it on the map AND in `AGENT-TOOLS.md`.

_When applying:_ if any file under `aops-core/agents/*.md`, `.github/agents/*.agent.md`, or any other agent-persona file has a `tools:` frontmatter change, check that BOTH `specs/ENFORCEMENT-MAP.md` AND `specs/audit/AGENT-TOOLS.md` were updated in the same diff (the matrix file's row for that agent, or its regenerator output, must reflect the new state). If either is missing → `REVISE`.

## Graph-Shaper Authority — Pauli is the sole graph-shaper {#graph-shaper-authority}

**Decomposition, epic creation, batch reparenting, batch reclassification, batch merging, node merging, and any other operation that **shapes** the PKB graph** routes to `@pauli` via `/planner`. Pauli is the **sole graph-shaper** — no other agent (including `junior`, who runs day-to-day lifecycle) may invoke the PKB graph-shaping verbs directly. Working agents create, update, and complete tasks; only Pauli decides shape (what is an epic, what reparents to what, what merges, which classification).

- Graph-shaping is a **judgment-non-delegable** call ([[AXIOMS#judgment-non-delegable]]) — taxonomy and structure are qualitative decisions that determine downstream search, prioritisation, and review semantics; a mechanical or convenience-driven shape introduces structural debt that compounds.
- Operationally, this is enforced as an L4 chokepoint: the PKB graph-shaping tools (`decompose_task`, `batch_create_epics`, `batch_reparent`, `batch_reclassify`, `batch_update`, `batch_archive`, `batch_merge`, `merge_node`, `delete`, `delete_memory`) appear **only** in pauli's `tools:` list. The least-privilege grant **is** the enforcement.
- A PR that grants any of these tools to an agent other than pauli is escalating L4 chokepoint scope — it must be justified, documented in the enforcement map, AND match the rule's stated authority distribution.
- _E.g._ PR #1824 enacted this rule by removing the wildcard from junior and explicitly retaining only lifecycle verbs. The PR did not (and should have) recorded the rule it enacted.

_When applying:_ if a diff grants any of the graph-shaping verbs above to an agent other than pauli, or removes them from pauli, return `REVISE` and require a `## Graph-shaper authority change` block in the PR body justifying the redistribution.
