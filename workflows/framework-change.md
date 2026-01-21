---
id: framework-change
category: governance
---

# Framework Change Workflow

## Overview

Structured workflow for modifying framework governance files. Requires explicit justification before changes, with escalation routing based on change severity.

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

## Steps

### 1. Load context (MANDATORY)

Before any framework change, read the governance files:

```
Read AXIOMS.md
Read HEURISTICS.md
Read enforcement-map.md
```

Note which principles and heuristics are relevant to your change. You cannot proceed without this step.

### 2. Search prior art

Search for existing patterns and related tasks:

```
mcp__plugin_aops-core_tasks__search_tasks(query="[keywords related to your change]")
```

Check if:
- This pattern already exists (don't reinvent)
- Prior attempts failed (learn from them)
- Related enforcement exists (extend vs create new)

### 3. Emit Structured Justification

**MANDATORY**: Output this exact format before making any edit:

```yaml
## Rule Change Justification

**Scope**: [AXIOMS.md | HEURISTICS.md | enforcement-map.md | hooks/*.py | settings.json]

**Rules Loaded**:
- AXIOMS.md: [P#X, P#Y - or "not relevant"]
- HEURISTICS.md: [H#X, H#Y - or "not relevant"]
- enforcement-map.md: [enforcement entry name - or "not relevant"]

**Prior Art**:
- Search query: "[keywords used in task search]"
- Related tasks: [task IDs found, or "none"]
- Pattern: [existing pattern | novel pattern]

**Intervention**:
- Type: [corollary to P#X | new axiom | new heuristic | enforcement hook | deny rule]
- Level: [1a | 1b | 1c | 1d | 2 | 3a | 3b | 4 | 5 | 6 | 7]
- Change: [exact content, max 3 sentences]

**Minimality**:
- Why not lower level: [explanation]
- Why not narrower scope: [explanation]

**Spec Location**: [specs/enforcement.md | task body | N/A]

**Escalation**: [auto | critic | custodiet | human]
```

### 4. Route for approval

Based on the **Escalation** field:

| Escalation | Action |
|------------|--------|
| `auto` | Proceed immediately (corollaries only) |
| `critic` | `Task(subagent_type="critic", prompt="Review this rule change justification: [paste block]")` |
| `custodiet` | `Task(subagent_type="custodiet", prompt="Validate this enforcement change: [paste block]")` |
| `human` | `AskUserQuestion(question="Approve this framework change?", options=[...])` |

**Escalation Matrix**:

| Change Type | Default Escalation |
|-------------|-------------------|
| Corollary to existing axiom/heuristic | auto |
| New heuristic (soft guidance) | critic |
| New axiom (hard rule) | human |
| Enforcement hook (Level 4-5) | critic |
| Deny rule (Level 6) | human |
| settings.json modification | human |

### 5. CHECKPOINT: Approval received

Do NOT proceed until approval is obtained:
- `auto`: Self-approved, proceed
- `critic`: Critic returns PROCEED
- `custodiet`: Custodiet returns OK
- `human`: User confirms

If rejected: revise justification and re-submit, or abandon the change.

### 6. Make the change

Now execute the edit. Keep it minimal:
- Exact content from justification
- No scope creep
- No "while I'm here" additions

### 7. Update enforcement-map.md

Per [[enforcement-changes-require-rules-md-update]], add an entry:

```markdown
| [[new-rule-name]] | New Rule Name | [enforcement mechanism] | [enforcement point] | [level] |
```

### 8. Document in spec (if applicable)

If **Spec Location** was not "N/A", write the justification rationale to the appropriate spec file.

### 9. Commit with justification reference

```bash
git add -A
git commit -m "enforce: [brief description]

Justification: [paste structured justification block]

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Anti-patterns

**Fabricating Rules Loaded**: Claiming to have read files without actually reading them. Custodiet can spot-check relevance.

**Copy-paste boilerplate**: Using the same justification for different changes. Each change needs genuine reasoning.

**Escalation gaming**: Choosing "auto" to avoid review when change is significant. The escalation matrix is mandatory.

**Scope creep during edit**: Adding more changes than justified. Stick to exact content from justification.

## Success Metrics

- [ ] All three governance files read before starting
- [ ] Prior art search completed
- [ ] Structured justification emitted
- [ ] Appropriate approval obtained
- [ ] Change matches justification exactly
- [ ] enforcement-map.md updated
- [ ] Committed with justification reference
