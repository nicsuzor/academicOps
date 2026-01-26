---
id: framework-gate
category: routing
bases: []
---

# Framework Gate

**Check FIRST before any other routing.** Detects framework modification intent and routes appropriately.

## Routing Signals

Framework modification intent detected via prompt content (NOT file paths). Watch for:

- **Explicit mentions**: "aops/", "framework", "hydrator", "hooks", "skills", "workflows", "enforcement"
- **Component names**: "prompt-hydrator", "custodiet", "critic", "policy_enforcer"
- **Governance files**: "AXIOMS", "HEURISTICS", "enforcement-map", "settings.json"
- **Framework concepts**: "add a rule", "update the workflow", "change the spec"

## Routing Rules

| Intent | Route to | Rationale |
|--------|----------|-----------|
| Governance changes (AXIOMS, HEURISTICS, enforcement-map, hooks, deny rules) | `[[framework-change]]` | Requires structured justification and escalation |
| Framework code (specs, workflows, agents, skills, scripts) | `[[design]]` + spec review | Framework code is shared infrastructure |
| Framework debugging | `[[debugging]]` + framework context | Still needs spec awareness |

## Framework Context Output

For ANY framework modification, output:

```markdown
### Framework Change Context

**Component**: [which framework component is being modified]
**Spec**: [relevant spec file, e.g., specs/workflow-system-spec.md]
**Indices**: [which indices need updating: WORKFLOWS.md, SKILLS.md, enforcement-map.md, etc.]
**Governance level**: [governance (AXIOMS/HEURISTICS/hooks) | code (specs/workflows/skills)]
```

## Critical Rule

Framework work MUST go through the appropriate workflow. Never route framework changes to `[[simple-question]]` regardless of apparent simplicity.
