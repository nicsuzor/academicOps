# Enforcement Map

> **State — operative current-state register.** Which **rule** is reinforced by which **mechanism**, at which pyramid level, _right now_. This file is the single source of truth (SSoT) for the macroscopic matrix mapping rules to enforcement triggers, client differences, and gate modes.
>
> **Where things live now (read this if you came looking for prose):** design reasoning — pyramid theory, escalation discipline, CBA, the coercion-vs-cost axis — is in [`enforcement/enforcement.md`](enforcement/enforcement.md). Per-mechanism schema detail (trigger / location / scope / status) is in [`enforcement/enforcement-mechanisms.md`](enforcement/enforcement-mechanisms.md). Per-gate forensic detail (config / verify / debug) is in [`enforcement/GATES.md`](enforcement/GATES.md). Hook wire-channel detail (which field reaches user vs agent) is in [`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md). `rbg` blocks on this file's currency (P#65).

---

## 1. Unified SSoT Matrix: Rules, Mechanisms, and Triggers

This matrix is the centralized authoritative register tracking every core rule, how it is enforced (the mechanism), when it fires (trigger), its mode across interactive vs. autonomous surfaces, and any client-specific routing variations.

| Rule (Axiom/Directive)                           | Mechanism / Gate                                | Trigger                                                 | Level | Mode: Interactive (`junior`) | Mode: Polecat (Background) | Mode: Subagents | Client Routing Notes                                               |
| :----------------------------------------------- | :---------------------------------------------- | :------------------------------------------------------ | :---- | :--------------------------- | :------------------------- | :-------------- | :----------------------------------------------------------------- |
| `data-boundaries`, `evidence-immutable`          | `sentinel` gate                                 | **PreToolUse:** destructive verb on protected path      | L4    | `block`                      | `block`                    | `block`         | Claude/Gemini: `denyReason` to both. Agy: `denyReason` model-only. |
| `all axioms`                                     | `enforcer` gate                                 | **PreToolUse:** every N (default 50) write ops          | L4→L6 | `warn` (default)             | `warn` (default)           | `warn`          | Subagent dispatch resets threshold.                                |
| `all axioms`                                     | `rbg-review` gate                               | **Stop:** while task is bound                           | L2→L6 | OPEN (inert)                 | `block`                    | `block`         | Held `CLOSED` until `rbg` runs.                                    |
| `exercise-authority`, show-don't-tell            | `qa` gate                                       | **Stop:** after task claimed `in_progress`              | L2    | `warn`                       | `warn`                     | `warn`          | Reopens when `qa`/`verify`/`marsha` runs.                          |
| `halt-on-failure`                                | `handover` gate                                 | **Stop:** if work was done (task/write tool)            | L2    | `warn` (merge)               | `block`                    | `warn`          | Reopens when `/end-session` or `/dump` runs.                       |
| `honest-epistemics`                              | `ida` gate                                      | **Stop:** first stop per turn                           | L2    | `warn`                       | `warn`                     | `warn`          | Fire-once per turn. Claude: `additionalContext` (no block).        |
| `honest-epistemics`, `single-source-of-truth`    | `pkb.nudge`                                     | **UserPromptSubmit**                                    | L2    | advisory                     | n/a                        | advisory        | Injected into agent context (Agy: transient `ephemeralMessage`).   |
| `do-one-thing`                                   | `hydration.warn`                                | **UserPromptSubmit:** main session only                 | L2    | advisory                     | n/a                        | advisory        | Routing hints.                                                     |
| `halt-on-failure`, `data-boundaries`             | Safety floor (`CORE.md`)                        | **SessionStart:** `@`-import                            | L1    | instruction                  | instruction                | instruction     | One injected copy for every surface.                               |
| `single-source-of-truth` (related-work cohesion) | `enforcer`/`rbg` review + `cohesive-pr-epic.md` | **PR-time:** a coupled task set must share ONE draft PR | L7    | review                       | review                     | review          | `junior.md` pointer is always-on (#2004).                          |

### 1.1 Per-message routing (agent-first)

Every hook message is enforcement **directed at the agent** — the **agent channel is non-negotiable and always present** (the `Agent template` column, which is the `CONTEXT_INJECTION` template the agent reads). What is _optional_ is whether anything also reaches the **user terminal**:

- **`silent`** — nothing rendered to the user; the agent handles it.
- **`same`** — the user sees the same text the agent sees (no separate template).
- **`[[file]]`** — a user-specific `USER_MESSAGE` template (the linked `*.policy_message` file).

**`Ephemeral→agent`** is the _target_ delivery discipline: push the full instruction to the agent **ephemerally** (transient) and leave only the **outcome + which hook fired** in the durable transcript. Supported today on agy (`injectSteps[].ephemeralMessage`, P✗); on Claude `additionalContext` still persists (P✓), so `✓` rows are aspirational there pending the Claude Stop-inject retirement ([`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md) P4). Channel wire-fields per client live in [`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md); this table owns the **disposition** (who-sees-what), not the wire mechanics.

**Δ** marks a proposed change from current behaviour (the `*.policy_message` currently renders to the user).

| Gate · fire (event)                           | Agent template (always)                                                                      | User message                                                                                                 | Ephemeral→agent | Notes                                                                                 |
| :-------------------------------------------- | :------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- | :-------------- | :------------------------------------------------------------------------------------ |
| `sentinel` · deny (PreToolUse)                | [sentinel-policy-context](../aops-core/hooks/templates/sentinel-policy-context.md)           | `same`                                                                                                       | ✗ (durable)     | Hard-deny on a protected path — the **one** case the user genuinely needs the banner. |
| `enforcer` · block (PreToolUse)               | [enforcer-policy-context](../aops-core/hooks/templates/enforcer-policy-context.md)           | **Δ `silent`** (was [enforcer-policy-message](../aops-core/hooks/templates/enforcer-policy-message.md))      | ✓               | Periodic compliance plumbing; outcome + hook in transcript only.                      |
| `enforcer` · countdown (PreToolUse run-up)    | —                                                                                            | **Δ `silent`** (was [enforcer-countdown](../aops-core/hooks/templates/enforcer-countdown.md))                | n/a             | "N calls until the check" is pure user noise — drop from the user surface.            |
| `enforcer` · dispatch (PreToolUse)            | [enforcer-instruction](../aops-core/hooks/templates/enforcer-instruction.md)                 | `silent`                                                                                                     | ✓               | Instruction to invoke the enforcer subagent.                                          |
| `qa` · block (Stop)                           | [qa-policy-context](../aops-core/hooks/templates/qa-policy-context.md)                       | **Δ `silent`†** (was [qa-policy-message](../aops-core/hooks/templates/qa-policy-message.md))                 | ✓†              | "Verify before you stop" is agent-directed.                                           |
| `handover` · block (Stop)                     | [stop-gate-handover-block](../aops-core/hooks/templates/stop-gate-handover-block.md)         | **Δ `silent`†** (was [handover-policy-message](../aops-core/hooks/templates/handover-policy-message.md))     | ✓†              | Agent-directed handover instruction.                                                  |
| `ida` · reminder (Stop)                       | [ida-reminder](../aops-core/hooks/templates/ida-reminder.md)                                 | **Δ `silent`†** (was [ida-policy-message](../aops-core/hooks/templates/ida-policy-message.md))               | ✓†              | Fires **every turn** — the biggest user-noise reduction.                              |
| `ida` · AskUserQuestion nudge (PreToolUse)    | [ida-askuserquestion-reminder](../aops-core/hooks/templates/ida-askuserquestion-reminder.md) | `silent`                                                                                                     | ✓               | Already agent-only.                                                                   |
| `rbg_review` · block (Stop)                   | [rbg-review-policy-context](../aops-core/hooks/templates/rbg-review-policy-context.md)       | **Δ `silent`†** (was [rbg-review-policy-message](../aops-core/hooks/templates/rbg-review-policy-message.md)) | ✓†              | Polecat/crew-only, agent-directed.                                                    |
| `rbg_review` · degraded escape-hatch (Stop)   | —                                                                                            | `keep` ([rbg-review-degraded](../aops-core/hooks/templates/rbg-review-degraded.md))                          | n/a             | Loud **by design** (5 Stop-blocks/turn) — the user **should** see this fired.         |
| `pkb` · nudge (UserPromptSubmit)              | [pkb-nudge](../aops-core/hooks/templates/pkb-nudge.md)                                       | `silent`                                                                                                     | ✓               | Already agent-only.                                                                   |
| `hydration` · routing hint (UserPromptSubmit) | [hydration-gate-warn](../aops-core/hooks/templates/hydration-gate-warn.md)                   | **Δ `silent`**                                                                                               | ✓               | Routing hints are agent-directed; reclassify `USER_MESSAGE`→`CONTEXT_INJECTION`.      |

**Status / transition pings** (`allow` verdict — informational, not enforcement). Default `silent` to cut reassurance noise; the agent already knows the gate cleared:

| Ping                        | User message   | Notes                                             |
| :-------------------------- | :------------- | :------------------------------------------------ |
| `enforcer.verified` (reset) | **Δ `silent`** | Counter reset — agent-internal.                   |
| `qa.complete`               | **Δ `silent`** | Verifier ran.                                     |
| `handover.bound`            | **Δ `silent`** | Task bound.                                       |
| `handover.complete`         | `keep`         | Session-end confirmation — user-useful, low-rate. |
| `rbg_review.complete`       | **Δ `silent`** | rbg ran, gate cleared.                            |

> **† Stop-gate caveat (read before trusting the `silent` / ephemeral cells).** A disposition is an _intent_; whether it is achievable depends on the client **and the hook event** — see §1.2. The four `silent†` rows are **only honoured on agy**. On Claude/Gemini there is **no agent-only Stop channel**: every agent-visible Stop payload is _also_ user-visible (Claude `additionalContext` renders `Stop hook feedback:`/`Stop hook error:`; Gemini must block, `reason` U✓). To make these truly `silent`-to-user the reminder must be **relocated off `Stop` onto the next `UserPromptSubmit`** (`additionalContext`, U✗) — a re-architecture, not a template flip. The `✓†` ephemeral cells are likewise agy-native only.

### 1.2 Disposition achievability by client × event

The disposition in §1.1 is an _intent_; this is whether an **agent-visible-but-user-`silent`** payload is achievable on each surface. The trap: the **same wire field changes user-visibility by event** — Claude `additionalContext` is `U✗` on UPS/PreToolUse but `U✓` on **Stop** (PTY-measured, [`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md)).

