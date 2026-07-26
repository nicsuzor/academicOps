# aops-cowork: Cowork Native Task Synchronization

`aops-cowork` provides task list synchronization for Anthropic Cowork environments. It mirrors task units from the Personal Knowledge Base (PKB) onto Cowork's native interactive task list at `/pull` claim time and syncs completed status back to PKB.

## Control Flow & Architecture

```mermaid
flowchart TD
    subgraph Triggers ["Triggers"]
        PULL["/pull skill invocation (task claim)"]
        NATIVE["Native Task UI update (mark task completed)"]
        DUMP["/dump full skill invocation (handover)"]
    end

    subgraph Processing ["aops-cowork Processing"]
        P1["skills/cowork-sync: ToolSearch(TaskCreate, TaskUpdate, TaskList, TaskGet)"]
        P2["Fetch PKB task & subtask tree via pkb__get_task"]
        P3["Create parent & subtask native items via TaskCreate & TaskUpdate(addBlocks)"]
        P4["Parse PKB ID prefix & invoke pkb__complete_task"]
        P5["Reconcile all TaskList() items against PKB status"]
    end

    subgraph Emits ["Outputs & Emits"]
        E1["Harness-native task hierarchy in Cowork UI"]
        E2["Real-time PKB subtask completion"]
        E3["Final PKB state reconciliation"]
    end

    PULL --> P1 --> P2 --> P3 --> E1
    NATIVE --> P4 --> E2
    DUMP --> P5 --> E3
```

## Customisation Surface

### Plugin Configuration (`userConfig`)

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `auto_sync` | `boolean` | `true` | Automatically mirror PKB tasks onto the Cowork native task list during `/pull`. |
| `sync_children` | `boolean` | `true` | Mirror PKB subtask leaf nodes as blocking native tasks on the Cowork task list. |

## Installation & Quickstart

`aops-cowork` is bundled in the Cowork distribution build (`dist/cowork`).

```bash
claude plugin install aops-cowork@academicOps-cowork
```

## Contents

- `skills/cowork-sync/` — Procedures for mirroring tasks and reconciling status between PKB and Cowork native tasks.
- `.claude-plugin/plugin.json` — Plugin manifest with `userConfig` options.
