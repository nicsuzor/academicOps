# ts

Opt-in Tailscale bring-up for academicOps remote/cloud sessions and session transcript sync.

## Hooks

- `SessionStart`: Runs `hooks/tailscale-up.sh` to connect to the tailnet when `CLAUDE_CODE_REMOTE=true` and `TS_AUTHKEY` is set.
- `SessionEnd`: Runs `hooks/session-end-sync.sh` to render and ship session transcripts to `AOPS_TS_SYNC_DEST` via SSH/tar.

Both hooks exit 0 on failure to avoid blocking sessions, except for a malformed `AOPS_TS_SYNC_DEST` (exits 1). Diagnostics go to stderr.

## Configuration

All configuration is provided via environment variables (no defaults):

| Variable             | Used by        | Required | Description                                                                          |
| -------------------- | -------------- | -------- | ------------------------------------------------------------------------------------ |
| `CLAUDE_CODE_REMOTE` | Both           | Yes      | Must be `true` for hooks to execute.                                                 |
| `TS_AUTHKEY`         | `SessionStart` | Yes      | Tailscale auth key for `tailscale up`.                                               |
| `HOSTNAME`           | `SessionStart` | No       | Tailnet device name: `claude-web-${HOSTNAME}` (defaults to Tailscale-assigned name). |
| `AOPS_TS_SYNC_DEST`  | `SessionEnd`   | Yes      | Remote target as `[user@]host:path`.                                                 |
| `AOPS_SRC_DIR`       | `SessionEnd`   | Yes      | academicOps checkout with `lib/py/transcripts/runner.py`.                            |
| `AOPS_TS_SYNC_RAW`   | `SessionEnd`   | No       | Set to `1` to ship raw unredacted JSONL if rendering pipeline is absent.             |
| `AOPS_TS_SSH_CMD`    | `SessionEnd`   | No       | SSH binary (default: `tailscale ssh` if on PATH, else `ssh`).                        |
| `AOPS_TS_SSH_OPTS`   | `SessionEnd`   | No       | Extra SSH flags (e.g. `-o StrictHostKeyChecking=accept-new`).                        |

## Dependencies

- `tailscale` / `tailscaled` on `PATH` (pre-installed by host).
- `tar` and `openssh-client` on local `PATH`; `tar` on remote.
- Passwordless `sudo` if running as non-root.
- academicOps checkout at `AOPS_SRC_DIR` for transcript rendering.
