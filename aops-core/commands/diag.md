---
name: diag
category: instruction
description: Quick diagnostic check of what's currently loaded in this session
allowed-tools: None
permalink: commands/diag
---

**Purpose**: Quick diagnostic check of what's currently loaded in this session.

**NOT a skill**: This is a diagnostic command only - for framework operations, invoke `[[skills/framework/SKILL.md|framework]]` skill.

**Respond IMMEDIATELY from current state. Do NOT read any files.**

List what you currently have loaded:

## 1. Skills Available

List all skills from the Skill tool's Available Commands section.

## 2. Slash Commands Available

List all commands from the SlashCommand tool's Available Commands section.

## 3. Task Subagent Types

List all subagent_type values from the Task tool description.

## 4. MCP Tools

List MCP server prefixes you have access to (e.g., mcp__memory__, mcp__gh__).

## 5. Files Referenced This Session

List any files that were:

- **[FULL]** - Full content provided in context
- **[READ]** - You explicitly read with Read tool
- **[REF]** - Only filename/path mentioned, not read

Format as a quick reference table or bullet list. Be concise.
