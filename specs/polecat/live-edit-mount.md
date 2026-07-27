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
  `_plugin_install_dir_error`, `resolve_live_edit_mounts`,
  `verify_live_edit_destinations`, and the `--live-edit` option on `run`
- [[tests/polecat/test_live_edit_mount.py]] — destinations taken from the
  image and never derived host-side, the `-v` mounts present when enabled and
  absent when disabled, the refusal on a bogus, malformed, or over-wide
  destination and on an unreadable image, and the warning and confirmation
  lines that keep a live session distinguishable from a baked one
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

The mirror-image danger is a destination that is real but too wide. Docker
mounts happily over a directory that already exists, so the preflight in step 5
cannot catch this one: a `source` of `/home/worker` would shadow the container's
entire home read-only and still pass every existence check. The live route to it
is not a corrupt-image hypothetical —
[[plugins/aops/polecat/defaults/docker_gemini_fixups.py]]'s
`fixup_marketplace_cache` falls back to `version_dir = ""` when a plugin's cache
directory has no version subdirectory, which makes that plugin's `source` its
_parent_ cache directory. Mounting there hides the very version directory
`installed_plugins.json` points at, and hides it silently.

Only one shape is therefore accepted as a Claude-side destination:
`cache/<marketplace>/<plugin>/<version>` — exactly two segments below the
image's plugin cache root, with the first naming the plugin that claims it. That
is one plugin's own install directory and nothing wider. A `source` that is
relative, outside the cache root, short a version segment, or another plugin's
directory is refused at the point the manifest is read, before any of it can
become a mount.

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
   plugins the image reported, not the ones the host built. A plugin the image
   installed but the host has not built is a hard failure, because leaving it
   unmounted would leave it serving baked-in code inside a session that
   believes it is live.

   A plugin the host built but the image lacks is the opposite case — there is
   no destination to shadow, so it cannot be mounted — and it is a **warning
   naming the skipped plugins**, not a refusal. The run remains genuinely
   useful for every other plugin, and the realistic cause is a developer adding
   a new plugin against an older image, where refusing would block a working
   loop. Skipping it silently would not be acceptable, though: that developer
   gets exit 0, no output, and a container that ignores their edits — the same
   false green the whole feature exists to prevent, produced by the feature
   itself. The warning names the skipped plugins and says that the image never
   installed them, so they are not in the container at all — absent, not stale.
   A developer told instead that the container "runs what the image was built
   with" would go hunting for out-of-date behaviour from a plugin that has no
   copy there to be out of date.

   A build for _either_ runtime counts as built: `dist/<name>-agy` with no
   `-claude` sibling is still a plugin whose edits will not be live, and
   scanning only the Claude side would reproduce the silent skip inside the
   warning meant to end it.

3. **Both runtimes are mounted, whichever `AGENT_CMD` runs.**
   The Claude-side destination is the probed `source`. The agy-side
   destination is `/home/worker/.gemini/antigravity-cli/plugins/<plugin>` —
   flat and unversioned, because the Dockerfile installs agy plugins by plain
   `cp -r "$MP_ROOT/$p-agy"` to that path, so no version enters it. Mounting
   both means `--live-edit` means the same thing for `run claude`, `run agy`,
   and a `run shell` that invokes either.

4. **Fail loudly, before any mount, on a source that cannot be trusted.**
   `resolve_live_edit_mounts` refuses if the workspace has no `dist/` (no
   local build) or if any plugin the image installed lacks its built
   `dist/<name>-claude` or `dist/<name>-agy` directory.
   `probe_image_plugin_roots` refuses if the image has no readable manifest,
   if the manifest is not JSON, if it is not a JSON object, if it declares no
   plugins, if any plugin entry is not itself an object (a bare list of names
   and a plugin-keyed mapping are both valid JSON and neither carries a
   `source`), if an entry has no name, or if its `source` is not that plugin's
   own install directory in the shape given above. Each is a hard failure
   naming the offending path or entry, not a skipped mount — and a refusal,
   never a traceback: a crash and a refusal are equivalent only until someone
   tries to act on the message.

