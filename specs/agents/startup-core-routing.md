---
title: Startup Core Routing
status: ready
---

# Startup Core Routing

Framework agents receive shared core instructions, operational invariants, and repository mappings through the workspace startup file (`CLAUDE.md` and/or `AGENTS.md`) loaded by the runtime harness into ambient session context at session initialization.

## User stories

### US-1 Single Instruction Entry Point for Sessions

As an agent executing within a workspace, I want to receive shared core operational rules and project context automatically from the ambient startup file, so that I operate under consistent constraints across all sessions.

- **AC-1.1** Given an execution session initialized under Claude Code, when the harness starts, then it loads `CLAUDE.md` and expands the `@` import directive pointing to `CORE.md` into ambient session context.
- **AC-1.2** Given an execution session initialized under Antigravity, when the session begins, then the harness loads `AGENTS.md` and its referenced `CORE.md` rules into ambient instruction context.
- **AC-1.3** Given an execution session initialized under OpenClaw, when the session initializes, then the harness loads the root workspace startup file (`CLAUDE.md` / `AGENTS.md`) and resolves core rules into session context.

### US-2 Modular Agent Definitions

As a framework architect and maintainer, I want agent persona definitions to contain only persona-specific identity, capabilities, and behavioral rules, so that agent definitions remain modular and compliant with craftsmanship standards.

- **AC-2.1** Given any framework agent definition under `plugins/*/agents/*.md`, when inspected in source, then it adheres to persona scope without external import directives.
- **AC-2.2** Given built plugin artifacts in distribution archives, when built for any supported client, then agent prompt bodies pass through without added inlined text blocks.
- **AC-2.3** Given the plugin build system, when compiling agent definitions for distribution, then agent prompt bodies pass through as raw text without transformation.

### US-3 Plugin-Scoped Startup Injection

As an agent operating outside a repository checkout or within client workspaces, I want each installed plugin to inject its plugin-scoped `CORE.md` into ambient session context at startup, so that I receive essential instructions for using and learning that plugin's features without extraneous or agent-specific text.

- **AC-3.1** Given any framework plugin loaded in a session, when `SessionStart` fires, then the plugin injects its plugin-scoped `CORE.md` (at most 20 lines) into ambient session context.
- **AC-3.2** Given a plugin-scoped `CORE.md`, when evaluated for admission, then every line passes the four tests: (1) valuable to all agents in every deployment, (2) every value presented works and is filled in, (3) nothing is duplicated, and (4) nothing is extraneous.
- **AC-3.3** Given the `ida` plugin's `CORE.md`, when inspected, then it instructs formatting Argdown assertions (`ida:argdown-toulmin`), evaluating incoming briefs per `ida:premise-check`, including valid Argdown blocks on all outgoing assertions, and routing PKB custody, planning, and all knowledge tasks exclusively to Pauli, with zero agent-specific rules.

## Design

### Architecture

The framework relies on a single, clear contract: **the startup file is the sole entry point to `CORE.md`.**

The harness loads `CORE.md` via the workspace startup file into ambient session context at initialization, making shared core instructions available to executing agents.

```
Workspace Root
└── CLAUDE.md / AGENTS.md  ──(native startup import)──>  CORE.md
                                                            │
                                             (ambient session context)
                                                            ▼
                                                   Active Agent Session
```

1. **Harness Startup Loading:**
   Every supported agent harness reads a designated startup file at session initialization:
   - **Claude Code**: Reads `CLAUDE.md` in the working directory root. Automatically follows and expands `@<path>` import directives relative to the importing file up to a maximum depth of 4 hops.
   - **Antigravity**: Reads `AGENTS.md` in the workspace root, loading its contents into active system instruction rules.
   - **OpenClaw**: Reads the root instruction files (`CLAUDE.md` / `AGENTS.md`) according to standard workspace configuration.

2. **Raw Build Adapter Pass-Through:**
   Client build adapters pass agent markdown bodies through as raw text without modification. This keeps distribution packages lightweight, prevents duplicate rule text across multiple subagent prompts, and relies strictly on native harness loading mechanisms.

### Per-Harness Loading Contract

| Harness | Startup File | Import Mechanism | Hop / Scope Limit | Agent Definition Behavior |
| :- | :- | :- | :- | :- |
| **Claude Code** | `CLAUDE.md` | Native `@` expansion | Max 4 hops from `CLAUDE.md` | Native persona loading. Ambient context supplies `CORE.md`. |
| **Antigravity** | `AGENTS.md` | Workspace rule ingestion | Root workspace file | Native persona loading. Ambient rules supply `CORE.md`. |
| **OpenClaw** | `CLAUDE.md` / `AGENTS.md` | Workspace instruction ingestion | Root workspace file | Standard persona loading. Ambient rules supply `CORE.md`. |

### Plugin-Scoped Startup Injection

When agents execute outside a repository checkout or within client workspaces, repository startup files (`CLAUDE.md` / `AGENTS.md`) are unreachable. To ensure universal baseline instructions and tool contracts are available in all execution contexts, each plugin injects its own plugin-scoped `CORE.md` via a `SessionStart` hook.

