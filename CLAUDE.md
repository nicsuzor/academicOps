Read `./agents/_CORE.md` for core axioms and project instructions.

## Repository: nicsuzor/academicOps

This is the **academicOps** framework repository (PUBLIC), providing agent infrastructure for academic projects.

**Directory structure:**
```
$ACADEMICOPS/          # This repository
├── agents/                # Self-contained agentic workflows (subagents)
├── commands/              # Slash command definitions
├── config/                # Claude Code settings (hooks, permissions)
├── core/                  # Universal instructions (auto-loaded at SessionStart)
├── docs/                  # Framework documentation
│   ├── bots/              # Framework development context (auto-loaded at SessionStart)
│   └── INSTRUCTION-INDEX.md  # Complete file registry
├── hooks/                 # SessionStart, PreToolUse, Stop hooks
├── scripts/               # Supporting automation
└── skills/                # Packaged skills (installed to ~/.claude/skills/)
```

**How projects use this framework:**
- Projects reference via `$ACADEMICOPS` environment variable
- SessionStart hook auto-loads `core/_CORE.md` and `docs/bots/INDEX.md` from 3 tiers (framework/personal/project)
- Specialized agents invoked via slash commands (`/trainer`, `/analyst`, `/dev`, etc.)
- Hooks run automatically to validate tool use and load context

**Working in this repository:**
- Evidence-based changes and experiments (we're building a SYSTEM, not fixing discrete bugs)
- Log failures to experiment tracker and GitHub issues (prefer existing issues)
- See `docs/INSTRUCTION-INDEX.md` for complete file visibility (SHOWN vs REFERENCED)
