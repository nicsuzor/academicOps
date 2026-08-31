---
status: draft
tier: 2
type: spec
title: Orchestrator client split, polecat default agent, and ida routing
tags: [agents, polecat, james, ida, mcp, build]
created: 2026-08-15
---

# Orchestrator client split, polecat default agent, and ida routing

`james` runs by default inside every polecat container, on both agy and claude.
`ida`, outside the container, reaches work only through `pc`. No hook blocks on
any exit path — advice injection only.

Open objections and unresolved prerequisites are in
[orchestrator-client-split-review.md](orchestrator-client-split-review.md).

## Already landed

Verified in the working tree; these parts of the original design need no further
work and are retained here only so the remainder reads correctly.

- `plugins/orchestrate/agents/agy.md` ships enabled (no `.disable` suffix) and
  already carries the client-conditional form: a section that tells an occupant
  already running agy to ignore the launch instructions below it.
- `lib/polecat/cli.py` has a paired `--agent` / `--no-agent`, not a magic
  `--agent none` sentinel.
- `plugins/orchestrate/agents/pc.md` executes the commands it documents rather
  than building an unrun variable, and its `Bash` grant covers what it runs
  (`uv run`, `git`, `ssh`, `tailscale ssh`).
- `specs/ARCHITECTURE.md` no longer claims a blocking `orchestrate` `Stop` hook.
- `ida.md` now lives at `plugins/aops/agents/ida.md` and declares no `tools` or
  `allowedTools` at all.

## Constraints the design must respect

| #   | Constraint                                                                                                                                                                                                                                               | Evidence                                                                 |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| C1  | The build has no per-client agent scoping: both adapters glob `*.md` only, so every `agents/*.md` is emitted for both clients                                                                                                                            | `build/clients/claude.py:65`, `build/clients/agy.py:225`                 |
| C2  | A `model:` value agy does not recognise silently unregisters the agent, and `--agent` then falls back to an unnamed full-tool session — an escalation, not a cosmetic bug                                                                                | `build/clients/agy.py:271-275`                                           |
| C3  | The no-`tools:` fallback emitting `tools: ["*"]` crashed every custom agent on agy, which has no converter for `*`                                                                                                                                       | fixed in `250921f8d`                                                     |
| C4  | `call_mcp_tool` must never appear in an agy `tools:` list — it fails executor construction before the model runs, exit 1                                                                                                                                 | #2422                                                                    |
| C5  | An MCP server or tool name starting `mcp_` bypasses the accepted-vocabulary check, so a wrong name passes the build and fails only at agy runtime                                                                                                        | `specs/ARCHITECTURE.md`                                                  |
| C6  | A declared allowlist is not runtime ground truth: a spawned `ida` held a top-level tool set wider than `ida.md` declared                                                                                                                                 | `specs/agents/agent-authority.md:163-176`                                |
| C7  | `tools`, `allowedTools` and `disallowedTools` are three distinct surfaces. `tools` is the capability grant; `allowedTools` is only the approval rule set in `Tool(pattern)` form. The field that restricts which subagents may be spawned is `subagents` | `specs/agents/agent-authority.md:63-74`, `:94`, `:97-101`                |
| C8  | Comments cannot survive the build — both adapters round-trip frontmatter through `yaml.safe_load` → `yaml.safe_dump`, so a commented-out "ready to enable" block ships as nothing                                                                        | `build/clients/claude.py:78`, `:134`; `build/clients/agy.py:239`, `:325` |
| C9  | Cross-plugin MCP _naming_ is allowed (naming is not reading), on two conditions: the runtime dependency is declared in the naming plugin's README, and `services` is never re-configured outside `plugins/aops/manifest/mcp.template.json`               | rbg ruling, this review round                                            |
| C10 | `@ref`-style content inclusion does not exist in the build. `inject_shared` copies whole files from `lib/`; `@path` is Claude Code's own runtime syntax and would sit as literal text on agy                                                             | `build/shared.py:105-108`                                                |
| C11 | `dist/` is gitignored but present on disk and carries `james`-bearing files. Any grep-driven sweep must exclude it or it edits files the next `make build` overwrites                                                                                    | —                                                                        |

## A. One agent, two client files

