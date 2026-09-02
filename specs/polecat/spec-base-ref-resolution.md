---
id: spec-base-ref-resolution
title: "Polecat Base-Ref Resolution & Remote Freshness"
type: spec
status: ready
tier: polecat
depends_on: []
tags: [spec, polecat, git, freshness]
---

# Polecat Base-Ref Resolution & Remote Freshness

How `resolve_isolated_workspace()` (`lib/polecat/cli.py`) picks the commit a
worker's isolated clone diverges from. This is step 3 of
[polecat-system.md](polecat-system.md) § What `run` does. Implemented; regression
tests are `tests/polecat/test_workspace_isolation.py`.

## The two failure modes this design closes

Resolution reads refs from the shared host checkout, which can disagree with
`origin` in two ways:

| Mode                      | Condition                                                           | Consequence if unhandled                                                                                                        |
| ------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **1 — silent stale base** | Local ref exists but is behind remote                               | Worker branches from an old commit, runs, exits 0 with a plausible commit that is a **revert of merged upstream work**. Silent. |
| **2 — unresolvable ref**  | Ref exists on `origin` but was never fetched into the host checkout | `rev-parse` fails; dispatch is blocked on legitimate branches pushed from another worktree or agent. Loud.                      |

Mode 1 is the governing defect: a fix that only makes Mode 2 refs resolve, while
still preferring a local ref, fails the safety bar. Everything below follows from
preferring the remote.

## Binding rules

1. **Never default to a remote default branch.** No path and no error branch falls
   back to `main`, `master`, or `origin`'s HEAD — that would silently retarget a
   dispatch made from a feature branch.
2. **Freshness is verified against `origin` at dispatch time**, never inferred from
   a ref resolving locally.
3. **Zero mutation of the shared canonical checkout.** Fetches write only
   `refs/remotes/origin/*`. Local branches, working tree, and index in
   `canonical_dir` are never touched, fast-forwarded, or checked out. Every
   checkout happens inside `<polecat_home>/worktrees/<session_id>`.
4. **`--branch` names the output worker branch, not the base.** It reaches
   `checkout -B <branch_name> <base_sha>` in the clone and never sets `base_ref`.

## Resolution

### Choosing `base_ref`

- `--base <ref>` given → `base_ref = base.strip()`.
- `--base` omitted → the canonical checkout's current branch
  (`git symbolic-ref --short HEAD`), or `"HEAD"` when detached.

### Resolving `base_ref` to `base_sha`

With an `origin` remote configured:

- **A branch or tag name.** Fetch into the remote-tracking namespace only:

  ```bash
  git -C <canonical_dir> fetch origin +refs/heads/<base_ref>:refs/remotes/origin/<base_ref>
  ```

  falling back to `git fetch origin <base_ref>`. Then resolve in order
  `refs/remotes/origin/<base_ref>`, `origin/<base_ref>`, `<base_ref>` — the
  remote-tracking ref is tried **first**, which is what closes Mode 1, and the
  fetch is what closes Mode 2.

- **An `origin/<name>` ref.** Fetch `<name>` the same way, then resolve
  `refs/remotes/origin/<name>`.

- **`HEAD`.** If HEAD tracks an upstream (`git rev-parse --abbrev-ref
  --symbolic-full-name @{u}`), fetch `origin` and resolve the upstream ref,
  falling back to `HEAD`. With no upstream, resolve `HEAD` — a local-only branch
  has no upstream truth to diverge from, so local HEAD is the only coherent base.

With no `origin` remote, resolve `base_ref` locally. There is no upstream to
verify against.

### Fetch failure

Fetch failure fails the dispatch, unconditionally, for every `--base` form —
`--base <ref>`, `--base origin/<name>`, and the default (current-branch)
`base_ref` derived when `--base` is omitted. There is no fallback to
local-only verification, even when the ref also happens to resolve in the
canonical checkout (`--base HEAD~1`, a raw SHA, a same-named stale local
branch). Silently resolving to the wrong base lands work on the wrong tree
and stays invisible until much later; that is the ambiguity case where
halting beats guessing. An error that halts dispatch is visible and
actionable, a dispatch on a stale ref destroys merged work quietly.

This does not distinguish a transient network failure from a `<ref>` that
never existed on `origin` — both surface as a non-zero `git fetch` exit and
are treated identically. `git`'s own error text is not a reliable signal to
branch on (transport errors, auth failures, and "couldn't find remote ref"
are not consistently distinguishable across git versions and remotes), and
the two cases share the same governing risk: proceeding without remote
confirmation. A caller who hits this on a flaky network re-runs; a caller who
hits it on a typo'd ref gets the same actionable message either way. Divide
this further only if a concrete failure mode requires it — offline work is
explicitly out of scope for `resolve_isolated_workspace`, which always
verifies freshness against `origin` when one is configured.

## Clone materialisation

```bash
git clone --local --no-checkout -c push.autoSetupRemote=true <repo_root> <clone_path>
git -C <clone_path> checkout -B <branch_name> <base_sha>
```

`origin` in the clone is then **removed and re-added** at the canonical repo's own
upstream URL — not merely repointed. `git clone --local` seeds
`refs/remotes/origin/*` from the _source checkout's own local branches_, which were
never fetched from any remote; once the URL matches GitHub those fabricated refs
are indistinguishable from real remote-tracking refs. Dropping and re-adding the
remote removes them, so a later `origin/<branch>` lookup in the clone fails loudly
instead of silently resolving to a value that was never fetched.

The clone records what it was based on, in its own git config: `polecat.base` and
`branch.<branch_name>.base` both hold `base_ref`.

**Shallow-source handling.** When `canonical_dir` is shallow, `git clone --local`
can omit objects outside local `refs/heads/*`, so `base_sha` may be missing in the
clone. On checkout failure, the clone fetches the commit directly
(`git -C <clone_path> fetch --depth=50 origin <base_sha>`) and retries. A second
failure removes `<clone_path>` and fails loudly. Under no circumstance is a stale
local SHA substituted to make the checkout succeed.
