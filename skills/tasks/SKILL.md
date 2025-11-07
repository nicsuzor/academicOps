---
name: tasks
description: Task lifecycle operations for Basic Memory tasks. Handles creation, prioritization, progress tracking, completion, and strategic alignment. Uses context-search for discovery and bmem-ops for file operations.
license: Apache 2.0
permalink: aops/skills/tasks/skill
---

# Task Management

## Framework Context

@resources/AXIOMS.md

## Overview

Manages complete task lifecycle in Basic Memory format. Uses semantic search (context-search) for discovery and bmem-ops for file operations. Enforces strategic alignment and prevents duplicates.

**Core principle**: Tasks must link to goals. Silent capture without user interruption.

## When to Use This Skill

Use tasks skill for:

- **Creating tasks** from user mentions or emails
- **Finding tasks** via semantic search (not paging through lists)
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
           (context-search)   (bmem-ops) (update)  (notes) (bmem-ops)
```

## Core Operations

### 1. Search for Tasks (ALWAYS DO THIS FIRST)

**Use context-search skill for semantic discovery**:

```
Invoke context-search skill with:
  query: "task description or keywords"
  types: ["task"]
  project: "project-slug" (optional)
```

**DO NOT**:

- Page through task_view.py results
- Use Glob/Grep to find tasks
- Randomly search file system

**Why**: Semantic search finds related tasks even with different wording.

### 2. Create Task

**MANDATORY: Check for duplicates FIRST** (use context-search above)

```
1. Search for similar tasks (context-search)
2. If similar task exists → Update instead of create
3. If no duplicate → Proceed with creation

4. Invoke bmem-ops skill for file creation
5. Use @assets/task-template.md
6. Fill with BM-compliant structure:
   - YAML frontmatter (all required fields)
   - Context section (what needs to be done)
   - Observations (categorized with tags)
   - Relations (project link if applicable)
```

**Task ID format**: `YYYYMMDD-HHMMSS-hostname-uuid`

```bash
# Generate task ID:
date -u +%Y%m%d-%H%M%S-$(hostname -s)-$(uuidgen | cut -d'-' -f1)
```

**Required frontmatter fields**:

```yaml
---
title: Action-oriented task title
permalink: tasks/[TASK_ID]
type: task
tags: [task-type, priority-p1, project:project-slug]
task_id: [TASK_ID]
priority: 1-3
status: inbox
due: "YYYY-MM-DD"
project: project-slug
---
```

**File location**: `$ACADEMICOPS_PERSONAL/data/tasks/inbox/[TASK_ID].md`

### 3. Prioritize Task

**Prioritization Framework** (P1/P2/P3):

**P1 (Today/Tomorrow)** - Immediate action required:

- Action window closing NOW (not just deadline approaching)
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

**Key prioritization factors** (in order):

1. **Temporal constraints**: Due date, action window, meeting dates
2. **Strategic alignment**: Check goals via context-search
3. **Dependencies & roles**: Who's waiting? What's your role?

**CRITICAL**: Distinguish deadline vs action window. A task due Friday may need action TODAY if delay reduces effectiveness.

### 4. Update Task

Use bmem-ops skill to modify task file:

```
1. Invoke context-search to find task
2. Invoke bmem-ops to edit file
3. Update frontmatter (priority, status, due date)
4. Add observation with update note
5. Update modified timestamp
```

### 5. Complete and Archive Task

When task is done:

```
1. Invoke context-search to find task
2. Invoke bmem-ops to:
   - Update status to "completed"
   - Add completion observation
   - Move to data/tasks/archived/
3. If standup-worthy, update accomplishments:
   - File: data/context/accomplishments.md
   - Format: One line unless significant