There is **no `james`/`jim` split**. There is one orchestrator named `james`, and
every existing `james` reference stays correct — no reference sweep is needed.

The two client bodies differ in exactly one section, how to dispatch; roughly 55
of 66 lines are common (fail-fast, the hearsay rule, the logical-integrity check,
the output standard, PKB discipline). Every recurring failure on this surface has
been a **frontmatter translation** failure (C2, C3, C4), never a prose failure.
So the split is by file, not by conditional prose, and not by translating
difficult frontmatter:

```
plugins/orchestrate/agents/james.agy.md      → agy   builds agents/james.md
plugins/orchestrate/agents/james.claude.md   → claude builds agents/james.md
```

Slight body duplication is accepted as the price of frontmatter that is authored,
not derived. `[[shared]]` injection from `lib/` is the mechanism if common
chunks are later factored out; `@ref` is not (C10).

### Required build change

Today this convention fails silently: `james.agy.md` matches neither adapter's
`*.md` glob (C1), so it would be copied through unadapted and shipped to **both**
clients as a stray file with no error — exactly as `agy.md.disable` used to.
Roughly ten lines per adapter:

1. Glob `*.md` **plus** this client's suffix (`*.claude.md` / `*.agy.md`).
2. Strip the suffix when writing, so both land as `agents/james.md`.
3. Delete the other client's suffixed file from the build dir. Without this the
   convention "works" while leaking the other client's agent definition into
   every artifact.
4. Fail the build when one name resolves from two sources (`james.md` _and_
   `james.agy.md`), because precedence is otherwise undefined.
5. Tests for all four.

## B. Default the agent per client in polecat

`lib/polecat/cli.py`: when no agent is supplied and no `--agent` appears in
`extra_args`, default to `james` on both `claude` and `agy`. Never for
`shell`/`bash`/`sleep`/passthrough — that exclusion is already structural in
`_build_inner_command`, so claim it rather than build it.

This is new work, not the verification of a prior decision: the `--agent` option
carries no `default=`, `_agent_args` returns `[]` when the agent is falsy, and a
dispatched worker today boots as no agent at all.

**Verification must be a live in-container call, not a green build.** C2 means a
non-resolving default yields a full-tool unnamed session that looks like success.
Prove it by comparing the tool count and a live PKB call inside the built image
under `--agent james` against the same container with no `--agent`. A resolving
agent name is not sufficient evidence.

## C. `pc` gains a synchronous mode

`pc` today launches detached only. Add a headless synchronous stream: foreground,
blocking, `--prompt` last, explicit timeout. Detached behaviour stays as shipped.

## D. Lock `ida` to `pc`

**Blocked.** Prerequisites, in order, in the review.

The intent is that `ida` reaches nothing but `pc`, so hydrate/q/brief/enqueue all
execute inside the container. Two things make the design as originally written
unworkable and must be settled before implementation:

- The route cannot rest on `allowedTools`, which only governs approval prompts
  (C7); the field that restricts subagent spawning is `subagents`. And no
  declared surface is runtime ground truth (C6), so a lockdown expressed in
  frontmatter alone pays the whole cost of the rewrite and may buy nothing.
- `pc.md`'s charter — "Your ONLY job… you never do the work yourself… asked for
  anything else, HALT" — refuses the traffic this section would route through it.
  Either the charter changes or the route does; the narrowness is a recorded
  decision, not an accident.

Removing `Agent(pauli)` also strands `plugins/ida/skills/strategize/SKILL.md`,
which is built end to end on handing reads and writes to `pauli`, plus the
`ENFORCEMENT-MAP.md` rows marked `live` and `binding`. This is the largest
behavioural change in the design and the most likely to be wrong.

## E. MCP wiring

Settle first, by live call: **does agy merge per-plugin MCP configs into one
namespace?** `build/clients/agy.py:63-67` writes `mcp_config.json` per plugin, and
nothing records the answer. Every grant below depends on it.

1. **PKB for the orchestrators** — declare `mcpServers: [services,
   plugin:aops:services]`, the shape `pauli` uses. Permitted under C9.
