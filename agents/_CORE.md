# Generic Agent Instructions

<!-- This file is read on every session start. Keep it short. -->

## Core Axioms (Inviolable Rules)

1. **Data Boundaries**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE
2. **Project Isolation**: Project-specific content belongs ONLY in the project repository
3. **Project Independence**: Projects (submodules) must work independently without cross-dependencies
4. **Fail-Fast Philosophy**: No fallbacks, no defensive programming, no workarounds, no backwards compatibility, **no `.get(key, default)`**
   - ❌ PROHIBITED: `config.get("param", default_value)` - Silent misconfiguration corrupts research data
   - ✅ REQUIRED: `config["param"]` - Raises KeyError immediately if missing
   - ✅ REQUIRED: Pydantic Field() with no default - Raises ValidationError
   - ✅ REQUIRED: Explicit check: `if key not in dict: raise ValueError(...)`
5. Everything is **self-documenting**: documentation-as-code first; never make separate documentation files. Our live, validated, rigorous academic projects are also tutorials and guides; everything is replicable so we work on live code and data; never create fake examples for tests or documentation.
6. **DRY**, modular, and **EXPLICIT**: one golden path, no defaults, no guessing, no backwards compatibility.
1. **STOP WHEN INTERRUPTED** - If user interrupts, stop immediately.
3. **VERIFY FIRST** - Check actual state, never assume.
4. **NO EXCUSES** - Never close issues or claim success without confirmation. No error is somebody else's problem. If you can't verify and replicate, it doesn't work.
5. **WRITE FOR THE LONG TERM** for replication: NEVER create single use scripts or tests or use ad-hoc analysis. We build the inrastructure that guarantees replicability and integrity for the long term.
6. Always document your progress. Use github issues in the appropriate repository to track progress. Assume you can be interrupted at any moment and will have no memory. Github is your memory for project-based work. The user's database in `data` is your memory for the user's projects, tasks, goals, strategy, notes, reminders, and planning.
7. **DON'T MAKE SHIT UP**. If you don't know, say so. No guesses.
8. **ALWAYS** cite your sources. No plagiarism. Ever.

## Repository Structure

```
${OUTER}/                          # Parent repo (PRIVATE)
├── CLAUDE.md                      # Entry point (1 line)
├── bot/                           # academicOps submodule (PUBLIC on GitHub)
│   ├── agents/
│   │   ├── trainer.md             # Agent definitions
│   │   └── ...
│   ├── scripts/                    # Public tools
│   └── docs/                       
│   │   ├── INSTRUCTIONS.md        # Generic rules (PUBLIC)
│   │   └── ...
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
└── .gemini/                        # Gemini CLI instructions
```


## Key tools

- **Python**: Use `uv run python` for all execution.
- **Issues**: Close only when explicit success metrics met or user confirms. For automation: months of error-free operation required.
- **Error Handling**: Stop immediately, report exactly, wait for instruction
