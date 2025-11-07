# Core Architecture

## PROJECT PLANNING: TASKS, PROJECTS, and PRIORITIES

Keep Nic organised with a central hub.

### 1. Strategic Dashboard (Main Hub)

**Purpose**: Single-page visual overview of everything at a glance

**Components**:

- **Monthly Goals Progress** (Progress bars with percentages)
- **Active Projects Status** (Kanban board view)
- **Weekly Focus Areas** (Top 3 priorities this week)
- **Recent Wins** (Completed items auto-populated)
- **Idea Capture Quick Add** (Template button for instant idea entry)

### 2. Projects Database

**Properties**:

- Project Name (Title)
- Status (Select: Planning, Active, On Hold, Completed, Archived)
- Priority (Select: High, Medium, Low)
- Area (Select: Research, Teaching, Writing, Service, Personal)
- Progress (Formula: % of related tasks completed)
- Last Updated (Last edited time)
- Deadline (Date)
- Next Action (Relation to Tasks database)
- Link (URL to corresponding To-Do list)

**Views**:

- **Active Projects Board** (Kanban by Status, filtered to exclude archived)
- **Priority Matrix** (Table grouped by Priority, then Area)
- **Deadline Tracker** (Calendar view)
- **Research Focus** (Filtered to Research area only)

### 3. Tasks Database

**Properties**:

- Task Name (Title)
- Project (Relation to Projects)
- Status (Select: Not Started, In Progress, Waiting, Completed)
- Priority (Select: Urgent, High, Medium, Low)
- Due Date (Date)
- Context (Select: Deep Work, Admin, Communication, Quick Win)
- Energy Required (Select: High, Medium, Low)
- Time Estimate (Number: hours)
- Microsoft To-Do Synced (Checkbox)
- Notes (Rich text)

**Views**:

- **Today's Focus** (Filter: Due today + High priority + In Progress)
- **Context Buckets** (Grouped by Context for batch processing)
- **Energy-Based Planning** (Grouped by Energy Required)
- **Quick Wins** (Filter: Time Estimate ≤ 1 hour, Status = Not Started)

### 4. Ideas Database

**Properties**:

- Idea Title (Title)
- Raw Capture (Rich text - for voice-to-text dumps, fragments)
- Category (Select: Research, Teaching, Writing, Service, Tech, Personal)
- Related Project (Relation to Projects - can be empty)
- Processing Status (Select: New, Categorized, Developed, Implemented, Archived)
- Potential Impact (Select: High, Medium, Low)
- Effort Required (Select: High, Medium, Low)
- Created (Created time)
- Quick Action (Rich text - immediate next step if any)

**Views**:

- **Inbox Triage** (Filter: Processing Status = New, sorted by Created desc)
- **High-Impact Ideas** (Filter: Potential Impact = High, Status ≠ Archived)
- **Quick Implementation** (Filter: Effort = Low, Impact = Medium/High)
- **Research Pipeline** (Filter: Category = Research, grouped by Related Project)

### 5. Progress Tracking Database

**Properties**:

- Week Of (Date)
- Goals Set (Rich text)
- Goals Achieved (Rich text)
- Key Accomplishments (Rich text)
- Challenges (Rich text)
- Next Week Focus (Rich text)
- Energy Level (Select: High, Medium, Low)
- Projects Advanced (Relation to Projects)

## AUTOMATION: agent instructions and workflows

All components must:

- **Integrate through MCP** (ok in LIMITED CASES to use python script, but only create scripts with extensive planning and explicit permission.)
- **Follow error handling strategy** (See [Error Handling](error-handling.md))

### Workflows

Files in `workflows/*.md` are for:

- Executable specifications and instructions
- Architecture decisions and system design
- Reusable templates and patterns
- Configuration and integration details
