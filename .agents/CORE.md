# academicOps Project Context

This project contains the **academicOps** framework itself. You are currently working on the framework's source code.

### Where to find documentation

**Always check the specs directory first** for design intent, feature specs, methodology, or architecture decisions. The canonical home is `specs/`. Source code tells you what the system does _now_; specs tell you why and what it should do.

Specifically for this project:

- Specs: `specs/INDEX.md` (MOC) — read this first when scoping any change
- Project hub: [[aops|brain/projects/aops/aops]]
- Vision: [[vision|brain/projects/aops/vision]] (where applicable)
- Canonical taxonomy: `~/src/academicOps/aops-core/skills/remember/references/TAXONOMY.md`
- Framework Capabilities & Artifacts: `specs/CAPABILITIES.md`
- Agent Compliance Matrix: `specs/audit/AGENT-COMPLIANCE-MATRIX.md`
- Agent Tool Matrix: `specs/audit/AGENT-TOOLS.md`
- Agent Remediation Backlog: `specs/audit/AGENT-REMEDIATION-BACKLOG.md`

If you need to make a framework change, the spec is the contract. If the spec doesn't exist for the area you're touching, write or update one _first_ — don't ship undocumented framework changes.

If reading source code is your first move, you've skipped this step. Stop and check the PKB.

## Path Discovery (CRITICAL)

To discover project locations, read `.agents/INDEX.md` in the relevant repo. If the file is missing, STOP and report.

## Fail-Fast / Halt Rule (ENFORCED)

If you cannot do what was asked, **STOP and report** — do NOT search broadly, do NOT invent workarounds.

- **Missing Paths**: If a documented path does not exist, STOP and report.
- **No Broad Grep**: Never grep `$HOME` or `/` to find source repos or documents. Use `.agents/INDEX.md` for discovery.
- **Tool Failures**: If a tool doesn't work as documented, report the failure — do not invent alternatives.
- **Ambiguity**: If instructions conflict or are ambiguous, ask for clarification.
- **Unsatisfiable / out-of-scope AC**: If an acceptance criterion cannot be met _as written_ — it needs runtime access, a config/settings change outside your worktree, or a method you cannot run — HALT and report `blocked` with the specific impediment. Do NOT substitute an easier _adjacent_ action you _can_ perform and justify it against a loose reading of the AC; that is the streetlight effect (searching where the light is, not where the answer is). Per **A6b** you cannot weaken or substitute the criteria; per **A8** substituting a working-looking alternative is routing around a failure. This applies to methodology too: if a loaded methodology (e.g. a live self-test) requires a method you can't run, run it or halt — a synthetic stand-in is substitution, not the test.

## Safety Invariants (universal — all agents, all surfaces)

These are the universal safety floor. They are injected here at session start as the **single source of truth** for every agent (Junior, Ida, polecats, subagents) — not duplicated into individual agent definitions.

- **Safety Invariants**: Never read, store, or broker credentials. Never suggest weakening guardrails.
- **PKB-HALT**: If a PKB operation is needed and the required MCP verb is not available, **STOP immediately**. Emit `[ATTN] PKB verb missing: <verb> for <operation>` in the transcript and file a follow-up task via `create_task`. Do NOT invent a shell-out, an SSH escape, a file write, or any other workaround — routing around the PKB MCP is a security incident (aops-18572bc0 §5; the 2026-05-19 incident established this).

## Key Components

