# academicOps Documentation Index

## Quick Start
- [PATH-RESOLUTION](PATH-RESOLUTION.md) - **READ FIRST**: How the system finds files across different machines
- [AGENT-INSTRUCTIONS](AGENT-INSTRUCTIONS.md) - Core operational guide for AI agents
- [modes](modes.md) - Interaction modes and constraints

## Architecture & Design
- [architecture](architecture.md) - System components and data flow
- [FAIL-FAST-PHILOSOPHY](FAIL-FAST-PHILOSOPHY.md) - Core design principle for error handling
- [AUTO-EXTRACTION](AUTO-EXTRACTION.md) - Automatic information extraction from conversations

## Development
- [DEVELOPMENT](DEVELOPMENT.md) - Guidelines for system development
- [error-handling](error-handling.md) - Error handling strategy
- [error-quick-reference](error-quick-reference.md) - Quick reference for common errors

## Agent Documentation
- [AGENT-TRAINER-PROMPT](AGENT-TRAINER-PROMPT.md) - Agent trainer for performance optimization

## Email System
- [EMAIL](EMAIL.md) - Email processing system documentation
- [EMAIL-TRIAGE-DESIGN](EMAIL-TRIAGE-DESIGN.md) - Email triage system design

## Scripts

### Task Management
Located in `scripts/`:
- `task_add.sh` - Add new tasks to inbox
- `task_complete.sh` - Mark tasks as completed
- `task_view.py` - Generate current task view
- `task_process.py` - Process and organize tasks
- `auto_sync.sh` - Git sync with automatic commit/push

### Email Processing
Located in `scripts/`:
- `email-triage.py` - Triage and categorize emails
- `outlook-read.ps1` - Read emails from Outlook (Windows)
- `outlook-draft.ps1` - Create draft responses (Windows)
- `outlook-message.ps1` - Send messages (Windows)

## Configuration

### Path Configuration
- `config/paths.sh` - Bash path resolution
- `config/paths.py` - Python path resolution

### Agent Configuration
- `.claude/` - Claude agent configurations
- `.gemini/` - Gemini agent configurations

## Data Structure

### Standard Directory Layout
```
$ACADEMIC_OPS_ROOT/           # User's workspace
├── data/                      # User data (private)
│   ├── goals/                 # Strategic goals
│   ├── projects/              # Project files
│   ├── tasks/                 # Task management
│   └── views/                 # Aggregated views
├── docs/                      # User documentation
├── projects/                  # Project repositories
└── bot/                       # This repository (public)
```

## Key Concepts

### Workflow Modes
1. **WORKFLOW MODE** - Strict sequential execution of documented workflows
2. **SUPERVISED MODE** - User-directed execution only
3. **DEVELOPMENT MODE** - System component creation/modification

### Error Handling
- Fail fast every time.
- Never continue with bad state
- Track issues systematically via GitHub

### Security Principles
- Never mix private and public data
- Use environment variables for sensitive configuration
- Maintain clear separation between repositories

## Integration Points

### Git Integration
- Automatic commit and sync
- Conflict resolution strategies
- Branch management

### AI Agent Integration
- Claude for complex development tasks
- Gemini for cost-effective workflows
- Custom agents for specialized tasks

### External Tools
- Outlook integration (Windows)
- Command-line interfaces
- Web-based dashboards (planned)

## Troubleshooting

### Common Issues
1. Path resolution failures - See [PATH-RESOLUTION](PATH-RESOLUTION.md)
2. Git sync conflicts - Check `auto_sync.sh` logs
3. Agent mode violations - Review [modes](modes.md)
4. Permission errors - Verify file permissions and paths

### Getting Help
1. Check relevant documentation
2. Search GitHub issues
3. Review error logs
4. Create new issue if needed

## Contributing
See [DEVELOPMENT](DEVELOPMENT.md) for contribution guidelines and development setup.