# ts

Opt-in Tailscale bring-up for academicOps remote/cloud sessions, and the
transcript sync that gets a session's record off the box before it disappears.

```mermaid
flowchart TD
    A[SessionStart fires] --> B{CLAUDE_CODE_REMOTE=true?}
    B -- no --> Z[exit 0, no-op]
    B -- yes --> C{TS_AUTHKEY set?}
    C -- no --> Z
    C -- yes --> D{tailscale on PATH?}
    D -- no --> Z
    D -- yes --> E{tailscale status succeeds?}
    E -- yes, already up --> F[log current tailnet IP]
    E -- no --> G[start tailscaled if not running]
    G --> H["tailscale up --authkey=$TS_AUTHKEY --accept-routes --accept-dns=true"]
    H -- succeeds --> F
    H -- fails --> I[log failure to stderr, still exit 0]

    A2[SessionEnd fires] --> B2{CLAUDE_CODE_REMOTE=true?}
    B2 -- no --> Z2[exit 0, no-op]
    B2 -- yes --> C2{AOPS_TS_SYNC_DEST set?}
    C2 -- no --> Z2
    C2 -- "set but not host:path" --> X2[FATAL, exit 1 — never guess a destination]
    C2 -- yes --> D2{tailnet up? tar + ssh present?}
    D2 -- no --> Z2
    D2 -- yes --> E2{transcript_path in payload?}
    E2 -- yes --> S1[single-session mode]
    E2 -- no --> S2["batch mode, --all"]
    S1 --> R{"AOPS_SRC_DIR has lib/py/transcripts/runner.py?"}
    S2 --> R
    R -- yes --> P["render into a staging dir, --no-sync"]
    R -- "no, batch mode" --> Z2
    R -- "no, single session" --> RAW{AOPS_TS_SYNC_RAW=1?}
    RAW -- no --> Z2
    RAW -- yes --> P2[stage the RAW, UNREDACTED JSONL]
    P --> T["tar czf - | RSH HOST 'tar xzf -'"]
    P2 --> T
    T --> Y[log outcome, exit 0]
```

Both hooks always exit 0 — a Tailscale failure never blocks session start, and
a sync failure never blocks session end. The one exception is a malformed
`AOPS_TS_SYNC_DEST`, which exits 1 rather than invent a landing directory. All
diagnostics go to stderr; stdout stays empty because hook stdout is injected
into the model context.

## Provides

| Type | Name           | Effect                                                                                    |
| ---- | -------------- | ----------------------------------------------------------------------------------------- |
| Hook | `SessionStart` | Runs `hooks/tailscale-up.sh`, bringing the tailnet up.                                    |
| Hook | `SessionEnd`   | Runs `hooks/session-end-sync.sh`, shipping the session transcript to the configured host. |

Both are wired for Claude Code. `SessionStart` is also wired for agy;
`SessionEnd` is not, because agy has no confirmed wire event for it.

## Configuration

No value in this plugin has a default. Every value below must come from the
environment. With none of them set, both hooks are silent no-ops.

| Var                  | Used by        | Required       | Meaning                                                                                                                                                                        |
| -------------------- | -------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CLAUDE_CODE_REMOTE` | both           | yes            | Must be exactly `true` for either hook to act at all.                                                                                                                          |
| `TS_AUTHKEY`         | `SessionStart` | yes            | Tailscale auth key used for `tailscale up --authkey=...`.                                                                                                                      |
| `HOSTNAME`           | `SessionStart` | no             | When set, the tailnet device is named `claude-web-${HOSTNAME}`. When unset, no `--hostname` is passed and Tailscale chooses its own device name.                               |
| `AOPS_TS_SYNC_DEST`  | `SessionEnd`   | yes            | Where transcripts land, as `[user@]host:path`. Both halves required. Unset means no sync at all; malformed means exit 1.                                                       |
| `AOPS_SRC_DIR`       | `SessionEnd`   | yes, to render | An academicOps checkout containing `lib/py/transcripts/runner.py` and either a `.venv` or `uv` on `PATH`. The pipeline has third-party dependencies, so it runs from there.    |
| `AOPS_TS_SYNC_RAW`   | `SessionEnd`   | no             | `1` permits shipping the raw session JSONL when the pipeline is unavailable. Raw transcripts are **unredacted**. Unset means such a session is skipped rather than sent as-is. |
| `AOPS_TS_SSH_CMD`    | `SessionEnd`   | no             | Remote-shell program. `tailscale ssh` when tailscale is on `PATH`, else `ssh`. A program name only — every host and path comes from `AOPS_TS_SYNC_DEST`.                       |
| `AOPS_TS_SSH_OPTS`   | `SessionEnd`   | no             | Extra options for the plain-`ssh` path, e.g. `-o StrictHostKeyChecking=accept-new`.                                                                                            |

The payload lands under the destination path as `transcripts/` (rendered
markdown, HTML, and JSON) and, on the opt-in raw path only, `incoming/`.

## Depends on

- `tailscale` (and `tailscaled`) on `PATH`, installed by the environment's own
  setup/init script — this plugin never installs it.
- `openssh-client` and `tar` on `PATH` for the sync; `tar` on the remote. No
  `rsync` on either side.
- Passwordless `sudo` when the session runs as a non-root user (auto-detected;
  falls back to running direct, which works only as root).
- An academicOps checkout at `AOPS_SRC_DIR` for transcript rendering. The
  plugin ships no Python and reads no other plugin's files; without the
  checkout it renders nothing.
