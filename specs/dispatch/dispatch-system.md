---
id: dispatch-system
title: "Dispatch: Isolated Workers in Docker Sandboxes"
type: spec
status: ready
tier: dispatch
depends_on: []
tags: [spec, dispatch, sandbox, architecture]
---

# Dispatch: Isolated Workers in Docker Sandboxes (`sbx`)

Dispatch puts one worker on one task inside one Docker Sandbox with its own git
clone. The mechanism is Docker's `sbx` command itself. The framework ships no
launcher, no wrapper, and no baked image: what it ships is a pair of kits and the
skill that composes the `sbx` invocation from them.

Task lifecycle -- claim, work, record, hand over -- is the dispatched agent's own
job, driven by a seeded `/aops:pull <task-id>` prompt and the `pull` skill
running inside the sandbox.

## Giving effect

- [[plugins/aops/skills/dispatch/SKILL.md]] -- the operative mechanics: create,
  wait, seed, collect
- [[plugins/aops/agents/sara.md]] -- the dispatcher: branch, sequence, wave, merge
- [[lib/kits/agy/spec.yaml]] -- the sandbox kit supplying the `agy` client
- [[lib/kits/claude/spec.yaml]] -- the sandbox kit supplying the `claude` client
- [[lib/kits/aops/spec.yaml]] -- the mixin kit that builds and installs the
  framework from the sandbox's own clone
- [[lib/polecat/env_contract.py]] -- the forwarded environment variable contract

## The invocation

```bash
sbx create --clone --name <name> -e PKB_MCP_URL --kit lib/kits/agy --kit lib/kits/aops agy .
```

Kits and forwarded environment variables are the only configuration. No images,
no docker flags, no host paths, and no credentials are passed on the command line.

Kits merge: one kit of `kind: sandbox` supplies the client, its network
allowlist, and its credential contract; `lib/kits/aops` is a `kind: mixin` that
adds the framework's own install and startup steps on top. Both are required --
the client kit alone yields a sandbox with no framework in it.

## The clone

`--clone` gives the container a private git clone at the same path as the host
repository (`$WORKSPACE_DIR`), and mounts the host repository read-only at
`/run/sandbox/source`. `--branch` is not accepted: `sbx` rejects it with
`ERROR: --branch is no longer supported; use --clone instead`.

**The clone carries only committed work.** The container cannot see the host's
working tree. Anything the worker must see -- a task file, a kit, a Makefile
target, a plugin change -- is committed and pushed to the dispatch branch before
the sandbox is created, or it does not exist inside the sandbox.

Every epic gets one branch and every worker for that epic clones from it. Sara
commits and pushes to that branch again between waves, so each wave starts from
the merged results of the last.

## Collection

Creating a sandbox creates a host git remote named `sandbox-<name>`, backed by a
git daemon serving the container's clone. The container's commits reach the host
through it, arriving under `refs/sandboxes/<name>/`:

```bash
git fetch "sandbox-$NAME"
sbx rm -f "$NAME"
```

Fetch before removing. `sbx rm -f` destroys the clone and the daemon serving it,
and uncollected commits go with them.

## Startup is asynchronous

`sbx create` returns once the sandbox exists, while the `aops` kit's startup
command (`make install-agy`, run in `$WORKSPACE_DIR`) is still building the
plugin set from the clone and installing it for the client. Until it finishes the
worker cannot resolve `/aops:pull`.

Progress is written to `/var/log/sbx-kit-startup.log`. Success ends
`=== dispatcher complete ===`; failure logs a line naming
`fail /etc/durable-startup`. Dispatch waits on that log with a bounded loop and
an explicit timeout, and a `fail` line or a timeout is a halt: a sandbox whose
framework did not install is never seeded.

## Guarantees

1. **Isolation.** Every dispatch runs inside a dedicated Docker Sandbox with its
   own kernel, network rules, and filesystem, isolated from the host.
2. **The host tree is never written.** The host repository is mounted read-only;
   the worker edits its own clone and delivers over git.
3. **Delivery is by commit.** Work that is not committed inside the sandbox does
   not survive the sandbox.
4. **Credential scoping.** Secrets reach the container through the sandbox
   credentials proxy or the forwarded environment contract, never as flags.
5. **Declarative environments.** Network allowlists, runtime dependencies, and
   the client's auto-approval flags live in the kits, versioned with the
   repository.

## Open defect: agy cannot authenticate in the sandbox

A dispatched `agy -p "..."` fails with
`Error: authentication required. Run 'agy' to log in, then retry.` Docker's
documentation states that proxy-managed OAuth is unsupported for third-party
sandbox agents, so the OAuth sentinels in `lib/kits/agy/spec.yaml` do not resolve
to a usable session inside the container.

This blocks automated `agy` dispatch. The kit stays as it is; Nic holds this one.
