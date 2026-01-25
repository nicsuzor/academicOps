# Design Workflow

Specification and planning for known work.

Extends: base-task-tracking

## When to Use

Use this workflow when:
- "Add feature X" but requirements are unclear
- Complex modifications need architecture decisions
- Asking "how should we build this?"

Do NOT use for:
- Uncertain path (use decompose first)
- Simple bugs (use debugging)

## Constraints

### Spec Requirement

- Before creating a plan, verify that a spec exists (user stories, acceptance criteria)
- If no spec exists, create a SPEC task first that blocks implementation

### Design Sequencing

1. **Acceptance criteria** must be defined before creating a plan
2. **Plan** must exist before implementation
3. **Critic must review** before implementation begins

### Critic Gates

- If critic says PROCEED → proceed to implementation
- If critic says REVISE → revise the plan
- If critic says HALT → halt and report to user

### Exit Routing

After design is approved, route to the appropriate implementation workflow:
- For general code → use base-tdd
- For Python code → use python-dev skill
- For framework code → use framework skill

## Triggers

- When design request arrives → verify spec exists
- When spec is verified → define acceptance criteria
- When acceptance criteria are defined → create plan
- When plan is created → invoke critic review
- When critic says PROCEED → proceed to implementation
- When critic says REVISE → revise the plan
- When critic says HALT → halt and report

## How to Check

- Spec verified: spec document exists with user stories and acceptance criteria
- No spec: spec does not exist
- Acceptance criteria defined: task body contains "## Acceptance Criteria" with measurable items
- Plan exists: task body contains "## Implementation Plan"
- Critic reviewed: critic agent was spawned and returned a verdict
- Critic proceeds: critic verdict is "PROCEED"
- Critic revises: critic verdict is "REVISE"
- Critic halts: critic verdict is "HALT"
- General code: implementation is general purpose code
- Python code: implementation is Python-specific
- Framework code: implementation modifies framework components