- **.agents/**: Instructions for working on the framework
- **aops-core/**: Framework core (hooks, enforcement, skills)
- **aops-tools/**: Additional tools and utilities
- **specs/**: Framework specifications and architecture
- **tests/**: All tests (at repo root, NOT in aops-core/). Subdirs: `hooks/`, `integration/`, `lib/`, `e2e/`

## Component Topology

Use this table to route `/q` captures and task decompositions to the correct `project` field. The `project` field drives polecat repo cloning and is **embedded permanently in task IDs** — getting it wrong creates tasks with the wrong ID prefix that cannot be renamed after creation.

| Task subject                                                            | Correct `project` | Wrong default |
| ----------------------------------------------------------------------- | ----------------- | ------------- |
| PKB MCP server code, knowledge graph internals, brain/                  | `mem`             | `aops`        |
| aops-core skills, hooks, gates, plugin packaging                        | `aops`            | —             |
| Polecat sandbox, container forwarding, agent-env-map                    | `aops`            | —             |
| Daily notes, $ACA_DATA layout, PKB content (not code)                   | `mem`             | `aops`        |
| Teaching tasks, course prep, QUT unit coordination, student interaction | `qut`             | `mem`         |

**Resolution order when the table is ambiguous or the subject is not listed**:

1. Look up the parent task via `get_task` and inherit its `project` field.
2. If the parent has no `project`, walk the ancestor chain until you find a project-typed node.
3. If the ancestor chain has no project, **STOP and ask the user** — do not default to any project slug.

**Rename-impossible constraint**: `update_task` can change the `project` frontmatter field but cannot rename the task ID. An ID like `mem-abc123` permanently signals `project=mem` to all routing consumers even after the frontmatter is corrected. File the task with the right project the first time.

## Core Agents

The framework uses named agents with distinct personalities and areas of expertise to provide qualitative judgment and oversight.

- **James (The Orchestrator)**: Manages multi-agent review loops and synthesises conflicting findings.
- **Ruth (rbg, The Judge)**: Enforces universal axioms and workflow discipline.
- **Pauli (The Logician)**: Provides strategic review, systems thinking, and acts as the Memory Custodian owning PKB-facing skills (`/remember`, `/planner`, `/dump`, `/daily`, `/sleep`).
- **Marsha (The QA Reviewer)**: Independently verifies work against original user intent.
- **Junior (The Assistant)**: General-purpose framework interaction — loads framework + project context from PKB, coordinates work, maintains institutional memory (`aops-state` PKB document).

## Tool Capabilities in Dispatched Sessions

Claude Code sessions dispatched from Cowork/Dispatch (or started locally on this machine) have access to significantly more tools than agents typically assume. When dispatched, sessions inherit the full local environment:

**Plugins and Skills:**

- **aops-core plugin**: All skills (`/planner`, `/supervisor`, `/qa`, `/strategic-review`, `/daily`, `/pull`, `/remember`, `/aops`, `/project`, `/sleep`, etc.) and named subagents (james, pauli, rbg, marsha, enforcer, etc.)
- **aops-tools plugin**: domain skills — `analyst`, `extract` (incl. doc-to-md), `diagram`, and others
- **Standard skills**: `docx`, `xlsx`, `pdf`, `pptx`, `canvas-design`, `mcp-builder`, `skill-creator`

**MCP Servers:**

- **PKB** (`mcp__plugin_aops-core_pkb__*`): Full task/document/graph/memory CRUD (~50 tools)
- **Outlook** (`mcp__outlook__*`): Messages, calendar, attachments, search
- **Discord** (`mcp__plugin_discord_discord__*`): Fetch/reply/edit/react
- **Computer-use** (`mcp__computer-use__*`): Full desktop automation (screenshot, click, type, scroll) — 30-min approval timeout for Dispatch-spawned sessions
- **Playwright** (`mcp__playwright__*`): Full headless browser automation — navigate, click, type, screenshots, JS evaluation, DOM inspection, console logs, network monitoring
- **Chrome tools**: `mcp__claude-in-chrome__*` for lightweight browser control; `mcp__Claude_Preview__*` for dev server preview/screenshot/interaction
- **context7**: Library documentation lookup via `mcp__context7__*`
- **Scheduled tasks**: Cron-style task scheduling

**Browser Testing for UI Work:**

- **Playwright MCP** (`mcp__playwright__*`): Full headless browser automation — navigate, click, type, take screenshots, evaluate JS, inspect DOM, check console, monitor network requests. Primary choice for UI QA in code sessions.
  - Ideal workflow: start dev server, navigate to it, screenshot each view, click to test interactions
  - Use Playwright for comprehensive UI testing and QA verification
- **Claude_Preview** (`mcp__Claude_Preview__*`): Dev server preview with screenshot/interaction — quick visual verification
- **Computer-use**: Full desktop automation with visual feedback — for cross-app workflows
- **Do NOT assume you lack browser access** — always check ToolSearch first before declaring a limitation

**Key Principle:** Always verify what tools are available via ToolSearch before assuming you can't do something. The tool set is richer than default Claude Code.

## Cross-Repository Safety

**NEVER modify files outside the current git repository without explicit user authorization.** If a bug is found in an upstream dependency, report it and file a task — do not edit the dependency directly. This applies to all skills, all agent types, and all platforms.

## Development Procedures

- **Pre-commit Hooks**: Run `./scripts/format.sh` before committing to avoid failures.
- **Testing**: Run tests using `uv run pytest tests/` or `uv run pytest aops-core/`.
- **Building**: Use `uv run python scripts/build.py` to build the distribution.
- **Installing**: Use `make install-dev` (orchestrator) or `uv run python scripts/install.py` to install locally. (`setup.sh` is a deprecated tombstone that forwards to `scripts/install.py`.)

## PR Review Management

- **Dismiss stale reviews** when you have addressed the reviewer's concerns or the human has overridden them.
- **Always include a clear dismissal message** explaining why: what was fixed, or which human decision overrides the concern.
- **Never dismiss a review you haven't addressed.**

## Agent Rules

- **Always leave a loose thread.** Before completing work that is part of a chain, file the next task in the PKB so the chain isn't dropped. A summary message in chat is not sufficient; it disappears when the user multitasks. Use `create_task` with a clear parent, title, and body.
- **File friction immediately.** When you encounter friction (tool limitations, bugs, missing instructions), invoke the `/learn` skill at the point of discovery. Do not ask "want me to file this?" or "happy to file if you confirm" — filing friction is unilateral. One friction = one `/learn` call.
- **Drive-by fix policy:** Bundle an unrelated fix into the current PR only when ALL of: (a) it is blocking your PR from merging (e.g. CI failure that's not your fault), (b) the fix is trivial and obvious, and (c) you can describe it in one sentence in the PR description. Otherwise, file a separate task — don't expand the PR scope.
- **Resume hints.** As your last act before stopping or waiting for user input, output a one-line summary prefixed with "Next Action:" or "Resume Hint:". This powers the cross-session command center.

See [[README.md]] for framework usage documentation.
