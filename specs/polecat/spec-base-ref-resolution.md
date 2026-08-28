# Specification: Polecat Base-Ref Resolution & Remote Freshness

- **Task:** [[aops_a0eca995]]
- **Epic:** [[aops_bb5d538b]]
- **Status:** Draft / Ready for Review
- **Author Identity:** Antigravity Engineering Agent
- **Target Subsystem:** `lib/polecat/cli.py` (`resolve_isolated_workspace`)

---

## 1. Problem Statement & Failure Modes

Polecat isolates worker container workspaces by creating a dedicated local clone for each dispatch session. When creating the worker clone, `resolve_isolated_workspace()` resolves the base commit SHA from which the worker's branch diverges.

In the current implementation (`lib/polecat/cli.py`):

1. Candidate refs are constructed as `refs_to_try = [base_ref]`, appending `origin/<base_ref>` **second** as a fallback.
2. Candidate resolution runs `git -C <canonical_dir> rev-parse` directly against the shared host checkout's local state.
3. No `git fetch` is performed anywhere in `cli.py`.

This architecture produces two critical failure modes:

| Failure Mode                               | Condition                                                                              | Current Behaviour                                                                                                                   | Severity                                                                                                                       |
| ------------------------------------------ | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Mode 1: Silent Stale Base**              | Local ref exists in canonical checkout but is behind remote upstream                   | Resolves to local stale SHA, creates worktree on old commit, runs and exits 0 with plausible single-purpose commit.                 | **Catastrophic (Silent Wrong Answer)**: Commits become reverts of merged upstream PRs. Diff stat shows mass deletions/reverts. |
| **Mode 2: Unresolvable / Remote-Only Ref** | Ref exists on remote `origin` but has not been fetched locally into canonical checkout | Candidate `[base_ref, origin/base_ref]` fails `rev-parse`, dying with `failed to resolve base ref` or `fatal: unable to read tree`. | **High (Loud Failure)**: Blocks dispatch on legitimate feature branches pushed from other worktrees/agents.                    |

Mode 1 is the primary defect: any fix that only resolves Mode 2 (making unresolvable refs work) while leaving Mode 1 open (silently preferring local stale refs) fails the safety bar.

---

## 2. Binding Constraints & Direction (Nic, 2026-08-26)

The following directions from project maintainer Nic are binding on this specification:

1. **No default to remote's default branch:** _"don't default to origin's main branch — I just changed that so it would allow dispatching from a feature branch."_ No path or error branch in the resolution logic may fall back to `main`, `master`, or any remote default branch.
2. **Require / prefer explicit branch over inference:** _"We should probably just ALWAYS specify branch, tbh."_ Requiring `--base` (or treating `--base` as explicit specification) is the leading candidate; inferring a base must strictly verify against remote.
3. **Freshness verified against remote at dispatch time:** _"ALWAYS make sure it's fresh."_ Freshness is verified against `origin` at dispatch time, never assumed from a ref resolving locally.

---

## 3. Resolution Rule & Algorithm

### 3.1 Base Ref Candidate Identification

When `resolve_isolated_workspace(canonical_dir, session_id, polecat_home, base, branch, config, ...)` is invoked:

- If `--base <ref>` is explicitly provided: `base_ref = base.strip()`.
- Else (if `--base` is omitted):
  - Check current HEAD in `canonical_dir`. If HEAD is attached to a branch `b` (e.g. `git symbolic-ref --short HEAD`), `base_ref = b`.
  - If HEAD is detached (e.g. raw SHA or rebase): `base_ref = "HEAD"`.
  - If configuration specifies a default branch (`config.get("branch")` or `config.get("default_branch")`), that is used only if not on a local branch.
  - Note: `--branch` specifies the name of the _output worker branch_ (Rule 3), not the base for divergence.

### 3.2 Remote Freshness & Verification

For a given `base_ref`:

1. Check if `canonical_dir` has a configured `origin` remote (`git remote get-url origin`).
2. If `origin` exists:
   - **If `base_ref` is a branch or tag name (not a detached raw SHA / HEAD):**
     - Fetch the ref from origin into the canonical checkout's remote-tracking namespace without moving any local branch:
       ```bash
       git -C <canonical_dir> fetch origin +refs/heads/<base_ref>:refs/remotes/origin/<base_ref>
       ```
     - Alternatively, run `git -C <canonical_dir> fetch origin <base_ref>`.
     - Resolve `base_sha` from the fetched remote ref:
       ```bash
       git -C <canonical_dir> rev-parse refs/remotes/origin/<base_ref>^{commit}
       ```
       (or `FETCH_HEAD^{commit}`).
     - **Remote ref is tried FIRST.** Local `refs/heads/<base_ref>` is NEVER consulted before the remote ref.
   - **If `base_ref` is `HEAD`:**
     - Determine if HEAD tracks an upstream branch: `git rev-parse --abbrev-ref --symbolic-full-name @{u}`.
     - If upstream exists (e.g. `origin/dev`), fetch it: `git fetch origin <upstream_branch>` and resolve `base_sha` from the upstream tracking ref.
     - If HEAD has no upstream or is detached: resolve local `HEAD^{commit}` (see Designer Decision 1).
