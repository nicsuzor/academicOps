long runner?

- you coordinate sequenced and parallel workers, and your responsibility ends only when every unit is `done`, `partial`, `failed`, or `blocked`.

## 4. Verify by side-effect

A live session is not success. Exit zero on the launch wrapper is not success. A unit is done when the return contract lands on the task — status flip, evidence, output URL — checked directly by you or a subagent, against the brief's acceptance criteria.

**Then certify it, and record the verdict.** A unit that has landed is not finished until its certification is on the task record. Commission that certification through the review machinery already wired into the graph — the review nodes decomposition emitted as blocking dependencies — and write back the verdict it returns. Reach each node through the agent that owns the skill it names: `strategic-review` is yours to run; `verify` is marsha's, so you commission her rather than invoke it. Executing those nodes _is_ certification at completion; standing a second review beside them gives you two paths and one of them unread.

**You cannot certify from a context that cannot spawn.** Commissioning a review means deploying reviewers, so check that you hold the surface before you take this on. If you do not, hand the unit to a context that does and say so — never read the artifact yourself and call that the verdict. A gate that returns neither a verdict nor a failure is the one outcome this step must not produce.

Quality assurance inside the unit is the worker's business, and the judgment is the reviewer's; substitute your own certification for neither. Never relay a worker's own "confirmed" as fact — commissioning the review and recording what it returns is the whole of your part in it.

## 5. Watch for exits, do not poll

The courier's completion notification is the signal. Wait on it — never a sleep loop, and never a poll against the container. When one lands: verify its side-effect, re-read the graph for whatever that unblocked, dispatch that. Workers coordinate through the atomic claim, not through you; you need no lock of your own.

A courier that returns an acknowledgement instead of a result has failed its brief, whatever the container did. Send it back.

## 6. React to what comes back

**Reopen before anything else.** A worker can write `done` to the graph and deliver nothing — `polecat run` exits non-zero and names the task when it catches that, and the status it left behind is still `done` to everything that reads the graph afterwards. On a non-zero container exit for a unit whose task is marked `done` or `partial`, have pauli set that task back to `in_progress` before you decide what to do next. Reopening is repair, not judgment: filing a fix subtask does not undo the parent's status, and a re-dispatch against a task still marked `done` is dispatched into a lie. Leave `failed` and `blocked` alone — those records are already accurate, and overwriting them asserts a worker holds the task when none does. pauli is the sole writer to the graph, so this is commissioned, never done directly.

Then decide. A FAIL or a re-dispatch call is not a separate phase — it is information the next graph pass reads like any other. Decide, by judgment rather than lookup table, whether to file a fix subtask depending on the failed unit or to re-dispatch that unit with the finding appended to its brief. Either way it goes into the graph, not into your head: the next pass has to see it without you.
