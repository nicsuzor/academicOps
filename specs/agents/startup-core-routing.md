---
title: Startup Core Routing
status: ready
---

# Startup Core Routing

Framework agents receive shared core instructions, operational invariants, and repository mappings exclusively through the workspace startup file (`CLAUDE.md` and/or `AGENTS.md`) loaded by the runtime harness at session initialization, rather than via redundant, unexpanded import directives embedded in agent persona definitions.

## User stories

### US-1 Single Instruction Entry Point for Sessions

As an agent executing within a workspace, I want to receive shared core operational rules and project context automatically from the ambient startup file, so that I operate under consistent constraints without requiring persona-level imports.

- **AC-1.1** Given an execution session initialized under Claude Code, when the harness starts, then it loads `CLAUDE.md` and expands the `@` import directive pointing to `CORE.md` into ambient session context.
- **AC-1.2** Given an execution session initialized under Antigravity, when the session begins, then the harness loads `AGENTS.md` and its referenced `CORE.md` rules into ambient instruction context.
- **AC-1.3** Given an execution session initialized under OpenClaw, when the session initializes, then the harness loads the root workspace startup file (`CLAUDE.md` / `AGENTS.md`) and resolves core rules into session context.

### US-2 Clean Agent Definitions Without Redundant Imports

As a framework architect and maintainer, I want agent persona definitions to contain only persona-specific identity, capabilities, and behavioral rules, so that agent definitions remain independent of filesystem layout, require no build-time text inlining, and carry no dead directives.

- **AC-2.1** Given any framework agent definition under `plugins/*/agents/*.md`, when inspected in source, then it contains no `@` import lines or links to `CORE.md`.
- **AC-2.2** Given built plugin artifacts in distribution archives, when built for any supported client, then no agent markdown file contains references or imports to `CORE.md`.
- **AC-2.3** Given the plugin build system, when compiling agent definitions for distribution, then no text inlining, file interpolation, or AST parsing of imports is performed on agent prompt bodies.

## Design

### Architecture

The framework relies on a single, clear contract: **the startup file is the sole entry point to `CORE.md`.**

```
Workspace Root
├── CLAUDE.md / AGENTS.md  ──(native startup import)──>  .agents/CORE.md (or plugins/ida/CORE.md)
│                                                              ▲
└── plugins/ida/agents/                                        │
    ├── ida.md    ──(no CORE.md link)──────────────────────────┤
    ├── james.md  ──(no CORE.md link)──────────────────────────┤  (Clean persona definitions;
    ├── marsha.md ──(no CORE.md link)──────────────────────────┤   no unexpanded directives)
    ├── pauli.md  ──(no CORE.md link)──────────────────────────┤
    └── sara.md   ──(no CORE.md link)──────────────────────────┘
```

1. **Harness Startup Loading:**
   Every supported agent harness reads a designated startup file at session initialization:
   - **Claude Code**: Reads `CLAUDE.md` in the working directory root. Automatically follows and expands `@<path>` import directives relative to the importing file up to a maximum depth of 4 hops.
   - **Antigravity (`agy`)**: Reads `AGENTS.md` in the workspace root, loading its contents into active system instruction rules.
   - **OpenClaw**: Reads the root instruction files (`CLAUDE.md` / `AGENTS.md`) according to standard workspace configuration.

2. **Agent Definition Decoupling:**
   Agent persona definitions under `plugins/ida/agents/` (and all other plugin agent definitions) define role identity, purpose, and behavioral boundaries. Because harnesses load `CORE.md` into ambient session context at startup, persona definitions have no need to reference `CORE.md`. Directives such as `@../CORE.md` inside agent definitions are removed entirely.

3. **No Build-Time Inlining:**
   Build adapters for all clients (`build/clients/claude.py`, `build/clients/agy.py`, `build/clients/openclaw.py`) pass agent markdown bodies through without attempting to resolve or inline `@` file imports. Avoiding build-time inlining keeps distribution packages lightweight, prevents duplicate rule text across multiple subagent prompts, and relies strictly on native harness loading mechanisms.

