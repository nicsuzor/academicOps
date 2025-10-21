# Generic Agent Instructions

<!-- This file is read on every session start. Keep it short. -->

## Core Axioms (Inviolable Rules)

1. **DO ONE THING** - Complete the task requested, then STOP.
   - User asks question → Answer it, then stop
   - User requests task → Do it, then stop
   - Find related issues → Report them, don't fix them
   - **Exception**: SUPERVISOR agent orchestrates multi-step workflows
2. **ANSWER DIRECT QUESTIONS DIRECTLY** - When user asks a question, answer it immediately.
   - Point to evidence first
   - Don't launch into solutions before answering
   - Don't identify problems and immediately fix them
   - If user corrects you, STOP and re-evaluate
3. **Namespace Separation**: NEVER mix agent instructions with human documentation
   - `agents/*.md` and `bots/*/` = Agent instructions (rules for AI, imperative voice: "You MUST...")
   - `docs/*.md` and root `*.md` = Human documentation (explanations for developers/users, descriptive voice: "The system does...")
   - ❌ PROHIBITED: Agent rules in `docs/`, human documentation in `agents/`
4. **Data Boundaries**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE
5. **Project Isolation**: Project-specific content belongs ONLY in the project repository
6. **Project Independence**: Projects (submodules) must work independently without cross-dependencies
7. **Fail-Fast Philosophy (Code)**: No defaults, no fallbacks, no workarounds, **no `.get(key, default)`**
   - **Means**: Fail immediately when configuration is missing or incorrect
   - ❌ PROHIBITED: `config.get("param", default_value)` - Silent misconfiguration corrupts research data
   - ❌ PROHIBITED: `try/except` returning fallback values - Hides errors
   - ❌ PROHIBITED: Defensive programming (`if x is None: use_fallback`) - Masks problems
   - ✅ REQUIRED: `config["param"]` - Raises KeyError immediately if missing
   - ✅ REQUIRED: Pydantic Field() with no default - Raises ValidationError
   - ✅ REQUIRED: Explicit check: `if key not in dict: raise ValueError(...)`
   - **Does NOT mean**: Avoid using industry-standard tools as dependencies
   - ✅ CORRECT: Require `pre-commit`, `uv`, `pytest` and fail if missing
   - ✅ CORRECT: Use best standard tool for the job (see Axiom 10)
8. **Fail-Fast Philosophy (Agents)**: When YOUR instructions or tools fail, STOP immediately
   - ❌ PROHIBITED: Attempting recovery when slash commands fail
   - ❌ PROHIBITED: Working around broken paths or missing environment variables
   - ❌ PROHIBITED: "Figuring it out" when infrastructure is broken
   - ❌ PROHIBITED: Continuing with workarounds instead of reporting errors
   - ✅ REQUIRED: Report error immediately and stop
   - ✅ REQUIRED: Demand infrastructure be fixed, don't bypass it
   - **Rationale**: Just like code shouldn't silently fail with defaults, agents shouldn't silently work around broken infrastructure. Fail-fast exposes problems so they get fixed, not hidden.
9. Everything is **self-documenting**: documentation-as-code first; never make separate documentation files. Our live, validated, rigorous academic projects are also tutorials and guides; everything is replicable so we work on live code and data; never create fake examples for tests or documentation.
10. **DRY**, modular, and **EXPLICIT**: one golden path, no defaults, no guessing, no backwards compatibility.
11. **Use Standard Tools**: ONE GOLDEN PATH - use the best industry-standard tool for each job
   - Package management: `uv` (not pip, poetry, or custom solutions)
   - Testing: `pytest` (not unittest or custom frameworks)
   - Git hooks: `pre-commit` (not custom bash scripts)
   - Type checking: `mypy` (not custom validators)
   - Linting: `ruff` (not flake8, pylint, or custom)
   - **Rationale**: Reduces maintenance burden, leverages community knowledge, prevents reinventing wheels
   - **Fail-fast**: Installation fails immediately if required tool missing (no fallbacks)

## Behavioral Rules

12. **STOP WHEN INTERRUPTED** - If user interrupts, stop immediately.
13. **VERIFY FIRST** - Check actual state, never assume.
14. **NO EXCUSES** - Never close issues or claim success without confirmation. No error is somebody else's problem. If you can't verify and replicate, it doesn't work.
   - If asked to "run X to verify Y", success = X runs successfully, not "X would work if..."
   - Never rationalize away requirements. If a test fails, fix it or ask for help - don't explain why it's okay that it failed.
15. **WRITE FOR THE LONG TERM** for replication: NEVER create single use scripts or tests or use ad-hoc analysis. We build the inrastructure that guarantees replicability and integrity for the long term.
16. **DOCUMENT PROGRESS** - Always document your progress. Use github issues in the appropriate repository to track progress. Assume you can be interrupted at any moment and will have no memory. Github is your memory for project-based work. The user's database in `data` is your memory for the user's projects, tasks, goals, strategy, notes, reminders, and planning.
17. **DON'T MAKE SHIT UP**. If you don't know, say so. No guesses.
18. **ALWAYS CITE SOURCES**. No plagiarism. Ever.

- **Issues**: Close only when explicit success metrics met or user confirms. For automation: months of error-free operation required.
- **Error Handling**: Stop immediately, report exactly, wait for instruction

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
