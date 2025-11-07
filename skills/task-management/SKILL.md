---
name: task-management
description: Task lifecycle operations for Basic Memory tasks. Handles creation, prioritization, progress tracking, completion, and strategic alignment. Uses context-search for discovery and markdown-ops for file operations.
license: Apache 2.0
permalink: aops/skills/task-management/skill
---

# Task Management

## Framework Context

@resources/SKILL-PRIMER.md @resources/AXIOMS.md

## Overview

Manages complete task lifecycle in Basic Memory format. Coordinates with context-search for discovery and markdown-ops for file operations. Enforces strategic alignment and prevents duplicates.

**Core principle**: Tasks must link to goals. Silent capture without user interruption.

## When to Use This Skill

Use task-management for:

- **Creating tasks** from user mentions or emails
- **Updating tasks** (priority, status, due dates)
- **Completing tasks** and archiving
- **Progress tracking** and notes
- **Strategic alignment** checks
- **Duplicate prevention**

Invoked by scribe subagent during background capture.

## Task Lifecycle

```
Mentioned → Search duplicates → Create → Prioritize → Work → Complete → Archive
             ↓                    ↓         ↓          ↓       ↓
           (context-search)   (markdown-ops) (update)  (notes) (markdown-ops)
```

## Core Operations

### 1. Create Task

**MANDATORY: Check for duplicates FIRST**

```
1. Invoke context-search skill:
   mcp__bm__search_notes(
     query="[task description]",
     types=["task"],
     search_type="text"
   )

2. If similar task exists → Update instead of create
3. If no duplicate → Proceed with creation

4. Invoke markdown-ops skill for file creation
5. Use @assets/task-template.md
6. Fill with BM-compliant structure:
   - YAML frontmatter (title, permalink, type, tags)
   - Context section (what needs to be done)
   - Observations (categorized with tags)
   - Relations (project link if applicable)
```

**Task ID format**: `YYYYMMDD-HHMMSS-hostname-uuid`

```bash
# Generate with:
date -u +%Y%m%d-%H%M%S-$(hostname -s)-$(uuidgen | cut -d'-' -f1)
```

### 2. Prioritize Task

**Prioritization Framework** (P1/P2/P3):

**P1 (Today/Tomorrow)** - Immediate action required:

- Action window closing NOW
- Meeting prep due within 24 hours
- Immediate blocker for others
- Time-sensitive response needed

**P2 (This Week)** - Important, soon:

- Deadline within 7 days
- Significant strategic value
- Preparation needed soon
- Collaborative work where others waiting

**P3 (Within 2 Weeks)** - Lower urgency:

- Longer timeline
- Lower strategic alignment
- No immediate action window

**Key factors**:

1. **Temporal constraints**: Due date, action window, meeting dates
2. **Strategic alignment**: Check project → goal linkage via context-search
3. **Dependencies & roles**: Who's waiting? What's your role? Who has agency?

**Distinguish deadline vs action window**: Task due Friday may need action TODAY if delay reduces effectiveness.

### 3. Update Task

**Use markdown-ops to modify existing task**:

```
1. Invoke context-search to find task
2. Read task file
3. Use Edit tool to update:
   - Priority in frontmatter
   - Due date in frontmatter
   - Add observations for progress notes
   - Update status in frontmatter
```

**Progress notes** (add to Observations section):

```markdown
- [progress] Completed literature review #milestone
- [blocker] Waiting for reviewer feedback #blocked
- [decision] Pivoted to approach B after testing #strategic
```

### 4. Complete Task

**Completion workflow**:

```
1. Invoke context-search to find task
2. Read task to verify completion
3. Add completion observation:
   - [completed] Task finished [date] #done
4. Update status to "completed" in frontmatter
5. Move file from inbox/ to archived/ using bash mv:
   mv data/tasks/inbox/{task-id}.md data/tasks/archived/{task-id}.md
6. Update accomplishments if strategic significance
```

**Accomplishment criteria** (from scribe):

- Task completion (with task ID link)
- Strategic decisions affecting priorities
- Non-task work (minimal, one line)
- "Weekly standup level" - what you'd mention in 30-second update

### 5. Archive Task

