---
name: dump
description: "Session exit and handover -- commit and push your work, release any claimed PKB tasks with a status report, and emit a single final handover message. Invoke whenever a session is ending, being interrupted, or work must be handed off to the next agent."
---

# Dump -- Session Exit

Every session exit must provide a formal handover.

If you have hit an error, exhausted your resources, or have been asked to terminate:

- you must abort immediately, save any progress, and return with minimal explanation and a simple resume path.
- you must still provide a handover message.
- you must release every task you claimed. A task you could not finish is
  released unfinished, with the reason; it is never left claimed and never
  quietly dropped.

## Handover process

### 1. SAVE AND PUSH YOUR WORK

You are running in an isolated, _ephemeral_ environment. Any files left on your local storage will be DESTROYED. Your commits are how your work leaves this session: uncommitted work does not exist.

- You **must** commit every change you made. Committing is not optional and is not conditional on the work being finished -- partial work is committed too, with a message that says what is partial.
- You **must** push if you can (`git push`).
- If you are opening a pull request (`gh pr create`), always target the base branch matching the cut line your worktree diverged from (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`); never hardcode `dev`, `main`, or `master`.
- If you are blocked from committing or pushing, you must find another way to save your work in a durable location, and you must say so in your final report.
- State the branch and commit SHA you left the work on in your report.

### 2. RELEASE YOUR TASKS

For EACH task you have worked, starting with children:

A. **Choose the status.** Incomplete and failed work has a terminal status;
reaching one is the handover, not a failure of it.

- `done` -- the deliverable meets the acceptance criteria as written. Nothing
  else earns it.
- `partial` -- a coherent chunk is delivered and the remainder is carried. Say
  in **Next** what the remainder is and what carries it.
- `review` -- the task is undeliverable as designed, or needs a human judgment
  you do not have authority to make. A `reason` is mandatory. Lack of access,
  tooling, instructions, or infrastructure lands here; it is not your fault and
  you do not repair it by rewriting the task.
- `cancelled` -- the task should not be done at all. Say why.
- `in_progress` -- only when a named successor is already picking this up in
  another live session. Ending a session on `in_progress` otherwise leaves the
  task claimed by a session that no longer exists.

Never write `status: blocked` into frontmatter. `blocked` is derived from
directed `blocks` edges: create or update the edge on the blocking task pointing
at this one, and release this task `review` or `partial`.

B. **Construct your report in the following format:**

```markdown
### Task: <task-id> (<precis>) -- <status: done | cancelled | review | partial | in_progress >

- **Update**: [ 1-3 sentences: what you did, what you learned, what remains ]
- **Output**: [ reference to any artifacts or work produced: e.g. `<branch>` (uncommitted: yes/no) | `url` | `pkb note id` and title | `filename` (warning: local files will be destroyed on exit)]
- **Next**: `<task-id>` [ title ] | [ Plain english instructions, with just enough detail to allow the next agent to pick up the work where you left off. ]
```

C. **Release your tasks, children first:** release the task with your session
id and your concise report via the PKB MCP tool (`pkb__release_task` or
`release_task`). Never fall back to direct filesystem access in `$ACA_DATA` or
the `pkb` CLI.

If the MCP tool fails or is unavailable, stop releasing and carry the verbatim
error into step 3. Your commits and your final report are then the whole
handover, so say in it which tasks are still claimed and by which session id.
A failed release does not licence a second attempt at stopping without a
report.

### 3. EMIT FINAL REPORT

Compile each of your reports into a single final message:

```markdown
## Handover: <agent> <session-id>

1. **The task** -- restate the whole thing you were asked to do, and check you
   have not read the scope more narrowly than it was written.
2. **Summary** -- what you found or made.
3. **Output**: <branch + commit SHA> | <PR or artefact URL> (description)
4. **Receipts** -- every load-bearing claim, itemized, each carrying its basis tag.
5. **Limitations** -- what is uncertain, what failed (with verbatim errors), what you did not do.
```

## STRICT REJECTION PROTOCOL: the rule against hearsay and return contract

Every load-bearing claim in your report MUST satisfy the Evidence Contract.

- **Declare basis on every claim**: Label each claim with its explicit basis:
  - `[observed: <file:line | command + verbatim output | node ID | URL>]` -- directly seen, cited with a pinpoint pointer.
  - `[attempted-and-failed: <command> -> <verbatim error>]` -- attempted action, command, or tool with its error output attached. (Mandatory for capability claims.)
  - `[exhaustively-searched: <tool/query/scope>]` -- search with stated query, tool, and bounded scope.
  - `[not-observed]` -- data or state not seen in the examined scope; never grounds non-existence.
  - `[inferred: <premises>]` -- deduced conclusion with stated premises and warrants.
  - `[assumed]` -- explicit working hypothesis.
  - `[reported-by-another: <source>]` -- attributed source with preserved qualification.
- **Hard gate on negative and capability claims**: You are strictly prohibited from asserting negative claims ("X does not exist", "X failed silently") or capability limits ("I don't have tool X", "I cannot run Y", "no Agent tool, no shell") without:
  1. A failed attempt with its verbatim error output (`[attempted-and-failed]`), OR
  2. A search whose exhaustiveness and exact boundary are stated (`[exhaustively-searched]`).
     Never assert a limit on yourself without having tested it.
- **Never launder inferences or assumptions as fact**: Uncertainty always propagates. Status qualifiers must survive every hop.
- **Cite EVERY empirical source**: `file:line`, task ID, command + output, or URL. Never remove citations or break the chain of evidence.
- **No causal claims without tracing**: Sequence is not cause. Prove every link.

## The Honesty and Integrity Clause

**HONESTY CLAUSE**: You are _strictly prohibited_ from acting upon or reproducing unreliable reports. Every claim you make must be supported by appropriate evidence, and all evidence must carry a citation or reference that will stand up to independent audit.

**LOGICAL INTEGRITY**: Critically evaluate your own reasoning before you submit your report. Any inference you draw must be carefully weighted to fit your warrants. Your report must contain a logically cohesive set of reasons to support your judgment.

Overconfidence is unacceptable; you must explain your level of confidence in every claim, hedge appropriately, explain why you rejected alternate hypotheses, and clearly disclose any limitations and unknowns.
