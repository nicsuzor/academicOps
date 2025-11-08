---
title: Core Agent Instructions
type: agent-instructions
description: Universal agent instructions loaded at SessionStart via three-tier system.
  References chunks/ for axioms, infrastructure, and behavioral rules.
tags:
- core
- agent-instructions
- sessionstart
- framework
relations:
- '[[chunks/AXIOMS]]'
- '[[chunks/INFRASTRUCTURE]]'
- '[[chunks/AGENT-BEHAVIOR]]'
permalink: a-ops/docs/unused/core/core
---

# Generic Agent Instructions

<!-- This file is read on every session start. Keep it short. -->

## Universal Principles

@../chunks/AXIOMS.md

## Framework Infrastructure

@../chunks/INFRASTRUCTURE.md

## Agent-Specific Behavior

@../chunks/AGENT-BEHAVIOR.md

---

**Note**: Skills do NOT receive this file via SessionStart hooks. Skills access shared context via `@resources/` symlinks to chunks/.