```

## Task Title Guidelines

**DO**:

- Use action verbs: "Prepare slides", "Review draft", "Respond to inquiry"
- Be specific and scannable
- Keep concise (1-8 words)

**DON'T**:

- Write "Email from X about Y" (not action-oriented)
- Include strategic analysis in title
- Be vague ("Handle things", "Follow up")

**Examples**:

- ✅ "Confirm keynote for Platform Governance Conference"
- ✅ "Review student thesis Chapter 3 and schedule meeting"
- ✅ "Submit talk title for November conference"
- ❌ "Email about conference"
- ❌ "Student wants to meet"
- ❌ "Handle administrative stuff"

## Task Summary Writing

**Write for the USER, not for strategic analysis**.

**Include**:

- What needs to be done (briefly, title already covers this)
- Why it matters (1 sentence)
- When it's due or action window
- Where to find materials (if relevant)

**Don't include**:

- Strategic analysis of priority choices
- Explanations of relationships user already knows
- Role definitions or organizational hierarchy
- Lengthy dependency chains

**Examples**:

✅ **GOOD**: "Prepare keynote slides for Nov 15 conference. Focus on accountability frameworks. Review with team by Nov 10."

❌ **TOO MUCH**: "As the invited keynote speaker for the conference on Nov 15, which aligns with your Academic Profile goal and was mentioned in your current priorities as a strategic initiative for increasing research visibility in the platform governance space, you need to prepare slides focusing on your recent work on accountability frameworks because this represents a key opportunity to advance Goal 2..."

✅ **GOOD**: "Student requesting feedback on Chapter 3 draft. Schedule meeting this week."

❌ **TOO MUCH**: "Meeting request from PhD student (supervision context, Academic Profile goal) regarding Chapter 3 thesis feedback. This represents a P2 priority supervision task that requires review of draft materials and coordination..."

**Detail level**: Write what the user needs to take action, nothing more.

## Strategic Alignment Enforcement

**CRITICAL**: Priority tasks MUST link to goals.

**When creating P1 or P2 tasks**:

```
1. Invoke context-search to find related project
2. Verify project exists
3. Invoke context-search to verify project → goal linkage
4. If misaligned:
   - Create task anyway (don't fail)
   - Add observation noting misalignment
   - Suggest linking to goal or lowering priority
```

**Strategic context to load** (use context-search):

- `type:project` - Find related projects
- `type:goal` - Verify strategic goals
- `data/context/current-priorities.md` - Current focus

**Note**: Strategic alignment validation is a CHECK, not a BLOCKER.

## Common Patterns

### Email → Task Extraction

When extracting tasks from emails:

1. **Search for duplicates** (context-search, NOT task_view.py)
2. Create one task per actionable item (don't combine)
3. Use sender/subject to inform priority:
   - From supervisor → likely P1 or P2
   - "Urgent" in subject → P1
   - Conference/deadline keywords → Check date
   - Administrative → Often P3 unless time-sensitive
4. Include email context in summary: "From: [sender]. Deadline: [date]."

### Conversation → Task Extraction

When extracting tasks from conversations:

1. **Mine deeply**, not just keywords:
   - "I'll need to prepare X" → task
   - "Can you review by Friday?" → task with deadline
   - "Meeting next Tuesday" → task with due date
   - "Need your input on Y" → task
   - Implicit commitments → tasks

2. **Capture immediately** (don't wait for conversation end)
3. Extract fragments even if incomplete (better than missing)

### Task Completion → Accomplishments

When user mentions completing work:

```
1. Invoke context-search to find completed task
2. Invoke bmem-ops to archive task
3. If standup-worthy, update accomplishments:
   File: data/context/accomplishments.md
   Format: One line, "Completed [task title]"
```

**Accomplishments detail level**: "Weekly standup level" - one line unless truly significant.

## Integration with Skills

**context-search** (MANDATORY for discovery):

- Find existing tasks
- Check for duplicates
- Load strategic context
- Verify project/goal linkage

**bmem-ops** (MANDATORY for file operations):

- Create task files
- Update task files
- Move to archived
- Ensure BM format compliance

**scribe** orchestrates tasks for:

- Silent background capture
- Automatic duplicate checking
- Strategic alignment enforcement

## Data Structure

Tasks stored in Basic Memory format:

```
$ACADEMICOPS_PERSONAL/data/
  tasks/
    inbox/                  # New tasks
      [TASK_ID].md
    archived/               # Completed tasks
      [TASK_ID].md
  projects/                 # Project files (for task→project linkage)
    *.md
  goals/                    # Strategic goals (for project→goal linkage)
    *.md
  context/                  # Strategic context
    current-priorities.md
    accomplishments.md
```

## Critical Rules

**NEVER**:

- Create tasks without searching for duplicates first
- Use task_view.py or other Python scripts (use context-search)
- Write files directly (use bmem-ops)
- Include strategic analysis in user-facing summaries
- Skip strategic alignment checks for P1/P2 tasks
- Batch task operations (create/archive immediately)

**ALWAYS**:

- Invoke context-search FIRST for discovery
- Invoke bmem-ops for file operations
- Use action-oriented titles
- Link P1/P2 tasks to projects and goals
- Keep summaries brief and user-focused
- Archive completed tasks promptly
- Load strategic context before prioritizing

## Quick Reference

**Most common workflow**:

```
1. Search for duplicates (context-search skill):
   query: "[task description]"
   types: ["task"]

2. Create task if no duplicate (bmem-ops skill):
   Use @assets/task-template.md
   Fill: title, priority, project, due, summary
   Location: data/tasks/inbox/[TASK_ID].md

3. Archive when complete (bmem-ops skill):
   Update status to "completed"
   Move to data/tasks/archived/
   Update accomplishments if standup-worthy
```

**Priority decision tree**:

```
Q: Action window closing within 24 hours?
YES → P1

Q: Deadline within 7 days OR high strategic value?
YES → P2

Q: Longer timeline OR lower alignment?
YES → P3
```

**Title formula**: `[Action Verb] + [Specific Object] + [Optional Context]`

**Summary formula**: `[What] + [Why, 1 sentence] + [When/Where if relevant]`
