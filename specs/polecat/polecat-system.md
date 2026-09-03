---
id: polecat-system
title: "Polecat System: Ephemeral Agent Containers"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, architecture]
---

# Polecat System: Ephemeral Agent Containers via Docker Sandboxes (`sbx`)

Polecat runs an agent CLI invocation inside an isolated Docker Sandbox (`sbx`),
using tailored kits for `claude` and `agy`. This allows the agent to run inside an
isolated microVM container with its own kernel, filesystem, and host-proxied credentials,
while seamlessly operating directly on the local workspace as if running locally.

It is a single command — `polecat run` — not a task-claiming service: task lifecycle
(claim, work, record, hand over) is the invoked agent's own job, driven by a seeded
`/pull <task-id>` prompt and the `pull` skill running inside the sandbox.

## Giving Effect

- [[lib/polecat/cli.py]] — the CLI: one Click command, `run`, invoking `docker sbx run`
- [[lib/polecat/kits/claude/spec.yaml]] — Docker Sandbox kit for Claude Code (`extends: claude`)
- [[lib/polecat/kits/agy/spec.yaml]] — Docker Sandbox kit for Google Antigravity CLI (`agy`)
- [[lib/polecat/env_contract.py]] — forwarded environment variable contract
- [[Dockerfile]] — lightweight sandbox container base
- [[plugins/aops/skills/polecat/SKILL.md]] — coordinator launcher skill

## What `run` does

1. Resolves the workspace: `--repo-dir` or `--workspace` mounts the host path directly
   into the sandbox; `--project` resolves canonical project aliases from `polecat.yaml`
   and maps host paths from `<polecat_home>/local.yaml`. Defaults to current working directory.
2. Resolves the agent kit: selects the appropriate kit (`lib/polecat/kits/claude` or
   `lib/polecat/kits/agy`, or user-specified `--kit`).
3. Forwards environment and credentials: forwards variables defined in `FORWARDED_ENV`
   and OpenTelemetry telemetry configurations via `-e` into the sandbox.
4. Executes native Docker Sandbox: executes `docker sbx run` (or `sbx run`) pointing to
   the kit, workspace directory, and agent CLI with appropriate flags (e.g. `--print` for
   headless seeded execution or interactive TTY).
5. Writes `run.json`: records session execution status, exit code, and timestamps.

## Guarantees

1. **Isolation.** Every `run` executes inside a dedicated Docker Sandbox microVM (`sbx`),
   with its own kernel, network rules, and container filesystem isolated from the host.
2. **Seamless local operation.** The host repository or specified workspace directory is
   mounted directly into the sandbox. Files edited by the agent are reflected directly
   on the local workspace without throwaway worktrees, git cloning, or remote pushes.
3. **Credential scoping.** Secrets and API tokens are mediated via Docker Sandboxes'
   built-in credentials proxy or explicitly forwarded environment variables (`FORWARDED_ENV`).
4. **Declarative Kits.** Agent environments are packaged as Docker Sandbox kits
   (`lib/polecat/kits/claude` and `lib/polecat/kits/agy`) specifying network allowlists,
   runtime dependencies, and auto-approved tool execution flags (`--dangerously-skip-permissions`).
5. **Stream separation.** Polecat's own prose — progress, banners, `fail()` — goes
   to stderr, never stdout, so a caller can pipe the inner agent's output unmodified.
   `--quiet`/`-q` suppresses polecat's stderr progress prose.
