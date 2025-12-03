# academicOps Framework

Minimal LLM agent automation for Claude Code. Fight bloat aggressively.

## Paths (DO NOT GUESS - use these exact paths)

| Variable | Resolves To | Purpose |
|----------|-------------|---------|
| `$AOPS` | `/home/nic/src/aOps` | Framework source (SSoT for all framework files) |
| `$ACA_DATA` | `/home/nic/writing` | User data (tasks, sessions, knowledge base) |
| `~/.claude/` | symlinks → `$AOPS` | Runtime directory (DO NOT edit here) |

**To edit framework files**: Always edit in `$AOPS/`, never in `~/.claude/` symlinks.

| Component | Edit Location | Symlinked From |
|-----------|---------------|----------------|
| Commands | `$AOPS/commands/` | `~/.claude/commands/` |
| Skills | `$AOPS/skills/` | `~/.claude/skills/` |
| Hooks | `$AOPS/hooks/` | `~/.claude/hooks/` |
| Agents | `$AOPS/agents/` | `~/.claude/agents/` |

## Commands

| Command | Purpose |
|---------|---------|
| /meta | Strategic brain + executor. Design, build, verify end-to-end. |
| /advocate | Reactive verification. "Prove it actually worked." |
| /log | Log patterns to thematic files via learning-log skill. |
| /transcript | Generate session transcripts (full + abridged). |
| /bmem | Capture session info to knowledge base. |
| /email | Extract action items from emails to tasks. |
| /learn | Minor instruction adjustments for future agents. |
| /qa | Quality assurance verification against acceptance criteria. |
| /ttd | TDD orchestration workflow. |
| /parallel-batch | Parallel file processing with subagents. |

## Skills

| Skill | Purpose |
|-------|---------|
| framework | Convention reference before modifying infrastructure. |
| python-dev | Production Python (fail-fast, type safety). |
| learning-log | Pattern logging to thematic bmem files. |
| transcript | Session JSONL → markdown (full + abridged). |
| analyst | Data analysis (dbt, Streamlit, stats). |
| bmem | Knowledge base operations (project="main"). |
| pdf | Markdown → PDF with academic formatting. |
| tasks | Task management via MCP server. |

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
- **$ACA_DATA/projects/aops/VISION.md** - End state vision
- **$ACA_DATA/projects/aops/ROADMAP.md** - Maturity stages
