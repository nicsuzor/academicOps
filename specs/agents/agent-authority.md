---
id: agent-authority-spec
title: Agent Authority — Permissions and Skill Delegation
type: spec
status: ready
tier: core
depends_on: [rbg, enforcement, polecat-system]
tags: [spec, agents, agent-authority, governance, permissions, skill-delegation, framework]
created: 2026-04-21
---

# Agent Authority — Permissions and Skill Delegation

Agent frontmatter is the single source of truth for what an agent may do. This spec defines the schema — fields, canonical tool naming, the four permissions axes, and the delegation rules; the per-agent files under `plugins/*/agents` and `.github/agents` are the binding declarations against it.

## Giving Effect

- [[rbg]] — the authority envelope this spec makes concrete
- [[enforcement]] — five-layer enforcement model; this spec feeds L3/L4
- [[polecat-system]] — enforces `fileAccess` and `bashScopes` at the worktree boundary

## Problem

AI agents are biased toward action: left alone they expand scope and take helpful shortcuts adjacent to the task. An agent writing to a file it was not supposed to touch is a planning failure, not a security incident. Permissions and delegation implied by prose cannot be checked, so this spec makes the authority envelope explicit, machine-readable, and visible before a task runs.

## Principles

1. **Deny-by-default.** An agent may call only what its frontmatter declares.
2. **Single source of truth.** Claude Code format is canonical; other harnesses are produced by build-time translation.
3. **Skills stay portable.** A skill declares `allowed-tools` — the set it needs to function — and never which agents may call it. That restriction lives on the agent side.
4. **Authority does not transit by spawning.** When agent A spawns agent B, B runs with B's own declared authority. Only the prompt transits.
5. **Authority does transit into skills.** A skill invoked via the `Skill` tool executes inside the agent's turn, bounded by the agent's allowlist. Effective set = intersection.
6. **Declare intent, then enforce it.** Frontmatter is a public commitment, checked after the fact by the ultra-vires enforcer (L4) and blocked pre-execution by hooks (L5). The declaration is the specification, not the enforcement.
7. **Four orthogonal axes, independently closed.** Tools, MCP servers, bash commands, and filesystem paths are four distinct surfaces. Granting one never implies another.

## Canonical Tool Naming

All agent and skill files use Claude Code tool names:

| Category          | Form                                    | Examples                                                                                                                                   |
| ----------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Built-in          | PascalCase                              | `Read`, `Edit`, `Write`, `Bash`, `Grep`, `Glob`, `Agent`, `Skill`, `TodoWrite`, `AskUserQuestion`, `WebFetch`, `WebSearch`, `NotebookEdit` |
| MCP               | `mcp__<server>__<tool>`                 | `mcp__services__pkb__search`, `mcp__playwright__browser_navigate`                                                                          |
| Plugin-scoped MCP | `mcp__plugin_<plugin>_<server>__<tool>` | `mcp__services__pkb__create_task`                                                                                                          |

Snake_case names (`read_file`, `run_shell_command`, `mcp_playwright_browser_navigate`) are not permitted in source; the build script translates to target-specific forms.

## Claude Agent Frontmatter Schema

Agent files live under `plugins/<plugin>/agents/<name>.md` (core) or `.github/agents/<name>.agent.md` (GitHub Actions). Frontmatter is YAML.

**Required:**

```yaml
name: <string>               # Canonical agent name (matches filename stem)
description: <string>        # One-line routing description (shown to callers)
model: <string>              # "inherit" | "haiku" | "sonnet" | "opus" | concrete id
tools: <list<string>>        # Tool allowlist (canonical names above). Empty list = no tools.
```

**Optional — harness fields.** Valid in any agent or sub-agent file. All but `allowedTools` appear in the Claude Code agent-frontmatter schema itself.

