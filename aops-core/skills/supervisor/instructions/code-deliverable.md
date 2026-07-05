# Code Deliverable Subworkflow

How the generic supervisor loop ([[../SKILL.md]], [[supervision-loop]]) maps onto the
**code-PR concrete case**: each work item is a pull request, the review surface is GitHub, async
ownership transfers via PR labels. The universal loop — orient → decompose → review → dispatch →
verify → react → halt — is unchanged; only the vocabulary below is code-specific. A non-code
deliverable (research, methodology) has its own subworkflow with different vocabulary and the same
generic loop.

> **`polecat` not on PATH?** In non-interactive shells the alias is not loaded — substitute the
> canonical form `uv run --project $AOPS $AOPS/polecat/cli.py <args>` for bare `polecat`.

## Surface binding

The code-deliverable specialisation, one row per artifact class:

| Artifact class                                                 | Review surface                     | Sanctioned harness                                                                                                                                                                                             | Completion condition                                        |
| -------------------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Intermediate task on a shared branch (cohesive single-PR epic) | shared branch diff — **no PR yet** | local outcome check: `git log origin/polecat/epic-<epic-id> --grep=<task-id>` proves the commit landed; diff inspected non-empty, syntactically valid, no debug scripts / placeholders / leaked creds          | `merge_ready` on a clean local verify (unblocks dependents) |
| Cumulative final PR (cohesive single-PR epic)                  | one GitHub PR at the end           | **marsha capstone** — the §2a single pass on the cumulative diff (sanctioned QA harness identified at ORIENT, exact previously-failing user-facing check from the ledger, byte-match rule-out); never invented | `merge_ready` when the promoted PR passes marsha            |
| Standalone / independent task                                  | per-task GitHub PR                 | marsha per PR                                                                                                                                                                                                  | PR open + marsha PASS                                       |

Decompose = review-sized subtasks (≤ 0.5d, ≤ 10 files, single "why", ≤ 15-min human read), grouped
for the shared-branch default. React on the capstone verdict: marsha **FAIL** → pauli `role=react`;
**REVISE** → file a verification subtask; worker exit with **no PR** → pauli `role=react`, context
`no-deliverable`; intermediate local-verify FAIL / worker exit non-zero → pauli `role=react`,
context `verification-failed` / `worker-failed`.

## Dispatch

- **Pre-dispatch gates** (pauli runs them at preflight; the main agent never invokes them inline) —
  host check, PKB-readiness probe, and the Pre-flight Confirmation Summary. Canonical:
  [[worker-dispatch#mandatory-pre-dispatch-gates]]. Critic gate for high-blast-radius tasks:
  [[worker-dispatch#critic-gate-for-high-blast-radius-tasks]].
- **Dispatch command** (shared-branch `--branch polecat/epic-<epic-id>` default, model aliases,
  Jules): [[../references/cohesive-pr-epic#canonical-dispatch-command-polecat-surface]]; current host
  path + model-alias list in PKB memory `mem-3014f36b`.
- **Polecat exit codes**: exit 0 + "✅ already done" → task was `done`, graceful noop; exit 2 +
  "🔒 locked" → task already has an open PR, record it and do not retry dispatch.
- **PR-opened detection** is a one-shot `gh pr list --search head:polecat/<id>` on worker exit —
  never a poll loop. In-session batch notify-watch (docker `die` events):
  [[../SKILL.md#in-session-multi-tick-supervision-notify-watch]].

## Halt — the supervisor stops at the review surface

The supervisor's job ends when the single PR (cohesive epic) or the individual PRs (standalone) are
promoted / opened — that **is** the completion signal. Set the epic `merge_ready` and stop; the
existing GHA pipeline (pr-pipeline.yml → CI, lint, rbg axiom review, admit gate) and manual human
review own everything downstream. The supervisor **MUST NOT** poll CI, run `gh run watch` /
`gh pr view --json statusCheckRollup,reviews`, chase reviewers, read `merge-prep-status`, react to
bot `CHANGES_REQUESTED`, or `gh pr merge` — a transcript showing any of these against an
already-open PR is a bug (the supervisor should have halted). Task completion on merge is handled by
the branch-name → `pkb` automation, not the supervisor.

Final report = one table per epic (# / Task ID / Title / PR / State) ending with
"Next surface: the existing GHA pipeline and manual human review. No further supervisor action." —
never a "polling will continue" / "I'll check back in N minutes" line.

## Traps specific to code deliverables

(Per-surface worker failure modes: [[SURFACES.md]] _Known traps_ sections.)

- **Deferred verification is not verification.** A TDD fix shipping with tests the worker could not
  actually run (Docker rebuild, credentialed service, long wall-clock, external API) is inference —
  marsha returns `REVISE`; file a follow-up verification task `depends_on` the PR that `soft_blocks`
  the epic's COMPLETE transition. Do not mark the epic complete until every deferred-verification
  task is `done` or the human accepts it as permanently manual.
- **Jules**: sessions show "Completed" when coding is done but require human approval on the Jules
  web UI before branches push and PRs open (`jules remote list --session`).
- **Fork PRs**: a bot pushing to a fork needs CI checkout on `head.sha` (not `head.ref`); guard
  autofix-push steps with `head.repo.full_name == github.repository`.
- Auto-finish overrides manual completion when another worker already fixed the task (`aops-fdc9d0e2`).
  Gemini polecats are slow (15–20+ min to first commit; boot-time stderr is cosmetic —
  [[SURFACES.md#polecat-run-gemini]]). Use the task ID in the container name to avoid
  concurrent-dispatch collisions. Check `dprint.json` before dispatch (plugin 404s burn 10+ min).
  PKB MCP is unreachable from sandbox containers (workers can't update task status).
  `merge-prep-status` is set/cleared by the pipeline — the supervisor never reads, triggers, or waits on it.
