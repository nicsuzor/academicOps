# academicOps Agent Framework

A modular, hierarchical agent framework for rigorous, context-aware automation in research projects.

## AUTHORITATIVE: Workspace Structure

academicOps is designed to work with a specific workspace structure:

- **academicOps**: Contains all reusable content for automating academic work. Located at `${OUTER}/bot/`
- **OUTER repository**: Personal workspace (e.g., 'writing'). This is PRIVATE and contains:
    - `data/` - Personal task/project database
    - `projects/` - Academic project submodules
    - `bot/` - The academicOps submodule
- **Projects**: Submodules of the OUTER repository. Do NOT clone academicOps separately.

### Workspace Root

Users work from `${OUTER}/` as the workspace root. This ensures the instruction hierarchy works correctly:

1. **Personal instructions** (`${OUTER}/docs/agents/`) take precedence
2. **Project-specific instructions** (`${PROJECT}/docs/agents/`) are combined with generic academicOps instructions
3. **Generic academicOps instructions** (`./bot/agents/`, `./bot/docs/`) provide the foundation

## Core Concepts

This framework is built on three key components:

1. **Base Agent (`base.md`)**: The foundational prompt containing core, non-negotiable operational principles for all agents (e.g., security, error handling).
2. **Personas (`agents/`)**: A library of specialized agent prompts for specific roles (e.g., `developer`, `analyst`). These personas inherit the principles from the base agent.
3. **Hierarchical Instructions**: A system that allows project-specific instructions to override general agent personas, ensuring agents always operate with the most relevant context.

## How to Use academicOps

### Setup

1. Create your OUTER workspace repository (e.g., 'writing')
2. Add academicOps as a submodule:

   ```bash
   git submodule add https://github.com/nicsuzor/academicOps.git bot
   ```

3. Create personal agent instructions in `${OUTER}/docs/agents/INSTRUCTIONS.md`
4. Add projects as submodules in `${OUTER}/projects/`

### Working with Projects

When working on any project, agents will:

1. Load personal instructions from `${OUTER}/docs/agents/INSTRUCTIONS.md` (highest priority)
2. Combine with project-specific instructions from `${PROJECT}/docs/agents/`
3. Use generic academicOps instructions from `./bot/agents/` as foundation

### Agent Configuration Hierarchy

Agents load instructions with the following priority:

1. **Personal workspace** (`${OUTER}/docs/agents/INSTRUCTIONS.md`) - Highest priority
2. **Project-specific** (`${PROJECT}/docs/agents/`) - Combined with above
3. **Generic academicOps** (`./bot/agents/`, `./bot/docs/`) - Foundation layer
