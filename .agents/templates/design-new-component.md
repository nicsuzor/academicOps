---
title: Design New Component
type: template
category: process
description: Design and scaffold a new framework component (skill, hook, tool, or workflow) following structural standards. Select when adding new capabilities to the framework.
tags: [component-design, scaffolding, plugin-development, standards, process]
---

# Process: Design New Component

Standardized design and scaffolding workflow for framework plugins, skills, and tools.

## 1. Purpose and Interface Definition

- Define the core purpose, user persona, and invocation trigger for `<component-name>`.
- Determine the component type: Skill, Hook, MCP Tool, or Workflow Template.
- Apply the craft standard to design minimal, unambiguous interfaces.

## 2. Specification and Schema Authoring

- Author formal specification defining input parameters, output schemas, and error states.
- Ensure strict JSON schemas (`additionalProperties: false`, required fields).

## 3. Scaffolding and Implementation

- Create component directory structure and manifests (`plugin.json`, `mcp.json`, `hooks.json`).
- Implement core logic and handler functions following test-driven development (`tdd`).

## 4. Test Suite and Verification

- Write unit tests covering normal operation, invalid arguments, and edge conditions.
- Verify manifest registration and build pipeline integration.

## 5. Documentation and Review

- Update documentation and plugin index.
- Run `audit` to verify no dangling references or dead links.
