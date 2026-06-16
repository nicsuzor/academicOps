# Subagent Contracts

Detailed contracts for subagents invoked by the supervisor. The supervisor main agent
reads verdicts from these subagents and acts on them — it never executes their roles itself.

## Egress Constraints

Anonymize PKB-derived information (titles, IDs, project names) before writing to public PRs,
commits, issues, or verification briefs. Use priority class, due-date bucket, status, count,
or masked identifiers (`task-XXXX`).

## pauli — Preflight & React

- **Role**: Determine next action, handle worker exits, and react to verification failures.
- **Verdict Shape**: A single paragraph specifying exactly one action:
  - `dispatch <worker> on <task-id> in <project>`
  - `brief composed on <task-id>`
  - `file fix-task <title> under <parent>`
  - `halt: <reason>`
- **Verification Brief Assembly**:
  - Read original brief/spec and `## Fitness Rubric`.
  - Output one paragraph: artifact location/link + goal + spec link.
  - Do not include history, reviewer notes, dimensions, or manual check steps.
  - Halt if `## Fitness Rubric` is missing for user-facing artifacts.

## marsha — Verify (Review Surface)

- **Role**: Review deliverables for work items.
- **Review Surface Shift**:
  - **Cohesive Single-PR-Epic (Default)**: The supervisor review surface shifts to **single-PR-at-end**.
    The supervisor does NOT run marsha on separate PRs or individual work items as each finishes.
    Intermediate tasks are verified using local outcome-based verification (checking remote commit
    existence and inspecting the diff on the shared branch); once verified they are transitioned to
    `merge_ready`. The supervisor invokes marsha to review exactly ONE cumulative PR when the final
    stage promotes it. That single pass IS the capstone verification (§2a in [[../SKILL.md]]).
    The marsha brief MUST carry: the **sanctioned QA harness** (identified at ORIENT, never
    invented; HALT and `[ATTN]` if none recorded), the **exact previously-failing user-facing
    check** (supplied by the supervisor from the epic ledger — not reconstructed by marsha), and
    the **byte-match hallucination rule-out**. marsha's own `[[../verify/SKILL.md]]` enforces
    fresh-instance / non-implementer / source-trace posture.
  - **Standalone / Independent Tasks**: Keep legacy branch-per-task behavior; verify each PR individually.
- **Verdict**: PASS, FAIL `<reason>`, or REVISE `<reason>`.

| Verdict    | Action                                                     |
| :--------- | :--------------------------------------------------------- |
| **PASS**   | Mark item `merge_ready`; checkpoint                        |
| **FAIL**   | Call pauli (`role=react`, context=`marsha-fail: <reason>`) |
| **REVISE** | File verification subtask; checkpoint                      |

## Worker Handback Format

Every brief requires a capped structured handback — the supervisor reads _this_, not the
narrative thread:

```
VERDICT: <PASS | FAIL | BLOCKED | NEEDS-PRINCIPAL>
CLAIM: <one sentence — the conclusion>
GATE: <the acceptance gate, and the observed result against it>
EVIDENCE: <pointers — session id, log path, line refs — NOT pasted dumps>
CONFIDENCE: <high|med|low> + <what single control/test would falsify this>
CONFOUND CHECK: <did a clean-room/differential control run? result? — or "NOT RUN">
```

`CONFOUND CHECK` is mandatory whenever the verdict blames what we don't own; `NOT RUN` means do
not relay — commission the control first (§3 of [[../SKILL.md]]).

## Compose-then-Dispatch Separation

- The agent authoring a brief must not dispatch against it (agent-identity separation).
- If the brief was modified during the tick, pauli must output `brief composed on <task-id>`. The
  main agent persists the brief, then invokes a fresh subagent context (dispatch-agent) to
  validate and emit the `dispatch` verdict.
- If the brief is stable PKB content, pauli emits `dispatch` directly.
- Evaluate the dispatch-agent's verdict (action named, coherent, non-contradictory) before acting;
  do not rubber-stamp.

## Verdict Sanity Check

Before acting on any subagent verdict: one coherent action, internally consistent, grounded in
the actual task-body state. If it doesn't hold up — note why in the ledger and exit. This is a
read-and-judge, not a shape-validator.
