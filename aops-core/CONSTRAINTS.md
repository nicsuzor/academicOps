---
title: Framework Constraints
type: instructions
created: 2026-02-23
---

# Framework Constraints

Hard rules for aops framework internals. Enforced by pre-commit hooks where possible, by agents otherwise.

| Check                    | Script                              | Rule(s)                | Tier       | Behaviour                                                    |
| ------------------------ | ----------------------------------- | ---------------------- | ---------- | ------------------------------------------------------------ |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `advisory` | Exits 0; reports files with no incoming wikilinks            |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `advisory` | Exits 1 when any SKILL.md exceeds 500 lines; lists offenders |

## Agent permission envelopes

Each core agent in `aops-core/agents/` has a defined permission envelope: what it may **read**, **write**, and **shell out to**, plus which **subagents** and **skills** it may invoke. The envelope is declared in the agent's frontmatter (`tools:` allowlist) and reinforced in the agent body (role, deny-overrides, delegation rules).

This is the SSoT for per-agent authority. Extends the principles in `.agents/ENFORCEMENT-MAP.md` (which catalogues the _mechanisms_) into the specifics of _who_ is permitted _what_.

| Agent  | Role            | Read   | Write                                                      | Bash                                                                          | Subagents                 | Skills                                             | Hard denies                                                             |
| ------ | --------------- | ------ | ---------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------- |
| james  | Orchestrator    | `**/*` | _none_ (synthesises only)                                  | orchestration-only; delegates shell to subagents                              | rbg, pauli, marsha        | as needed                                          | filesystem writes; direct implementation                                |
| pauli  | PKB curator     | `**/*` | _none on disk_ (PKB writes go through MCP)                 | _none_                                                                        | _none_                    | remember, planner, strategic-review                | shell; filesystem writes                                                |
| rbg    | Judge / editor  | `**/*` | `**/*.md`, `**/*.py`, `**/*.yaml`, `**/*.yml`, `**/*.json` | _none_ (intentionally non-shelling — string-edit only)                        | _none_                    | _none_                                             | `**/.env*`, `**/secrets/**`; shell                                      |
| marsha | QA / verifier   | `**/*` | _none_ ("Modify code yourself — report only")              | `pytest`, `ruff`, `fs:read`, `net:http`, `pkg:install`, `git:read`, `gh:read` | rbg                       | qa                                                 | source writes; `git:write`; `gh:write`                                  |
| jr     | Router / butler | `**/*` | `.agents/CAPABILITIES.md`, `.agents/README.md` only        | `git:read`, `gh:read`, `fs:read`, narrow `fs:write`                           | james, rbg, marsha, pauli | aops, planner, qa, research, dump, daily, remember | `.agents/CORE.md`, `.agents/BUTLER.md`, `.agents/rules/**`; `git:write` |

## GitHub actions

**`.github/agents/*.agent.md`** (`merge-prep`, `pr-reviewer`, `qa`) are GitHub Actions runners. Their authority is governed by the workflow YAML's `permissions:` block and the runner's bot PAT scopes:

TODO: finish this table.
