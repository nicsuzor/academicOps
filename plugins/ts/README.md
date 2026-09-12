# ts

Opt-in Tailscale bring-up for academicOps remote/cloud sessions.

## Hooks

- `SessionStart`: Runs `hooks/tailscale-up.sh` to connect to the tailnet when `CLAUDE_CODE_REMOTE=true` and `TS_AUTHKEY` is set.

The hook exits 0 on failure to avoid blocking sessions. Diagnostics go to stderr.

## Configuration

All configuration is provided via environment variables (no defaults):

| Variable             | Used by        | Required | Description                                                                          |
| -------------------- | -------------- | -------- | ------------------------------------------------------------------------------------ |
| `CLAUDE_CODE_REMOTE` | `SessionStart` | Yes      | Must be `true` for the hook to execute.                                              |
| `TS_AUTHKEY`         | `SessionStart` | Yes      | Tailscale auth key for `tailscale up`.                                               |
| `HOSTNAME`           | `SessionStart` | No       | Tailnet device name: `claude-web-${HOSTNAME}` (defaults to Tailscale-assigned name). |

## Dependencies

- `tailscale` / `tailscaled` on `PATH` (pre-installed by host).
- Passwordless `sudo` if running as non-root.
