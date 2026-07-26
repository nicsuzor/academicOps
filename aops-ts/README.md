# aops-ts: Tailscale Bring-Up & Transcript Egress

`aops-ts` provides opt-in Tailscale bring-up and transcript egress synchronization for academicOps remote and cloud sessions.

`aops-ts` ships two hooks:
- **`SessionStart`**: Runs `tailscale up` so tailnet-only services — most importantly the **PKB MCP server** at `*.ts.net` — resolve inside a remote session.
- **`SessionEnd`**: Parses session transcripts and ships them to a tailnet host over `tailscale ssh`, preserving transcript records when cloud containers are reclaimed.

## Control Flow & Architecture

```mermaid
flowchart TD
    subgraph SessionStartFlow ["SessionStart Hook (hooks/tailscale-up.sh)"]
        S1["Event: SessionStart"]
        S2{"Check Env: CLAUDE_CODE_REMOTE=true & TS_AUTHKEY set?"}
        S3["Start tailscaled daemon if needed"]
        S4["Run tailscale up --accept-dns=true"]
        S5["No-op (exit 0)"]
    end

    subgraph SessionEndFlow ["SessionEnd Hook (hooks/session-end-sync.sh)"]
        E1["Event: SessionEnd"]
        E2{"Check Env: CLAUDE_CODE_REMOTE=true & AOPS_TS_SYNC_DEST set?"}
        E3{"Validate AOPS_TS_SYNC_DEST format ([user@]host:path)"}
        E4["Run transcript.py -> staging directory"]
        E5["Stream tarball via tailscale ssh (or AOPS_TS_SSH_CMD)"]
        E6["Fail fast (exit 1) on malformed dest"]
        E7["No-op (exit 0)"]
    end

    S1 --> S2
    S2 -- Yes --> S3 --> S4
    S2 -- No --> S5

    E1 --> E2
    E2 -- Yes --> E3
    E2 -- No --> E7
    E3 -- Valid --> E4 --> E5
    E3 -- Malformed --> E6
```

## Customisation Surface

### Plugin Configuration (`userConfig`)

| Option | Type | Description |
| :--- | :--- | :--- |
| `sync_dest` | `string` | Transcript egress destination `[user@]host:path` on the tailnet. Maps to `AOPS_TS_SYNC_DEST`. |
| `ssh_cmd` | `string` | Custom SSH command override for transcript egress. Maps to `AOPS_TS_SSH_CMD`. |

### Environment Variables

| Variable | Required | Meaning | Default |
| :--- | :--- | :--- | :--- |
| `CLAUDE_CODE_REMOTE` | Yes (activation) | Hook no-ops unless set to `true` (remote/cloud session indicator). | None |
| `TS_AUTHKEY` | Yes (SessionStart) | Tailscale authentication key used for container bring-up. | None |
| `AOPS_TS_SYNC_DEST` | Yes (SessionEnd) | Destination `[user@]host:path` on the tailnet. Both host and `:path` are required. Malformed destination exits 1. | None |
| `AOPS_TS_SSH_CMD` | Optional | Full remote-shell command override. Defaults to `tailscale ssh` when tailscale is present. | `tailscale ssh` |
| `AOPS_TS_SSH_OPTS` | Optional | Extra SSH options for fallback plain `ssh` (ignored if `AOPS_TS_SSH_CMD` is set). | None |
| `AOPS_SRC_DIR` | Optional | `aops-core` source directory used to locate `transcript.py`. | Plugin cache search |

## Behaviour & Prerequisites

1. **Tailscale installed**: Prerequisites require `tailscale` binary on `PATH`.
2. **`TS_AUTHKEY` set**: Injected at session runtime.
3. **Session Egress Layout**: Destination receives payload structured into `transcripts/`, `summaries/`, and raw JSONL fallback in `incoming/`.

## Installation

```bash
claude plugin install aops-ts@academicOps
```

## Contents

- `hooks/tailscale-up.sh` — `SessionStart` Tailscale bring-up script.
- `hooks/session-end-sync.sh` — `SessionEnd` transcript packaging and SSH streaming script.
- `hooks/hooks.json` — Manifest declaring `SessionStart` and `SessionEnd` hooks.
