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

This file is the umbrella. The individual designs are
[base-ref resolution](spec-base-ref-resolution.md),
[image staleness detection](spec-image-staleness-detection.md),
[partial-work delivery](spec-partial-work-tight-loop-delivery.md), and
[interactive tmux driving](tmux-interactive-driving.md).

## Giving Effect

- [[lib/polecat/cli.py]] — the entire CLI: one Click command, `run`
- [[lib/polecat/entrypoint.sh]] — container entrypoint: sets git identity,
  installs a token-based credential helper, merges staged per-session config over
  the image defaults, then execs the agent CLI
- [[lib/polecat/staleness.py]] — image provenance and staleness evaluation
- [[lib/polecat/env_contract.py]] — the forwarded/container-set environment contract
- [[lib/polecat/defaults/]] — baked container defaults (`claude-config.json`,
  `agy-settings.json`, `agy-onboarding.json`, `ccstatusline-settings.json`,
  `agystatusline-settings.json`, `docker_gemini_fixups.py`)
- [[Dockerfile]] — the image `run` executes inside
- [[plugins/aops/skills/pull/SKILL.md]] — worker-side: claim, execute, record, hand
  over — what a seeded `/pull <task-id>` prompt actually does once inside the
  container
- [[plugins/orchestrate/agents/pc.md]] — coordinator-side: the launcher agent that builds
  the `polecat run` command and runs it synchronously (or wrapped under tmux), locally
  or over ssh. It is one route in, not a gate: `run`'s own guarantees hold on any
  invocation, and nothing stops a caller reaching the CLI directly
- [[.agents/skills/debug/SKILL.md]] — the operational skill for driving a
  `polecat run` container interactively via tmux

## What `run` does

1. Resolves `POLECAT_HOME` (cache root) and the container image reference — both
   required, from the environment or the operator's polecat config file; no
   default.
2. Resolves the workspace: `--repo-dir` mounts a host path exactly as given
   (caller owns isolation); `--project` looks the project up in
   `<polecat_home>/local.yaml`'s `paths` map.
3. Unless `--repo-dir` was given, clones the resolved repo (`git clone --local
   --no-checkout`) into `$POLECAT_HOME/worktrees/<session-id>`, checks out
   `polecat/<session-id>` at the base commit, and repoints `origin` at the host
   repo's own remote — so a push from inside the container reaches the real
   remote and nothing the container does is visible in the host checkout until
   pushed. This clone is deleted again when `run` exits, success or failure.
   Base commit selection, and its remote-freshness rule, are
   [spec-base-ref-resolution.md](spec-base-ref-resolution.md).
4. Stages a per-session credential/settings directory (`pluginConfigs.pkb_mcp_url`,
   an optional worker model override, and — when `GEMINI_CONFIG_DIR` is set — a
   secret-stripped copy of the agy/Gemini CLI's own auth files) and mounts it
   read-only at `/tmp/staging`; `entrypoint.sh` merges it into `$HOME` inside the
   container.
5. Forwards a fixed environment allowlist (PKB MCP URL/token, git author/committer
   identity, `CI`/`NONINTERACTIVE`, the OpenTelemetry contract, the Claude OAuth
   token, the bot GitHub token) and denies every other git credential path
   (`GIT_ASKPASS=true`, empty `SSH_AUTH_SOCK`, `GIT_SSH_COMMAND=false`,
   `GIT_TERMINAL_PROMPT=0`) — auth resolves from the forwarded token or not at all.
   cope's evaluator (`COPE_EVALUATOR_URL/PROTOCOL/MODEL/API_KEY/TIMEOUT`) is
   forwarded the same way, with one configured fallback: an unset host variable
   falls back to the operator's polecat config file's own `cope:` block
   (`resolve_cope_evaluator`) rather than depending only on what happened to be
   exported in the invoking shell. Absent both, cope runs unconfigured in the
   container — a legitimate no-op, not a fault. Every one of these names is
   passed as a valueless `docker run -e NAME`, with the value supplied through
   the `docker` process's own environment, because argv is world-readable in the
   host process table for the life of the container: a value on the command line
   is a value published to every local process. Only `CONTAINER_SET_ENV` — the
   container-internal paths and flags, never a credential — carries its value
   on argv.
6. Evaluates image staleness and emits the provenance banner
   ([spec-image-staleness-detection.md](spec-image-staleness-detection.md)).
7. Runs `docker run --rm --pull=never` as the invoking host UID, with the
   workspace mounted at `/workspace`, the staging dir read-only, and the session
   log directory bind-mounted straight into the agent's own session-state path so
   logs and transcripts are visible on the host live, not just at container exit.
   When the operator's config names a `rules_dir` (or `$POLECAT_RULES_DIR` is
   set), that host directory is mounted read-only at the container's own
   `$ACA_DATA/.agents/rules/` (`/data/.agents/rules` — `ENV ACA_DATA=/data` in
   the `Dockerfile`), which is what makes cope/rbg's layer 3 reach a container;
   absent, the container simply has no layer 3, and a configured-but-unreadable
   directory is a hard failure before any container starts. The image is never
   pulled from a registry — it must already be built locally or CI-produced; a
   missing image is a hard failure with an actionable message.
