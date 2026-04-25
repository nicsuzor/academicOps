---
title: Enforcement Map
type: state
category: state
description: Live registry of framework enforcement mechanisms and their severity tiers.
tier: core
depends_on: [enforcement]
tags: [framework, enforcement, rules, state]
---

# Enforcement Map

This map records framework enforcement: **for each rule, which mechanisms catch it today, at what severity, and where the next move should land.**

## Pipeline Reference

Pipeline (Capture → Soft gates → Hard blocks → Review → Handover → Merge) lives in `specs/enforcement.md` §3. Mechanisms cite events: `PreToolUse`, `Stop`, `review-time`, `PR push`, `merge attempt`, `always-on`.

## Severity Pyramid

`inject` → `advisory` → `warn` → `block` → `hard-deny`. Use the lightest tier. Move up on bypass; move down on false-positives. Tier choice is governed by `enforcement.md` §5, not intuition.

| Tier      | Action             | Released when             |
| :-------- | :----------------- | :------------------------ |
| Inject    | info into context  | n/a — non-blocking        |
| Advisory  | verdict for caller | caller integrates verdict |
| Warn      | gate warning       | n/a — agent proceeds      |
| Block     | pauses progress    | gate condition met        |
| Hard-deny | rejects call       | not released              |

### Gate Mode Environment Variables

| Variable              | Default | Values                 | Controls                  |
| :-------------------- | :------ | :--------------------- | :------------------------ |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | periodic compliance audit |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | hydration before work     |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification           |
| `COMMIT_GATE_MODE`    | `warn`  | `warn`, `block`        | commit policy             |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | reflection before exit    |

## Rule Registry

