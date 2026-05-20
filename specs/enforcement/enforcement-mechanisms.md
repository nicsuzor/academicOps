---
id: enforcement-mechanisms
title: Enforcement Mechanisms (reference catalogue)
type: spec
status: inbox
tier: core
depends_on: [enforcement]
tags: [enforcement, reference, mechanisms]
---

# Enforcement Mechanisms (reference catalogue)

> **Design-narrative companion, not the operative catalogue.** This file
> is keyed to the L0–L11 pipeline view in `specs/enforcement/enforcement.md`
> — a useful frame for thinking about _when_ a mechanism fires. **No
> blocking rule cites L0–L11 or the base/middle/tip pyramid.** The
> operative catalogue for add/escalate/remove decisions is the L0–L7
> cost ladder in **`.agents/ENFORCEMENT-MAP.md`**, which `rbg` blocks on
> via P#65. Reach for this file when you need the per-mechanism schema
> details (trigger, location, scope, status); reach for the operative
> state file when you need the current cost-ladder ranking.

This is the per-mechanism detail catalogue referenced from `specs/enforcement/enforcement.md` §6. For the design statement — why enforcement is shaped the way it is, how the pipeline and pyramid views relate, and how the evidence loop closes — read `specs/enforcement/enforcement.md` first. For the operative state catalogue keyed by mechanism × rule, read `.agents/ENFORCEMENT-MAP.md`. For the per-gate runtime catalogue (5-question template: what / where / how-configured / how-verify / how-debug for each session-time gate), see [`aops-core/GATES.md`](../../aops-core/GATES.md).

Entries below use the fixed schema declared in `specs/enforcement/enforcement.md` §6 and are organised by **pipeline layer** (L0 → L11 → Evidence loop), not by pyramid tier. Mechanisms that span pyramid tiers (e.g. `/dump` runs as middle-tier during normal handover, tip-tier when the handover gate blocks Stop) carry both tiers with a conditional clause. Status fields are derived from source files where observable; unverifiable fields are flagged "verify".

## §6 Mechanisms by pipeline layer

### L0 Capture

#### /q skill (quick queue)

- **Pipeline layer**: L0 Capture
- **Pyramid tier**: base
- **Trigger**: user invokes `/q` slash command
- **Purpose**: Quick-queue a task by delegating to planner in capture mode, so backlog entries never live outside the PKB.
- **Location**: `aops-core/commands/q.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### PKB create_task MCP

- **Pipeline layer**: L0 Capture
- **Pyramid tier**: base
- **Trigger**: any agent calls the `create_task` MCP tool
- **Purpose**: Structured task creation path that enforces schema (title, parent, status, tags) at the tool boundary rather than via free-form markdown.
- **Location**: `mcp__plugin_aops-core_pkb__create_task` (MCP tool; server implementation outside this repo surface)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Inbox-default status on task creation

- **Pipeline layer**: L0 Capture
- **Pyramid tier**: base
- **Trigger**: `create_task` called without explicit status
- **Purpose**: New tasks default to an inbox/unscheduled state so capture never silently commits to work.
- **Location**: TBD — verify at next pass (PKB MCP server; not in this repo tree)
- **Scope**: polecat, crew, interactive
- **Status**: active — verify

#### Complexity evaluation on capture

- **Pipeline layer**: L0 Capture
- **Pyramid tier**: base
- **Trigger**: task creation or intake review
- **Purpose**: Lightweight complexity/uncertainty scoring so downstream decomposition knows which tasks need breaking up.
- **Location**: TBD — verify at next pass (referenced in planner SKILL.md; no dedicated tool seen in `mcp__plugin_aops-core_pkb__` surface)
- **Scope**: polecat, crew, interactive
- **Status**: planned — verify

### L1 Context injection

#### session_env_setup

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: SessionStart hook event
- **Purpose**: Populate per-session env vars, apply agent-env-map credential scoping, and persist state for subsequent hooks.
- **Location**: `aops-core/hooks/session_env_setup.py`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Lightweight hydrator (routing hint)

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: UserPromptSubmit hook event (non-subagent, non-task-notification)
- **Purpose**: Inject the skills-routing table and context-map hints so the agent sees relevant skills/docs without a full hydration pass.
- **Location**: `aops-core/hooks/router.py` — `_run_lightweight_hydrator` (~line 411)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Skills routing table

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: rendered as part of the lightweight hydrator on every UserPromptSubmit
- **Purpose**: Point the agent at the right skill for a user intent before it fabricates its own procedure.
- **Location**: template rendered by `aops-core/hooks/router.py` via `lib.template_registry` (template key `hydration.warn`)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### CLAUDE.md / AGENTS.md load

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: client startup (harness-native, not a hook)
- **Purpose**: Project-level instructions the host CLI auto-loads into the system prompt.
- **Location**: `.agents/AGENTS.md` (this repo); CLAUDE.md may be supplied by the user at cwd
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Gate status strip

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: injected into context on hydration events
- **Purpose**: Show current gate states (hydration, enforcer, qa, handover) as a concise strip so the agent can see what is open/closed.
- **Location**: TBD — verify at next pass (referenced in hydrator design; rendering path not isolated in one file)
- **Scope**: polecat, crew, interactive
- **Status**: active — verify

#### Context-map injection

- **Pipeline layer**: L1 Context injection
- **Pyramid tier**: base
- **Trigger**: UserPromptSubmit, when `.agents/context-map.json` exists in cwd
- **Purpose**: Surface curated doc references keyed to user prompts so the agent reaches for known-good context.
- **Location**: `aops-core/hooks/router.py` — `_inject_context_map_hints` (~line 447)
- **Scope**: polecat, crew, interactive
- **Status**: active

### L2 Decomposition

#### /planner skill

- **Pipeline layer**: L2 Decomposition
- **Pyramid tier**: middle
- **Trigger**: user invokes `/planner` or another skill delegates capture
- **Purpose**: Strategic planning — decomposition, PKB graph ownership, knowledge-building so executable tasks reach workers already scoped.
- **Location**: `aops-core/skills/planner/SKILL.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Task templates

