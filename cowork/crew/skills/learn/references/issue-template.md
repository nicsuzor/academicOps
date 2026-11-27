---
name: Learn / Root-Cause Diagnosis
about: File a systemic root-cause diagnosis or verification miss from /learn
labels: ["bug", "triage"]
---

### Summary

<!-- 1-3 sentences: what failed at runtime and what observable symptom resulted. -->

### Execution Evidence

<!-- Grounded runtime evidence: OpenTelemetry span IDs, tool names, error payloads, HTTP status codes, or CLI exit codes. Strip all credentials, personal names, private paths, session IDs, private telemetry domains, and PKB IDs (aops_..., mem_..., task_...). -->

```text
<paste relevant logs / trace spans / tool error payloads here>
```

### Root Mechanism

<!-- The concrete contract, protocol, instruction, or state invariant breach that produced this failure class. Use active voice: name the actor, quote the governing instruction or workflow text that led them to act, and state the framework defect. Do not guess internal model states or speculate about unverified code. -->

### Verification Miss

<!-- The existing control (rule, axiom, test, lint, or review lens) that should have caught this failure class, and why it did not fire or pass. If no control exists, cite the exhaustive search conducted. -->

### Scope & Impact

- **Scope**: [Framework | Project | User/PKB]
- **Impact**: [Blocking | Degraded | Intermittent]
- **Classification**: [General Bug | Verification Miss / Handler Failure]
