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
| `custodiet` gate      | PreToolUse       | `aops-core/lib/gates/definitions.py`                    | (R: workflow discipline — premature termination)  | All sessions                          | `warn`  | Detects scope explosion / plan-less execution                            |
| `policy_enforcer`     | PreToolUse       | `aops-core/hooks/policy_enforcer.py`                    | (R: destructive-command guards)                   | All sessions                          | `block` | Hard-blocks dangerous Bash patterns (force-push to main, `rm -rf`, etc.) |
| `aca_data_autocommit` | PostToolUse      | `aops-core/hooks/router.py` `_run_aca_data_autocommit`  | (procedural: keep PKB synced)                     | When `$ACA_DATA` set                  | n/a     | Auto-commits `$ACA_DATA` after state-modifying tool calls                |
| `context-map hints`   | UserPromptSubmit | `aops-core/hooks/router.py` `_inject_context_map_hints` | (procedural: discovery via `.agents/context-map`) | Repos with `.agents/context-map.json` | `hint`  | Injects relevant doc pointers from the repo's context map                |

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

## Composition-time prompt-prose checks (in-agent, no hook)

Mechanisms embedded directly in agent prompt files. They fire when the
agent composes or reviews output, before emitting to the user. Not wired
to hooks or CI — enforced by the agent's own instructions.

| Mechanism                    | Source                                                                                   | Rule(s) | Scope                                                          | Tier         | Behaviour                                                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------- | ------- | -------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rbg a8-instinct`            | `aops-core/agents/rbg.md` (axiomatic; no named section — instinct via `@AXIOMS.md`)      | A8      | All rbg PR review sessions                                     | `block`      | Applies A8 instinct check to every PR review. Emits `REQUEST_CHANGES` when workaround-offer or drift-framing patterns detected. Instinct-based (no phrase-match enumeration) — restructured from `rbg pre-response A8 scan` in PR #891; combined-lenses framing removed in PR #895. `§ "How you judge"` was removed in PR #895; A8 compliance is now exercised through AXIOMS.md axiom-application. |
| `rbg p65-gate`               | `aops-core/agents/rbg.md` § "Blocking Verdict Rules"                                     | P#65    | All rbg PR review sessions                                     | `block`      | BLOCKs when a PR adds, removes, or modifies an enforcement gate and `.agents/ENFORCEMENT-MAP.md` is not updated in the same PR. Gate types: `gates/definitions.py` entries, pre-commit hooks in `.pre-commit-config.yaml`, deny rules in `settings.json`/`policies/*.toml`, hooks under `aops-core/hooks/`, policy enforcers under `aops-core/scripts/`. Added in PR #896.                          |
| `rbg criterion-substitution` | `aops-core/agents/rbg.md` § "Rule 1 — Criterion Substitution Detector"                   | A3      | All rbg PR review sessions                                     | `block`      | BLOCKs when a PR's title or description claims to deliver change X but the diff only contains artifacts _about_ X rather than artifacts that _are_ X. Carve-outs for documentation-only and test-only PRs with matching titles. Added in PR #896 (previously in PR #853; reverted; restored).                                                                                                       |
| `rbg scope-awareness`        | `aops-core/agents/rbg.md` § "Rule 2 — Scope Awareness"                                   | A7      | All rbg PR review sessions                                     | `block`      | BLOCKs with redirect when the change claimed by the PR cannot be made in the current repository because the relevant artifacts live elsewhere. Emits the correct repo/surface and recommends closing and redirecting. Added in PR #896 (previously in PR #853; reverted; restored).                                                                                                                 |
| `rbg keystone-disclosure`    | `aops-core/agents/rbg.md` § "Rule 3 — Unverified-Keystone Disclosure"                    | A3      | All rbg PR review sessions                                     | `revise`     | REVISEs when a PR has load-bearing technical claims with no supporting evidence (test, runtime trace, cited spec, or upstream doc link) and the claim is not disclosed as unverified in the PR body. Disclosed unverified claims are not blocking. Added in PR #896 (previously in PR #853; reverted; restored).                                                                                    |
| `rbg sensitive-data-scan`    | `aops-core/agents/rbg.md` § "Rule 4 — Sensitive-Data Scanner"                            | A9      | All rbg PR review sessions                                     | `block/warn` | Scans diff for private network identifiers committed to a public repo: Tailscale `*.ts.net` hostnames, RFC1918 literal IPs, mDNS `*.local` hostnames (excluding `localhost` and `*.local.test`). BLOCKs in production usage; WARNs in environment-orientation docs (e.g. `CAPABILITIES.md`). Added in PR #896 (previously in PR #853; reverted; restored).                                          |
| `supervisor A8 prose scan`   | `aops-core/skills/supervisor/SKILL.md` § "Engineering Integrity (A8) Is Non-Negotiable"  | A8      | Supervisor skill sessions during decomposition and plan-review | `block`      | Prohibits drift-framing phrases (#821 blacklist) in triage tables, subtask bodies, and user-facing summaries. Requires rewrite before posting.                                                                                                                                                                                                                                                      |
| `supervisor decomp A8 gate`  | `aops-core/skills/supervisor/instructions/decomposition-and-review.md` § "A8 prose scan" | A8      | Supervisor decomposition phase (Post-Decomposition Self-Check) | `block`      | Mandatory prose scan of every subtask body and plan-review summary before posting. Prohibited phrase + structural patterns; rewrite to fix-only decomposition if triggered.                                                                                                                                                                                                                         |

## Whole-repo audits (advisory; not wired to commit/CI)

| Check                    | Script                              | Rule(s)                | Tier       | Behaviour                                                    |
| ------------------------ | ----------------------------------- | ---------------------- | ---------- | ------------------------------------------------------------ |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `advisory` | Exits 0; reports files with no incoming wikilinks            |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `advisory` | Exits 1 when any SKILL.md exceeds 500 lines; lists offenders |