5. **Fail loudly, before any mount, if the destination is wrong.**
   `verify_live_edit_destinations(image, mounts)` runs a plain
   `docker run --rm --entrypoint sh <image> -c 'test -d <dest1> || echo
   <dest1>; ...'` — no volumes attached — against every destination before
   `run`'s real container ever starts, and refuses naming each destination the
   image reported back as absent. This is what makes a wrong path a hard
   failure instead of Docker's silent directory-auto-create. Checking _after_
   mounting would only ever observe the mount's own target and could never
   detect this bug.

   This stays a second container rather than folding into step 1's probe.
   The destinations being checked _come from_ step 1's output, so a single
   probe would have to replace `test -d <exact destination>` with a directory
   listing post-processed on the host — a weaker predicate, and a second
   host-side implementation of the destination rule, against a hardcoded cache
   tree depth, free to drift from `_plugin_install_dir_error` with nothing to
   catch it. `test -d` instead asks the container the same question about the
   same path the mount will use. The saved container start is worth less than
   testing the predicate that actually governs the mount.

6. **Mount read-only, once verified.**
   Only after every destination is confirmed to pre-exist does `run` add
   `-v {host dist/<name>-{claude,agy}}:{container plugin path}:ro`, alongside
   the workspace/staging/session mounts `run` already builds (see
   [[polecat-system]] step 6). Read-only: a live-edit session edits the host
   checkout, never the container's filesystem.

7. **Say what was mounted, before the container starts.**
   Without this a `--live-edit` run's pre-container output is byte-identical to
   a baked one, so the terminal gives a developer no way to tell which code is
   about to run — the confusion this flag exists to end, left in place by the
   flag itself.

   `run` emits one line carrying the host `dist/` now being served, the plugins
   it covers, and the image's own version directory it displaced. The version
   is the image's — the commit that image was baked at, which is precisely the
   code just shadowed — so it is never rendered `<plugin>@<version>`: that is
   the universal idiom for the version in play, and a developer asking "why
   isn't my edit showing" must not be handed a commit that is not theirs as the
   answer. It is stated once, not per plugin: `make build` versions every
   plugin together, so the normal case is one version repeated across the whole
   set, which would bury the `dist/` path that actually answers the question.
   Only when the image reports genuinely differing versions does the line
   itemise them per plugin.

   The plugin list covers both runtimes, because both are mounted for every
   plugin. The version qualifier is marked Claude-side, since the agy
   destination is flat and has no version to report.

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
   `run` exits non-zero before the main container starts, naming that
   destination, and no container from that invocation ever runs. Likewise when
   the image carries no readable marketplace manifest.
5. **A destination wider than one plugin is refused** — Test: a manifest whose
   `source` is `/home/worker`, is the plugin's parent cache directory (no
   version segment), or is another plugin's directory exits non-zero at
   resolution time, even though all three directories exist in the image.
6. **A malformed manifest refuses rather than crashes** — Test: `{"plugins":
   ["aops"]}` and a plugin-keyed mapping both exit non-zero with a message
   naming the manifest path, not with an `AttributeError`.
7. **A plugin the image lacks is named, not swallowed** — Test: with a `dist/`
   containing a plugin the image never installed, `run --live-edit` warns on
   stderr naming that plugin and stating it is not installed in the container
   at all, and still mounts every plugin the image does install. A plugin built
   only as `dist/<name>-agy`, with no `-claude` sibling, is named the same way.
8. **A live session is distinguishable from a baked one** — Test: `run
   --live-edit` prints, before the container starts, a line naming the host
   `dist/`, the plugins covered, and the image's displaced version directory —
   attributed to the image and not spelled `<plugin>@<version>`, and carried
   once rather than once per plugin when the versions are equal; a run without
   the flag prints no such line.
9. **A host edit is visible in an image nobody rebuilt** — Test: against an
   image whose baked plugin version differs from the host's, edit a file
   under a plugin's shipped source on the host, rebuild `dist/` (`make
   build`, not `make docker-build`), start a container with `--live-edit`,
   and read the edited string back from the container's own installed-plugin
   path. Edit again, `make build` again, and the second edit is visible too —
   with no image rebuild between them.
