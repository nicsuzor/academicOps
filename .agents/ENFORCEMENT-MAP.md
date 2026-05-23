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
> [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md).
> This file is the operative register; that spec is the framing.
>
> **Adjacent state SSoT.** Per-gate forensic-debug detail (source path,
> `polecat.yaml` config, how to verify firing, how to debug) →
> [`aops-core/GATES.md`](../aops-core/GATES.md). Both are state.

## Pyramid positions (L0–L7)

Lower numbers sit at the **wide base** (high volume, low invasiveness); higher numbers sit toward the **apex** (rare, severe). Add/escalate/remove decisions cite a row of this file plus the position justifying the change. Costs are **marginal** per-fire; combine with frequency for per-session totals. Numbers are order-of-magnitude — measure when proposing.

| L  | Mechanism                               | Indicative marginal cost                                                 | When justified                                                 |
| -- | --------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------- |
| L0 | PKB note / inline comment               | ~0                                                                       | Any time                                                       |
| L1 | Skill SKILL.md / CORE.md text           | ~50–500 tok/session × per-invoke (cached at SessionStart)                | Recurrent friction (≥3 instances) and a clear callsite         |
| L2 | Mechanical check (pre-commit/bridge)    | ~50ms–2s wall-clock or negligible latency                                | Mechanical, deterministic check; no judgement                  |
| L3 | Stop-hook injection (always-on)         | ~400–4,000 tok in-window per session (compounds on repeated Stop)        | Cross-cutting + agent demonstrably forgets between turns       |
| L4 | PreToolUse gate (`warn`)                | ~20–800 tok per fire (depends on injected template); no model dispatch   | Periodic compliance check without LLM dispatch                 |
| L5 | PreToolUse gate (`block`)               | ~100–500 tok per block fire + tool-call latency to evaluate every call   | Hard-block needed; destructive / legal / privacy               |
| L6 | LLM-gated hook (subagent call per fire) | ~1.5–3k tok + 5–30s latency × every fire (subagent dispatch)             | Last resort; structural fixes (L1–L3) have failed              |
| L7 | Numbered axiom (A-tier)                 | Permanent context burn (~100 lines, prompt-cached) + every surface cites | Rule must beat trained reflex; cross-cutting; primary contract |

