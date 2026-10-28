---
title: Startup Core Routing
status: ready
---

# Startup Core Routing

Framework agents receive shared core instructions, operational invariants, and repository mappings exclusively through the workspace startup file (`CLAUDE.md` and/or `AGENTS.md`) loaded by the runtime harness at session initialization, rather than via redundant import directives embedded in agent persona definitions.

## User stories

### US-1 Single Instruction Entry Point for Sessions

As an agent executing within a workspace, I want to receive shared core operational rules and project context automatically from the ambient startup file, so that I operate under consistent constraints without requiring persona-level imports.

- **AC-1.1** Given an execution session initialized under Claude Code, when the harness starts, then it loads `CLAUDE.md` and expands the `@` import directive pointing to `CORE.md` into ambient session context.
- **AC-1.2** Given an execution session initialized under Antigravity, when the session begins, then the harness loads `AGENTS.md` and its referenced `CORE.md` rules into ambient instruction context.
- **AC-1.3** Given an execution session initialized under OpenClaw, when the session initializes, then the harness loads the root workspace startup file (`CLAUDE.md` / `AGENTS.md`) and resolves core rules into session context.

### US-2 Clean Agent Definitions Without Redundant Imports

As a framework architect and maintainer, I want agent persona definitions to contain only persona-specific identity, capabilities, and behavioral rules, so that agent definitions remain independent of filesystem layout and carry no dead directives.

- **AC-2.1** Given any framework agent definition under `plugins/*/agents/*.md`, when inspected in source, then it contains no `@` import lines or links to `CORE.md`.
- **AC-2.2** Given built plugin artifacts in distribution archives, when built for any supported client, then no agent markdown file contains references or imports to `CORE.md`.
- **AC-2.3** Given the plugin build system, when compiling agent definitions for distribution, then agent prompt bodies pass through as raw text without transformation.

## Design

### Architecture

The framework relies on a single, clear contract: **the startup file is the sole entry point to `CORE.md`.**

```
Workspace Root
├── CLAUDE.md / AGENTS.md  ──(native startup import)──>  CORE.md
│                                                           ▲
└── plugins/*/agents/                                       │
    └── <persona>.md       ──(no CORE.md link)──────────────┘
                           (Clean persona definitions;
                            no unexpanded directives)
```

1. **Harness Startup Loading:**
   Every supported agent harness reads a designated startup file at session initialization:
   - **Claude Code**: Reads `CLAUDE.md` in the working directory root. Automatically follows and expands `@<path>` import directives relative to the importing file up to a maximum depth of 4 hops.
   - **Antigravity**: Reads `AGENTS.md` in the workspace root, loading its contents into active system instruction rules.
   - **OpenClaw**: Reads the root instruction files (`CLAUDE.md` / `AGENTS.md`) according to standard workspace configuration.

2. **Agent Definition Decoupling:**
   Agent persona definitions define role identity, purpose, and behavioral boundaries. Because harnesses load `CORE.md` into ambient session context at startup, persona definitions have no need to reference `CORE.md`. Directives such as `@../CORE.md` inside agent definitions are removed entirely.

3. **Raw Build Adapter Pass-Through:**
   Client build adapters pass agent markdown bodies through as raw text without modification. This keeps distribution packages lightweight, prevents duplicate rule text across multiple subagent prompts, and relies strictly on native harness loading mechanisms.

### Per-Harness Loading Contract

| Harness | Startup File | Import Mechanism | Hop / Scope Limit | Agent Definition Behavior |
| :- | :- | :- | :- | :- |
| **Claude Code** | `CLAUDE.md` | Native `@` expansion | Max 4 hops from `CLAUDE.md` | Ignores `@` lines in `agents/*.md` (remains literal text). Ambient context supplies `CORE.md`. |
| **Antigravity** | `AGENTS.md` | Workspace rule ingestion | Root workspace file | Native persona loading. Ambient rules supply `CORE.md`. |
| **OpenClaw** | `CLAUDE.md` / `AGENTS.md` | Workspace instruction ingestion | Root workspace file | Standard persona loading. Ambient rules supply `CORE.md`. |

### Outcome-Level Build Criteria

Downstream implementation of this design must satisfy the following verifiable outcome-level criteria:

#### Goal 1: Startup File Links `CORE.md`

- **OBC-1.1**: The root workspace startup file (`CLAUDE.md`) contains a valid, resolvable import pointing to `CORE.md`.
- **OBC-1.2**: The root workspace startup file (`AGENTS.md`) contains a valid, resolvable import pointing to `CORE.md`.
- **OBC-1.3**: In all framework environments and templates, the workspace startup file maintains the single link to `CORE.md` within the 4-hop limit.

#### Goal 2: No Agent Definition Links `CORE.md`

- **OBC-2.1**: Zero occurrences of `@../CORE.md` or any `@` import directive across all source agent files in `plugins/*/agents/*.md`.
- **OBC-2.2**: Zero occurrences of `@` import directives or inlined `CORE.md` text blocks in built distribution agent files (`dist/*-claude/agents/*.md`, `dist/*-agy/agents/*.md`, `dist/*-openclaw/agents/*.md`).
- **OBC-2.3**: Client build adapters pass agent prompt bodies through unaltered without custom file inlining.
- **OBC-2.4**: No agent markdown definition in source or built distribution artifacts contains links or import directives to `CORE.md`.

## Enforcement Map Extract

The following extract defines the enforcement register row for downstream merge upon implementation:

| Rule | Mechanism | Severity | Detail |
| :- | :- | :- | :- |
| `[Startup Core Routing](agents/startup-core-routing.md)` -- Every harness reads CORE.md through its startup file (`CLAUDE.md` / `AGENTS.md`); agent definitions never link CORE.md. | instructions | imperative | `specs/agents/startup-core-routing.md`: Workspace startup files provide the sole route to `CORE.md` across all harnesses (Claude Code, Antigravity, OpenClaw); agent definitions carry no imports or links to `CORE.md`. Observation: Claude Code loads `CORE.md` via `CLAUDE.md` import up to 4 hops and ignores agent definition `@` imports; Antigravity loads `AGENTS.md` at session start. |

## Enforcement Options Pass & Evidence for the Move

### Options Pass

1. **Doctrine (baseline)**: Single source of truth, closure, and proportionality. Reaching `CORE.md` via one canonical route preserves a single source of truth without competing delivery mechanisms.
2. **Instructions (selected mechanism)**: Native harness startup files (`CLAUDE.md` and `AGENTS.md`) provide the single route to `CORE.md`. Agent definitions remain clean and modular.
3. **Structural: Friction / Verification (downstream check)**: Automated verification in the test suite ensures agent definitions contain no `@` imports, preventing regressions.
4. **Structural: Block / Protection (rejected escalation)**: Programmatic build-time inlining of `CORE.md` into agent definitions is rejected as disproportionate mechanism escalation. It introduces unnecessary build parser complexity to compensate for harness behaviors already handled natively by startup files.

### Evidence for the Move

- **Sentinel tests of harness loading**: Empirical tests demonstrate that Claude Code resolves `@` imports up to 4 hops exclusively from `CLAUDE.md`, leaving `@` lines inside agent definition bodies unexpanded as inert literal text.
- **Antigravity startup ingestion**: Antigravity natively loads `AGENTS.md` into active workspace rules, rendering redundant imports in agent definitions unnecessary.
- **Architectural clarity**: Establishing a single route through startup files eliminates duplicate copies of `CORE.md` in prompt context and maintains modular instruction boundaries.
