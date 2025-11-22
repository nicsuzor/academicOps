---
description: Make minor adjustments to memory/instructions for future agents
permalink: commands/learn
---

**IMMEDIATELY** invoke the `framework` skill. The user wants to update memory/instructions with a minor adjustment.

**Purpose**: Update existing documentation or add minimal context so future agents discover needed information just-in-time.

**NOT FOR BEHAVIOR PATTERNS**: Use `/log` for agent behavior patterns. Use `/learn` for memory/instruction adjustments.

**CRITICAL - Minimal Documentation Mode**: You MUST:

✅ **DO**:

- **Check if information already exists** - UPDATE rather than duplicate
- Determine WHERE this lesson belongs (thematic learning files at `$ACA_DATA/projects/aops/learning/` for patterns, SKILL.md for workflows, other docs for specific guidance)
- Ask: "When would an agent need this information?" - file it there
- Keep it minimal (3 sentences max)
- Make it discoverable (tags, location, clear title)
- Focus on WHAT the agent needs to know, not WHY we learned it

❌ **DO NOT**:

- Add duplicate information when you should UPDATE existing content
- Write lengthy explanations or background
- Add information "just in case" - only what's needed
- Create new files without justification
- Violate single source of truth principle
- Add to `AXIOMS.md` - principles require explicit user decision
- Log behavior patterns here - use `/log` for that
- Add to root `CLAUDE.md`, `CORE.md`, etc. unless absolutely necessary

**Filing Decision Tree**:

1. **Is it a workflow step for specific skill?** → That skill's `SKILL.md` (update if exists, add if new)
2. **Is it project/directory-specific context?** → That directory's `CLAUDE.md` (if exists, or consider creating)
3. **Is it context about a specific tool/integration?** → Appropriate reference doc in that skill (update if exists)
4. **Is it general framework guidance?** → Framework README or skill reference docs (update existing section)

**NEVER add to**:

- `AXIOMS.md` - Principles are too important, require explicit user decision
- Thematic learning files directly - Use `/log` command for behavior patterns
- Root `CLAUDE.md` - Only for high-level directives, avoid bloat

**Just-In-Time Principle**:

Information should appear when agents need it, not proactively. Ask:

- "When does an agent encounter this situation?"
- "What's the minimal info needed to handle it correctly?"
- "Can they discover this via existing docs/logs when needed?"

**Example Good Lessons** (minor instruction updates):

- "Task scripts require `uv run python` from repo root" → tasks/SKILL.md
- "Outlook MCP reads email threads with full history" → Reference doc in outlook skill
- "Project X uses custom config format Y" → projects/X/CLAUDE.md

**Example Bad Lessons** (use `/log` instead):

- "Agent deleted log entries during merge conflict" → Use `/log`, this is a behavior pattern
- "Agent ignored user's explicit tool choice" → Use `/log`, this is a behavior pattern
- "Never use --no-verify except when requested" → Use `/log`, this is a behavior pattern

**Example Bad Lessons** (too broad, creates bloat):

- "Here's everything about git hooks" → Too much, agents can read docs
- "User prefers X approach" → Too vague, needs specific context
- "We tried Y and it failed" → Use `/log` if it's a pattern, otherwise skip
