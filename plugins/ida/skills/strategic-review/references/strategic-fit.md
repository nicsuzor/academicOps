# Strategic-Fit Review Reference

The Strategic-Fit Review role (executed by `pauli`) evaluates whether candidate artifacts, specifications, architecture proposals, or pull requests strategically belong in the system before detailed compliance or quality is examined.

## Review Duties

1. **Objective Alignment**:
   - Trace the deliverable to the claimed parent task or target node in the PKB graph.
   - Verify that the scope directly advances the parent objective without unrequested scope drift or mission creep.
2. **Parsimony and Necessity**:
   - Assess whether the proposed mechanism is necessary at all.
   - Check if an existing framework tool, native platform mechanism, or active competing pull request (e.g. #1919 vs #1920) already satisfies the underlying need more simply.
   - Recommend reverting or closing redundant or oversized proposals.
3. **Cross-Task Lifecycle Coherence**:
   - Examine task graph dependencies (`depends_on`, `needs`) and lifecycle transition states.
   - Detect deadlocks (e.g. downstream tasks blocked by contradictory release states).
4. **Verdict**:
   - Render an explicit `FIT` or `MISFIT` verdict. A `MISFIT` must cite the specific objective misalignment, redundant machinery, competing proposal, or lifecycle deadlock.

## Non-Overlapping Boundaries

Operate strictly within strategic alignment and lifecycle coherence:

- **Do not inspect source code for axiom violations or write mechanisms analysis**: Evaluating whether code delegates qualitative judgment or introduces silent fallback branches belongs exclusively to Rule Compliance (`rbg`).
- **Do not execute runtime tests, run test suites, or write scratch probe scripts**: All runtime execution, test suite verification, and live probes belong exclusively to QA (`marsha`).
