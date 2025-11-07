# bot/docs/ - Agent Instructions for Framework Development

This directory contains agent instructions for working **ON the academicOps framework itself**.

## What Goes Here

- `agents/INSTRUCTIONS.md` - Project-specific context when developing academicOps
- `ARCHITECTURE.md` - Framework design documentation
- Other development-related guides

## What Does NOT Go Here

- Generic agent rules → `bot/agents/_CORE.md`
- User-specific context → `$OUTER/docs/agents/INSTRUCTIONS.md`
- Project-specific instructions → `projects/{name}/docs/agents/INSTRUCTIONS.md`

## When This Loads

Files in `bot/docs/agents/` are for agents working on academicOps framework development. They contain context about open issues, development principles, and framework architecture.

For most users, these files are NOT loaded automatically - they're only relevant when explicitly working on the framework itself.
