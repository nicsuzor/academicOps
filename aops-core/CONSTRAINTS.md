---
title: Framework Constraints
type: instructions
created: 2026-02-23
---

> **Curated by audit skill** - Regenerate with Skill(skill="audit")

# Framework Constraints

Hard rules for aops framework internals. Enforced by pre-commit hooks where possible, by agents otherwise.

## C1: Workflow file length

**Max 100 lines** for any workflow or procedure markdown file (`workflows/*.md`, `skills/*/procedures/*.md`).

Workflows that exceed this are too complex to follow reliably. Split into:

- A shorter orchestration workflow that delegates to sub-workflows
- Reference docs (in `references/`) for detail that doesn't need to be in the execution path

**Enforced by**: `check-workflow-length` pre-commit hook (`.pre-commit-config.yaml`).

**Current violations**: Most existing workflows exceed this. Treat as tech debt — enforce on new workflows, refactor existing ones opportunistically.

---

## C2: Framework integrity (SKILLS.md + WORKFLOWS.md + wikilinks)

Skills in `aops-core/skills/` MUST have entries in `SKILLS.md`. Workflows referenced in `WORKFLOWS.md` MUST exist on disk. Wikilinks in framework files MUST resolve.

**Enforced by**: `check-framework-integrity` pre-commit hook (`scripts/check_framework_integrity.py`), runs on changes to `WORKFLOWS.md`, `SKILLS.md`, workflow `.md` files, and `SKILL.md` files.

**CI only**: Full codebase wikilink scan (`--full`) runs in CI, not on local commits (too slow).

---

## C3: Non-interactive Execution (P#55)

Agents MUST NOT execute commands that require interactive terminal input.

- For `gh pr create`, always ensure the branch is pushed to origin first (`git push -u origin <branch>`), or use appropriate flags (`--fill`) to prevent interactive prompts about where to push.
- For `npm`, `uv`, `apt`, use `-y`, `--yes`, `--no-interaction`, or `--non-interactive` flags.

**Enforced by**: Agent behavior and system prompts. Interactive commands will hang the session and cause timeouts.

---

## C4: Agent permission envelopes

Each core agent in `aops-core/agents/` has a defined permission envelope: what it may **read**, **write**, and **shell out to**, plus which **subagents** and **skills** it may invoke. The envelope is declared in the agent's frontmatter (`tools:` allowlist) and reinforced in the agent body (role, deny-overrides, delegation rules).

This is the SSoT for per-agent authority. Extends the principles in `.agents/ENFORCEMENT-MAP.md` (which catalogues the _mechanisms_) into the specifics of _who_ is permitted _what_.

| Agent  | Role            | Read   | Write                                                      | Bash                                                                          | Subagents                 | Skills                                             | Hard denies                                                             |
| ------ | --------------- | ------ | ---------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------- |
| james  | Orchestrator    | `**/*` | _none_ (synthesises only)                                  | orchestration-only; delegates shell to subagents                              | rbg, pauli, marsha        | as needed                                          | filesystem writes; direct implementation                                |
| pauli  | PKB curator     | `**/*` | _none on disk_ (PKB writes go through MCP)                 | _none_                                                                        | _none_                    | remember, planner, strategic-review                | shell; filesystem writes                                                |
| rbg    | Judge / editor  | `**/*` | `**/*.md`, `**/*.py`, `**/*.yaml`, `**/*.yml`, `**/*.json` | _none_ (intentionally non-shelling — string-edit only)                        | _none_                    | _none_                                             | `**/.env*`, `**/secrets/**`; shell                                      |
| marsha | QA / verifier   | `**/*` | _none_ ("Modify code yourself — report only")              | `pytest`, `ruff`, `fs:read`, `net:http`, `pkg:install`, `git:read`, `gh:read` | rbg                       | qa                                                 | source writes; `git:write`; `gh:write`                                  |
| jr     | Router / butler | `**/*` | `.agents/CAPABILITIES.md`, `.agents/README.md` only        | `git:read`, `gh:read`, `fs:read`, narrow `fs:write`                           | james, rbg, marsha, pauli | aops, planner, qa, research, dump, daily, remember | `.agents/CORE.md`, `.agents/BUTLER.md`, `.agents/rules/**`; `git:write` |

**`.github/agents/*.agent.md`** (`merge-prep`, `pr-reviewer`, `qa`) are GitHub Actions runners. Their authority is governed by the workflow YAML's `permissions:` block and the runner's bot PAT scopes — **not** by this table. They are out of scope.

**Enforced by**: Agent body prose + frontmatter `tools:` allowlist (the harness consumes the allowlist directly). No standalone lint — drift is caught at review time by `rbg` against this table.

**When changing an agent's envelope**: update the row above in the same PR, and explain the rationale in the PR body. Adding shell scope, broadening write globs, or removing a deny-override is a permission change that warrants reviewer attention even when the diff to the agent file looks small.
