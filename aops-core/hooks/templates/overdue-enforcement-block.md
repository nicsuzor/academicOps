---
name: overdue-enforcement-block
title: Compliance Overdue Block Message
category: template
description: |
  Block message when compliance check is overdue and mutating tool attempted.
  Variables:
    {temp_path} - compliance file path
    {tool_calls} - Number of tool calls since last compliance check
---

Compliance check overdue ({tool_calls} tool calls since last check). Run 'custodiet' skill with argument: {temp_path}
