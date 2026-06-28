# Enforcement Map

> **State — operative current-state register.** Which **rule** is reinforced by which **mechanism**, at which pyramid level, _right now_. This file is the single source of truth (SSoT) for the macroscopic matrix mapping rules to enforcement triggers, client differences, and gate modes.
>
> **Where things live now (read this if you came looking for prose):** design reasoning — pyramid theory, escalation discipline, CBA, the coercion-vs-cost axis — is in [`enforcement/enforcement.md`](enforcement/enforcement.md). Per-mechanism schema detail (trigger / location / scope / status) is in [`enforcement/enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md). Per-gate forensic detail (config / verify / debug) is in [`enforcement/GATES.md`](enforcement/GATES.md). Hook wire-channel detail (which field reaches user vs agent) is in [`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md). `rbg` blocks on this file's currency (P#65).

---

## 1. Unified SSoT Matrix: Rules, Mechanisms, and Triggers

This matrix is the centralized authoritative register tracking every core rule, how it is enforced (the mechanism), when it fires (trigger), its mode across interactive vs. autonomous surfaces, and any client-specific routing variations.

| Rule (Axiom/Directive)                        | Mechanism / Gate         | Trigger                                            | Level | Mode: Interactive (`junior`) | Mode: Polecat (Background) | Mode: Subagents | Client Routing Notes                                               |
| :-------------------------------------------- | :----------------------- | :------------------------------------------------- | :---- | :--------------------------- | :------------------------- | :-------------- | :----------------------------------------------------------------- |
| `data-boundaries`, `evidence-immutable`       | `sentinel` gate          | **PreToolUse:** destructive verb on protected path | L4    | `block`                      | `block`                    | `block`         | Claude/Gemini: `denyReason` to both. Agy: `denyReason` model-only. |
| `all axioms`                                  | `enforcer` gate          | **PreToolUse:** every N (default 50) write ops     | L4→L6 | `warn` (default)             | `warn` (default)           | `warn`          | Subagent dispatch resets threshold.                                |
| `all axioms`                                  | `rbg-review` gate        | **Stop:** while task is bound                      | L2→L6 | OPEN (inert)                 | `block`                    | `block`         | Held `CLOSED` until `rbg` runs.                                    |
| `exercise-authority`, show-don't-tell         | `qa` gate                | **Stop:** after task claimed `in_progress`         | L2    | `warn`                       | `warn`                     | `warn`          | Reopens when `qa`/`verify`/`marsha` runs.                          |
| `halt-on-failure`                             | `handover` gate          | **Stop:** if work was done (task/write tool)       | L2    | `warn` (merge)               | `block`                    | `warn`          | Reopens when `/end-session` or `/dump` runs.                       |
| `honest-epistemics`                           | `ida` gate               | **Stop:** first stop per turn                      | L2    | `warn`                       | `warn`                     | `warn`          | Fire-once per turn. Claude: `additionalContext` (no block).        |
| `honest-epistemics`, `single-source-of-truth` | `pkb.nudge`              | **UserPromptSubmit**                               | L2    | advisory                     | n/a                        | advisory        | Injected into agent context (Agy: transient `ephemeralMessage`).   |
| `do-one-thing`                                | `hydration.warn`         | **UserPromptSubmit:** main session only            | L2    | advisory                     | n/a                        | advisory        | Routing hints.                                                     |
| `halt-on-failure`, `data-boundaries`          | Safety floor (`CORE.md`) | **SessionStart:** `@`-import                       | L1    | instruction                  | instruction                | instruction     | One injected copy for every surface.                               |

---

## 2. Capability & Identity Restrictions (Tool Access)

Tool and identity restrictions serve as foundational enforcement mechanisms, restricting what agents can do based on their role.

| Restriction Area                       | Enforcement Rule                                                                                                                                              | Applied To                                    |
| :------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ | :-------------------------------------------- |
| **Specialized Execution (Playwright)** | Playwright and heavy e2e testing tools are strictly gated to specialized validation agents (`marsha`), enforcing separation of authoring vs QA.               | Excludes: `junior`, `pauli`, `rbg`            |
| **PKB Knowledge Write**                | While baseline agents (`junior`, `pauli`, `james`, `marsha`, `rbg`) share `mcp__plugin_aops-core_pkb__*` access, writes are constrained by `data-boundaries`. | Enforced via `rbg` review & `data-boundaries` |
| **Baseline Tooling**                   | Universal access to `Bash`, `Edit`, `Grep`, `Read`, `Skill` is granted across interactive (`junior`) and background workers to ensure `full-observability`.   | All Authoring Agents                          |