3. If `origin` does NOT exist (local-only standalone repo):
   - Resolve `base_sha` from local `base_ref`.

### 3.3 Worker Clone Creation & Materialisation

1. Clone repo root with `--local --no-checkout`:
   ```bash
   git clone --local --no-checkout -c push.autoSetupRemote=true <repo_root> <clone_path>
   ```
2. Reset `origin` in `clone_path` per `aops_1f4c8e02` (`remote remove` + `remote add <origin_url>`) to eliminate fabricated refs.
3. Check out target branch at `base_sha`:
   ```bash
   git -C <clone_path> checkout -B <branch_name> <base_sha>
   ```
4. **Shallow repository object handling:** If `checkout` fails because `base_sha` is missing in `<clone_path>` (possible when `canonical_dir` is shallow and `git clone --local` omitted objects outside local `refs/heads/*`):
   - Fetch the commit directly in `<clone_path>`:
     ```bash
     git -C <clone_path> fetch --depth=50 origin <base_sha> || git -C <clone_path> fetch origin <base_ref>
     ```
   - Re-attempt checkout:
     ```bash
     git -C <clone_path> checkout -B <branch_name> <base_sha>
     ```
   - If checkout still fails, fail loudly and clean up `<clone_path>`.

---

## 4. Quadrant Analysis Table

The resolution behaviour across all repository types and local ref states is defined below:

| Repository Type | Local Ref State              | Defined Behaviour & Freshness Verification                                                                                                                                                                                             | Safety Property                                                                                        |
| --------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Non-Shallow** | **Current** (matches remote) | `git fetch origin <ref>` updates remote tracking ref; resolves `origin/<ref>`; checks out in clone.                                                                                                                                    | Safe (Current remote SHA used).                                                                        |
| **Non-Shallow** | **Stale** (behind remote)    | `git fetch origin <ref>` updates `origin/<ref>` to latest remote SHA. Resolution uses `origin/<ref>`, ignoring stale local `refs/heads/<ref>`. Clone checks out remote SHA.                                                            | **Safe (Mode 1 Closed)**: Stale local SHA is never selected.                                           |
| **Non-Shallow** | **Absent** (only on remote)  | `git fetch origin <ref>` fetches ref and objects into `canonical_dir`; resolves `origin/<ref>`; clone checks out remote SHA.                                                                                                           | **Safe (Mode 2 Closed)**: Unresolvable ref resolves cleanly.                                           |
| **Shallow**     | **Current** (matches remote) | `git fetch origin <ref>` verifies current SHA; clone checks out SHA (fetches in clone if object missing).                                                                                                                              | Safe.                                                                                                  |
| **Shallow**     | **Stale** (behind remote)    | `git fetch origin <ref>` updates `origin/<ref>` to latest remote SHA. Canonical `rev-parse` resolves `origin/<ref>`. Worker clone checks out remote SHA; if shallow clone lacks object, worker clone fetches `base_sha` from `origin`. | **Safe (Collision Resolved)**: Mode 1 closed in shallow repos without mutating local canonical branch. |
| **Shallow**     | **Absent** (only on remote)  | `git fetch origin <ref>` fetches ref into `canonical_dir`; `rev-parse` resolves `origin/<ref>`. Worker clone fetches `base_sha` from `origin` if shallow transfer omitted objects.                                                     | **Safe (Mode 2 Closed)**.                                                                              |

_Note on Shallow + Local-Ref-Stale quadrant:_ The tension between shallow checkouts and remote tracking refs is resolved by fetching the ref from `origin` to obtain the true remote SHA, and ensuring the worker clone fetches the missing object directly from `origin_url` if the local shallow clone did not inherit it. Under no circumstances is the stale local SHA used.

---

## 5. Designer Decisions on Open Questions

The following decisions address the three gaps where Nic's rules are silent. These are explicitly **the designer's decisions**, not attributed to Nic:

### Decision 1: Up-to-Date Definition for Detached HEAD / No Upstream

- **Question:** What does "up to date" mean when HEAD is detached or on a local-only branch with no upstream remote?
- **Designer's Decision:**
  - If `--base` is explicitly passed: the named ref MUST exist on `origin` (or be resolvable). If not found on `origin` and not found locally, fail fast.
  - If `--base` is omitted and HEAD is on a branch with no upstream tracking branch (or HEAD is detached): resolve local `HEAD^{commit}` directly. A local-only workspace with no remote has no upstream truth to diverge from, so local HEAD is the only coherent base.
  - _Rationale:_ Avoids artificial failures in offline / local-only test repos while strictly enforcing remote freshness whenever an upstream remote exists.

### Decision 2: Fetch Failure Behaviour (Fail Closed)

