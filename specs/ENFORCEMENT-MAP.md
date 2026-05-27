# Enforcement Map

> **SSoT (state).** Maps each axiom and load-bearing rule to the
> mechanism(s) currently enforcing it — answers **how is rule X enforced
> today?** Any PR that adds, escalates, or retires enforcement updates a
> row here in the same change (P#65); `rbg` blocks on map currency.
>
> Enforcement is a **regulatory pyramid** (Ayres & Braithwaite 1992,
> _Responsive Regulation_): wide base of high-volume soft mechanisms
> (instructions, conventions, hints), narrowing to a sharp apex of rare
> severe responses (hard blocks, axioms, branch protection). Positions
> **L0–L7** below mark where each mechanism sits; the width at each
> level tracks frequency × marginal cost there. Pyramid framing,
> escalation discipline, PR cost-benefit requirements, and the worked
> A7 example live in
> [`specs/enforcement/enforcement.md`](enforcement/enforcement.md).
> This file is the operative register; that spec is the framing.
>
> **Adjacent state SSoT.** Per-gate forensic-debug detail (source path,
> `polecat.yaml` config, how to verify firing, how to debug) →
> [`specs/GATES.md`](GATES.md). Both are state.

## Pyramid positions (L0–L7)

Lower numbers sit at the **wide base** (high volume, low invasiveness); higher numbers sit toward the **apex** (rare, severe). Add/escalate/remove decisions cite a row of this file plus the position justifying the change. Costs are **marginal** per-fire; combine with frequency for per-session totals. Numbers are order-of-magnitude — measure when proposing.

| L  | Mechanism                            | Marginal cost                               | When justified                                            |
| -- | ------------------------------------ | ------------------------------------------- | --------------------------------------------------------- |
| L0 | PKB note / inline comment            | ~0                                          | Any time                                                  |
| L1 | Skill SKILL.md / CORE.md text        | ~50–500 tok/session (prompt-cached)         | Recurrent friction (≥3 instances), clear callsite         |
| L2 | Mechanical check (pre-commit/bridge) | ~50ms–2s wall-clock                         | Mechanical, deterministic; no judgement                   |
| L3 | Stop-hook injection (always-on)      | ~400–4k tok in-window (compounds on retry)  | Cross-cutting + agent forgets between turns               |
| L4 | PreToolUse gate (`warn`)             | ~20–800 tok per fire; no model dispatch     | Periodic compliance check without LLM                     |
| L5 | PreToolUse gate (`block`)            | ~100–500 tok + tool-call latency            | Hard-block needed; destructive / legal / privacy          |
| L6 | LLM-gated hook (subagent per fire)   | ~1.5–3k tok + 5–30s latency                 | Last resort; structural fixes (L1–L3) have failed         |
| L7 | Numbered axiom (A-tier)              | Permanent context burn (~100 lines, cached) | Must beat trained reflex; cross-cutting; primary contract |

> **Anti-pattern**: jumping to L3+ when the actual failure is recurrence at a single L1 callsite. Most over-deference recurrences (issue #195) were L1 fixes that propagated incompletely, not failures of L1 as a position.

## Runtime gates

### Gate lifecycle

Each gate is a state machine driven by hook events. Forensic detail → [`specs/GATES.md`](GATES.md).

| Gate     | Starts | Closes when                              | Opens when                                   | Re-arms on       | Policy event           | Policy action                     |
| -------- | ------ | ---------------------------------------- | -------------------------------------------- | ---------------- | ---------------------- | --------------------------------- |
| enforcer | OPEN   | n/a (counter-based)                      | `enforcer`/`rbg` subagent resets counter     | counter reset    | PreToolUse @ threshold | Block non-read/infra tools        |
| qa       | OPEN   | Write tool used, or task → `in_progress` | `marsha`/`qa`/`verify` subagent completes    | UserPromptSubmit | Stop while CLOSED      | Block/warn; demand verifier       |
| handover | OPEN   | Write tool used, or task → `in_progress` | `/end_session`, `/dump`, or `handover` skill | UserPromptSubmit | Stop while CLOSED      | Block/warn; demand handover       |
| ida      | CLOSED | n/a (always armed)                       | First Stop in turn (fire-once)               | UserPromptSubmit | Stop while CLOSED      | Inject "show your proof" advisory |

### Gate mode environment variables

| Variable              | Default | Values                 | Controls                  |
| :-------------------- | :------ | :--------------------- | :------------------------ |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | Periodic compliance audit |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | Hydration before work     |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification           |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | Reflection before exit    |
| `IDA_GATE_MODE`       | `warn`  | `warn`, `block`        | Honesty/proof reminder    |

### Session scope

Enforcement is **session-scoped**: every execution context with its own session ID and `SessionStart` event (interactive CLI, background jobs, polecats, GHA workflows) receives the full gate and context-injection stack. Inline subagents spawned via the `Agent` tool share the parent's session ID — gates and context injection are skipped (`ctx.is_subagent` checks in `router.py`) to avoid double-enforcement and recursive loops. Observability (logging, telemetry) fires unconditionally.

This is policy, not a gap. The upstream limitation is that Claude Code provides no native `agent_id` signal (`anthropics/claude-code#16424`); the framework relies on `is_subagent_session()` heuristics in `lib/hook_utils.py`, which are fragile under platform changes. When the upstream signal ships, the heuristics should be replaced.

Full session taxonomy and implementation pointers: [`specs/enforcement/hook-router.md` § Session Scope](enforcement/hook-router.md#session-scope).

## Action vocabulary

| Action    | Definition         | Released when             |
| :-------- | :----------------- | :------------------------ |
| inject    | info into context  | n/a — non-blocking        |
| advisory  | verdict for caller | caller integrates verdict |
| warn      | gate warning       | n/a — agent proceeds      |
| block     | pauses progress    | gate condition met        |
| hard-deny | rejects call       | not released              |

## Axiom × mechanism map

Which mechanism(s) catch a given axiom, what they do when they fire, where in the session lifecycle.

| Rule         | Mechanism                            | Action     | Fires at       | Notes                                                |
| :----------- | :----------------------------------- | :--------- | :------------- | :--------------------------------------------------- |
| A1 Closure   | AXIOMS.md / CORE.md                  | inject     | always-on      |                                                      |
| A1 Closure   | `rbg` review                         | advisory   | review-time    |                                                      |
| A2 Gen       | AXIOMS.md instruction                | inject     | always-on      |                                                      |
| A2 Gen       | `rbg` critic review                  | advisory   | review-time    |                                                      |
| A2 Gen       | aops-skill Phase 2 design            | advisory   | pre-impl       |                                                      |
| A3 Epistemic | AXIOMS.md / CORE.md                  | inject     | always-on      |                                                      |
| A3 Epistemic | Proof-of-compliance                  | block      | `release_task` |                                                      |
| A3 Epistemic | `marsha` verification                | advisory   | review-time    |                                                      |
| A3 Epistemic | `rbg` review                         | advisory   | review-time    |                                                      |
| A4 Citations | AXIOMS.md instruction                | inject     | always-on      |                                                      |
| A4 Citations | auto-mode `Academic Integrity`       | warn       | PreToolUse     |                                                      |
| A4 Citations | `rbg` review                         | advisory   | review-time    |                                                      |
| A4 Citations | `/learn` RCA schema                  | block      | invocation     |                                                      |
| A5 SSOT      | AXIOMS.md / aops-skill SSOT          | inject     | always-on      |                                                      |
| A5 SSOT      | auto-mode `Backup File Patterns`     | warn       | PreToolUse     |                                                      |
| A5 SSOT      | `find_duplicates` tool               | advisory   | on-demand      |                                                      |
| A5 SSOT      | `rbg` duplicate review               | advisory   | review-time    |                                                      |
| A6 Scope     | AXIOMS.md / Decision Frm             | inject     | always-on      |                                                      |
| A6 Scope     | TodoWrite reminder                   | inject     | TodoWrite      |                                                      |
| A6 Scope     | auto-mode `Scope Discipline`         | warn       | PreToolUse     |                                                      |
| A6 Scope     | auto-mode `Plan First`               | warn       | PreToolUse     |                                                      |
| A6 Scope     | auto-mode `Costly Operations`        | warn       | PreToolUse     | Threshold: >50 calls or >$1                          |
| A6 Scope     | `orchestrator_boundary`              | warn       | PostToolUse    |                                                      |
| A6 Scope     | enforcer gate                        | warn/block | PreToolUse     |                                                      |
| A6 Scope     | `rbg` review                         | advisory   | review-time    |                                                      |
| A6 Scope     | pr-reviewer GHA                      | warn       | PR push        |                                                      |
| A7 Authority | AXIOMS.md / task criteria            | inject     | always-on      |                                                      |
| A7 Authority | auto-mode `Classification`           | warn       | PreToolUse     |                                                      |
| A7 Authority | auto-mode `Acceptance Criteria`      | warn       | PreToolUse     |                                                      |
| A7 Authority | `marsha` criterion check             | advisory   | review-time    |                                                      |
| A7 Authority | `rbg` review                         | advisory   | review-time    |                                                      |
| A7 Authority | pr-reviewer GHA                      | warn       | PR push        |                                                      |
| A7 Authority | QA gate                              | block      | Stop           | See gate lifecycle table                             |
| A8 Halt      | AXIOMS.md / CORE.md                  | inject     | always-on      |                                                      |
| A8 Halt      | auto-mode `No Validation Bypass`     | block      | PreToolUse     | `--force` carve-out for benign cleanup               |
| A8 Halt      | auto-mode `Silent Workaround`        | warn       | PreToolUse     |                                                      |
| A8 Halt      | auto-mode `Infra Workarounds`        | warn       | PreToolUse     |                                                      |
| A8 Halt      | `policy_enforcer` (git)              | hard-deny  | PreToolUse     |                                                      |
| A8 Halt      | `fail_fast_watchdog`                 | warn       | PostToolUse    |                                                      |
| A8 Halt      | commit gate                          | warn       | commit-time    |                                                      |
| A8 Halt      | branch protection                    | block      | merge          |                                                      |
| A8 Halt      | `rbg` review                         | advisory   | review-time    |                                                      |
| A9 Boundary  | AXIOMS.md instruction                | inject     | always-on      |                                                      |
| A9 Boundary  | credential isolation                 | hard-deny  | SessionStart   |                                                      |
| A9 Boundary  | CC auto-mode rules                   | block      | PreToolUse     |                                                      |
| A9 Boundary  | `policy_enforcer` (env)              | hard-deny  | PreToolUse     |                                                      |
| A9 Boundary  | commit gate                          | warn       | commit-time    |                                                      |
| A9 Boundary  | branch protection                    | block      | merge          |                                                      |
| A10 Immut    | AXIOMS.md / CORE.md                  | inject     | always-on      |                                                      |
| A10 Immut    | auto-mode `Evidentiary Immutability` | block      | PreToolUse     | Globs: `**/records/**`, `$ACA_DATA/records/**`, etc. |
| A10 Immut    | `policy_enforcer` paths              | hard-deny  | PreToolUse     |                                                      |
| A10 Immut    | `rbg` review                         | advisory   | review-time    |                                                      |

### Cross-cutting concerns

| Concern    | Mechanism               | Action     | Fires at      | Notes                                      |
| :--------- | :---------------------- | :--------- | :------------ | :----------------------------------------- |
| Hydration  | hydrator / skills       | inject     | UserPrompt    |                                            |
| Hydration  | hydration gate          | warn       | lifecycle     |                                            |
| Handover   | /dump / reflection      | inject     | invocation    |                                            |
| Handover   | handover gate           | warn/block | Stop          | See gate lifecycle table                   |
| Audit      | countdown / subagent    | warn/block | threshold     |                                            |
| Audit      | compliance block flag   | hard-deny  | lifecycle     |                                            |
| Pipeline   | pr-reviewer / enforcer  | warn       | PR push       |                                            |
| Pipeline   | linter / branch prot    | block      | merge         |                                            |
| Pipeline   | loop detector           | hard-deny  | merge-prep    |                                            |
| Pipeline   | admin approval          | block      | merge         |                                            |
| Linting    | rules 6-9 (skill/agent) | block      | Pre-commit/PR | Linter: `aops-core/lib/lint_axiom_refs.py` |
| Linting    | permissions-lint        | block      | PR push       | **planned**                                |
| Supervisor | plan-review gate        | block      | post-decomp   |                                            |
| H91        | HEURISTICS.md           | inject     | always-on     |                                            |
| H91        | `rbg` review            | advisory   | review-time   |                                            |

### Known gaps

- **Hydration**: parent skip cascades to child; missing hydration/commit gate bodies.
- **Reactive**: PostToolUse on tool error is `planned` (Phase 2).
- **QA**: gate active (close-on-work-begin landed); requirements still freeform — verifier prompt reviews session narrative, no structured acceptance-criteria source yet.
- **Settings**: global/user rules unverifiable from this repo.
- **Evidence Loop**: Steps 4-5 (pattern detection) and Step 7 (auto-map update) partial/unbuilt.
- **Subagent enforcement**: gates and context injection skipped for `is_subagent` sessions — this is by policy, not a gap. See [Session scope](#session-scope) above.

## Mechanism catalogues

Each entry: name, pyramid position, purpose, authoritative source. Runtime-gate forensic detail → [`specs/GATES.md`](GATES.md).

### Runtime hooks (`aops-core/hooks/router.py`)

| Mechanism             | L  | Action     | Purpose                                                | Source                                                                                   |
| :-------------------- | :- | :--------- | :----------------------------------------------------- | :--------------------------------------------------------------------------------------- |
| `enforcer` gate       | L6 | warn/block | Periodic axiom-compliance check via subagent           | [`ultra-vires-enforcer.md`](enforcement/ultra-vires-enforcer.md), [`GATES.md`](GATES.md) |
| `qa` gate             | L3 | warn/block | Requires verification before Stop                      | [`GATES.md`](GATES.md)                                                                   |
| `handover` gate       | L3 | warn/block | Blocks Stop until commit + task update + reflection    | [`GATES.md`](GATES.md)                                                                   |
| `ida` gate            | L3 | warn       | Back assertions with proof; disclose skips             | [`GATES.md`](GATES.md)                                                                   |
| `hydration` gate      | L4 | warn       | Blocks tool calls until hydrator runs (mode-dependent) | [`GATES.md`](GATES.md)                                                                   |
| `aca_data_autocommit` | L2 | —          | Auto-commits `$ACA_DATA` after state-modifying calls   | `aops-core/hooks/router.py:_run_aca_data_autocommit`                                     |
| `context-map hints`   | L1 | inject     | Doc pointers from `.agents/context-map.json` on UPS    | `aops-core/hooks/router.py:_inject_context_map_hints`                                    |
| ~~`policy_enforcer`~~ | —  | —          | **Retired 2026-05-15** (sandbox supersedes)            | `aops-e0d015d9`                                                                          |
| ~~`commit` gate~~     | —  | —          | **Retired PR #988** (superseded by `handover`)         | —                                                                                        |

### Pre-commit hooks

| Hook                        | L  | Action | Purpose                                                 | Source                                 |
| :-------------------------- | :- | :----- | :------------------------------------------------------ | :------------------------------------- |
| `check-no-new-orphan-md`    | L2 | warn   | New `.md` outside canonical-location allowlist (R5.6)   | `scripts/check_no_new_orphan_md.py`    |
| `check-framework-integrity` | L2 | warn   | Broken wikilinks or missing index entries               | `scripts/check_framework_integrity.py` |
| `check-no-fallbacks`        | L2 | warn   | Silent-fallback patterns in hooks (A8 / P#8; #930)      | `scripts/check_no_fallbacks.py`        |
| `normalize-mcp-names`       | L2 | warn   | Auto-heals Gemini-form MCP names to Claude form (#1128) | `scripts/normalize_mcp_names.py`       |

### Bridge-level constraints

| Constraint                 | L  | Action | Purpose                                       | Source                  |
| :------------------------- | :- | :----- | :-------------------------------------------- | :---------------------- |
| `create_task` prefix guard | L2 | block  | ID prefix must match task type / project slug | `polecat/pkb_bridge.py` |
| `claude` OAUTH pre-flight  | L2 | block  | Exits 4 when `CLAUDE_CODE_OAUTH_TOKEN` unset  | `polecat/cli.py`        |

### CORE.md directives

| Directive   | L  | Action | Purpose                                   | Source            |
| :---------- | :- | :----- | :---------------------------------------- | :---------------- |
| `pkb-first` | L1 | inject | Agents must use PKB before reading source | `.agents/CORE.md` |

### Scheduled batch automation

| Job                   | L  | Purpose                                         | Source                               |
| :-------------------- | :- | :---------------------------------------------- | :----------------------------------- |
| `apply_triage` labels | L0 | Labels open PRs; opens issue for escalate-class | `aops-core/scripts/dump_pr_state.py` |

### PR-pipeline agents (v2)

Branch protection AND-gates each `<agent>-status` directly — no LLM judgment in the merge gate. **Phase 1 operative (PR #1062); phases 2/3/5 pending.** Contract: [`pr-pipeline-v2.md`](workflows/pr-pipeline-v2.md).

| Agent              | L     | Action | Purpose                                         | Source                                                          |
| :----------------- | :---- | :----- | :---------------------------------------------- | :-------------------------------------------------------------- |
| `enforcer-status`  | L6    | block  | Reviews PR diff against axioms; SHA-skip dedupe | `.github/workflows/agent-enforcer.yml@enforcer-v1`              |
| `alignment-status` | L6    | block  | PKB design-intent alignment; off-GHA dispatch   | `.github/workflows/agent-alignment.yml@alignment-v1`            |
| `mechanic-status`  | L4–L6 | —      | Mechanical merge + conflict resolution only     | `.github/workflows/agent-mechanic.yml@mechanic-v1`              |
| ~~v1 agents~~      | —     | —      | **Retired Phase 1** (PR #1062)                  | [`pr-pipeline-v2.md`](workflows/pr-pipeline-v2.md) §3.1/§3.6/§5 |

## Related

- [`specs/enforcement/enforcement.md`](enforcement/enforcement.md) — pyramid framing, escalation discipline, PR cost-benefit requirements, worked A7 example.
- [`specs/enforcement/enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md) — per-mechanism reference catalogue.
- [`specs/enforcement/ultra-vires-enforcer.md`](enforcement/ultra-vires-enforcer.md) — enforcer agent + gate internal design.
- [`specs/enforcement/hook-router.md`](enforcement/hook-router.md) — hook router architecture.
- [`.agents/rules/AXIOMS.md`](../.agents/rules/AXIOMS.md) — universal axioms.
- [`.agents/rules/HEURISTICS.md`](../.agents/rules/HEURISTICS.md) — advisory heuristics; P#65 governs map currency.
- [`specs/GATES.md`](GATES.md) — adjacent state SSoT for runtime gate forensic detail.