2. **Playwright for marsha, claude-side only.** agy's accepted vocabulary already
   carries 23 native browser tools, so agy-side marsha needs none and must not be
   given one. Claude-side is the gap: `@playwright/mcp` is in the image
   (`Dockerfile:164`) and no manifest registers it. This needs a build change or
   a different mechanism — the `clients.claude`/`clients.agy` split scopes server
   _config_, while the _grant_ lives in `marsha.md` frontmatter, which ships to
   both clients (C1), and `build/tools.py:105-111` reads `mcpServers`
   unconditionally.
3. **context7 for james** — absent from the repo entirely. Needs the full shape
   pkb already ships: `${user_config.*}` for claude, env for agy, a `userConfig`
   entry with no default, `"mcpServers": "./.mcp.json"` under `clients.claude` in
   `plugin.template.json`, and `manifestVersion` + `clients` or the build fails.
   context7 is a keyed service, and the credential comes from the environment or
   `userConfig` — never a shipped default.

Every grant here lands in C5's blind spot and must be proven by a live call.

## F. Keep hooks advisory

No change to hook behaviour is in scope: every `rbg` handler is unregistered and
`orchestrate`'s are all `warn`, so nothing blocks today. The work is to **assert**
the property, because it is not self-maintaining — the same `HANDLERS` disable
was made in `60be332b9` and silently reverted by `9ebb6d872`, an unrelated feature
commit.

Add a test that fails if a registered handler can return a blocking disposition,
so the next accidental revert breaks the build. Scope it to **"no handler blocks
on agy"**: the measured harm was agy-specific, and the stop gate is still owed on
claude. Route it through `tests/policy.toml` per `.agents/rules/RULES.md:36-39`,
not hardcoded Python literals.

Reconcile the three-way drift over hook registration before codifying anything:
`handlers.py` registers `PostToolBatch` and `SubagentStart`, `ARCHITECTURE.md`
and `tests/policy.toml` each say something different, and
`lib/hooks/dispatch.py`'s `CANONICAL_EVENTS` lacks `SubagentStart` — which
demonstrably fires.

## G. Reconcile the stale record

`aops_bb35214b`, `aops_95564402`, `aops_e5e2c80f` and `mem_dcedd813` all still
assert that `agy --agent <name>` strips MCP tools and write capability (#2387).
That was refuted end to end in commit `250921f8d`: headless
`agy --agent <name> --prompt … --output-format json` was confirmed working for
filesystem, network and PKB.

This is high-value, not housekeeping. Both reviewers of this design independently
reached the stale claim and treated it as a blocker, which is the evidence that
the records are actively misdirecting competent readers. Route the four nodes to
`pauli`, the sole writer.

`build/tool_map.toml:4` still holds `call_mcp_tool` and `delete_knowledge` out of
the accepted vocabulary. That is a separate open question about _declaring_ the
primitive; the working path does not need it declared.

## H. Deferred

One long-lived container per branch hosting multiple polecats, and question-back
by resuming a finished agy run from its session log. Recorded as a task with its
open design questions named, not silently dropped.

## Execution order

1. **Section A** — the suffixed agent files and the build change that makes them
   real. Everything downstream names `james`.
2. **Section B** — polecat's per-client default. Depends on A resolving.
3. **Section C** — `pc`'s synchronous mode. Depends on B, since `pc` invokes the
   defaults.
4. **Section D** — the `ida` lockdown. **Last**, and only after `pc` is correct:
   it removes ida's fallback routes, so if `pc` is wrong she has no working path.
5. **Section E** — independent of the above, gated on the agy-merge probe.
6. **Section F** — independent and cheap; do it early, it protects the property
   while everything else churns.
7. **Section G** — independent of the code work; same pass, not "later".

## Verification

- `make format`, `make lint`, `make test`, `make build`, `make docker-build`.
- In a live container: the default agent resolves on each client and is **not**
  the silent full-tool fallback (check `agy agents` and the tool count); `pc`
  detached returns immediately; `pc` synchronous blocks and streams; PKB,
  playwright and context7 are each reachable by the agent granted them.
- Confirm no registered handler returns a blocking disposition on any exit path.
- Persona edits and enforcement changes require `specs/enforcement/enforcement.md`
  updated in the same PR (`.agents/rules/RULES.md:15-22`).
