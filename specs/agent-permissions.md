---
title: Agent Permissions — Tool Allowlists, MCP/Server Scoping, Deny-by-Default
type: spec
status: draft
tier: core
depends_on: [agent-authority, ultra-vires-enforcer, enforcement, polecat-system]
tags: [spec, agents, permissions, governance, enforcement]
created: 2026-04-23
---

# Agent Permissions — Tool Allowlists, MCP/Server Scoping, Deny-by-Default

**Status**: Draft. Sibling to `specs/agent-authority.md`. Lint and audit tooling tracked under parent `task-d380d98f`.

## Giving Effect

- [[specs/agent-authority.md]] — Broader authority envelope (skill delegation, sub-agent spawning, non-transit rule). This spec narrows to the **permissions surface**.
- [[specs/ultra-vires-enforcer.md]] — Consumes the permissions declaration as input to drift detection at L4.
- [[specs/enforcement.md]] — Frontmatter is an L3 (structural) control; the lint is L4 (detection); `policy_enforcer.py` and the polecat sandbox remain L5 (hard block).
- [[specs/polecat-system.md]] — Enforces `file_access` and `bash_scopes` at the worktree boundary.
- [[aops-core/agents/]] — All core agent files MUST conform.
- [[aops-core/hooks/policy_enforcer.py]] — Mechanical gate for path and command denials.

## Scope

This spec defines the **permissions** an agent is granted: which tools it may call, which MCP servers it may reach, which bash command families it may run, and which filesystem regions it may read or write. It is the mechanical surface the hooks, the enforcer, and the lint can all read.

It does **not** cover:

- **Skill delegation** and **sub-agent spawning** — see `specs/agent-authority.md` §Skill Delegation / §Sub-agent Delegation.
- **Authority non-transit** semantics between parent and child agents — see `specs/agent-authority.md` §Principles #4.
- **Prompt or persona content** — see `specs/agent-authority.md` §Derived Agents and the persona unification tracked under `task-1939d819`.

This spec and `agent-authority.md` share a single frontmatter schema; where they overlap (`tools`, `mcpServers`), this spec is the operational source of truth and `agent-authority.md` is the authority-semantics reference.

## Principles

1. **Deny-by-default.** An agent may call only what its frontmatter **explicitly declares**. Any tool, server, bash command, or filesystem path not listed is denied.
2. **Four orthogonal surfaces.** `tools`, `mcp_servers`, `bash_scopes`, and `file_access` are independent axes. Omitting any one closes that axis entirely.
3. **No implicit grants.** Role labels, agent names, group membership, and prose in the agent body confer nothing. Only declared fields grant authority.
4. **Narrowest form wins.** Where multiple fields could grant the same action, the **most specific deny** is honoured first (denylist overrides allowlist; path-level deny overrides scope grant).
5. **Declared, not derived.** The enforcer and the hooks read declared permissions verbatim. They never infer from the agent's description, persona, or past behaviour.
6. **Source of truth is Claude Code format.** Other harnesses (Gemini CLI, google-adk) receive translated output from `scripts/build.py`; see `agent-authority.md` §Build Translation.

## Permissions Model

### Four surfaces

| Surface       | Grants                                  | Enforced at                                                        |
| ------------- | --------------------------------------- | ------------------------------------------------------------------ |
| `tools`       | Named tool invocations (built-in + MCP) | Harness (L1), `policy_enforcer.py` (L5), ultra-vires enforcer (L4) |
| `mcp_servers` | Whole-server MCP access                 | Harness (L1); narrowed by `disallowed_tools`                       |
| `bash_scopes` | Bash command families the agent may run | `policy_enforcer.py` (L5), polecat sandbox                         |
| `file_access` | Filesystem read/write regions           | `policy_enforcer.py` (L5), polecat worktree, deny-extension-writes |

The permissions declaration is **intent**; L5 hooks and the polecat sandbox are the **sharp edges**. An agent declaring `bash_scopes: ["git:read"]` must still pass the hook check at call time — the declaration is necessary but not sufficient.

### Agent ↔ tool

An agent may call tool `T` iff `T ∈ effective(agent)` where

```
effective(agent) = (tools ∪ expand(mcp_servers)) ∖ disallowed_tools
```

`expand(mcp_servers)` is every `mcp__<server>__*` tool surfaced by the declared servers at load time.

### Agent ↔ MCP server

`mcp_servers` grants whole-server access. To narrow, either:

- Omit `mcp_servers` and enumerate specific tools in `tools`, or
- Include `mcp_servers` and list unwanted tools in `disallowed_tools`.

### Agent ↔ bash

If the agent holds `Bash ∈ tools`, the **command scope** is controlled by `bash_scopes`. Each scope is a named family whose concrete match patterns live in the hook. An empty or absent `bash_scopes` with `Bash ∈ tools` is an **invalid configuration** that the lint MUST reject (it is implicitly unlimited bash, which violates deny-by-default).

Standard scope names (extensible, maintained in `aops-core/policies/bash_scopes.toml`):

| Scope          | Grants                                                              |
| -------------- | ------------------------------------------------------------------- |
| `git:read`     | `git status`, `git log`, `git diff`, `git show`, `git branch`, etc. |
| `git:write`    | `git add`, `git commit`, `git push`, `git pull`, `git merge`, etc.  |
| `gh:read`      | `gh pr view`, `gh pr list`, `gh issue view`, etc.                   |
| `gh:write`     | `gh pr create`, `gh pr merge`, `gh issue create`, etc.              |
| `pytest`       | `pytest` with any args                                              |
| `ruff`         | `ruff check`, `ruff format`                                         |
| `fs:read`      | `ls`, `cat`, `head`, `tail`, `find` (read-only inspection)          |
| `fs:write`     | `mv`, `cp`, `rm`, `mkdir`, `rmdir`                                  |
| `net:http`     | `curl`, `wget`                                                      |
| `pkg:read`     | `uv pip list`, `npm list`                                           |
| `pkg:install`  | `uv pip install`, `npm install`                                     |
| `docker`       | `docker`, `docker compose`                                          |
| `unrestricted` | Any command. Wildcard — declared explicitly or not at all.          |

A scope may be granted without granting its paired `:write` variant. `git:read` without `git:write` is a valid read-only posture.

### Agent ↔ filesystem

If the agent holds any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, `Grep` in `tools`, the **paths** it may reach are controlled by `file_access`. Paths are repo-relative glob patterns. Each entry declares a mode:

```yaml
file_access:
  read:
    - "**/*"                   # any file
  write:
    - "aops-core/skills/**"
    - "specs/**"
    - "!specs/archived/**"     # explicit deny; overrides grant above
```

Semantics:

- `read` globs gate the `Read`, `Glob`, `Grep` tools and bash `fs:read` scopes.
- `write` globs gate the `Write`, `Edit`, `NotebookEdit` tools and bash `fs:write` scopes.
- Patterns prefixed with `!` are explicit denies and beat any overlapping grant (narrowest form wins).
- Omitting `file_access` with any filesystem tool in `tools` is an **invalid configuration** that the lint MUST reject.
- Paths outside the repo worktree are categorically denied by the polecat sandbox; `file_access` cannot re-open them.

### Deny-by-default grid

| Field              | Omitted means                                                   |
| ------------------ | --------------------------------------------------------------- |
| `tools`            | No tool calls permitted                                         |
| `mcp_servers`      | No MCP servers (only tools explicitly in `tools` are reachable) |
| `bash_scopes`      | No bash — even if `Bash ∈ tools`, every call is denied          |
| `file_access`      | No filesystem access — even if `Read`/`Write`/`Glob`/`Grep` ∈ `tools` |
| `disallowed_tools` | No explicit denylist                                            |
| `skills`           | No skill invocation (see `agent-authority.md`)                  |
| `subagents`        | No sub-agent spawning (see `agent-authority.md`)                |

## Frontmatter Schema

The schema extends the one declared in `specs/agent-authority.md` with two new fields (`bash_scopes`, `file_access`) and standardises the MCP server field name.

### Required

```yaml
name: <string>                # Canonical agent name (matches filename stem)
description: <string>         # One-line routing description
model: <string>               # "inherit" | "haiku" | "sonnet" | "opus" | concrete id
tools: <list<string>>         # Tool allowlist (canonical Claude Code names)
```

### Required when applicable

```yaml
bash_scopes: <list<string>>   # REQUIRED if `Bash` ∈ tools. Empty list means no bash allowed (and `Bash` should be dropped from tools).
file_access:                  # REQUIRED if any of Read/Write/Edit/NotebookEdit/Glob/Grep ∈ tools.
  read: <list<glob>>
  write: <list<glob>>
```

### Optional

