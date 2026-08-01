**Rule check before you stop.** This session is not finished until its compliance
has been checked against the rules that govern it, and that check has produced
evidence somebody else can verify. Do it now, then stop again.

**Run the check.** Invoke the `rbg` rule checker over the work of this session,
against all three layers in order: the shipped `axioms/` (the floor, inviolable),
this project's `.agents/rules/`, and your own `$ACA_DATA/.agents/rules/`. Later
layers add obligations; none of them weakens an axiom. If your surface cannot
reach `rbg`, apply the same three layers yourself and say that you did so
unassisted.

**Cite what makes each finding checkable** — the file and line, the command and
its exit code, the output you read. "Followed the rules", "all checks pass" and
"verified" are claims, and a claim is what this check exists to replace.

**Name every violation you find, including the ones you are not going to fix.**
A violation stated with its reason is a finding; a violation smoothed over is a
defect this check was supposed to catch. If a rule could not be checked, say
which rule and why — an unchecked rule is not a rule that passed.

**The check annotates your answer; it never replaces it.** What you were handing
back is still what you hand back.
