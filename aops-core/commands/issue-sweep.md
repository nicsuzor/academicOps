---
name: issue-sweep
type: command
category: instruction
description: Triage one batch of open GitHub issues — classify, present, gate on user, dispatch confirmed fix-epics via /supervisor.
triggers:
  - "issue sweep"
  - "sweep issues"
  - "triage issues"
  - "drain issue backlog"
  - "process open issues"
modifies_files: true
needs_task: false
mode: execution
domain:
  - framework
  - operations
  - quality-assurance
allowed-tools: Bash, Read, Grep, Glob, Edit, Skill, Agent, AskUserQuestion, mcp__pkb__list_tasks, mcp__pkb__get_task, mcp__pkb__create_task, mcp__pkb__update_task, mcp__pkb__append
model: opus
permalink: commands/issue-sweep
---

# /issue-sweep — Quality-gated GitHub issue triage

**Purpose**: Run **one cycle** of the open-issue sweep on `nicsuzor/academicOps`. Classify a batch (≤ 20) of open issues against a fixed disposition rubric, present the proposed dispatch plan to the user, wait for sign-off, then execute the confirmed actions (close / comment / file polecat task / dispatch fix-epic via `/supervisor`). Record cycle outcomes in the loop epic body. **HALT after one cycle** — re-invoke `/issue-sweep` for the next.

**Privacy rule**: Never paste raw transcripts, PII, or credentials into issue comments. Issues are public.

**Hard halts**:

- No silent dispatch. Every state-changing action waits for explicit user confirmation in chat.
- No improvised disposition. If an issue does not fit a rubric row cleanly, surface it under "Needs human triage" — do not invent a sixth bucket mid-cycle.
- No cursor stored in task body. The label `triaged-*` IS the cursor; the next cycle's `gh` query excludes already-stamped issues.

**See also**: [[../skills/supervisor/SKILL.md]] · [[../skills/qa/SKILL.md]] · [[../AXIOMS.md]] · [[../HEURISTICS.md]]

## Concepts

### Disposition set

| Disposition      | Criterion                                                                                                                                                                                                                                                                                                                           | Action                                                                                   | Stamp label                                                      |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `close-as-stale` | (a) > 90d old AND no recent comments AND root cause fixed, **or** (b) describes behaviour the framework no longer has — verifiable cheaply by `grep` for the named component returning zero hits in the current source tree, or by a linked PR/commit retiring it. If neither verification is cheap, route to "Needs human triage." | `gh issue close` with a comment citing the resolving change or the retired component     | `triaged-stale` (issue is closed; label is on the closed record) |
| `comment-only`   | Volume bump on a duplicate or related still-open issue (the canonical issue should track the recurrence count)                                                                                                                                                                                                                      | `gh issue comment` on canonical issue, then close the duplicate referencing it           | `triaged-comment`                                                |
| `single-task`    | Atomic mechanical fix: (i) AC stated or trivially derivable from issue body, (ii) ≤ 3 files changed, (iii) one obvious implementation (no design choice), (iv) no cross-component coordination                                                                                                                                      | File a polecat task with `Closes #N` in PR body; dispatch via the existing polecat queue | `triaged-single`                                                 |
| `fix-epic`       | Multi-step, multi-file, or design-required (no obvious AC without scoping)                                                                                                                                                                                                                                                          | Propose epic to user. On confirmation: create epic + decompose + invoke `/supervisor`    | `triaged-epic`                                                   |
| `defer`          | Real but blocked, low-criticality, or waiting on external input/signal                                                                                                                                                                                                                                                              | Apply `triaged-defer` label with a `revisit-by-YYYY-MM-DD` line in a comment             | `triaged-defer`                                                  |

**Decidability rule**: every disposition must be decidable in < 30 seconds by a fresh agent reading the issue body and its top three comments. If you find yourself spending longer, the issue belongs in "Needs human triage."

### Cursor strategy: label-based, not numeric

There is **no cursor in the task body**. The cycle protocol uses the existence of `triaged-*` labels as a durable filter:

```bash
# Already-triaged issues are excluded by label. Order is criticality-desc, then age-asc.
gh issue list --repo nicsuzor/academicOps --state open --limit 100 \
  --search 'sort:created-asc -label:triaged-stale -label:triaged-comment -label:triaged-single -label:triaged-epic -label:triaged-defer'
```

Then sort the JSON output client-side by criticality first (critical > high > medium > low > unlabelled), age second.

