---
id: reflexes-integration
title: Reflexes Safety Harness Integration & CoPE Policy System
type: spec
status: ready
tags: [enforcement, reflexes, cope, hooks, gates, safety-harness]
---

# Reflexes Safety Harness Integration & CoPE Policy System

## Overview

This specification documents the integration of the **Reflexes** safety harness (`github.com/zentropi-ai/reflexes` — public Apache-2.0 runtime with markdown CoPE-format policies) into the academicOps framework as the core runtime-enforcement layer for axiom compliance.

The 15 canonical axiom rule files in `.agents/rules/*.md` remain the sole **Single Source of Truth (SSoT)** for framework rules. The Reflexes CoPE-format policy files in `aops/reflexes/policies/*.md` serve as a derived, runtime-enforcement rendering optimized for policy-steerable classification.

---

## 1. Inventory of Existing Hook Wiring

academicOps maintains a unified hook dispatch infrastructure across supported agent environments. All hook injection points compose cleanly without introducing parallel hook stacks.

### Claude Code Hook Inventory (`aops/templates/hooks.template.json`)

| Hook Event | Execution Target | Purpose / Injected Content |
|---|---|---|
| `SessionStart` | `router.py claude SessionStart` | Environment initialization, session credential isolation (`AOPS_BOT_GH_TOKEN`, `GIT_CONFIG_*`). |
| `PreToolUse` | `gate_dispatch.py claude` | Evaluates runtime gate functions (`GATES` list in `registry.py`), including `require_subagent_model` and `require_aops_bot_gh_token`. |
| `Stop` | `router.py claude Stop`<br>`gate_dispatch.py claude` | Sequential hook executions: `router.py` injects exit reminders (`handover.md`); `gate_dispatch.py` runs stateful stop gates (`exit_reflection_reminder`). |
| `SubagentStop` | `router.py claude SubagentStop` | Injects subagent honesty and formatting reminders (`honesty.md`). |
| `UserPromptSubmit` | `router.py claude UserPromptSubmit` | Injects hydration context (`hydrate.md`). |
| `PostToolUse` | `router.py claude PostToolUse` | Injects subagent output verification reminders (`verify.md`). |

### Antigravity Hook Inventory (`aops/templates/hooks.template.json`)

| Hook Event | Execution Target | Purpose / Injected Content |
|---|---|---|
| `PreInvocation` | `router.py agy PreInvocation` | Ephemeral message context injection (`hydrate.md`). |
| `PostInvocation` | `router.py agy PostInvocation` | Ephemeral message context injection (`handover.md`). |

### Integration Composition Architecture

Reflexes policy evaluation composes cleanly within the existing `gate_dispatch.py` engine:
- No parallel hook stack or duplicate event listeners are registered.
- Reflexes CoPE policy evaluation operates as a gate module within `aops/hooks/gates/`.
- Merged verdicts follow the existing invariant: `deny > warn > allow` (`None`).

---

## 2. CoPE Policy Set & SSoT Relationship

### Canonical SSoT vs. Derived Policy Set

- **Single Source of Truth**: `.agents/rules/*.md` (15 axiom files). Any change to an axiom definition must occur in `.agents/rules/`.
- **Derived Policy Set**: `aops/reflexes/policies/*.md` (15 CoPE criteria files). These are derived renderings translated into CoPE (Content Policy Evaluator) criteria format.

### SSoT ↔ Policy Mapping