To protect prompt context budgets, every plugin `CORE.md` is strictly bounded to at most 20 lines and must contain zero agent-specific or extraneous rules.

#### Plugin Hook Inventory

The following table inventories current session startup hook registration across all repository plugins:

| Plugin | `SessionStart` Hook Registered? | Current Injected Content | Target State |
| :- | :- | :- | :- |
| `plugins/ida` | Yes (`Claude Code`: `dispatch.py claude SessionStart`; `agy`: `SessionStart` and `PreInvocation` pointer) | Formatted session metadata (`session`, `time`, `host`, `cwd`, `pkb`, `plugins`, `tracing`), single-line `PREMISE_CHECK_POINTER`, optional image staleness warning, optional credential isolation notification. | Reconcile hook to inject `plugins/ida/CORE.md` alongside metadata (max 20 lines). |
| `plugins/rbg` | No (hooks registered for `PreToolUse`, `Stop`, `SubagentStop`, and `PreInvocation` only; currently unwired) | None (0 hooks firing). | Wire `SessionStart` hook to inject `plugins/rbg/CORE.md` (max 20 lines). |
| `plugins/tools` | No (no hooks registered in manifest) | None. | Register `SessionStart` hook in manifest to inject `plugins/tools/CORE.md` (max 20 lines). |
| `plugins/aops-debug` | Yes (`Claude Code`: `dispatch.py claude SessionStart`; `agy`: `SessionStart`) | Executes `dump_payload` to write raw payload to temp file and emit debug trace; injects zero text into session context. | Retain debug tracing; inject `plugins/aops-debug/CORE.md` (max 20 lines). |
| `plugins/ida-telegram` | No (`PreToolUse` for `AskUserQuestion` only) | None. | Register `SessionStart` hook to inject `plugins/ida-telegram/CORE.md` (max 20 lines). |

#### Justification of Draft Plugin `CORE.md` Files Against the Four Tests

Every plugin's draft `CORE.md` is evaluated against the four tests for startup injection:

1. **Valuable to all agents in every deployment**: States cross-cutting requirements and routing entry points needed by any executing agent.
2. **Values filled in and working**: Every pointer, tool, skill name, and endpoint is operational and active.
3. **Nothing duplicated**: Omits general axioms, repository-local conventions, and agent-specific traits defined elsewhere.
4. **Nothing extraneous**: Contains zero historical context, incident narratives, or persona-specific directives.
5. **Length ceiling**: Strictly ≤ 20 lines.

| Plugin | Draft Lines | Test 1: Valuable to All | Test 2: Working & Filled | Test 3: No Duplication | Test 4: Nothing Extraneous |
| :- | :- | :- | :- | :- | :- |
| `plugins/ida` | 8 | Directs all agents to Argdown formatting, premise-check brief reviews, PKB custody and all knowledge tasks exclusively under Pauli, and dynamic workflow discovery. | Pointers to `ida:argdown-toulmin`, `ida:premise-check`, `ida:workflow-library`, and Pauli are active and functional. | Replaces 57-line legacy file; removes inlined agent persona blocks and git branch rules. | Contains only actionable directives; no persona voice, sub-agent spawning rules, or background essays. |
| `plugins/rbg` | 7 | Establishes the 3-tier rule hierarchy (Axioms → Project Rules → PKB User Rules), authority boundaries, and fail-fast invariant for all agents. | References to `rbg:axioms`, `.agents/rules/`, and `type: rule` match active runtime loaders. | Does not duplicate axiom bodies or test configurations. | Concise constraints and routing to `rbg` compliance review. |
| `plugins/tools` | 7 | Routes research pipeline tasks (analysis, transformations, plotting, publishing, diagramming) to specialized domain skills. | Pointers to `tools:analyst`, `tools:dbt`, `tools:streamlit`, `tools:python-viz`, `tools:pdf`, and `tools:diagram` exist and run. | Does not duplicate skill bodies or library options. | High-density routing pointers without implementation instructions. |
| `plugins/aops-debug` | 5 | Informs executing agents that diagnostic telemetry and payload logging are active with zero behavioral side-effects. | Telemetry endpoints and temp file logging match `handlers.py`. | Does not repeat OTel configuration or tracer internals. | 3 brief lines defining role and zero-side-effect invariant. |
| `plugins/ida-telegram` | 6 | Informs agents of Telegram channel constraints: expandable blockquote progressive disclosure, broker-routed user questions, and reaction standards. | Pointers to `AskUserQuestion` broker and `ida-telegram:telegram` skill are operational. | Does not repeat bot setup, authentication tokens, or web app internals. | Essential channel invariants only. |

### Outcome-Level Build Criteria

Downstream implementation of this design must satisfy the following verifiable outcome-level criteria:

#### Goal 1: Startup File Links `CORE.md`

- **OBC-1.1**: The root workspace startup file (`CLAUDE.md`) contains a valid, resolvable import pointing to `CORE.md`.
- **OBC-1.2**: The root workspace startup file (`AGENTS.md`) contains a valid, resolvable import pointing to `CORE.md`.
- **OBC-1.3**: In all framework environments and templates, the workspace startup file maintains the single link to `CORE.md` within the 4-hop limit.

