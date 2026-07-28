---
description: Never modify or substitute a source serving as evidence; if the primary source is unreachable, halt.
trigger: always_on
---

## Evidence Is Immutable and Irreplaceable

Source datasets, ground-truth labels, records, traces, and any artifact serving as evidence for a claim are never modified, converted, reformatted, "fixed", or substituted. If the primary source named in a task is unreachable, the work halts.

- **Substitution is modification.** A summary, a derived report, a prior note, "the gist", a mock, a synthetic sample, or an example output is not the source. A claim verified against a stand-in is only a claim about the stand-in.
- **Where infrastructure cannot process the data as it exists, the infrastructure is wrong.** Halt and report the gap. Silently transforming evidence to match what tooling expects invalidates every claim resting on it.
- **Evidentiary scope must match the scope requested.** If the task says raw traces and you read summaries, you have changed the scope — report the change before producing a deliverable.

Recording "couldn't reach the source, used a summary instead" in the log and then marking the task done is a halt misreported as completion.
