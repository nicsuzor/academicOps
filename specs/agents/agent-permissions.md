---
id: agents-f552b6c1
title: Agent Permissions — Design
type: spec
status: inbox
tier: core
depends_on: [agent-authority, ultra-vires-enforcer, enforcement, polecat-system]
tags: [spec, agents, permissions, governance]
created: 2026-04-23
---

# Agent Permissions — Design

**Status**: Draft. Sibling to [[agent-authority]]. Implementation tracked under parent `task-d380d98f`.

**Sibling spec (frontmatter schema)**: [[agent-authority]] (`specs/agents/agent-authority.md`) — the agent frontmatter schema, canonical tool naming, skill/sub-agent delegation rules, and the non-transit principle. Together with this file it constitutes the single logical spec for agent permissions. That file owns the structural schema; this file owns the four concrete axes (tools / mcpServers / bashScopes / fileAccess) and their lint requirements. Read both together.

**Operative state** (per-agent declarations): `aops-core/agents/<name>.md` frontmatter is the SSoT for what tools and permissions each individual agent holds. This spec defines the four-axis schema; the per-agent files are the binding declarations against that schema.

**Audit-artifact** (current-state snapshot): `specs/audit/AGENT-TOOLS.md` is the mechanical dump generated from the per-agent frontmatter for at-a-glance comparison. It is not a writeable source — drift is reported by it, not declared in it.

## Problem

Framework agents have organically accumulated permissions through implicit convention: if you are "the planner", you get filesystem access; if you are "the polecat runner", you get bash. Nobody decided this — it just accreted. The result is that we cannot audit what any agent is actually allowed to do, and the ultra-vires enforcer has no ground truth to check against.

The deeper problem is not technical. It is that **AI agents are biased toward action**. Left to their own devices, they expand scope, they find helpful shortcuts, they do things adjacent to the task because they seem useful. A well-meaning agent that writes to a file it was not supposed to touch is not a security incident — it is a planning failure. The permissions model is how we make "scope" visible before a task runs, not after.

This spec and [[agent-authority]] together constitute the framework's answer to that problem. `agent-authority.md` defines the conceptual envelope: which agents may spawn which, which skills are permitted, what it means for authority not to transit through spawning. This spec narrows to the _permissions surface_: which specific tools, servers, command families, and filesystem regions an agent may reach.

## Design Philosophy

Three principles shape every decision in this spec.

**Declare intent, then enforce it.** The permissions frontmatter is a public commitment about what an agent does. An agent that declares `bash_scopes: [git:read]` is saying: "I will read git history, nothing more." That declaration is then checked by the enforcer after the fact (L4) and blocked by hooks pre-execution (L5). The declaration is not the enforcement — it is the specification the enforcement reads from. This separation matters: design the right envelope first, then automate detection of violations.

**Deny-by-default, explicit grants only.** An agent may use only what its frontmatter explicitly names. An agent role, a helpful description, a parent's broader permissions — none of these confer anything. The only thing that grants authority is a field in the agent's own frontmatter. This is not paranoia; it is the only posture that makes permissions _auditable_. "What can this agent do?" must have a definite answer you can read off the file without simulating the agent's reasoning.

**Four orthogonal axes, independently closed.** The previous informal model treated "agent permissions" as one blob. In practice there are four distinct surfaces an agent can reach — tools, MCP servers, bash commands, filesystem paths — and they are independent. Granting tool access does not imply bash access. Granting bash does not imply filesystem write. Each axis is closed by default and opened explicitly. Omitting any axis closes it entirely, regardless of what the other axes say.

## The Four Axes

### Tools

