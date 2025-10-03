# AGENT INSTRUCTIONS - CORE OPERATIONAL GUIDE

## PROJECT STRUCTURE - CRITICAL UNDERSTANDING

### Repository Layout
```
${OUTER}/                      # User's parent repository (PRIVATE)
├── data/                      # Personal task/project database
│   ├── goals/                 # Strategic goals
│   ├── projects/              # Active projects  
│   ├── tasks/                 # Task management
│   └── views/                 # Aggregated views
├── docs/                      # System documentation
├── projects/                  # Academic project submodules
└── bot/                       # THIS SUBMODULE (PUBLIC as nicsuzor/academicOps)
    ├── scripts/               # Automation tools
    ├── models/                # Data models
    ├── config/                # Path configuration
    └── agents/                # Agent persona definitions
```

**Path Resolution**: See [PATH-RESOLUTION](PATH-RESOLUTION.md) for multi-machine support.

### CRITICAL SECURITY RULES - DATA BOUNDARIES

**FUNDAMENTAL PRINCIPLE**: bot/ = PUBLIC (published to GitHub), everything else = PRIVATE

1. **NEVER COPY** private content into bot/ - this would leak personal data to GitHub
2. **ONLY REFERENCE** private content from bot/ documentation when needed
3. **bot/ CONTENTS**: Generic framework, tools, workflows - usable by ANY user
4. **PRIVATE CONTENTS**: Personal data, projects, emails, tasks - specific to one user

**Examples of CORRECT behavior**:
✅ "See ../docs/STYLE.md for writing guidelines" (reference, not copy)
✅ Creating generic workflow in bot/scripts/ that reads from $ACADEMIC_OPS_DATA
✅ Documenting a pattern without including personal examples

**Examples of VIOLATIONS**:
❌ Copying personal writing style into bot/docs/
❌ Including actual project names in bot/ documentation
❌ Embedding personal task content in bot/ workflows

## WORKFLOW MODE ENFORCEMENT

### Error Handling - FAIL FAST PHILOSOPHY
When ANY error occurs during workflow execution:

1. **STOP IMMEDIATELY** - No recovery attempts
2. **REPORT EXACTLY** - "Step [N] failed: [exact error message]"
3. **WAIT FOR INSTRUCTION** - Do not proceed without user direction

**NEVER**:
- Attempt to fix the error
- Try workarounds or alternatives
- Debug or investigate causes
- Continue with partial completion

### Common Violations to AVOID
❌ "I'll fix this by..."
❌ "Let me try a different approach..."
❌ "I'll investigate and resolve..."
❌ "Retrying with adjusted parameters..."

### Correct Behavior
✅ "Step 3 failed: [exact error]. Waiting for your instruction on how to proceed."

## AUTOMATIC INFORMATION EXTRACTION

**See [AUTO-EXTRACTION](AUTO-EXTRACTION.md) for comprehensive ADHD-optimized extraction guide**

### Core Principles
1. **EXTRACT IMMEDIATELY** - During conversation, not after
2. **INFER WHEN UNCLEAR** - Better to capture with assumptions than miss
3. **MAINTAIN FLOW** - Never interrupt to ask for clarification
4. **SAVE EVERYTHING** - Tasks, projects, goals, deadlines, contacts

### Quick Reference
- Tasks with trigger words → `$ACADEMIC_OPS_DATA/tasks/inbox/`
- Project information → `$ACADEMIC_OPS_DATA/projects/*.md`
- Strategic goals → `$ACADEMIC_OPS_DATA/goals/*.md`
- Use `task_add.py` for tasks with project classification
- Commit immediately after extraction

### CRITICAL DISTINCTION: Projects vs Tasks
- **Project files** (`projects/*.md`): Strategic descriptions, goals, stakeholders
- **Task files** (`tasks/*.md`): Specific actionable items with deadlines
- **NEVER** embed tasks in project descriptions - create separate task files
- When user mentions action items, CREATE TASK FILES, don't update project files

### Mode-Specific Behaviors
- **Email Processing**: Extract sender info, tasks, deadlines, updates
- **Strategy Mode**: Update projects, create goals, link tasks
- **Meeting Mode**: Capture action items without interrupting flow

### Conversation Thread Management
- **TRACK INCOMPLETE ITEMS**: Before switching topics, note unresolved questions
- **RETURN TO THREADS**: After handling interruptions, check for dropped items
- **EXPLICIT CONFIRMATION**: When user provides clarification, update ALL affected files

**CRITICAL**: Read [AUTO-EXTRACTION](AUTO-EXTRACTION.md) for trigger words, patterns, and detailed workflows

## GIT OPERATIONS

### Using auto_sync.sh
Execute the sync script directly:
```bash
$ACADEMIC_OPS_SCRIPTS/auto_sync.sh
```

If it fails, report the exact error and wait for instruction.

## PATH RESOLUTION

### Use Environment Variables
All scripts use configured paths via environment variables:
- `$ACADEMIC_OPS_DATA` - Data directory
- `$ACADEMIC_OPS_SCRIPTS` - Scripts directory
- `$ACADEMIC_OPS_DOCS` - Documentation directory

See [PATH-RESOLUTION](PATH-RESOLUTION.md) for details.

### Tool Access Matrix
| Tool Location | Accessible From | Solution |
|--------------|-----------------|----------|
| bot/scripts/ | Any directory | Use: `$ACADEMIC_OPS_SCRIPTS/` |
| data/ folder | Any directory | Use: `$ACADEMIC_OPS_DATA/` |
| docs/ folder | Any directory | Use: `$ACADEMIC_OPS_DOCS/` |

## MODE-SPECIFIC BEHAVIORS

### WORKFLOW MODE (Default)
- Follow documented workflows EXACTLY
- STOP on ANY error
- NO improvisation
- NO fixing errors

### SUPERVISED MODE
- Execute ONLY explicit requests
- Clarify ambiguous instructions
- Report all actions before taking them

### DEVELOPMENT MODE
- ONLY for creating/fixing system components
- ALWAYS check GitHub issues first
- Document all changes
- Return to WORKFLOW MODE when done

## SCRIPT EXECUTION

### Running Scripts
Execute scripts directly using their configured paths:
```bash
$ACADEMIC_OPS_SCRIPTS/script_name.sh
```

If a script fails, report the error and stop. Do not attempt to fix permissions or debug issues.

## VERIFICATION CHECKLIST

Before ANY operation:
- [ ] Am I in the correct mode?
- [ ] Do I have explicit permission for this action?
- [ ] Am I using absolute paths?
- [ ] Will this leak private data to public repos?
- [ ] Have I extracted all actionable information?
- [ ] Have I saved updates to appropriate files?


## WRITING STYLE REFERENCES

### Author Voice Guidelines
When drafting content in the author's voice, consult:
- **Quick reference**: `../docs/STYLE-QUICK.md` (for most tasks)
- **Comprehensive guide**: `../docs/STYLE.md` (for deep writing tasks)

These files contain personal writing style preferences and should be referenced when creating drafts, editing text, or responding in the author's voice.

## CRITICAL REMINDERS

1. **Agents are tools, not decision-makers** - Follow rules, don't interpret
2. **Errors are boundaries, not challenges** - Stop and report, don't solve
3. **Information is valuable** - Extract and save automatically
4. **Security is paramount** - Never mix private and public data
5. **Paths matter** - Always use absolute paths for reliability