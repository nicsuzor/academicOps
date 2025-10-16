# academicOps Setup Guide

## Workspace Structure

academicOps is designed to work as a **submodule** of a larger workspace:

- **OUTER repository** (e.g., 'writing'): Your personal workspace (PRIVATE)
- **academicOps**: Located at `${OUTER}/bot/` - contains all reusable automation
- **Projects**: Submodules of OUTER repository at `${OUTER}/projects/`

## Installation

### 1. Create your OUTER workspace repository

```bash
mkdir my-workspace && cd my-workspace
git init
```

### 2. Add academicOps as a submodule

```bash
git submodule add https://github.com/nicsuzor/academicOps.git bot
```

### 3. Create personal instructions

```bash
mkdir -p docs
# Create docs/INSTRUCTIONS.md with your personal rules
```

### 4. Add projects as submodules

```bash
git submodule add <project-url> projects/<project-name>
```

## Instruction Hierarchy

Agents load instructions with the following priority:

1. **OUTER workspace** (`${OUTER}/docs/INSTRUCTIONS.md`) - Highest priority
2. **Project-specific** (`${PROJECT}/docs/`) - Combined with above
3. **Generic academicOps** (`bot/agents/`, `bot/docs/`) - Foundation layer

This ensures agents always operate with the most relevant context while maintaining clean separation between generic framework and personal/project-specific content.

## Environment Variables

For portability across machines, configure these environment variables:

- `$ACADEMIC_OPS_DATA` - Data directory
- `$ACADEMIC_OPS_SCRIPTS` - Scripts directory
- `$ACADEMIC_OPS_DOCS` - Documentation directory

See `bot/docs/PATH-RESOLUTION.md` for detailed configuration.
