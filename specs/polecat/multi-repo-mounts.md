---
id: multi-repo-mounts
title: "Polecat System: Mapping Additional Repositories into a Container"
type: spec
status: draft
tier: polecat
depends_on: [polecat-system]
tags: [spec, polecat, architecture, multi-repo, mount-contract]
---

# Polecat System: Mapping Additional Repositories into a Container

**Door type: one-way.** This changes the mount contract every dispatch depends
on. This document is the design; it authorises nothing to be built. Per
`framework-gate`, implementation proceeds only after this spec is approved —
Nic's merge of the spec PR is the sign-off (no separate `SIGN-OFF (Nic)` task
node is created for it, per the 2026-08-26 rule in `wf-human-approval` /
`pr-review`).

Task: `aops_12ccba4c`. Read against working-tree HEAD `7119a4f87` (branch
`polecat/session-b7ca6a48`) on 2026-08-28. Every citation below was read this
session; none is carried over from the task body's 2026-08-13 ground truth,
whose line numbers have moved (`_resolve_workspace` was `cli.py:882-899`, is
now `cli.py:984-1001`; `_build_docker_argv` was `cli.py:1006-1094`, is now
`cli.py:1283-1408`).

## 1. Problem statement — DRAFT, unconfirmed, needs Nic's sign-off

**No confirmed problem statement exists.** The task's acceptance criteria
require establishing this with Nic (`develop-specification` step 3); this is a
headless spec pass with no channel to ask him directly, so the following is an
inferred draft only, offered so PR review has something concrete to correct
rather than nothing:

The single-repo guarantee (`specs/polecat/polecat-system.md`, line 13) means a
polecat cannot be dispatched on any task that touches two repositories in one
container — e.g. testing a framework change (this repo) against a downstream
client project that depends on it, or a task that edits a project repo and
needs to read (not edit) a sibling reference repo for context. The parent epic
(`task-50c6f767`, "Ship the polecat distributed worker fleet") scopes this
work to provisioning, not to a named use case, and its target
(`aops-f770fe8a`) discounts the value to "possible" specifically because
"the design is not settled" and "cuts into the isolation guarantee the
fleet's trustworthiness rests on" — i.e. the epic itself treats the use case
as unproven, not as a given.

**This is a real gap.** A reviewer must not read the rest of this document as
though the problem statement is settled. It is the first thing PR review
should either confirm or correct.

## 2. Nic's mount rule (stated 2026-08-13, binding, verbatim)

> isolation earns write; shared host state gets read-only.

A repo polecat clones, or one that is on its own branch, mounts RW. A
directory mapped straight off the host mounts RO. This spec applies the rule
mechanically (§4.1) rather than exposing it as an operator-settable flag, so
no config can violate it by construction.

**Out of scope, decided elsewhere:** whether the _existing_ `-d`/`--repo-dir`
path (today RW, `cli.py:1346-1348`, no `:ro`) becomes RO under this same rule
belongs to `aops_e2a29475` per no-duplication — that task's acceptance
criterion is exactly this decision. This spec does not touch `-d`'s current
behaviour for the primary repo.

## 3. What this changes in `specs/polecat/polecat-system.md`

- **Line 13** — "Polecat runs one agent CLI invocation inside an isolated
  Docker container, on an isolated git clone" states the mount as singular.
  Changes to: one agent CLI invocation inside an isolated Docker container, on
  one primary isolated git clone (or host mount) and zero or more additional
  repos, each either its own isolated clone or a read-only host mount.
- **"What `run` does" step 2** (`polecat-system.md:46-48`) — resolves exactly
  one workspace. Gains a new step: resolve zero or more additional repos from
  `projects.<slug>.repos` (§4.1) or `--extra-repo-dir` (§4.3), each following
  the same clone-or-mount branch as the primary.
- **"Guarantees" item 1** (`polecat-system.md:127-129`) — "Every `run` without
  `--repo-dir` works on its own throwaway clone" is true per-repo already (the
  sentence doesn't assume a repo count); it gains a clause that every
  _additional_ cloned repo gets its own throwaway clone under the same
  session, torn down with the primary's.