- **Question:** What happens when `git fetch` fails (network outage, auth expired, ref deleted upstream)? Fail the dispatch, or proceed on the local SHA with a warning?
- **Designer's Decision:** **FAIL CLOSED (Immediate Dispatch Error).**
- **Argument for Failure Direction:**
  Proceeding on a stale local SHA when remote verification fails re-opens Failure Mode 1 (silent wrong answers / mass reverts). In automated agent dispatch, an error that halts dispatch is visible, actionable, and safe. A dispatch that proceeds on stale refs silently destroys merged PRs. Therefore, any network, auth, or ref resolution error during fetch must abort dispatch immediately with a clear error message.

### Decision 3: Shared Canonical Checkout Immutability

- **Question:** May the fix move or fast-forward a local branch in the canonical checkout?
- **Designer's Decision:** **NO. ZERO MUTATION OF SHARED CANONICAL STATE.**
- **Specification:**
  - `git fetch origin +refs/heads/<ref>:refs/remotes/origin/<ref>` only touches `refs/remotes/origin/*`.
  - Local branches (`refs/heads/*`), working directory files, and index in `canonical_dir` are NEVER touched, fast-forwarded, or checked out.
  - All branch checkouts and modifications happen strictly inside `<polecat_home>/worktrees/<session_id>`.

---

## 6. Nic's Three Rules Implementation Mapping

| Rule ([[mem_ee2c4b30]])                                   | Specification in `lib/polecat/cli.py`                                                                                                                                                                    |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rule 1: Default to up-to-date HEAD**                    | When `--base` is unset, inspect current branch in canonical repo. If upstream tracking branch exists on origin, fetch it and use `origin/<upstream>` SHA. Detached/no-upstream HEAD uses local HEAD SHA. |
| **Rule 2: `--base` brings branch up to date by fetching** | When `--base <ref>` is passed, run `git fetch origin <ref>` to update `origin/<ref>` in canonical repo. Resolve `origin/<ref>` SHA first. Worker clone creates worktree from this remote SHA.            |
| **Rule 3: `--branch` names worktree, not base**           | `--branch <name>` is passed to `checkout -B <branch_name> <base_sha>` in the worker clone. It does NOT set or override `base_ref`.                                                                       |

---

## 7. Instruction Layer Updates

The instruction layer across skills and templates currently advises agents:
`--base` (which pins the dispatcher's local SHA, causing Mode 1).

### Disposition of Instructions:

1. **`dispatch` skill & CLI documentation:**
   - Change instructions from `--base` to `--base <branch-name>` (e.g. `--base dev` or `--base feature/my-feature`).
   - Passing branch names allows the dispatcher to verify freshness against `origin/<branch-name>` automatically.
   - For same-branch dispatches within the active repo, omit `--base` to automatically track up-to-date upstream HEAD per Rule 1.
2. **Disambiguation of `--branch` vs `--base`:**
   - Ensure all references clearly define `--base <ref>` as the base commit/branch to diverge from, and `--branch <name>` as the output branch name in the isolated workspace.

---

## 8. Integration Test Suite Design (TDD Specification)

Tests will be added to `tests/polecat/test_workspace_isolation.py` driving real git subprocesses without mocks.

### Test Cases:

1. `test_isolated_workspace_fetches_remote_when_local_branch_is_stale` (Mode 1 Regression Test):
   - **Setup:** Upstream bare repo with commit A, then B on branch `dev`. Canonical repo clones at A, creates local `dev` at A (stale). Upstream advances to B.
   - **Action:** Call `resolve_isolated_workspace(canonical, base="dev")`.
   - **Assert:** Isolated workspace HEAD is commit B (remote SHA), NOT commit A (stale local SHA). File contents in isolated workspace match commit B.
2. `test_isolated_workspace_fetches_remote_only_branch` (Mode 2 Regression Test):
   - **Setup:** Upstream bare repo has branch `feature-remote` with commit C. Canonical repo has never fetched `feature-remote` (no local branch, no remote tracking ref).
   - **Action:** Call `resolve_isolated_workspace(canonical, base="feature-remote")`.
   - **Assert:** Isolated workspace successfully resolves commit C and checks out without error.
3. `test_isolated_workspace_defaults_to_upstream_head_when_unconfigured`:
   - **Setup:** Upstream has commit D on `main`. Canonical checkout is on `main` at stale commit C.
   - **Action:** Call `resolve_isolated_workspace(canonical, base=None)`.
   - **Assert:** Isolated workspace HEAD is commit D (upstream HEAD), canonical checkout remains at C and is not mutated.
4. `test_isolated_workspace_fails_closed_on_unreachable_remote`:
   - **Setup:** Canonical repo with invalid origin URL (`https://invalid.example.com/repo.git`).
   - **Action:** Call `resolve_isolated_workspace(canonical, base="dev")`.
   - **Assert:** Raises `SystemExit` (fail-closed), does not fall back to stale local ref.
5. `test_canonical_checkout_is_never_mutated`:
   - **Assert:** Canonical repo `git status --porcelain` and `git rev-parse HEAD` are identical before and after all dispatch resolutions.

---

## 9. Deliverable Summary & Implementation

This document and the associated implementation in `lib/polecat/cli.py` and `tests/polecat/test_workspace_isolation.py` are delivered together under epic [[aops_bb5d538b]].
