# Enforcement Map

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, and its failure tier. Updated whenever a new check is added
or retired (P#65).

## Runtime hooks (in-session)

Mechanisms that fire during a live Claude Code / Gemini session. Routed through
`aops-core/hooks/router.py`. Tier semantics: `hint` = injected reminder,
`warn` = non-blocking warning surfaced via PostToolUse, `block` = hard gate
that prevents the tool call.

**Bypass:** When `AOPS_HOOKS_OFF=1` is set in the environment, `aops-core/hooks/router.sh`
exits 0 before the Python bootstrap, making all mechanisms below into no-ops for that session.
Set by `polecat` when launching crew containers in vanilla-crew trial mode
(`POLECAT_VANILLA_CREW=1`). Applies to interactive `crew` sessions only;
autonomous `polecat run` workers always run with `AOPS_HOOKS_OFF` unset.

| Mechanism             | Hook event       | Source                                                  | Rule(s)                                           | Scope                                                     | Tier    | Behaviour                                                                |
| --------------------- | ---------------- | ------------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------- | ------- | ------------------------------------------------------------------------ |
| `hydration` gates     | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: hydration discipline)                         | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `warn`  | Blocks tool calls until hydrator runs (mode-dependent)                   |
| `enforcer` gate       | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | A1, A6, A8 (axiom compliance, scope, halt)        | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `warn`  | Periodic compliance checks via the enforcer subagent                     |
| `qa` gate             | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: QA before completion)                         | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `warn`  | Requires QA verification before session can stop                         |
| `handover` gate       | Stop             | `aops-core/lib/gates/definitions.py`                    | (R: handover discipline)                          | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `warn`  | Blocks Stop until commit + task update + framework reflection complete   |
| `custodiet` gate      | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: workflow discipline — premature termination)  | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `warn`  | Detects scope explosion / plan-less execution                            |
| `policy_enforcer`     | PreToolUse       | `aops-core/hooks/policy_enforcer.py`                    | (R: destructive-command guards)                   | All sessions (bypassed when `AOPS_HOOKS_OFF=1`)           | `block` | Hard-blocks dangerous Bash patterns (force-push to main, `rm -rf`, etc.) |
| `aca_data_autocommit` | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`  | (procedural: keep PKB synced)                     | When `$ACA_DATA` set (bypassed when `AOPS_HOOKS_OFF=1`)   | n/a     | Auto-commits `$ACA_DATA` after state-modifying tool calls                |
| `context-map hints`   | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints` | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json` (bypassed when `AOPS_HOOKS_OFF=1`) | `hint`  | Injects relevant doc pointers from the repo's context map                |

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier   | Behaviour                                                             |
| --------------------------- | -------------------------------------- | -------------------------- | ------ | --------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn` | Exits 1 on new `.md` files outside canonical-location allowlist       |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn` | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries |

## CORE.md directives (always-on)

Static guidance embedded in `.agents/CORE.md` and loaded into every agent session context for this repo. Unlike hooks, these are not event-triggered — they are part of the agent's context window whenever it works in academicOps.

| Directive   | Source                                                    | Rule(s)                           | Scope            | Tier   | Behaviour                                               |
| ----------- | --------------------------------------------------------- | --------------------------------- | ---------------- | ------ | ------------------------------------------------------- |
| `pkb-first` | `.agents/CORE.md` — "Where to find documentation" section | (procedural: PKB-first discovery) | academicOps repo | `hint` | Instructs agents to use PKB before reading source code. |