```yaml
color: <string>              # Display hint; no authority semantics
mcpServers: <list<string>>   # MCP servers the agent may use. Implicitly grants every mcp__<server>__* tool.
allowedTools: <list<string>> # Permission rules in Tool(pattern) form — e.g. Agent(pauli), Skill(q), Bash(git *).
                             # Narrows *how* a granted tool may be called; `tools` grants the tool at all.
disallowedTools: <list<string>>  # Explicit denylist. Narrows the default set; the harness ignores it when `tools` is also set.
skills: <list<string>>       # Skill preload list. If omitted, no skills are preloaded.
hooks: <map>                 # PreToolUse / PostToolUse / Stop hooks scoped to this agent's lifetime.
memory: <string>             # Persistent memory scope: "user" | "project" | "local".
initialPrompt: <string>      # Auto-submitted first message when the agent runs as the main session (via --agent). Not read when spawned as a sub-agent.
permissionMode: <string>     # "default" | "dontAsk" | "acceptEdits" | "auto" | "bypassPermissions" | "plan". Default: "default".
maxTurns: <int | false>      # Turn budget. false = unlimited (orchestrator-class only).
effort: <string>             # "low" | "medium" | "high" | "max" | integer. Advisory only.
background: <bool>           # Default execution mode. Advisory.
isolation: <bool | "worktree">  # Default isolation mode. Advisory.
```

**Optional — academicOps-local.** Declared in the same frontmatter, consumed by this spec's lint and by the polecat sandbox rather than by the harness:

```yaml
bashScopes: <list<string>>   # Named command families (e.g. git:read, gh:write, pytest). REQUIRED when `Bash` ∈ tools.
fileAccess:                  # Repo-relative read/write globs. REQUIRED when any of Read/Write/Edit/NotebookEdit/Glob/Grep ∈ tools.
  read: <list<glob>>
  write: <list<glob>>        # optional; omit if no write needed
subagents: <list<string>>    # Sub-agent allowlist for the Agent tool. If omitted, no subagent spawning is permitted.
```

`tools`, `allowedTools`, and `disallowedTools` are three distinct surfaces, not variants of one field. `tools` is the capability grant; `allowedTools` is the approval rule set, in the same `Tool(pattern)` syntax the CLI's `--allowedTools` flag and `permissions.allow` accept, and is what lets a granted call proceed without a prompt under `permissionMode: dontAsk`; `disallowedTools` is the denylist. Removing any one changes what an agent may do or what it must stop and ask about.

**Unresolved:** `allowedTools` appears neither in the harness's own agent-definition schema nor in any reader under `build/`, so which component consumes an agent file's `allowedTools` is not established. Until a runtime trial settles it, treat it as a declared commitment on the same footing as `bashScopes` and `subagents`.

### Deny-by-default grid

| Field             | Omitted means                                                         |
| ----------------- | --------------------------------------------------------------------- |
| `tools`           | No tool calls permitted                                               |
| `mcpServers`      | No MCP servers                                                        |
| `bashScopes`      | No bash — even with `Bash` in `tools`; lint rejects this              |
| `fileAccess`      | No filesystem access — lint rejects if `tools` requires it            |
| `skills`          | No skills preloaded into prompt context                               |
| `subagents`       | No sub-agent spawning                                                 |
| `allowedTools`    | No pre-approved call patterns; every call falls through to the prompt |
| `disallowedTools` | No explicit overrides                                                 |
| `permissionMode`  | `"default"`                                                           |
| `hooks`           | No agent-scoped hooks                                                 |
| `memory`          | No persistent memory                                                  |
| `initialPrompt`   | No auto-submitted first turn                                          |
| `maxTurns`        | Harness default                                                       |

### Harness defect: an explicit `tools` list starves an agent of MCP

Deny-by-default is currently inverted by a harness defect. A spawned custom agent whose frontmatter declares an explicit `tools` allowlist receives only the harness's own built-in tools — no `mcp__*` tool and no `ToolSearch` materializes, regardless of what the allowlist or `mcpServers` grants (upstream: anthropics/claude-code#25200, #13898). The only path confirmed to deliver the full tool pool is omitting `tools` entirely, so that the agent inherits its parent's complete effective set.