> **Anti-pattern**: jumping to L3+ when the actual failure is recurrence at a single L1 callsite. Most over-deference recurrences (issue #195) were L1 fixes that propagated incompletely, not failures of L1 as a position.

## Axiom × mechanism map

Which mechanism(s) catch a given axiom, what they do when they fire, where in the session lifecycle. **Pyramid position (L0–L7)** sits with the mechanism in the catalogues below; the **Action** column here is the descriptive vocabulary — what the mechanism _does_ when it fires (`inject` / `advisory` / `warn` / `block` / `hard-deny`).

| Action    | Definition         | Released when             |
| :-------- | :----------------- | :------------------------ |
| inject    | info into context  | n/a — non-blocking        |
| advisory  | verdict for caller | caller integrates verdict |
| warn      | gate warning       | n/a — agent proceeds      |
| block     | pauses progress    | gate condition met        |
| hard-deny | rejects call       | not released              |

### Gate mode environment variables

| Variable              | Default | Values                 | Controls                  |
| :-------------------- | :------ | :--------------------- | :------------------------ |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | periodic compliance audit |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | hydration before work     |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification           |
| `COMMIT_GATE_MODE`    | `warn`  | `warn`, `block`        | commit policy             |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | reflection before exit    |

### Axiom-keyed rule registry

| Rule         | Mechanism                            | Action     | Fires at       | Status                                                                                                     |
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
| A7 Authority | QA gate                              | block      | Stop           | active — closes on `update_task in_progress` / write tool; reopens on `qa\|verify\|marsha` subagent        |
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
| Linting      | rules 6-9 (skill/agent)              | block      | Pre-commit/PR  | active — linter: aops-core/lib/lint_axiom_refs.py                                                          |
| Linting      | permissions-lint                     | block      | PR push        | planned                                                                                                    |
| Supervisor   | plan-review gate                     | block      | post-decomp    | active                                                                                                     |
| H91 Deadline | HEURISTICS.md                        | inject     | always-on      | active                                                                                                     |
| H91 Deadline | `rbg` review                         | advisory   | review-time    | active                                                                                                     |

### Known gaps (axiom-keyed view)

- **Hydration**: parent skip cascades to child; missing hydration/commit gate bodies.
- **Reactive**: PostToolUse on tool error is `planned` (Phase 2).
- **QA**: gate active (close-on-work-begin landed); requirements still freeform — verifier prompt reviews session narrative, no structured acceptance-criteria source yet.
- **Settings**: global/user rules unverifiable from this repo.
- **Evidence Loop**: Steps 4-5 (pattern detection) and Step 7 (auto-map update) partial/unbuilt.

## Mechanism catalogues

Each entry: name + position + one-line purpose + link to authoritative file. Runtime-gate forensic detail → [`aops-core/GATES.md`](../aops-core/GATES.md).

### Runtime hooks (in-session, via `aops-core/hooks/router.py`)

- **`hydration` gate** (L4, warn) — blocks tool calls until hydrator runs (mode-dependent). → [`GATES.md`](../aops-core/GATES.md)
- **`enforcer` gate** (L6, warn/block) — periodic axiom-compliance check via enforcer subagent. → [`ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md), [`GATES.md`](../aops-core/GATES.md)
- **`qa` gate** (L3, warn) — requires verification (marsha via `/verify`) before Stop. → [`GATES.md`](../aops-core/GATES.md)
- **`handover` gate** (L3, warn) — blocks Stop until commit + task update + framework reflection complete. → [`GATES.md`](../aops-core/GATES.md)
- **`ida` gate** (L3, warn) — reminder to back assertions with proof and disclose skips. → [`GATES.md`](../aops-core/GATES.md)
- **`aca_data_autocommit`** (L2) — auto-commits `$ACA_DATA` after state-modifying tool calls. → `aops-core/hooks/router.py:_run_aca_data_autocommit`
- **`context-map hints`** (L1, hint) — injects doc pointers from `.agents/context-map.json` on UPS. → `aops-core/hooks/router.py:_inject_context_map_hints`
- ~~`policy_enforcer`~~ — **retired 2026-05-15** (sandbox supersedes; `aops-e0d015d9`).
- ~~`commit` gate~~ — **retired PR #988** (config-only; superseded by `handover`).

### Pre-commit hooks

- **`check-no-new-orphan-md`** (L2, warn) — exits 1 on new `.md` outside canonical-location allowlist (R5.6). → `scripts/check_no_new_orphan_md.py`
- **`check-framework-integrity`** (L2, warn) — exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries. → `scripts/check_framework_integrity.py`
- **`check-no-fallbacks`** (L2, warn) — exits 1 on silent-fallback patterns in hooks (A8 / P#8; #930). → `scripts/check_no_fallbacks.py`
- **`normalize-mcp-names`** (L2, warn) — auto-heals Gemini-form MCP names to canonical Claude form (#1128). → `scripts/normalize_mcp_names.py`

### CORE.md directives (always-on, prompt-cached)

- **`pkb-first`** (L1, hint) — agents must use PKB before reading source code. → `.agents/CORE.md` "Where to find documentation"

### Bridge-level constraints (synchronous, fires at call time)

- **`create_task` prefix guard** (L2, block) — raises `ValueError` when ID prefix mismatches task type / project slug. → `polecat/pkb_bridge.py` (spec: `projects/aops/specs/pkb/consistency.md` AC#5)
- **`claude OAUTH token pre-flight`** (L2, block) — exits 4 with `claude setup-token` remediation when `CLAUDE_CODE_OAUTH_TOKEN` is unset (A8; `aops-06ab3ee0`). → `polecat/cli.py`

### Scheduled batch automation

- **`apply_triage` labels** (L0) — applies `triage:escalate` / `:stale` / `:auto-mergeable` / `:needs-judgment` to open PRs; opens GitHub issue for escalate-class PRs. → `aops-core/scripts/dump_pr_state.py`

### PR-pipeline agents (v2)

LLM agents that fire on PR events; each maps to one named GitHub status check. Branch protection AND-gates each `<agent>-status` directly — no LLM judgment in the merge gate. **Phase 1 operative (PR #1062); phases 2/3/5 pending.** Contract: [`pr-pipeline-v2.md`](../specs/workflows/pr-pipeline-v2.md).

- **`enforcer-status` (rbg)** (L6, block) — reviews PR diff against axioms; posts review + status on HEAD SHA (SHA-skip dedupe). → `.github/workflows/agent-enforcer.yml@enforcer-v1` + `.github/agents/enforcer.agent.md`
- **`alignment-status` (pauli)** (L6, block) — reviews PR for alignment to PKB-recorded design intent; off-GHA dispatch via polecat. Closes v1 gap #1034. → `.github/workflows/agent-alignment.yml@alignment-v1` + `aops-core/scripts/alignment-dispatcher.sh`
- **`mechanic-status`** (L4–L6) — mechanical only: merge from base + unambiguous conflict resolution; does not approve or substitute for missing agent verdicts. → `.github/workflows/agent-mechanic.yml@mechanic-v1`
- ~~v1: Author-trailer loop-skip, Triage-substitution, Loose enforcer triggers~~ — all retired Phase 1 (PR #1062); see [`pr-pipeline-v2.md`](../specs/workflows/pr-pipeline-v2.md) §3.1/§3.6/§5.

## Related

- [`specs/enforcement/enforcement.md`](../specs/enforcement/enforcement.md) — pyramid framing, escalation discipline, PR cost-benefit requirements, worked A7 example, user-story flows (witness → judge separation).
- [`specs/enforcement/enforcement-mechanisms.md`](../specs/enforcement/enforcement-mechanisms.md) — per-mechanism reference catalogue (companion spec).
- [`specs/enforcement/ultra-vires-enforcer.md`](../specs/enforcement/ultra-vires-enforcer.md) — enforcer agent + gate internal design.
- [`specs/enforcement/hook-router.md`](../specs/enforcement/hook-router.md) — hook router architecture.
- [`aops-core/AXIOMS.md`](../aops-core/AXIOMS.md) — universal axioms.
- [`aops-core/HEURISTICS.md`](../aops-core/HEURISTICS.md) — advisory heuristics; P#65 governs map currency.
- [`aops-core/GATES.md`](../aops-core/GATES.md) — adjacent state SSoT for runtime gate forensic detail.