- No other guarantee, user expectation, or "what `run` does not do" line
  changes. In particular, guarantee 5 ("One plugin path") and the branch-naming
  user expectation (`polecat-system.md:202`) are untouched — this spec adds
  repos, not plugin paths or output-branch semantics.

## 4. Design

### 4.1 Config surface: extend the config Nic already sketched, don't invent a new one

`lib/polecat/defaults/polecat.yaml.example` already documents a
`projects.<slug>.mounts:` list — added by Nic himself in the same merge that
shipped `--with-sessions` (`83def5ee2`, 2026-08-26):

```
#     mounts:                         # optional, for empirical projects
#       - host: $AOPS_SESSIONS/secrets/your-project/
#         container: /run/secrets/project/
#         mode: ro
```

**This key is documented but unimplemented**: `grep -n '"mounts"' lib/polecat/cli.py`
returns zero matches. It is the closest existing precedent for "map something
extra into a container by config," but its shape (`host`, `container`,
free-form `mode`) is wrong for repos specifically: a free `mode: rw|ro` field
lets an operator declare a host-mapped directory RW, which is exactly what
Nic's rule forbids. Rather than generalise that field, this spec proposes a
sibling key scoped to repos, where RW/RO is _derived_ from how the repo enters
the container, never independently settable:

```yaml
projects:
  your-project:
    repos:
      - name: sibling-repo        # required; becomes the container mount name
        project: sibling-project  # looked up in local.yaml paths, cloned like the primary -> RW
        branch: main               # optional; extends --base/branch: semantics, see §4.2
```

A repo entered via `project:` (looked up in `<polecat_home>/local.yaml`
`paths`, precedented at `cli.py:990-991`) is cloned exactly like the primary
(§4.2) and mounts RW. There is no `path:`/host-directory form in the `repos:`
list — a host directory that bypasses cloning is a `--extra-repo-dir` CLI flag
(§4.3), not a config key, matching the existing primary-repo dichotomy where
`--repo-dir` is a CLI-only override and never appears in `polecat.yaml`.

**Why not generalise `mounts:` instead:** the existing `mounts:` block is
already scoped to "empirical projects" (secrets, data directories) and is
unimplemented — repurposing it for full repo clones would conflate two
different lifecycles (an inert host directory vs. a per-session git clone with
its own teardown, remote-repoint, and ref resolution) under one schema. Naming
them separately keeps `mounts:` free for its stated purpose and keeps this
feature's teardown/isolation logic auditable as its own code path.

### 4.2 Per-repo ref selection: extends `--base` / `branch:`, no second mechanism

Per Nic's 2026-08-13 instruction (recorded on the closed `aops-eedee10b`, and
verified live: `--base`'s help text is unchanged, `cli.py:1654-1656`), a
second ref-selection mechanism is a defect. Each entry in `repos:` reuses the
exact resolution chain `resolve_isolated_workspace` already implements
(`cli.py:634-683`): explicit override, then `branch:` on that repo's own
`projects.<name>` config block, then `HEAD`. Concretely: the per-repo `branch:`
key in §4.1's example is not a new mechanism — it is the same top-level
`branch:` key (`cli.py:682`, `config.get("branch")`) read from that repo's own
project config instead of the invocation's primary project config, which is
already how `sessions_access` is resolved per-project
(`config.get("projects", {}).get(project, {}).get("sessions_access")`,
`cli.py:1822`). No new flag is introduced for ref selection.

`--base` on the CLI remains primary-repo-only, unchanged. There is no
`--base` equivalent for additional repos; an operator who needs a
non-default ref for an additional repo sets that repo's own `branch:` in
`polecat.yaml`.

### 4.3 CLI surface

```
--extra-repo-dir PATH   Host path mounted directly, read-only, no clone.
                         Repeatable. Name derived from the directory's own
                         basename (sanitised the same way --project is,
                         cli.py:1746-1747).
```

This mirrors `-d`/`--repo-dir`'s existing "caller's own isolation to own"
comment (`cli.py:1764-1765`) for the primary repo, extended to additional
repos, and is unconditionally RO because a directly-mounted host path is
exactly the "shared host state" half of Nic's rule — there is no RW option
for this flag, by construction.