The core agents work around it. `ida` (`plugins/aops/agents/ida.md`), `james` (`plugins/orchestrate/agents/james.md`), `marsha` (`plugins/orchestrate/agents/marsha.md`), `pauli` (`plugins/aops/agents/pauli.md`), and `rbg` (`plugins/rbg/agents/rbg.md`) all omit `tools`, and scope their roles through their bodies instead. Of those, only `marsha` narrows the inheritance by declaring `mcpServers`. `pc` (`plugins/orchestrate/agents/pc.md`) is the exception that still declares a real envelope: `tools: [Bash]` with `bashScopes: [uv, git, ssh]`, pairing `permissionMode: dontAsk` with an `allowedTools` list scoped to the same families.

**A declared allowlist has also been observed not to bind.** A spawned agent's actual top-level tool set was recorded as its parent session's effective set — including `Bash`, `Edit`, `Write`, and a full MCP namespace — while its own frontmatter granted none of them and denied several by name in `disallowedTools`. This is the opposite failure from the one above: there an explicit allowlist collapses to _fewer_ tools, here it is ignored in favour of _more_. The consequence binds RBG: no agent's declared allowlist is trustworthy ground truth for review until enforcement is demonstrated from the tool-call record rather than from an agent's own account of its capabilities.

Restore explicit `tools` allowlists on all agents once upstream ships a fix that lets an explicit allowlist reliably materialize MCP tools.

### Wildcards and bounded delegation

- `skills` accepts the single-element wildcard `["*"]`, meaning any installed skill — an explicit, auditable declaration that the agent is intentionally open.
- `subagents` in core plugin agents must be explicitly bounded, enumerated or omitted. Wildcard `subagents: ["*"]` is prohibited in core agents (`test_agent_declares_a_bounded_subagent_set`), to prevent unbounded recursive fan-out across nested spawns.
- `tools` does not accept a wildcard: it is always explicit or omitted.

### Effective tool set

```
effective  = (tools ∪ expand(mcpServers)) ∖ disallowedTools
unprompted = { calls matching allowedTools }              # under permissionMode: dontAsk
```

`expand(mcpServers)` is every `mcp__<server>__*` tool surfaced by those servers at load time. `effective` is what the agent may do; `unprompted` is the subset it may do without stopping for approval. An agent declaring both `tools` and `disallowedTools` is held to the intersection, irrespective of which the harness reads first.

## Permissions Model

Four independent axes, each closed by default.

**Tools.** An agent may call tool `T` iff `T ∈ effective(agent)`. The harness enforces this; RBG detects violations after the fact.

**MCP servers.** `mcpServers` grants whole-server access — appropriate where an agent needs an entire surface. To narrow, either omit `mcpServers` and enumerate in `tools`, or include it and list unwanted tools in `disallowedTools`.

**Bash scopes.** `Bash` in `tools` grants the ability to run shell commands; _which_ commands is answered separately by `bashScopes`, using named families (`git:read`, `git:write`, `gh:read`, `gh:write`, `pytest`, `ruff`, `fs:read`, `fs:write`, `net:http`, `pkg:install`, `docker`). The concrete patterns behind each family are the bash-scope policy's, not this spec's. Families exist because the design-time question is "should a QA agent run tests?", not "should it run `pytest --tb=short -x`?". `Bash` without `bashScopes` is invalid and the lint rejects it. The special value `unrestricted` grants any command, must be declared explicitly, exists only for orchestrator-class agents, and always warns.

**Filesystem paths.** `fileAccess` applies when the agent holds any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, or `Grep`, and declares which repo-relative globs it may read and write:

```yaml
fileAccess:
  read:
    - "**/*"
  write:
    - "plugins/aops/skills/**"
    - "specs/**"
    - "!specs/archived/**"   # deny override; beats the grant above
```

A `!`-prefixed pattern beats any overlapping grant. Symlinks are denied outright, because bash access could otherwise create one inside a granted directory pointing outside the worktree. Any filesystem tool without `fileAccess` is invalid and the lint rejects it. `fileAccess` narrows access _within_ the worktree and can never expand beyond it — paths outside are categorically denied by the polecat sandbox regardless of what it says.

## Skill Delegation