- **Pipeline layer**: L2 Decomposition
- **Pyramid tier**: base
- **Trigger**: planner / supervisor writes a task using a template
- **Purpose**: Canonical shapes for specs, user-stories, experiment plans, and test specs so decomposition is consistent across agents.
- **Location**: `aops-core/skills/aops/templates/` (`dev-plan.md`, `experiment-plan.md`, `spec.md`, `test-spec.md`, `user-story.md`)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Proof-of-compliance tool fields

- **Pipeline layer**: L2 Decomposition
- **Pyramid tier**: middle
- **Trigger**: agent calls `release_task` or `complete_task`
- **Purpose**: Require `completion_evidence` / `summary` / `blocker` inline at the tool boundary so claims of done carry the evidence that makes them checkable.
- **Location**: `polecat/pkb_bridge.py` — `create_task` / `release_task` helpers (`completion_evidence` at L228; `release_task` at L313)
- **Scope**: polecat (primary); crew, interactive via PKB MCP
- **Status**: active

### L3 Workflow composition

#### Workflow composition layer (Phase 3 placeholder)

- **Pipeline layer**: L3 Workflow composition
- **Pyramid tier**: middle
- **Trigger**: n/a — not yet formalised
- **Purpose**: Task-creating agents compose compliant workflows from axioms, heuristics, and procedures at task-creation time (see `specs/enforcement.md` §9).
- **Location**: aspirational — Phase 3 of `task-e64e29c5` / `task-b5fec0b5` Thread 4
- **Scope**: polecat, crew, interactive
- **Status**: planned

### L4 Soft gates

#### CC auto-mode classifier

