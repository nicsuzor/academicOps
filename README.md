# Bot Automation Framework

**Minimal LLM agent instructions and automation for Claude Code.**

**Philosophy**: Start minimal. Add only what's proven necessary through integration tests. Fight bloat aggressively.

---

## academicOps Repository Structure

**Note**: User-specific files (ACCOMMODATIONS, CORE, STYLE, VISION, ROADMAP) live in `$ACA_DATA`, not in this repository. This repo contains only generic framework infrastructure.

```
$AOPS/
├── AXIOMS.md            # Framework principles and quality standards (generic, loaded by all agents)
├── README.md            # THIS FILE - framework directory map and installation
│
├── BMEM-FORMAT.md       # bmem markdown format specification
├── BMEM-CLAUDE-GUIDE.md # Using bmem from Claude Code
├── BMEM-OBSIDIAN-GUIDE.md # Using bmem with Obsidian
│
├── skills/              # Agent skills (specialized workflows - invoke via Skill tool)
│   ├── framework/       # Framework maintenance, experimentation, strategic partner
│   │   ├── SKILL.md     # Main skill instructions
│   │   ├── STATE.md     # Current framework state, mandatory processes, blockers
│   │   ├── TASK-SPEC-TEMPLATE.md # Template for automation specifications
│   │   ├── workflows/   # Step-by-step procedures (design, debug, experiment, monitor, review, spec)
│   │   ├── references/  # Technical references (hooks guide, script design, testing patterns)
│   │   └── specs/       # Task specifications for planned automations
│   ├── analyst/         # Data analysis (dbt, Streamlit, statistical methods)
│   │   └── SKILL.md
│   ├── python-dev/      # Production Python code (type safety, fail-fast, research standards)
│   │   └── SKILL.md
│   ├── tasks/           # Task management system (MCP server)
│   │   ├── SKILL.md     # Task operations skill
│   │   ├── README.md    # Task system documentation
│   │   ├── server.py    # MCP server implementation
│   │   ├── task_ops.py  # Task operation functions
│   │   └── models.py    # Task data models
│   ├── bmem/            # Knowledge base operations (MCP wrapper)
│   │   └── SKILL.md
│   └── feature-dev/     # Feature development workflow (future)
│       └── SKILL.md
│
├── hooks/               # Lifecycle automation (Python scripts triggered by Claude Code events)
│   ├── hooks.json       # Hook configuration
│   ├── README.md        # Hook documentation (configuration, available hooks, debugging)
│   ├── session_logger.py         # Session logging module
│   ├── log_session_stop.py       # Stop hook - logs session activity
│   ├── extract_session_knowledge.py  # Knowledge extraction from session
│   └── prompts/         # Markdown prompts loaded by hooks
│
├── experiments/         # Temporary experiment logs (moved to $ACA_DATA/projects/aops/experiments/ when finalized)
│   └── YYYY-MM-DD_*.md  # Work-in-progress experiments
│                        # NOTE: Learning patterns LOG.md and completed experiments live at $ACA_DATA/projects/aops/experiments/
│
├── scripts/             # Deployment and maintenance scripts
│   └── package_deployment.py  # Release packaging for GitHub
│
├── lib/                 # Shared Python utilities
│   └── paths.py         # Path resolution (single source of truth for paths)
│
├── commands/            # Slash commands (workflow triggers)
│   ├── bmem.md          # Invoke bmem skill
│   ├── email.md         # Extract tasks from emails
│   ├── learn.md         # Update memory/instructions
│   ├── log.md           # Log agent performance
│   ├── meta.md          # Invoke framework skill for strategic questions
│   ├── task-viz.md      # Generate visual task dashboard (mind-map)
│   └── ttd.md           # Test-driven development orchestration
│
├── agents/              # Agentic workflows (future)
└── config/              # Configuration files
```

---

## User Data Repository Structure

academicOps stores user data separately from framework code. User-specific files live here:

```
$ACA_DATA/  (e.g., ~/src/writing/data/)
├── ACCOMMODATIONS.md    # Work style requirements (ADHD, cognitive load) [SESSION START: loaded first]
├── CORE.md              # User context, tools, paths [SESSION START: loaded second]
├── STYLE-QUICK.md       # Writing style reference [SESSION START: loaded third]
├── STYLE.md             # Full writing style guide (referenced, not loaded at start)
│
├── tasks/               # Task data (markdown files, bmem-compliant)
│   ├── active/          # Current tasks
│   ├── completed/       # Finished tasks
│   └── deferred/        # Postponed tasks
│
├── sessions/            # Claude Code session logs
│   └── YYYY-MM-DD_HH-MM-SS.md
│
├── projects/            # Project-specific data
│   └── aops/            # academicOps project data
│       ├── VISION.md    # End state: fully-automated academic workflow
│       ├── ROADMAP.md   # Maturity stages 0-5, progression plan
│       ├── experiments/ # Framework experiment logs
│       │   └── LOG.md   # Learning patterns (append-only)
│       └── tests/       # Framework integration tests (pytest)
│
└── [other bmem entities] # People, orgs, concepts, work items, etc.
```

---

## Installation in Other Projects

academicOps installs via symlinks to user's `~/.claude/`:

```
project-repo/           # Any academic project repository
├── .claude/            # Claude Code configuration directory
│   ├── CLAUDE.md       # Project-specific instructions
│   ├── skills/         # Symlink → $AOPS/skills/
│   ├── hooks/          # Symlink → $AOPS/hooks/
│   └── commands/       # Symlink → $AOPS/commands/
├── [project files...]
```

**Installation**: Download [latest release](https://github.com/nicsuzor/academicOps/releases), extract, run `bash setup.sh`.

---

## Contact

- **Repository**: https://github.com/nicsuzor/academicOps
- **Releases**: https://github.com/nicsuzor/academicOps/releases
