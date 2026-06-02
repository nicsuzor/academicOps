# Enforcement Map

> **State.** Routing table for "how is each rule currently enforced?". Any PR that adds, escalates, or retires a mechanism updates a row here in the same change (P#65); `rbg` blocks on currency.
>
> Framing, escalation discipline, PR cost-benefit, and the worked A7 example → [`specs/enforcement/enforcement.md`](enforcement/enforcement.md). Per-gate forensic detail (config, verify, debug) → [`specs/GATES.md`](GATES.md). Both adjacent files are state.

## Axiom × mechanism map

Which mechanism(s) catch a given axiom, what they do when they fire, where in the session lifecycle.

| RULE                                                      | SURFACE      | EXACT TRIGGER                                                     | WORKFLOW IMPACT                               |
| :-------------------------------------------------------- | :----------- | :---------------------------------------------------------------- | :-------------------------------------------- |
| A1 Closure (Require explicit state conclusion)            | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A2 Gen (No premature abstraction)                         | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A2 Gen (No premature abstraction)                         | session      | aops-skill pre-impl phase invocation                              | advises on design generalisation              |
| A3 Epistemic (Only assert what you can verify)            | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A3 Epistemic (Only assert what you can verify)            | session      | `release_task` invocation                                         | blocks task closure until proof is supplied   |
| A4 Citations (Provide exact evidence for claims)          | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A4 Citations (Provide exact evidence for claims)          | tool-call    | PreToolUse (auto-mode classifier match)                           | warns agent before tool execution             |
| A4 Citations (Provide exact evidence for claims)          | session      | `/learn` invocation                                               | blocks submission if RCA schema is missing    |
| A5 SSOT (Single source of truth)                          | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A5 SSOT (Single source of truth)                          | tool-call    | PreToolUse (auto-mode classifier match)                           | warns agent before tool execution             |
| A5 SSOT (Single source of truth)                          | session      | `find_duplicates` invocation                                      | provides advisory findings                    |
| A6 Scope (Stay strictly within requested bounds)          | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A6 Scope (Stay strictly within requested bounds)          | session      | TodoWrite invocation                                              | injects reminder into task                    |
| A6 Scope (Stay strictly within requested bounds)          | tool-call    | PreToolUse (auto-mode classifier match)                           | warns agent before tool execution             |
| A6 Scope (Stay strictly within requested bounds)          | tool-call    | PreToolUse (>50 calls or >$1)                                     | warns agent before tool execution             |
| A6 Scope (Stay strictly within requested bounds)          | tool-call    | PostToolUse                                                       | warns agent after tool execution              |
| A6 Scope (Stay strictly within requested bounds)          | tool-call    | PreToolUse (enforcer threshold)                                   | blocks or warns on non-read/infra tools       |
| A6 Scope (Stay strictly within requested bounds)          | GitHub PR    | PR push                                                           | warns change-author                           |
| A7 Authority (Exercise calibrated capability)             | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A7 Authority (Exercise calibrated capability)             | tool-call    | PreToolUse (auto-mode classifier match)                           | warns agent before tool execution             |
| A7 Authority (Exercise calibrated capability)             | GitHub PR    | PR push                                                           | warns change-author                           |
| A7 Authority (Exercise calibrated capability)             | session      | Stop-hook while QA gate is CLOSED                                 | blocks Stop until verifier subagent completes |
| A8 Halt (Stop and report when unable to proceed safely)   | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A8 Halt (Stop and report when unable to proceed safely)   | tool-call    | PreToolUse (auto-mode classifier match)                           | blocks tool execution                         |
| A8 Halt (Stop and report when unable to proceed safely)   | tool-call    | PreToolUse (auto-mode classifier match)                           | warns agent before tool execution             |
| A8 Halt (Stop and report when unable to proceed safely)   | tool-call    | PreToolUse                                                        | hard-denies tool execution                    |
| A8 Halt (Stop and report when unable to proceed safely)   | tool-call    | PostToolUse                                                       | warns agent after tool execution              |
| A8 Halt (Stop and report when unable to proceed safely)   | local commit | pre-commit                                                        | warns author                                  |
| A8 Halt (Stop and report when unable to proceed safely)   | GitHub PR    | PR merge attempt                                                  | blocks auto-merge until resolved              |
| A9 Boundary (Never modify files outside current git repo) | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A9 Boundary (Never modify files outside current git repo) | session      | SessionStart                                                      | hard-denies credential access                 |
| A9 Boundary (Never modify files outside current git repo) | tool-call    | PreToolUse (auto-mode classifier match)                           | blocks tool execution                         |
| A9 Boundary (Never modify files outside current git repo) | tool-call    | PreToolUse                                                        | hard-denies env execution                     |
| A9 Boundary (Never modify files outside current git repo) | local commit | pre-commit                                                        | warns author                                  |
| A9 Boundary (Never modify files outside current git repo) | GitHub PR    | PR merge attempt                                                  | blocks auto-merge until resolved              |
| A10 Immut (Never alter historical records)                | session      | always-on (SessionStart load)                                     | injects instruction into prompt context       |
| A10 Immut (Never alter historical records)                | tool-call    | PreToolUse (globs: `**/records/**`, `$ACA_DATA/records/**`, etc.) | blocks tool execution                         |
| A10 Immut (Never alter historical records)                | tool-call    | PreToolUse                                                        | hard-denies tool execution                    |

### PR review pipeline

The mechanisms that fire on a PR / at merge. Same column shape as the axiom map above. Where a mechanism reviews **all** axioms (it is not keyed to one), `RULE` is the shorthand `Verify AXIOM compliance` rather than a per-axiom enumeration. The above per-axiom GitHub-PR rows that simply restated "PR push or `/review-pr` advises on axiom X" have been folded into the `Verify AXIOM compliance` rows here; the genuinely axiom-specific PR rows (A6/A7 `PR push → warns change-author`; A8/A9 `PR merge attempt → blocks auto-merge`) remain in the axiom map. **This subsection reflects what is deployed today (v1 hybrid + enforcer-v1); planned v2 phases are listed separately below and are NOT live gates.**

| RULE                                        | SURFACE                                 | EXACT TRIGGER                                                                                         | WORKFLOW IMPACT                                                                                                                                                                                                     |
| :------------------------------------------ | :-------------------------------------- | :---------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Verify AXIOM compliance                     | GitHub PR — GHA `enforcer-status` (rbg) | PR opened/synchronize/ready_for_review/reopened, `/enforce` comment, or manual dispatch; per-SHA skip | rbg reviews HEAD diff vs AXIOMS.md; posts `enforcer-status` (success/failure/pending) + "Enforcer Review" PR review; required check → blocks merge on CHANGES_REQUESTED/failure                                     |
| Verify AXIOM compliance                     | session — local `/review-pr` → james    | `/review-pr` invocation                                                                               | james orchestrates rbg+pauli+marsha; advisory APPROVE/REVISE/ESCALATE to change-author; non-blocking (runs in the dev session, not GHA)                                                                             |
| A3 Epistemic + A7 Authority                 | session — marsha / qa / verify subagent | `/verify` or `qa` invocation                                                                          | marsha verifies completion claims against the original request (A3) + catches criterion substitution / over-deference (A7); advisory PASS/FAIL/REVISE (axiom-specific — delegates formal compliance to rbg)         |
| A8 Halt                                     | GitHub PR — GHA merge-prep loop ceiling | each merge-prep run; `MAX_MERGE_PREP_RUNS=5`                                                          | counts `Merge-Prep-By:` commits on the branch; at ceiling dismiss bot approval + set `merge-prep-status` failure → blocks merge                                                                                     |
| merge-prep `merge-prep-status` triage       | GitHub PR — GHA agent-merge-prep (v1)   | PR events (`opened/synchronize/ready_for_review/reopened`) + cron bazaar window (~15 min)             | rebase / conflict-resolve, bot-approve the PR, set `merge-prep-status`, enable auto-merge; self-loop detection; required check                                                                                      |
| Verify AXIOM compliance (enforced at merge) | GitHub PR — branch protection ruleset   | merge attempt                                                                                         | AND-gates required checks ("Lint / Lint", "Pytest / Pytest", `merge-prep-status`, `enforcer-status`) + 2 approving reviews (merge-prep bot + human); merge blocked until all pass + Nic's human approval on the SHA |

**Planned (NOT deployed — do not treat as live gates):** `alignment-status` (pauli, **Phase 2** — no `agent-alignment.yml`, no host dispatcher yet); `mechanic-status` (**Phase 3** — no `agent-mechanic.yml`; merge-prep v1 still does triage); `qa-status` (marsha, **Phase 6+** — not a GHA check; marsha runs locally via `/verify`). Phasing per [`pr-pipeline-v2.md`](workflows/pr-pipeline-v2.md) §9.

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

## Known gaps

- **Hydration**: parent skip cascades to child; missing hydration/commit gate bodies.
- **Reactive**: PostToolUse on tool error is `planned` (Phase 2).
- **QA**: gate active (close-on-work-begin landed); requirements still freeform — verifier prompt reviews session narrative, no structured acceptance-criteria source yet.
- **Settings**: global/user rules unverifiable from this repo.
- **Evidence Loop**: Steps 4-5 (pattern detection) and Step 7 (auto-map update) partial/unbuilt.
- **Subagent enforcement**: gates and context injection skipped for `is_subagent` sessions — this is by policy, not a gap. See [`enforcement.md` Session scope](enforcement/enforcement.md#session-scope).
- **Design-intent / alignment review at the PR gate**: NOT enforced yet (Phase 2 — `alignment-status`). Pauli cannot run from GHA (no PKB MCP reachability), so the alignment verdict is missing entirely from the merge gate. This is pathology **P3** in [`pr-pipeline-v2.md`](workflows/pr-pipeline-v2.md). Only `enforcer-status` (axiom review) and the mechanical checks gate the merge today.
- **QA at the PR gate**: `qa-status` is **local-only** — marsha runs via `/verify` in the dev session and is advisory; it is **not** a GHA check on the merge gate (Phase 6+).
- **Merge gate is a v1 hybrid**: branch protection still requires `merge-prep-status` and `required_approving_review_count: 2` (merge-prep bot + human). The v2 target (mechanic-only, count → 1) is pending Phase 3; until then merge-prep v1 retains its triage/approval/auto-merge role.