- **Pipeline layer**: L4 Soft gates (pre-execution, per tool call)
- **Pyramid tier**: middle (soft_deny → permission prompt) and tip (block / hard-deny rules)
- **Trigger**: every tool call, before execution, when CC is running in auto mode
- **Purpose**: Sonnet 4.6 pre-execution gate. Reads the proposed tool call alongside the conversation transcript and the prose `autoMode.environment` / `allow` / `soft_deny` / `block` rules, then judges whether to allow, surface a permission prompt (warn), or block. Treat it as **rbg-class judgment running at the per-action gate** — transcript-aware, prose-reasoning, fast.
- **Location**: rules in `aops-core/.claude-plugin/plugin.json` (`autoMode` key); merge logic and installation in `aops-core/lib/automode.py` (invoked by `scripts/install.py`).
- **Scope**: Claude Code only (polecat, crew, interactive — not Gemini, not GHA).
- **Status**: active. Rule wording carries P#-ID-style framing inherited from before the classifier was understood as judgment-capable; rewrite as prose-with-reasoning is `task-06db60dc`.
- **Design notes**: rule design implications — see `specs/ultra-vires-enforcer.md` §"Relationship to Claude Code auto mode". Rules state principle and reasoning so the classifier can apply them with judgment; do not write them as rule-ID lookups. Explicit user intent in conversation can override default rules; stated boundaries become block signals. The classifier's verdict surfaces to the user (permission UI), not to the agent's working context — for verdicts the framework needs to read and act on, use the enforcer subagent instead.

#### Hydration gate

- **Pipeline layer**: L4 Soft gates
- **Pyramid tier**: middle
- **Trigger**: session lifecycle events; evaluated by gate engine
- **Purpose**: Ensure hydration has fired before the agent proceeds with substantive work.
- **Location**: `aops-core/hooks/gate_config.py:398` (`HYDRATION_GATE_MODE`); no entry in `aops-core/lib/gates/definitions.py` — env var wired, gate body not yet present
- **Scope**: polecat, crew, interactive
- **Status**: warn-only — default `off`; verify

#### Enforcer gate

- **Pipeline layer**: L4 Soft gates
- **Pyramid tier**: middle
- **Trigger**: PreToolUse after `ENFORCER_TOOL_CALL_THRESHOLD` non-infrastructure tool calls since last verification
- **Purpose**: Periodically force a compliance verification by dispatching the enforcer subagent to read logs and certify the session is in-bounds.
- **Location**: `aops-core/agents/enforcer.md` + gate body in `aops-core/lib/gates/definitions.py:27`; env in `aops-core/hooks/gate_config.py:396` (`ENFORCER_GATE_MODE`, `ENFORCER_TOOL_CALL_THRESHOLD`)
- **Scope**: polecat, crew, interactive
- **Status**: active (mode per `ENFORCER_GATE_MODE` env var; default `warn` when unset)

#### QA gate

- **Pipeline layer**: L4 Soft gates
- **Pyramid tier**: middle
- **Trigger**: Stop event while gate is CLOSED; opened by qa/marsha subagent completion
- **Purpose**: Block exit until planned requirements have been verified by the QA agent.
- **Location**: `aops-core/lib/gates/definitions.py:71`; env in `aops-core/hooks/gate_config.py:395` (`QA_GATE_MODE`)
- **Scope**: polecat, crew, interactive
- **Status**: active — but `specs/enforcement.md` §3 flags the operational coverage as planned; verify

#### Unified logger

- **Pipeline layer**: L4 Soft gates (feeds L6 observability)
- **Pyramid tier**: base
- **Trigger**: every hook event routed through the gate engine
- **Purpose**: Write a single canonical per-event record so observability and agent review work against one log shape.
- **Location**: `aops-core/hooks/unified_logger.py`
- **Scope**: polecat, crew, interactive
- **Status**: active

### L5 Hard blocks

#### policy_enforcer.py

- **Pipeline layer**: L5 Hard blocks
- **Pyramid tier**: tip
- **Trigger**: PreToolUse; evaluated before any tool call
- **Purpose**: Hard-deny tool invocations that match policy rules (paths, binaries, credentials), independent of gate state.
- **Location**: `aops-core/hooks/policy_enforcer.py`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### settings.json deny rules

