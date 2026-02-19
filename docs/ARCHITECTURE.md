---
title: academicOps Architecture
type: note
category: spec
permalink: architecture
tags:
  - framework
  - architecture
  - design
---

# academicOps Architecture

This document defines the core vs. optional dependency architecture of the academicOps framework. The framework is designed to be modular, with a minimal core and several optional plugins that provide specialized capabilities.

## 1. Core Framework (Required)

The core framework provides the essential infrastructure for workflow enforcement, task management, and knowledge persistence.

| Component               | Purpose                                             | Dependencies                                            |
| ----------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| **Task System**         | Hierarchical task graph with blocking dependencies. | `task_manager` MCP server                               |
| **Memory System**       | Semantic search index for cross-session knowledge.  | `memory` MCP server                                     |
| **Prompt Hydration**    | Transforms user prompts into execution plans.       | `prompt-hydrator` agent, `critic` agent                 |
| **Compliance Auditing** | Real-time monitoring of agent behavior.             | `custodiet` agent                                       |
| **Standard Tools**      | Basic file operations and environment access.       | `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `Task` |

### Core Logic

The core logic resides in `aops-core/lib/` and is shared across all tools and agents. This includes the task model, session state management, and path resolution.

## 2. Optional Plugins (Recommended)

Optional plugins extend the framework with domain-specific capabilities. These require additional setup or external accounts.

### 2.1 Research & Citations

| Component              | Purpose                                  | Requirement                          |
| ---------------------- | ---------------------------------------- | ------------------------------------ |
| **Zotero Integration** | Search papers and manage citations.      | `zot` MCP server, local Zotero setup |
| **Oversight Board**    | Legal reasoning analysis over OSB cases. | `osb` MCP server                     |

### 2.2 Communication & Coordination

| Component               | Purpose                                  | Requirement                            |
| ----------------------- | ---------------------------------------- | -------------------------------------- |
| **Outlook Integration** | Email triage and task capture.           | `omcp` MCP server, local Outlook setup |
| **Notifications**       | Real-time alerts for long-running tasks. | `ntfy` server and topic setup          |

### 2.3 Data Analysis

| Component         | Purpose                                 | Requirement        |
| ----------------- | --------------------------------------- | ------------------ |
| **Analyst Skill** | Research data pipelines and dashboards. | `dbt`, `Streamlit` |

## 3. Dependency Management

The framework uses a **"Call to Verify"** pattern for optional dependencies (see [[AXIOMS.md#fail-fast|Fail-Fast]]):

1. **Do NOT assume availability**: Agents should never assume a plugin is configured.
2. **Invoke Tool directly**: To check for availability, the agent attempts to call the relevant tool.
3. **Graceful Degradation**: If the tool returns an error indicating it's missing or unconfigured, the agent reports this to the user and continues with reduced functionality if possible.

## 4. Repository Model

academicOps uses a three-repo model to ensure privacy and modularity:

1. **`$AOPS/` (Public)**: The core framework machinery. Contains no personal data.
2. **`$ACA_DATA/` (Private)**: Your personal knowledge base, tasks, and memories. Never shared.
3. **Project Repos (Collaborative)**: Research code and documentation. Shared with collaborators.
