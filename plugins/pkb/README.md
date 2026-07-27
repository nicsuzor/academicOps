# aops-pkb

Pauli — memory, effectual planning, workflow composition, and the client wiring
for a Personal Knowledge Base.

## How it works

```mermaid
flowchart TD
    prompt([user prompt]) --> hook

    subgraph hookpath["every prompt"]
        hook["UserPromptSubmit<br/>hooks/handlers.py"]
        hook --> msg["hooks/messages/pkb-context.md<br/>search the PKB before acting"]
    end

    msg --> agent
    prompt --> agent["any agent"]

    agent -- "planning, memory,<br/>anything that writes" --> pauli

    subgraph pkbwrite["agents/pauli.md — the only writer to the PKB"]
        pauli(("pauli"))
        pauli --> planner["skills/planner<br/>altitude · means · assumptions<br/>sequence by information value"]
        planner --> hydrate["skills/hydrate<br/>context bundle"]
        hydrate --> situate["skills/situate<br/>one task, valued and wired"]
        situate --> decompose["skills/decompose<br/>subtask DAG + review nodes"]
        decompose --> brief["skills/brief<br/>delegation brief"]
        decompose -.-> workflow["skills/workflow<br/>compose the process"]
        pauli --> remember["skills/remember<br/>capture · consolidate"]
        pauli --> graph["skills/graph-maintenance<br/>wire · garden"]
    end

    workflow --> library[["workflows/INDEX.md<br/>workflows/process/*.md"]]
    workflow --> userlayer[["$ACA_DATA/.agents/workflows/<br/>overrides by filename"]]
    workflow --> wf[["PKB documents tagged wf-template"]]

    remember --> mcp
    graph --> mcp
    situate --> mcp
    decompose --> mcp
    brief --> mcp

    mcp[".mcp.json — services<br/>HTTP, or scripts/run-mcp.sh over stdio"] --> pkbstore[(PKB)]

    brief --> dispatch([dispatch by task id])
```

The hook fires on every prompt and never calls the PKB itself — it tells the
agent to search, and names the searches worth running. Establishing an MCP
session on the critical path of every turn is not affordable, and a slow server
would stall the turn.

Everything that mutates the PKB goes through pauli. Its tool grant is the only
one carrying PKB mutation; other agents reach the graph by asking it.

## What it provides

### Agent

| Agent   | Does                                                                                                         |
| ------- | ------------------------------------------------------------------------------------------------------------ |
| `pauli` | Logician, effectual strategist, and custodian of the PKB. The sole writer to it. Call first, and call often. |

### Skills

| Skill               | Does                                                                                                        |
| ------------------- | ----------------------------------------------------------------------------------------------------------- |
| `planner`           | Effectual planning: fix the altitude, start from means, surface assumptions, sequence by what teaches most. |
| `hydrate`           | Emit a right-sized context bundle so nothing downstream starts cold.                                        |
| `situate`           | Turn a hydrated ask into one valued, well-connected task, then stop.                                        |
| `decompose`         | Cut a due task into a subtask DAG and emit its review steps as blocking nodes.                              |
| `brief`             | Turn the subtask that is due into a brief a cold agent can execute and be judged on.                        |
| `workflow`          | Compose the process this work runs under, from the shipped library, the user layer, and the PKB.            |
| `remember`          | Capture knowledge as it emerges; consolidate episodic records into durable notes.                           |
| `graph-maintenance` | Wire weighted `contributes_to` edges; garden parentage, links, duplicates, and orphans.                     |

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

| Setting       | Where it comes from | For                                                                                                                                                             |
| ------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pkb_mcp_url` | client `userConfig` | The streamable-HTTP endpoint of the PKB MCP server. Claude Code reads it into `.mcp.json`.                                                                      |
| `PKB_MCP_URL` | environment         | The same endpoint, for clients that launch the server over stdio via `scripts/run-mcp.sh`. Required there; the script exits non-zero without it.                |
| `ACA_DATA`    | environment         | The PKB root. `$ACA_DATA/.agents/workflows/` overrides and extends the shipped workflow library by filename. Unset means there is no user layer — not an error. |

`$ACA_DATA` is the PKB's storage, reached through the MCP tools. Nothing in this
plugin reads or writes it as a filesystem path.

## Depends on

- A PKB MCP server, reachable at the configured endpoint. The server is external
  to this plugin; the plugin ships client wiring only.
- `lib/hooks/`, injected into `hooks/` at build time.
- `lib/doctrine/`, inlined into `agents/pauli.md` at build time.
- `uv`, for the stdio launcher only.
