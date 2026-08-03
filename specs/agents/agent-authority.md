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

**Operative state**: `plugins/<plugin>/agents/<name>.md` frontmatter is the SSoT for what tools and permissions each agent holds. This spec defines the schema — fields, canonical tool naming, the four permissions axes, and skill/sub-agent delegation rules; the per-agent files are the binding declarations against it.

## Giving Effect

- [[rbg]] — Authority envelope this spec makes concrete
- [[enforcement]] — Five-layer enforcement model; this spec feeds L3/L4
- [[polecat-system]] — Enforces `fileAccess` and `bashScopes` at the worktree boundary
- `plugins/*/agents`, `.github/agents` — Must conform (GH Action agents: subset, see §GitHub Action Agents)

## Problem

Agent **permissions** (tools, servers, bash commands, file paths) and **skill delegation** are implied by prose and inconsistent frontmatter rather than declared. AI agents are biased toward action — left alone, they expand scope and take helpful shortcuts adjacent to the task. An agent writing to a file it wasn't supposed to touch is a planning failure, not a security incident. This spec makes the authority envelope explicit, machine-readable, and enforceable, so scope is visible before a task runs.

## Principles

1. **Deny-by-default.** An agent may call only what its frontmatter declares. Anything not listed is denied.
2. **Single source of truth.** Claude Code format is canonical. Other harnesses (agy, etc.) are produced by build-time translation.
3. **Skills stay portable.** Skills declare `allowed-tools` as the set the skill needs to function. Skills do not declare which agents may call them — that restriction lives on the agent side.
4. **Authority does not transit by spawning.** When agent A spawns agent B via the `Agent` tool, B runs with B's own declared authority. A does not hand B its tools.
5. **Authority does transit into skills.** When an agent invokes a skill via the `Skill` tool, the skill executes inside the agent's turn and is bounded by the agent's tool allowlist. The skill's `allowed-tools` states what the skill needs; the agent's `tools` states what the agent grants. Effective set = intersection.
6. **Declare intent, then enforce it.** Frontmatter is a public commitment about what an agent does, checked after the fact by the ultra-vires enforcer (L4) and blocked pre-execution by hooks (L5). The declaration is the specification; it is not itself the enforcement.
7. **Four orthogonal axes, independently closed.** Permissions are not one blob. Tools, MCP servers, bash commands, and filesystem paths are four distinct surfaces, each closed by default and opened explicitly. Granting one never implies another.

## Canonical Tool Naming

All agent and skill files use **Claude Code tool names**:

| Category          | Form                                    | Examples                                                                                                                                   |
| ----------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Built-in          | PascalCase                              | `Read`, `Edit`, `Write`, `Bash`, `Grep`, `Glob`, `Agent`, `Skill`, `TodoWrite`, `AskUserQuestion`, `WebFetch`, `WebSearch`, `NotebookEdit` |
| MCP               | `mcp__<server>__<tool>`                 | `mcp__services__pkb__search`, `mcp__playwright__browser_navigate`                                                                          |
| Plugin-scoped MCP | `mcp__plugin_<plugin>_<server>__<tool>` | `mcp__services__pkb__create_task`                                                                                                          |

Legacy snake_case names (`read_file`, `run_shell_command`, `mcp_playwright_browser_navigate`) are **not permitted** in source. The build script (see §Build Translation) translates to target-specific forms as needed.

## Agent Frontmatter Schema

Agent files live under `plugins/<plugin>/agents/<name>.md` (core) or `.github/agents/<name>.agent.md` (GitHub Actions). Frontmatter is YAML.

**Required:**

```yaml
name: <string>               # Canonical agent name (matches filename stem)
description: <string>        # One-line routing description (shown to callers)
model: <string>              # "inherit" | "haiku" | "sonnet" | "opus" | concrete id
tools: <list<string>>        # Tool allowlist (canonical names above). Empty list = no tools.
```

**Optional:**

