# Worker Dispatch

The dispatch mechanics that govern epic progression.

> **Surface reference**: see [[SURFACES.md]] for execution surfaces, plugin sources, gates, and dispatch capability per surface. Pauli reads it fresh on each preflight.

## Mandatory Pre-Dispatch Gates

### 0. Select + Gates spine (owned by `task-lifecycle` §§1–2)

Before the supervisor-only gates below, run the shared **Select → Gates** spine
authored once in [[../../task-lifecycle/SKILL.md]] §§1–2 (§1 Select; §2 Gates: the
premise gate plus the freshness / stale-leftover pre-check). Apply it as written
there — this file does not restate it. The premise gate is the two-judge clearance
owned by [[../../remember/references/premise-gate.md]] §2 (`rbg` + `pauli`,
CLEAR/BOUNCE); on a hard-refuse, append `dispatch_halt` to Pattern Memory before
exiting.

The pre-dispatch gates below — the pauli pre-flight confirmation, existing-PR
check, and critic gate — are the supervisor's own; they have no counterpart in
`task-lifecycle` and run **after** the shared spine, before dispatch.

### Pre-flight Confirmation Summary (one canonical checklist)

Before pauli emits a `dispatch` verdict, she validates the task purely through PKB operations via a single 5-row **Pre-flight Confirmation Summary**. One checklist covers both code/edit and design/spec/research tasks — only **row 2** (the deliverable-location row) reads differently by task type.

**Inputs**: task body; existing file paths (code/edit) or Acceptance Criteria (design/spec/research).
**Checks (5-row table)**:

1. **Task ID:** the epic / subtask being dispatched.
2. **Deliverable location** (variant-aware):
   - _Code / edit task_ (default) — **source repo**, inferred from the file paths the task names (file-path grep validates it).
   - _Design / spec / research task_ (task `type`/`kind` is design/spec/research, OR the AC creates a new file / design doc / spec) — **output-artefact location**, the canonical spec or reference doc the edits land in (from the AC).
3. **Project:** task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
4. **Next link in chain:** ensure the task unblocks the epic's critical path.
5. **Sanctioned mechanism:** check the memory/loop spec for a recorded sanctioned mechanism (e.g. `feedback_agy_wsl_dashboard_qa_loop`). Verify the chosen worker/method aligns; refuse ad-hoc harness/test-script substitutions.

**Halt conditions:** any row is unknown; row 2 cannot be resolved (source repo not inferable, or no AC describes where the deliverable lands); `project` is missing and ancestors are ambiguous; dependencies are not met; or a sanctioned mechanism is violated/substituted.
**Dispatch line:** `dispatch <worker> on <task-id> in <project>`

**Prep / review-only briefs — save the work, don't withhold it.** When the brief is "prepare a reviewable diff / prep only / do not merge / do not open a PR," it constrains the _terminal action only_. The brief MUST still direct the worker to **commit each chunk and push the branch to `origin`** — a reviewable diff is a pushed branch, not a dirty working tree in an environment about to be torn down. Never phrase a prep brief in a way that reads as "leave work unsaved." Canonical rule: [[framework-conventions-summary#commit-and-push-discipline]].

### Existing PR Check

For both variants: Is there already a PR linked to this task? If it's a known `pr_url`, Pauli checks its state. This is the only external call Pauli makes, if needed; strictly we prefer to trust the PKB status.

## Critic Gate for High-Blast-Radius Tasks

Some tasks carry risk of irreversible harm: OTA firmware updates, production deployments, data migrations, file deletions at scale. These require independent review of the task spec BEFORE dispatch.

### When the gate applies

A task requires critic-gated dispatch when the action is irreversible or has a blast radius disproportionate to its scope — operations that close recovery paths, affect systems beyond version control, or cannot be undone through a normal revert. Pauli judges whether the gate applies; if in doubt, gate it.

### Gate Protocol

1. **Prepare dispatch review context** (task spec, blast radius).
2. **Invoke critic** — pauli evaluates: is the spec complete? Are preconditions verified? Does the action close any recovery path? Verdict: `SAFE_TO_DISPATCH` / `NEEDS_REFINEMENT` / `DO_NOT_DISPATCH`.
3. **Record gate result** in the task body's Pattern Memory.

## Dispatch Execution

The supervisor main agent runs the dispatch. See [[../references/cohesive-pr-epic#canonical-dispatch-command-polecat-surface]] for the Bash template, and PKB memory `mem-3014f36b` for the current host path and model alias list.

**Compose-then-Dispatch Separation (mandatory).** The invocation that dispatches MUST NOT be the same invocation that authored or substantively refined the `## Dispatch Brief`. If pauli wrote or reshaped the brief this invocation, the verdict is `brief composed on <task-id>`; the supervisor chains a _separate_ dispatch-agent subagent (fresh subagent context) that reads the persisted brief from PKB and emits its own dispatch verdict. Compose-agent and dispatch-agent MAY co-occur in a single tick. Evaluate the dispatch-agent's verdict (action named, coherent, non-contradictory) before acting; do not rubber-stamp. See [[../references/subagent-contracts#compose-then-dispatch-separation]] and the canonical doctrine at [[../../aops/references/authoring-discipline#3-compose-then-dispatch-separation]].

**Task Body Anti-Pattern (Verify Before Naming):** If you have to look up paths to fill the body, you're doing the worker's job. Apply the Task-Body Authoring Discipline ([[../../aops/references/authoring-discipline]]): **intent + AC, not prescription**. Any cited tool, file, or agent MUST be empirically verifiable; if you are unsure, mark it as "polecat to verify" or omit the specific name entirely.

**Jules notes**: For Jules (asynchronous, runs on Google infrastructure), pipe task context:
`pkb task <task-id> | jules new --repo <owner>/<repo>`

## Post-Dispatch

The supervisor checks status on its next ORIENT tick — it does not actively poll.
Stale task cleanup is periodic: `polecat reset-stalled --hours 4`

Worker failures surface as missing PRs or crashed statuses. The task stays `in_progress` until reset or picked up by the react phase.