An agent may invoke skill `S` iff `Skill ∈ effective(agent)` and `S ∈ agent.skills`. Invoking a skill temporarily extends the agent's turn; the effective set for that turn is `effective(agent) ∩ skill.allowed-tools`. If the intersection is empty for a tool the skill requires, the skill cannot run.

Portability here is the permission-control half of the personalities-are-not-skills doctrine ([[enforcement]] §Personalities are not skills): withholding a tool a skill needs is a legitimate way to force a workflow shape — gating Playwright to the QA role, say — but that is capability wiring, not a claim that the skill belongs to one personality.

**Nested delegation.** A skill may invoke further skills or spawn sub-agents only where the enclosing agent's `skills`/`subagents` permit it. Nested invocation never expands authority.

**No implicit orchestrator privilege.** Orchestrator agents have no special spawning rights and must each list `subagents` explicitly — an obligation no shipped agent file currently meets, for the materialization reason above. "Orchestrator" is a role description, not a permission class.

## Sub-agent Delegation

An agent may spawn sub-agent `B` iff `Agent ∈ effective(agent)` and `B ∈ agent.subagents`. `B` runs with `B`'s own declared authority: spawning is dispatch, not delegation of rights. A parent needing broader action routes to an agent that already declares it rather than endowing a child at runtime, so that "what can this agent do?" is answered by one file and never by a spawning chain.

## Build Translation

Claude Code frontmatter is the source of truth; other harnesses receive translated output from `build/build.py`.

| From (Claude Code) | To (agy / google-adk)      |
| ------------------ | -------------------------- |
| `Read`             | `read_file`                |
| `Write`            | `write_file`               |
| `Edit`             | `replace`                  |
| `Bash`             | `run_shell_command`        |
| `Grep`             | `grep_search`              |
| `Glob`             | `glob`                     |
| `mcp__<s>__<t>`    | `mcp_<s>_<t>` (underscore) |

Translation is mechanical: source files are never hand-edited to target form, and target output directories are build artifacts rather than committed source. Where an agent needs genuinely client-specific instructions or frontmatter, write a native per-client file (`<name>.<client>.md`), which `resolve_client_agents` in `build/agents.py` resolves in place instead of translating.

## AGY Permissions

The permission engine inside agy (Jetski) checks tool requests against rules configured under `permissions` in `~/.gemini/antigravity-cli/settings.json`, each entry of the form `<action_type>(<target_or_pattern>)`.

| Action Type        | Scope                                                | Examples                                                                        |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| `mcp(...)`         | MCP server/tool calls                                | `mcp(services/pkb__status)`, `mcp(services/pkb__*)`, `mcp(services/*)`          |
| `read_file(...)`   | Reading files or directories (recursive for folders) | `read_file(/workspace/src/*)`, `read_file(/workspace/*.md)`                     |
| `write_file(...)`  | Creating, editing, or deleting files/directories     | `write_file(/workspace/dist/*)`, `write_file(/workspace/plugins/orchestrate/*)` |
| `command(...)`     | Shell commands via `run_shell_command`               | `command(git status*)`, `command(pytest*)`, `command(make build*)`              |
| `read_url(...)`    | Fetching web content via `read_url_content` / HTTP   | `read_url(https://antigravity.google/*)`                                        |
| `execute_url(...)` | Remote script/action execution via web endpoints     | `execute_url(https://api.github.com/*)`                                         |
| `unsandboxed(...)` | Commands running outside container boundaries        | `unsandboxed(docker *)`                                                         |

Workspaces the engine will act in at all are listed under `trustedWorkspaces`.

## Lint Rules

**Not yet built.** `make lint` runs `ruff check`, `scripts/check_refs.py`, and `basedpyright` — none of which reads agent frontmatter. This section specifies what a frontmatter lint must enforce; until one exists, nothing here blocks CI.