### Per-Harness Loading Contract

| Harness | Startup File | Import Mechanism | Hop / Scope Limit | Agent Definition Behavior |
| :- | :- | :- | :- | :- |
| **Claude Code** | `CLAUDE.md` | Native `@` expansion | Max 4 hops from `CLAUDE.md` | Ignores `@` lines in `agents/*.md` (remains literal text). Ambient context supplies `CORE.md`. |
| **Antigravity (`agy`)** | `AGENTS.md` | Workspace rule ingestion | Root workspace file | Native persona loading. Ambient rules supply `CORE.md`. |
| **OpenClaw** | `CLAUDE.md` / `AGENTS.md` | Workspace instruction ingestion | Root workspace file | Standard persona loading. Ambient rules supply `CORE.md`. |

### Outcome-Level Build Criteria

Downstream implementation of this design must satisfy the following verifiable outcome-level criteria:

#### Goal 1: Startup File Links `CORE.md`

- **OBC-1.1**: The root workspace startup file (`CLAUDE.md`) in `academicOps` contains a valid, resolvable import pointing to `CORE.md` (`@.agents/CORE.md`).
- **OBC-1.2**: The root workspace startup file (`AGENTS.md`) in `academicOps` contains a valid, resolvable import pointing to `CORE.md` (`@.agents/CORE.md`).
- **OBC-1.3**: In all framework environments and templates, the workspace startup file maintains the single link to `CORE.md` within the 4-hop limit.

#### Goal 2: No Agent Definition Links `CORE.md`

- **OBC-2.1**: Zero occurrences of `@../CORE.md` or any `@` import directive across all source agent files in `plugins/*/agents/*.md`.
- **OBC-2.2**: Zero occurrences of `@` import directives or inlined `CORE.md` text blocks in built distribution agent files (`dist/*-claude/agents/*.md`, `dist/*-agy/agents/*.md`, `dist/*-openclaw/agents/*.md`).
- **OBC-2.3**: Build scripts and client adapters contain no custom file-inlining or AST import-resolution logic for agent prompt bodies.
- **OBC-2.4**: A repository-wide static test or assertion verifies that no agent markdown definition in source or build output contains links or imports to `CORE.md`.

## Enforcement Pyramid & Evidence for the Move

### Options Pass

1. **Doctrine (baseline)**: Universal Axioms (`single-source-of-truth`, `closure`, `proportionate`). Reaching `CORE.md` via one canonical route preserves a single source of truth without competing delivery mechanisms.
2. **Instructions (chosen mechanism)**: Native harness startup files (`CLAUDE.md` and `AGENTS.md`) provide the single route to `CORE.md`. Agent definitions are kept clean and modular.
3. **Friction (verification)**: A static assertion in the test suite verifies that agent definitions contain no `@` imports, preventing regressions.
4. **Tooling (rejected escalation)**: Programmatic build-time inlining of `CORE.md` into agent definitions (proposed in PR #3215) is rejected as disproportionate mechanism escalation. It adds 200+ lines of custom build parser code to compensate for harness-specific behaviors that are already handled natively by startup files.

### Evidence for the Move

- **Sentinel tests of harness loading**: Empirical sentinel test runs documented that Claude Code resolves `@` imports up to 4 hops exclusively from `CLAUDE.md`, leaving `@` lines inside agent definition bodies unexpanded as inert literal text.
- **Antigravity startup ingestion**: Antigravity natively loads `AGENTS.md` into active workspace rules, rendering redundant imports in agent definitions unnecessary.
- **Architectural clarity**: Establishing a single route through startup files eliminates duplicate copies of `CORE.md` in prompt context and honors the instruction modularity rule (`specs/meta/doc-taxonomy.md:25`).
