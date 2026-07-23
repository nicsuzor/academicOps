# reflexes-cope

Optional plugin package for academicOps containing the Reflexes/CoPE safety harness policy definitions, evaluator hook, and derived CoPE rule files.

## Architecture & Advisory Contract

Per v0.5 topology rules, `reflexes-cope` operates under an advisory-only contract:
- Policy evaluator output is an overridable advisory consumed by a deciding agent.
- No autonomous deny or blocking verdicts are produced.
- Strict fail-open resilience on evaluator outage or exception.
