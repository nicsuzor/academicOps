# aops-tools Plugin

Tools and utilities plugin for academicOps - planning, communication, visualization, data processing, and development.

## Overview

This plugin provides a collection of specialized tools, agents, and commands that extend the academicOps framework with practical utilities for research workflows.

## Components

### Agents (1)

| Agent | Purpose |
|-------|---------|
| [effectual-planner](./agents/effectual-planner.md) | Effectuation-based strategic planning agent |

### Commands (3)

| Command | Purpose |
|---------|---------|
| [/aops](./commands/aops.md) | Main academicOps command interface |
| [/diag](./commands/diag.md) | Diagnostics and system health checks |
| [/email](./commands/email.md) | Email composition and management |

### Skills (10)

| Skill | Category | Purpose |
|-------|----------|---------|
| [analyst](./skills/analyst/) | Analysis | Data analysis and interpretation |
| [annotations](./skills/annotations/) | Processing | Annotation management and processing |
| [convert-to-md](./skills/convert-to-md/) | Processing | Convert various formats to Markdown |
| [daily](./skills/daily/) | Planning | Daily workflow and planning |
| [dashboard](./skills/dashboard/) | Visualization | Dashboard creation and management |
| [excalidraw](./skills/excalidraw/) | Visualization | Excalidraw diagram creation |
| [flowchart](./skills/flowchart/) | Visualization | Flowchart generation |
| [garden](./skills/garden/) | Organization | Digital garden management |
| [pdf](./skills/pdf/) | Processing | PDF processing and extraction |
| [python-dev](./skills/python-dev/) | Development | Python development utilities |

## Plugin Structure

```
aops-tools/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── agents/                  # Specialized agents
│   └── effectual-planner.md
├── commands/                # User-invocable commands
│   ├── aops.md
│   ├── diag.md
│   └── email.md
├── skills/                  # Skill definitions
│   ├── analyst/
│   ├── annotations/
│   ├── convert-to-md/
│   ├── daily/
│   ├── dashboard/
│   ├── excalidraw/
│   ├── flowchart/
│   ├── garden/
│   ├── pdf/
│   └── python-dev/
├── specs/                   # Specifications
├── docs/                    # Documentation
└── README.md               # This file
```

## Installation

This plugin is part of the academicOps framework. It is automatically discovered by Claude Code when present in the repository.

## Usage

- **Invoke skills**: Use the Skill tool with the skill name (e.g., `Skill(skill="analyst")`)
- **Run commands**: Type the command name (e.g., `/aops`, `/diag`, `/email`)
- **Use agents**: Agents are invoked automatically by the framework or via the Task tool

## Related Plugins

- [aops-core](../aops-core/) - Core framework components (hooks, agents, workflows)

## License

MIT
