---
name: fail-fast-reminder
title: Fail-Fast Reminder
category: template
description: |
  Reminder message shown to agent when a tool returns an error.
  Instructs agent to report error and ask user for guidance.
  No variables.
---
FAIL-FAST REMINDER: This tool returned an error.

Per AXIOMS #7-8 (Fail-Fast):
- DO NOT investigate infrastructure or configuration
- DO NOT search for solutions or workarounds
- DO NOT try to fix the underlying problem

Instead:
- Report the error clearly to the user
- Ask what the user wants you to do

The user may want to fix it themselves, ask you to investigate, or try something else entirely. That's THEIR decision, not yours.
