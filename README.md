# academicOps Framework

Academic support framework for Claude Code. Minimal, fight bloat aggressively.

## Quick Start

- **Paths**: `FRAMEWORK.md` (injected at session start)
- **Principles**: `AXIOMS.md` (injected at session start)
- **File tree**: `INDEX.md`

## Glossary

| Term | Definition |
|------|------------|
| **Skill** | Workflow instructions in `skills/*/SKILL.md` - invoke via `Skill` tool |
| **Command** | User-invokable `/slash` command in `commands/` |
| **Hook** | Python script triggered by Claude Code events in `hooks/` |
| **Agent** | Spawnable subagent via `Task` tool (`subagent_type`) |

## Commands

| Command | Purpose | Invocation |
|---------|---------|------------|
| /meta | Strategic brain + executor | Slash command |
| /email | Extract action items from emails → tasks | Slash command |
| /bmem | Capture session info to knowledge base | Slash command |
| /log | Log patterns to thematic learning files | Slash command |
| /transcript | Generate session transcripts | Slash command |
| /task-viz | Task graph visualization (Excalidraw) | Slash command |
| /qa | Verify against acceptance criteria | Slash command |
| /ttd | TDD orchestration workflow | Slash command |
| /parallel-batch | Parallel file processing | Slash command |

## Skills

| Skill | Purpose | Invocation |
|-------|---------|------------|
| analyst | Research data analysis (dbt, stats) | `Skill(skill="analyst")` |
| bmem | Knowledge base operations | `Skill(skill="bmem")` or `/bmem` |
| framework | Convention reference, categorical imperative | `Skill(skill="framework")` |
| osb-drafting | IRAC analysis, citation verification | `Skill(skill="osb-drafting")` |
| pdf | Markdown → professional PDF | `Skill(skill="pdf")` |
| python-dev | Production Python (fail-fast, typed) | `Skill(skill="python-dev")` |
| tasks | Task management + email extraction | `Skill(skill="tasks")` or `/email` |
| transcript | Session JSONL → markdown | `Skill(skill="transcript")` |
| learning-log | Pattern logging to thematic files | `Skill(skill="learning-log")` |

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `sessionstart_load_axioms.py` | SessionStart | Inject AXIOMS.md, FRAMEWORK.md paths |
| `user_prompt_submit.py` | UserPromptSubmit | Context injection on every prompt |
| `prompt_router.py` | UserPromptSubmit | Keyword → skill suggestions |

## Agents

| Agent | Purpose | Invocation |
|-------|---------|------------|
| dev | Routes to python-dev skill | `Task(subagent_type="dev")` |
| Explore | Fast codebase exploration | `Task(subagent_type="Explore")` |
| Plan | Implementation planning | `Task(subagent_type="Plan")` |

## Testing

- **Unit tests**: `tests/` (270 tests, 98% pass)
- **Integration tests**: `tests/integration/` (require Claude CLI)
- **Run**: `uv run pytest tests/`

## Knowledge Base

**Always use `project="main"`** with all `mcp__bmem__*` tools.

## See Also

| Document | Purpose |
|----------|---------|
| AXIOMS.md | Principles (inviolable rules) |
| INDEX.md | Complete file tree |
| $ACA_DATA/projects/aops/VISION.md | What we're building |
| $ACA_DATA/projects/aops/ROADMAP.md | Current status |
