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
`dist/` read-only over the plugin directories the image itself reports it
installed, so an edit to plugin source (`lib/`, `plugins/*/hooks`, `skills`,
`commands`, `agents`) takes effect on the next `run` with no
`make docker-build`. Opt-in only — without the flag, `run`'s behavior is
unchanged and the container serves whatever was baked in at image-build time
(see [[polecat-system]] for what `run` does end to end).

## Giving Effect

- [[plugins/aops/polecat/cli.py]] — `probe_image_plugin_roots`,
  `resolve_live_edit_mounts`, `verify_live_edit_destinations`, and the
  `--live-edit` option on `run`
- [[tests/polecat/test_live_edit_mount.py]] — destinations taken from the
  image and never derived host-side, the `-v` mounts present when enabled and
  absent when disabled, and the loud failure on a bogus destination or an
  unreadable image
- [[Dockerfile]] — `MP_NAME=academicOps`, the fixed marketplace name every
  image installs its plugins under; the plugin-install `RUN` block that
  creates `/home/worker/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`
  and copies each `<plugin>-agy` build to
  `/home/worker/.gemini/antigravity-cli/plugins/<plugin>/`
- [[plugins/aops/polecat/defaults/docker_gemini_fixups.py]] —
  `fixup_marketplace_cache`, which rewrites each plugin's `source` in the
  image's marketplace manifest to the absolute cache directory that image
  actually installed

## Why a mount here is dangerous by default

Docker does not error when a bind-mount destination does not already exist —
it silently creates an empty directory and mounts over it. A mount computed
from a wrong path therefore lands somewhere nothing in the image reads. The
container starts cleanly, the agent runs normally, and it silently executes
the image's baked-in code instead of the host's edited source — with no error
anywhere. This is a false-green failure: a review or test run against the
container reports on stale code while appearing to have exercised the edit.

The path is easy to get wrong because Claude Code installs each plugin at
`cache/<marketplace>/<plugin>/<version>`, and `<version>` is the version baked
at **image build** time — not any version the host can compute. Every
host-side derivation of it (recomputing from git state, or reading the host's
own `dist/.claude-plugin/marketplace.json`) is correct only while the image
and the checkout still agree, which is to say only immediately after a
rebuild. That is exactly the condition `--live-edit` exists to escape, so a
host-derived destination defeats the feature in its normal case.

## Mechanism

1. **Source of truth: the image, asked directly.**
   `probe_image_plugin_roots(image)` runs one
   `docker run --rm --entrypoint cat <image>
   /home/worker/.claude/plugins/marketplaces/academicOps/.claude-plugin/marketplace.json`
   — no volumes attached — and reads each plugin's `source`. The Dockerfile
   copies the marketplace manifest to that durable path and then invokes
   `docker_gemini_fixups.py fixup-marketplace-cache`, which rewrites every
   `source` to the absolute cache directory that build installed. It is the
   same file Claude Code itself loads plugins through, so the mount
   destination and the runtime's own resolution cannot disagree, whatever the
   image's age.

   The marketplace name in that path is the fixed constant
   `CONTAINER_PLUGIN_MARKETPLACE = "academicOps"` — never the local dist
   manifest's own `name`, which is deliberately `"aops"`
   (`build/marketplace.py`, `generate_local_marketplace`) so a host
   `make install-dev` never collides with a real `academicOps` install. The
   Dockerfile installs every image under `academicOps` regardless of build
   source (`MP_NAME=academicOps`, unconditional), making the container-side
   marketplace name a fact about the image's filesystem — the same category
   as `CONTAINER_ACA_DATA` in `cli.py`.

2. **The image also fixes the plugin set.**
   `resolve_live_edit_mounts(workspace_dir, image_plugin_roots)` iterates the
   plugins the image reported, not the ones the host built. A plugin the host
   has and the image lacks has no destination to shadow and is not mounted; a
   plugin the image installed but the host has not built is a hard failure,
   because leaving it unmounted would leave it serving baked-in code inside a
   session that believes it is live.

3. **Both runtimes are mounted, whichever `AGENT_CMD` runs.**
   The Claude-side destination is the probed `source`. The agy-side
   destination is `/home/worker/.gemini/antigravity-cli/plugins/<plugin>` —
   flat and unversioned, because the Dockerfile installs agy plugins by plain
   `cp -r "$MP_ROOT/$p-agy"` to that path, so no version enters it. Mounting
   both means `--live-edit` means the same thing for `run claude`, `run agy`,
   and a `run shell` that invokes either.

4. **Fail loudly, before any mount, if the source is missing.**
   `resolve_live_edit_mounts` refuses if the workspace has no `dist/` (no
   local build) or if any plugin the image installed lacks its built
   `dist/<name>-claude` or `dist/<name>-agy` directory. `probe_image_plugin_roots`
   refuses if the image has no readable manifest, if it is not JSON, if it
   declares no plugins, or if a `source` is not an absolute path. Each is a
   hard failure naming the missing path, not a skipped mount.

5. **Fail loudly, before any mount, if the destination is wrong.**
   `verify_live_edit_destinations(image, mounts)` runs a plain
   `docker run --rm --entrypoint sh <image> -c 'test -d <dest1> && test -d
   <dest2> && ...'` — no volumes attached — against every destination before
   `run`'s real container ever starts. This is what makes a wrong path a hard
   failure instead of Docker's silent directory-auto-create. Checking _after_
   mounting would only ever observe the mount's own target and could never
   detect this bug.

6. **Mount read-only, once verified.**
   Only after every destination is confirmed to pre-exist does `run` add
   `-v {host dist/<name>-{claude,agy}}:{container plugin path}:ro`, alongside
   the workspace/staging/session mounts `run` already builds (see
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
   `/home/worker/.claude/plugins/cache/` or
   `/home/worker/.gemini/antigravity-cli/plugins/`, and no probe runs.
2. **Destinations are the image's, never derived host-side** — Test: against
   an image whose baked version differs from anything the host would compute,
   the `-v` destination is the version the image reported, and resolution
   makes no subprocess call that could re-derive one.
3. **Enabled produces the expected mounts** — Test: with a local `dist/`
   build present, `--live-edit` adds a `:ro` mount from
   `dist/<name>-claude` to the image's reported `source`, and from
   `dist/<name>-agy` to
   `/home/worker/.gemini/antigravity-cli/plugins/<name>`, for every plugin
   the image installed.
4. **A bogus destination is a hard failure, not a silent no-op** — Test: when
   the preflight probe reports a destination does not exist in the image,
   `run` exits non-zero before the main container starts, and no container
   from that invocation ever runs. Likewise when the image carries no
   readable marketplace manifest.
5. **A host edit is visible in an image nobody rebuilt** — Test: against an
   image whose baked plugin version differs from the host's, edit a file
   under a plugin's shipped source on the host, rebuild `dist/` (`make
   build`, not `make docker-build`), start a container with `--live-edit`,
   and read the edited string back from the container's own installed-plugin
   path. Edit again, `make build` again, and the second edit is visible too —
   with no image rebuild between them.
