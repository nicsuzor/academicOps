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

## Choosing

**Task scope is the default home.** An instruction phrased for the work in front
of you — "for this task", "this session", "while we're doing this" — is task
scope even when it reads like a rule, and promotion to a standing surface needs
its own explicit ruling, never inference from "this seems like a rule". Writing a
session-bound preference into a repo-wide standing surface is the characteristic
failure this taxonomy exists to prevent: every future worker on the repo then
reads it as binding law.

**A project rule earns its place** only if a reviewer could name the breach from
a diff, and it does not already follow from an axiom. If it cannot be checked, it
is knowledge, not a rule.

**Do not legislate from the case in front of you.** A standing rule needs a
warrant beyond the incident that prompted it: either the user asked for a rule,
or the same failure is established across several recorded findings. One salient
incident, however clear it feels from inside the review, is not a warrant — and
the clarity is the tell, not the evidence. Absent a warrant, the lesson is task
scope or knowledge, and it goes there.

**Knowledge is what you would want recalled** in a session that has never seen
this one — a fact about a system, a technique, a constraint, a decision and why.
Not status, not implementation minutiae version control already holds.

**Universal scope binds every project** consuming these plugins. Claiming it
requires evidence of recurrence across findings, not one salient incident.

## The gate on universal-scope destinations

Framework source and the framework's issue tracker are writable only from inside
the framework's own source tree. Test it: the tree has both `lib/axioms/` and
`build/marketplace.toml`. If either is missing, you are in a consuming project and
those two destinations are closed to you.

**When gated out, degrade — never drop, and never redirect to a surface you have
no standing to write.** Record the lesson as a tracked improvement task tagged
`framework-gap`, carrying the diagnosis, the evidence, and the destination it was
headed for. Raise it as an issue on the framework repository only when the user
asks. A lesson written to the wrong destination because the right one was closed
is worse than one parked where someone can find it.
