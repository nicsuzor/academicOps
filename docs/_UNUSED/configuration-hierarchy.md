# Configuration Hierarchy Documentation

## Overview

The agent configuration system uses a three-layer hierarchy with standardized locations to ensure consistent, predictable behavior across all projects and submodules.

## Directory Structure

```
/writing/                           # Repository root
├── docs/
│   └── agent/
│       └── INSTRUCTIONS.md        # Global personal preferences
├── bot/                           # academicOps submodule
│   ├── agents/                    # Base agent definitions
│   │   ├── base.md               # Core operational principles
│   │   ├── strategist.md         # Strategic planning agent
│   │   ├── trainer.md            # Meta-agent for improvements
│   │   └── ...                   # Other specialized agents
│   └── docs/
│       └── configuration-hierarchy.md  # This file
└── projects/
    ├── wikijuris/                # WikiJuris submodule
    │   └── docs/
    │       └── agent/
    │           └── INSTRUCTIONS.md   # WikiJuris-specific rules
    └── buttermilk/               # Buttermilk submodule
        └── docs/
            └── agent/
                └── INSTRUCTIONS.md   # Buttermilk-specific rules
```

## Configuration Precedence (Highest to Lowest)

1. **Project-Specific** (`./docs/agents/INSTRUCTIONS.md`)
   - Always checked first in the current working directory
   - Contains project-specific overrides and workflows
   - Completely overrides lower levels for specified behaviors

2. **Personal/Global** (`/writing/docs/agents/INSTRUCTIONS.md`)
   - User's personal preferences across all projects
   - Applied when no project-specific configuration exists
   - Can reference and modify base agent behaviors

3. **Base/Default** ${ACADEMICOPS}/agents/*.md`)
   - Core agent definitions and shared behaviors
   - Public, reusable components
   - Foundation for all agent operations

## How It Works

### Agent Loading Process

1. When an agent starts, it checks for instructions in a specific order
2. First, it looks for `./docs/agents/INSTRUCTIONS.md` in the current directory
3. If found, those project-specific instructions take precedence
4. If not found, it checks `/writing/docs/agents/INSTRUCTIONS.md` for global preferences
5. Base agent definitions from ${ACADEMICOPS}/agents/*.md` provide the foundation
6. More specific instructions always override more general ones

### Key Benefits

- **Robust**: Works regardless of directory structure or submodule configuration
- **Consistent**: Same pattern everywhere - always check `./docs/agents/INSTRUCTIONS.md`
- **Simple**: All configuration in standardized INSTRUCTIONS.md files
- **Discoverable**: Standard location makes configurations easy to find
- **Flexible**: Projects can override anything while maintaining base definitions
- **Clean**: No empty directories or duplicate files

## Creating a New Project Configuration

To add agent configuration to a new project:

1. Create the directory structure:
   ```bash
   mkdir -p ./docs/agent
   ```

2. Create INSTRUCTIONS.md with this template:
   ```markdown
   # Agent Instructions for [Project Name]

   ## Configuration Hierarchy

   This is the project-specific configuration for [Project].

   1. **Project-Specific** (this file) - Overrides all other configurations
   2. **Global** (`/writing/docs/agents/INSTRUCTIONS.md`) - Repository-wide preferences
   3. **Base** ${ACADEMICOPS}/agents/*.md`) - Core agent definitions

   ## [Project]-Specific Instructions

   [Your project-specific instructions here]

   ## Agent Overrides

   When using base agents from ${ACADEMICOPS}/agents/`:

   - Use [agent] with these modifications: [...]
   ```

3. That's it! Agents will automatically find and use these instructions.

## Migration from Old System

The previous system had:

- Multiple configuration files with unclear precedence
- BOT_INSTRUCTIONS.md files
- Various scattered instruction files
- Unclear precedence and duplication

The new system consolidates everything into a clear, three-layer hierarchy with standardized locations.

## Troubleshooting

### Agent not finding instructions

- Check you're using `./docs/agents/INSTRUCTIONS.md` (note the `./`)
- Verify the directory structure matches the standard
- Ensure the INSTRUCTIONS.md file exists in the expected location

### Conflicting instructions

- Remember: Project-specific > Global > Base
- More specific instructions always win
- Check all three layers to understand the full context

### Updating configurations

- Project changes: Edit `./docs/agents/INSTRUCTIONS.md` in that project
- Global changes: Edit `/writing/docs/agents/INSTRUCTIONS.md`
- Base changes: Edit files in ${ACADEMICOPS}/agents/`

## Best Practices

1. **Keep project instructions focused**: Only include what's unique to that project
2. **Reference base agents**: Don't duplicate, extend and modify
3. **Use clear section headers**: Make it easy to scan and understand
4. **Document the hierarchy**: Include the configuration hierarchy section in each INSTRUCTIONS.md
5. **Avoid duplication**: Let the hierarchy handle inheritance