### 4.4 Container mount points and `_build_docker_argv`

The primary repo keeps `-v {workspace_dir}:/workspace -w /workspace`
unchanged (`cli.py:1346-1349`). Each additional repo mounts at
`/workspaces/<name>` (a new sibling directory, never inside `/workspace`
itself, so nothing already reading the tree at `/workspace` sees a change).
`_build_docker_argv` (`cli.py:1283-1298`) currently takes no mounts parameter
beyond the fixed set it already special-cases (`rules_dir`, docker socket,
`with_sessions`/`sessions_base`, lines 1368-1384); it needs a new parameter,
e.g. `extra_repos: tuple[(name, host_path, mode)]`, appended to `cmd` the same
way the existing `with_sessions` block is (lines 1380-1384) — one `-v` per
entry, `:ro` suffix present only for host-mapped entries, absent for cloned
ones, matching the existing pattern where `:ro` is a literal string suffix
(`cli.py:1351`, staging dir) rather than a separate flag.

### 4.5 Clone-path collision (found this session, not in the original ground truth)

`resolve_isolated_workspace` computes `clone_path = clones_dir / session_id`
(`cli.py:676-678`) — **one clone directory per session, not per repo.** If a
second repo is also cloned for the same session, it cannot reuse this path.
Proposal: leave the primary's clone path exactly as-is (`clones_dir /
session_id`, zero behaviour change to the primary), and clone each additional
repo at `clones_dir / session_id / "extra-<name>"`. This is a narrow addition
to `resolve_isolated_workspace`'s call sites, not a rewrite of the function:
it is called once per additional repo with a different `clone_path`, same
`base`/`branch`/`config` resolution.

## 5. Disposition of the five unowned constraints (task body's "hopes")

Every claim below is a fresh citation read this session, not a restatement of
the task body's 2026-08-13 citations.

**Git identity — unaffected, no change needed.** `resolve_git_identity`
(`cli.py:306-338`) reads one top-level `git_identity: {name, email}` block and
sets `GIT_AUTHOR_NAME/EMAIL`, `GIT_COMMITTER_NAME/EMAIL` as container-wide env
(`cli.py:367`). This is process-wide, not per-mount: every `git commit`
anywhere inside the container, in any mounted repo, already uses the same
identity today, and nothing in this design touches that call. A requirement
for _different_ bot identities per repo is a different feature, not requested
here and not implied by "map multiple repos."

**Credential helper — unaffected for repos the existing token already
reaches; out of scope otherwise.** `entrypoint.sh:23-30` installs one
`credential.helper` that echoes `GH_TOKEN` (`AOPS_BOT_GH_TOKEN`) for any
`https://` git remote. This is host-agnostic in its mechanism (it answers any
credential request the same way) but only actually authenticates where that
one token has access. Multiple repos on the same GitHub account/org the bot
token already covers work with zero change. A repo needing a distinct token
or host is out of scope: no per-repo credential mechanism exists today and
none is proposed — flagged as a residual limitation (§8), not solved here.

**Session-state path (`CLAUDE_SESSION_PATH`/`AGY_SESSION_PATH`) — unaffected,
no change needed.** These are module-level constants
(`/home/worker/.claude/projects/-workspace`,
`/home/worker/.gemini/tmp/workspace`, `cli.py:1006-1007`) that encode where
the _agent's own_ CLI writes its session transcript, keyed to the primary
workspace mount point. Because §4.4 keeps the primary at `/workspace`
unchanged and puts additional repos at a disjoint `/workspaces/<name>` path,
neither constant needs to change or become plural.

