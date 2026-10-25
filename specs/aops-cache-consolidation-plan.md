---
title: Local Cache and Working Directory Consolidation
status: ready
---

# Local Cache and Working Directory Consolidation

Unifies local cache, state, configuration, and temporary working directories across the framework under the XDG Base Directory Specification, replacing legacy unpartitioned dotfiles and ad-hoc temp paths with standard, predictable paths.

## User stories

### US-1 Predictable Cache Management

As a developer or agent, I want recomputable model weights and binary caches stored under standard cache paths, so that caches can be purged without destroying configuration or active session state.

- **AC-1.1** Given a component storing recomputable cache data (such as embedding model weights), when resolving its storage path, then it uses `$XDG_CACHE_HOME/aops` (defaulting to `~/.cache/aops`).

### US-2 Isolated State and Worktrees

As a framework orchestrator, I want isolated git checkouts and session state stored in dedicated state paths, so that machine-local state persists across invocations but remains partitioned from configuration.

- **AC-2.1** Given a polecat session requiring an isolated git clone or worktree, when creating the working directory, then the directory is allocated under `$XDG_STATE_HOME/aops/worktrees/<session-id>` (defaulting to `~/.local/state/aops/worktrees/<session-id>`).
- **AC-2.2** Given session telemetry, OpenTelemetry buffers, and local state trackers, when writing state, then state files reside under `$XDG_STATE_HOME/aops/` (defaulting to `~/.local/state/aops/`).

### US-3 Centralized Configuration and Runtime IPC

As a system operator, I want machine-specific environment configurations and runtime lockfiles placed according to standard OS conventions, so that secrets and overrides are easy to locate and IPC files clean up on reboot.

- **AC-3.1** Given machine-local configuration overrides or launch daemon environment scripts, when resolving config files, then they are read from `$XDG_CONFIG_HOME/aops/` (defaulting to `~/.config/aops/`).
- **AC-3.2** Given ephemeral IPC pointers, lockfiles, or premise check verification files, when allocated at runtime, then they reside in `$XDG_RUNTIME_DIR/aops/` (defaulting to `/tmp/aops-$UID/`).

## Design

### 1. Directory Taxonomy & Roles

| Directory Role | Standard Environment Variable | Standard Fallback Path | Contents & Lifecycle |
| :- | :- | :- | :- |
| **Cache** | `$XDG_CACHE_HOME/aops` | `~/.cache/aops` | Recomputable model weights, tokenizer data, runtime binaries. Safe to wipe at any time. |
| **State** | `$XDG_STATE_HOME/aops` | `~/.local/state/aops` | Machine-local persistent state: OTel traces, lockfiles, automode state, and active worker worktrees (`worktrees/<session-id>`). |
| **Config** | `$XDG_CONFIG_HOME/aops` | `~/.config/aops` | Machine-specific environment overrides, project path mappings, launchd forwarders. |
| **Runtime / IPC** | `$XDG_RUNTIME_DIR/aops` | `/tmp/aops-$UID` | Ephemeral inter-process communication, premise gate state, session pointers. Purged on reboot. |

### 2. Migration and Backward Compatibility

1. **Resolution Shim**: A centralized path helper resolves directories in order: explicit environment variable (`XDG_*`), followed by legacy environment variable (`POLECAT_HOME` or `AOPS_CACHE` if set), followed by standard XDG fallback.
2. **Graceful Fallback**: If legacy configurations exist under `~/.aops`, components read from `~/.aops` with a deprecation notice before migrating contents to `~/.config/aops` and `~/.local/state/aops`.
