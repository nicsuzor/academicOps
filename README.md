# academicOps Agent Framework

A modular, hierarchical agent framework for rigorous, context-aware automation in research projects.

## Core Concepts

This framework is built on three key components:

1.  **Base Agent (`base.md`)**: The foundational prompt containing core, non-negotiable operational principles for all agents (e.g., security, error handling).
2.  **Personas (`agents/`)**: A library of specialized agent prompts for specific roles (e.g., `developer`, `analyst`). These personas inherit the principles from the base agent.
3.  **Hierarchical Instructions**: A system that allows project-specific instructions to override general agent personas, ensuring agents always operate with the most relevant context.

## How to Use in Your Project

To integrate this framework into your own research project, follow these steps:

### 1. Add as a Submodule

Include the `academicOps` repository as a Git submodule, typically in a `bot/` directory within your project.

```bash
git submodule add https://github.com/nicsuzor/academicOps.git bot
```

### 2. Select a Persona

When invoking an agent, select a persona from the `bot/agents/` directory that best fits your task (e.g., for coding, use the `developer` persona).

### 3. Provide Project-Specific Instructions (Recommended)

To give an agent context specific to your project, create a `BOT_INSTRUCTIONS.md` file in the root of your project directory.

This file is the highest authority. The agent will always prioritize instructions found here.

**Example:** In your project `my_research_paper/`, you could create `my_research_paper/BOT_INSTRUCTIONS.md` with the following content:

```markdown
# Project: My Research Paper

## Data Analysis Protocol

- All data analysis MUST use the dataset located at `/data/processed/my_dataset.csv`.
- Do not use any other data source.
- All charts must be saved to the `/figures` directory.
```

## Instruction Loading Order

Agents load instructions with the following priority:

1.  **`[Your Project]/BOT_INSTRUCTIONS.md`** (Highest priority)
2.  `bot/agents/<selected_persona>.md`
3.  `bot/agents/base.md` (Lowest priority)