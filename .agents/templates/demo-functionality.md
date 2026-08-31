---
title: Live Framework Demonstration
type: template
category: process
description: Demonstrate a framework mechanism live on real state with narrated steps and visible output. Select when demonstrating how a feature works; not for explaining abstract theory or modifying code.
tags: [demo, dogfood, walkthrough, framework, process]
---

# Process: Live Framework Demonstration

Live, read-only walkthrough demonstrating framework mechanisms in operation.

## 1. Scope and Target Selection

- Identify the specific mechanism, command, or workflow to demonstrate (`<target-mechanism>`).
- Ensure target environment and test fixtures are configured and initialized.

## 2. Live Step Execution

- Execute each step in sequence using real CLI commands or tools.
- Display actual verbatim command outputs, exit codes, and generated artifacts.
- Narrate key decision points and state transitions as they occur.

## 3. Boundary and Edge Case Demonstration

- Demonstrate system behavior under edge conditions or invalid inputs.
- Show error recovery and fail-safe mechanisms in action.

## 4. Summary and Teardown

- Summarize demonstrated capabilities and operational takeaways.
- Clean up transient test artifacts without modifying persistent system state.
