---
name: dispatch
description: Coordinator-side pathway to a worker surface — a supervised in-session team or an isolated polecat container. The mandatory route to `polecat run`; a raw invocation outside this skill bypasses the delivery-guard and image-freshness obligations below.
agent: "ida:james"
---

# Dispatch

Route one unit of work to the surface that fits it, and hold the obligations that surface carries until the work actually lands. A worker's own "done" is never the verdict — see `strategic-review`.

## 1. Choose the surface

- **Supervised in-session team** — small or tightly coupled work you want to watch and correct turn by turn. Spawn subagents directly; you stay in the loop.
- **Polecat container** — anything substantial, anything with real sub-structure, or anything that should proceed unattended. Fire and forget: don't poll a container session, don't narrate that one is running.

A polecat container is the only path that gives a worker its own isolated clone, its own credentials, and a delivery guard that catches silent loss. Route there by default once a task clears "small enough to babysit."

## 2. Resolve the workspace and the task

- `--task <id>` seeds `/pull <id>` as the container's first prompt — the claimed task is the container's entire brief; do not also paste the brief inline.
- `--project <name>` resolves through `$POLECAT_HOME/local.yaml`'s `paths` map; use `--repo-dir <path>` for a host path not registered there. Never point either at a linked git worktree — its `.git` is a file pointing outside the mounted directory, and every git command inside the container fails.
- `AGENT_CMD` is `claude` or `agy`. Prefer `agy` where cost matters and the task doesn't need Claude specifically.

## 3. Image freshness — before any dispatch you intend to certify

`lib/polecat/cli.py` never pulls or rebuilds the image; it runs whatever `$POLECAT_IMAGE` already names, built from whatever `dist/` happened to exist when someone last ran `make docker-build`. `dist/` is built from the working tree, not `HEAD` — a committed change is invisible to the next container until both a clean tree and a fresh build back it.

Before a dispatch whose result you plan to certify against a change to `plugins/`, `lib/`, the Dockerfile, or shipped skills/agents/commands: confirm the tree you built from is the tree you mean to certify (clean, the change committed), then run `make docker-build`. Use `make verify-docker` (`--no-cache`) rather than `make docker-build` before the certifying run of a release-bound change — a cached layer can carry the previous plugin set into an image that looks rebuilt. Skip this step only for a dispatch you are not going to treat as evidence of anything (a routine work unit against an unchanged image).

## 4. Launch

Invoke `${CLAUDE_PLUGIN_ROOT}/polecat/cli.py run` directly — this is the one supported entry point; there is no `start`/`crew`/`swarm` alternative. For live, interactive driving (debugging a container rather than dispatching real work), use the `debug` skill instead — it wraps the same `run` command under tmux.

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/polecat/cli.py" \
  run agy --project <name> --task <task-id>
```

Required environment (`POLECAT_HOME`, `POLECAT_IMAGE`, git author identity, the bot GitHub token, and — for `agy` — `POLECAT_AGENT_HOME`) has no defaults; `cli.py` fails loudly naming whichever is missing rather than guessing. See `plugins/ida/README.md` ("Configuration") for the full list.

## 5. Read the result

`run` itself already refuses to report success when the workspace has uncommitted or unpushed work, or when a seeded dispatch's transcript shows no trace of the task it was given (`specs/polecat/polecat-system.md`, "Guarantees"). A non-zero exit from `run` means the delivery guard caught something — treat its named failure as the report, not as an error to route around.

A zero exit is not itself the verdict: it means delivery landed, not that the work is good. Run `strategic-review` before writing `done` onto the task record.

## 6. On a delivery-guard failure

`run` detects a lost delivery; it does not repair it. If a worker already wrote `done` or `partial` onto the task before its commit or push was lost, that status is left standing until you act on it — the CLI holds no client for the PKB's tool namespace and cannot write there itself.

On any non-zero exit from a dispatch that carried `--task <id>`: commission `pkb:pauli` to reopen that task (back to `queued`), naming the failure `run` reported. Do this before anything else reads the task's status as final. A caught delivery loss that is never reopened is indistinguishable, downstream, from one that never happened.
