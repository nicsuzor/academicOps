# aops-pkb: Personal Knowledge Base & Task Intake

`aops-pkb` is the knowledge graph and task intake package for academicOps. It contains the Pauli persona (`pauli`), graph maintenance procedures, task intake skills (`hydrate`, `situate`, `decompose`), brief composition (`brief`), and unified memory storage (`remember`).

## Control Flow & Architecture

```mermaid
flowchart TD
    subgraph Input ["User Prompt / Inbound Ask"]
        P["User Request / Goal"]
    end

    subgraph Pipeline ["Task Intake & Graph Pipeline"]
        H["/hydrate: Search PKB & workflow index for context bundle"]
        S["/situate: Convert prompt to task node (status: needs_decomposition)"]
        D["/decompose: Cut task into subtask DAG with review steps"]
        B["/brief: Compose 7-element delegation brief for due subtasks"]
        R["/remember: Synthesize learnings & store in PKB memory"]
        G["/graph-maintenance: Densify edges & fix orphan nodes"]
    end

    subgraph PKB ["PKB Storage & Outputs"]
        K1["data/tasks/*.md Task Graph"]
        K2["Delegation Briefs & Workflows"]
        K3["PKB Memories & Context Nodes"]
    end

    P --> H --> S --> D --> B
    D --> K1
    B --> K2
    R --> K3
    G --> K1
```

## Customisation Surface

### Plugin Configuration (`userConfig`)

| Option | Type | Description |
| :--- | :--- | :--- |
| `pkb_mcp_url` | `string` | Endpoint URL of the PKB MCP server (`PKB_MCP_URL`). |
| `aca_data` | `string` | Path to your personal knowledge base root directory (`ACA_DATA`). |

### Environment Variables

| Variable | Required | Description | Default |
| :--- | :--- | :--- | :--- |
| `PKB_MCP_URL` | Yes (remote) | URL for the PKB MCP server (Streamable HTTP or local stdio fallback). | Local stdio |
| `ACA_DATA` | Yes | Path to local personal knowledge base root directory containing tasks and notes. | None |

## Installation & Quickstart

### Claude Code

```bash
claude plugin install aops-pkb@academicOps
```

### Antigravity (`agy`)

```bash
agy plugin install ./dist/aops-pkb-antigravity
```

## Contents

- `agents/pauli.md` — Persona charter for Pauli (design intent & graph guardian).
- `skills/` — Graph and intake skills (`hydrate`, `situate`, `decompose`, `brief`, `remember`, `graph-maintenance`).
- `workflows/` — Standard operating procedures and process indexes (`INDEX.md`, `feature-dev.md`, `tdd.md`, etc.).
- `templates/` — Manifest templates (`aops-pkb.template.json`, `mcp.template.json`).
