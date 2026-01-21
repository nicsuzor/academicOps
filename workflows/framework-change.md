---
id: framework-change
category: governance
---

# Framework Change Workflow

Structured workflow for modifying framework governance files. Requires explicit justification with escalation routing based on severity.

## When to Use

Any modification to:
- AXIOMS.md (hard rules)
- HEURISTICS.md (soft guidance)
- enforcement-map.md (enforcement wiring)
- hooks/*.py (blocking/detection mechanisms)
- settings.json deny rules

## When NOT to Use

- User data files ($ACA_DATA)
- Session artifacts
- Task updates
- Non-governance code changes

## Scope Signals

| Signal | Indicates |
|--------|-----------|
| Modifying AXIOMS/HEURISTICS/enforcement | Framework change |
| Adding new principle or heuristic | Framework change |
| Regular code/data change | Standard workflow |

## Key Steps

1. **Load context**: Read AXIOMS.md, HEURISTICS.md, enforcement-map.md
2. **Search prior art**: Check for existing patterns
3. **Emit structured justification**: Scope, rules loaded, prior art, intervention type
4. **Route for approval**: Auto/critic/custodiet/human based on severity
5. **Checkpoint**: Wait for approval
6. **Make change**: Exact content from justification
7. **Update enforcement-map.md**
8. **Commit with justification reference**

## Escalation Matrix

| Change Type | Escalation |
|-------------|------------|
| Corollary to existing | auto |
| New heuristic | critic |
| New axiom | human |
| Enforcement hook | critic |
| Deny rule | human |

## Quality Gates

- All governance files read before starting
- Prior art search completed
- Structured justification emitted
- Appropriate approval obtained
- Change matches justification exactly
- enforcement-map.md updated
