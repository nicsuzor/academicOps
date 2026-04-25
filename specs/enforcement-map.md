---
title: Enforcement Map
type: state
category: state
description: Live registry of how each framework rule is enforced — which mechanism, at what severity, and where the next escalation or demotion should land if evidence supports it.
tier: core
depends_on: [enforcement]
tags: [framework, enforcement, rules, pyramid, state]
---

# Enforcement Map

This is the **current-state** companion to `specs/enforcement.md`. The design doc is the principle (the pipeline, the pyramid, the evidence loop). This map is the live record: **for each rule the framework enforces, which mechanisms catch it today, at what severity, and where the next move should land.**

When the §5 evidence loop completes a cycle — a pattern surfaces, a fix ships — a row in this map changes.

## Pipeline view (when mechanisms fire)

The temporal pipeline lives in `specs/enforcement.md` §3 — _Capture → Context injection → Decomposition → Workflow composition → Soft gates → Hard blocks → Observability → Agent review → Handover → Review pipeline → Merge gates → Follow-up_. Mechanisms below cite their lifecycle event (`PreToolUse`, `Stop`, `review-time`, `PR push`, `merge attempt`, `always-on`) rather than re-declaring the layer.

## Severity pyramid

Why a pyramid: **as severity rises, frequency falls.** The base tier covers everything cheaply, by default; the tip is reserved for unambiguous high-stakes cases. The principle is least invasion — prefer the lightest tier that catches the failure. The cost of a heavier tier is friction and false positives; the cost of a lighter tier is escapes. Tier choice is governed by §5 evidence, not by intuition.

```
                  ╱╲
                 ╱  ╲           Hard-deny  — rejected outright; no in-call release
                ╱────╲                       (policy_enforcer.py, settings.json deny,
               ╱      ╲                       credential isolation, auto-mode `block`,
              ╱        ╲                      loop detector at ceiling)
             ╱  Block   ╲       Block       — pauses until condition met
            ╱────────────╲                    (QA gate, handover gate in block mode,
           ╱              ╲                   branch protection, linter workflows,
          ╱     Warn       ╲                  proof-of-compliance schema)
         ╱──────────────────╲
        ╱                    ╲   Warn        — warning surfaced; agent proceeds
       ╱      Advisory        ╲                (enforcer gate default, handover gate
      ╱────────────────────────╲                default, pr-reviewer GHA, agent-enforcer GHA)
     ╱                          ╲
    ╱          Inject             ╲   Advisory  — verdict for a caller; non-blocking
   ╱────────────────────────────────╲              (rbg, marsha, james, pauli,
                                                     enforcer subagent)

                                       Inject     — surfaces info into context;
                                                     non-blocking
                                                     (lightweight hydrator,
                                                      AXIOMS.md/CORE.md instruction,
                                                      /learn, skills routing table)
```

| Tier      | Action                                 | Released when                                |
| --------- | -------------------------------------- | -------------------------------------------- |
| Inject    | surfaces information into context      | n/a — non-blocking                           |
| Advisory  | returns a verdict consumed by a caller | caller integrates the verdict                |
| Warn      | surfaces a warning at gate evaluation  | n/a — agent proceeds                         |
| Block     | pauses progress                        | gate condition met (verdict, schema, checks) |
| Hard-deny | rejects the call outright              | not released for this call                   |

**Escalation rule.** Move a (rule, mechanism) pair UP a tier when evidence — GH issues, /retro findings, /trend-review patterns, QA fails — shows the current tier is repeatedly bypassed.

**Demotion rule.** Move DOWN when evidence shows the current tier produces false positives without commensurate protection.

**Never guess.** The pyramid is moved by §5 evidence, not by authorial intuition.

### Gate mode environment variables

The mode of a configurable gate is set by env var, defaults below:

