---
id: enforcement-318d578e
title: Enforcement Architecture
type: spec
status: ready
tier: core
depends_on: []
tags: [enforcement, compliance, framework-architecture, verification]
---

# Enforcement Architecture

## Governing principle — agents all the way down

The framework enforces **no programmatic, deterministic, or mechanical verdict on quality or process**. Hooks, server contracts, and config are **delivery channels** — they remind, route, and make things visible; they never decide whether work is good or whether a rule was followed. Every verdict — did this follow the rules, is this actually good, was this worth doing — is an agent's judgment, and the bar every reviewing agent applies is world-leading, not technically-acceptable.

The only **mechanical** enforcement in the framework is **structural prevention**: credential and workspace isolation (Docker containers for polecat workers, repo-scoped access, no ambient credentials inside a container). Prevention by construction — never reactive detection, never content-sniffing ("no shitty NLP" — no regex-for-meaning, no destructive-verb pattern matching), never a deterministic pass/fail on the substance of an agent's work.

This is a deliberate, ratified narrowing from an earlier model that ran a ~40-mechanism in-session gate pyramid (turn-based compliance counters, blocking Stop gates with per-gate mode config, a dedicated `GateConfig` engine). That engine has been retired in full; see [Retired](#retired) below. Enforcement's centre of gravity is now the **task-graph boundary** (claim → execute → release, see [task-contract.md](task-contract.md)) and the **agent judgment** applied at review time (see [workflow.md](workflow.md)), not a stack of harness-level gates.

## Personalities are not skills

An **agent personality** (charter — Ida, pauli, rbg, marsha, james, …) defines conduct, judgment register, disposition, and responsibilities: who the agent is and what standard it holds. An **agent skill** defines a procedure or capability: how a job gets done. These are different artifacts and are never conflated.

- **Default: skills are personality-agnostic.** Any sufficiently capable agent can execute any skill; a skill that silently assumes one personality is a defect.
- **Binding a skill to a personality is a deliberate, documented exception**, for exactly two reasons: **earmarking** (the skill genuinely depends on that personality's judgment register — e.g. `/verify` owned by marsha's broken-until-proven disposition) or **permission control** (tool grants deliberately restricted to force a workflow — e.g. a review role gated to keep authoring and verification separate).
- The three review lenses in [workflow.md](workflow.md) — pauli / rbg / marsha — name **judgment registers a review must apply**, not exclusive executors: which agent carries a lens is a dispatch decision, provided reviewer ≠ executor holds.

## What actually enforces things today

**Enforcement is risk-reduction**: compliance is not guaranteed. Mechanical hard blocks are often NOT the best option. We have four groups of levers:

1. **Norms** — the agent's internalised alignment with intent (prompt directives, system rules, explicit instructions).
2. **Cost** — the token/time/friction cost of complying versus the incentive to bypass.
3. **Defaults** — whether the compliant path is mechanically the path of least resistance (e.g. automated execution) rather than something the agent must remember to invoke.
4. **Likelihood** — the probability a violation is detected, multiplied by its consequence (Rule + Delict × Likelihood) — this is the one lever pyramid severity directly moves.

Before escalating severity, check whether the actual failure is a cost or defaults problem — the "Escalate up" rule below already requires confirming the lighter tiers were exhausted first, and a cost/defaults fix is usually cheaper than a severity bump. _Worked example:_ repeated stale-state PKB assertions across sessions are not a norms or severity failure — agents are told to check the PKB and the rule is known and enforced. The fix is lowering the cost (better search ergonomics, trimmed response payloads) and improving the default (inject PKB search results directly into context via the `UserPromptSubmit` hook, rather than merely exhorting agents to search).

### 1. Structural prevention (the only mechanical layer)

- **Container isolation** — polecat workers run inside Docker (`Dockerfile`, `aops-jr/polecat/cli.py`), with no ambient host credentials, a read-only staging mount, and a scoped workspace volume. This is prevention by construction: a worker cannot exfiltrate host secrets or touch files outside its mount because the container doesn't have them, not because a rule told it not to.
- **`polecat.yaml`** is the single posture source for session configuration (gate mode keys, session-type defaults) — see [`aops-jr/polecat/defaults/polecat.yaml.example`](../../aops-jr/polecat/defaults/polecat.yaml.example). No overlay/defaults-naming, no built-in code fallback: a missing value is a hard fail, not a silent default.

### 2. The harness delivery channel (reminder, not gate)

The entire in-session hook surface is one script: [`aops/hooks/router.py`](../../aops/hooks/router.py), wired via [`aops/templates/hooks.template.json`](../../aops/templates/hooks.template.json) to `Stop` / `SubagentStop` / `UserPromptSubmit` (Claude Code) and `PreInvocation` / `PostInvocation` (Antigravity). It injects two static templates, unconditionally, identically, on every surface — no per-client branching beyond the wire format, no mode key, no blocking:

- **`ida-hydrate.md`** — on prompt submit: search the PKB before re-deriving procedure.
- **`ida-reminder.md`** — on Stop/SubagentStop: an honesty and durable-capture reminder (finish the actual ask, don't create homework for the user, commit and push before the session ends, curate durable knowledge, and close with a structured Observed/Reported proof rather than a narrative) — this is the exit-reflection discipline from the ratified plan's §1, delivered as a reminder rather than as a blocking gate.

Nothing in this layer produces a verdict. It cannot stop an agent from exiting, and it does not check whether the agent actually did what the reminder asked — that is the executing agent's own judgment call, backstopped by the review lenses below, not by the hook.

**Target vs current, named explicitly:** the ratified plan (§1) envisions the harness eventually _dispatching_ the reflection/audit subagent directly on Stop, where the harness supports it, rather than only injecting reminder text. `router.py` does not do this yet — it injects text only. This is an open implementation gap against the ratified design, not a design ambiguity; flagging it here rather than asserting it as already built.

### 3. Claude Code's native auto-mode classifier

A model-based (not deterministic) tool-call classifier built into the harness, configured with prose rules in [`aops-jr/polecat/defaults/claude-settings.json`](../../aops-jr/polecat/defaults/claude-settings.json). Full design statement, admission criteria, and cost model: [auto-mode-classifier.md](auto-mode-classifier.md). Because it is an LLM judgment call over a stripped transcript rather than a deterministic pattern match, it sits inside the "agents all the way down" principle rather than beside it — it is the one place a per-action judgment call happens before the agent's own review loop closes.

### 4. Task-graph boundary — the primary enforcement point

`claim_task` in, `release_task` out. A completion claim must carry independent-verification evidence or a stated failure reason — this is where the framework actually holds agents accountable, because it binds to the claim act rather than to session mechanics. Full contract: [task-contract.md](task-contract.md); the universal claim-evidence shape every boundary reads: [evidence-contract.md](evidence-contract.md).

### 5. Task-boundary review — three pauli-specified lenses

- **pauli** (pre-hoc) — the premise standard: the idea is sound, elegant, and strongly aligned with the project's strategic aims when evaluated in the full context. The `decompose` skill (see [`aops/skills/decompose/SKILL.md`](../../aops/skills/decompose/SKILL.md)) always emits this as a standing, early-blocking task node **at decomposition time** — the rest of the epic depends on it clearing. The former standalone dispatch-time "premise gate" (a two-judge hard-refuse ceremony run at `/pull`/`/dispatch`) is retired; decomposition carries this judgment instead, and dispatch surfaces trust the planner's decomposition rather than re-judging it.
- **rbg** — rules were followed: boundary review of the task contract and handback only (inputs/outputs), never the transcript. Always emitted as a standing task node blocking epic acceptance.
- **marsha** (post-hoc) — the task does what it was supposed to and does it _well_: delivered artifact vs. the original aim and acceptance criteria, bar is excellent, not passing. Always emitted as a standing task node blocking epic acceptance.

`decompose` plans only: it emits these three tasks and their `depends_on` wiring into the graph; it never dispatches or runs them itself. Review depth (per-chunk subtasks vs. one consolidated pass at the final PR) is the planner's call at decomposition time, based on the work's risk and blast radius. Full shape: [workflow.md](workflow.md).

### 6. Workflow components for assembly

A set of composable gate _components_ — prose, not code — that an assembled workflow can wire into a pipeline: [`aops/workflows/gates/`](../../aops/workflows/gates/) (`outbound-review`, `verification`, `handover`, `constraint-check`, `qa`, `human-approval`). Each names its own stakes, door-type (one-way/two-way), and category. Workflows assemble these at generation time rather than every task inventing its own review ceremony.

### 7. Sign-off — the workflow-level instantiation

The git PR pipeline (`.github/workflows/`: `rbg-review.yml`, `agent-qa.yml`, `agent-enforcer.yml`, `agent-mechanic.yml`, `agent-pre-admission-responder.yml`, `issue-sweep.yml`, plus mechanical `lint.yml`/`pytest.yml`/`typecheck.yml`) is the concrete instantiation of workflow-level sign-off for anything that ships as a PR. Design statement: [sign-off.md](sign-off.md).

## Evidence loop — how the framework learns

Two flows, deliberately separated (witness vs. judge), so the volume and direction of framework change is governed by cross-incident pattern, not by the salience of the most recent failure:

1. **File a bug** (`/learn`, [`aops/commands/learn.md`](../../aops/commands/learn.md)) — an agent that hits friction files the forensic facts (what happened, root-cause category, rule already in place if any, impact) immediately, unilaterally, with no fix proposed. One friction = one filing.
2. **Improve the framework** (`/issue-sweep` / the `triage` skill's sweep mode) — a detached pass over the accumulated issue queue, on a cadence the user sets, classifies each issue and only proposes a mechanism add/escalation where ≥3 recurrences (or explicit user direction) justify it. The user gates every disposition.

A single incident that is a **bug** (broken skill routing, a wrong path, an incomplete instruction) gets fixed immediately from one report. A single incident that is an **escalation proposal** (a new gate, a new axiom, a heavier mechanism) gets logged and waits for the pattern.

## Design principles

1. **Default to instructions.** Agents are intelligent and instructions work in the large majority of cases; the burden of proof is on adding a mechanism, not on keeping behaviour in prose.
2. **Bias hard against mechanical gates.** Every hard-coded check is permanent complexity and a new place for the framework to fail. Given the choice, extend the prose an agent reads and judges against, not the code that pre-judges for it.
3. **Measure before changing.** The evidence loop above is the authority for adding or escalating a mechanism. Authorial intuition is not evidence.
4. **Show, don't tell.** Where compliance is claimed, require information that demonstrates it — the evidence contract, not reassurance.
5. **Never guess.** With no evidence either way, current placement holds.

## Retired

The framework's prior in-session hook/gate engine — a dedicated `GateConfig` framework, a ~1600-line hook router, per-gate mode-key plumbing, a turn-based `rbg` PreToolUse compliance counter, standalone critic/QA-exit gates, a two-judge dispatch-time premise gate, and the separate `ENFORCEMENT-MAP.md` / `GATES.md` / `pyramid.md` register documents that catalogued it — has been deleted in full, not versioned or kept as a fallback. The concerns it addressed either moved to the task-graph boundary and review lenses above, moved to structural prevention, or are judged unnecessary given the module-boundary thesis. Git history is the record of what existed and why it was removed; this spec describes what exists now, not an archive of what came before.

## Sibling documents

- [task-contract.md](task-contract.md) — the work-unit contract (`claim_task` → `release_task`).
- [workflow.md](workflow.md) — the five-step workflow shape (contract → execution → boundary-check → QA-around → sign-off) and the review-depth call.
- [sign-off.md](sign-off.md) — the workflow-level review, instantiated today as the git PR pipeline.
- [evidence-contract.md](evidence-contract.md) — the single universal claim-evidence shape every boundary above reads.
- [auto-mode-classifier.md](auto-mode-classifier.md) — design statement for Claude Code's native per-action classifier.
- [`aops/workflows/gates/`](../../aops/workflows/gates/) — the prose workflow-gate component library for assembled workflows.
