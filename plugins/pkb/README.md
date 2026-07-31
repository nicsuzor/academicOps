# pkb

Pauli — memory, effectual planning, workflow composition, and the client wiring
for a Personal Knowledge Base.

## How it works

```mermaid
flowchart TD
    prompt([user prompt]) --> hook

    hook["UserPromptSubmit hook<br/>one advisory message, every prompt:<br/>run search · task_search · retrieve_memory"]
    hook --> agent
    prompt --> agent["any agent<br/>calls the PKB MCP tools itself"]

    agent -- "planning, memory,<br/>anything that writes" --> pauli

    subgraph pkbwrite["agents/pauli.md — one stage per invocation"]
        pauli(("pauli"))
        pauli --> hydrate["skills/hydrate<br/>four-section context bundle<br/>always first, six-call budget"]

        hydrate --> situate["skills/situate<br/>one task, valued and wired<br/>sets needs_decomposition, stops"]
        situate --> gate{{"human sets status queued<br/>agents pull only from here<br/>and never promote into it"}}
        gate --> pull["skills/pull<br/>claim it, execute it,<br/>record the result, hand over"]

        pauli --> composer["skills/workflow<br/>compose the process into a checklist<br/>three layers, loaded every time"]
        pauli --> remember["skills/remember<br/>capture · consolidate"]
        pauli --> learn["skills/learn<br/>diagnose the incident,<br/>route the lesson by its scope"]

        learn -. knowledge scope .-> remember
        learn -. project scope .-> addrule(["rbg — skills/add-rule<br/>write the project rule"])
        learn -. task scope .-> pull
    end

    pull --> dump["skills/dump<br/>session exit — bail, close,<br/>hand back, or pause"]

    composer --> library[["workflows/INDEX.md<br/>workflows/process/*.md"]]
    composer --> userlayer[["$ACA_DATA/.agents/workflows/<br/>overrides by filename"]]
    composer --> wftemplates[["PKB documents tagged wf-template"]]

    pkbwrite -- "every read and write" --> mcp
    agent -- "the three hook searches" --> mcp

    mcp[".mcp.json — services<br/>HTTP, or scripts/run-mcp.sh over stdio"] --> pkbstore[(PKB)]

    gate --> dispatch(["ida:james — skills/dispatch<br/>compose the brief, dispatch by task id"])
```

### The hook asks; nothing checks

The hook fires on every prompt and never calls the PKB itself. Establishing an
MCP session on the critical path of every turn is not affordable, and a slow
server would stall the turn. It emits one advisory message
(`hooks/messages/pkb-context.md`, editable without touching code) naming three
MCP tool calls to issue before answering — `search`, `task_search`,
`retrieve_memory`. It names no skill and does not invoke `hydrate`.

Compliance is voluntary. The handler returns an advisory, which is context
injection only; nothing reads back whether the agent searched. Agents can act on
it because they hold the PKB tools directly — james, marsha, rbg and pauli all
inherit the full MCP namespace. `ida` is the one agent whose declared `tools`
exclude them, and the message covers that case: say the tools are unavailable
and work from what is visible, rather than guessing at what the PKB would have
said.

The `hydrate` skill is a different mechanism with a similar name. It is pauli's,
runs inside pauli's pipeline, spends a six-call budget, and appends a
four-section bundle to a task. There, it is always first and never skipped. The
hook's read is neither pauli's nor enforced.

### Mutation is a convention, not a boundary

Everything that mutates the PKB is routed through pauli by instruction. That is
doctrine, not permission: pauli, james, marsha and rbg all omit `tools` to work
around a harness materialization defect (`specs/agents/agent-authority.md`), so
each inherits its parent's full effective set including the PKB MCP namespace.
James holds read, knowledge-write, and task-lifecycle operations outright by its
own charter, and routes only graph mutation — creating, reparenting, decomposing
— to pauli. Restore the boundary as a tool grant when the harness defect is
fixed.

### Stages advance by invocation, not by trigger

Each skill runs in its own invocation and stops. No stage fires the next one.
`hydrate` emits a bundle. `situate` sets `needs_decomposition: true` and halts —
nothing polls for that flag or consumes it. Turning a `needs_decomposition`
task into subtasks has no shipped owner in this tree: `decompose`, `brief`,
`planner`, and `reconcile` are named in the surrounding design docs but ship
under no `plugins/*/skills/` path — a library gap, not a stage to route
around or assume exists.

The gate in the middle is a person. `queued` means the user has released the
work for agent dispatch; agents pull only from there and never promote into it.
Any reconciliation of an abandoned claim must return it to `ready`, never
`queued` — the same rule, wherever it runs. So the pipeline cannot run end to
end unattended.