```yaml
color: <string>              # Display hint; no authority semantics
mcpServers: <list<string>>   # MCP servers the agent may use. Implicitly grants every mcp__<server>__* tool. Use disallowedTools to narrow this set.
disallowedTools: <list<string>>  # Explicit denylist. Overrides grants from `tools` and `mcpServers`.
bashScopes: <list<string>>   # Named command families (e.g. git:read, gh:write, pytest). REQUIRED when `Bash` ∈ tools — see Bash Scopes below.
fileAccess:                  # Repo-relative read/write globs. REQUIRED when any of Read/Write/Edit/NotebookEdit/Glob/Grep ∈ tools — see Filesystem Paths below.
  read: <list<glob>>
  write: <list<glob>>        # optional; omit if no write needed
skills: <list<string>>       # Skill allowlist. If present, agent may invoke only these via the Skill tool. If omitted, no skill invocation is permitted.
subagents: <list<string>>    # Sub-agent allowlist for the Agent tool. If omitted, no subagent spawning is permitted.
permissionMode: <string>     # "default" | "bypassPermissions" | "plan". Default: "default".
maxTurns: <int | false>      # Turn budget. false = unlimited (orchestrator-class only).
effort: <string>             # "low" | "medium" | "high". Advisory only.
background: <bool>           # Default execution mode. Advisory.
isolation: <bool | "worktree">  # Default isolation mode. Advisory.
```

### Deny-by-default grid

| Field             | Omitted means                                              |
| ----------------- | ---------------------------------------------------------- |
| `tools`           | No tool calls permitted                                    |
| `mcpServers`      | No MCP servers                                             |
| `bashScopes`      | No bash — even with `Bash` in `tools`; lint rejects this   |
| `fileAccess`      | No filesystem access — lint rejects if `tools` requires it |
| `skills`          | No skill invocation                                        |
| `subagents`       | No sub-agent spawning                                      |
| `disallowedTools` | No explicit overrides                                      |
| `permissionMode`  | `"default"`                                                |
| `maxTurns`        | Harness default                                            |

### Known exception: `tools` omitted (harness materialization defect)

The deny-by-default default above is currently inverted by a harness defect: a
spawned custom agent whose frontmatter declares an explicit `tools` allowlist
receives only the harness's own built-in tools — no `mcp__*` tool and no
`ToolSearch` materializes, regardless of what the allowlist or `mcpServers`
grants (upstream: anthropics/claude-code#25200, #13898). The only path
confirmed to deliver the full tool pool, including MCP servers, is omitting
`tools` entirely — the agent then inherits its parent's complete effective set
instead of "no tool calls permitted."

**The same inversion held for `subagents` until this was ruled on: all five
agent files now declare it, each per its actual role.** `pauli`
(`plugins/pkb/agents/pauli.md`) is an open-ended dispatcher that routes to
whatever worker type a task needs, and declares `subagents: ["*"]`. `james`
(`plugins/orchestrate/agents/james.md`) declares the explicit list
`["rbg:rbg", "pkb:pauli", "orchestrate:marsha", "general-purpose"]` — the
three reviewers his own description names, plus the plain worker surface his
dispatch skill requires. `rbg` (`plugins/rbg/agents/rbg.md`) and `marsha`
(`plugins/orchestrate/agents/marsha.md`) declare `subagents: []` — neither's
own description involves spawning: rbg returns a verdict, marsha verifies and
never fixes. `ida` (`plugins/ida/agents/ida.md`) declares the explicit list
`["orchestrate:james", "pkb:pauli"]`, matching the only two delegation targets
named in its own file. The row now describes a real declaration on every agent
file, not an absent gate — though nothing yet enforces membership against it
(see Lint Rules below: the frontmatter lint that would check `subagents`
membership does not exist, so this remains a declared commitment rather than a
checked one). The claim at "No implicit orchestrator privilege" below — that
each orchestrator lists its `subagents` explicitly — is now true of the tree.

`plugins/orchestrate/agents/james.md` omits `tools` for this reason;
`plugins/pkb/agents/pauli.md`, `plugins/orchestrate/agents/marsha.md`, and
`plugins/rbg/agents/rbg.md` declare the wildcard `tools: ["*"]` rather than an
explicit allowlist, to the same end. Each of the four needs
`mcp__services__pkb__*` (or broader) to function at all, so an unenforced
grant is preferable to a materialized set of six built-ins. `plugins/ida/agents/ida.md` keeps its declared `tools` list — its
restriction is deliberate, but see the runtime finding below: declaring it does
not currently mean it is enforced. Consequence: RBG's ultra-vires review (L4
below) has no frontmatter ground truth for these four agents until the harness
is fixed and `tools` is restored. Restore `tools` on all four the moment
upstream ships a fix that lets an explicit allowlist materialize MCP tools
again.