| Event class                    | Claude                                                           | Gemini                                      | agy                                           |
| :----------------------------- | :--------------------------------------------------------------- | :------------------------------------------ | :-------------------------------------------- |
| **UserPromptSubmit**           | `additionalContext` U✗ → **silent ✓**                            | `additionalContext` U✗ → **✓**              | `ephemeralMessage` U✗ → **✓ (native)**        |
| **PreToolUse — advisory/warn** | `additionalContext` U✗ → **✓**                                   | `additionalContext` U✗ → **✓**              | **n/a** — no inject channel (renderer raises) |
| **PreToolUse — deny**          | `permissionDecisionReason` **U✓** → can't hide                   | `reason` **U✓** → can't hide                | `denyReason` U✗ → **silent ✓**                |
| **Stop**                       | `additionalContext`/`reason` **U✓** (warn+block) → **no silent** | must block; `reason` **U✓** → **no silent** | `ephemeralMessage` U✗ → **✓ (native)**        |

Consequences for §1.1: (1) **`silent` on Stop = agy-only** today (the `†` rows). (2) **`same`** is only truly dual-channel on Claude/Gemini; agy has one model-facing stream, so `same` **degrades to silent-to-user** there. (3) **`ephemeral→agent`** is **agy-native only** — Claude/Gemini `additionalContext` _persists_ (P✓), so every `✓` in that column is aspirational on those clients pending the Claude Stop-inject retirement ([`CLIENT-TRANSLATION.md`](CLIENT-TRANSLATION.md) P4).

