# academicOps Project Context

This project contains the **academicOps** framework itself. You are currently working on the framework's source code.

## Path Discovery (CRITICAL)

To discover project locations, read `.agents/context-map.json` in the relevant repo. If the map is missing or any path it references does not exist, STOP and report.

## Fail-Fast / Halt Rule (ENFORCED)

If you cannot do what was asked, **STOP and report** — do NOT search broadly, do NOT invent workarounds.

- **Missing Paths**: If a documented path does not exist, STOP and report.
- **No Broad Grep**: Never grep `$HOME` or `/` to find source repos or documents. Use `context-map.json` for discovery.
- **Tool Failures**: If a tool doesn't work as documented, report the failure — do not invent alternatives.
- **Ambiguity**: If instructions conflict or are ambiguous, ask for clarification.

## Key Components

- **.agents/**: Instructions for working on the framework
- **aops-core/**: Framework core (hooks, enforcement, skills)
- **aops-tools/**: Additional tools and utilities
- **specs/**: Framework specifications and architecture
- **tests/**: All tests (at repo root, NOT in aops-core/). Subdirs: `hooks/`, `integration/`, `lib/`, `e2e/`

## Core Agents

The framework uses named agents with distinct personalities and areas of expertise to provide qualitative judgment and oversight.

- **James (The Orchestrator)**: Manages multi-agent review loops and synthesises conflicting findings.
- **Ruth (rbg, The Judge)**: Enforces universal axioms and workflow discipline.
- **Pauli (The Logician)**: Provides strategic review, systems thinking, and acts as the Memory Custodian owning PKB-facing skills (`/remember`, `/planner`, `/dump`, `/daily`, `/sleep`).
- **Marsha (The QA Reviewer)**: Independently verifies work against original user intent.
- **Jr (The Assistant)**: General-purpose framework interaction — loads framework + project context from PKB, coordinates work, maintains institutional memory (`aops-state` PKB document).

## Tool Capabilities in Dispatched Sessions

Claude Code sessions dispatched from Cowork/Dispatch (or started locally on this machine) have access to significantly more tools than agents typically assume. When dispatched, sessions inherit the full local environment:

**Plugins and Skills:**

- **aops-core plugin**: All skills (`/planner`, `/supervisor`, `/qa`, `/review-pr`, `/daily`, `/pull`, `/remember`, `/aops`, `/project`, `/sleep`, etc.) and named subagents (james, pauli, rbg, marsha, enforcer, etc.)
- **aops-cowork plugin**: `convert-to-md`, `analyst`, `extract`, `excalidraw`, `flowchart`, and others
- **Standard skills**: `docx`, `xlsx`, `pdf`, `pptx`, `canvas-design`, `mcp-builder`, `skill-creator`

**MCP Servers:**

- **PKB** (`mcp__plugin_aops-core_pkb__*`): Full task/document/graph/memory CRUD (~50 tools)
- **Outlook** (`mcp__outlook__*`): Messages, calendar, attachments, search
- **Discord** (`mcp__plugin_discord_discord__*`): Fetch/reply/edit/react
- **Computer-use** (`mcp__computer-use__*`): Full desktop automation (screenshot, click, type, scroll) — 30-min approval timeout for Dispatch-spawned sessions
- **Chrome tools**: `mcp__claude-in-chrome__*` for lightweight browser control; `mcp__Claude_Preview__*` for dev server preview/screenshot/interaction
- **context7**: Library documentation lookup via `mcp__context7__*`
- **Scheduled tasks**: Cron-style task scheduling

**Browser Testing for UI Work:**

- Agents working on UI (dashboard, web apps, frontend changes) should use **Claude_Preview** or **Control_Chrome** MCP tools to verify changes visually
- Playwright can be installed via npm for headless testing but requires explicit setup
- **Do NOT assume you lack browser access** — always check ToolSearch first before declaring a limitation

**Key Principle:** Always verify what tools are available via ToolSearch before assuming you can't do something. The tool set is richer than default Claude Code.

## Cross-Repository Safety

**NEVER modify files outside the current git repository without explicit user authorization.** If a bug is found in an upstream dependency, report it and file a task — do not edit the dependency directly. This applies to all skills, all agent types, and all platforms.

## Development Procedures

- **Pre-commit Hooks**: Run `./scripts/format.sh` before committing to avoid failures.
- **Testing**: Run tests using `uv run pytest tests/` or `uv run pytest aops-core/`.
- **Building**: Use `uv run python scripts/build.py` to build the distribution.
- **Installing**: Use `./setup.sh` or `uv run python scripts/install.py` to install locally.

## PR Review Management

- **Dismiss stale reviews** when you have addressed the reviewer's concerns or the human has overridden them.
- **Always include a clear dismissal message** explaining why: what was fixed, or which human decision overrides the concern.
- **Never dismiss a review you haven't addressed.**

## Agent Rules

- **Always leave a loose thread.** Before completing work that is part of a chain, file the next task in the PKB so the chain isn't dropped. A summary message in chat is not sufficient; it disappears when the user multitasks. Use `create_task` with a clear parent, title, and body.

See [[README.md]] for framework usage documentation.