**When to archive**:

- Task completed
- Task cancelled/no longer relevant
- Task superseded by another

**Process**:

```bash
# Move to archived directory
mv data/tasks/inbox/{task-id}.md data/tasks/archived/{task-id}.md

# Update status in frontmatter to "archived"
# Add observation explaining why (completed/cancelled/superseded)
```

## Strategic Alignment

**CRITICAL**: All tasks MUST link to projects, and projects MUST link to goals.

**Verification workflow**:

```
1. Task created/updated with project link
2. Invoke context-search:
   mcp__bm__read_note(
     identifier="project-slug",
     project="writing"
   )
3. Check project Relations section for goal links
4. If no goal link → FLAG TO USER
```

**If misaligned, present to user**:

```
"Task '{title}' claims to support project '{project}', but that project
isn't linked to any goal in data/goals/.

Options:
a) Link project to goal (confirm strategic importance)
b) Deprioritize task (not strategically aligned)

Your goals are the source of truth for focus."
```

## Task Summary Writing

**Write for USER resumption, not analysis**:

✅ **GOOD**:

```
Review Joel's chapter draft on marginal value of films
(https://sharepoint.com/...). Focus on storytelling and
platform realities. Provide feedback before supervision meeting.
```

❌ **TOO MUCH**:

```
As the invited keynote speaker for the conference on Nov 15, which
aligns with your Academic Profile goal and was mentioned in your
current priorities, you need to prepare slides...
```

**Include**:

- What needs to be done
- Minimal context (why it matters, briefly)
- When it's due
- Where to find materials (direct links)

**Don't include**:

- Strategic analysis
- Explanations of relationships user knows
- Role definitions
- Dependency chains

## Email Processing Integration

**When scribe processes emails** (via Outlook MCP):

```
1. Scribe reads email via MCP
2. Scribe extracts:
   - Action required? → Task
   - Project mention? → Context
   - Deadline? → Due date
   - Strategic importance? → Priority

3. Scribe invokes task-management
4. task-management checks duplicates (context-search)
5. task-management creates task (markdown-ops)
6. task-management links to project if mentioned
```

**Task metadata from email**:

- `metadata.email_id` - Email identifier
- `metadata.sender` - Sender email
- `metadata.sender_name` - Sender display name
- `type: email_reply` - Task type
- `tags: [email_reply]` - Categorization

## Integration with Other Skills

**context-search** (MANDATORY before operations):

- Find existing tasks (prevent duplicates)
- Search by project/goal
- Verify strategic alignment
- Build context for prioritization

**markdown-ops** (MANDATORY for file operations):

- Create task files in BM format
- Update task files
- Validate BM syntax
- Use templates

**scribe subagent** (orchestrator):

- Invokes task-management when task detected
- Provides extracted information
- Handles silent execution
- Manages user interruption avoidance

## Critical Rules

**NEVER**:

- Create task without checking duplicates first
- Create task without project/goal linkage (if strategic)
- Write files directly (use markdown-ops)
- Use Glob/Grep (use context-search)
- Interrupt user flow to ask questions
- Create tasks for infrastructure work (that's git log)

**ALWAYS**:

- Invoke context-search FIRST for discovery
- Invoke markdown-ops for file operations
- Verify strategic alignment (task → project → goal)
- Use templates from assets/
- Add observations for progress
- Link to projects using `part_of [[Project]]`
- Archive completed tasks
- Check accomplishment criteria

## Quick Reference

**Create task workflow**:

```
1. context-search: Check duplicates
2. markdown-ops: Use task-template.md
3. Fill: title, priority, project, due, summary
4. Verify: project → goal linkage
5. Save: data/tasks/inbox/{task-id}.md
```

**Update task**:

```
1. context-search: Find task
2. Read current content
3. Edit: Update fields/add observations
4. Save
```

**Complete task**:

```
1. context-search: Find task
2. Add completion observation
3. Update status: "completed"
4. Move: inbox/ → archived/
5. Update accomplishments if strategic
```

**Prioritize**:

```
P1: Today/tomorrow (action window closing)
P2: This week (deadline <7 days, strategic)
P3: Within 2 weeks (longer timeline)
```
