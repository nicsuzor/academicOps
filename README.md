# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## Structure

```
$AOPS/
├── CORE.md              # User context, tools, paths (loaded at session start)
├── AXIOMS.md            # Universal principles (loaded at session start)
├── ACCOMMODATIONS.md    # ADHD work style (loaded at session start)
├── STYLE-QUICK.md       # Writing style quick ref (loaded at session start)
├── STYLE.md             # Full writing style guide (referenced, not loaded)
├── README.md            # THIS FILE - framework documentation
│
├── skills/              # Agent skills (specialized workflows)
│   ├── framework/       # Framework maintenance skill
│   ├── analyst/         # Data analysis (dbt, Streamlit, stats)
│   ├── python-dev/      # Production Python code
│   └── feature-dev/     # Feature development workflow
│
├── hooks/               # Lifecycle hooks
│   ├── hooks.json       # Hook configuration
│   ├── README.md        # Hook documentation
│   ├── session_logger.py         # Session logging module
│   ├── log_session_stop.py       # Stop hook
│   ├── extract_session_knowledge.py  # LLM-powered knowledge extraction
│   └── prompts/         # Markdown prompts for hooks
│
├── commands/            # Slash commands (future)
├── agents/              # Agentic workflows (future)
└── config/              # Configuration files (future)
```

---

## Session Start

Files loaded at session start (in order):

1. `CORE.md` → User context, tools, paths
2. `AXIOMS.md` → Framework principles
3. `ACCOMMODATIONS.md` → Work style requirements
4. `STYLE-QUICK.md` → Writing style reference

---

## Skills

Specialized agent workflows for specific domains. See `skills/*/SKILL.md` for instructions.

---

## Hooks

Lifecycle automation scripts. See `hooks/README.md` for configuration.

---

## Principles

See `AXIOMS.md` for framework principles.

---

## Testing

See `skills/framework/SKILL.md` for testing requirements and workflows.

---

## Experiments

See `experiments/LOG.md` for learning patterns and `experiments/*.md` for individual experiments

---

## Installation & Deployment

See `scripts/package_deployment.py` for release packaging and deployment instructions.

---

## Contact

- **Repository**: https://github.com/nicsuzor/academicOps
- **Releases**: https://github.com/nicsuzor/academicOps/releases
