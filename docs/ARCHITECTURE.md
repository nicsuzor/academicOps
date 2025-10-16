# academicOps Architecture

## Core Concept: Framework vs Personalization

**academicOps** provides a PUBLIC framework for AI-assisted academic work. This framework is designed to be:
- **Generic**: Works for any researcher using these tools
- **Modular**: Components can be adopted independently
- **Hierarchical**: Instructions layer from generic to specific

**Your personalized setup** uses academicOps as infrastructure but prioritizes YOUR work:
- academicOps is a TOOL, not the primary focus
- Framework development happens when needed, not by default
- User-specific strategic needs ALWAYS take priority over framework issues

## The Golden Path: Single Activation Pattern

**ONE way to activate agents across all contexts:**

```bash
# In any repository (writing, buttermilk, automod, etc.)
claude code @agent-{name}
```

This works consistently because:
1. SessionStart hook loads foundational context automatically
2. Agent-specific instructions loaded on `@agent-{name}` invocation
3. Project-specific context discovered when accessing files in that directory

**No multiple invocation methods. No confusion. One golden path.**

## Document Loading Hierarchy

All agents follow this strict loading sequence:

### Layer 1: Foundational Context (Automatic)

Loaded via SessionStart hook (`validate_env.py`) at every session start:

1. **bot/agents/INSTRUCTIONS.md** (PUBLIC)
   - Generic agent rules applicable to ANY user
   - Core axioms, fail-fast philosophy, critical constraints
   - Token-optimized (must be read on EVERY session)

2. **docs/agents/INSTRUCTIONS.md** (PRIVATE)
   - User-specific context (workflow, repos, structure, accommodations)
   - Project names, paths, strategic priorities
   - **Priority context**: What the user actually cares about

**CRITICAL PRIORITY ORDER**: User-specific needs (Layer 1.2) must be emphasized over generic framework rules (Layer 1.1) in startup context.

### Layer 2: Agent-Specific Instructions (On-Demand)

3. **bot/agents/{NAME}.md** or **.claude/agents/{name}.md**
   - Loaded when specific agent is invoked via `@agent-{name}`
   - Inherits all rules from Layer 1
   - Adds specialized behaviors for that agent type

### Layer 3: Project-Specific Instructions (Discovery)

4. **projects/{name}/CLAUDE.md** (Project context)
   - Discovered automatically when accessing files in that directory
   - Loaded on-demand, not at session start
   - Claude Code searches UP to parent directories and DOWN to subdirectories
   - Contains project-specific rules, workflows, constraints

### Layer 4: Nested Directory Instructions (Discovery)

5. **projects/{name}/subdir/CLAUDE.md** (Deep context)
   - Discovered when working in deeply nested directories
   - Example: `papers/automod/tja/CLAUDE.md` for TJA evaluation work
   - Most specific context, closest to actual files being edited

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

## LLM Client Instruction Loading Behavior

Understanding how different LLM clients load instructions is critical for architecture decisions.

### Claude Code CLI

**Instruction Discovery:**
- **CLAUDE.md files**: Discovered automatically when accessing files in directories
  - Searches UP to parent directories (at session start)
  - Searches DOWN to subdirectories (on-demand when accessing files)
- **Agent files**: Loaded via `@agent-{name}` syntax
- **SessionStart hook**: Runs `validate_env.py` to inject foundational context

**Working Directory Behavior:**
- CWD resets between Bash calls (absolute paths required in scripts)
- File access triggers directory-specific CLAUDE.md discovery
- Project context loaded lazily, not eagerly

**Configuration:**
- `.claude/settings.json`: Project-level settings (in git)
- `.claude/settings.local.json`: User-level overrides (gitignored)
- `~/.claude/settings.json`: Global user settings (DO NOT EDIT)

### Gemini CLI

**Instruction Discovery:**
- `.gemini/` directory structure similar to `.claude/`
- Different hook execution model (TBD: needs research)
- Configuration precedence hierarchy (7 levels)

**Configuration:**
- `.gemini/settings.json`: Project settings
- Environment variables override settings
- Sandboxing available via Docker

**Key Differences from Claude Code:**
- [RESEARCH NEEDED] How does Gemini discover CLAUDE.md files?
- [RESEARCH NEEDED] Does Gemini have SessionStart hook equivalent?
- [RESEARCH NEEDED] How does agent invocation work?

**Action Item**: Document Gemini CLI behavior through systematic testing (Issue TBD)

### Impact on Architecture

**Why This Matters:**
1. **Nested directory hierarchies**: Must work consistently across both clients
2. **Hook timing**: SessionStart vs on-demand loading affects what context is available when
3. **CWD limitations**: Affects how scripts reference files and directories
4. **Token budgets**: Eager loading (SessionStart) vs lazy loading (discovery) trade-offs

**Design Constraints:**
- Cannot assume eager loading of ALL context files
- Must support both SessionStart injection and lazy discovery
- Instructions must work regardless of which client loads them
- Absolute paths required in any code that runs across Bash calls

## Related Issues

- #84: Configuration-based instruction enforcement
- #93: Agent detection in validate_tool.py
