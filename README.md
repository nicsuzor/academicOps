# academicOps Framework

Minimal LLM agent automation for Claude Code. Fight bloat aggressively.

## Quick Start

- **Paths**: See `FRAMEWORK.md` (injected at session start)
- **Principles**: See `AXIOMS.md` (injected at session start)
- **Full file tree**: See `INDEX.md`

## Glossary

| Term | Definition |
|------|------------|
| **Skill** | Workflow instructions in `skills/*/SKILL.md` that agents read |
| **Command** | User-invokable `/slash` command in `commands/` |
| **Hook** | Python script triggered by Claude Code events in `hooks/` |
| **Agent** | Spawnable subagent via Task tool (`subagent_type`) |
| **Workflow** | Step-by-step procedure within a skill |
| **Script** | Executable Python file within a skill |
| **Spec** | Formal design document in `$ACA_DATA/projects/aops/specs/` |

## Commands

| Command | Purpose |
|---------|---------|
| /meta | Strategic brain + executor. Design, build, verify end-to-end. |
| /archive-extract | Extract archived info to bmem knowledge base. |
| /bmem | Capture session info to knowledge base. |
| /bmem-validate | Parallel bmem file validation. |
| /docs-update | Update README + INDEX documentation. |
| /email | Extract action items from emails to tasks. |
| /learn | Minor instruction adjustments for future agents. |
| /log | Log patterns to thematic files via learning-log skill. |
| /parallel-batch | Parallel file processing with subagents. |
| /qa | Quality assurance verification against acceptance criteria. |
| /strategy | Strategic planning. |
| /task-viz | Task graph visualization. |
| /transcript | Generate session transcripts (full + abridged). |
| /ttd | TDD orchestration workflow. |

## Skills

| Skill | Purpose |
|-------|---------|
| analyst | Data analysis (dbt, Streamlit, stats). |
| bmem | Knowledge base operations (project="main"). |
| dashboard | Live task dashboard (Streamlit). |
| docs-update | README + INDEX maintenance. |
| excalidraw | Visual diagram generation. |
| extractor | Archive → bmem extraction. |
| feature-dev | Feature development templates. |
| framework | Convention reference before modifying infrastructure. |
| framework-debug | Framework debugging. |
| learning-log | Pattern logging to thematic bmem files. |
| pdf | Markdown → PDF with academic formatting. |
| python-dev | Production Python (fail-fast, type safety). |
| skill-creator | Skill packaging and creation. |
| tasks | Task management via MCP server. |
| training-set-builder | Training data extraction. |
| transcript | Session JSONL → markdown (full + abridged). |

## Hooks

Session lifecycle automation (Python scripts in `hooks/`):
- `sessionstart_load_axioms.py` - Injects AXIOMS.md at session start
- `user_prompt_submit.py` - Context injection on every prompt
- `prompt_router.py` - Keyword analysis → skill suggestions

See INDEX.md for complete hook list.

## Agents

Spawnable subagents (Task tool with subagent_type):
- `dev` - Routes to python-dev skill
- `bmem-validator` - Parallel bmem file validation
- `email-extractor` - Email archive processing

## Knowledge Base (bmem)

**Always use `project="main"`** with all `mcp__bmem__*` tools.

Location: `$ACA_DATA` (single knowledge base, shared across projects).

## See Also

- **AXIOMS.md** - Framework principles (inviolable rules)
- **INDEX.md** - Complete file tree with annotations
- **docs/OBSERVABILITY.md** - Session logging, hooks, dashboard data sources
- **docs/JIT-INJECTION.md** - How agents receive context (hooks, triggers, files loaded)
- **$ACA_DATA/projects/aops/VISION.md** - End state vision
- **$ACA_DATA/projects/aops/ROADMAP.md** - Maturity stages
