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
- **AC-3.2** Given ephemeral IPC pointers, lockfiles, or premise check verification files, when allocated at runtime on Linux, then they reside in `$XDG_RUNTIME_DIR/aops/` (defaulting to `/tmp/aops-$UID/`).

### US-4 Environment Compatibility and Operational Safety

As a system operator or worker, I want path resolution to preserve active sessions, support macOS launchd environments, and operate within container VM mount boundaries, so that migration does not disrupt running processes or break container filesystem access.

- **AC-4.1** Given in-flight sessions or existing worker worktrees, when path resolution updates, then existing sessions continue to read their allocated directories without in-flight file moves or session interruption.
- **AC-4.2** Given a macOS launchd environment where standard XDG variables are unset, when launchd forwarders execute, then configuration scripts probe `$XDG_CONFIG_HOME/aops/launchd-env.sh` (defaulting to `~/.config/aops/launchd-env.sh`) with fallback to `~/.aops/launchd-env.sh`, and export defined XDG variables into the per-user launchd context.
- **AC-4.3** Given an environment running within or mounting into a VM where only `$HOME` is shared (such as Colima or Docker Desktop on macOS), when allocating runtime or IPC directories and `$XDG_RUNTIME_DIR` is unset, then runtime IPC paths fall back to `$XDG_STATE_HOME/aops/run/` (defaulting to `~/.local/state/aops/run/` with permissions `0700`) inside `$HOME` rather than host `/tmp`.

## Design

### 1. Directory Taxonomy & Roles

| Directory Role | Standard Environment Variable | Standard Fallback Path | Contents & Lifecycle |
| :- | :- | :- | :- |
| **Cache** | `$XDG_CACHE_HOME/aops` | `~/.cache/aops` | Recomputable model weights, tokenizer data, runtime binaries. Safe to wipe at any time. |
| **State** | `$XDG_STATE_HOME/aops` | `~/.local/state/aops` | Machine-local persistent state: OTel traces, lockfiles, automode state, and active worker worktrees (`worktrees/<session-id>`). |
| **Config** | `$XDG_CONFIG_HOME/aops` | `~/.config/aops` | Machine-specific environment overrides, project path mappings, launchd forwarders. |
| **Runtime / IPC** | `$XDG_RUNTIME_DIR/aops` | Linux: `/run/user/$UID/aops` or `/tmp/aops-$UID`<br>macOS/VM: `~/.local/state/aops/run` (mode `0700`) | Ephemeral inter-process communication, premise gate state, session pointers. Purged on reboot or session teardown. |

### 2. Path Resolution and Backward Compatibility

Path resolution follows a strict priority order:

1. Explicit standard environment variable (`XDG_CACHE_HOME`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR`).
2. Legacy environment variable (`POLECAT_HOME` or `AOPS_CACHE`) if set in the calling environment.
3. Standard XDG fallback path (e.g., `~/.cache/aops`, `~/.local/state/aops`, `~/.config/aops`).
4. Read-only legacy fallback: if a configuration or data file is absent from the standard XDG path but present under `~/.aops`, components read from `~/.aops`. To prevent data corruption and race conditions during active operations, existing files are not moved automatically at runtime.

### 3. Operational Risk Mitigations

#### Active Sessions

Active sessions and worker worktrees running in legacy paths (e.g. `$POLECAT_HOME/worktrees/<session-id>`) remain untouched until completion. New sessions allocate strictly under `$XDG_STATE_HOME/aops/worktrees/<session-id>`. Path resolution avoids background filesystem mutations or locking locks while sessions are active.

#### macOS launchd Compatibility

On macOS, launchd daemons and GUI-launched applications run without shell environment initialization and have no XDG variables defined by default.

- The LaunchAgent configuration probes `${XDG_CONFIG_HOME:-$HOME/.config}/aops/launchd-env.sh` first, falling back to `${POLECAT_HOME:-$HOME/.aops}/launchd-env.sh`.
- The environment script explicitly exports `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_STATE_HOME`, and `XDG_RUNTIME_DIR` via `launchctl setenv` whenever defined, making standard paths available to all per-user GUI applications.

#### Colima and VM Bind Mount Boundaries

In virtualized container setups on macOS (Colima, Docker Desktop), only `$HOME` is mounted into the virtual machine by default (`mounts: []`). Host paths in `/tmp` (or `/private/tmp`) are not reachable within the VM; mounting them produces empty, root-owned directories that fail silently.

- On macOS, or whenever `$XDG_RUNTIME_DIR` is not supplied by the operating system, the runtime and IPC fallback path defaults to `$XDG_STATE_HOME/aops/run` (`~/.local/state/aops/run/` with permissions `0700`).
- Because `$XDG_STATE_HOME` defaults to a subdirectory of `$HOME`, all container bind mounts for runtime sockets, IPC files, and session workspaces remain within the VM's shared filesystem boundary.
