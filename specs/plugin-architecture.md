---
title: Plugin Architecture
type: spec
category: architecture
description: Component assignments and boundaries for academicOps plugins
---

# Plugin Architecture

## Giving Effect

- [[aops-core/.mcp.json]] - Core plugin MCP server definitions (gemini, memory, task_manager)
- [[aops-core/hooks/hooks.json]] - Core plugin hook registrations
- [[aops-core/skills/]] - Core skills directory (audit, framework, remember, etc.)
- [[aops-core/agents/]] - Core agents directory (critic, custodiet, prompt-hydrator, qa)
- [[aops-tools/.mcp.json]] - Tools plugin MCP server definitions (context7, outlook, playwright)
- [[aops-tools/skills/]] - Tools skills directory (analyst, daily, excalidraw, pdf, etc.)

This document defines the component assignments for the academicOps plugin ecosystem.

## Design Principles

1. **Core vs Tools Separation**: aops-core provides framework infrastructure; aops-tools provides domain utilities
2. **MCP Server Assignment**: Each plugin bundles only the MCP servers it needs
3. **Clear Boundaries**: Each component belongs to exactly one plugin

## aops-core Plugin

**Purpose**: Core framework infrastructure for agent coordination, quality assurance, and workflow orchestration.

### Components

**Skills**:
- `audit` - Framework governance audit with structure and justification checking
- `feature-dev` - Test-first feature development from idea to validated implementation
- `framework` - Framework infrastructure workflows (deprecated - delegates to framework agent)
- `remember` - Persist knowledge to markdown and memory server with semantic search
- `session-insights` - Generate session insights from transcripts using Gemini
- `tasks` - Task lifecycle management using scripts and MCP tools

**Commands**:
- `/learn` - Graduated framework improvement workflow
- `/log` - Log framework observations to bd issues

**Agents**:
- `critic` - Second-opinion review of plans and conclusions
- `custodiet` - Ultra vires detector (catches agents acting beyond authority)
- `framework` - Framework infrastructure work with explicit skill access
- `prompt-hydrator` - Transform terse prompts into complete execution plans
- `qa` - Independent end-to-end verification before completion

**MCP Servers**:
- `gemini` - Google Gemini API access (used by session-insights)
- `memory` - Persistent memory service

## aops-tools Plugin

**Purpose**: Domain-specific tools and utilities for research workflows - planning, communication, visualization, data processing, and development.

### Components

**Skills**:
- `analyst` - Data analysis with dbt and Streamlit for academic research
- `annotations` - Scan and process inline HTML comments for human-agent collaboration
- `convert-to-md` - Batch convert documents to markdown
- `daily` - Daily note lifecycle management
- `dashboard` - Cognitive Load Dashboard for task visibility
- `excalidraw` - Hand-drawn diagrams with organic layouts
- `flowchart` - Mermaid flowcharts with accessibility best practices
- `garden` - Incremental PKM maintenance
- `pdf` - Convert markdown to professionally formatted PDFs
- `python-dev` - Production-quality Python code with fail-fast philosophy

**Commands**:
- `/aops` - Show framework capabilities
- `/diag` - Diagnostic check of current session
- `/email` - Create actionable tasks from emails
- `/q` - Queue task for later execution (creates bd issue)

**Agents**:
- `effectual-planner` - Strategic planning under uncertainty

**MCP Servers**:
- `context7` - Context management and memory
- `outlook` - Microsoft Outlook/Office integration
- `playwright` - Browser automation

## Cross-Plugin Dependencies

### aops-tools depends on aops-core for:
- Framework agents (hydrator, custodiet, qa, critic)
- Core workflows (/learn, /log)
- Audit capabilities

### aops-core has no dependencies on aops-tools
- Core framework remains independent
- Can be used without tools plugin

## MCP Server Rationale

**aops-core servers**:
- `gemini`: Required for session-insights skill (transcript analysis)
- `memory`: Core capability for persistent agent memory

**aops-tools servers**:
- `context7`: Context management for research workflows
- `outlook`: Email processing for academic communication
- `playwright`: Browser automation for data collection and testing

## Extension Guidelines

When adding new components:

1. **Determine plugin**: Core infrastructure → aops-core, Domain utility → aops-tools
2. **Check dependencies**: Component should only depend on its own plugin or aops-core
3. **MCP servers**: Assign to plugin that uses them; prefer stdio over HTTP for security
4. **Document here**: Update this spec when adding components