1. **Schema conformance.** All required fields present; no unknown fields.
2. **Canonical naming.** No snake_case tool names in source.
3. **Referential integrity.** Every entry in `tools`, `mcpServers`, `skills`, `subagents` resolves to a real tool / server / skill / agent.
4. **No authority inflation in prose.** Agent body text does not instruct the agent to call tools absent from its allowlist.
5. **Skill `allowed-tools` present.** Every `plugins/*/skills/**/SKILL.md` declares `allowed-tools`.
6. **Bash requires scopes.** `Bash ∈ tools` without `bashScopes` is rejected.
7. **Filesystem tools require fileAccess.** Any of `Read`/`Write`/`Edit`/`NotebookEdit`/`Glob`/`Grep` in `tools` without `fileAccess` is rejected.
8. **`unrestricted` bashScope always warns**, regardless of agent class.

Rules 1–3, 6, and 7 report as `error` and block CI. Rules 4, 5, and 8 — prose drift, missing skill metadata, orchestrator-class exceptions — report as `warn` and are surfaced without blocking.

## Derived and GitHub Action Agents

Some agents are thin wrappers over a canonical persona. **`enforcer`** is the `rbg` persona on the PR pipeline: `.github/workflows/agent-enforcer.yml` concatenates `plugins/rbg/agents/rbg.md` with a PR-context framing wrapper (`.github/agents/enforcer.agent.md`) and runs it on Sonnet with `Bash,Read,Edit,Write` granted via `claude_args`.

`.github/agents/*.agent.md` are prompts delivered to GitHub-hosted runs. They have no local frontmatter surface for tool allowlists — tools are granted via `claude_args` in the calling workflow — so they must declare at minimum `name` and `description`, and should declare `tools: <list<string>>` mirroring the `claude_args` grant set, which the audit then confirms matches.

## Relation to RBG and the Enforcement Layers

RBG is the post-hoc reviewer that flags activity outside declared authority, and this spec's frontmatter is its ground truth: a call to any tool, server, bash family, or filesystem path outside the declared set is mechanical overreach. The permissions layer is declarative and RBG is observational — a declaration without observation drifts silently, and observation without a declaration has nothing to check drift against.

| Layer | Mechanism                      | When it acts        | On violation            |
| ----- | ------------------------------ | ------------------- | ----------------------- |
| L3    | This spec (frontmatter + lint) | At commit / CI      | Lint error              |
| L4    | Ultra-vires enforcer (RBG)     | Post-session review | Flag, surface, escalate |
| L5    | Policy hooks, polecat sandbox  | Pre-execution       | Hard block              |

L5 is the hard edge: a declaration cannot re-open a path an L5 hook blocks. An agent operating outside its declaration is flagged even where no hook caught it, because the declaration is a binding commitment rather than a configuration hint. L3/L4/L5 is a scheme local to this spec; [`specs/ENFORCEMENT-MAP.md`](../ENFORCEMENT-MAP.md) indexes every enforcement mechanism by name and is the live state register.

**Funnel/chokepoint pattern** (last resort): deny a capability to every agent and grant it to exactly one that must be commissioned to use it — ida declares no PKB tools at all and reaches the graph only through `aops:pauli`. Architecturally unforgeable, but it taxes every gated call, so deploy it only after the cheaper rungs of the ladder in [`specs/enforcement/enforcement.md`](../enforcement/enforcement.md#the-escalation-ladder-the-enforcement-pyramid) — instruction, tooling and affordances, deterministic gates and post-hoc enforcers, code prohibitions — demonstrably fail.

Path enforcement itself is [`specs/polecat/polecat-system.md`](../polecat/polecat-system.md), which applies `fileAccess` and `bashScopes` at the worktree boundary.

## Non-Goals

- **Path-level enforcement mechanics.** `fileAccess` declares intent; the polecat sandbox and `policy_enforcer.py` hooks implement it.
- **Rate or quota limits.** Harness budgets.
- **Prompt content review.** rbg and the enforcer.
- **Per-operation timeouts.** Harness-level.
- **Runtime approval machinery.** `permissionMode` and `allowedTools` are load-bearing frontmatter and are specified above; the prompting mechanism they drive is not this spec's. They govern _how_ a call is approved, never _whether_ it is within the envelope.
- **Cross-repo permissions.** Each repo's agent files are scoped to that repo; multi-repo coordination happens through the polecat dispatch layer.
