---
status: draft
tier: 2
type: spec
title: Orchestrator client split, polecat default agent, and ida routing
tags: [agents, polecat, james, ida, mcp, build]
created: 2026-08-15
---

# Plan — split james, default it into polecat containers, lock ida to `pc`

> **Superseded in part.** Nic decided 2026-08-15 that there is **no `james`/`jim`
> split**: one agent, authored as `james.agy.md` + `james.claude.md`, accepting
> slight body duplication. See
> [orchestrator-client-split-review.md](orchestrator-client-split-review.md) for
> the reconciled verdict, which supersedes this document wherever they conflict.

## Objective

`james` runs by default inside every polecat container, under both agy and claude.
Claude-side and agy-side orchestrators become two distinct agents. `ida`, outside
the container, can call only `pc`. No binding hooks anywhere: advice injection
only, nothing blocks before exit.

## Established facts (observed, with sources)

| #   | Fact                                                                                                                                                                                                                                                                  | Evidence                                                                           |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| F1  | Both CLIs accept `--agent <name>`; claude also honours an `agent` key in settings                                                                                                                                                                                     | `claude --help`, `agy --help`                                                      |
| F2  | `polecat run` already has `--agent/-a`, defaulting to nothing; `_agent_args` suppresses it when the caller passed `--agent` in `extra_args`                                                                                                                           | `lib/polecat/cli.py:910-917`, `:1331-1335`                                         |
| F3  | `agy --help` output format values are `text, json, stream-json` — **not** `json-stream`                                                                                                                                                                               | `agy --help`                                                                       |
| F4  | `polecat run`'s `-o` is `--output-format`, not a headless switch; headless is implied for agy when no prompt/interactive flag is present                                                                                                                              | `lib/polecat/cli.py:1336-1340`, `:1002-1014`                                       |
| F5  | The build has **no** per-client agent scoping — every `agents/*.md` is emitted for both clients                                                                                                                                                                       | `build/build.py:43-44`, `build/clients/{claude,agy}.py` `_adapt_agents`            |
| F6  | `orchestrate` hooks are all advisory (`warn`); none block                                                                                                                                                                                                             | `plugins/orchestrate/hooks/handlers.py:196-205`                                    |
| F7  | `rbg` has a blocking `rule_check` on Stop/SubagentStop, but its `HANDLERS` map is **entirely commented out** — nothing is registered, so nothing blocks today                                                                                                         | `plugins/rbg/hooks/handlers.py:320`, `:341-345`                                    |
| F17 | **A documented known issue says passing `--agent <name>` to `agy` strips MCP tools and write capabilities** (issue #2387) — which is exactly what plan item 6 proposes to do by default, to an agent whose whole point is PKB access                                  | `.agents/skills/debug/SKILL.md:122`                                                |
| F18 | `specs/ARCHITECTURE.md:196` states orchestrate's `Stop` hook "fires blocking (`block`)". `plugins/orchestrate/hooks/handlers.py:202` registers only the tracer `stop`, which returns `None`. The spec is stale on the one property the user is asking us to guarantee | both files                                                                         |
| F19 | `orchestrate`'s python package is literally `name = "james"`, and `plugin.template.json` lists `"james"`                                                                                                                                                              | `plugins/orchestrate/pyproject.template.toml:2`, `manifest/plugin.template.json:7` |
| F16 | An MCP name starting `mcp_` bypasses the accepted-vocabulary check, so a wrong server/tool name passes the build and fails only at agy runtime                                                                                                                        | `specs/ARCHITECTURE.md:352-354`                                                    |
| F15 | That disable has silently regressed once before: made in `60be332b9`, reverted by unrelated feature commit `9ebb6d872`                                                                                                                                                | `plugins/rbg/hooks/handlers.py:336-340`                                            |
| F8  | `@playwright/mcp` is baked into the image, but **no `mcpServers` entry registers it** in any plugin manifest                                                                                                                                                          | `Dockerfile:153`; grep of `*/manifest/mcp.template.json`                           |
| F9  | `context7` appears nowhere in the repo except a disabled spec note                                                                                                                                                                                                    | grep; `plugins.disabled/specs/informed-improvement-options.md:11`                  |
| F10 | The agy wrapper already exists but is disabled, and already defaults to `--agent james`                                                                                                                                                                               | `plugins/ida/agents/agy.md.disable:22`                                             |
| F11 | `pc.md`'s synchronous block builds `CMD` and never executes it                                                                                                                                                                                                        | `plugins/orchestrate/agents/pc.md:38-42`                                           |
| F12 | `ida` currently reaches `pauli`, `james`, and `pc`                                                                                                                                                                                                                    | `plugins/ida/agents/ida.md:6-9`                                                    |
| F13 | A `model:` value agy does not recognise silently drops the agent from `agy agents`, and `--agent` then falls back to an unnamed full-tool session                                                                                                                     | `build/clients/agy.py:271-275`                                                     |
| F14 | agy's accepted tool vocabulary (54 names) already includes 23 native browser tools                                                                                                                                                                                    | `build/tool_map.toml:27-65`                                                        |

## Design

### A. Split the orchestrator into two agents

Because of **F5**, the split is done by _name_, not by build-time client scoping.
Both files ship to both clients; which one runs is decided by `--agent` at launch.
No build change required.

**Names are decided by the user:** the agy-side orchestrator **keeps `james`**;
the claude-side dispatcher is renamed **`jim`**.

```
agy    --agent james  → fans out natively; no bash, no polecat
claude --agent jim    → dispatches by bash into agy
```

1. **Rewrite** `plugins/orchestrate/agents/james.md` — the in-container agy
   orchestrator, keeping its name. Fans out natively to in-session subagents.
   Never shells out to `agy`, never touches `polecat`. Body = today's content
   minus any dispatch mechanics, narrowed to the two-job mandate: **fan work out,
   and certify it.** Honesty and the hearsay rule stay as instruction text.
   Frontmatter: `name`, `description`, `enable_mcp_tools: true`, PKB + context7
   `mcpServers`. **No `tools:` key** — which under the restored fallback grants the
   full vocabulary, i.e. unrestricted, as required.

2. **New** `plugins/orchestrate/agents/jim.md` — the claude-side dispatcher.
   Dispatches by bash into agy. Invoked only by `ida`/`pc` at container launch.
   Ships _unrestricted_ by default; the lockdown surface (`pauli` + the `agy`
   wrapper only) is written into the file as a commented, ready-to-enable
   `allowedTools` block so it can be switched on without redesign.

3. **Sweep every reference.** `specs/ARCHITECTURE.md` currently describes one
   `james` who routes "to a supervised in-session agent team **or** to an
   asynchronous polecat container" — that second half is now `jim`. Every mention
   of `james` in specs, skills (`strategic-review`, `verify`, `audit`, `debug`,
   `dogfood`), `ida.md` and `agy.md` must be re-pointed at whichever of the two it
   actually means. A reference left pointing at `james` will still _resolve_, so
   this cannot be caught by a build error — it needs a deliberate pass.

### B. Make the agy invocation non-negotiable

4. Re-enable `plugins/ida/agents/agy.md` (drop `.disable`) and correct it:
   - `--agent james` as the default (**F10** — already correct, and stays correct
     under the chosen naming).
   - Sandbox rule made conditional: **inside** a polecat container, no `--sandbox`
     (the container _is_ the isolation); **outside**, `--sandbox` is mandatory.
     The current unconditional "NEVER without `--sandbox`" is wrong in-container.
5. Back it with `lib/agy/dispatch.sh` (in `lib/`, so both plugins may use it and
   no copy exists) that applies the non-negotiable options. Rationale: the
   `--agent james` silent-fallback regression proved that an instruction to pass a
   flag is droppable, and the failure is invisible.

### C. Default the agent per client in polecat

6. `lib/polecat/cli.py`: when `--agent` is not supplied and no `--agent` appears in
   `extra_args`, apply a per-client default — `james` for `agy`, `jim` for
   `claude`. Never for `shell`/`bash`/`sleep`/passthrough.
7. Provide an explicit opt-out (`--agent none`) so a bare, un-personified session
   remains reachable; without one, this change is irreversible from the CLI.
8. Guard **F13**: a default agent name that does not resolve fails _silently_ into
   a full-tool unnamed session. The default must be verified to resolve inside the
   image, not assumed.

### D. `pc` gets exactly two modes

9. Rewrite `plugins/orchestrate/agents/pc.md`:
   - **Detached** — `tmux new-session -d -s "$NAME" "<polecat run …>"`; returns
     immediately with the session name and the host-side log path.
   - **Headless synchronous stream** — foreground, blocking, `--prompt` last, explicit timeout.
   - Fix **F11** (command built, never run) and **F4** (`-o` mis-described as a
     headless switch).

### E. Lock `ida` to `pc`

10. `ida.md`: `allowedTools` → `Agent(pc)` only; drop `Agent(pauli)` and
    `Agent(james)`.
11. **Consequence that must be handled, not glossed:** `ida.md`'s current
    "Asynchronous dispatch" section instructs her to call `pauli` for
    hydrate/q/brief/enqueue. With `pauli` removed that section is dead
    instruction. It must be rewritten so every one of those steps is requested
    _through_ `pc`, executed inside the container. This is the single largest
    behavioural change in the plan and the most likely to be wrong.

### F. MCP wiring

12. **PKB for the orchestrators** — declare `mcpServers: [services,
    plugin:aops-core:services]` (the shape `pauli` uses). Open question: `services` is
    configured in `plugins/aops-core/manifest/mcp.template.json`; an `orchestrate` agent
    naming it is a cross-plugin reference. Must be _verified to resolve at
    runtime_, not assumed — and checked against "a plugin never reads another
    plugin's files".
13. **Playwright for marsha — claude-side only.** **F14**: agy's accepted
    vocabulary already carries 23 **native** browser tools (`browser_*`,
    `capture_browser_screenshot`, `open_browser_url`, `execute_browser_javascript`
    …), so agy-side marsha needs no playwright MCP and must not be given one.
    The gap is claude-side: **F8** — `@playwright/mcp` is in the image and nothing
    registers it. Add an `mcpServers` entry under the `claude` key only (owner:
    `orchestrate`, where marsha ships) and grant it to marsha.
14. **context7 for james** — **F9**: absent entirely. Needs a new server entry
    whose endpoint comes from `userConfig`/environment, never a baked default.

### G. Hooks: advisory only

15. **This requirement is already met and the work is to keep it met, not to
    change anything.** **F7**: every rbg handler is unregistered, and orchestrate's
    are all `warn`. No hook blocks on any exit path today. So: **no hook change is
    in scope.** Instead — assert it. **F15** shows this exact disable has already
    been silently reverted once by an unrelated merge, which means the property is
    not self-maintaining. Add a test that fails if any registered handler can
    return a blocking disposition, so the next accidental revert breaks the build
    instead of quietly re-arming the gate.

### H. Reconcile the record

17. **Correct the stale MCP nodes.** `aops_bb35214b`, `aops_95564402`,
    `aops_e5e2c80f`, `mem_dcedd813` and `.agents/skills/debug/SKILL.md:122` all
    still assert that `agy --agent` strips MCP tools. Last session refuted this
    end to end (commit `250921f8d`). Route the four PKB nodes to **pauli**, the
    sole writer; the doc line is ours to fix directly. Also correct
    `specs/ARCHITECTURE.md:196` (**F18**), which claims a blocking orchestrate
    `Stop` the code does not register.

### I. Explicitly deferred

18. One long-lived container per branch hosting multiple polecats, and
    question-back by resuming a finished agy run from its session log. Not built
    now — the user said this still needs thinking through. Recorded as a task with
    its open design questions named, not silently dropped.

## PKB findings — this ground is already covered, and partly already settled

Retrieved directly from the knowledge base (pauli went idle twice without
reporting; these are my own queries).

- **`aops_bb35214b`** — "agy: `--agent` strips `call_mcp_tool`, write and shell —
  fixed in polecat; container MCP still intermittent". Records: _"**Unmet: no agy
  session runs with our personas.** Every agent this repo builds loses its
  toolset under `--agent` (#2387). Polecat now omits the flag for agy, which is a
  downgrade being carried, not a design — marked TEMPORARY MITIGATION."_
- **`aops_267a459a`** — "polecat: dispatched workers **default to `--agent
  james`** — container-level verification outstanding". So **plan item 6 is not a
  new idea; it is a previously-taken decision whose verification never happened.**
  The node states the gap precisely: the tests assert the argv polecat
  _constructs_ against a mocked container, "never what a container _does_ with
  that argv."
- **`aops_95564402`** — "agy agents can **SEE** services MCP tools but **cannot
  CALL** them — no `call_mcp_tool` declared; agent falls back to raw HTTP
  JSON-RPC."
- **`aops_e5e2c80f`** — "agy subagent invocation broken for any subagent
  declaring MCP tools ('no tool converter registered for `call_mcp_tool`')" — and
  notes a worker previously **routed around this by self-editing the tool
  declaration instead of halting.**
- **`mem_dcedd813`** — a state note carrying a correction history in which an
  earlier note was edited back into force claiming `--agent` was "Fixed" when it
  was not. Treat any "this is fixed" claim about `--agent` as suspect.
- **`aops_e39b6b9d`** — status `done`. It delivered
  `specs/agents/ida-supervision-migration.md` (313 lines), now in **draft PR
  #2446**, unreviewed. Its recorded design finding bears directly on our item 10:
  ida's routing discipline is _carried in prose alone_ (note: under canonical enforcement doctrine, prose instructions are the primary starting rung rather than a disqualifier), and the spec holds that
  **"no stage past 0 is entered while the envelope is neither declared nor
  enforced."** Our `ida` lockdown is exactly such a stage change, and there is an
  unreviewed spec that already owns the question.

### Resolved — these nodes are STALE, and that is itself work

**The user has settled this: `call_mcp_tool` was proved end to end in the
immediately preceding session.** Headless `agy --agent <name> --prompt …
--output-format json` was confirmed working for filesystem, network **and PKB**.
So `--agent` does _not_ strip MCP execution, and items 6 and 12 are both
satisfiable. There is no blocker here.

What remains is a knowledge-base defect, not a code defect: **`aops_bb35214b`,
`aops_95564402`, `aops_e5e2c80f` and `mem_dcedd813` all still assert the broken
state**, and `mem_dcedd813` already carries a correction history showing this
exact claim flip-flopping. Left standing, they will send the next agent — or the
next session of this one, as they nearly sent this one — down a halt that is no
longer real.

**Action:** reconcile those four nodes against last session's evidence
(commit `250921f8d`, branch `polecat/session-e6cc0451`). This is a real work item,
added to the plan as item 17. It is routed to pauli, the sole writer.

`build/tool_map.toml:5-16` still holds `call_mcp_tool` and `delete_knowledge` out
of the accepted vocabulary pending #2422. That is a separate, still-open question
about _declaring_ the primitive in `tools:`, and nothing here asks us to change
it — the working path does not need it declared.

## Framework defect observed while running this review

Dogfood evidence, recorded because it degraded this very session.

Four subagents were spawned (`pauli-advice`, and `review-rbg` / `review-pauli` /
`review-marsha` for the strategic review). **Three of the four emitted an
`idle_notification` with `idleReason: "available"` and delivered no report at
all** — no findings, no partial result, no stated failure. `ListAgents` returned
"No reachable agents" throughout, including immediately after successful spawns
and successful `SendMessage` calls to those same agents, so the listing surface
disagrees with the messaging surface.

Consequence: the `strategic-review` skill's own guarantee — _"a reviewer
commissioned but not actually invoked and awaited is not a completed review
step"_ — could not be met by the skill as written, because the reviewers were
invoked and awaited and still returned nothing. The PKB findings above were
recovered by querying the knowledge base **directly**, not from `pauli`.

This is not a workaround being carried silently: it is the reason the review
below is thinner than the skill specifies, and it should be filed.

## Execution order

The plan is not order-free. Two items gate everything downstream, and both are
cheap.

**Gate 0 — RESOLVED, not a gate.** `--agent` + MCP was proved end to end last
session. Proceed. (Re-confirm once after Gate 1 as a smoke check, not as a
decision point.)

**Gate 1 — `make install-dev`.** The installed artifacts under
`~/.gemini/config/plugins/` are stale and hand-edited from a previous session, so
any probe run before this tests the wrong file. This was the pending step from
last session anyway.

Then:

1. Items 1–3 — the agent split and the reference sweep. Do the sweep _with_ the
   split, not after: a stale reference resolves to a real agent, so there is no
   later error to catch it (**R4**).
2. Items 4–5 — the `agy` wrapper and `lib/agy/dispatch.sh`. Depends on 1 (it
   names `--agent james`).
3. Items 6–8 — polecat's per-client default. Depends on 1 (the names must
   resolve) and on Gate 0.
4. Item 9 — `pc`'s two modes. Depends on 6–8, since `pc` invokes the defaults.
5. Items 10–11 — the `ida` lockdown. **Last**, and only after `pc` is correct:
   it removes ida's fallback routes, so if `pc` is wrong at that point she has no
   working path at all.
6. Items 12–14 — MCP wiring. Independent of the above, but each grant must be
   proven by a live call (**F16**/**R3**), never by a green build.
7. Item 15 — the no-blocking-hooks assertion test. Independent; do it early, it
   is cheap and it protects the property while everything else churns.
8. Item 17 — reconcile the stale record. Independent of the code work; route the
   PKB nodes to pauli. Do it in the same pass, not "later" — these are the nodes
   that will misdirect the next agent.
9. Item 18 — record the deferred per-branch-container design as a task.

## Verification

- `make format`, `make lint`, `make test`, `make build`.
- `make docker-build`, then in a live container: agy default agent resolves (and
  is _not_ the silent full-tool fallback — check `agy agents` and the tool count);
  claude default agent resolves; `pc` detached returns immediately with a live
  tmux session; `pc` synchronous blocks and streams; PKB, playwright and context7
  MCP each reachable from inside the container by the agent granted them.
- Confirm no hook returns a blocking disposition on any exit path.

## Decisions taken

- **Naming** — settled by the user: agy keeps `james`, claude-side becomes `jim`.
- **Lockdown** — `jim` ships open, with the narrow `pauli` + `agy`-wrapper
  surface written in and ready to enable. The user asked for the _option_, not the
  restriction.
- **`ida` restricted to `pc`** — implemented as her only `Agent(...)` grant.

## Known risks

- **R1 — the `ida` rewrite strands more than `ida.md`.** Removing `Agent(pauli)`
  breaks, at minimum: `ida.md`'s whole hydrate/q/brief/enqueue workflow;
  `plugins/ida/skills/strategize/SKILL.md` — **the one skill ida runs herself** —
  which is built end to end on handing reads and writes to `pkb:pauli`
  (`:18,21,72,79,87`); `plugins/ida/README.md`, which states her two delegation
  targets as a designed property (`:48`); and 4 `ENFORCEMENT-MAP.md` rows marked
  `live` and `binding` (`:47,62,63,162`). Routing all of it through `pc` also
  collides with `pc`'s own charter — "You are PROHIBITED from taking any other
  action" (`pc.md:19`). Highest-consequence item in the plan, and the one most
  likely to be wrong as specified.
- **R2 — silent default-agent fallback.** **F13**: a non-resolving `--agent` does
  not error; it yields a full-tool unnamed session that looks like success. This
  is exactly the bug fixed last session. Both new defaults must be proven to
  resolve _inside the built image_.
- **R3 — cross-plugin MCP reference, and MCP names are unchecked at build time.**
  `orchestrate` agents naming pkb's `services` server may or may not resolve
  (each plugin ships its own `mcp_config.json`), and may or may not sit within "a
  plugin never reads another plugin's files". Worse, **F16**: a name starting
  `mcp_` bypasses the accepted-vocabulary check, so a wrong server name **passes
  the build and fails only at agy runtime**. Every new MCP grant here — PKB for
  the orchestrators, playwright for claude-marsha, context7 — lands in exactly
  that blind spot and must be proven by a live call, not by a green build.
- **R4 — stale `james` references.** They resolve to a real agent, so nothing
  fails loudly. Only a deliberate sweep catches them. A full sweep finds ~50
  across `specs/ARCHITECTURE.md`, `specs/ENFORCEMENT-MAP.md` (8 rows),
  `specs/agents/agent-authority.md`, both plugin READMEs, `ida.md`,
  `strategize/SKILL.md`, `debug/SKILL.md`, `lib/polecat/cli.py:848,858`, and two
  test files. Most of these mean _dispatch_, i.e. the new `jim`, not the agy
  fan-out `james` that keeps the name — so the majority will silently bind to the
  wrong agent.
- **R6 — CLOSED.** `--agent` stripping MCP was refuted end to end last session.
  The residual risk is the inverse: **four PKB nodes and one project doc
  (`.agents/skills/debug/SKILL.md:122`) still assert the broken state.** Stale
  records that say "halt here" are as costly as a real blocker — they nearly
  halted this plan. Item 17 reconciles them.
- **R7 — the spec is already wrong about blocking hooks.** **F18**: the
  architecture spec claims a blocking orchestrate `Stop` that the code does not
  register. Anyone verifying "no binding hooks" against the spec rather than the
  code gets the wrong answer.
- **R5 — the no-blocking-hooks property is not self-maintaining.** It holds today
  by a commented-out `HANDLERS` map, and **F15** records that exact comment being
  silently un-done by an unrelated merge. Nothing currently detects the revert.
