---
trigger: always_on
description: Evidence Is Immutable and Irreplaceable
---

## Evidence Is Immutable and Irreplaceable {#evidence-immutable}

Source datasets, ground-truth labels, records, and any artifact serving as evidence for a claim are sacred: never modify, convert, reformat, "fix," or **substitute** them. If the primary source named in a task is unreachable, the work HALTS — summaries, derived reports, prior notes, or "the gist" are not acceptable substitutes for trace-level claims.

- **Evidence is sacred and immutable.** Where infrastructure cannot process the data as it exists, **the infrastructure is wrong, not the data** — halt and report the gap. Silently transforming evidence to match what tooling expects invalidates every downstream claim resting on it.
- **Substitution equals modification.** A generated, derived, or example stand-in is not the source: a deliverable that quotes an example output instead of the real trace it purports to describe is making things up, and a progress-log admission of substitution is a hard block on `done`, not progress.
- **Evidentiary scope must match data scope.** If the task says "extract from raw traces" and you read summaries, you have changed the scope — report the change in the task body before producing a deliverable, never silently downgrade and ship.
- _E.g._ "couldn't reach the source, used a derived summary instead" recorded in the log and then marked done is a HALT misreported as completion.

_Review: [[AXIOMS-REVIEW#evidence-immutable]]._
