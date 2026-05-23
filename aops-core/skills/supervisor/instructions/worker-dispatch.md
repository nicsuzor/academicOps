# Worker Dispatch

The dispatch mechanics that govern epic progression.

> **Surface reference**: see [[SURFACES.md]] for execution surfaces, plugin sources, gates, and dispatch capability per surface. Pauli reads it fresh on each preflight.

## Mandatory Pre-Dispatch Gates

Before pauli emits a `dispatch` verdict, she validates the task purely through PKB operations via a 4-row **Pre-flight Confirmation Summary**.

**Which variant applies:** Use the Design/Research variant if task `type` or `kind` is design/spec/research, OR if the AC indicates creating a new file/design doc/spec. Otherwise, use the Code/Edit variant.

### 1. Pre-flight Confirmation Summary (Code / Edit Tasks)

**Inputs**: Task body, existing file paths.
**Checks (4-row table)**:

1. **Task ID:** The epic / subtask being dispatched.
2. **Source repo:** Inferred from file paths the task names (file-path grep validates source repo).
3. **Project:** Task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
4. **Next link in chain:** Ensure the task unblocks the epic's critical path.

**Halt conditions:** Any row is unknown, source repo cannot be inferred, `project` is missing and ancestors are ambiguous, or dependencies are not met.
**Dispatch line:** `dispatch <worker> on <task-id> in <project>`

### 2. Pre-flight Confirmation Summary (Design / Spec / Research Tasks)

**Inputs**: Task body, Acceptance Criteria.
**Checks (4-row table)**:

1. **Task ID:** The epic / subtask being dispatched.
2. **Output artefact location:** Canonical spec or reference doc the design edits will land in (taken from AC).
3. **Project:** Task's `project:` frontmatter MUST exist. If missing, pauli resolves it from unambiguous ancestors.
4. **Next link in chain:** Ensure the task unblocks the epic's critical path.

**Halt conditions:** Any row is unknown, no AC describes where the deliverable lands, `project` is missing and ancestors are ambiguous, or dependencies are not met.
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

The supervisor main agent runs the dispatch. See the **Canonical Dispatch Template** in `SKILL.md` for the exact Bash invocation.

**Compose-then-Dispatch Separation (mandatory).** The _agent invocation_ that dispatches a worker MUST NOT be the same invocation that authored or substantively refined the `## Dispatch Brief`. If pauli's work this invocation included writing or reshaping the brief — filtering inherited prose, narrowing scope to the worker shape, rewriting AC — the verdict is `brief composed on <task-id>`. The supervisor then chains a _separate_ dispatch-agent subagent (fresh subagent context — pauli re-invoked with `role=dispatch`, or another preflight-capable subagent) that reads the persisted brief from PKB and emits its own dispatch verdict. Compose-agent and dispatch-agent are two independent subagent invocations; they MAY co-occur in a single supervisor tick. A tick-exit-and-defer fallback remains legitimate for genuinely large compositions, but it is not required. See [[../SKILL#compose-then-dispatch-separation]] for the rationale (A17 propagated to the dispatch surface) and [[../../aops/references/authoring-discipline#3-compose-then-dispatch-separation-a17-propagated-to-the-dispatch-surface]] for the canonical doctrine.

This is not a gate or verdict on brief shape — pauli is not grading the brief and deciding whether to allow dispatch. It is a workflow boundary: composition and dispatch are different _agent invocations_, mediated by PKB. There is no PASS / REWRITE / HALT check inserted between them. The supervisor MUST evaluate the dispatch-agent's verdict's structural shape (action named, coherent, non-contradictory, no capability fabrication) before acting on it; rubber-stamping a malformed verdict erases the recusal property A17 establishes.

**Task Body Anti-Pattern (Verify Before Naming):** If you have to look up paths to fill the body, you're doing the worker's job. Apply the Task-Body Authoring Discipline ([[../../aops/references/authoring-discipline]]): **intent + AC, not prescription**. Any cited tool, file, or agent MUST be empirically verifiable; if you are unsure, mark it as "polecat to verify" or omit the specific name entirely.

**Jules notes**: For Jules (asynchronous, runs on Google infrastructure), pipe task context:
`pkb task <task-id> | jules new --repo <owner>/<repo>`

## Post-Dispatch

The supervisor checks status on its next ORIENT tick — it does not actively poll.
Stale task cleanup is periodic: `polecat reset-stalled --hours 4`

Worker failures surface as missing PRs or crashed statuses. The task stays `in_progress` until reset or picked up by the react phase.

### Turn Budget Exhaustion

If a worker exhausts its turn budget without finishing the task, it exits cleanly (status 1) and preserves the uncommitted worktree.

- Supervisors can resume the worktree with a fresh budget: `polecat resume <task-id>`
- To explicitly override the turn limit on a retry, use: `polecat run -t <task-id> --force --max-turns 150`