**Re-verified: the prior 9/9 pauli failure did not reproduce, and the
previously-untested ida → pauli path works.** Five fresh trials against the
current tree (async spawns via the `Agent` tool, no worktree isolation,
notification-confirmed results): three direct `aops-pkb:pauli` spawns from a
full-effective-set parent each received `ToolSearch`, resolved
`mcp__plugin_aops-pkb_services__pkb__status` through it, and completed a live
call (`mem` 0.3.74, git `b2c6bd3`, release) — 3/3 PASS, where the prior session
recorded 9/9 FAIL with no `ToolSearch` and no `mcp__*` tool ever materializing.
Two further trials spawned `aops-pkb:pauli` from an `aops-ida:ida` parent — the
path this row exists to answer, previously untested — and both also reached
`ToolSearch`, resolved the same tool, and completed the same live call: 2/2
PASS. The hypothesis that ida's restricted `tools` declaration (no MCP grant)
would propagate to a spawned pauli and starve it of tools too is refuted by
direct observation. No cause for the reversal from 9/9 FAIL to 5/5 PASS is
confirmed — the plugin-scoped `.mcp.json` collision named as the leading
suspect in the prior record remains untested either way, and nothing here
rules it in or out. Prior PKB records (`aops_b2b3e821`, `task_2c737b81`)
describe this symptom as nondeterministic; this session's 5/5 PASS is
consistent with that framing rather than with the intervening 21-trial
session's fully deterministic split — treat pauli's PKB reachability as flaky
across sessions until a run reproduces a failure and identifies what varies
between runs. On this session's evidence, the reconcile-on-engagement design
this row exists to gate is operable on its intended path.

