# reflexes-cope

Optional plugin package for academicOps containing the Reflexes/CoPE safety harness policy definitions, evaluator hook, and derived CoPE rule files.

## Architecture & Advisory Contract

Per v0.5 topology rules, `reflexes-cope` operates under an advisory-only contract:
- Policy evaluator output is an overridable advisory consumed by a deciding agent.
- No autonomous deny or blocking verdicts are produced.
- Strict fail-open resilience on evaluator outage or exception.

## Installation & Quickstart

`reflexes-cope` is an optional plugin for axiom-derived policy assembly and advisory evaluation.

### Claude Code

Install from the `academicOps` marketplace:

```bash
claude plugin install reflexes-cope@academicOps
```

### Antigravity (`agy`)

Install from local build:

```bash
agy plugin install ./dist/reflexes-cope-antigravity
```

## Contents

- [`reflexes/`](reflexes/) — axiom policy definitions (`policies/*.md`) and policy loader configuration.
- [`hooks/`](hooks/) — advisory policy evaluator gate and gate dispatch launcher.
- [`specs/`](specs/) — design specification (`reflexes-integration.md`).
