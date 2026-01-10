---
name: remind
category: instruction
description: Queue agent work to bd for later execution
allowed-tools: Bash,mcp__memory__retrieve_memory
permalink: commands/remind
---

# /remind - Queue Agent Work

**Purpose**: Capture work for agents to do later, stored in bd issues.

**Distinction from /q**:

- `/q` = user tasks → task system (markdown files)
- `/remind` = agent work → bd issues (`.beads/issues.jsonl`)

## Workflow

1. **Determine prefix** from current repo:
   - `~/src/academicOps` → `aops`
   - Otherwise → `ns`

2. **Search existing issues**: `bd search "[keywords]"`

3. **If related issue exists**: Update it with `bd update <id> --description "..."`

4. **If no related issue**: Create new issue:
   ```bash
   bd create --title "[concise title]" --type task --priority 2 --label agent-work --body "[details]"
   ```

5. **DO NOT execute** the work now. Issue queued for future sessions.

## Key Rules

- Always search first to avoid duplicates
- Use `--label agent-work` to distinguish from other issues
- Keep titles concise (< 80 chars)
- Include context in body (why this matters, what triggered it)
- Default priority 2 unless user specifies otherwise
