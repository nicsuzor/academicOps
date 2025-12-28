---
name: supervisor
description: Generic supervisor orchestrating multi-agent workflows with quality gates,
  acceptance criteria lock, and scope drift detection. Loads workflow templates to
  parameterize behavior for different domains (TDD, batch review, audits, etc.).
permalink: aops/skills/supervisor
allowed-tools:
  - Task
  - Skill
  - TodoWrite
  - AskUserQuestion
---


## WORKFLOW LOADING (First Step)

**On invocation**, parse `$ARGUMENTS` to determine workflow:

1. **Extract workflow name**: First word of arguments (e.g., "tdd", "batch-review", "skill-audit")
2. **Load workflow template**: Spawn Explore agent to read `workflows/{name}.md`
3. **Extract from template**:
   - `required-skills`: Skills subagents MUST invoke before domain work
   - `scope`: What this workflow handles
   - `iteration-unit`: What constitutes ONE cycle
   - `quality-gate`: Domain-specific validation
   - `subagent-prompts`: Templates for spawning workers
4. **Apply template**: Use extracted content in generic phases below

#### 0.1 Load Workflow Template

```
Task(subagent_type="Explore", prompt="
Read the workflow template at skills/supervisor/workflows/{workflow-name}.md

Extract and report:
1. required-skills list
2. scope definition
3. iteration-unit definition
4. quality-gate checklist
5. subagent-prompts for this workflow
")
```

**If workflow not found**:
```
AskUserQuestion(questions=[{
  "question": "Which workflow do you want to use?",
  "header": "Workflow",
  "options": [
    {"label": "tdd", "description": "Test-first development with pytest"},
    {"label": "batch-review", "description": "Parallel batch processing with quality gates"},
    {"label": "skill-audit", "description": "Review skills for content separation"}
  ],
  "multiSelect": false
}])
```

**Available workflows**: See `workflows/` directory for all templates.

---

---

## Available Workflows

Load from `workflows/` directory:

- [[workflows/tdd.md]] - Test-first development with pytest
- [[workflows/batch-review.md]] - Parallel batch processing with quality gates
- [[workflows/skill-audit.md]] - Review skills for content separation

To add a new workflow: Create `workflows/{name}.md` following the template format.