### Stopping condition (label-based completeness — NOT count-based)

The loop stops only when, after a cycle's labels are applied, **every** open issue is one of:

1. < 7 days old (newly arrived, not yet due for triage), OR
2. Stamped `triaged-defer` with a `revisit-by-YYYY-MM-DD` comment, OR
3. Linked to an in-progress fix-epic (issue body or comment references the epic ID and the epic's status is `in_progress` or `merge_ready`), OR
4. Closed.

**Plus** both:

- Zero `criticality:critical` open without an active fix-epic.
- Zero `criticality:high` open and > 14 days old without an active fix-epic.

If the cycle leaves any open issue not satisfying one of (1)–(4), the loop continues.

## Workflow

### 1. Pre-flight

```bash
# Confirm baseline.
gh issue list --repo nicsuzor/academicOps --state open --limit 1 --json totalCount  # or fall back to --json number, count locally
gh label list --repo nicsuzor/academicOps --limit 200 | grep -E '^(triaged-|criticality:)'
```

**Required labels (verify, then create only what's missing)**:

```bash
existing=$(gh label list --repo nicsuzor/academicOps --limit 200 --json name --jq '.[].name')
for L in triaged-stale triaged-comment triaged-single triaged-epic triaged-defer; do
  if ! grep -qx "$L" <<< "$existing"; then
    gh label create "$L" --repo nicsuzor/academicOps --color ededed --description "Issue-sweep disposition: ${L#triaged-}"
  fi
done
```

If `gh label create` fails for a label that does not already exist, halt and surface the error — do not paper over with `|| true`.

Read the parent loop epic so the cycle log goes to the right place:

```
mcp__pkb__get_task(id="epic-a0523a25")   # the loop epic — cycle log appends here, not to T2
```

If `epic-a0523a25` is not `in_progress`, halt and ask the user (the loop has been paused).

### 2. Pull a batch

Cap at **20 issues per cycle**. Smaller is fine — quality at small N beats sloppy throughput.

```bash
gh issue list --repo nicsuzor/academicOps --state open --limit 100 \
  --search 'sort:created-asc -label:triaged-stale -label:triaged-comment -label:triaged-single -label:triaged-epic -label:triaged-defer' \
  --json number,title,labels,createdAt,updatedAt,comments,body \
  > /tmp/issue-sweep-batch.json
```

Client-side sort: criticality-desc, then age-asc. Take the top 20.

### 3. Classify

For each issue in the batch:

1. Read the body and the most recent ≤ 3 comments. For potential `fix-epic` candidates, also read any linked PR titles.
2. Apply the rubric. Pick exactly one disposition or mark "Needs human triage."
3. Group `fix-epic` candidates that share a root cause into proposed epics. **Cap at 5 issues per proposed epic** to keep scope tight.
4. Note the rationale in one line per issue. The user reads this to authorise.

Common pitfalls:

- An issue describing a "missing label" or "missing automation" is usually a `single-task`, not a `fix-epic`.
- An issue whose body is one sentence and which has zero comments is usually `single-task` or `defer`, not `fix-epic`. Don't over-decompose.
- An issue describing behaviour the framework no longer has (component retired, replaced, deleted) is `close-as-stale` even if it's recent.

### 4. Present the cycle plan and gate

Output the plan in this exact format and **wait for confirmation per fix-epic** plus one batch confirmation for single-tasks and one for close/comment-only. Do not proceed past this step without explicit `y` from the user for each section.

```
## Cycle <N> — proposed dispatches  (open before: <K>; batch size: <M>)

### Fix-epic 1: <one-line title>
- Issues bundled: #A, #B, #C
- Why grouped: <one line>
- Proposed scope: <bullet list of subtasks>
- Estimated effort: <S/M/L>
- Acceptance criteria: <bullets>
- Confirm? [y / edit / defer / split / merge-into-epic-X]

### Fix-epic 2: ...
(repeat per epic)

### Single-tasks
- #X → "<title>" (estimated XS)
- #Y → "<title>" (estimated S)
Confirm batch? [y / edit list / defer all]

### Close / comment-only
- Close (stale): #P (resolving change: PR#…), #Q (component retired)
- Comment + close as duplicate: #R → bumps #S, #T → bumps #U
Confirm? [y / edit]

### Needs human triage
- #Z (rubric ambiguous: <reason>)
```

Use `AskUserQuestion` for each gate. Halt cleanly if the user declines or edits — re-emit the plan and gate again.

### 5. Execute confirmed actions

Order of execution (low-blast-radius first, so failures don't strand higher-impact work):

1. **`comment-only`**: post comment on canonical, then close duplicate.
2. **`close-as-stale`**: close with comment.
3. **`defer`**: add `triaged-defer` label and post the `revisit-by-YYYY-MM-DD` comment.
4. **`single-task`**: file polecat task via `mcp__pkb__create_task`. Set body to include the issue body, AC, and `Closes #N` instruction for the eventual PR. Stamp the issue with `triaged-single`.
5. **`fix-epic`** (only those confirmed by the user): create epic via `mcp__pkb__create_task` parented under the appropriate component epic (NOT under `epic-a0523a25` — per its Coherence rule, per-issue fixes are not children of the loop epic). Decompose into subtasks. Per P#109, create a `verify-parent` task that depends on all subtasks — this task confirms the epic's bundled issues are fully resolved after implementation completes. Invoke `/supervisor` on the new epic. Stamp each bundled issue with `triaged-epic` and a comment linking the epic ID.

For each disposition, stamp the corresponding `triaged-*` label so the next cycle's filter excludes it.

### 6. Append cycle log to the loop epic

The cycle-log schema is owned by **`epic-a0523a25`** (the loop epic), not by this command. Read the loop epic body and copy the schema fields verbatim — do not maintain a parallel copy here, which would drift on schema changes.

Process:

1. `mcp__pkb__get_task(id="epic-a0523a25")` — read the body, find the `## Cycle state (lives in T2 body)` block. (Despite the section's wording, this loop's actual decision was to log to the loop epic itself; the schema fields are still authoritative.)
2. Populate one entry per field defined there. Add a `**triaged-* totals**` line (stale=, comment=, single=, epic=, defer=) so the next cycle's stopping-condition check is one read away.
3. If the schema is absent or unreadable, **halt** — do not invent fields.

Append:

```
mcp__pkb__append(id="epic-a0523a25", content="<populated entry, including: cursor=label-based; batch size; issues processed; per-disposition lists; friction filed; open count after cycle; triaged-* totals; stopping condition met yes/no with one-line evidence>")
```

### 7. Hand off to /qa

After the log entry is appended, hand off to the per-cycle independent reviewer (T3 in the loop architecture). Pass a prose brief naming the cycle, the epic, and the reviewer pair; the `/qa` skill itself accepts a free-form prompt rather than CLI flags.

```
Skill(skill="qa", args="Verify cycle <N> of /issue-sweep on epic-a0523a25. Sample 20% of processed issues (minimum 3). Reviewers: Pauli (cohesion) + RBG (axiom compliance). Conditionally also Marsha if any single-tasks dispatched this cycle.")
```

The QA contract (sample size: 20% of the cycle's processed issues, minimum 3):

- **Pauli** (cohesion lens, always): does each disposition match the rubric? Are fix-epic groupings coherent (single root cause)? Are single-tasks structurally atomic per the rubric (≤ 3 files, one obvious implementation, no design choice)?
- **RBG** (axiom compliance, always): does the cycle violate any AXIOMS.md or HEURISTICS.md rule? Was a user-confirmation gate skipped? Was an issue silently dropped between the cursor advance and the dispatch list?
- **Marsha** (runtime verification, conditional — invoked only if ≥ 1 single-task was dispatched this cycle): for at least one dispatched single-task, does the linked polecat task body actually solve the issue's AC?

If QA produces a regression verdict, file via `/learn` before re-invoking `/issue-sweep`.

### 8. HALT

Do **not** start the next cycle. Re-invocation of `/issue-sweep` (manually or by a future scheduler) starts cycle N+1.

### 9. Framework Reflection

```
## Framework Reflection
**Prompts**: /issue-sweep
**Outcome**: [success/partial/failure]
**Cycle**: <N>
**Open delta**: <K> → <K'>
**Dispatched fix-epics**: <ids>
**Friction filed**: <issue URLs from /learn, if any>
```

## Worked examples (from the 2026-04-30 backlog)

These are the canonical patterns. When in doubt, pattern-match against these.

| Disposition      | Issue                                                                                             | Why this disposition                                                                                                                                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `close-as-stale` | **#5** "[Hydration] Deadlock: prompt-hydrator subagent blocked by the hook it's meant to resolve" | Describes the prompt-hydration architecture, which has been retired (PKB-MCP migration, brain PKB migration). Falls under the "behaviour the framework no longer has" branch even though < 90d. Close with a comment citing the migration PRs. |
| `comment-only`   | **#100** "Bug: agent shortcut bias skipped E2E test execution from plan"                          | Volume bump on the recurring "shortcut bias / skipped verification" theme also seen in #380 and #583. Comment on the canonical issue (whichever has the most thread depth) and close #100 as a duplicate.                                      |
| `single-task`    | **#102** "Bug: router.sh UV_CACHE_DIR blocks Claude inside Docker containers"                     | Atomic mechanical fix. One file (`router.sh`), one cause (hardcoded `UV_CACHE_DIR`), obvious fix (use writable user path or guard inside container). AC: Claude produces tokens inside Docker. ≤ 1h.                                           |
| `fix-epic`       | **#817** "aops-core periodic-enforcer hook references non-existent aops-core:enforcer agent"      | Multi-plugin (aops-core + aops-cowork), requires design decision (rename agent? update hook? cross-plugin namespacing?), touches hooks + agents + plugin manifests. Cannot be done as a single mechanical patch.                               |
| `defer`          | **#83** "Enhancement: Scale sleep cycle for 1000+ task graph maintenance"                         | Real but speculative; current graph far below 1000 tasks; no urgency; needs empirical scaling data before AC can be written. Apply `triaged-defer` with `revisit-by-2026-10-01` (six months) and a comment explaining the prerequisite.        |

## Arguments

- `/issue-sweep` — run one cycle starting from the highest-criticality, oldest untriaged issue. Default batch size: 20.
- `/issue-sweep --batch 10` — override batch size for this cycle.
- `/issue-sweep --dry-run` — produce the cycle plan and present it for review, but do not execute confirmed actions or write the cycle log. Use during rubric tuning.

## What this command does NOT do

- **Does not fix any issue.** Single-tasks and fix-epics are dispatched, not executed in this command. Their actual work is done by polecat workers and `/supervisor`-driven sub-agents.
- **Does not modify `/learn` or `/retro`.** Their issue-creation behaviour is the input.
- **Does not run on a schedule.** GHA-cron `/issue-sweep` is explicitly out of scope until the manual loop has proven its rubric over 3–5 cycles. Silent dispatch would violate quality guarantee #4 of the loop epic.
- **Does not consume `/loop`.** Per the loop-epic decision log, `/loop`-driven cadence is decided after manual cycles have validated the rubric.

## Anti-patterns

| Anti-pattern                                                                    | Why it's wrong                                                                            | What to do instead                                                                                 |
| :------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| "Use judgment" criteria                                                         | Fresh agents will diverge; rubric loses meaning                                           | Every disposition must be decidable in < 30s — sharpen the criterion                               |
| Skipping the user-confirmation gate "because the criteria are obvious"          | The gate IS the quality guarantee                                                         | Always present and wait                                                                            |
| Stamping `triaged-epic` or invoking `/supervisor` before the user's `y` arrives | Violates loop-epic quality guarantee #4 (no silent dispatch) — even the label is dispatch | All stamps and `/supervisor` calls live in step 5, AFTER step 4's gate returns `y`. Never overlap. |
| Auto-deciding via a recommendation engine                                       | Loop is human-in-the-loop by design                                                       | Surface the plan; never act on classification alone                                                |
| Inventing a sixth disposition mid-cycle                                         | Erodes the rubric                                                                         | Surface under "Needs human triage"                                                                 |
| Storing a numeric cursor in the task body                                       | Diverges from labels under interruption                                                   | Labels are the cursor — read the GH state, not the task body                                       |
| Writing the cycle log to T2 (the driver)                                        | Wrong file — schema lives in the loop epic                                                | Append to `epic-a0523a25`                                                                          |
| Parenting fix-epics under `epic-a0523a25`                                       | Violates Coherence rule of the loop epic                                                  | Parent under the relevant component epic                                                           |
| Bundling > 5 issues into one fix-epic                                           | Scope balloons; user can't review                                                         | Split into multiple fix-epics or surface the largest as `human-triage`                             |
| Re-running the cycle without halting                                            | Silent multi-cycle drift                                                                  | Halt after one cycle; re-invoke for the next                                                       |
| Filing a `/learn` regression mid-cycle                                          | Confuses dispatch state                                                                   | Finish the cycle, then file friction at step 9                                                     |