| Axiom Slug | SSoT Rule File | CoPE Policy File | Code | Trigger |
|---|---|---|---|---|
| `bounded-execution` | `.agents/rules/bounded-execution.md` | `aops/reflexes/policies/Bounded-Execution.md` | `BE` | `before_tool_call` |
| `categorical-imperative` | `.agents/rules/categorical-imperative.md` | `aops/reflexes/policies/Categorical-Imperative.md` | `CI` | `before_response` |
| `cite-sources` | `.agents/rules/cite-sources.md` | `aops/reflexes/policies/Cite-Sources.md` | `CS` | `before_response` |
| `closure` | `.agents/rules/closure.md` | `aops/reflexes/policies/Closure.md` | `CL` | `before_tool_call` |
| `costly-ops-approval` | `.agents/rules/costly-ops-approval.md` | `aops/reflexes/policies/Costly-Ops-Approval.md` | `CO` | `before_tool_call` |
| `data-boundaries` | `.agents/rules/data-boundaries.md` | `aops/reflexes/policies/Data-Boundaries.md` | `DB` | `before_tool_call` |
| `do-one-thing` | `.agents/rules/do-one-thing.md` | `aops/reflexes/policies/Do-One-Thing.md` | `DT` | `before_response` |
| `evidence-immutable` | `.agents/rules/evidence-immutable.md` | `aops/reflexes/policies/Evidence-Immutable.md` | `EI` | `before_tool_call` |
| `exercise-authority` | `.agents/rules/exercise-authority.md` | `aops/reflexes/policies/Exercise-Authority.md` | `EA` | `before_tool_call` |
| `full-observability` | `.agents/rules/full-observability.md` | `aops/reflexes/policies/Full-Observability.md` | `FO` | `before_response` |
| `halt-on-failure` | `.agents/rules/halt-on-failure.md` | `aops/reflexes/policies/Halt-On-Failure.md` | `HF` | `before_tool_call` |
| `honest-epistemics` | `.agents/rules/honest-epistemics.md` | `aops/reflexes/policies/Honest-Epistemics.md` | `HE` | `before_response` |
| `judgment-non-delegable` | `.agents/rules/judgment-non-delegable.md` | `aops/reflexes/policies/Judgment-Non-Delegable.md` | `JD` | `before_tool_call` |
| `pull-over-push` | `.agents/rules/pull-over-push.md` | `aops/reflexes/policies/Pull-Over-Push.md` | `PP` | `before_response` |
| `single-source-of-truth` | `.agents/rules/single-source-of-truth.md` | `aops/reflexes/policies/Single-Source-Of-Truth.md` | `ST` | `before_tool_call` |

---

## 3. Fail-Open Behavior & Runtime Resilience

Reflexes enforces a strict **fail-open** policy for evaluator infrastructure:
- **Network Outage / Timeout / Model Unreachable**: If the policy evaluator endpoint fails, times out, or raises an exception, the error is caught, logged to `sys.stderr`, and the evaluation returns an `allow` (`None`) verdict.
- **Rationale**: An evaluator outage must never block local developer or agent productivity. Product signal is separated from infrastructure errors.
- **Process Stability**: `gate_dispatch.py` wraps each gate execution individually (`_run_gate`), preventing any single policy failure or exception from crashing the dispatcher or discarding verdicts from other gates.

---

## 4. Lifecycle Event Hooks & Evaluation Flow

### Event Normalization Flow

```
[ Hook Event (stdin JSON) ]
            │
            ▼
   gate_dispatch.py (normalize -> Event)
            │
            ├─► Structural Self-Loop Guard (Stop / SubagentStop)
            ├─► Load Session State (state.py)
            │
            ▼
   GATES Registry Loop
            │
            ├─► require_subagent_model
            ├─► exit_reflection_reminder
            ├─► require_aops_bot_gh_token
            └─► reflexes_evaluator (CoPE Policies)
            │
            ▼
   Verdict Merge (deny > warn > allow)
            │
            ▼
   Client Emit Adapter (emit.py -> stdout JSON)
```

---

## 5. Credential Enforcement (AOPS_BOT_GH_TOKEN)

Git and GitHub push operations enforce strict credential isolation:
- All `git push` and `gh pr create` / `gh release create` / `gh push` actions require `AOPS_BOT_GH_TOKEN` to be set in the active environment.
- The `require_aops_bot_gh_token` gate intercepts `PreToolUse` events on `Bash` tools.
- If `AOPS_BOT_GH_TOKEN` is unset or empty during a push command, the gate issues a `deny` verdict, failing closed immediately before shell execution.

---

## 6. Host-Side Hook Activation (Scope & Manual Opt-In)

Per framework policy, host-side hook activation is **OUT OF SCOPE** for automated background builds.
- Host-level hook files (`~/.claude/settings.json`, global shell profiles) are NOT modified during automated installation.
- Host-side activation is documented as a manual, opt-in step performed by system administrators.
