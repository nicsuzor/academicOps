**Rule check before you stop.** This session is not finished until its compliance
has been checked against the rules that govern it, and that check has produced
evidence somebody else can verify. Do it now, then stop again.

**Run the check.** Invoke the `rbg` rule checker over the work of this session,
against all three layers in order: the shipped `axioms/` (the floor, inviolable),
this project's `.agents/rules/`, and your own `$ACA_DATA/.agents/rules/`. Later
layers add obligations; none of them weakens an axiom. If your surface cannot
reach `rbg`, apply the same three layers yourself and say that you did so
unassisted.

**Present checkable evidence, not a claim of compliance.** For every rule that
bears on what you did, cite what makes it checkable: the file and line, the
command and its exit code, the output you read. "Followed the rules", "all
checks pass", and "verified" are claims, and a claim is what this check exists
to replace.

- **Observed** — you watched it happen this turn. Cite the thing you watched.
- **Reported** — a tool, subagent, or document said so. Name the source and say
  whether you checked it yourself.
- **"Fixed", "works", "passing"** require the originally-failing behaviour
  observed passing. Until then the honest register is "changed, unverified".

**Name every violation you find, including the ones you are not going to fix.**
A violation stated with its reason is a finding; a violation smoothed over is a
defect this check was supposed to catch. If a rule could not be checked, say
which rule and why — an unchecked rule is not a rule that passed.

**Your response must still be the answer.** If the work you were about to hand
back has been displaced by commentary about this check, you are not finished:
re-output it in full, annotated with what the check found.
