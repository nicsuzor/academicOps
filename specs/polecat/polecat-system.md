---
id: polecat-system
title: "Polecat System: Ephemeral Agent Containers"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, architecture]
---

# Polecat System: Ephemeral Agent Containers

Polecat runs one agent CLI invocation inside an isolated Docker container, on an
isolated git clone, so dispatched work never touches the caller's own checkout or
host credentials. It is a single command — `polecat run` — not a task-claiming
service: task lifecycle (claim, work, record, hand over) is the invoked agent's own
job, driven by a seeded `/pull <task-id>` prompt and the `pull` skill running inside
the container.

## Giving Effect

- [[plugins/aops/polecat/cli.py]] — the entire CLI: one Click command, `run`
- [[plugins/aops/polecat/entrypoint.sh]] — container entrypoint: sets git identity,
  installs a token-based credential helper, merges staged per-session config over
  the image defaults, then execs the agent CLI
- [[plugins/aops/polecat/defaults/]] — baked container defaults (`claude-settings.json`,
  `claude-config.json`, `ccstatusline-settings.json`, `agy-onboarding.json`,
  `docker_gemini_fixups.py`)
- [[Dockerfile]] — the image `run` executes inside
- [[plugins/aops/skills/pull/SKILL.md]] — worker-side: claim, execute, record, hand
  over — what a seeded `/pull <task-id>` prompt actually does once inside the
  container
- [[plugins/aops/skills/dispatch/SKILL.md]] — coordinator-side: the mandatory
  pathway to a polecat container; a raw `polecat run` outside this skill bypasses
  the dispatch contract
- [[.agents/skills/debug/SKILL.md]] — the operational skill for driving a
  `polecat run` container interactively via tmux (see
  [[tmux-interactive-driving]])

## What `run` does

1. Resolves `POLECAT_HOME` (cache root) and the container image reference — both
   required, from the environment or the operator's polecat config file; no
   default.
2. Resolves the workspace: `--repo-dir` mounts a host path exactly as given
   (caller owns isolation); `--project` looks the project up in
   `<polecat_home>/local.yaml`'s `paths` map.
3. Unless `--repo-dir` was given, clones the resolved repo (`git clone --local
   --no-checkout`) into `$POLECAT_HOME/worktrees/<session-id>`, checks out
   `polecat/<session-id>` at the host repo's current `HEAD`, and repoints `origin`
   at the host repo's own remote — so a push from inside the container reaches the
   real remote and nothing the container does is visible in the host checkout
   until pushed. This clone is deleted again when `run` exits, success or failure.
4. Stages a per-session credential/settings directory (`pluginConfigs.pkb_mcp_url`,
   an optional worker model override, and — when `POLECAT_AGENT_HOME` is set — a
   secret-stripped copy of the agy/Gemini CLI's own auth files) and mounts it
   read-only at `/tmp/staging`; `entrypoint.sh` merges it into `$HOME` inside the
   container.
5. Forwards a fixed environment allowlist (PKB MCP URL/token, git author/committer
   identity, `CI`/`NONINTERACTIVE`, the OpenTelemetry contract, the Claude OAuth
   token, the bot GitHub token) and denies every other git credential path
   (`GIT_ASKPASS=true`, empty `SSH_AUTH_SOCK`, `GIT_SSH_COMMAND=false`,
   `GIT_TERMINAL_PROMPT=0`) — auth resolves from the forwarded token or not at all.
6. Runs `docker run --rm --pull=never` as the invoking host UID, with the
   workspace mounted at `/workspace`, the staging dir read-only, and the session
   log directory bind-mounted straight into the agent's own session-state path so
   logs and transcripts are visible on the host live, not just at container exit.
   The image is never pulled from a registry — it must already be built locally
   or CI-produced; a missing image is a hard failure with an actionable message.
7. Builds the inner command from `AGENT_CMD` (`claude`, `agy`, `shell`/`bash`,
   `sleep`, or any other passthrough binary). With `--task <id>` and no explicit
   prompt, seeds `/pull <id>` as the prompt. An `agy` dispatch with no explicit
   interactive/prompt flag runs headless (`--print`) with an optional
   `--print-timeout` so the container exits when the agent's loop completes,
   rather than idling forever.
8. On completion, verifies delivery before reporting success: for a seeded `agy`
   dispatch, the agent's own transcript must reference the task id (retried once
   if not, then a hard failure — a clean exit is not evidence the seed was ever
   delivered); the workspace must have no uncommitted changes, and if `HEAD`
   moved, the new commit must be present on the remote. A delivery-guard failure
   on a task that the PKB now shows in a terminal status (`done`, `completed`,
   `complete`, `merge_ready`) reverts it to `in_progress` rather than letting a
   silent loss stand as a recorded success.

## Guarantees

1. **Isolation.** Every `run` without `--repo-dir` works on its own throwaway
   clone, torn down when the invocation ends; nothing an agent does is visible in
   the host checkout until it pushes to the real remote.
2. **Credential scoping.** The container never receives the host's SSH agent,
   ambient git credential helpers, or the host's own `~/.claude`/`~/.gemini`
   config — only the forwarded env allowlist and the staged, secret-stripped
   settings.
3. **No silent delivery loss.** `run` refuses to report success when the
   workspace has uncommitted or unpushed work, or when a seeded dispatch's
   transcript shows no trace of the task it was given.
4. **No registry drift.** `run` never pulls the image; it fails loudly if the
   named image isn't already present locally.

## What `run` does not do

There is no `start`, `finish`, `crew`, `nuke`, `swarm`, `list`, `init`, or `sync`
subcommand, no bare-mirror registry under a `.repos/` directory, no workspace that
survives past a single invocation, and no claiming, PR-filing, or status-setting
performed by the CLI itself. Those either don't exist or are the invoked agent's
own job, driven by the `pull` skill against the PKB task graph from inside the
container.

## User Expectations

1. **Workspace isolation** — Test: files changed inside a `run` invocation (no
   `--repo-dir`) are not visible in the registered host checkout, before or after
   the run.
2. **Credential denial** — Test: inside the container, `ssh -T git@github.com` and
   any git operation not using the forwarded token fail; only the forwarded token
   authenticates.
3. **Delivery guard** — Test: a `run` that leaves uncommitted changes, or commits
   that never reach the remote, exits non-zero and (with `--task`) reverts a
   terminal-status task back to `in_progress`.
4. **No stale image** — Test: `run` against an image not present in the local
   Docker cache fails with an explicit message, never a silent registry pull.
5. **Branch naming** — Test: an isolated clone's branch is `polecat/<session-id>`.