> **Note on Voluntary Skills (L3)**: Voluntary skills (e.g., `/verify`, `/design-rubric`, `/q`) are **capabilities, not enforcement mechanisms**. The restrictions on their use, and the hooks (like `qa` gate) that remind agents to use them, constitute the actual enforcement.

---

## 3. PR / merge pipeline (current state)

The mechanisms that fire on a PR / at merge. Terse current-state rows; the canonical contract is [`workflows/pr-pipeline.md`](workflows/pr-pipeline.md), per-agent detail is in [`enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md) §L9–L10.

| Mechanism                  | Level | Required at merge?          | What it does                                                                                                                                |
| :------------------------- | :---- | :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| `enforcer-status` (rbg)    | L7    | **yes**                     | LLM axiom review of HEAD diff; auto on PR events, manual `/enforce`. Blocks on CHANGES_REQUESTED/failure.                                   |
| `qa-status` (marsha)       | L7    | **yes**                     | Runtime verification ("broken until proven"); auto on PR events, manual `/qa`/`/verify`.                                                    |
| `admit-status` (human)     | L7    | **yes**                     | The single human "good idea — make it mergeable" approval (a maintainer PR review approval, `admit-on-review.yml`). Arms `--auto --squash`. |
| Lint / Pytest              | L4    | **yes**                     | Mechanical CI.                                                                                                                              |
| `alignment-status` (pauli) | L7    | no — **advisory by design** | PKB design-intent review (NOT axioms). Queue surface live; host dispatch spec-only. Informs the human admit gate.                           |
| `mechanic-status`          | L4    | no — informational          | Post-admission dev + conflict-resolve; `MAX_MECHANIC_RUNS=5`; enforcer+qa re-verify each SHA.                                               |
| `review-attestation`       | L7    | in-ruleset (apply pending)  | Fail-closed proof a _named_ reviewer ran on _this_ SHA.                                                                                     |
| branch protection          | L7    | **yes**                     | AND-gates the required checks (active ruleset `13762049`, API-verified 2026-06-09).                                                         |

> Local/off-pipeline routes to the same agents: `/strategic-review` → james (deploys rbg+pauli+marsha, reconciles APPROVE/REVISE/ESCALATE, advisory); `/verify` → marsha; `/enforce` PR comment → rbg.

---

## Known gaps

- **Axioms are enforced reactively, not delivered always-on** (corrected 2026-06-03). No hook injects the axiom set at SessionStart; no working agent `@`-imports `AXIOMS.md` — only `rbg` does (as its review reference, not "told to obey"). `.agents/CORE.md` restates `halt-on-failure`/`data-boundaries` operationally, and (D1, spec [[mem-438429c5]] §4.1) now carries the **universal safety floor** — Safety Invariants (no credential read/store/broker) + PKB-HALT — as the one injected copy for every surface. **Injection-path caveat (D2 verify gate):** `session_env_setup.py` reads `aops-core/CORE.md`, which does NOT exist in-repo, so in dev/local sessions CORE.md reaches the model via the `@`-import in `CLAUDE.md`/`GEMINI.md`, not that hook read. Confirming the safety floor actually reaches a **polecat** requires verifying WHICH path carries CORE.md into the container and OBSERVING the prose in a real polecat transcript — the D2 hard gate that must be GREEN before `junior.md`'s per-agent safety copy is removed (D3). Enforcement is the periodic enforcer gate + the per-rule rows in [Unified Matrix](#1-unified-ssot-matrix-rules-mechanisms-and-triggers). QA tracker: `aops-98c7ce49`.
- **Auto-mode classifier wired but unseeded** (L5). `autoMode` rules absent by deliberate 2026-06-04 decision — instruction tier walked first; a rule is seeded only on measurement showing instruction insufficient. Canonical: [`auto-mode-classifier.md`](enforcement/auto-mode-classifier.md).
- **Hydration / commit gates**: env vars wired (`HYDRATION_GATE_MODE`, `COMMIT_GATE_MODE`) but no `GateConfig` body — stubs.
- **Evidence loop steps 4–5** (`/aops` pattern detection → recommendation) aspirational; capture (step 2 `/learn`) and implementation (step 6) exist. Step 7 auto-map-update is manual.
- **`orchestrator-boundary-warn.md`** — template file not in `TEMPLATE_SPECS`; likely dead/unwired (cleanup follow-up).
- **PTY harness coverage** — measures Claude user-visibility + Stop agent-context; agy wire-acceptance, `--resume` persistence, and a model-echo agent-context lane for UPS/PreToolUse are not yet ported (`scripts/pty_hook_probe.py` is `client`-parameterized for it).
