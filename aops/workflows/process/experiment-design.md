---
id: experiment-design
kind: process
category: general
description: Design, implement, and evaluate a discrete framework or process experiment before committing to it
requires: [task-tracking]
pairs-with: [verification]
conflicts: []
version: 1.0.0
permalink: workflows-process-experiment-design
---

# Process: Experiment Design

**When**: testing a new approach, optimization, or capability. Must be
well-designed, discrete, and evaluable — not sprawling.

## Steps

1. **Define hypothesis** — clear, testable statement; measurable success
   criteria; bounded scope.
2. **Design** — single variable changed; control and test conditions defined;
   evaluation method specified upfront, before results exist.
3. **Log the experiment** — hypothesis, success criteria, design, control,
   implementation, results, evaluation, decision, lessons — all in one durable
   record.
4. **Implement** — minimal required changes, all documented.
5. **Evaluate** — measure actual outcomes against the hypothesis (compose
   [[verification]]); document evidence objectively.
6. **Decide**: keep (success, no conflicts) | revert (failed, or conflicts) |
   iterate (only with a clear path to success).
7. **Clean up** — remove experimental code if reverting; update docs if
   keeping; archive the log with the final decision.
