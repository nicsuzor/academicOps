# Enforcement Map

> **State.** Routing table for "how is each rule currently enforced?". Any PR that adds, escalates, or retires a mechanism updates a row here in the same change (P#65); `rbg` blocks on currency.
>
> Framing, escalation discipline, PR cost-benefit, and the worked A7 example → [`specs/enforcement/enforcement.md`](enforcement/enforcement.md). Per-gate forensic detail (config, verify, debug) → [`specs/GATES.md`](GATES.md). Both adjacent files are state.

## Pyramid (L0–L7)

Rows are **mechanism categories** on a coercion-strength × frequency axis. A tier holds **multiple blocks** at the same coercion level. Axioms (rules) do **not** appear as pyramid rows — they are the _content_ L1 always-on mechanisms carry. Executive/legislative distinction and escalation discipline → [`enforcement.md`](enforcement/enforcement.md) §4. Costs are order-of-magnitude per fire; combine with frequency for per-session totals.

| L  | Class      | Mechanism categories (multiple blocks per tier)                                                                                                                                  | Marginal cost                              |
| -- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| L0 | base       | **Authoring memory**: PKB notes · inline comments · doc-strings                                                                                                                  | ~0                                         |
| L1 | base       | **SessionStart guaranteed reads**: CORE.md · AXIOMS.md · HEURISTICS.md · agent persona · status strip · `session_env_setup` env vars                                             | ~50–500 tok/session, prompt-cached         |
| L2 | base       | **Lifecycle context injection**: UPS hints (`context-map.json`) · hydrator · Stop-hook reminders (IDA, QA-gate, handover-gate)                                                   | ~50–500 tok per event                      |
| L3 | base       | **Voluntary skill invocation**: `/verify` · `/design-rubric` · `/q` · `/pull` · `/learn` · others (agent opts in)                                                                | per-skill, agent decides                   |
| L4 | middle     | **Mechanical checks (deterministic, no LLM)**: pre-commit hooks · bridge guards · `aca_data_autocommit` · `fail_fast_watchdog` · `normalize_mcp_names` · `orchestrator_boundary` | 50ms–2s wall-clock                         |
| L5 | middle     | **PreToolUse classifier**: auto-mode warn rules · auto-mode block rules · `policy_enforcer` hard-deny                                                                            | ~20–800 tok per fire + tool-call latency   |
| L6 | tip        | **LLM-mediated review subagent**: `rbg` · `marsha` · `enforcer` subagent · `alignment`                                                                                           | ~1.5–3k tok + 5–30s latency                |
| L7 | tip (apex) | **Branch protection + merge AND-gates**: branch protection rules · `loop_detector` · `<agent>-status` AND-checks · project-owner / admin approval                                | merge-blocking, irreversible at the moment |

> **Base-tier note.** L1, L2, and L3 are **delivery channels**; within each, the instruction can be tuned across a wide insistence / urgency / visibility / salience / placement spectrum (see [`aops-core/skills/aops/references/enforcement-design.md`](../aops-core/skills/aops/references/enforcement-design.md) — "Within-class Insistence & Placement Spectrum"). "Escalating" a base-tier failure means walking that spectrum (louder → reasoned → relocated → propagated → structured) and propagating the instruction across every failing surface before moving to a heavier tier. Default to instructions; bias hard against new L5+ gates (§4 of [`enforcement.md`](enforcement/enforcement.md)).

## Lifecycle

Which pyramid tiers fire at which event in the session/PR lifecycle. The pyramid says **how invasive**; the lifecycle says **when**.

```mermaid
flowchart LR
  SS[SessionStart]            -->|L1 inject| UPS[UserPromptSubmit]
  UPS                         -->|L2 inject| PTU[PreToolUse]
  PTU                         -->|L4 mech / L5 classifier| TOOL[tool exec]
  TOOL                        -->|L4 mech| PTU2[PostToolUse]
  PTU2                        -->|L2 inject / L6 review| STOP[Stop]
  STOP                        -->|L4 hooks| COM[commit]
  COM                         -->|L4 / L5 / L6| PR[PR push]
  PR                          -->|L6 LLM review| MERGE((merge))
  MERGE                       -.->|L7 AND-gate| Done([done])
  classDef base fill:#e6f3ff,stroke:#1e6091,color:#000
  classDef mid  fill:#fff4d6,stroke:#a76700,color:#000
  classDef tip  fill:#ffe1e1,stroke:#a30000,color:#000
  class SS,UPS,STOP base
  class PTU,PTU2,COM,PR mid
  class MERGE tip
```

L3 (voluntary skill invocation) is omitted from the flow because it's not lifecycle-anchored — agents invoke skills mid-turn at their own discretion.

## Runtime gates

### Gate lifecycle

Each gate is a state machine driven by hook events. Forensic detail → [`specs/GATES.md`](GATES.md).

| Gate     | Starts | Closes when                              | Opens when                                       | Re-arms on       | Policy event           | Policy action                     |
| -------- | ------ | ---------------------------------------- | ------------------------------------------------ | ---------------- | ---------------------- | --------------------------------- |
| enforcer | OPEN   | after n turns (counter-based)            | Calling `enforcer`/`rbg` subagent resets counter | counter reset    | PreToolUse @ threshold | Block non-read/infra tools        |
| qa       | OPEN   | Write tool used, or task → `in_progress` | `marsha`/`qa`/`verify` subagent completes        | UserPromptSubmit | Stop while CLOSED      | Block/warn; demand verifier       |
| handover | OPEN   | Write tool used, or task → `in_progress` | `/end_session`, `/dump`, or `handover` skill     | UserPromptSubmit | Stop while CLOSED      | Block/warn; demand handover       |
| ida      | CLOSED | n/a (always armed)                       | First Stop in turn (fire-once)                   | UserPromptSubmit | Stop while CLOSED      | Inject "show your proof" advisory |

### Gate mode environment variables

| Variable              | Default | Values                 | Controls                  |
| :-------------------- | :------ | :--------------------- | :------------------------ |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | Periodic compliance audit |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | Hydration before work     |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification           |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | Reflection before exit    |
| `IDA_GATE_MODE`       | `warn`  | `warn`, `block`        | Honesty/proof reminder    |

### Session scope

Enforcement is **session-scoped**: every execution context with its own session ID and `SessionStart` event (interactive CLI, background jobs, polecats, GHA workflows) receives the full gate and context-injection stack. Inline subagents spawned via the `Agent` tool share the parent's session ID — gates and context injection are skipped (`ctx.is_subagent` checks in `hooks/router.py`) to avoid double-enforcement and recursive loops. Observability (logging, telemetry) fires unconditionally.

This is policy, not a gap. Claude Code v2.1.69+ (2026-03-05) includes `agent_id` and `agent_type` in hook payloads for subagent-originated tool calls; `is_subagent_session()` in `lib/hook_utils.py` uses these as its primary detection method. Heuristic fallbacks remain for Gemini CLI, which does not provide equivalent fields.

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
| `qa` gate             | L6 | warn/block | Requires verifier subagent before Stop                 | [`GATES.md`](GATES.md)                                                                   |
| `handover` gate       | L6 | warn/block | Blocks Stop until commit + task update + reflection    | [`GATES.md`](GATES.md)                                                                   |
| `ida` gate            | L2 | warn       | Stop-hook inject: back assertions with proof           | [`GATES.md`](GATES.md)                                                                   |
| `hydration` gate      | L4 | warn       | Blocks tool calls until hydrator runs (mode-dependent) | [`GATES.md`](GATES.md)                                                                   |
| `aca_data_autocommit` | L4 | —          | Auto-commits `$ACA_DATA` after state-modifying calls   | `aops-core/hooks/router.py:_run_aca_data_autocommit`                                     |
| `context-map hints`   | L2 | inject     | UPS lifecycle inject from `.agents/context-map.json`   | `aops-core/hooks/router.py:_inject_context_map_hints`                                    |
| ~~`policy_enforcer`~~ | —  | —          | **Retired 2026-05-15** (sandbox supersedes)            | `aops-e0d015d9`                                                                          |
| ~~`commit` gate~~     | —  | —          | **Retired PR #988** (superseded by `handover`)         | —                                                                                        |

### Pre-commit hooks

| Hook                        | L  | Action | Purpose                                                 | Source                                 |
| :-------------------------- | :- | :----- | :------------------------------------------------------ | :------------------------------------- |
| `check-no-new-orphan-md`    | L4 | warn   | New `.md` outside canonical-location allowlist (R5.6)   | `scripts/check_no_new_orphan_md.py`    |
| `check-framework-integrity` | L4 | warn   | Broken wikilinks or missing index entries               | `scripts/check_framework_integrity.py` |
| `check-no-fallbacks`        | L4 | warn   | Silent-fallback patterns in hooks (A8 / P#8; #930)      | `scripts/check_no_fallbacks.py`        |
| `normalize-mcp-names`       | L4 | warn   | Auto-heals Gemini-form MCP names to Claude form (#1128) | `scripts/normalize_mcp_names.py`       |

### Bridge-level constraints

| Constraint                 | L  | Action | Purpose                                       | Source                  |
| :------------------------- | :- | :----- | :-------------------------------------------- | :---------------------- |
| `create_task` prefix guard | L4 | block  | ID prefix must match task type / project slug | `polecat/pkb_bridge.py` |
| `claude` OAUTH pre-flight  | L4 | block  | Exits 4 when `CLAUDE_CODE_OAUTH_TOKEN` unset  | `polecat/cli.py`        |

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

| Agent              | L  | Action | Purpose                                                 | Source                                                                      |
| :----------------- | :- | :----- | :------------------------------------------------------ | :-------------------------------------------------------------------------- |
| `enforcer-status`  | L6 | block  | LLM review of PR diff against axioms; SHA-skip dedupe   | `.github/workflows/agent-enforcer.yml@enforcer-v1`                          |
| `alignment-status` | L6 | block  | LLM review of PKB design-intent alignment               | `.github/workflows/agent-alignment.yml@alignment-v1`                        |
| `mechanic-status`  | L4 | —      | Mechanical merge + conflict resolution only             | `.github/workflows/agent-mechanic.yml@mechanic-v1`                          |
| branch protection  | L7 | block  | AND-gates all required `<agent>-status` checks at merge | GitHub repo settings (admin-configured)                                     |
| `loop_detector`    | L7 | block  | Refuses merge if loop detected in PR-pipeline state     | `.github/workflows/agent-merge-prep.yml` (steps: loop-check, ceiling-check) |
| ~~v1 agents~~      | —  | —      | **Retired Phase 1** (PR #1062)                          | [`pr-pipeline-v2.md`](workflows/pr-pipeline-v2.md) §3.1/§3.6/§5             |

## Related

- [`specs/enforcement/enforcement.md`](enforcement/enforcement.md) — pyramid framing, escalation discipline, PR cost-benefit requirements, worked A7 example.
- [`specs/enforcement/enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md) — per-mechanism reference catalogue.
- [`specs/enforcement/ultra-vires-enforcer.md`](enforcement/ultra-vires-enforcer.md) — enforcer agent + gate internal design.
- [`specs/enforcement/hook-router.md`](enforcement/hook-router.md) — hook router architecture.
- [`.agents/rules/AXIOMS.md`](../.agents/rules/AXIOMS.md) — universal axioms.
- [`.agents/rules/HEURISTICS.md`](../.agents/rules/HEURISTICS.md) — advisory heuristics; P#65 governs map currency.
- [`specs/GATES.md`](GATES.md) — adjacent state SSoT for runtime gate forensic detail.