### Dispatch composes the brief itself

`ida`'s `dispatch` composes the delegation brief immediately before dispatching
a unit, freshly each time — never earlier, because context moves between
passes. There is no separate composer stage: the skill that writes the brief
and the skill that dispatches it are the same invocation.

### Composing a workflow

`workflow` runs inside pauli — read and composed in context, every time, never
carried in pauli's own text. Its three template layers sit outside the box
because they are sources, not stages: the shipped library, the user's
`$ACA_DATA/.agents/workflows/`, and PKB documents tagged `wf-template`. They form
one namespace; a PKB template composes exactly like a shipped one.

The output lands on the task as its checklist, not as a file or a document:
the composed steps, in order, plus one pointer bullet naming the templates and
the proportionality call. An empty review set is a library gap the composing
skill names rather than silently passing — with no shipped skill currently
turning that gap into a blocking node (see the stages note above).

### Remembering

`remember` is not a command. It fires on a standing obligation inlined into
pauli, ida, james and marsha at build time: write facts, decisions, and state to
the knowledge base the moment they emerge, without waiting to be asked. Any
agent under that obligation reaches for the skill; pauli holds the write.

Consolidation turns episodic records into canonical topic notes — synthesis,
not collection. The standard for what that means is
[`skills/remember/references/quality.md`](skills/remember/references/quality.md).

## What it provides

### Agent

| Agent   | Does                                                                                                              |
| ------- | ----------------------------------------------------------------------------------------------------------------- |
| `pauli` | Logician, effectual strategist, and custodian of the PKB. Every mutation routes here. Call first, and call often. |

### Skills

| Skill      | Does                                                                                                              |
| ---------- | ----------------------------------------------------------------------------------------------------------------- |
| `hydrate`  | Emit a right-sized context bundle so nothing downstream starts cold.                                              |
| `situate`  | Turn a hydrated ask into one valued, well-connected task, then stop.                                              |
| `workflow` | Compose the process this work runs under, from the shipped library, the user layer, and the PKB.                  |
| `pull`     | Claim a queued task, execute it, record the result on the task, and hand over.                                    |
| `remember` | Capture knowledge as it emerges; consolidate episodic records into durable notes.                                 |
| `learn`    | Diagnose an incident back to the structural cause, then route the lesson to the one destination its scope claims. |
| `dump`     | Session exit — bail, close, hand back partial work, or pause with the work still in progress.                     |

### Command

| Command | Does                                                          |
| ------- | ------------------------------------------------------------- |
| `/q`    | Quick-queue a thought onto the graph. Delegates to `situate`. |

### Hook

| Event              | Does                                                                                    |
| ------------------ | --------------------------------------------------------------------------------------- |
| `UserPromptSubmit` | Injects the instruction to ground the prompt in the PKB, and names the searches to run. |

Wording lives in `hooks/messages/pkb-context.md` and is editable without
touching code. Claude Code fires this event directly; on Antigravity it arrives
as `PreInvocation`.

## Configuration

There are no defaults. No URL, host, port, path, or token is baked into anything
this plugin ships.

| Setting       | Where it comes from | For                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pkb_mcp_url` | client `userConfig` | The streamable-HTTP endpoint of the PKB MCP server. Claude Code reads it into `.mcp.json`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `PKB_MCP_URL` | environment         | The same endpoint, for clients that launch the server over stdio via `scripts/run-mcp.sh`. Required there; the script exits non-zero without it. On agy, `mcp_config.json` invokes the script but sets no `env` for it — the value must already be in the process environment that launches agy. Inside an aops-crew container that is guaranteed (the entrypoint exports it). On a bare host, exporting it is still not enough: the launcher path itself carries `${extensionPath}`, which only the aops-crew image rewrites, so `agy plugin install` outside that image cannot start the server at all. |
| `ACA_DATA`    | environment         | The PKB root. `$ACA_DATA/.agents/workflows/` overrides and extends the shipped workflow library by filename. Unset means there is no user layer — not an error.                                                                                                                                                                                                                                                                                                                                                                                                                                           |

`$ACA_DATA` is the PKB's storage, reached through the MCP tools. Nothing in this
plugin reads or writes it as a filesystem path.

## Depends on

- A PKB MCP server, reachable at the configured endpoint. The server is external
  to this plugin; the plugin ships client wiring only.
- `lib/hooks/`, injected into `hooks/` at build time.
- `lib/axioms/`, applied as global rule context for pauli.
- `uv`, for the stdio launcher only.
