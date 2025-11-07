# CLAUDE.md Just-In-Time Context Loading

## Overview

`CLAUDE.md` files provide directory-specific context that loads automatically when agents work in that directory. They use `@references` to modular documentation, enabling just-in-time context loading without upfront token cost.

## Purpose

**Problem**: Loading all documentation upfront wastes tokens and provides irrelevant context.

**Solution**: Place `CLAUDE.md` in directories with `@references` to relevant docs. Claude Code loads it automatically when agents enter that directory.

## When to Use CLAUDE.md

Create `CLAUDE.md` in a directory when:

1. **Specialized context needed**: Tests, scripts, specific modules need domain guidance
2. **Workflow-specific**: Directory has unique development patterns
3. **Tool-specific**: Directory uses specific tools/frameworks
4. **Standards enforcement**: Directory has specific quality requirements

**Don't create CLAUDE.md when:**

- Generic project-wide context (use root CLAUDE.md instead)
- One-off temporary directories
- Auto-generated directories (build/, .venv/, etc.)

## CLAUDE.md Structure

### Template

```markdown
# [Directory Purpose]

Context for working in [directory name].

## Standards

@../path/to/STANDARDS.md

## Workflows

@../path/to/WORKFLOWS.md

## Tools

@../path/to/TOOLS.md

## Project-Specific

[Any directory-specific notes that don't belong in referenced docs]
```

### Key Principles

1. **References only**: Use `@references`, don't duplicate content
2. **Relative paths**: Always use paths relative to CLAUDE.md location
3. **Minimal custom content**: Only add what's truly directory-specific
4. **Modular docs**: Reference chunked documentation, not monolithic files

## Common Patterns

### Python Source Directory

```markdown
# Python Development Context

@../agents/_CORE.md @../docs/_CHUNKS/FAIL-FAST.md @../.claude/skills/python-dev/SKILL.md

Use fail-fast principles: no defaults, explicit configuration only.
```

### Test Directory

```markdown
# Test Development Context

@../agents/_CORE.md @../docs/TESTING.md @../.claude/skills/test-writing/SKILL.md

Write integration tests using real configurations. No mocking internal code.
```

### Scripts Directory

```markdown
# Script Development Context

@../agents/_CORE.md @../docs/_CHUNKS/FAIL-FAST.md @../scripts/CLAUDE.md

Scripts must be executable in git. Fail-fast, no error recovery.
```

### Project-Specific Module

```markdown
# [Module Name] Context

@../../bot/docs/PYTHON_DEV.md @./MODULE_DESIGN.md

[Module-specific notes about architecture, dependencies, or constraints]
```

## Directory Structure Example

```
project/
├── CLAUDE.md                    # Root: project overview
├── tests/
│   ├── CLAUDE.md               # Test-specific context
│   └── integration/
│       └── CLAUDE.md           # Integration test context
├── scripts/
│   └── CLAUDE.md               # Script development context
├── src/
│   ├── CLAUDE.md               # Source code context
│   └── module/
│       └── CLAUDE.md           # Module-specific context
└── bot/
    └── prompts/
        └── CLAUDE.md           # Prompts directory context
```

## Best Practices

### DO

- ✅ Use `@references` to modular documentation
- ✅ Keep CLAUDE.md files short (<50 lines)
- ✅ Reference chunked docs in `docs/_CHUNKS/`
- ✅ Use relative paths from CLAUDE.md location
- ✅ Document directory-specific workflows only
- ✅ Update when directory purpose changes

### DON'T

- ❌ Duplicate content from referenced docs
- ❌ Create CLAUDE.md for every directory (only when needed)
- ❌ Use absolute paths
- ❌ Reference entire monolithic files
- ❌ Add generic project-wide content
- ❌ Let CLAUDE.md files become bloated (>50 lines)

## Integration with Skills

CLAUDE.md complements skills:

- **Skills**: Portable workflows packaged with scripts
- **CLAUDE.md**: Directory-specific context loading

**Example flow:**

1. Agent enters `tests/` directory
2. Claude Code loads `tests/CLAUDE.md`
3. CLAUDE.md references `@../.claude/skills/test-writing/SKILL.md`
4. Agent uses test-writing skill with directory context

## Maintenance

### When to Update CLAUDE.md

- Directory purpose changes
- New referenced documentation created
- Workflow patterns evolve
- Tool/framework changes

### When to Remove CLAUDE.md

- Directory becomes generic (no special context needed)
- All content moved to referenced docs
- Directory deprecated

## Migration from Agent Instructions

**Old approach** (agent instructions):

```markdown
# Developer Agent

When working in tests/:

1. Use pytest framework
2. Write integration tests
3. No mocking internal code ... [50 lines of test-specific instructions]
```

**New approach** (CLAUDE.md):

```markdown
# tests/CLAUDE.md

@../.claude/skills/test-writing/SKILL.md

Integration tests use real configurations from conf/.
```

**Benefits:**

- Context loads only when needed
- Reduces agent instruction bloat
- Modular, reusable documentation
- Lower token cost

## Technical Implementation

Claude Code automatically:

1. Detects CLAUDE.md in current working directory
2. Reads file and expands `@references`
3. Loads referenced content into context
4. Makes available to agent

**No hooks needed** - this is built-in Claude Code functionality.

## Related Systems

- **Skills** (`.claude/skills/*/SKILL.md`): Packaged workflows
- **Agent Instructions** (`agents/*.md`): Orchestration only
- **Hooks** (`.claude/settings.json`): Dynamic injection
- **Modular Docs** (`docs/_CHUNKS/*.md`): Reusable content chunks

## Examples in Practice

See these directories for reference implementations:

- `bot/scripts/CLAUDE.md`
- `bot/tests/CLAUDE.md`
- `bot/bots/CLAUDE.md`
