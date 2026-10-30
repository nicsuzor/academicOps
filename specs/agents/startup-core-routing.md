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

## Enforcement Map Extract

The following extract defines the enforcement register row for downstream merge upon implementation:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| `[Startup Core Routing](agents/startup-core-routing.md)` -- Every harness loads CORE.md at session start through its workspace startup file (`CLAUDE.md` / `AGENTS.md`). | instructions | imperative | `specs/agents/startup-core-routing.md`: Workspace startup files provide the canonical entry point to `CORE.md` across all harnesses (Claude Code, Antigravity, OpenClaw), establishing shared core instructions in ambient session context at initialization. Observation: Claude Code loads `CORE.md` via `CLAUDE.md` import up to 4 hops; Antigravity loads `AGENTS.md` at session start. |

## Enforcement Options Pass & Evidence for the Move

### Options Pass

1. **Doctrine (baseline)**: Single source of truth, closure, and proportionality. Loading `CORE.md` into ambient context at startup preserves a single source of truth without competing delivery mechanisms.
2. **Instructions (selected mechanism)**: Native harness startup files (`CLAUDE.md` and `AGENTS.md`) provide the single route to `CORE.md`. Ambient context supplies shared rules to all executing agents.
3. **Structural: Block / Protection (rejected escalation)**: Programmatic build-time inlining of `CORE.md` into agent definitions is rejected as disproportionate mechanism escalation. It introduces unnecessary build parser complexity to compensate for harness behaviors already handled natively by startup files.

### Evidence for the Move

- **Sentinel tests of harness loading**: Empirical tests demonstrate that Claude Code resolves `@` imports up to 4 hops directly from `CLAUDE.md` into ambient context.
- **Antigravity startup ingestion**: Antigravity natively loads `AGENTS.md` into active workspace rules at session start.
- **Architectural clarity**: Establishing a single route through startup files provides consistent core rules in ambient prompt context across all executing agents.