8. Builds the inner command from `AGENT_CMD` (`claude`, `agy`, `shell`/`bash`,
   `sleep`, or any other passthrough binary). With `--task <id>` and no explicit
   prompt, seeds `/pull <id>` as the prompt. An `agy` dispatch with no explicit
   interactive/prompt flag runs headless (`--print`) with an optional
   `--print-timeout` so the container exits when the agent's loop completes,
   rather than idling forever. `polecat.yaml`'s `timeout` supplies that value on
   _every_ headless dispatch.
9. On completion, verifies delivery before reporting success (Guarantee 3), then
   writes `run.json`.

## Guarantees

1. **Isolation.** Every `run` without `--repo-dir` works on its own throwaway
   clone, torn down when the invocation ends; nothing an agent does is visible in
   the host checkout until it pushes to the real remote.
2. **Credential scoping.** The container never receives the host's SSH agent,
   ambient git credential helpers, or the host's own `~/.claude`/`~/.gemini`
   config — only the forwarded env allowlist and the staged, secret-stripped
   settings.
3. **No silent delivery loss.** `run` refuses to report success when the
   workspace has uncommitted work, when `HEAD` moved but the new commit is not
   present on the remote (matching a remote ref tip, or reachable on a remote
   branch after fetch), or when a seeded dispatch's transcript shows no trace of
   the task it was given.

   The transcript check exists because a dropped seed and a completed task look
   identical from outside: if the prompt never reached the agent the container
   still exits zero with an unchanged workspace — exactly the shape the workspace
   check accepts as a legitimate no-op. So for a seeded `agy` dispatch (`--task
   <id>`, no explicit prompt) `run` scans the session's transcripts and logs for
   the task id, retries the whole dispatch once if absent, and on a second miss
   fails loudly naming the task and the session directory.

   Detection is only half of it. A worker that already wrote `done` leaves that
   status behind, and `run` cannot repair it without holding a client for another
   plugin's tool namespace. The repair is the dispatcher's — it reopens the task
   through pauli on a non-zero exit for a `done` or `partial` unit. Nothing
   enforces that half; `run`'s own failure text names it ("the dispatcher must
   reopen it (via pauli) before filing a fix subtask or re-dispatching"), and no
   agent or skill body carries it.
4. **No registry drift.** `run` never pulls the image; it fails loudly if the
   named image isn't already present locally.
5. **One plugin path.** Plugins load only from the image's own plugin cache. No
   mount registers a marketplace, so plugin code reaches an agent only by being
   built into the image. The converse does not hold and is not claimed — see
   Guarantee 6.
6. **Instruction state does not share that path.** Project skills, `CLAUDE.md`,
   and cope's project rule layer reach the agent from the mounted workspace, and
   `rules_dir` mounts a host rule directory — none of it through the image, and
   the workspace clone tracks the host repo's `HEAD`. So a committed change to
   host-side instruction files is live in the next `run` with no rebuild. A
   certifying run therefore needs both a clean committed tree and a fresh
   `make docker-build`, which builds `dist/` from the working tree rather than
   from `HEAD`. Nothing on the launch path enforces either; the staleness
   detector warns, and the obligation to act on the warning is carried
   project-locally by [`debug`](../../.agents/skills/debug/SKILL.md) — build the
   image, then dispatch against it — and by no shipped surface.
7. **Stream separation.** Polecat's own prose — progress, banners, `fail()` — goes
   to stderr, never stdout, so a caller can pipe the inner agent's output
   unmodified. `--quiet`/`-q` suppresses polecat's stderr progress prose,
   including the `Workspace:` and `Session logs:` lines that locate a run's state.
   `fail()` output is exempt, because an exit code alone is not a reliable failure
   signal here — agy can exit 0 on internal error — so error text must survive
   `--quiet`. The `Workspace:`/`Session logs:`/`Running:` lines are the evidence
   [`debug`](../../.agents/skills/debug/SKILL.md) requires a run to report, so
   `--quiet` and that skill are mutually exclusive by construction: the flag is off
   by default and no debug procedure passes it.
8. **Plain-text stdout contract, opt-in stream-json.** Headless dispatches default
   to plain text on stdout, not a JSON event stream. `--output-format stream-json`
   is the explicit opt-in (`claude` accompanied by `--verbose` as the CLI requires;
   `agy` using native `--output-format stream-json`). Exactly one output stream
   reaches stdout per invocation: on the seed-verification retry path, aborted
   attempt output is buffered and suppressed so callers never receive
   concatenated streams.

## What `run` does not do

There is no detached container mode — detaching is the wrapping tmux session's
job; `polecat run` is strictly a single synchronous script returning results on
stdout, quiet by default. There is no `start`, `finish`, `crew`, `nuke`, `swarm`,
`list`, `init`, or `sync` subcommand, no bare-mirror registry under a `.repos/`
directory, no workspace that survives past a single invocation, and no claiming,
PR-filing, or status-setting performed by the CLI itself. Those either don't exist
or are the invoked agent's own job, driven by the `pull` skill against the PKB
task graph from inside the container.
