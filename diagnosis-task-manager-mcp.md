# Diagnosis: task-manager MCP Tool Discovery Failure

## Evidence

**From user's transcript** (task-manager attempting email processing):
```
⎿ Bash(uv run mcp-client-cli list_tools mcp-outlook-mail)
   Error: Exit code 2 - No such file or directory

⎿ Bash(env | grep -i mcp)
   No matches found

⎿ Read(file_path: "/home/nic/.config/claude/claude_desktop_config.json")
   Error: File does not exist

⎿ Search(pattern: "**/claude*.json", path: "/home/nic/.config")
```

**Actual MCP configuration** (`~/.claude/mcp.json`):
- MCP server `outlook` is configured (line 49-58)
- Uses `uvx fastmcp run http://nicwin.stoat-musical.ts.net:8023/mcp`
- Tools are available as `mcp__outlook__*` (confirmed in email skill)

**Email skill documentation** (`~/.claude/skills/email/SKILL.md:16-21`):
```markdown
- **`mcp__outlook__messages_index`** - Overview of inboxes and folders
- **`mcp__outlook__messages_list_recent`** - List recent emails
- **`mcp__outlook__messages_get`** - Read specific email content
- **`mcp__outlook__messages_query`** - Search emails with filters
```

## Root Cause

**Agent attempted tool discovery instead of using skills**

Task-manager violated its own constraint:
- Instruction (line 65-67): "For ALL email operations, use email skill"
- Actual behavior: Tried to discover MCP tools manually before invoking email skill

## Why This Happened

**Hypothesis 1: Agent doesn't understand tool visibility**
- MCP tools are ALREADY in the agent's tool list
- No need to "discover" them - they're directly callable
- Agent thought it needed to find config/enumerate tools first

**Hypothesis 2: Agent bypassed skills**
- Should have invoked `Skill(command="email")` FIRST
- Email skill would have told it to use `mcp__outlook__messages_list_recent`
- Instead, agent tried to be "smart" and discover tools itself

**Hypothesis 3: Agent confused about tool access**
- Doesn't know that MCP tools are directly available
- Tried to use CLI tool (`mcp-client-cli`) that doesn't exist
- Looked for Desktop app config instead of understanding MCP is already integrated

## What Should Have Happened

**Correct workflow** (from task-manager.md:88-95):
```
1. Invoke `Skill(command="email")` to load email expertise
2. Follow email skill instructions to list recent messages
3. Follow email skill instructions to filter/prioritize
4. Follow email skill instructions to read high-priority content
```

**After invoking email skill**, agent would see (from email/SKILL.md:39-46):
```markdown
### 2. List Recent Emails

To retrieve recent emails from inbox:

```python
mcp__outlook__messages_list_recent(
    folder="inbox",
    limit=20
)
```
```

## The Fix

**NOT a permissions issue** - MCP tools are already available to the agent

**NOT an instruction clarity issue** - Instructions are clear: "use email skill"

**IS an execution issue** - Agent didn't follow instructions to invoke skill FIRST

### Required Changes

**Option 1: Add explicit pre-flight check to task-manager**
Add to task-manager.md after line 68:
```markdown
**DO NOT** attempt to discover or enumerate MCP tools yourself. MCP tools are already available to you. Simply invoke the email skill to learn which tools to use.
```

**Option 2: Strengthen email skill invocation requirement**
Update task-manager.md lines 90-95:
```markdown
### 1. Fetch and Read Emails

**FIRST**: Invoke `Skill(command="email")` to load email expertise
- DO NOT attempt to discover MCP tools yourself
- DO NOT search for MCP configuration
- MCP tools are already available - the skill will tell you which ones to use

**THEN**: Follow email skill instructions to:
1. List recent messages using the tool the skill specifies
2. Filter/prioritize based on skill guidance
3. Read high-priority content using the tool the skill specifies
```

**Option 3: Add tool awareness to agent instructions**
Add after "Core Identity" section (line 25):
```markdown
## Tool Awareness

**MCP tools are directly available to you** - no discovery needed:
- MCP server configuration is handled automatically
- Tools appear in your tool list with `mcp__` prefix
- DO NOT attempt to enumerate, discover, or search for MCP tools
- DO NOT look for configuration files or environment variables

**To use MCP tools**: Invoke the appropriate skill (email, tasks, etc.) which will tell you exactly which MCP tools to call.
```

## Recommendation

**Implement Option 3** (Tool Awareness section) because:
1. Most explicit about agent's capabilities
2. Prevents future "discovery" attempts
3. Reinforces skill-first workflow
4. Addresses root misconception directly

**Also add Option 1** (explicit prohibition) to doubly prevent the bad pattern.

## Success Criteria

After fix, agent should:
1. Invoke `Skill(command="email")` immediately when asked to process emails
2. NOT attempt any tool discovery/enumeration
3. NOT search for config files or environment variables
4. Follow email skill guidance to call `mcp__outlook__messages_list_recent` directly

## Testing

**Test case**: `/email` command
**Expected**:
```
1. Agent invokes Skill(command="email")
2. Agent calls mcp__outlook__messages_list_recent(limit=30)
3. Agent processes emails
4. Agent invokes Skill(command="tasks")
5. Agent creates tasks as appropriate
```

**NOT expected**:
- Any Bash commands to discover tools
- Any Read commands for config files
- Any attempts to enumerate MCP servers

---

## Implementation Results

### Changes Made to task-manager.md

**1. Added Tool Awareness section** (after Core Identity, line 27-36):
- Explains MCP tools are directly available with `mcp__` prefix
- Explicit prohibition against discovery/enumeration
- Directive to invoke skills FIRST

**2. Strengthened "Use Skills Exclusively" section** (line 80-84):
- Added explicit DO NOT list with 4 prohibited behaviors
- Prohibits tool discovery before invoking email skill
- Prohibits searching for MCP config or env vars
- Prohibits running any "discovery" commands

**3. Enhanced Email Processing Workflow** (line 107-116):
- Split into "FIRST" and "THEN" sections
- Explicit step-by-step prohibition of tool discovery
- Reinforces that MCP tools are already available
- Emphasizes skill-first workflow

### Net Impact
- **+22 lines** of explicit guidance
- Three reinforcement points (Tool Awareness, Use Skills Exclusively, Workflow)
- Addresses root misconception at multiple levels

### Other Agents Requiring Similar Updates

**STRATEGIST agent** (`agents/STRATEGIST.md`):
- Lines 3, 24, 127-132, 229-230, 259, 269, 287, 301, 305 reference email skill
- Currently says "use email skill" but doesn't explain Skill(command="email") syntax
- Would benefit from same Tool Awareness section
- Needs explicit prohibition against tool discovery

**scribe agent** (`agents/scribe.md`):
- Lines 3, 42-44 reference tasks skill
- Says "invoke tasks skill" but doesn't show Skill(command="tasks") syntax
- Does NOT use email skill (only tasks)
- Lower risk but could still benefit from skill invocation guide reference

**Recommendation**:
1. Add Tool Awareness section to STRATEGIST (uses MCP via email skill)
2. Add reference to skill-invocation-guide.md in both STRATEGIST and scribe
3. Monitor for similar patterns in future agents

### Success Criteria
- [ ] Test task-manager with `/email` command
- [ ] Verify no tool discovery attempts
- [ ] Verify Skill(command="email") invoked first
- [ ] If successful, apply similar pattern to STRATEGIST
- [ ] Document experiment results in `/home/nic/.claude/experiments/2025-11-02_task-manager-skill-invocation-fix.md`