#### Goal 2: Modular Agent Definitions

- **OBC-2.1**: Agent definitions under `plugins/*/agents/*.md` contain exclusively persona identity, behavior, output schemas, and routing.
- **OBC-2.2**: Built distribution agent files pass through without added inlined text blocks.
- **OBC-2.3**: Client build adapters pass agent prompt bodies through unaltered without custom file inlining.
- **OBC-2.4**: Ambient session context provides shared core rules without requiring persona-level imports.

#### Goal 3: Plugin-Scoped Startup Injection

- **OBC-3.1**: Every plugin provides a `CORE.md` in its root directory containing at most 20 lines of markdown instructions.
- **OBC-3.2**: Each plugin's `SessionStart` hook injects its plugin-scoped `CORE.md` into ambient session context at initialization.
- **OBC-3.3**: Every line in every plugin `CORE.md` passes the four tests: valuable to all agents in every deployment, values filled in, no duplication, and nothing extraneous.
- **OBC-3.4**: `plugins/ida/CORE.md` instructs using `ida:argdown-toulmin` and `ida:premise-check`, enforcing valid Argdown blocks on outgoing assertions, placing all durable context in the PKB, routing PKB curation, planning, and all knowledge tasks exclusively to Pauli, and carries zero agent-specific rules.

## Enforcement Map Extract

The following extract defines the enforcement register row for downstream merge upon implementation:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| `[Startup Core Routing](agents/startup-core-routing.md)` -- Every harness loads CORE.md at session start through workspace startup files and plugin-scoped `CORE.md` files via SessionStart hooks. | instructions, JIT injection | imperative, advisory | `specs/agents/startup-core-routing.md`: Workspace startup files provide canonical entry points to workspace `CORE.md`; plugin SessionStart hooks inject plugin-scoped `CORE.md` files (≤ 20 lines) into ambient session context at initialization. |

## Enforcement Options Pass & Evidence for the Move

### Options Pass

1. **Doctrine (baseline)**: Single source of truth, closure, and proportionality. Ambient context supplies shared rules to all executing agents.
2. **Instructions (selected mechanism for workspace)**: Native harness startup files (`CLAUDE.md` and `AGENTS.md`) provide the single route to workspace `CORE.md`.
3. **JIT injection (selected mechanism for plugins)**: `SessionStart` hooks inject plugin-scoped `CORE.md` files (≤ 20 lines) to reach agents running outside workspace checkouts without inlining rules into agent definitions or hardcoding repo paths.
4. **Structural: Block / Protection (rejected escalation)**: Programmatic build-time inlining of `CORE.md` into agent definitions is rejected as disproportionate mechanism escalation. It introduces unnecessary build parser complexity to compensate for harness behaviors already handled natively by startup files and hooks.

### Evidence for the Move

- **Sentinel tests of harness loading**: Empirical tests demonstrate that Claude Code resolves `@` imports up to 4 hops directly from `CLAUDE.md` into ambient context.
- **Antigravity startup ingestion**: Antigravity natively loads `AGENTS.md` into active workspace rules at session start.
- **Cross-directory execution reach**: When agents operate in client workspaces or outside the academicOps repository root, repository startup files are unread. Plugin-scoped `SessionStart` hooks provide the verified path for JIT injection of plugin invariants while strictly respecting the 20-line ceiling to preserve startup context quota.

### Regulatory Experiment Record

- **Hypothesis**: Injecting a bounded (≤ 20 lines) plugin-scoped `CORE.md` via `SessionStart` hooks provides agents operating outside the repository checkout or in client workspaces with essential plugin operational invariants and skill discovery routing without polluting context quota or introducing duplicate instructions into agent persona definitions.
- **What moved**: From zero startup injection for non-ida plugins (and legacy 57-line persona-bloated ida startup instructions) to JIT injection of concise (5–8 lines, bounded to max 20 lines) plugin-scoped `CORE.md` files at `SessionStart` across all five plugins (`ida`, `rbg`, `tools`, `aops-debug`, `ida-telegram`).
- **On what evidence**: When agents execute outside repository roots or within isolated client workspaces, ambient workspace startup files (`CLAUDE.md` / `AGENTS.md`) are unreachable, leaving agents without essential plugin routing (Argdown standards, rule hierarchy, research pipeline tools, diagnostic tracing, and channel invariants). Conversely, inlining rules into agent definitions at build time caused severe prompt bloat and duplication across subagent definitions.
- **Observation / Promotion Criteria**: Verified by `test_fresh_session_outside_deployment_repo_shows_plugin_core_md` and `test_every_shipped_plugin_session_start_hook_injects_core_md`: fresh sessions initialized outside any repository receive each installed plugin's `CORE.md` within ambient context, each file strictly bounded to at most 20 lines, with zero persona-specific or extraneous text.
- **Kill / Escalation Criteria**: If agent adherence to plugin invariants remains inadequate without enforcement, evaluate progressive escalation through specific turn-level advisory hooks. If session context usage from plugin startup files exceeds 5% of startup token budgets, compress or consolidate plugin entry points.
