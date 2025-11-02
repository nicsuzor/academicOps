# Skill Invocation Guide for Agents

## The Three-Layer Distinction

**Understanding what tools are available to you:**

1. **Tools** - Direct capabilities you can call
   - Examples: `Bash`, `Read`, `Edit`, `mcp__outlook__messages_list_recent`
   - Usage: Call directly in tool invocation blocks

2. **Skills** - Expertise modules with instructions (NOT directly callable)
   - Examples: `email`, `tasks`, `scribe`
   - Location: `~/.claude/skills/*/SKILL.md`
   - Usage: Must be invoked via `Skill` tool (see below)

3. **Skill Tool** - The bridge between you and skills
   - Name: `Skill`
   - Purpose: Loads skill instructions into your context
   - Usage: Call `Skill` tool with `command` parameter = skill name

## How to Invoke a Skill

**When instructions say "use the email skill"**, this means:

1. Invoke the `Skill` tool with `command="email"`
2. The skill's instructions will load into your context
3. Then follow those instructions (which may involve calling MCP tools)

**Example: Using the email skill**

```
Step 1: Invoke the skill to load expertise
→ Call Skill tool with command="email"
→ Email skill instructions now available

Step 2: Follow skill's instructions
→ Email skill says: "Use mcp__outlook__messages_list_recent to fetch emails"
→ Now call mcp__outlook__messages_list_recent directly
```

## Concrete Examples

### Example 1: Email Skill Workflow

**Instruction**: "Use email skill to fetch recent emails"

**What you do**:
1. First, invoke Skill tool: `Skill(command="email")`
2. Read the skill instructions that load
3. Follow the skill's guidance to call: `mcp__outlook__messages_list_recent(limit=30)`
4. Process results as skill instructs

### Example 2: Tasks Skill Workflow

**Instruction**: "Use tasks skill to create a task"

**What you do**:
1. First, invoke Skill tool: `Skill(command="tasks")`
2. Read the skill instructions that load
3. Follow the skill's guidance to run: `Bash("uv run python ~/.claude/skills/scribe/scripts/task_add.py ...")`
4. Verify creation as skill instructs

### Example 3: Combined Workflow (Email → Tasks)

**Instruction**: "Use email skill to fetch emails, then use tasks skill to create tasks"

**What you do**:
1. Invoke `Skill(command="email")` → Read email skill instructions
2. Call `mcp__outlook__messages_list_recent()` as email skill instructs
3. Invoke `Skill(command="tasks")` → Read tasks skill instructions
4. Call `Bash("uv run python ... task_add.py ...")` as tasks skill instructs

## Common Mistake: Calling Skill Instead of Tool

**WRONG**: Trying to call `email` or `tasks` directly
→ These are NOT tools, they're skill names

**CORRECT**: Call `Skill` tool with skill name as parameter
→ `Skill(command="email")` loads the email skill's instructions

## When to Use Skill Tool vs Direct Tools

**Use Skill tool when**:
- Instructions say "use the X skill"
- You need expertise/guidance for a domain (email, tasks, etc.)
- You're unsure HOW to do something

**Use direct tools when**:
- You already know HOW (from skill instructions or your own knowledge)
- Performing specific operations (Bash, Read, Edit, MCP tools)
- Skill instructions tell you to call specific tools

## Quick Reference

**Skills load expertise, tools execute operations**

- `Skill(command="email")` → Loads email handling expertise
- `mcp__outlook__messages_list_recent()` → Actually fetches emails
- `Skill(command="tasks")` → Loads task management expertise
- `Bash("uv run python ... task_add.py")` → Actually creates task

**Pattern**: Skill first (learn HOW), then tools (DO it)
