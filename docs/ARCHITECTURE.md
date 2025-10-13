# academicOps Architecture

## Document Loading Hierarchy

All agents follow this strict loading sequence:

1. **CLAUDE.md** (${OUTER}/CLAUDE.md)
   - Entry point read by Claude Code CLI
   - Single line: "Read `bot/README.md` and `docs/INSTRUCTIONS.md` IMMEDIATELY."
   - Exists in parent repo (PRIVATE)

2. **bot/agents/INSTRUCTIONS.md** (PUBLIC)
   - Generic agent rules applicable to ANY user
   - Core axioms, fail-fast philosophy, critical constraints
   - Token-optimized (must be read on EVERY session)
   - Loaded via validate_env.py hook

3. **docs/agents/INSTRUCTIONS.md** (PRIVATE)
   - User-specific context (Nic's workflow, repos, structure)
   - Project names, paths, accommodations
   - Loaded via validate_env.py hook

4. **Agent-Specific Instructions** (bot/agents/{name}.md)
   - Loaded when specific agent is invoked
   - Inherits all rules from layers 1-3

## Enforcement Mechanism

**SessionStart Hook** (.claude/settings.json):

- Runs `bot/scripts/validate_env.py` at session start
- Script injects both instruction files as `additionalContext`
- Agents MUST read these before any tool use

**PreToolUse Hook**:

- Validates agent permissions via `bot/scripts/validate_tool.py`
- Blocks unauthorized tool use based on agent configuration
- Enforces write restrictions, mode compliance
- Enforces Axiom #5 (documentation-as-code): blocks .md file creation except for:
  - Research papers (papers/, manuscripts/)
  - Agent instructions (bot/agents/)
  - Trainer agent override (can create any .md if truly needed)

## Repository Structure

## Repository Structure

```
${OUTER}/                          # Parent repo (PRIVATE)
├── CLAUDE.md                      # Entry point (1 line)
├── bot/                           # academicOps submodule (PUBLIC on GitHub)
│   ├── agents/
│   │   ├── INSTRUCTIONS.md        # Generic rules (PUBLIC)
│   │   ├── trainer.md             # Agent definitions
│   │   └── ...
│   ├── scripts/                   # Public tools
│   └── docs/                      # Documentation (legacy files)
│       └── ...
├── docs/
│   └── agents/
│       └── INSTRUCTIONS.md        # User-specific context (PRIVATE)
├── projects/                      # Submodules
│   ├── buttermilk/               # Shared dependency
│   │   ├── docs/agents/            # Project specific automation instructions
│   │   └── ...
│   ├── zotmcp/
│   │   ├── docs/agents/            # Project specific automation instructions
│   │   └── ...
│   └── ...
├── .claude/                        # Claude Code instructions
│   ├── settings.json              # Hook configuration
|   └── agents/*.md                # Agent permissions
└── .gemini/                        # Gemini CLI instructions
```

## Design Principles

1. **Data Boundaries**: bot/ = PUBLIC (GitHub), everything else = PRIVATE
2. **Project Isolation**: Projects work independently, no cross-dependencies
3. **Fail-Fast**: No fallbacks, no defensive programming, immediate halts on errors
4. **Configuration-Based Enforcement**: Use hooks, not prompts, to enforce rules
5. **Token Efficiency**: Core instructions read every session must be minimal

## Permission System

**Agent Types by Tool Access**:

- **Trainer**: Read, Write (bot/), Edit, Bash (git/gh), WebFetch, WebSearch, TodoWrite
- **Developer**: Full access (all tools, all paths)
- **Strategist**: Full access including MCP tools
- **Mentor**: Read-only (Read, Grep, Glob)
- **Academic Writer**: Read, Write (manuscripts), MCP (Zotero, OSB)
- **Documenter**: Read, Write (docs/), Edit, Bash, WebFetch

## Path Resolution

Use absolute paths starting from ${OUTER}:

- Production: `/home/nic/src/writing/`
- All paths must be absolute, never relative

## Hook Flow

```
Session Start
    ↓
validate_env.py runs
    ↓
Injects bot/agents/INSTRUCTIONS.md (generic)
Injects docs/agents/INSTRUCTIONS.md (user-specific)
    ↓
Agent loaded with full context
    ↓
User prompt → Tool use attempt
    ↓
validate_tool.py checks permissions
    ↓
Allow (exit 0) or Block (exit 2)
```

## Key Files

- `.claude/settings.json`: Hook configuration, global permissions
- `.claude/agents/*.md`: Agent-specific tool allowlists
- `bot/agents/INSTRUCTIONS.md`: Generic rules (PUBLIC)
- `docs/agents/INSTRUCTIONS.md`: User context (PRIVATE)
- `bot/README.md`: Agent framework overview
- `docs/INSTRUCTIONS.md`: Legacy (being phased out)

## Related Issues

- #84: Configuration-based instruction enforcement
- #93: Agent detection in validate_tool.py