```yaml
mcp_servers: <list<string>>   # Whole-server MCP grants. Alias: `mcpServers` (camelCase, Claude Code native). Lint accepts either; canonical is snake_case.
disallowed_tools: <list<string>>  # Explicit denylist. Overrides grants from `tools` and `mcp_servers`.
skills: <list<string>>        # Skill allowlist (see agent-authority.md).
subagents: <list<string>>     # Sub-agent allowlist for the Agent tool (see agent-authority.md).
permission_mode: <string>     # "default" | "bypass_permissions" | "plan". Default: "default".
max_turns: <int | false>      # Turn budget. false = unlimited (orchestrator-class only).
```

### Field naming reconciliation

Existing agent files (and `agent-authority.md`) use camelCase: `mcpServers`, `disallowedTools`, `permissionMode`, `maxTurns`. This spec prefers snake_case for new fields and declares snake_case as the canonical source form. The lint MUST accept both forms and emit a `warn` on camelCase; migration is tracked under `task-b5fec0b5`. Translation for non-Claude-Code harnesses (`scripts/build.py`) uses the canonical snake_case form as input.

### Wildcards

- `skills`, `subagents`, `mcp_servers` accept the single-element wildcard `["*"]` meaning "any installed". Wildcards are **explicit declarations**, not missing gates — the lint surfaces them at `info` level for audit.
- `tools`, `bash_scopes`, `file_access` do **not** accept a wildcard. Explicit enumeration only.
- `unrestricted` in `bash_scopes` is the reserved wildcard-equivalent for bash; it must appear alone and triggers a lint `warn` regardless of agent.

## Authority Inheritance

When a parent agent spawns a child via the `Agent` tool:

1. **Permissions do not transit.** The child runs with its own declared `tools`, `mcp_servers`, `bash_scopes`, and `file_access`. The parent cannot hand the child anything the child did not declare.
2. **Spawn authority is separate.** The parent may only spawn children named in its `subagents` list (see `agent-authority.md` §Sub-agent Delegation). The right to dispatch is independent of the rights the dispatched agent holds.
3. **No upward escalation.** A child cannot request or receive permissions beyond its own declaration, even if the parent holds them. If the task needs wider authority, the **task must be routed to a more-privileged agent**, not the current child elevated.
4. **Skills inherit, sub-agents do not.** When an agent invokes a skill via the `Skill` tool, the skill executes inside the agent's turn bounded by the agent's permissions (effective set = `agent.permissions ∩ skill.requirements`). When the agent spawns a sub-agent, the sub-agent's turn is its own. This asymmetry is intentional: skills are **library code** running in the caller's frame; sub-agents are **processes** with their own frame. See `agent-authority.md` §Skill Delegation for the controlling statement.
5. **Nested spawns close over the top.** If A spawns B and B spawns C, C's permissions are C's declaration — unaffected by A or B. At every level the controlling envelope is the child's own frontmatter.
6. **Parent MUST pass context, not authority.** A parent that needs a child to operate on a file must either (a) route to a child whose `file_access` covers that file, or (b) deliver the file contents in the spawn prompt. The parent's own `file_access` does not bridge.

### Inheritance table

| Channel          | Inherits from parent?                                                 |
| ---------------- | --------------------------------------------------------------------- |
| `tools`          | No — child's declaration governs                                      |
| `mcp_servers`    | No                                                                    |
| `bash_scopes`    | No                                                                    |
| `file_access`    | No                                                                    |
| Prompt / context | Yes — parent chooses what to pass (this is the only bridging channel) |
| Working dir      | Yes — polecat worktree is shared state; not a permissions channel     |

## Relation to Ultra Vires Enforcer

The enforcer (`specs/ultra-vires-enforcer.md`) is the L4 reviewer that reads session narratives and flags activity outside granted authority. Permissions declared under this spec feed the enforcer in three ways:

1. **Reference envelope.** The enforcer's per-agent authority reference is the agent's frontmatter (this spec's schema). A call to any tool / server / bash family / path outside the declared set is a **Type C — mechanical overreach** flag.
2. **Scope anchor.** Type A (reactive helpfulness) and Type B (deliberate scope expansion) judgments still depend on user intent, but the permissions declaration gives the enforcer a ground truth for what was even **possible** within authority. A refactor done via tools not declared cannot be excused as "in scope" regardless of intent.
3. **Compliance matrix.** Each agent's declared permissions are audited against observed calls in the `specs/agent-compliance-matrix.md` audit (`task-8544ef68`). Divergence feeds the enforcer's accuracy metrics and, where persistent, the lint's rule updates.

The permissions layer is **declarative**; the enforcer is **observational**. Neither alone is enough: a declaration with no observer drifts; an observer with no declaration has nothing to enforce against.

### Precedence vs. L5 hooks

| Layer | Mechanism                              | What it sees                               | Action on violation      |
| ----- | -------------------------------------- | ------------------------------------------ | ------------------------ |
| L3    | This spec (frontmatter structure)      | Declared permissions at load time          | Lint errors block CI     |
| L4    | Ultra-vires enforcer (post-hoc review) | Session narrative vs. declared permissions | Flag / revert / escalate |
| L5    | `policy_enforcer.py` hooks             | Each tool call / bash command / path write | Hard block pre-execution |

If an agent declares `git:write` but a hook in `policy_enforcer.py` blocks `git push --force`, the hook wins — declaration cannot re-open a mechanically blocked action. The inverse also holds: a tool call blocked by missing declaration is a Type C flag even if no hook caught it.

## Lint Rules (Permissions-specific)

In addition to the structural rules in `agent-authority.md` §Lint Rules:

1. **Bash without scopes.** `Bash ∈ tools` with `bash_scopes` absent or empty is an **error**.
2. **Filesystem tools without file_access.** Any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, `Grep` in `tools` with `file_access` absent is an **error**.
3. **Write without read.** `file_access.write` declared without `file_access.read` is an **error** (you cannot coherently write where you cannot read).
4. **Scope enumeration.** Every entry in `bash_scopes` MUST appear in `aops-core/policies/bash_scopes.toml`. Unknown scopes are **errors**.
5. **Path globs.** `file_access.read` / `.write` entries MUST be repo-relative and MUST NOT contain `..` or start with `/`. Absolute or traversal paths are **errors**.
6. **Wildcard drift.** `bash_scopes: ["unrestricted"]` or `file_access.write: ["**/*"]` outside a declared orchestrator-class agent is a **warn**.
7. **Naming.** camelCase field names (`mcpServers`, `disallowedTools`, etc.) are **warns**; lint accepts them and emits a migration hint.
8. **Coverage.** An agent whose body text instructs a bash command family not listed in `bash_scopes` is a **warn** (prose drift detection).

## Giving Effect — Implementation Order

The implementation work is decomposed under parent `task-d380d98f` and sibling planning tasks:

- `task-8ff8dac0` — Build translation + lint scaffolding (sibling).
- `task-8544ef68` — Compliance matrix for current agents (sibling).
- Follow-on: migrate existing agent files to populate `bash_scopes` and `file_access` (this spec is the schema input).
- Follow-on: `aops-core/policies/bash_scopes.toml` (new file; enumerates the standard scopes).
- Follow-on: `policy_enforcer.py` pre-tool-call check that reads the active agent's frontmatter and enforces this spec's rules at L5.

## Cross-References

- **`task-1939d819`** — Persona/knowledge/authority unification. This spec supplies the **permissions** layer; `task-1939d819` owns persona and knowledge layers.
- **`task-4a6eb501`** — Orchestrator boundary enforcement. Consumes the `subagents` allowlist declared under `agent-authority.md` and the `tools` / `bash_scopes` declared here.
- **`task-b5fec0b5`** — Framework structure formalisation. This spec is one of the structural artifacts it catalogues; owns the camelCase→snake_case migration.

## Non-Goals

- **Rate and quota limits.** Harness budgets, not a permissions concern.
- **Prompt content review.** rbg and the enforcer, not this spec.
- **Runtime permission prompting** (user-approves-each-call). Orthogonal to the declarative schema; `permission_mode` is a hint for the harness.
- **Per-operation timeouts.** Harness-level concern.

## Open Questions

- **Scope registry location.** `aops-core/policies/bash_scopes.toml` vs. inline in `policy_enforcer.py`. Current proposal: the TOML file, for reviewability.
- **Per-skill file_access.** Should skills declare their own `file_access` needs, intersected with the agent's grant? Current position: no — skills declare `allowed-tools` only; path access is the agent's responsibility.
- **Transitional `mcpServers` alias.** How long to support camelCase before lint promotes warn → error. Proposal: one audit cycle after `task-b5fec0b5` lands.
- **`file_access` symlink policy.** Current proposal: **deny symlinks outright** — consistent with the deny-by-default posture and eliminates the class of attacks where a Bash-capable agent creates a symlink inside an allowed directory pointing to a sensitive path outside the worktree. Alternative: follow symlinks with resolved-path check (resolved target must fall within the grant and the worktree). Revisit if a concrete case requires symlink traversal.
