---
name: overdue-enforcement-block
title: Compliance Overdue Block Message
category: template
description: |
  Block message when compliance check is overdue and mutating tool attempted.
  Variables:
    {tool_calls} - Number of tool calls since last compliance check
---
Compliance check overdue ({tool_calls} tool calls since last check). Spawn custodiet agent before continuing with mutating operations.