- **Pipeline layer**: L5 Hard blocks
- **Pyramid tier**: tip
- **Trigger**: harness-native permission check on every tool call
- **Purpose**: Host CLI's own deny/allow list — last line of defence that the agent cannot talk past.
- **Location**: `/.claude/settings.json` (project-level); user/global settings outside repo
- **Scope**: crew (primary); polecat, interactive via their own settings files
- **Status**: active — verify (this repo's `.claude/settings.json` currently declares only allow rules)

#### Credential isolation (agent-env-map)

- **Pipeline layer**: L5 Hard blocks
- **Pyramid tier**: tip
- **Trigger**: SessionStart; enforced through env-var scoping per agent
- **Purpose**: Prevent unrelated agents from inheriting credentials they should not hold.
- **Location**: `aops-core/hooks/session_env_setup.py:164` (applies `aops-core/agent-env-map.conf`)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Extension-write deny policy

- **Pipeline layer**: L5 Hard blocks
- **Pyramid tier**: tip
- **Trigger**: PreToolUse on write tools targeting plugin/extension paths
- **Purpose**: Prevent agents from overwriting installed plugin payloads during normal work.
- **Location**: `aops-core/policies/deny-extension-writes.toml`
- **Scope**: polecat, crew, interactive
- **Status**: active — verify

### L6 Observability

#### Session logs

- **Pipeline layer**: L6 Observability
- **Pyramid tier**: base
- **Trigger**: every hook event
- **Purpose**: Durable per-session record of every hook evaluation, tool call, and gate transition for later review.
- **Location**: `$AOPS_SESSIONS/{session_id}/hooks/` (resolved by `aops-core/lib/session_paths.py`)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Task-file append

- **Pipeline layer**: L6 Observability
- **Pyramid tier**: base
- **Trigger**: supervisor / worker agents append progress notes to the active task record
- **Purpose**: Keep narrative state on the task itself so interruption is recoverable and review has a single source.
- **Location**: referenced in `aops-core/skills/supervisor/` (supervision-loop / worker-dispatch) and `aops-core/commands/pull.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### STATUS.md

- **Pipeline layer**: L6 Observability
- **Pyramid tier**: base
- **Trigger**: maintained manually / by review agents
- **Purpose**: Repo-level source of truth on current state; input to strategic-review bots that need context beyond the PR diff.
- **Location**: `.agents/STATUS.md`
- **Scope**: all
- **Status**: active

### L7 Agent review

#### rbg (The Judge)

- **Pipeline layer**: L7 Agent review
- **Pyramid tier**: middle
- **Trigger**: commissioned by james or invoked directly for compliance audit
- **Purpose**: Axiom enforcement and compliance — produces parseable OK/WARN/BLOCK verdicts against framework axioms.
- **Location**: `aops-core/agents/rbg.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### enforcer agent

- **Pipeline layer**: L7 Agent review
- **Pyramid tier**: middle
- **Trigger**: dispatched by the enforcer gate when the tool-call threshold is crossed
- **Purpose**: Periodic compliance verification — reads session logs and certifies the session is in-bounds before releasing the counter.
- **Location**: `aops-core/agents/enforcer.md`; dump templates at `aops-core/hooks/templates/enforcer-*.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### qa / marsha

- **Pipeline layer**: L7 Agent review
- **Pyramid tier**: middle
- **Trigger**: commissioned by james or dispatched by QA gate
- **Purpose**: Runtime verification — assumes broken until proven otherwise, runs code and UI to produce PASS/FAIL/REVISE verdicts.
- **Location**: `aops-core/agents/marsha.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### pauli (Architect of Thought and Memory)

- **Pipeline layer**: L7 Agent review (also L8 handover)
- **Pyramid tier**: middle
- **Trigger**: commissioned by james for strategic review; dispatched by `/dump` for handover
- **Purpose**: Strategic / PKB-custodian review — keeps the knowledge graph coherent and assesses effectual strategy.
- **Location**: `aops-core/agents/pauli.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### james orchestrator

- **Pipeline layer**: L7 Agent review (also L9 review pipeline)
- **Pyramid tier**: middle
- **Trigger**: user invokes review, `/review-pr` skill calls it, or supervisor delegates
- **Purpose**: Multi-agent review orchestrator — commissions rbg/pauli/marsha, iterates, synthesises APPROVE/REVISE/ESCALATE.
- **Location**: `aops-core/agents/james.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

### L8 Handover

#### /dump skill

- **Pipeline layer**: L8 Handover
- **Pyramid tier**: middle → tip when the handover gate blocks Stop
- **Trigger**: user invokes `/dump`; may also fire via Pauli subagent or prompt-injected handover template
- **Purpose**: Comprehensive session close — commit, push, PR, task updates, follow-ups, Framework Reflection, halt.
- **Location**: `aops-core/skills/dump/SKILL.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Framework Reflection block

- **Pipeline layer**: L8 Handover
- **Pyramid tier**: middle
- **Trigger**: emitted as the very last output of `/dump`
- **Purpose**: Structured H2 section (`## Framework Reflection`) with `**Field**: value` lines so the reflection parser can extract signals post-session.
- **Location**: `aops-core/skills/dump/SKILL.md` (§ Framework Reflection Format, from ~L110)
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Handover gate

- **Pipeline layer**: L8 Handover
- **Pyramid tier**: tip
- **Trigger**: Stop event while gate CLOSED; opened by `/dump` completion
- **Purpose**: Block session exit until a handover has been produced, so work does not evaporate without a Framework Reflection.
- **Location**: `aops-core/lib/gates/definitions.py:111`; env in `aops-core/hooks/gate_config.py:394` (`HANDOVER_GATE_MODE`)
- **Scope**: polecat, crew, interactive
- **Status**: active (mode per `HANDOVER_GATE_MODE`; defaults to `warn` when unset)

#### Commit gate

- **Pipeline layer**: L8 Handover
- **Pyramid tier**: middle
- **Trigger**: evaluated during commit-time flows; env-controlled
- **Purpose**: Soft checkpoint that commits conform to repo policy (signing, hooks, message shape).
- **Location**: env in `aops-core/hooks/gate_config.py:399` (`COMMIT_GATE_MODE`); gate body not in `aops-core/lib/gates/definitions.py`
- **Scope**: polecat, crew, interactive
- **Status**: planned — verify (env wired, gate definition not yet present)

### L9 Review pipeline

#### review-pr skill (James local)

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: user invokes `/review-pr`
- **Purpose**: Local PR review orchestrator — James drives the review-and-revise cycle against a real PR, across repos.
- **Location**: `aops-core/commands/review-pr.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### pr-reviewer GHA

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: pull_request events (opened, synchronize, ready_for_review, reopened)
- **Purpose**: Server-side automated review comments on every PR push.
- **Location**: `.github/workflows/pr-review.yml`
- **Scope**: GHA
- **Status**: active

#### agent-enforcer GHA

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: PR / push event per workflow config
- **Purpose**: Server-side enforcement pass — applies axiom/enforcement checks on GHA where hooks cannot reach.
- **Location**: `.github/workflows/agent-enforcer.yml`
- **Scope**: GHA
- **Status**: active

#### Linter workflows

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: PR / push
- **Purpose**: Ruff lint+format, typecheck, and pytest as the sequential CI pipeline the PR must pass.
- **Location**: `.github/workflows/lint.yml`, `.github/workflows/typecheck.yml`, `.github/workflows/pytest.yml`, composed by `.github/workflows/pr-pipeline.yml`
- **Scope**: GHA
- **Status**: active

#### Framework-health workflow

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: scheduled / dispatch
- **Purpose**: Monitor framework-level invariants between PRs.
- **Location**: `.github/workflows/framework-health.yml`
- **Scope**: GHA
- **Status**: active — verify

#### validate-ruleset workflow

- **Pipeline layer**: L9 Review pipeline
- **Pyramid tier**: middle
- **Trigger**: PR touching ruleset files
- **Purpose**: Validate that ruleset / axiom declarations remain well-formed.
- **Location**: `.github/workflows/validate-ruleset.yml`
- **Scope**: GHA
- **Status**: active — verify

### L10 Merge gates

#### agent-merge-prep auto-merge

- **Pipeline layer**: L10 Merge gates
- **Pyramid tier**: tip
- **Trigger**: PR reaches merge-ready state; runs after review fixes
- **Purpose**: Apply agent-produced merge-prep fixes and enable auto-merge so PRs land once checks pass and a human approves.
- **Location**: `.github/workflows/agent-merge-prep.yml` (auto-merge at ~L271)
- **Scope**: GHA
- **Status**: active

#### merge-prep-cron

- **Pipeline layer**: L10 Merge gates
- **Pyramid tier**: tip
- **Trigger**: cron schedule
- **Purpose**: Periodic sweep that retries merge-prep across open PRs so stalled PRs get rechecked without user action.
- **Location**: `.github/workflows/merge-prep-cron.yml`
- **Scope**: GHA
- **Status**: active — verify

#### Branch protection

- **Pipeline layer**: L10 Merge gates
- **Pyramid tier**: tip
- **Trigger**: PR merge attempt
- **Purpose**: GitHub-native rule that requires passing checks + approvals before `main` accepts a merge.
- **Location**: TBD — verify at next pass (GitHub branch-protection config, not in repo tree)
- **Scope**: GHA
- **Status**: active — verify

#### Loop detector (merge-prep self-loop guard)

- **Pipeline layer**: L10 Merge gates
- **Pyramid tier**: tip
- **Trigger**: every merge-prep run inspects prior commit authorship
- **Purpose**: Skip merge-prep if the previous commit was itself merge-prep, and halt entirely after a ceiling of consecutive merge-prep commits, to stop runaway bot loops.
- **Location**: `.github/workflows/agent-merge-prep.yml:86-137` (loop-check + ceiling-check steps)
- **Scope**: GHA
- **Status**: active

#### Project-owner / admin approval

- **Pipeline layer**: L10 Merge gates
- **Pyramid tier**: tip
- **Trigger**: merge block; explicit approval required by branch-protection rules
- **Purpose**: Final human signoff — irreducible tip-tier check that the framework design explicitly preserves.
- **Location**: GitHub branch-protection + CODEOWNERS (not in repo tree)
- **Scope**: GHA
- **Status**: active — verify

### L11 Follow-up

#### Task-completion tracking

- **Pipeline layer**: L11 Follow-up
- **Pyramid tier**: base
- **Trigger**: `complete_task` / `release_task` tool calls
- **Purpose**: Record the close of work with schema-enforced evidence so later audits can reconstruct completion.
- **Location**: `polecat/pkb_bridge.py` (`release_task` L313); `mcp__plugin_aops-core_pkb__complete_task`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Unblocked-downstream surfacing

- **Pipeline layer**: L11 Follow-up
- **Pyramid tier**: base
- **Trigger**: daily / pull flows inspect `depends_on` edges when a task closes
- **Purpose**: Make newly unblocked tasks visible without requiring users to poll the graph.
- **Location**: `aops-core/skills/daily/` (progress-sync / briefing-and-triage) and `aops-core/commands/pull.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### Cross-reference PR / task / commit

- **Pipeline layer**: L11 Follow-up
- **Pyramid tier**: base
- **Trigger**: PR body / commit message conventions recognised by review agents
- **Purpose**: Bind evidence across surfaces — PR closes tasks, commits cite PRs, issues reference back — so the loop closes automatically.
- **Location**: cross-cutting; see `aops-core/skills/dump/SKILL.md` (PR/followup steps) and GitHub auto-close on `Fixes #…`
- **Scope**: all
- **Status**: active

### Evidence loop

#### /learn skill

- **Pipeline layer**: Evidence loop (Step 2)
- **Pyramid tier**: base
- **Trigger**: user or agent invokes `/learn` when a failure is observed
- **Purpose**: File an anonymised, RCA-schema GitHub issue in the framework repo, with dedup-by-search, as the canonical evidence capture path.
- **Location**: `aops-core/commands/learn.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### GitHub issues as evidence store

- **Pipeline layer**: Evidence loop (Step 3)
- **Pyramid tier**: base
- **Trigger**: filed via `/learn`; clustered by labels
- **Purpose**: Durable store — the issue list is the evidence base; volume × criticality informs priority for pattern detection.
- **Location**: GitHub issues on the framework repo (external; `aops-core/commands/learn.md` is the writer)
- **Scope**: all
- **Status**: active

#### /aops pattern detection

- **Pipeline layer**: Evidence loop (Steps 4–5)
- **Pyramid tier**: middle
- **Trigger**: periodic (intended) — read issue labels/bodies/close-status, detect recurring failure modes
- **Purpose**: Map patterns to pyramid layers where intervention needs to change, produce proposed enforcement adjustments.
- **Location**: aspirational — no `aops-core/commands/aops.md` present; principal known gap per `specs/enforcement.md` §5
- **Scope**: polecat, crew, interactive
- **Status**: planned

#### /retro skill (failure detection feed)

- **Pipeline layer**: Evidence loop (Step 1)
- **Pyramid tier**: base
- **Trigger**: user invokes `/retro`
- **Purpose**: Critical transcript review — reads recent sessions with a framework-dev lens and files issues via `/learn`.
- **Location**: `aops-core/commands/retro.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

#### /trend-review skill (failure aggregation feed)

- **Pipeline layer**: Evidence loop (Step 1)
- **Pyramid tier**: middle
- **Trigger**: user invokes `/trend-review`
- **Purpose**: Multi-session performance trend analysis across many transcripts/audit files, feeding the evidence loop with cross-session signal rather than per-session anecdotes.
- **Location**: `aops-core/commands/trend-review.md`
- **Scope**: polecat, crew, interactive
- **Status**: active

## Known-gap register

Mechanisms below are aspirational, partial, or cannot be fully verified from the current source tree. One-line note per entry states what is missing.

- **/aops pattern detection** — no implementation on disk; Steps 4–5 of the evidence loop unbuilt (`specs/enforcement.md` §5 principal gap).
- **QA gate operational coverage** — gate body present in `aops-core/lib/gates/definitions.py:71`, but `specs/enforcement.md` §3 still labels it "planned"; scope of "planned requirements" not yet codified.
- **Hydration gate body** — `HYDRATION_GATE_MODE` env var wired in `aops-core/hooks/gate_config.py:398` but no matching `GateConfig` in `aops-core/lib/gates/definitions.py`; currently a stub with default `off`.
- **Commit gate body** — `COMMIT_GATE_MODE` env var wired in `aops-core/hooks/gate_config.py:399` but no matching `GateConfig` in `aops-core/lib/gates/definitions.py`.
- **Enforcer rename historical note** — the custodiet→enforcer rename (agent, gate name, env-var surface `CUSTODIET_*` → `ENFORCER_*`) was executed as a hard break; see `specs/enforcement.md` §8 for operator impact.
- **Complexity-eval at capture** — referenced in planner disposition but no dedicated MCP tool surfaced in the visible PKB tool list; likely lives in the PKB server, not in-repo.
- **Inbox-default status** — policy is real (tasks capture without status default to inbox) but the enforcement is inside the PKB server, not verifiable from this repo tree.
- **Gate status strip** — rendering path not isolated to one module; spread across template registry + hydrator; needs a single reference location to be citable.
- **Workflow composition (L3)** — named as a pipeline layer for spec consistency; no concrete mechanism yet (`specs/enforcement.md` §9, Phase 3 placeholder).
- **Automatic `.agents/ENFORCEMENT-MAP.md` row updates** — evidence-loop Step 7 currently requires a manual map-row update in the closing PR.
- **Branch protection / admin approval** — configured in GitHub, not in-repo; presence assumed but not verifiable from the file tree.
- **settings.json deny rules** — this repo's `.claude/settings.json` currently lists only `allow` entries; any deny/deny-by-default policy must come from user/global settings, and is therefore out-of-tree and unverifiable here.
- **framework-health.yml / validate-ruleset.yml** — workflow files exist; their enforcement shape (what they block on, how loud they warn) not inspected in this pass.

---

**Related**

- **Operative state catalogue (SSoT)**: `.agents/ENFORCEMENT-MAP.md` — L0–L7 cost ladder + every mechanism row. `rbg` blocks on it (P#65).
- `specs/enforcement/enforcement.md` — design statement (read first).
- `specs/enforcement/enforcement-map.md` — redirect stub (superseded 2026-05-20 by `.agents/ENFORCEMENT-MAP.md`).
- `specs/enforcement/ultra-vires-enforcer.md` — enforcer agent + gate internal design.
