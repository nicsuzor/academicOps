# Worker Dispatch

The dispatch mechanics that govern epic progression.

> **Surface reference**: see [[SURFACES.md]] for execution surfaces, plugin sources, gates, and dispatch capability per surface. Pauli reads it fresh on each preflight.

## Mandatory Pre-Dispatch Gates

### 0. Premise Gate (hard refuse — runs first, before any pre-flight row)

Before anything else, **read the task body and judge whether it carries a genuine premise assessment** — a one-sentence, principal-voice judgment, recorded at promotion to `queued`, that this task is worth doing and rightly shaped (see [[../../remember/references/premise-gate.md]]). This is an **agent judgment made by reading**, never a regex/field/heading presence-check — a presence-check rig would itself be the deterministic-substitute-for-judgment the gate exists to stop (`judgment-non-delegable`). If the body shows no genuine premise judgment (absent, empty, a rubber-stamp like "looks fine", or a checklist instead of a judgment), **HALT — do not dispatch, do not spend compute**: append `dispatch_halt` to Pattern Memory, set the task back to `ready` / route it to the promoter with a one-line reason, and exit. The premise judgment is the spend-stopper; it is cheaper to bounce a bad premise here than after a worker has built it.

### Pre-flight Confirmation Summary

Before pauli emits a `dispatch` verdict, she validates the task purely through PKB operations via a 4-row **Pre-flight Confirmation Summary**.

**Which variant applies:** Use the Design/Research variant if task `type` or `kind` is design/spec/research, OR if the AC indicates creating a new file/design doc/spec. Otherwise, use the Code/Edit variant.

### 1. Pre-flight Confirmation Summary (Code / Edit Tasks)

**Inputs**: Task body, existing file paths.
**Checks (5-row table)**:

1. **Task ID:** The epic / subtask being dispatched.
2. **Source repo:** Inferred from file paths the task names (file-path grep validates source repo).
3. **Project:** Task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
4. **Next link in chain:** Ensure the task unblocks the epic's critical path.
5. **Sanctioned mechanism:** Check memory/loop spec for a recorded sanctioned mechanism (e.g. `feedback_agy_wsl_dashboard_qa_loop`). Verify chosen worker/method aligns; refuse ad-hoc harness/test-script substitutions.

**Halt conditions:** Any row is unknown, source repo cannot be inferred, `project` is missing and ancestors are ambiguous, dependencies are not met, or a sanctioned mechanism is violated/substituted.
**Dispatch line:** `dispatch <worker> on <task-id> in <project>`

### 2. Pre-flight Confirmation Summary (Design / Spec / Research Tasks)

**Inputs**: Task body, Acceptance Criteria.
**Checks (5-row table)**:

1. **Task ID:** The epic / subtask being dispatched.
2. **Output artefact location:** Canonical spec or reference doc the design edits will land in (taken from AC).
3. **Project:** Task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
4. **Next link in chain:** Ensure the task unblocks the epic's critical path.
5. **Sanctioned mechanism:** Check memory/loop spec for a recorded sanctioned mechanism (e.g. `feedback_agy_wsl_dashboard_qa_loop`). Verify chosen worker/method aligns; refuse ad-hoc harness/test-script substitutions.

**Halt conditions:** Any row is unknown, no AC describes where the deliverable lands, `project` is missing and ancestors are ambiguous, dependencies are not met, or a sanctioned mechanism is violated/substituted.
**Dispatch line:** `dispatch <worker> on <task-id> in <project>`

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
