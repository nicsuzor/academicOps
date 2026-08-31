---
title: Map Then Wire Plugin Development
type: template
category: process
description: "Two-phase plugin architecture workflow: first map all events, handlers, and tools, then implement and wire handler code. Select when building or refactoring complex plugins."
tags: [plugin, architecture, mapping, wiring, hooks, development, process]
---

# Process: Map Then Wire Plugin Development

Two-phase design and implementation methodology for plugin development.

## 1. Phase 1: Architectural Mapping

- Enumerate all events, tools, skills, and configuration schemas the plugin requires (`<plugin-target>`).
- Map event flows: trigger event -> handler function -> payload transformation -> injected context.
- Author plugin manifests (`plugin.json`, `mcp.json`, `hooks.json`) as pure declarations before writing handler logic.

## 2. Phase 1 Review Gate

- Review the plugin map against framework axioms:
  - No handler blocks interactive chat.
  - Tool schemas are strictly bounded (`additionalProperties: false`).
  - No cyclic event dependencies.

## 3. Phase 2: Implementation & Wiring

- Implement handler functions and tool backends in test-driven fashion (`tdd`).
- Wire handlers to registered event entry points.

## 4. Integration Verification

- Execute hook dispatch tests and tool invocation tests against the wired plugin.
- Build dist tarballs (`make build`) and verify manifest packaging.

## 5. Handover

- Run framework self-test (`framework-self-test`) and compose `wf-handover`.
