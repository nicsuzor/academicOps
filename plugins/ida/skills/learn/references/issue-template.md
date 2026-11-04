### Summary

<!-- 1-3 sentences: what failed at runtime and what observable symptom resulted. -->

### Execution Evidence

<!-- Grounded runtime evidence: Phoenix OTel span IDs, tool names, error payloads, HTTP status codes, or CLI exit codes. Strip all credentials, personal names, private paths, session IDs, private telemetry domains (*.suzor.com), and PKB IDs (aops_..., mem_..., task_...). -->

```
<paste relevant logs / trace spans / tool error payloads here>
```

### Root Mechanism

<!-- The concrete contract, protocol, or state invariant breach that produced this failure class. Focus on mechanism; do not guess internal model states or speculate about unverified code. -->

### Verification Miss

<!-- The existing control (rule, axiom, test, lint, or review lens) that should have caught this failure class, and why it did not fire or pass. If no control exists, cite the exhaustive search conducted. -->

### Scope & Impact

- **Scope**: [Framework | Project | User/PKB]
- **Impact**: [Blocking | Degraded | Intermittent]
- **Classification**: [General Bug | Verification Miss / Handler Failure]
