# aops-ts

Opt-in Tailscale bring-up + transcript egress for academicOps remote/cloud sessions.

`aops-ts` ships two hooks:

- A **`SessionStart`** hook that runs `tailscale up` so tailnet-only services —
  most importantly the **PKB MCP server** at `*.ts.net` — resolve inside a remote
  session (e.g. Claude Code on the web).
- A **`SessionEnd`** hook that parses the session transcript and rsyncs it to a
  tailnet host, so cloud sessions (which have no durable filesystem and no
  inbound access) don't lose their transcript when the container is reclaimed.

It is deliberately **separate from `aops-core`** so joining the tailnet is an
explicit choice. Installing `aops-core` never brings up Tailscale on its own;
you must add `aops-ts` to an environment that should be on the tailnet. The
`SessionStart` bring-up is a self-contained bash hook with no dependencies; the
`SessionEnd` sync hook reuses `aops-core`'s `transcript.py` when available and
falls back to shipping the raw JSONL otherwise.

## Why a hook (and not the setup script)

The authkey (`TS_AUTHKEY`) is injected at **session runtime**, not at container
init. So bring-up cannot live in the environment's setup script — it must run at
`SessionStart`, which is exactly what this hook does. User-level
(`~/.claude/settings.json`) hooks do not run in cloud sessions, so the bring-up
must ship as a repo/plugin hook.

## Prerequisites

1. **Tailscale installed.** This plugin does **not** install Tailscale (that
   needs root + `curl | sh` at container init). Add the install to your
   environment's setup script:

   ```bash
   command -v tailscale >/dev/null 2>&1 || curl -fsSL https://tailscale.com/install.sh | sh
   ```

2. **`TS_AUTHKEY` available at session time.** Provision it as an environment
   variable for the remote environment.

3. **`aops-ts` enabled.** Install the plugin in environments that should join
   the tailnet:

   ```bash
   claude plugin install aops-ts@academicOps
   ```

## Behaviour

The hook no-ops (exit 0) unless **all** of these hold:

- `CLAUDE_CODE_REMOTE=true` (only acts in remote/cloud sessions)
- `TS_AUTHKEY` is set
- `tailscale` is on `PATH`

When it acts, it starts `tailscaled` if needed, then runs `tailscale up` with
`--accept-dns=true` (required for MagicDNS resolution of `*.ts.net` hosts). It
always exits 0 — a Tailscale failure must never block session start. Diagnostics
go to stderr (SessionStart stdout is injected into the model context, so it is
kept empty). In non-root environments it auto-detects passwordless `sudo`.

## Session transcript sync (SessionEnd)

The `SessionEnd` hook (`session-end-sync.sh`) ships this session's transcript to
a tailnet host. It no-ops (exit 0) unless **all** of these hold:

- `CLAUDE_CODE_REMOTE=true`
- `AOPS_TS_SYNC_DEST` is set (the rsync/ssh destination)
- the tailnet is up (`tailscale status` succeeds)
- `rsync` is on `PATH`

Config (env):

| Var                 | Required | Meaning                                                                              |
| ------------------- | -------- | ------------------------------------------------------------------------------------ |
| `AOPS_TS_SYNC_DEST` | yes      | rsync/ssh dest on the tailnet, e.g. `nic@services-new:/data/aops-sessions/incoming/` |
| `AOPS_TS_SSH_OPTS`  | no       | extra ssh options, e.g. `-o StrictHostKeyChecking=accept-new`                        |
| `AOPS_SRC_DIR`      | no       | aops-core source dir (else the plugin cache is searched)                             |

It runs `aops-core`'s `transcript.py` (with `--no-sync`) into a staging dir —
producing the same redacted markdown + summary JSON the local pipeline commits to
`$AOPS_SESSIONS` — then `rsync`s the staging dir to `AOPS_TS_SYNC_DEST` over ssh.
If `aops-core`/`transcript.py` can't be run, it falls back to shipping the **raw
JSONL**, which is **unredacted** — so only sync to a trusted tailnet host you
control. SSH auth is your environment's responsibility (an ssh key, or Tailscale
SSH with an ACL permitting this node). It always exits 0.