> **Out of scope:** `SUBAGENT_INSTRUCTION` templates (`enforcer.context`, `qa.context`, `enforcer.audit`, `rbg_review.context`) reach **neither** the user nor the main agent — they are written to the temp file a _dispatched_ subagent reads. No user/agent disposition applies.

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

| Mechanism                  | Level | Required at merge?          | What it does                                                                                                                                                                                                                                                   |
| :------------------------- | :---- | :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enforcer-status` (rbg)    | L7    | **yes**                     | LLM axiom review of HEAD diff; auto on PR events, manual `/enforce`. Blocks on CHANGES_REQUESTED/failure.                                                                                                                                                      |
| `qa-status` (marsha)       | L7    | **yes**                     | Runtime verification ("broken until proven"); auto on PR events, manual `/qa`/`/verify`.                                                                                                                                                                       |
| `admit-status` (human)     | L7    | **yes**                     | The single human "good idea — make it mergeable" approval (a maintainer PR review approval, `admit-on-review.yml`). Arms `--auto --squash`.                                                                                                                    |
| Lint / Pytest              | L4    | **yes**                     | Mechanical CI.                                                                                                                                                                                                                                                 |
| `alignment-status` (pauli) | L7    | no — **advisory by design** | PKB design-intent review (NOT axioms). Queue surface live; host dispatch spec-only. Informs the human admit gate.                                                                                                                                              |
| `responder-status`         | L4    | no — informational          | Pre-admission mechanical fix: typos, failing CI (PR-attributable `Pytest` red; base-broken guard, #1965). NOT merge conflicts — a conflicting PR never reaches it (`workflows/pr-pipeline.md` §3.11). `MAX_RESPONDER_RUNS=3`; judgment calls surface to human. |
| `mechanic-status`          | L4    | no — informational          | Post-admission dev + conflict-resolve — the ONLY conflict resolver; a conflicting PR is reached only via the conflict-admission sweep (`workflows/pr-pipeline.md` §3.11). `MAX_MECHANIC_RUNS=5`; enforcer+qa re-verify each SHA.                               |
| `review-attestation`       | L7    | in-ruleset (apply pending)  | Fail-closed proof a _named_ reviewer ran on _this_ SHA.                                                                                                                                                                                                        |
| branch protection          | L7    | **yes**                     | AND-gates the required checks (active ruleset `13762049`, API-verified 2026-06-09).                                                                                                                                                                            |

> Local/off-pipeline routes to the same agents: `/strategic-review` → james (deploys rbg+pauli+marsha, reconciles APPROVE/REVISE/ESCALATE, advisory); `/verify` → marsha; `/enforce` PR comment → rbg.

---

## Known gaps

- **Axioms are enforced reactively, not delivered always-on** (corrected 2026-06-03). No hook injects the axiom set at SessionStart; no working agent `@`-imports `AXIOMS.md` — only `rbg` does (as its review reference, not "told to obey"). `.agents/CORE.md` restates `halt-on-failure`/`data-boundaries` operationally, and (D1, spec [[mem-438429c5]] §4.1) now carries the **universal safety floor** — Safety Invariants (no credential read/store/broker) + PKB-HALT — as the one injected copy for every surface. **Injection-path caveat (D2 verify gate):** `session_env_setup.py` reads `aops-core/CORE.md`, which does NOT exist in-repo, so in dev/local sessions CORE.md reaches the model via the `@`-import in `CLAUDE.md`/`GEMINI.md`, not that hook read. Confirming the safety floor actually reaches a **polecat** requires verifying WHICH path carries CORE.md into the container and OBSERVING the prose in a real polecat transcript — the D2 hard gate that must be GREEN before `junior.md`'s per-agent safety copy is removed (D3). Enforcement is the periodic enforcer gate + the per-rule rows in [Unified Matrix](#1-unified-ssot-matrix-rules-mechanisms-and-triggers). QA tracker: `aops-98c7ce49`.
- **Auto-mode classifier wired but unseeded** (L5). `autoMode` rules absent by deliberate 2026-06-04 decision — instruction tier walked first; a rule is seeded only on measurement showing instruction insufficient. Canonical: [`auto-mode-classifier.md`](enforcement/auto-mode-classifier.md).
- **Hydration / commit gates**: env vars wired (`HYDRATION_GATE_MODE`, `COMMIT_GATE_MODE`) but no `GateConfig` body — stubs.
- **Evidence loop steps 4–5** (`/aops` pattern detection → recommendation) aspirational; capture (step 2 `/learn`) and implementation (step 6) exist. Step 7 auto-map-update is manual.
- **`orchestrator-boundary-warn.md`** — template file not in `TEMPLATE_SPECS`; likely dead/unwired (cleanup follow-up).
- **PTY harness coverage** — measures Claude user-visibility + Stop agent-context; agy wire-acceptance, `--resume` persistence, and a model-echo agent-context lane for UPS/PreToolUse are not yet ported (`scripts/pty_hook_probe.py` is `client`-parameterized for it).