`tools` is the allowlist of named tool invocations: built-in Claude Code tools (`Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `Agent`, `Skill`, etc.) and MCP tools by full name (`mcp__plugin_aops-core_pkb__search`). An agent may only call tools in this list. Empty list means no tool calls at all.

### MCP servers

`mcp_servers` is a convenience shorthand: listing a server name implicitly grants every tool that server exposes. It is appropriate when an agent genuinely needs an entire server's surface (e.g., the PKB server for research agents). To narrow, either omit `mcp_servers` and enumerate specific tools explicitly, or include `mcp_servers` and add unwanted tools to `disallowed_tools`.

The effective tool set is:

```
effective = (tools ∪ expand(mcp_servers)) ∖ disallowed_tools
```

### Bash scopes

`Bash` in the tools list grants the ability to run shell commands — but "which commands" is a separate question. `bash_scopes` answers it using named families: `git:read`, `git:write`, `gh:read`, `gh:write`, `pytest`, `ruff`, `fs:read`, `fs:write`, `net:http`, `pkg:install`, `docker`, and so on. The concrete command patterns for each scope live in `aops-core/policies/bash_scopes.toml`.

Why named families instead of raw command patterns? Because the permission question at design time is "should a QA agent be able to run tests?" not "should it be able to run `pytest --tb=short -x`?" Named scopes let you reason at the right level of abstraction. The patterns are a downstream implementation detail.

**Having `Bash` in `tools` without any `bash_scopes` is an invalid configuration.** Bash without scope bounds is effectively unrestricted shell access — that violates deny-by-default and the lint must reject it.

The special value `unrestricted` grants any command. It must be declared explicitly, exists only for orchestrator-class agents, and triggers a lint warning regardless.

### Filesystem paths

`file_access` applies when the agent holds any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, or `Grep`. It declares which repo-relative path globs the agent may read and write:

```yaml
file_access:
  read:
    - "**/*"
  write:
    - "aops-core/skills/**"
    - "specs/**"
    - "!specs/archived/**"   # deny override; beats the grant above
```

Patterns prefixed with `!` are explicit denies. A deny beats any overlapping grant. Paths outside the repo worktree are categorically denied by the polecat sandbox regardless of what `file_access` says — `file_access` can only narrow within the worktree, never expand beyond it.

Symlinks are denied outright. An agent that can execute bash commands could otherwise create a symlink inside a granted directory pointing to a sensitive path outside the worktree, bypassing the path check entirely.

**Having any filesystem tool without `file_access` is an invalid configuration.** As with bash without scopes, the lint must reject it.

## Agent Taxonomy and Harness Profiles

The permission axes combine into recognisable patterns. These are not formal types — they are common configurations with different risk profiles.

**Read-only analyst.** Has `Read`, `Glob`, `Grep`, `file_access.read`. No bash, no write, no MCP servers that mutate state. Can survey the codebase and report findings. Cannot change anything. Appropriate for review agents (rbg, Marsha in pure audit mode).

**PKB-only agent.** Has `mcp_servers: [pkb]`, no bash, no filesystem tools. Can read and write the knowledge base through the MCP API. Cannot touch the repo directly. Appropriate for lightweight capture agents.

**Task executor.** Has `Read`, `Write`, `Edit`, `Bash` with `git:read`, `git:write`, `gh:write`, plus `file_access` scoped to the relevant directories. Can do real work within a bounded scope. Most polecat workers.

**Orchestrator.** Has `Agent`, `Skill`, broad tool access, `bash_scopes: [unrestricted]` (declared explicitly). Can spawn sub-agents and route to skills. Bounded by the spawning rules in [[agent-authority]], not by tool restriction. James and the supervisor skill run at this level.

These profiles inform how to read an agent file quickly. A worker agent with `unrestricted` bash is anomalous. An orchestrator without `Agent` is probably misconfigured.

## Frontmatter Schema (Reference)

Agent files live under `aops-core/agents/<name>.md`. The full authority schema (including `skills`, `subagents`, `model`, `permissionMode`) is defined in [[agent-authority]] (`specs/agents/agent-authority.md`). This spec owns the four permissions fields:

```yaml
# From agent-authority.md (required context):
name: <string>
description: <string>
model: "inherit" | "haiku" | "sonnet" | "opus" | <model-id>
tools: [<tool-name>, ...]          # explicit allowlist; empty = no tools

# This spec adds:
mcp_servers: [<server-name>, ...]  # whole-server grants (optional)
disallowed_tools: [<tool>, ...]    # explicit deny; overrides grants (optional)
bash_scopes: [<scope>, ...]        # REQUIRED when Bash ∈ tools
file_access:                       # REQUIRED when any filesystem tool ∈ tools
  read: [<glob>, ...]
  write: [<glob>, ...]             # optional; omit if no write needed
```

The deny-by-default grid:

| Field              | Omitted means                                           |
| ------------------ | ------------------------------------------------------- |
| `tools`            | No tool calls                                           |
| `mcp_servers`      | No MCP server grants                                    |
| `bash_scopes`      | No bash (even if `Bash` in tools — lint rejects this)   |
| `file_access`      | No filesystem access (lint rejects if tools require it) |
| `disallowed_tools` | No explicit denies                                      |

## Authority Inheritance

When a parent agent spawns a child via the `Agent` tool, the child runs with its own declared permissions. The parent's permissions do not transit. There is no implicit inheritance anywhere in the graph.

This is a design choice, not a constraint imposed by the harness. It means:

- **Delegation is routing, not elevation.** A parent that needs broader action routes to an agent that declared that authority, not to a child it tries to endow at runtime.
- **Permission scope is auditable from the file.** You can answer "what can this agent do?" by reading one file. You never need to trace the spawning chain.
- **Skills are bounded differently from sub-agents.** A skill invoked via the `Skill` tool runs inside the calling agent's turn. Its effective tool set is the _intersection_ of what the skill needs and what the agent declared. Skills are library code in the caller's frame. Sub-agents are separate processes with their own frames. See [[agent-authority]] §Skill Delegation.

The only thing that transits from parent to child is the prompt — the context the parent chooses to pass. That is the bridging channel. Everything else is the child's own declaration.

## Relation to the Ultra-Vires Enforcer

`specs/enforcement/ultra-vires-enforcer.md` defines the L4 post-hoc reviewer that reads session narratives and flags activity outside declared authority. This spec feeds it directly: the agent's frontmatter is the enforcer's ground truth. A call to any tool, server, bash family, or filesystem path outside the declared set is a Type C (mechanical overreach) flag.

The permissions layer is declarative; the enforcer is observational. Neither alone is sufficient. A declaration without observation drifts silently — agents start doing things outside their envelope and no one notices. Observation without a declaration has nothing to enforce against — the reviewer cannot tell drift from legitimate evolution.

The enforcement layers, from softest to hardest:

| Layer | Mechanism                     | When it acts        | On violation            |
| ----- | ----------------------------- | ------------------- | ----------------------- |
| L3    | This spec (frontmatter lint)  | At commit / CI      | Lint error              |
| L4    | Ultra-vires enforcer          | Post-session review | Flag, surface, escalate |
| L5    | Policy hooks, polecat sandbox | Pre-execution       | Hard block              |

L5 is the hard edge. A declaration cannot re-open a path that an L5 hook blocks. Conversely, an agent that operates outside its declaration is flagged even if no hook caught it — the declaration is a binding commitment, not a configuration hint.

## Non-Goals

- **Rate and quota limits.** These are harness budgets, not permission decisions.
- **Prompt content review.** That is rbg's and the enforcer's domain.
- **Per-operation timeouts.** Harness-level concern, independent of the permissions surface.
- **Runtime user approval prompts.** The `permissionMode` field (in [[agent-authority]]) is a hint to the harness about interactive approval UX. It is orthogonal to the declarative permissions defined here.
- **Cross-repo permissions.** Each repo's agent files are scoped to that repo. Multi-repo coordination happens through the polecat dispatch layer, not through permissions extension.

## Open Questions

- **Per-skill file_access.** Should skills declare their own `file_access` requirements, with the effective grant being the intersection with the calling agent's declaration? Current position: no — skills declare `allowed-tools` for routing; path access is the agent's responsibility. Revisit if agents routinely need to grant broader access than intended because a skill requires it.

- **Scope registry location.** Named bash scopes must be registered somewhere concrete. Current proposal: `aops-core/policies/bash_scopes.toml`. Alternative: inline in the policy hook. The TOML file is preferred for reviewability.

- **Compliance migration cadence.** Existing agent files predate this spec and lack `bash_scopes` and `file_access`. The migration is tracked under `task-b5fec0b5`. Open question: when does lint enforcement escalate from warn to error for existing files?

## Cross-References

- [[agent-authority]] (`specs/agents/agent-authority.md`) — Sibling spec. Authority envelope: frontmatter schema, skill delegation, sub-agent spawning, non-transit rule. This spec narrows to the four permissions axes.
- `specs/enforcement/ultra-vires-enforcer.md` — Consumes this spec's schema as the ground-truth reference for detecting permission violations.
- `specs/enforcement/enforcement.md` — Five-layer enforcement model; this spec operates at L3 (structural declaration) and feeds L4/L5.
- `specs/agents/polecat-system.md` — Enforces `file_access` and `bash_scopes` at the worktree boundary for remote agent tasks.
- `task-1939d819` — Persona/knowledge/authority unification. This spec supplies the permissions layer; that task owns persona and knowledge layers.
- `task-4a6eb501` — Orchestrator boundary enforcement. Consumes `bash_scopes` and `tools` declared here.
- `task-b5fec0b5` — Framework structure formalisation; owns the migration of existing agent files to comply with this spec.
