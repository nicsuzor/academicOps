# Environment Variable Audit

This audit enumerates every location that sets or overrides framework-relevant environment variables across `academicOps`, `dotfiles`, and Claude settings.

## Summary Table

| Variable                    | Authoritative Source            | Set Where                                                                                         | Consumed Where                                                    |
| --------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `AOPS`                      | `dotfiles` (`setup.sh`)         | `dotfiles/servers/remote/setup.sh`, `dotfiles/servers/nicwin/setup.sh`                            | `polecat/bootstrap.py`, `polecat/swarm.py`, build scripts         |
| `AOPS_BOT_GH_TOKEN`         | `.env.local` (via `sops`)       | `~/.claude/settings.json`, `~/.claude/settings.local.json`                                        | `polecat/bootstrap.py`, `polecat/entrypoint.sh`                   |
| `GH_TOKEN` / `GITHUB_TOKEN` | `polecat/entrypoint.sh`         | `dotfiles/scripts/cron-lib.sh`, `polecat/entrypoint.sh`, Claude `sessionstart-hook*.sh`           | GHA workflows, local Git credential helper                        |
| `PKB_MCP_URL`               | `~/.claude/settings.local.json` | Claude settings (`~/.claude/settings.local.json`), `dotfiles/scripts/polecat-dispatch-via-ssh.sh` | `polecat/pkb_bridge.py`, `polecat/cli.py`, `polecat/bootstrap.py` |
| `PKB_PORT`                  | `~/.claude/settings.json`       | Claude settings                                                                                   | Legacy PKB / MCP resolution                                       |
| `POLECAT_HOME`              | `~/.claude/settings.json`       | Claude settings (`~/.claude/settings.json`, `sessionstart-hook*.sh`)                              | `polecat/bootstrap.py`, `polecat/cli.py`                          |
| `AOPS_SESSIONS`             | `~/.claude/settings.json`       | Claude settings (`~/.claude/settings.json`)                                                       | `polecat/cli.py`                                                  |
| `GEMINI_API_KEY`            | `.env.local` (via `sops`)       | `~/.claude/settings.json`                                                                         | `polecat/bootstrap.py`, `polecat/cli.py`                          |
| `ACA_DATA`                  | `.env.local` (via `sops`)       | `~/.claude/settings.json`                                                                         | PKB server initialization, data resolution                        |

## Details by Location

### 1. `academicOps` Repository (Current)

- **`polecat/entrypoint.sh`**:
  - **SETS**: `GH_TOKEN`, `GITHUB_TOKEN` (derived directly from `AOPS_BOT_GH_TOKEN`).
  - **SETS**: git credential helper using `GH_TOKEN`.
- **`polecat/cli.py`**:
  - **CONSUMES**: `PKB_MCP_URL`, `POLECAT_HOME`, `AOPS_SESSIONS`, `GEMINI_API_KEY`, etc.
- **`polecat/bootstrap.py` / `pkb_bridge.py`**:
  - **CONSUMES**: `PKB_MCP_URL`, `AOPS_BOT_GH_TOKEN`, `AOPS`.

### 2. `~/dotfiles`

- **`dotfiles/scripts/cron-lib.sh`**:
  - **SETS**: `GH_TOKEN` from `AOPS_BOT_GH_TOKEN` after decrypting `.env.local`.
- **`dotfiles/servers/remote/setup.sh` & `servers/nicwin/setup.sh`**:
  - **SETS**: `AOPS` to `$HOME/src/academicOps`.
- **`dotfiles/scripts/polecat-dispatch-via-ssh.sh`**:
  - **OVERRIDES**: `POLECAT_HOME`, `AOPS_SESSIONS`, `PKB_MCP_URL` for remote sessions.

### 3. Claude Settings

- **`~/.claude/settings.json` & `.claude/settings.local.json`**:
  - **SETS**: `AOPS_BOT_GH_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, `PKB_MCP_URL`, `POLECAT_HOME`, `AOPS_SESSIONS`.
  - **MECHANISM**: Injects these heavily into `sessionstart-hook.sh` for Claude Code initialization.
