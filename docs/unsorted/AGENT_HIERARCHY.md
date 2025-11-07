# Agent Instruction Hierarchy

This document explains the hierarchical system used to provide instructions to agents, ensuring they operate with the most relevant context for any given task or project.

## The Principle of Specificity

The core principle is **specificity**: more specific, local instructions always override more general, global ones. This allows us to define base behaviors for all agents while providing fine-grained control for individual projects without modifying the core agent prompts.

## The Loading Order

When an agent is activated, it loads its instructions in the following order of precedence (from highest to lowest):

1. **Project-Specific Instructions (`BOT_INSTRUCTIONS.md`) - HIGHEST PRIORITY**
   - **Location**: A file named `BOT_INSTRUCTIONS.md` within a specific project's root (e.g., `projects/buttermilk/BOT_INSTRUCTIONS.md`).
   - **Purpose**: To provide context-specific rules, data sources, or workflows that are unique to that single project.
   - **Rule**: If this file exists, its instructions **SUPERSEDE** all other instructions. The agent MUST follow them as its primary guide.

2. **Assigned Agent Persona (`bot/agents/<agent_name>.md`)**
   - **Location**: The specific agent prompt file in the `bot/agents/` directory (e.g., `developer.md`).
   - **Purpose**: To define the specialized skills, tools, and workflow for a particular role (Developer, Analyst, etc.).
   - **Rule**: These instructions are followed if and only if no project-specific instruction file is found.

3. **Base Agent Instructions (`bot/agents/base.md`) - LOWEST PRIORITY**
   - **Location**: `bot/agents/base.md`
   - **Purpose**: To provide the foundational, non-negotiable operating principles for ALL agents (e.g., security boundaries, error handling).
   - **Rule**: These are the default rules that apply in the absence of more specific instructions.

## How to Use This System

To provide custom instructions for a project, simply create a `.gemini` directory in that project's root and add an `instructions.md` file.

### Example: `buttermilk` Project

If you are working within the `projects/buttermilk` directory and want the `developer` agent to use a specific debugging protocol:

1. Create the file: `projects/buttermilk/.gemini/instructions.md`
2. Add the specific instructions to that file:

   ```markdown
   # Buttermilk Project - Developer Instructions

   ## Debugging Protocol

   When debugging, you MUST use the custom logging utility provided in `buttermilk.utils.debugging`. Do not use standard `print()` statements.
   ```

When the `developer` agent is run from within the `projects/buttermilk` directory, it will find this file and prioritize the debugging protocol described within it, falling back to the standard `developer.md` and `base.md` instructions for all other tasks.