| Variable              | Default | Values                 | Controls                          |
| --------------------- | ------- | ---------------------- | --------------------------------- |
| `ENFORCER_GATE_MODE`  | `block` | `warn`, `block`        | periodic compliance audit         |
| `HYDRATION_GATE_MODE` | `off`   | `off`, `warn`, `block` | hydration before substantive work |
| `QA_GATE_MODE`        | `block` | `warn`, `block`        | QA verification before exit       |
| `COMMIT_GATE_MODE`    | `warn`  | `warn`, `block`        | commit policy                     |
| `HANDOVER_GATE_MODE`  | `warn`  | `warn`, `block`        | framework reflection before exit  |

A gate's effective tier (`warn` ↔ `block`) is its mode value at runtime, not a static spec entry.

### Note on auto-mode rows

The CC auto-mode classifier is a Sonnet 4.6 agent that reads the proposed tool call, the conversation transcript, and the rules expressed as prose, then judges whether to allow / prompt / block. It is not a regex matcher and it is not bound to a single tool call's local arguments — explicit user intent in prior turns and stated boundaries in conversation are part of its input. Treat it as **rbg-class judgment running at the per-action gate**.

Earlier rows in this map flagged auto-mode rules for removal on the grounds they were "session-level patterns, not per-action" or "judgment calls". That framing was wrong: the classifier has the transcript and is judgment-capable. The work tracked under `task-06db60dc` is **rule-rewriting** (P#-ID-style → prose-with-reasoning), not removal. Demotion to "removed" should require evidence the classifier cannot do the job — not a presumption that it cannot.

## Rule registry

One row per **(rule, mechanism)** pair. A rule with multiple mechanisms gets multiple rows. Each row records the current severity tier, where it fires, and current status — so escalation or demotion is tracked per row.

Rules are drawn from `aops-core/AXIOMS.md` (A1–A10) plus operational conventions in their own subsections.

### A1 — No Other Truths (Closure)

| Mechanism                         | Tier     | Fires at    | Status |
| --------------------------------- | -------- | ----------- | ------ |
| AXIOMS.md / CORE.md HALT Protocol | inject   | always-on   | active |
| `rbg` review                      | advisory | review-time | active |

Closure is structurally semantic — no per-action classifier can detect "rule not derivable from axioms." Escalation path would require a session-level audit subagent; not currently scoped.

### A2 — No Bills of Attainder (Categorical Imperative)

| Mechanism                        | Tier     | Fires at           | Status |
| -------------------------------- | -------- | ------------------ | ------ |
| AXIOMS.md instruction            | inject   | always-on          | active |
| `rbg` critic review              | advisory | review-time        | active |
| aops-skill Phase 2 design review | advisory | pre-implementation | active |

Generalisation is judgment-heavy. Mechanism above advisory would need a counterfactual reasoner.

### A3 — Honest Epistemics

| Mechanism                                                                  | Tier     | Fires at            | Status                                                         |
| -------------------------------------------------------------------------- | -------- | ------------------- | -------------------------------------------------------------- |
| AXIOMS.md / CORE.md "Inference is not evidence"                            | inject   | always-on           | active                                                         |
| Proof-of-compliance schema (`completion_evidence`, `release_task.summary`) | block    | `release_task` call | active (partial — schema enforces, content checked downstream) |
| `marsha` independent verification                                          | advisory | review-time         | active                                                         |
| `rbg` review                                                               | advisory | review-time         | active                                                         |

### A4 — Cite Sources

| Mechanism                                       | Tier     | Fires at    | Status |
| ----------------------------------------------- | -------- | ----------- | ------ |
| AXIOMS.md instruction                           | inject   | always-on   | active |
| `rbg` review                                    | advisory | review-time | active |
| `/learn` RCA schema (forces source attribution) | block    | invocation  | active |

### A5 — Single Source of Truth

| Mechanism                               | Tier     | Fires at    | Status                                                             |
| --------------------------------------- | -------- | ----------- | ------------------------------------------------------------------ |
| AXIOMS.md / aops-skill SSOT convention  | inject   | always-on   | active                                                             |
| auto-mode `Backup File Prevention` rule | warn     | PreToolUse  | active — needs rewrite as prose-with-reasoning per `task-06db60dc` |
| `find_duplicates` PKB tool              | advisory | on-demand   | active                                                             |
| `rbg` duplicate-detection review        | advisory | review-time | active                                                             |

### A6 — Stay Within Scope

| Mechanism                                         | Tier                                  | Fires at             | Status                                                                                          |
| ------------------------------------------------- | ------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| AXIOMS.md / aops-skill Decision Framework         | inject                                | always-on            | active                                                                                          |
| TodoWrite scope reminder                          | inject                                | TodoWrite            | active                                                                                          |
| auto-mode `Scope Discipline` rule                 | warn                                  | PreToolUse           | active — classifier reads transcript & judges drift; rule needs prose rewrite (`task-06db60dc`) |
| auto-mode `Explicit Approval for Costly Ops` rule | warn                                  | PreToolUse           | active — needs concrete threshold (`task-06db60dc`)                                             |
| `orchestrator_boundary` gate                      | warn                                  | PostToolUse          | active (hard-block in Phase 3)                                                                  |
| enforcer gate (ultra-vires Type B)                | warn (default) / block (configurable) | PreToolUse threshold | active — configurable via `ENFORCER_GATE_MODE`                                                  |
| `rbg` review                                      | advisory                              | review-time          | active                                                                                          |
| pr-reviewer GHA                                   | warn                                  | PR push              | active                                                                                          |

### A7 — Respect Delegated Authority

| Mechanism                                        | Tier     | Fires at    | Status                                                                              |
| ------------------------------------------------ | -------- | ----------- | ----------------------------------------------------------------------------------- |
| AXIOMS.md / task `acceptance_criteria` field     | inject   | always-on   | active                                                                              |
| auto-mode `Delegated Authority Only` rule        | warn     | PreToolUse  | active — classifier is judgment-capable; rule needs prose rewrite (`task-06db60dc`) |
| auto-mode `Acceptance Criteria Own Success` rule | warn     | PreToolUse  | active — same; rule needs prose rewrite (`task-06db60dc`)                           |
| `marsha` criterion-substitution check            | advisory | review-time | active — warn-only (`#621`)                                                         |
| `rbg` review                                     | advisory | review-time | active                                                                              |
| pr-reviewer GHA                                  | warn     | PR push     | active                                                                              |
| QA gate                                          | block    | Stop        | planned                                                                             |

### A8 — Halt on Failure

| Mechanism                                                        | Tier      | Fires at      | Status                                                                                         |
| ---------------------------------------------------------------- | --------- | ------------- | ---------------------------------------------------------------------------------------------- |
| AXIOMS.md / CORE.md Fail-Fast / Halt Rule                        | inject    | always-on     | active                                                                                         |
| auto-mode `No Validation Bypass` rule                            | block     | PreToolUse    | active — needs narrowing of `--force` to validation contexts (`task-06db60dc`)                 |
| auto-mode `Fail-Fast on Tool Failure` rule                       | warn      | PreToolUse    | active — classifier reads tool-result + transcript; rule needs prose rewrite (`task-06db60dc`) |
| auto-mode `No Infrastructure Workarounds` rule                   | warn      | PreToolUse    | active — same; rule needs prose rewrite (`task-06db60dc`)                                      |
| `policy_enforcer.py` (destructive git, `--force`, `--no-verify`) | hard-deny | PreToolUse    | active                                                                                         |
| `fail_fast_watchdog`                                             | warn      | PostToolUse   | active                                                                                         |
| commit gate                                                      | warn      | commit-time   | active                                                                                         |
| branch protection (required checks)                              | block     | merge attempt | active                                                                                         |
| `rbg` review                                                     | advisory  | review-time   | active                                                                                         |

### A9 — Data Boundaries

| Mechanism                                                                                                              | Tier      | Fires at      | Status                                             |
| ---------------------------------------------------------------------------------------------------------------------- | --------- | ------------- | -------------------------------------------------- |
| AXIOMS.md instruction                                                                                                  | inject    | always-on     | active                                             |
| credential isolation (agent-env-map)                                                                                   | hard-deny | SessionStart  | active — known gap: no runtime re-verification     |
| CC-default auto-mode rules (Memory Poisoning, Self-Modification, Git Push to Default Branch, Sandbox Network Callback) | block     | PreToolUse    | active — preserved through `lib/automode.py` merge |
| `policy_enforcer.py` (env file writes, oversized `.md`, plugin payloads)                                               | hard-deny | PreToolUse    | active                                             |
| commit gate                                                                                                            | warn      | commit-time   | active                                             |
| branch protection                                                                                                      | block     | merge attempt | active                                             |

A9 is unusual: aops contributes no novel auto-mode rule because CC defaults already cover the protected surfaces. Coverage rests on the merge strategy preserving CC's defaults.

### A10 — Evidentiary Immutability

| Mechanism                                        | Tier      | Fires at    | Status                                                                                                    |
| ------------------------------------------------ | --------- | ----------- | --------------------------------------------------------------------------------------------------------- |
| AXIOMS.md / CORE.md "Research Data is Immutable" | inject    | always-on   | active                                                                                                    |
| auto-mode `Research Data Immutable` (P#42)       | block     | PreToolUse  | active — `records/` glob needs concretising (`**/records/**`, `$ACA_DATA/records/**`) per `task-06db60dc` |
| `policy_enforcer.py` path protection             | hard-deny | PreToolUse  | active                                                                                                    |
| `rbg` review                                     | advisory  | review-time | active                                                                                                    |

### Operational rules (derived from axioms)

These are framework conventions with their own enforcement infrastructure. They derive from one or more axioms — derivation noted per row.

**Hydration before substantive work** _(derives from A1, A8 — agent must know rules before acting; missing context is a failure)_

| Mechanism            | Tier   | Fires at          | Status                                           |
| -------------------- | ------ | ----------------- | ------------------------------------------------ |
| lightweight hydrator | inject | UserPromptSubmit  | active — known gap: subagent inherit-from-parent |
| skills routing table | inject | UserPromptSubmit  | active                                           |
| gate status strip    | inject | UserPromptSubmit  | active — verify rendering path                   |
| hydration gate       | warn   | session lifecycle | warn (default off via `HYDRATION_GATE_MODE`)     |

**Session ends with handover** _(derives from A3 — completion claims need evidence)_

| Mechanism                   | Tier                                              | Fires at     | Status |
| --------------------------- | ------------------------------------------------- | ------------ | ------ |
| /dump skill                 | inject                                            | invocation   | active |
| Framework Reflection schema | inject                                            | end of /dump | active |
| handover gate               | warn (default) / block (per `HANDOVER_GATE_MODE`) | Stop         | active |

**Periodic compliance audit** _(derives from A6, A8 — drift catcher for session-level patterns auto-mode misses)_

| Mechanism                                     | Tier                   | Fires at             | Status                                                                                 |
| --------------------------------------------- | ---------------------- | -------------------- | -------------------------------------------------------------------------------------- |
| enforcer gate countdown                       | warn (default) / block | PreToolUse threshold | active — configurable via `ENFORCER_GATE_MODE`                                         |
| enforcer subagent                             | advisory               | gate threshold       | active                                                                                 |
| compliance block flag (`compliance_block.py`) | hard-deny              | session lifecycle    | active in `block` mode — block record at `$ACA_DATA/enforcer/blocks/`, cleared by user |

**PR review pipeline** _(derives from A3, A7)_

| Mechanism                                  | Tier                   | Fires at             | Status          |
| ------------------------------------------ | ---------------------- | -------------------- | --------------- |
| pr-reviewer GHA                            | warn                   | PR push              | active          |
| agent-enforcer GHA                         | warn → required-check  | PR push              | active          |
| linter workflows (ruff, typecheck, pytest) | block (required check) | PR push              | active          |
| branch protection                          | block                  | merge attempt        | active — verify |
| loop detector (merge-prep self-loop)       | hard-deny at ceiling   | every merge-prep run | active          |
| project-owner / admin approval             | block                  | merge attempt        | active — verify |

**Skill / agent declaration linting** _(derives from A1 — closure on derivable rules)_

| Mechanism                                              | Tier         | Fires at | Status  |
| ------------------------------------------------------ | ------------ | -------- | ------- |
| lint rule 6 (skill ↔ agent symmetry)                   | warn → error | PR push  | planned |
| lint rule 7 (nested reachability)                      | error        | PR push  | planned |
| lint rule 8 (agent–tool parity)                        | error        | PR push  | planned |
| lint rule 9 (persona inlining; LLM classification)     | warn         | PR push  | planned |
| permissions-lint: bash-without-scopes                  | error        | PR push  | planned |
| permissions-lint: filesystem-tools-without-file_access | error        | PR push  | planned |

**Supervisor plan-review gate** _(derives from A7 — user owns acceptance)_

| Mechanism                   | Tier  | Fires at                          | Status                                                                                                                       |
| --------------------------- | ----- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Supervisor plan-review gate | block | post-decomposition / pre-dispatch | active — `parent.status != "queued"` halts; `ready → queued` transition by user is the approval record (no warn-only bypass) |

## Known gaps

Rows that flag what the framework does NOT yet catch, or catches incompletely:

- **Subagent hydration inherit** — parent's hydration skip cascades to children; no subagent-independent hydration.
- **Reactive helpfulness** (ultra-vires Type A) — PostToolUse on tool error is `planned` (`specs/ultra-vires-enforcer.md` Phase 2); enforcer countdown only catches drift after the fact.
- **QA gate operational coverage** — gate body present (`lib/gates/definitions.py:71`) but `enforcement.md` §3 still labels it planned; "planned requirements" not codified.
- **Hydration gate body** — env var wired, gate definition not yet present.
- **Commit gate body** — env var wired, gate definition not yet present.
- **Auto-mode rules vs. A1–A10** — current rules cite pre-rework P# IDs; rewrite blocked on `task-06db60dc` / `task-0af27bfc` (axiom IDs in `aops-core/AXIOMS.md` are A1–A10 but `automode-rules.json` still references P# IDs).
- **Settings.json deny rules** — repo's `.claude/settings.json` declares only allow rules; deny enforcement comes from user/global settings (out-of-tree, unverifiable from this repo).
- **`/aops` pattern detection** — Steps 4–5 of the evidence loop are unbuilt; failure evidence accumulates in GH issues but no mechanism reads patterns and proposes pyramid adjustments. Principal known gap.
- **Automatic map-row updates** — Step 7 of the evidence loop is partial; row updates here are still manual in the closing PR.

## How to update this map

1. **Observe** the failure or insufficiency (QA / marsha fail, /retro, /sleep, user report, post-merge regression).
2. **File evidence** via `/learn` if no GH issue tracks the pattern. The skill enforces RCA schema and anonymisation. Labels: `framework`, `enforcement`, plus criticality.
3. **Locate the rule** in the registry. If multiple mechanisms exist, pick the row whose tier the evidence implicates.
4. **Propose a tier change** — escalate (move up) or demote (move down) per the rules above. If no mechanism currently catches the failure, the rule has a _gap row_ — add a new row at the lightest tier that plausibly catches it. Apply the least-invasion principle.
5. **Update the row** in the same PR that ships the change. Statuses: `active`, `warn-only`, `planned`, `aspirational`. If a tier change is in flight, note it in the row's status field.

## Related

- `specs/enforcement.md` — design statement (pipeline, pyramid, evidence loop)
- `specs/enforcement-mechanisms.md` — per-mechanism reference catalogue
- `specs/ultra-vires-enforcer.md` — enforcer agent and gate internal design
- `aops-core/AXIOMS.md` — A1–A10 source
- `aops-core/.claude-plugin/plugin.json` (`autoMode` key) — live auto-mode rules
- `task-06db60dc` — auto-mode rewrite against A1–A10 (blocked on axiom rework landing)