**Session-log keying — unaffected; the original concern does not hold once
read closely.** `session_dir = sessions_base / "logs" / session_date /
session_id / (project or "workspace")` (`cli.py:1761`). This is keyed by
`session_id` first — unique per invocation, either an explicit
`--session-name` or `f"session-{uuid.uuid4().hex[:8]}"` (`cli.py:1758`) — with
`project` only as the final path component under that already-unique
directory. Multiple repos mounted in **one** invocation share one
`session_id` and therefore one `session_dir`; there is no collision, because
the collision the task body worried about ("two repos under one `-p`
collide") would require two _separate_ invocations reusing one
`--session-name`, which is a pre-existing, unrelated behaviour this design
does not touch. No change needed here — this corrects rather than confirms
the original hope.

**Dispatch pathway — citation drift, real gap identified.** The task body
names a `dispatch` skill under `plugins/orchestrate/skills/` as the mandatory
route; no such skill exists in the current tree (that directory contains only
`audit/`, `session-trace/`, `strategic-review/`, `verify/` — checked via
`ls`). The actual sole constructor of `polecat run` invocations today is the
**`pc` agent** (`plugins/orchestrate/agents/pc.md`, lines 33-64), whose
documented commands pass exactly one `-p <project>` and no repo-count concept
at all. Recommendation:
**zero change to `pc.md`.** Because §4.1 puts additional repos entirely in
`polecat.yaml` (server-side config keyed by the primary project's slug), a
caller dispatching with the same `-p <project>` it already uses gets the
additional repos automatically, with no new flag for `pc` to learn or pass
through. This is a deliberate design consequence of §4.1's config-only
surface, not an oversight: it keeps `pc`'s already-narrow allowed toolset
(`Bash(uv run *)`, `Bash(git *)`, `Bash(ssh *)`) untouched. `--extra-repo-dir`
(§4.3) is CLI-only and, like `-d` today, is for direct/interactive/debug
invocations outside `pc`'s scope — `pc.md` should gain one line noting it
exists and is not part of `pc`'s own repertoire, so a future reader doesn't
assume the omission is accidental.

## 6. Why this will not decay the way the July rewrite's generic surface did

The July rewrite (`26bb3b45a`, 2026-07-30) deleted a generic
`polecat.yaml mounts:` mechanism along with the rest of the legacy package.
This design avoids repeating that shape in three ways:

1. **It is not a generic executor.** `repos:` and `--extra-repo-dir` are two
   named, enumerable knobs, each with one fixed behaviour (clone-and-RW,
   mount-and-RO) — not a free-form list interpreted at runtime the way the
   documented-but-unimplemented `mounts:` block is. A future maintainer
   auditing "what can this container touch" reads two call sites, not a
   config-driven loop.
2. **RW/RO is derived, not declared.** No field lets an operator write
   `mode: rw` against a host path — the isolation rule is enforced by which
   code path a repo takes to enter the container, not by a value a config
   file could get wrong. This is different from the `mounts:` block's own
   `mode:` field, which is exactly the kind of operator-settable flag that
   allowed the rule to erode before.
3. **It ships with tests mapped to each guarantee (§7), not just prose.**
   `test_workspace_isolation.py` already enforces the singular guarantee this
   way; extending that file (rather than only extending `polecat-system.md`)
   means the multi-repo guarantee fails CI the same way the single-repo one
   would, rather than depending on a maintainer re-reading a spec before a
   future change.

## 7. Acceptance criteria and integration-test mapping

| #   | Acceptance criterion                                                                                                                                                                                                                | Integration test                                                                                                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC1 | A repo listed under `projects.<slug>.repos` is cloned per-session at `clones_dir/session_id/extra-<name>`, mounted RW at `/workspaces/<name>`, and removed when the container exits — the host source repo is untouched throughout. | New test in `tests/polecat/test_workspace_isolation.py`, parallel to `test_isolated_workspace_is_never_the_canonical_path` (line 58) and `test_cleanup_removes_worktree_and_branch` (line 128), parametrised for an additional repo.                                       |
| AC2 | `--extra-repo-dir PATH` mounts a host directory read-only with no clone step invoked for it.                                                                                                                                        | New test in `tests/polecat/test_container_config.py`, parallel to `test_rules_dir_mounted_read_only_at_container_aca_data` (line 144) and `test_no_rules_mount_when_unconfigured` (line 137).                                                                              |
| AC3 | An additional repo's ref resolves through the same `base`/`branch`/`config` chain as the primary (explicit → that repo's `branch:` → `HEAD`), with no second flag.                                                                  | Extend the `resolve_isolated_workspace` test family (`test_isolated_workspace_respects_base_option`, line 204; `test_isolated_workspace_defaults_to_config_branch`, line 229) to assert the additional-repo call site is the same function, not a parallel implementation. |
| AC4 | git identity and the credential helper work unmodified for commits/pushes made in an additional repo inside the container.                                                                                                          | Extend `tests/polecat/test_container_smoke.py` (a real container run) to commit and push from the additional repo's mount, asserting author/committer match the single configured `git_identity`.                                                                          |
| AC5 | The primary workspace mount point, `CLAUDE_SESSION_PATH`/`AGY_SESSION_PATH`, and the session-log directory path are byte-identical whether zero or N additional repos are configured.                                               | New regression test asserting `_build_docker_argv`'s primary `-v .../workspace` and `-w /workspace` args, and the session-path env values, are unchanged by the presence of `extra_repos`.                                                                                 |
| AC6 | No `SIGN-OFF (Nic)` task node is created for this spec's own review/merge cycle.                                                                                                                                                    | Process check, not a code test: verified at merge time against the `wf-human-approval`/`pr-review` templates' 2026-08-26 rule.                                                                                                                                             |

## 8. Effort, risk, and out-of-scope

**Effort (estimate, not measured):** implementation is a config/CLI/mount-argv
change touching `_resolve_workspace`'s call sites, `resolve_isolated_workspace`
(new `clone_path` parameter), `_build_docker_argv` (new `extra_repos`
parameter), and `run`'s config-reading section — roughly the same order of
change as the `--with-sessions` merge (`83def5ee2`, 17 lines of doc + CLI flag

- ~15 lines in `_build_docker_argv`). One day is plausible; this is not
  measured against a prototype.

**Residual risk — cannot be closed from this session.** `aops_63985c64` ("the
isolation-leak class a new mount surface must not re-open") is unreadable:
`get_task`/`get_document` both fail with "Failed to read task file: Is a
directory (os error 21)" per this session's hydration pass, and no
independent content for it exists anywhere else in the graph or this
repository. This spec's RO/RW derivation (§6.2) is designed against Nic's
stated rule and against what I could read of the isolation guarantees in
`polecat-system.md`, but **it has not been checked against `aops_63985c64`'s
actual content**, because that content is not currently accessible to any
agent. This is a fail condition per the task's own acceptance text ("thin
evidence on the five constraints is itself a fail condition") for that one
node specifically, and it is out of this document's power to fix — it needs
filesystem-level repair of the PKB store, not a design change. **Recommend:
resolve `aops_63985c64`'s file corruption and re-read it against this design
before the human sign-off gate for implementation (not before this spec's own
PR review) — a design change here would need this spec to be revised, but
that revision should not block the current review from finding what it can
find.**

**Out of scope, explicitly:**

- Whether `-d`/`--repo-dir` becomes read-only for the primary repo —
  `aops_e2a29475`.
- A second branch/ref-override mechanism — forbidden by Nic, 2026-08-13
  (`aops-eedee10b`).
- The output-branch override (`polecat/<session-id>`) — a tested contract
  (`polecat-system.md:202`; `tests/polecat/test_workspace_isolation.py`), and
  confirmed dead as a design intent (`aops-613690b5`).
- Per-repo git identity or per-repo credentials — no evidence this was asked
  for; flagged as a residual limitation in §5, not designed here.
- Implementation itself. This document ends at an approved spec.

## 9. Pointers

- [[aops-eedee10b]] — base-ref selection, closed satisfied; the mechanism §4.2
  extends. Content only survives paraphrased in `aops_12ccba4c`'s own body —
  the node itself is unreadable this session (filesystem: "Is a directory").
- [[aops_e2a29475]] — owns whether `-d` becomes RO; unreadable this session,
  same cause. §2 defers to it explicitly.
- [[aops_63985c64]] — the isolation-leak class this design must not reopen;
  unreadable this session, no independent content found anywhere. See §8
  residual risk.
- [[aops-803b1ffa]] — cross-repo sessions access. Corrected this session (by
  the hydration pass) from "capability absent" to done: `--with-sessions`
  (`cli.py:1662-1666`, merged `83def5ee2`) delivers the sessions-mount half of
  its scope.
- [[aops-613690b5]] — the output-branch override, lost in the July rewrite; a
  design record, not live intent. Out of scope (§8).