| Rule         | Mechanism                            | Tier       | Fires at       | Status                                                                                                     |
| :----------- | :----------------------------------- | :--------- | :------------- | :--------------------------------------------------------------------------------------------------------- |
| A1 Closure   | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A1 Closure   | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A2 Gen       | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A2 Gen       | `rbg` critic review                  | advisory   | review-time    | active                                                                                                     |
| A2 Gen       | aops-skill Phase 2 design            | advisory   | pre-impl       | active                                                                                                     |
| A3 Epistemic | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A3 Epistemic | Proof-of-compliance                  | block      | `release_task` | active                                                                                                     |
| A3 Epistemic | `marsha` verification                | advisory   | review-time    | active                                                                                                     |
| A3 Epistemic | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A4 Citations | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A4 Citations | auto-mode `Academic Integrity`       | warn       | PreToolUse     | active                                                                                                     |
| A4 Citations | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A4 Citations | `/learn` RCA schema                  | block      | invocation     | active                                                                                                     |
| A5 SSOT      | AXIOMS.md / aops-skill SSOT          | inject     | always-on      | active                                                                                                     |
| A5 SSOT      | auto-mode `Backup File Patterns`     | warn       | PreToolUse     | active                                                                                                     |
| A5 SSOT      | `find_duplicates` tool               | advisory   | on-demand      | active                                                                                                     |
| A5 SSOT      | `rbg` duplicate review               | advisory   | review-time    | active                                                                                                     |
| A6 Scope     | AXIOMS.md / Decision Frm             | inject     | always-on      | active                                                                                                     |
| A6 Scope     | TodoWrite reminder                   | inject     | TodoWrite      | active                                                                                                     |
| A6 Scope     | auto-mode `Scope Discipline`         | warn       | PreToolUse     | active                                                                                                     |
| A6 Scope     | auto-mode `Plan First`               | warn       | PreToolUse     | active                                                                                                     |
| A6 Scope     | auto-mode `Costly Operations`        | warn       | PreToolUse     | active — threshold: >50 calls or >$1                                                                       |
| A6 Scope     | `orchestrator_boundary`              | warn       | PostToolUse    | active                                                                                                     |
| A6 Scope     | enforcer gate (B)                    | warn/block | PreToolUse     | active                                                                                                     |
| A6 Scope     | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A6 Scope     | pr-reviewer GHA                      | warn       | PR push        | active                                                                                                     |
| A7 Authority | AXIOMS.md / task criteria            | inject     | always-on      | active                                                                                                     |
| A7 Authority | auto-mode `Classification`           | warn       | PreToolUse     | active                                                                                                     |
| A7 Authority | auto-mode `Acceptance Criteria`      | warn       | PreToolUse     | active                                                                                                     |
| A7 Authority | `marsha` criterion check             | advisory   | review-time    | active                                                                                                     |
| A7 Authority | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A7 Authority | pr-reviewer GHA                      | warn       | PR push        | active                                                                                                     |
| A7 Authority | QA gate                              | block      | Stop           | planned                                                                                                    |
| A8 Halt      | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A8 Halt      | auto-mode `No Validation Bypass`     | block      | PreToolUse     | active — `--force` carve-out for benign cleanup                                                            |
| A8 Halt      | auto-mode `Silent Workaround`        | warn       | PreToolUse     | active                                                                                                     |
| A8 Halt      | auto-mode `Infra Workarounds`        | warn       | PreToolUse     | active                                                                                                     |
| A8 Halt      | `policy_enforcer` (git)              | hard-deny  | PreToolUse     | active                                                                                                     |
| A8 Halt      | `fail_fast_watchdog`                 | warn       | PostToolUse    | active                                                                                                     |
| A8 Halt      | commit gate                          | warn       | commit-time    | active                                                                                                     |
| A8 Halt      | branch protection                    | block      | merge          | active                                                                                                     |
| A8 Halt      | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| A9 Boundary  | AXIOMS.md instruction                | inject     | always-on      | active                                                                                                     |
| A9 Boundary  | credential isolation                 | hard-deny  | SessionStart   | active                                                                                                     |
| A9 Boundary  | CC auto-mode rules                   | block      | PreToolUse     | active                                                                                                     |
| A9 Boundary  | `policy_enforcer` (env)              | hard-deny  | PreToolUse     | active                                                                                                     |
| A9 Boundary  | commit gate                          | warn       | commit-time    | active                                                                                                     |
| A9 Boundary  | branch protection                    | block      | merge          | active                                                                                                     |
| A10 Immut    | AXIOMS.md / CORE.md                  | inject     | always-on      | active                                                                                                     |
| A10 Immut    | auto-mode `Evidentiary Immutability` | block      | PreToolUse     | active — globs: `**/records/**`, `$ACA_DATA/records/**`, `~/brain/records/**`, `~/writing/data/records/**` |
| A10 Immut    | `policy_enforcer` paths              | hard-deny  | PreToolUse     | active                                                                                                     |
| A10 Immut    | `rbg` review                         | advisory   | review-time    | active                                                                                                     |
| Hydration    | hydrator / skills                    | inject     | UserPrompt     | active                                                                                                     |
| Hydration    | hydration gate                       | warn       | lifecycle      | active                                                                                                     |
| Handover     | /dump / reflection                   | inject     | invocation     | active                                                                                                     |
| Handover     | handover gate                        | warn/block | Stop           | active                                                                                                     |
| Audit        | countdown / subagent                 | warn/block | threshold      | active                                                                                                     |
| Audit        | compliance block flag                | hard-deny  | lifecycle      | active                                                                                                     |
| Pipeline     | pr-reviewer / enforcer               | warn       | PR push        | active                                                                                                     |
| Pipeline     | linter / branch prot                 | block      | merge          | active                                                                                                     |
| Pipeline     | loop detector                        | hard-deny  | merge-prep     | active                                                                                                     |
| Pipeline     | admin approval                       | block      | merge          | active                                                                                                     |
| Linting      | rules 6-9 (skill/agent)              | warn/error | PR push        | planned                                                                                                    |
| Linting      | permissions-lint                     | error      | PR push        | planned                                                                                                    |
| Supervisor   | plan-review gate                     | block      | post-decomp    | active                                                                                                     |

## Known Gaps

- **Hydration**: parent skip cascades to child; missing hydration/commit gate bodies.
- **Reactive**: PostToolUse on tool error is `planned` (Phase 2).
- **QA**: gate present but requirements not codified.
- ~~**Auto-mode**: rules cite old P# IDs (task-06db60dc).~~ — closed; rules now cite A1–A10 axiom IDs as prose-with-reasoning.
- **Settings**: global/user rules unverifiable from this repo.
- **Evidence Loop**: Steps 4-5 (pattern detection) and Step 7 (auto-map update) partial/unbuilt.

## How to Update

1. **Observe** failure (QA, /retro, /sleep, report). 2. **File evidence** via `/learn`. 3. **Locate rule** in registry. 4. **Propose tier change** (escalate/demote). 5. **Update row** in same PR.

## Related

`specs/enforcement.md`, `specs/enforcement-mechanisms.md`, `specs/ultra-vires-enforcer.md`, `aops-core/AXIOMS.md`.
