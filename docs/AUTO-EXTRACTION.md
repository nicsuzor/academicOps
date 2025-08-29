# AUTOMATIC INFORMATION EXTRACTION GUIDE

## CORE PRINCIPLE
Extract and save actionable information IMMEDIATELY without waiting for user prompts.

## WHAT TO EXTRACT

### Tasks
**Trigger Words**: "need to", "should", "must", "will", "todo", "task", "reminder", "next month", "by [date]", "prepare for", "abstract for"
**Contextual Triggers**: 
- Upcoming events mentioned (keynotes, conferences, meetings)
- Deadlines discussed even without explicit task language
- "Next actions" sections in project discussions
**Action**: Create task file in `/home/nic/src/writing/data/tasks/inbox/`
**Format**:
```markdown
---
created: YYYY-MM-DD
project: [project-name if mentioned]
priority: [if mentioned]
deadline: [if mentioned]
---
# [Task title]

[Task description]
```

### Project Information
**Trigger**: Discussion about ongoing work, collaborations, deliverables, project assessments
**Action**: Update `/home/nic/src/writing/data/projects/[project-name].md`
**Information to Capture**:
- Collaborator names and contact info
- Deadlines and milestones
- Key decisions or changes
- Resources and references
- Next actions
- **Resource allocations** (team member time, percentages)
- **Strategic assessments** ("high risk/reward", "inefficient", etc.)
- **Dependencies and blockers**
- **Emotional/energy assessments** ("stressed about", "excited by")

### Goals and Strategy
**Trigger**: Discussion about objectives, vision, priorities
**Action**: Update `/home/nic/src/writing/data/goals/[goal-name].md`
**Information to Capture**:
- Theory of change
- Success metrics
- Supporting projects
- Strategic priorities

### Contacts
**Trigger**: Names, email addresses, organizational affiliations
**Action**: Add to relevant project files under "## Contacts" section
**Format**:
```markdown
## Contacts
- **[Name]** ([Organization]): [email] - [context/role]
```

## EXTRACTION RULES

### 1. Extract During Conversation (ADHD-OPTIMIZED)
Don't wait until the end. As information appears:
1. Identify the category (task/project/goal/contact)
2. Extract the relevant details
3. Save to appropriate file
4. Continue with conversation
5. **DO NOT interrupt flow to ask for clarification** - capture what you have
6. **Inference is better than missing data** - make reasonable assumptions from context

### 2. Be Comprehensive
Extract ALL actionable information, including:
- Explicit tasks ("I need to do X")
- Implicit tasks ("X is overdue")
- Contextual information (deadlines, people, resources)
- Strategic insights (priorities, concerns, opportunities)

### 3. Maintain Context
When extracting:
- Link tasks to projects
- Link projects to goals
- Preserve relationships between items
- Include source context (email subject, meeting topic)

### 4. Project Classification

Use the task_add.sh script with appropriate project parameter:
```bash
$ACADEMIC_OPS_SCRIPTS/task_add.sh "Task description" "project-name"
```

If uncertain about project classification, list available projects and ask user:
```bash
ls $ACADEMIC_OPS_DATA/projects/
# Show user the list and ask which project fits

## MODE-SPECIFIC BEHAVIORS

### Email Processing Mode
```python
for email in emails:
    extract_sender_info()  # Add to contacts
    extract_tasks()        # Create task files
    extract_deadlines()    # Add to tasks/projects
    extract_project_updates()  # Update project files
    save_all_extracted_info()
```

### Strategy Mode
```python
while in_strategy_discussion:
    if new_project_mentioned:
        create_or_update_project_file()
    if goal_discussed:
        update_goal_file()
    if priority_changed:
        update_priority_in_project()
    if task_identified:
        create_task_with_project_link()
```

### Meeting/Conversation Mode
```python
during_conversation:
    listen_for_actionable_items()
    extract_immediately()
    save_without_interrupting_flow()
    summarize_extracted_at_end()
```

## FILE OPERATIONS

### Creating New Task
Use the task_add.sh script:
```bash
$ACADEMIC_OPS_SCRIPTS/task_add.sh "Task description" "project-name"
```

### Updating Project File
Use direct file editing with the Edit tool to append information to project files.

## VALIDATION CHECKLIST

After any conversation/email/meeting:
- [ ] Did I extract all mentioned tasks?
- [ ] Did I update relevant project files?
- [ ] Did I capture new contacts?
- [ ] Did I note important deadlines?
- [ ] Did I link tasks to projects?
- [ ] Did I save everything with absolute paths?

## COMMON PATTERNS TO RECOGNIZE

### Academic Collaboration Pattern
```
"I've discussed with [Name] about [Topic]..."
→ Extract: Contact info, project details, next steps
```

### Deadline Pattern
```
"This needs to be done by [Date]..."
→ Extract: Task with deadline, add to project timeline
```

### Strategic Priority Pattern
```
"The most important thing is..."
→ Extract: Update goal priority, reorder project priorities
```

### Feedback Pattern
```
"[Person] suggested that we..."
→ Extract: Feedback as project note, potential task
```

## PATH USAGE

### Use Environment Variables
```bash
# Use configured paths
$ACADEMIC_OPS_DATA/tasks/...
$ACADEMIC_OPS_DATA/projects/...
$ACADEMIC_OPS_SCRIPTS/...
```

### Always Commit After Extraction
```bash
cd /home/nic/src/writing
git add -A
git commit -m "Auto-extracted information from [source]"
```

### Always Verify Extraction
After saving, confirm:
1. File was created/updated
2. Information is complete
3. Links are correct
4. Commit succeeded

## REPORTING

At the end of any session, report:
```
Extracted and saved:
- X new tasks created
- Y projects updated
- Z contacts added
- All changes committed to git
```