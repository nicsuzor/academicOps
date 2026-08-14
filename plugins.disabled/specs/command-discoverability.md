---
title: Command Discoverability
type: spec
category: spec
status: Implemented
permalink: command-discoverability
tags:
  - framework
  - ux
  - discoverability
---

# Command Discoverability

## User Story

As a framework user, I should be able to easily find out what commands to use within Claude Code to achieve the tasks I want.

## Solution

**README.md is the single source of truth** for framework capabilities. Users invoke `/aops` to see it.

## Acceptance Criteria

1. `/aops` outputs README.md content
2. README.md contains complete, current inventory of:
   - All slash commands with purpose and invocation
   - All skills with purpose and invocation
   - All agents with purpose and invocation
   - Quick start / entry points for common tasks
3. README.md is written for USERS (not developers) - focuses on "how do I accomplish X?"
4. README.md stays current when capabilities change (part of framework skill workflow)

## Implementation

- [x] `/aops` command created - outputs README.md
- [x] README.md audit - all 17 commands, 24 skills, 5 agents verified
- [x] README.md restructure - added "Common Tasks" section mapping goals → commands

## Maintenance

When adding/removing/changing commands, skills, or agents:

1. Update README.md tables as part of the change
2. Framework skill workflow should enforce this
