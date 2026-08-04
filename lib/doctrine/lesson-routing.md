A diagnosed lesson goes to exactly one destination, chosen by the **scope the
lesson actually claims** — not by the nearest writable surface. Declare the scope
before you write. Ambiguous scope is an unresolved lesson: say so and stop rather
than guessing.

| The lesson is                                          | Scope     | It goes to                                    |
| ------------------------------------------------------ | --------- | --------------------------------------------- |
| A preference about this task or this collaboration     | task      | The task record's body                        |
| A standing obligation for work in this repository      | project   | `$CWD/.agents/rules/RULES.md`, via `add-rule` |
| A durable fact, technique, or decision worth recalling | knowledge | The PKB, via `remember`                       |
| A change to what a shipped agent is directed to do     | universal | Framework source — **gated**                  |
| A defect in the framework itself                       | universal | A tracked issue — **gated**                   |

### Task scope is the default home

An instruction phrased for the work in front of you — "for this task", "this
session", "while we're doing this" — is task scope even when it reads like a
rule, and promotion to a standing surface needs its own explicit ruling, never
inference from "this seems like a rule". Writing a session-bound preference into
a repo-wide standing surface is the characteristic failure this taxonomy exists
to prevent: every future worker on the repo then reads it as binding law.

### Test what the obligation is bound to

Phrasing is a weak signal, because a task-scoped directive is usually stated as
plain law — "commit directly to `v0.7`, no new branches" names no task and reads
exactly like a standing rule. The reliable test is what the obligation is bound
to, not how it is worded:

**Does it name a value that will itself change?** A branch name, a release, a
current phase, a person, a machine, a task id, "for now", the thing you happen to
be doing today. If obeying it a year from now requires knowing which branch was
current when it was written, it is task scope — it describes a situation, not an
obligation. A standing rule must still be true and checkable when everything
transient about today has moved on.

Apply this before the earns-its-place test below, because a state-bound directive
can pass that test and still be wrong: "no new branches" is perfectly
diff-checkable, and was still the wrong thing to write down.

### A project rule earns its place

Only if a reviewer could name the breach from a diff, and it does not already
follow from an axiom. If it cannot be checked, it is knowledge, not a rule.

### Do not legislate from the case in front of you

Writing a standing rule from this pass needs the user to have asked for one. That
is a different actor's decision, which is what makes it a warrant.

Recurrence you notice yourself is **not** a warrant to write. Deciding that a
pattern across incidents justifies a standing rule is the cross-incident pass's
call, and it is made detached from any single case — including this one, whose
framing you are currently inside. When you see the same failure recurring, cite
the earlier findings in what you route and say the pattern looks established.
Citing it is the whole of your part in it; the standing surface still waits for
the detached pass.

### Knowledge is what you would want recalled

In a session that has never seen this one — a fact about a system, a technique, a
constraint, a decision and why. Not status, not implementation minutiae version
control already holds.

### Universal scope binds every project

Every project consuming these plugins, not just this one. Claiming it needs
recurrence established across findings, never one salient incident.

### When a lesson looks like it spans two destinations

It is usually one lesson being described two ways, or two lessons travelling
together. Name the obligation the lesson actually creates: if there is one, route
it by that and let the supporting fact ride along in what you write. If there are
genuinely two — a durable fact _and_ a separate checkable obligation — they are
two lessons, and each goes through routing on its own. Never write the same
lesson to two surfaces to be safe: the second copy is the one that goes stale
without anyone noticing.
