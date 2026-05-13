---
title: Claude Code Surfaces — Paths & Environment
type: reference
category: ref
permalink: ref-claude-surfaces
description: Where each Claude Code surface (CLI, GUI Claude Code, Cowork) reads plugins from, inherits env vars, and writes transcripts/hook logs
---

# Claude Code Surfaces — Paths & Environment

Three local Claude Code surfaces on this Mac. None executes in the cloud. Verified 2026-05-13.

## Comparison

|                             | **CLI Claude Code**                                                                          | **GUI Claude Code**                                                                         | **Cowork**                                                                                                                    |
| --------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Launched from**           | `claude` in terminal                                                                         | Claude.app → Claude Code tab                                                                | Claude.app → Cowork tab                                                                                                       |
| **Runtime**                 | full Claude Code                                                                             | full Claude Code (embedded binary in app)                                                   | cut-down Claude-Code-like                                                                                                     |
| **Plugin source**           | `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`                                  | same as CLI                                                                                 | `~/Library/Application Support/Claude/local-agent-mode-sessions/<account>/<surface>/rpm/plugin_<id>/`                         |
| **Plugin install**          | `claude plugin install` / `make install`                                                     | same as CLI (shared store)                                                                  | GUI: Cowork → Customize → Upload from file. Build with `make package-cowork`.                                                 |
| **Plugin registry**         | `~/.claude/plugins/installed_plugins.json`                                                   | same as CLI                                                                                 | `…/rpm/manifest.json` (account-bound; mirrors server)                                                                         |
| **Env source**              | interactive shell (`~/.zshrc`, `~/.env.local`)                                               | launchd (`launchctl getenv`) — does NOT source shell                                        | launchd (same as GUI Claude Code)                                                                                             |
| **Session transcript**      | `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`                                        | same as CLI                                                                                 | session JSON under `…/local-agent-mode-sessions/<account>/<surface>/local_<id>.json` (plus per-session working dir alongside) |
| **Aops hooks log**          | `~/.claude/projects/<encoded-cwd>/<YYYYMMDD-HHMM>-<short>-<repo>-claude-session-hooks.jsonl` | same as CLI                                                                                 | same as CLI (path set via `AOPS_HOOK_LOG_PATH` by SessionStart hook)                                                          |
| **Rendered transcripts**    | `$AOPS_SESSIONS/transcripts/` (= `~/src/sessions/transcripts/`)                              | same                                                                                        | same                                                                                                                          |
| **Settings**                | `~/.claude/settings.json`                                                                    | same                                                                                        | n/a                                                                                                                           |
| **MCP-only DXT extensions** | n/a                                                                                          | `~/Library/Application Support/Claude/Claude Extensions/` + `extensions-installations.json` | same as GUI Claude Code                                                                                                       |

## Per-session env file (`CLAUDE_ENV_FILE`)

SessionStart hooks that need to persist env vars write them to `$CLAUDE_ENV_FILE` (path provided by Claude Code per session). Aops uses this in `session_env_setup.py`.

| Concern                                      | Path                                                          |
| -------------------------------------------- | ------------------------------------------------------------- |
| Hook-written env file                        | `~/.claude/session-env/<session-id>/sessionstart-hook-<N>.sh` |
| Shell snapshot Bash-tool subprocesses source | `~/.claude/shell-snapshots/snapshot-zsh-<ts>-<id>.sh`         |

**Known 2.1.138 quirk**: Bash tool subprocesses source the shell snapshot but **not** the session-env hook file. Anything `session_env_setup.py` writes (e.g. `GH_TOKEN=$AOPS_BOT_GH_TOKEN`, `GIT_CONFIG_COUNT=4`, `SSH_AUTH_SOCK=""`) lands in the file correctly but never reaches Bash subprocesses — credential isolation chain is silently bypassed. Sourcing the env file manually inside a Bash tool call restores the expected state, which proves the file content is fine and only the harness wiring is broken. Re-verify on each Claude Code version bump.

## launchd env (GUI surfaces)

GUI Claude Code and Cowork inherit env from launchd, not from `~/.zshrc` / `~/.env.local`. Two installable files manage this; templates live in `scripts/macos-launchd/`.

| File                                                              | Role                                                                                                                                                                                                                                                                                                                                                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/Library/LaunchAgents/com.aops.envvars.plist`                   | LaunchAgent — runs at login, sources the two files below, calls `launchctl setenv` for `AOPS_SESSIONS` and `POLECAT_HOME`. Contains no secrets.                                                                                                                                                                                                                                                   |
| `~/.env.local`                                                    | User-secret store. Holds `AOPS_BOT_GH_TOKEN`. Also sourced by interactive shells.                                                                                                                                                                                                                                                                                                                 |
| `$POLECAT_HOME/launchd-env.sh` (default `~/.aops/launchd-env.sh`) | Credential isolation chain. Sources `AOPS_BOT_GH_TOKEN` → exports `GH_TOKEN`, `GITHUB_TOKEN`, `SSH_AUTH_SOCK=""`, `GIT_SSH_COMMAND=false`, and the four-entry `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n` chain that routes git via HTTPS + bot PAT and clears inherited credential helpers. **Do NOT source from interactive shell rc files** — these lockdowns would hijack normal terminal git usage. |

Effect: GUI Claude Code and Cowork sessions authenticate to GitHub as the bot identity (`GH_TOKEN`); SSH key fallback is blocked; system git config is shadowed. Verify with `gh auth status` inside a fresh GUI session — bot account should be `Active account: true`.

### Install / update

```
cp scripts/macos-launchd/com.aops.envvars.plist ~/Library/LaunchAgents/
cp scripts/macos-launchd/launchd-env.sh        "$POLECAT_HOME/launchd-env.sh"   # default ~/.aops/
launchctl load   ~/Library/LaunchAgents/com.aops.envvars.plist
launchctl kickstart -k gui/$(id -u)/com.aops.envvars     # forces RunAtLoad
launchctl getenv AOPS_SESSIONS                            # verify (token vars: check length only)
```

Then fully quit + relaunch Claude.app (Cmd-Q) — already-running processes keep the old env. `launchctl unsetenv VAR` clears a value; deleting the plist alone does not. `launchctl load` after `unload` does NOT re-run `RunAtLoad` reliably — use `kickstart -k` to force a fresh run after edits.

## Verification commands

| Question                                          | Command                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| CLI / GUI Claude Code: which versions are cached? | `ls ~/.claude/plugins/cache/<marketplace>/<plugin>/`                                             |
| CLI / GUI Claude Code: which version is active?   | `cat ~/.claude/plugins/installed_plugins.json`                                                   |
| Cowork: which plugins are installed?              | `cat ~/Library/Application\ Support/Claude/local-agent-mode-sessions/*/*/rpm/manifest.json`      |
| What env will GUI surfaces inherit?               | `launchctl getenv <VAR>`                                                                         |
| Marketplace pin                                   | `cat ~/.claude/plugins/marketplaces/academicOps/.claude-plugin/marketplace.json \| grep version` |

## Housekeeping

- `make clean-plugins` (also via `make clean`) prunes stale CLI cache versions + orphan install manifests, AND force-removes `aops-*` entries from Cowork's `rpm/manifest.json` when the GUI's uninstall button fails. Implementation: `scripts/clean_plugins.py`.
- `make install` updates the CLI/GUI Claude Code shared cache. Does **not** touch Cowork's rpm store.
- `make package-cowork` builds `dist/aops-core-v<X>.zip` for Cowork upload.
