# Enforcement Map

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, and its failure tier. Updated whenever a new check is added
or retired (P#65).

## Runtime hooks (in-session)

Mechanisms that fire during a live Claude Code / Gemini session. Routed through
`aops-core/hooks/router.py`. Tier semantics: `hint` = injected reminder,
`warn` = non-blocking warning surfaced via PostToolUse, `block` = hard gate
that prevents the tool call.

| Mechanism             | Hook event       | Source                                                  | Rule(s)                                           | Scope                                 | Tier    | Behaviour                                                                |
| --------------------- | ---------------- | ------------------------------------------------------- | ------------------------------------------------- | ------------------------------------- | ------- | ------------------------------------------------------------------------ |
| `hydration` gates     | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: hydration discipline)                         | All sessions                          | `warn`  | Blocks tool calls until hydrator runs (mode-dependent)                   |
| `enforcer` gate       | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | A1, A6, A8 (axiom compliance, scope, halt)        | All sessions                          | `warn`  | Periodic compliance checks via the enforcer subagent                     |
| `qa` gate             | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: QA before completion)                         | All sessions                          | `warn`  | Requires QA verification before session can stop                         |
| `handover` gate       | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: handover discipline)                          | All sessions                          | `warn`  | Blocks Stop until commit + task update + framework reflection complete   |
| `ida` gate            | Stop             | `aops-core/lib/gates/definitions.py`                    | A3, A4, A11 (proof, citation, observability)      | All sessions                          | `warn`  | Non-blocking reminder to back assertions with proof and disclose skips   |
| `custodiet` gate      | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: workflow discipline — premature termination)  | All sessions                          | `warn`  | Detects scope explosion / plan-less execution                            |
| `policy_enforcer`     | PreToolUse       | `aops-core/hooks/policy_enforcer.py`                    | (R: destructive-command guards, credential protection, doc-size limit, H#94 artifact protection) | All sessions | `block` | Hard-blocks: destructive git commands, Bash reads of credential paths (GH #408), `*-GUIDE.md` or oversized `.md` writes, writes to project-protected paths |
| `aca_data_autocommit` | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`  | (procedural: keep PKB synced)                     | When `$ACA_DATA` set                  | n/a     | Auto-commits `$ACA_DATA` after state-modifying tool calls                |
| `context-map hints`   | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints` | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json` | `hint`  | Injects relevant doc pointers from the repo's context map                |

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier   | Behaviour                                                                                                                                               |
| --------------------------- | -------------------------------------- | -------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn` | Exits 1 on new `.md` files outside canonical-location allowlist                                                                                         |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn` | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries                                                                                   |
| `check-no-fallbacks`        | `scripts/check_no_fallbacks.py`        | A8 / P#8                   | `warn` | Exits 1 on silent-fallback patterns in `aops-core/hooks/*.py`, `aops-core/agent-env-map.conf`, `scripts/repo-sync-cron.sh` (see issue #930 for context) |

## CORE.md directives (always-on)

Static guidance embedded in `.agents/CORE.md` and loaded into every agent session context for this repo. Unlike hooks, these are not event-triggered — they are part of the agent's context window whenever it works in academicOps.

| Directive   | Source                                                    | Rule(s)                           | Scope            | Tier   | Behaviour                                               |
| ----------- | --------------------------------------------------------- | --------------------------------- | ---------------- | ------ | ------------------------------------------------------- |
| `pkb-first` | `.agents/CORE.md` — "Where to find documentation" section | (procedural: PKB-first discovery) | academicOps repo | `hint` | Instructs agents to use PKB before reading source code. |
