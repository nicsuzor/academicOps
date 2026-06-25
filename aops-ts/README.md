# aops-ts

Opt-in Tailscale bring-up for academicOps remote/cloud sessions.

`aops-ts` is a single-purpose plugin: a `SessionStart` hook that runs
`tailscale up` so tailnet-only services — most importantly the **PKB MCP server**
at `*.ts.net` — resolve inside a remote session (e.g. Claude Code on the web).

It is deliberately **separate from `aops-core`** so joining the tailnet is an
explicit choice. Installing `aops-core` never brings up Tailscale on its own;
you must add `aops-ts` to an environment that should be on the tailnet.

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
kept empty).
