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

**Compose-then-Dispatch Separation (mandatory).** The invocation that dispatches MUST NOT be the same invocation that authored or substantively refined the `## Dispatch Brief`. If pauli wrote or reshaped the brief this invocation, the verdict is `brief composed on <task-id>`; the supervisor chains a _separate_ dispatch-agent subagent (fresh subagent context) that reads the persisted brief from PKB and emits its own dispatch verdict. Compose-agent and dispatch-agent MAY co-occur in a single tick. Evaluate the dispatch-agent's verdict (action named, coherent, non-contradictory) before acting; do not rubber-stamp. See [[../SKILL#compose-then-dispatch-separation]] and the canonical doctrine at [[../../aops/references/authoring-discipline#3-compose-then-dispatch-separation]].

**Task Body Anti-Pattern (Verify Before Naming):** If you have to look up paths to fill the body, you're doing the worker's job. Apply the Task-Body Authoring Discipline ([[../../aops/references/authoring-discipline]]): **intent + AC, not prescription**. Any cited tool, file, or agent MUST be empirically verifiable; if you are unsure, mark it as "polecat to verify" or omit the specific name entirely.

**Worker-Type Capability Check (mandatory).** Before dispatching, the dispatcher must verify that the target worker type carries the required capabilities to fulfill the brief. Specifically, PKB-dependent work (read/write via get_task/get_document/etc.) must only be briefed by PKB-ID (e.g. `polecat run -t <task-id>`) to worker types carrying the PKB MCP tools (such as `junior`, `james`, `pauli`, `rbg`, `marsha`, or `polecat` containers). When dispatching to worker types lacking PKB tools (e.g. `general-purpose` subagents, `Jules`, or `GHA` runners), the brief content must be passed inline in the prompt or piped (e.g. `pkb task <task-id> | jules new`) rather than by PKB-ID. The dispatcher must determine whether the chosen worker type can fulfill a PKB-by-ID brief prior to dispatch.

**Jules notes**: For Jules (asynchronous, runs on Google infrastructure), pipe task context:
`pkb task <task-id> | jules new --repo <owner>/<repo>`

## Post-Dispatch

The supervisor checks status on its next ORIENT tick — it does not actively poll.
Stale task cleanup is periodic: `polecat reset-stalled --hours 4`

Worker failures surface as missing PRs or crashed statuses. The task stays `in_progress` until reset or picked up by the react phase.
