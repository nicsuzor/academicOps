# AGENT INSTRUCTIONS - CORE OPERATIONAL GUIDE

## PROJECT STRUCTURE - CRITICAL UNDERSTANDING

### Repository Layout
```
$ACADEMIC_OPS_ROOT/            # User's parent repository (PRIVATE)
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
    └── .claude/.gemini/       # Agent configs
```

**Path Resolution**: See [PATH-RESOLUTION](PATH-RESOLUTION.md) for multi-machine support.

### CRITICAL SECURITY RULES
1. **NEVER** leak data from parent repository into the public `bot/` submodule
2. **ALWAYS** verify current working directory before operations
3. **UNDERSTAND**: Agents invoked from different folders have different access permissions
4. **SOLUTION**: Use path resolution system - see [PATH-RESOLUTION](PATH-RESOLUTION.md)

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

### When Processing Conversations/Emails
1. **IDENTIFY** key information categories:
   - Tasks → Create in `$ACADEMIC_OPS_DATA/tasks/inbox/`
   - Project updates → Update `$ACADEMIC_OPS_DATA/projects/*.md`
   - Goals/strategies → Update `$ACADEMIC_OPS_DATA/goals/*.md`
   - Deadlines → Add to relevant project/task files
   - Contacts → Note in project files

2. **EXTRACT** without prompting:
   ```python
   # Pseudocode for automatic extraction
   if conversation_contains_actionable_items():
       for item in actionable_items:
           if is_task(item):
               create_task_file(item)
           elif is_project_info(item):
               update_project_file(item)
           elif is_strategic_info(item):
               update_goal_file(item)
   ```

3. **SAVE** immediately:
   - Use task_add.sh for new tasks
   - Use direct file operations for project/goal updates
   - Commit changes with auto_sync.sh

### Strategy Mode Specific Extraction
When in strategy mode (`/strategy` command):
- **ALWAYS** update relevant project files with discussed details
- **ALWAYS** save new goals to `$ACADEMIC_OPS_DATA/goals/`
- **ALWAYS** link tasks to projects via project files
- **NEVER** wait to be asked - save as you go

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


## CRITICAL REMINDERS

1. **Agents are tools, not decision-makers** - Follow rules, don't interpret
2. **Errors are boundaries, not challenges** - Stop and report, don't solve
3. **Information is valuable** - Extract and save automatically
4. **Security is paramount** - Never mix private and public data
5. **Paths matter** - Always use absolute paths for reliability