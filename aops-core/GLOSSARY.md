# Framework Glossary

Quick definitions for framework-specific terminology. Used by hydrator to interpret user prompts without filesystem exploration.

> **Maintenance**: Update this file when adding major framework concepts. Run `Skill(skill="audit")` to regenerate indices including this glossary. If hydrator tries to search for a term, the glossary needs updating.

## Core Components

| Term | Definition |
|------|------------|
| **aops** | academicOps - the overall framework for academic workflow automation |
| **polecat** | Parallel worker system using git worktrees for isolated agent execution |
| **crew** | Script that sets up polecat worktrees; located at `scripts/crew` |
| **worktree** | Git worktree used by polecat workers for isolated file changes |
| **swarm** | Multiple polecat workers running in parallel |
| **task system** | Markdown-based task tracking with MCP tools (`mcp__plugin_aops-core_task_manager__*`) |
| **hydrator** | Agent that transforms terse prompts into execution plans (this context) |
| **custodiet** | Compliance-checking agent that enforces framework principles |
| **critic** | Agent that reviews plans before execution |
| **qa** | Quality assurance agent for end-to-end verification |

## Directories

| Term | Location |
|------|----------|
| **plugin root** | `~/.aops/aops-XXXXXXXX/aops-core/` - framework code |
| **skills/** | Skill definitions (markdown prompts) |
| **workflows/** | Workflow definitions |
| **agents/** | Agent specifications |
| **specs/** | Design documents and specifications |
| **hooks/** | Claude/Gemini hook scripts |
| **lib/** | Python library code |
| **scripts/** | Shell scripts (including `crew`, `polecat`) |

## Task Terminology

| Term | Definition |
|------|------------|
| **claim** | Mark a task as in_progress with assignee |
| **pull** | Get next ready task from queue and claim it |
| **decompose** | Break a task into subtasks |
| **leaf task** | Task with no children (directly executable) |
| **ready task** | Leaf task with all dependencies satisfied |
| **blocked task** | Task waiting on dependencies |

## Common User Phrases

| Phrase | Interpretation |
|--------|----------------|
| "kick off" / "trigger" | Activate existing automation (check workflows/CI first) |
| "claim a task" | Use `/pull` skill or `claim_next_task` |
| "what's next" | List ready tasks, recommend highest priority |
| "fix the bug in X" | Locate, understand, and fix - create task first |
| "run the tests" | Execute test suite for current project |
| "commit this" | Use `/commit` skill |

## Workflow References

| Term | File |
|------|------|
| **simple-question** | `workflows/simple-question.md` - pure info requests |
| **direct-skill** | `workflows/direct-skill.md` - skill invocation |
| **interactive-followup** | `workflows/interactive-followup.md` - session continuations |
| **code-authoring** | `workflows/code-authoring.md` - writing code |
| **framework** | `workflows/framework.md` - framework changes |

## Agent Types (for Task tool)

| Type | Purpose |
|------|---------|
| `Explore` | Codebase exploration and search |
| `Plan` | Software architecture planning |
| `aops-butler` | Framework coordination and STATUS updates |
| `aops-core:prompt-hydrator` | Transform prompts (internal) |
| `aops-core:critic` | Plan review |
| `aops-core:qa` | End-to-end verification |

## Key Principles (by ID)

| ID | Name | Summary |
|----|------|---------|
| P#3 | Don't Make Shit Up | Verify before acting; don't fabricate |
| P#5 | Do One Thing | Focus; don't over-engineer |
| P#8 | Fail Fast | Explicit errors over silent failure |
| P#26 | Verify First | Understand existing state before changing |
| P#58 | Indices Before Exploration | Use curated indices, not raw filesystem |
