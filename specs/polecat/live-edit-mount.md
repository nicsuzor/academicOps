---
id: polecat-live-edit-mount
title: "Polecat --live-edit: Mounting Plugin Source Without an Image Rebuild"
type: spec
status: ready
tier: polecat
depends_on: [polecat-system]
tags: [spec, polecat, docker, dev-loop]
---

# Polecat `--live-edit`: Mounting Plugin Source Without an Image Rebuild

`polecat run`'s `--live-edit` flag bind-mounts a workspace's locally built
`dist/` read-only over the container's installed-plugin cache, so an edit to
plugin source (`lib/`, `plugins/*/hooks`, `skills`, `commands`, `agents`)
takes effect on the next `run` with no `make docker-build`. Opt-in only —
without the flag, `run`'s behavior is unchanged and the container serves
whatever was baked in at image-build time (see [[polecat-system]] for what
`run` does end to end).

## Giving Effect

- [[plugins/aops/polecat/cli.py]] — `sanitize_cache_version`,
  `resolve_live_edit_mounts`, `verify_live_edit_destinations`, and the
  `--live-edit` option on `run`
- [[tests/polecat/test_live_edit_mount.py]] — the sanitization rule, the `-v`
  mount present when enabled and absent when disabled, and the loud failure
  on a bogus destination
- [[Dockerfile]] — `MP_NAME=academicOps`, the fixed marketplace name every
  image installs its plugins under, and the plugin-install `RUN` block that
  creates `/home/worker/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`
- [[build/marketplace.py]] — `generate_local_marketplace`, which deliberately
  names the local dist marketplace `aops`, never `academicOps`

## Why a mount here is dangerous by default

Claude Code's plugin installer writes each plugin's cache directory as
`cache/<marketplace>/<plugin>/<version>`, rewriting any `+` in the version to
`-` first. Confirmed live in a container: a plugin built at source version
`0.5.0+gdff86d32` installs at
`/home/worker/.claude/plugins/cache/academicOps/aops/0.5.0-gdff86d32/`, not
at a path containing the literal `+`.

Docker does not error when a bind-mount destination does not already exist —
it silently creates an empty directory and mounts over it. A mount computed
from the raw, un-sanitized version (or from any other wrong path: a stale
image, a plugin the image never installed) therefore lands somewhere nothing
in the image reads. The container starts cleanly, the agent runs normally,
and it silently executes the image's baked-in code instead of the host's
edited source — with no error anywhere. This is a false-green failure: a
review or test run against the container reports on stale code while
appearing to have exercised the edit.

## Mechanism

1. **Source of truth: the local build manifest, not live git state.**
   `resolve_live_edit_mounts(workspace_dir)` reads
   `dist/.claude-plugin/marketplace.json` — the exact file `make build`
   produced and `make docker-build` (`AOPS_DIST_SOURCE=local`) `COPY`'d into
   the image (see the Dockerfile's `aops-dist-local` stage). For each
   declared plugin it takes the `name` and `version` already recorded there.

   This is deliberate: a live-edit session's entire purpose is to dirty the
   workspace _after_ the image was built. `build/version.py`'s version
   derivation (`get_current_version`) depends on dirty-vs-clean git state, so
   recomputing a version from the workspace's current git state at `run`
   time would drift the moment the developer starts editing — reintroducing
   exactly the wrong-path failure mode above, just via a different route.
   Reading the manifest instead means the computed destination always
   matches what was actually baked into the currently-running image,
   regardless of how dirty the workspace has since become.

2. **Sanitize before computing the destination.**
   `sanitize_cache_version(version)` replaces every `+` with `-`, matching
   the installer's own rewrite. The destination is
   `/home/worker/.claude/plugins/cache/{CONTAINER_PLUGIN_MARKETPLACE}/{name}/{sanitized_version}`,
   where `CONTAINER_PLUGIN_MARKETPLACE = "academicOps"` is a fixed constant —
   not read from the local manifest's own `name` field, which is
   deliberately `"aops"` (`build/marketplace.py`,
   `generate_local_marketplace`) so a host `make install-dev` never collides
   with a real `academicOps` install on the same machine. The Dockerfile
   installs every image under `academicOps` regardless of build source
   (`MP_NAME=academicOps`, unconditional), so the container-side marketplace
   name is a fact about the image's filesystem, not a host value — the same
   category as `CONTAINER_ACA_DATA` in `cli.py`.

3. **Fail loudly, before any mount, if the source is missing.**
   `resolve_live_edit_mounts` refuses to proceed if `dist/.claude-plugin/
   marketplace.json` doesn't exist (no local build), is unreadable, declares
   no plugins, or names a plugin whose built `dist/<name>-claude` directory
   is absent. Each is a hard failure naming the missing path, not a skipped
   mount.

4. **Fail loudly, before any mount, if the destination is wrong.**
   `verify_live_edit_destinations(image, mounts)` runs a plain
   `docker run --rm --entrypoint sh <image> -c 'test -d <dest1> && test -d
   <dest2> && ...'` — no volumes attached — against every computed
   destination before `run`'s real container ever starts. This is what makes
   a wrong path (sanitization mismatch, stale image, a plugin the image
   never installed) a hard failure instead of Docker's silent
   directory-auto-create. Checking _after_ mounting would only ever observe
   the mount's own target and could never detect this bug.

5. **Mount read-only, once verified.**
   Only after every destination is confirmed to pre-exist does `run` add
   `-v {host dist/<name>-claude}:{container cache path}:ro` for each plugin,
   alongside the workspace/staging/session mounts `run` already builds (see
   [[polecat-system]] step 6). Read-only: a live-edit session edits the host
   checkout, never the container's filesystem.

## Resolution against `--repo-dir` / `--project`

`dist/` is gitignored — a build artifact, never committed — so it exists
only in the canonical checkout `make build` was run against. `run`'s
per-session isolated clone (`resolve_isolated_workspace`, used whenever
`--repo-dir` is not given) is a fresh `git clone --local --no-checkout` and
never has a `dist/` of its own. `--live-edit` therefore resolves mounts
against the workspace path captured _before_ that isolation clone can
replace it — the canonical `--repo-dir` or `--project` path, wherever `make
build` was actually run — not against the ephemeral per-session clone `run`
mounts at `/workspace`.

## User Expectations

1. **Off by default** — Test: `polecat run` with no `--live-edit` produces a
   `docker run` argv with no `-v` targeting
   `/home/worker/.claude/plugins/cache/`, and no preflight probe runs.
2. **Sanitization matches the installer exactly** — Test:
   `sanitize_cache_version("0.5.0+gdff86d32") == "0.5.0-gdff86d32"`.
3. **Enabled produces the expected mount** — Test: with a local `dist/`
   build present, `--live-edit` adds
   `-v <dist>/<name>-claude:/home/worker/.claude/plugins/cache/academicOps/<name>/<sanitized-version>:ro`
   for every plugin the local manifest declares.
4. **A bogus destination is a hard failure, not a silent no-op** — Test: when
   the preflight probe reports a computed destination does not exist in the
   image, `run` exits non-zero before the main container starts, and no
   container from that invocation ever runs.
5. **A host edit is actually visible in the container** — Test: edit a file
   under a plugin's shipped source on the host, rebuild `dist/` (`make
   build`, not `make docker-build`), start a container with `--live-edit`,
   and read the edited string back from the container's own installed-plugin
   cache path. Without `--live-edit`, the same container reads the
   image's original baked-in content.
