---
name: docs-update
description: Maintain README.md and INDEX.md documentation, detecting and correcting drift from actual filesystem state.
allowed-tools: Read,Glob,Grep,Edit,Write,Bash
version: 1.0.0
permalink: skills-docs-update
---

# Documentation Update Skill

Maintain two documentation files:
- **README.md** - Brief overview (~100 lines)
- **INDEX.md** - Complete file tree with annotations

## README.md Structure

Brief overview for all agents:

```markdown
# academicOps Framework

Minimal LLM agent automation for Claude Code.

## Paths

- `$AOPS` - Framework (skills, hooks, commands)
- `$ACA_DATA` - User data (tasks, learning, sessions)
- `~/.claude/` - Runtime (symlinks to $AOPS)

## Commands

- /meta: Strategic brain + executor. Design, build, verify.
- /advocate: Reactive verification. "Prove it worked."
- /log: Log patterns via learning-log skill.
- /transcript: Generate session transcripts.
[... one line each]

## Skills

- framework: Convention reference for infrastructure changes.
- python-dev: Production Python (fail-fast, types).
- learning-log: Pattern logging to thematic files.
[... one line each]

## Hooks

Session lifecycle. See INDEX.md for details.

## See Also

- AXIOMS.md - Principles
- INDEX.md - Full file tree
```

## INDEX.md Structure

Complete file-to-function mapping with cross-references:

```markdown
# Framework Index

See README.md for overview.

## File Tree

$AOPS/
├── AXIOMS.md                # Principles (session start injection)
├── README.md                # Brief overview
├── INDEX.md                 # THIS FILE
│
├── commands/
│   ├── meta.md              # → framework skill, python-dev skill
│   ├── advocate.md          # Standalone verification
│   ├── log.md               # → learning-log skill
│   └── transcript.md        # → transcript skill
│
├── skills/
│   ├── framework/           # Convention reference
│   ├── learning-log/        # → may invoke transcript skill
│   ├── transcript/          # Session → markdown
│   └── [each skill...]
│
├── hooks/
│   ├── sessionstart_load_axioms.py
│   └── [each hook...]
│
└── [complete tree...]

## Cross-References

### Command → Skill
- /meta → framework, python-dev
- /log → learning-log
- /transcript → transcript

### Skill → Skill
- learning-log → transcript
```

## Workflow

1. Scan repository: `find $AOPS -type f -not -path "*/.git/*" | sort`
2. Generate brief README.md (~100 lines)
3. Generate detailed INDEX.md (complete tree)
4. Validate cross-references resolve
5. Write both files

## Validation

- README.md < 150 lines
- INDEX.md has every file
- All `→` references point to existing files
- No broken wikilinks
