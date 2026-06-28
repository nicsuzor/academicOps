# Enforcement Map

> **State — operative current-state register.** Which **rule** is reinforced by which **mechanism**, at which pyramid level, _right now_. This file is the single source of truth (SSoT) for the macroscopic matrix mapping rules to enforcement triggers, client differences, and gate modes.
>
> **Where things live now (read this if you came looking for prose):** design reasoning — pyramid theory, escalation discipline, CBA, the coercion-vs-cost axis — is in [`enforcement/enforcement.md`](enforcement/enforcement.md). Per-mechanism schema detail (trigger / location / scope / status) is in [`enforcement/enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md). Per-gate forensic detail (config / verify / debug) is in [`enforcement/GATES.md`](enforcement/GATES.md). Hook wire-channel detail (which field reaches user vs agent) is in [`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md). `rbg` blocks on this file's currency (P#65).

---

## 1. Unified SSoT Matrix: Rules, Mechanisms, and Triggers

This matrix is the centralized authoritative register tracking every core rule, how it is enforced (the mechanism), when it fires (trigger), its mode across interactive vs. autonomous surfaces, and any client-specific routing variations.

| Rule (Axiom/Directive)                        | Mechanism / Gate            | Trigger                                            | Gate Mode (Interactive / Polecat) | Client Routing Notes                                               |
| :-------------------------------------------- | :-------------------------- | :------------------------------------------------- | :-------------------------------- | :----------------------------------------------------------------- |
| `data-boundaries`, `evidence-immutable`       | `sentinel` gate (L4)        | **PreToolUse:** destructive verb on protected path | `block` / `block`                 | Claude/Gemini: `denyReason` to both. Agy: `denyReason` model-only. |
| `all axioms`                                  | `enforcer` gate (L4→L6)     | **PreToolUse:** every N (default 50) write ops     | `warn` / `warn` (default)         | Subagent dispatch resets threshold.                                |
| `all axioms`                                  | `rbg-review` gate (L2→L6)   | **Stop:** while task is bound (polecat/crew only)  | OPEN (inert) / `block`            | Held `CLOSED` until `rbg` runs.                                    |
| `exercise-authority`, show-don't-tell         | `qa` gate (L2→tip)          | **Stop:** after task claimed `in_progress`         | `warn` / `warn`                   | Reopens when `qa`/`verify`/`marsha` runs.                          |
| `halt-on-failure`                             | `handover` gate (L2→tip)    | **Stop:** if work was done (task/write tool)       | `warn` (merge) / `block`          | Reopens when `/end-session` or `/dump` runs.                       |
| `honest-epistemics`                           | `ida` gate (L2→tip)         | **Stop:** first stop per turn                      | `warn` / `warn`                   | Fire-once per turn. Claude: `additionalContext` (no block).        |
| `honest-epistemics`, `single-source-of-truth` | `pkb.nudge` (L2)            | **UserPromptSubmit**                               | n/a (advisory only)               | Injected into agent context (Agy: transient `ephemeralMessage`).   |
| `do-one-thing`                                | `hydration.warn` (L2)       | **UserPromptSubmit:** main session only            | n/a (advisory only)               | Routing hints.                                                     |
| `halt-on-failure`, `data-boundaries`          | Safety floor (`CORE.md` L1) | **SessionStart:** `@`-import                       | n/a (instruction)                 | One injected copy for every surface.                               |

---