**New finding, not previously documented: ida's declared `tools` restriction
did not hold at runtime.** One of the two ida-parent trials reported ida's own
tool set directly: despite `plugins/ida/agents/ida.md` declaring
`tools: [Read, Skill, Agent, AskUserQuestion]`, the spawned ida's actual
top-level set was `Agent, Artifact, Bash, Edit, Read, Skill, ToolSearch, Write`
plus the full deferred `mcp__plugin_aops-pkb_services__*` namespace — Bash,
Edit, Write, and unrestricted PKB MCP access, none of which its frontmatter
grants. This is a different failure mode from the one this section otherwise
documents: that failure mode collapses an explicit allowlist to _fewer_ tools
(the harness's six built-ins, no MCP); this is an explicit allowlist being
ignored in favour of _more_ — the full parent session's effective set, the same
behaviour this section documents above for agents that omit `tools` entirely.
If declaring `tools` does not restrict a spawned agent when its parent holds a
broader set, no agent's declared allowlist is trustworthy ground truth for
RBG's review, not only the four that omit it. This needs its own investigation
and is out of scope for what this session verified; flagged here rather than
silently patched around, per this spec's own evidentiary standard.

### Wildcards

`skills` and `subagents` accept the single-element wildcard list `["*"]` meaning "any installed skill" / "any defined agent". The wildcard is an explicit, auditable declaration — the lint treats `["*"]` as a signal that the agent is intentionally open, not as a missing gate. Tools do not accept a wildcard: the `tools` list is always explicit.

### Effective tool set

```
effective = (tools ∪ expand(mcpServers)) ∖ disallowedTools
```

where `expand(mcpServers)` is every `mcp__<server>__*` tool surfaced by those servers at load time.

## Permissions Model

Four independent axes make up an agent's authority envelope. Each is closed by default; granting one axis does not open another.

**Tools.** An agent may call tool `T` iff `T ∈ effective(agent)`. The harness enforces this; RBG detects violations after the fact. Empty `tools` means no calls at all.

**MCP servers.** `mcpServers` grants whole-server access — appropriate when an agent genuinely needs an entire server's surface (e.g. PKB for research agents). To narrow to specific MCP tools, either omit `mcpServers` and enumerate in `tools`, or include `mcpServers` and list unwanted tools in `disallowedTools`.

**Bash scopes.** `Bash` in `tools` grants the ability to run shell commands — "which commands" is answered separately by `bashScopes`, using named families (`git:read`, `git:write`, `gh:read`, `gh:write`, `pytest`, `ruff`, `fs:read`, `fs:write`, `net:http`, `pkg:install`, `docker`, etc.). The concrete command patterns behind each family are defined by the bash-scope policy, not by this spec. Named families exist because the design-time question is "should a QA agent run tests?", not "should it run `pytest --tb=short -x`?". **`Bash` without any `bashScopes` is invalid and the lint rejects it.** The special value `unrestricted` grants any command; it must be declared explicitly, exists only for orchestrator-class agents, and always triggers a lint warning.

**Filesystem paths.** `fileAccess` applies when the agent holds any of `Read`, `Write`, `Edit`, `NotebookEdit`, `Glob`, or `Grep`. It declares which repo-relative path globs the agent may read and write:

```yaml
fileAccess:
  read:
    - "**/*"
  write:
    - "plugins/aops/skills/**"
    - "specs/**"
    - "!specs/archived/**"   # deny override; beats the grant above
```

A `!`-prefixed pattern is an explicit deny and beats any overlapping grant. Symlinks are denied outright — bash access could otherwise create one inside a granted directory pointing outside the worktree. **Any filesystem tool without `fileAccess` is invalid and the lint rejects it.** `fileAccess` narrows access _within_ the worktree only; it can never expand beyond it — paths outside the worktree are categorically denied by the polecat sandbox regardless of what `fileAccess` says. This spec declares the intent; the enforcing hooks and the polecat sandbox (`specs/polecat/polecat-system.md`) enforce it at the sharp edge.

## Skill Delegation

An agent may invoke skill `S` via the `Skill` tool iff (1) `Skill ∈ effective(agent)` and (2) `S ∈ agent.skills`. Skills are portable: they declare `allowed-tools` (what the skill needs), not which agents may call them. Invoking a skill temporarily extends the agent's turn; the effective tool set for that turn is `effective(agent) ∩ skill.allowed-tools`. If the intersection is empty for a required tool, the skill cannot run.

Portability here is the permission-control half of the personalities-are-not-skills doctrine ([[enforcement]] §Personalities are not skills): restricting which agent's frontmatter grants a tool a skill needs is a legitimate way to force a workflow shape (e.g. gating Playwright to the QA role), but it is capability wiring, not a claim that the skill itself belongs to one personality.

**Nested delegation.** A skill may itself invoke further skills or spawn sub-agents — only if the enclosing agent's `skills`/`subagents` list permits it. Nested invocation never expands authority; at every level the controlling envelope is the agent's own declared allowlists.

**No implicit orchestrator privilege.** Orchestrator agents (james, supervisor, planner) have no special spawning rights. Each lists its `subagents` explicitly. "Orchestrator" is a role description, not a permission class.

## Sub-agent Delegation (Agent tool)

An agent may spawn sub-agent `B` via the `Agent` tool iff (1) `Agent ∈ effective(agent)` and (2) `B ∈ agent.subagents`. The sub-agent runs with `B`'s own declared authority — the parent cannot hand the child tools it didn't declare (**authority-non-transit rule**: spawning is dispatch, not delegation of rights). A parent that needs broader action routes to an agent that already declares that authority, rather than endowing a child with more at runtime. This keeps permission scope auditable from a single file — "what can this agent do?" is answered by that agent's frontmatter alone, never a spawning chain. Only the prompt transits from parent to child.

## Build Translation

Claude Code frontmatter is the source of truth. Other harnesses receive translated output from `build/build.py`. Translation rules:

| From (Claude Code) | To (agy / google-adk)      |
| ------------------ | -------------------------- |
| `Read`             | `read_file`                |
| `Write`            | `write_file`               |
| `Edit`             | `replace`                  |
| `Bash`             | `run_shell_command`        |
| `Grep`             | `grep_search`              |
| `Glob`             | `glob`                     |
| `mcp__<s>__<t>`    | `mcp_<s>_<t>` (underscore) |

Translation is mechanical. Source files are never hand-edited to target form. Target output directories are build artifacts, not committed source.

## Lint Rules

**Not yet built.** `make lint` today runs `ruff check`, `scripts/check_refs.py`
(documented-path check), and `basedpyright` — none of which reads agent
frontmatter. The rules below specify what a frontmatter lint must enforce once
one exists; until then this section is a target, not a description of `make
lint`'s current behaviour, and nothing here is a CI blocker in practice.

The lint tool enforces:

1. **Schema conformance.** All required fields present; no unknown fields.
2. **Canonical naming.** No snake_case tool names in source.
3. **Referential integrity.** Every entry in `tools`, `mcpServers`, `skills`, `subagents` resolves to a real tool / server / skill / agent.
4. **No authority inflation in prose.** Agent body text does not instruct the agent to call tools absent from its allowlist.
5. **Skill `allowed-tools` present.** Every skill file under `plugins/*/skills/**/SKILL.md` declares `allowed-tools`.
6. **Bash requires scopes.** `Bash ∈ tools` without `bashScopes` is rejected.
7. **Filesystem tools require fileAccess.** Any of `Read`/`Write`/`Edit`/`NotebookEdit`/`Glob`/`Grep` in `tools` without `fileAccess` is rejected.
8. **`unrestricted` bashScope always warns**, regardless of agent class.

Violations are reported as `error` (1–3, 6, 7 — schema, naming, referential, and axis-completeness violations) or `warn` (4, 5, 8 — prose drift, missing skill metadata, and orchestrator-class exceptions). `error` is a CI blocker; `warn` is surfaced but non-blocking.

## Derived Agents

Some agents are thin wrappers over a canonical source persona rather than independent definitions. **`enforcer`** is the `rbg` persona reused on the PR pipeline: the workflow (`.github/workflows/agent-enforcer.yml`) concatenates `plugins/rbg/agents/rbg.md` with a PR-context framing wrapper (`.github/agents/enforcer.agent.md`) and runs it on Sonnet with `Bash,Read,Edit,Write` granted via `claude_args`.

## GitHub Action Agents

`.github/agents/*.agent.md` are prompts delivered to GitHub-hosted runs. They have no local frontmatter surface for tool allowlists — tools are granted via `claude_args` in the calling workflow. For this spec they MUST declare at minimum `name` and `description`, and SHOULD declare `tools: <list<string>>` (advisory, mirroring the `claude_args` grant set for audit — when present, the audit confirms the two match).

## Relation to the Ultra-Vires Scope and Other Specs

RBG is the post-hoc reviewer that flags activity outside declared authority. This spec feeds it directly: the agent's frontmatter is RBG's ground truth. A call to any tool, server, bash family, or filesystem path outside the declared set is flagged as mechanical overreach. The permissions layer is declarative; RBG is observational — a declaration without observation drifts silently, and observation without a declaration has nothing to check drift against.

The enforcement layers, from softest to hardest:

| Layer | Mechanism                      | When it acts        | On violation            |
| ----- | ------------------------------ | ------------------- | ----------------------- |
| L3    | This spec (frontmatter + lint) | At commit / CI      | Lint error              |
| L4    | Ultra-vires enforcer (RBG)     | Post-session review | Flag, surface, escalate |
| L5    | Policy hooks, polecat sandbox  | Pre-execution       | Hard block              |

L5 is the hard edge — a declaration cannot re-open a path an L5 hook blocks. An agent operating outside its declaration is flagged even if no hook caught it; the declaration is a binding commitment, not a configuration hint. (L3/L4/L5 here is a _local_ scheme for this spec; the former framework-wide enforcement pyramid's L0–L7 numbering was retired along with `ENFORCEMENT-MAP.md`, so there is no longer a numbered scheme to cross-reference it against.)

**Funnel/chokepoint pattern** (last resort only): deny a capability to all agents and grant it to exactly one that must invoke a specific skill (e.g. ida declares no PKB tools at all, so she reaches the graph only by commissioning `pkb:pauli`). Architecturally unforgeable but imposes a coordination tax on every gated call — deploy only after cheaper rungs (instruction → deterministic gate → post-hoc enforcer) demonstrably fail.

Related: **`specs/enforcement/enforcement.md`** (frontmatter is L3, lint is L4, hooks are L5); **`specs/polecat/polecat-system.md`** (enforces `fileAccess`/`bashScopes` at the worktree boundary). Plugin agents (when they exist) conform to this same schema; plugin-scoped MCP names follow `mcp__plugin_<plugin>_<server>__<tool>`.

## Non-Goals

- **Path-level enforcement mechanics.** `fileAccess` declares intent; the polecat sandbox and `policy_enforcer.py` hooks implement enforcement.
- **Rate or quota limits.** Handled by harness budgets.
- **Prompt content review.** Handled by rbg and the enforcer.
- **Per-operation timeouts.** Harness-level concern.
- **Runtime user approval prompts.** `permissionMode` is an interactive-UX hint, orthogonal to the declarative permissions defined here.
- **Cross-repo permissions.** Each repo's agent files are scoped to that repo; multi-repo coordination happens through the polecat dispatch layer.
