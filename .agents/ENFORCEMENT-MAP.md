# Enforcement Map

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, and its failure tier. Updated whenever a new check is added
or retired (P#65).

## Runtime hooks (in-session)

Mechanisms that fire during a live Claude Code / Gemini session. Routed through
`aops-core/hooks/router.py`. Tier semantics: `hint` = injected reminder,
`warn` = non-blocking warning surfaced via PostToolUse, `block` = hard gate
that prevents the tool call.

| Mechanism               | Hook event       | Source                                                                                                       | Rule(s)                                           | Scope                                 | Tier    | Behaviour                                                                                                                                                                |
| ----------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- | ------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `dispositor-reminder`   | UserPromptSubmit | `aops-core/lib/orchestrator_boundary.py` + `aops-core/hooks/templates/orchestrator-dispositor-reminder.md`   | P#122 (Orchestrator Is a Dispositor)              | Brain repo only (`cwd ⊆ ACA_DATA`)    | `hint`  | Injects "dispatch, don't execute" reminder on work-request prompts. Suppressed in polecat workers and outside `$ACA_DATA` (project source repos: academicOps, mem, etc.) |
| `orchestrator_boundary` | PostToolUse      | `aops-core/lib/gates/definitions.py` (`orchestrator_boundary` gate) + `is_orchestrator_project_write` custom | P#122                                             | Brain repo only (`cwd ⊆ ACA_DATA`)    | `warn`  | Warns when an orchestrator session writes to non-framework project source files. Same scope as `dispositor-reminder`                                                     |
| `hydration` gates       | PreToolUse       | `aops-core/lib/gates/definitions.py`                                                                         | (R: hydration discipline)                         | All sessions                          | `warn`  | Blocks tool calls until hydrator runs (mode-dependent)                                                                                                                   |
| `enforcer` gate         | PreToolUse       | `aops-core/lib/gates/definitions.py`                                                                         | A1, A6, A8 (axiom compliance, scope, halt)        | All sessions                          | `warn`  | Periodic compliance checks via the enforcer subagent                                                                                                                     |
| `qa` gate               | Stop             | `aops-core/lib/gates/definitions.py`                                                                         | (R: QA before completion)                         | All sessions                          | `warn`  | Requires QA verification before session can stop                                                                                                                         |
| `handover` gate         | Stop             | `aops-core/lib/gates/definitions.py`                                                                         | (R: handover discipline)                          | All sessions                          | `warn`  | Blocks Stop until commit + task update + framework reflection complete                                                                                                   |
| `custodiet` gate        | PreToolUse       | `aops-core/lib/gates/definitions.py`                                                                         | (R: workflow discipline — premature termination)  | All sessions                          | `warn`  | Detects scope explosion / plan-less execution                                                                                                                            |
| `policy_enforcer`       | PreToolUse       | `aops-core/hooks/policy_enforcer.py`                                                                         | (R: destructive-command guards)                   | All sessions                          | `block` | Hard-blocks dangerous Bash patterns (force-push to main, `rm -rf`, etc.)                                                                                                 |
| `aca_data_autocommit`   | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`                                                       | (procedural: keep PKB synced)                     | When `$ACA_DATA` set                  | n/a     | Auto-commits `$ACA_DATA` after state-modifying tool calls                                                                                                                |
| `context-map hints`     | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints`                                                      | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json` | `hint`  | Injects relevant doc pointers from the repo's context map                                                                                                                |

**Scope note (P#122)**: The orchestrator-boundary mechanisms — the
`dispositor-reminder` hint and the `orchestrator_boundary` PostToolUse gate —
are scoped to the **brain repo** because the dispositor concept is
brain-specific: only the agent running in `$ACA_DATA` is the orchestrator.
When the same agent runs in a project source repo (academicOps, mem,
explorations, etc.), it IS the worker for that repo and must execute
directly. Without this scoping, every session everywhere received "queue,
don't execute" instructions, paralysing direct work in project repos. See
PR #805 and issue #806.

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier    | Behaviour                                                                  |
| --------------------------- | -------------------------------------- | -------------------------- | ------- | -------------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn`  | Exits 1 on new `.md` files outside canonical-location allowlist            |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn`  | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries      |
| `lint-axiom-refs`           | `aops-core/lib/lint_axiom_refs.py`     | R1.1, R1.3                 | `block` | Exits 1 when `plugin.json` cites a non-existent or mis-parented Axiom/Rule |

## Composition-time prompt-prose checks (in-agent, no hook)

Mechanisms embedded directly in agent prompt files. They fire when the
agent composes or reviews output, before emitting to the user. Not wired
to hooks or CI — enforced by the agent's own instructions.

| Mechanism                    | Source                                                                                          | Rule(s)         | Scope                                                          | Tier    | Behaviour                                                                                                                                                                           |
| ---------------------------- | ----------------------------------------------------------------------------------------------- | --------------- | -------------------------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rbg pre-response A8 scan`   | `aops-core/agents/rbg.md` § "Pre-Response A8 Scan"                                             | A8              | rbg sessions assessing transcripts or drafted responses        | `block` | When rbg reviews a drafted response, scans for workaround-offer patterns (general-agent #720 blacklist + supervisor drift-framing #821 blacklist). Emits `a8-pre-response: BLOCK`. |
| `supervisor A8 prose scan`   | `aops-core/skills/supervisor/SKILL.md` § "Engineering Integrity (A8) Is Non-Negotiable"        | A8              | Supervisor skill sessions during decomposition and plan-review | `block` | Prohibits drift-framing phrases (#821 blacklist) in triage tables, subtask bodies, and user-facing summaries. Requires rewrite before posting.                                      |
| `supervisor decomp A8 gate`  | `aops-core/skills/supervisor/instructions/decomposition-and-review.md` § "A8 prose scan"       | A8              | Supervisor decomposition phase (Post-Decomposition Self-Check) | `block` | Mandatory prose scan of every subtask body and plan-review summary before posting. Prohibited phrase + structural patterns; rewrite to fix-only decomposition if triggered.         |

## Whole-repo audits (advisory; not wired to commit/CI)

| Check                    | Script                              | Rule(s)                | Tier       | Behaviour                                                    |
| ------------------------ | ----------------------------------- | ---------------------- | ---------- | ------------------------------------------------------------ |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `advisory` | Exits 0; reports files with no incoming wikilinks            |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `advisory` | Exits 1 when any SKILL.md exceeds 500 lines; lists offenders |

## Notes

- `data-markdown-only` — referenced in HEURISTICS.md P#105 as a pre-commit hook
  example; superseded by `check-no-new-orphan-md` (R5.6, added in PR #793).
- Hooks with tier `warn` exit non-zero to block the commit but agents may
  surface the add to the user and proceed under R8.1 in-session authorisation
  (`--no-verify`).
- Hooks with tier `block` represent hard constraints; `--no-verify` is itself
  prohibited by R8.1 for this tier.
- Hooks with tier `advisory` are not invoked by pre-commit or CI. The scripts
  exist for ad-hoc audits but do not gate any workflow.
- `check-skill-line-count` was deliberately removed from CI: the 500-line cap
  was too aggressive for legitimate skill content. The script is retained for
  manual audits, but the cap is not enforced. If we later want a length
  signal, set a higher threshold or convert to a soft warning rather than
  re-wiring the existing exit-1 behaviour.
- `check-orphan-files` wiring is undecided — the orphan question is real but
  the current threshold/scope hasn't been validated. Leaving advisory until
  triaged.