112:## 3. Pyramid placement register (L0–L7)
113-
114-The register-of-record for **where each mechanism sits** (escalation/coercion axis; width = volume × frequency). PRs that add/escalate/remove a mechanism cite its position and justify it against [`enforcement.md`](enforcement/enforcement.md) §4.1. The **cost axis** (coercion ≠ cost; the auto-mode-classifier and chokepoint rungs) is design reasoning and lives in [`enforcement.md`](enforcement/enforcement.md) §4.0 — not here.
115-
116-| L | Class | Mechanism categories | Per-fire cost |
117-| -- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
118-| L0 | base | Authoring memory: PKB notes · comments · doc-strings | ~0 |
119-| L1 | base | SessionStart guaranteed reads: persona · status strip · `session_env_setup` · `.agents/CORE.md` (`@`-import). **NOT** `AXIOMS.md` (rbg-only) | ~50–500 tok/session, cached |
120-| L2 | base | Lifecycle context injection: UPS hints · hydrator · Stop-hook reminders (ida, qa-gate, handover-gate) | ~50–500 tok/event |
121-| L3 | base | Voluntary skill invocation: `/verify` · `/design-rubric` · `/q` · `/pull` · `/dispatch` · `/learn` | per-skill, agent decides |
122-| L4 | middle | Mechanical checks (deterministic): pre-commit hooks · bridge guards · `aca_data_autocommit` · `policy_enforcer` hard-deny · settings deny rules · **least-privilege chokepoint** (last-resort) | 50ms–2s |
123-| L5 | middle | Judgment per-action gate (LLM): auto-mode classifier — `soft_deny`/`hard_deny`. **Narrow reserved / measurement-gated** (see Cost axis in enforcement.md) | ~20–800 tok/fire + latency |
124-| L6 | tip | LLM-mediated review subagent: `rbg` · `marsha` · `enforcer` subagent · `alignment` | ~1.5–3k tok + 5–30s |
125-| L7 | tip (apex) | Branch protection + merge AND-gates: `<agent>-status` checks · `loop_detector` · human admit approval | merge-blocking |
126-
127-> **Base-tier note.** L1/L2/L3 are **delivery channels**; "escalating" a base-tier failure means walking the within-class insistence/placement spectrum (louder → reasoned → relocated → propagated → structured) _before_ crossing to a heavier class. Default to instructions; bias hard against new L5+ gates. See [`enforcement.md`](enforcement/enforcement.md) §4 and [`aops-core/skills/aops/references/enforcement-design.md`](../aops-core/skills/aops/references/enforcement-design.md).
128-
129----
130-
131-## 4. PR / merge pipeline (current state)
132-
133-The mechanisms that fire on a PR / at merge. Terse current-state rows; the canonical contract is [`workflows/pr-pipeline.md`](workflows/pr-pipeline.md), per-agent detail is in [`enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md) §L9–L10.
134-
135-| Mechanism | Level | Required at merge? | What it does |
136-| :------------------------- | :---- | :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
137-| `enforcer-status` (rbg) | L6 | **yes** | LLM axiom review of HEAD diff; auto on PR events, manual `/enforce`. Blocks on CHANGES_REQUESTED/failure. |
138-| `qa-status` (marsha) | L6 | **yes** | Runtime verification ("broken until proven"); auto on PR events, manual `/qa`/`/verify`. |
139-| `admit-status` (human) | L7 | **yes** | The single human "good idea — make it mergeable" approval (a maintainer PR review approval, `admit-on-review.yml`). Arms `--auto --squash`. |
140-| Lint / Pytest | L4 | **yes** | Mechanical CI. |
141-| `alignment-status` (pauli) | L6 | no — **advisory by design** | PKB design-intent review (NOT axioms). Queue surface live; host dispatch spec-only. Informs the human admit gate. |
142-| `mechanic-status` | L4 | no — informational | Post-admission dev + conflict-resolve; `MAX_MECHANIC_RUNS=5`; enforcer+qa re-verify each SHA. |
143-| `review-attestation` | L7 | in-ruleset (apply pending) | Fail-closed proof a _named_ reviewer ran on _this_ SHA. |
144-| branch protection | L7 | **yes** | AND-gates the required checks (active ruleset `13762049`, API-verified 2026-06-09). |
145-
146-> Local/off-pipeline routes to the same agents: `/strategic-review` → james (deploys rbg+pauli+marsha, reconciles APPROVE/REVISE/ESCALATE, advisory); `/verify` → marsha; `/enforce` PR comment → rbg.
147-
148----
149-
150-## Known gaps
151-
152-- **Axioms are enforced reactively, not delivered always-on** (corrected 2026-06-03). No hook injects the axiom set at SessionStart; no working agent `@`-imports `AXIOMS.md` — only `rbg` does (as its review reference, not "told to obey"). `.agents/CORE.md` restates `halt-on-failure`/`data-boundaries` operationally, and (D1, spec [[mem-438429c5]] §4.1) now carries the **universal safety floor** — Safety Invariants (no credential read/store/broker) + PKB-HALT — as the one injected copy for every surface. **Injection-path caveat (D2 verify gate):** `session_env_setup.py` reads `aops-core/CORE.md`, which does NOT exist in-repo, so in dev/local sessions CORE.md reaches the model via the `@`-import in `CLAUDE.md`/`GEMINI.md`, not that hook read. Confirming the safety floor actually reaches a **polecat** requires verifying WHICH path carries CORE.md into the container and OBSERVING the prose in a real polecat transcript — the D2 hard gate that must be GREEN before `junior.md`'s per-agent safety copy is removed (D3). Enforcement is the periodic enforcer gate + the per-rule rows in [Unified Matrix](#1-unified-ssot-matrix-rules-mechanisms-and-triggers). QA tracker: `aops-98c7ce49`.
153-- **Auto-mode classifier wired but unseeded** (L5). `autoMode` rules absent by deliberate 2026-06-04 decision — instruction tier walked first; a rule is seeded only on measurement showing instruction insufficient. Canonical: [`auto-mode-classifier.md`](enforcement/auto-mode-classifier.md).
154-- **Hydration / commit gates**: env vars wired (`HYDRATION_GATE_MODE`, `COMMIT_GATE_MODE`) but no `GateConfig` body — stubs.
155-- **Evidence loop steps 4–5** (`/aops` pattern detection → recommendation) aspirational; capture (step 2 `/learn`) and implementation (step 6) exist. Step 7 auto-map-update is manual.
156-- **`orchestrator-boundary-warn.md`** — template file not in `TEMPLATE_SPECS`; likely dead/unwired (cleanup follow-up).
157-- **PTY harness coverage** — measures Claude user-visibility + Stop agent-context; agy wire-acceptance, `--resume` persistence, and a model-echo agent-context lane for UPS/PreToolUse are not yet ported (`scripts/pty_hook_probe.py` is `client`-parameterized for it).
