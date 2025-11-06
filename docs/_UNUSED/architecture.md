# Core Architecture

## Overview
The academicOps system provides a structured approach to academic task and project management with AI-assisted automation.

## System Components

### 1. Data Layer
Markdown-based file system for maximum portability and version control compatibility.

**Structure:**
```
data/
├── goals/         # Strategic goals and objectives
├── projects/      # Project documentation and status
├── tasks/         # Task files organized by status
│   ├── inbox/     # New, unprocessed tasks
│   ├── active/    # Tasks being worked on
│   ├── waiting/   # Blocked or waiting tasks
│   └── completed/ # Finished tasks
└── views/         # Aggregated data views
```

### 2. Automation Layer
Scripts and tools for task management and workflow automation.

**Key Components:**
- Task management scripts (add, complete, view, process)
- Email processing pipeline
- Git synchronization
- Data aggregation and reporting

### 3. AI Agent Layer
Multiple AI agents with specialized roles and capabilities.

**Agent Types:**
- **Workflow Agents**: Execute predefined workflows strictly
- **Development Agents**: Create and maintain system components
- **Training Agents**: Optimize agent performance and documentation

### 4. Interface Layer
Multiple interfaces for different use cases.

**Interfaces:**
- Command-line tools
- Script automation
- AI chat interfaces (Claude, Gemini)
- Email integration

## Design Principles

### 1. Plain Text First
All data stored in human-readable markdown files for:
- Version control compatibility
- Cross-platform portability
- Long-term accessibility
- Easy manual editing

### 2. Separation of Concerns
- Public code (bot repository) separate from private data
- Generic tools separate from personal configuration
- Agent instructions separate from implementation

### 3. Progressive Enhancement
- System works with basic file operations
- AI agents add intelligence and automation
- Scripts provide convenience and efficiency
- Each layer enhances but doesn't replace lower layers

### 4. Fail-Safe Design
- Errors stop execution rather than corrupt data
- All operations logged and traceable
- Git provides rollback capability
- Manual override always available

## Data Flow

### Task Creation Flow
1. Input received (email, chat, script)
2. Task created in inbox with metadata
3. Task processed and categorized
4. Task linked to project if applicable
5. Task moved through workflow states
6. Completion logged and archived

### Information Extraction Flow
1. Content analyzed by AI agent
2. Actionable items identified
3. Items categorized (task, project update, goal)
4. Files created or updated
5. Changes committed to git
6. User notified of updates

### Sync and Backup Flow
1. Local changes detected
2. Changes staged and committed
3. Sync with remote repository
4. Conflicts resolved if needed
5. Backup verification
6. Status reported

## Extension Points

### Adding New Workflows
1. Create workflow documentation in `docs/workflows/`
2. Implement supporting scripts if needed
3. Configure agent access and permissions
4. Test with supervised mode first
5. Document in appropriate guides

### Adding New Agents
1. Define agent role and constraints
2. Create agent configuration file
3. Document in agent index
4. Test interaction modes
5. Monitor performance

### Adding New Data Types
1. Define markdown schema
2. Create directory structure
3. Implement processing scripts
4. Update documentation
5. Test with existing tools

## Security Considerations

### Data Isolation
- Private user data never committed to public repositories
- Sensitive information filtered from logs
- Credentials stored in environment variables
- Access controls enforced at multiple levels

### Agent Constraints
- Agents operate in defined modes with clear boundaries
- No autonomous decision-making in workflow mode
- All changes tracked and reversible
- User approval required for critical operations

### Audit Trail
- All operations logged
- Git history provides complete audit trail
- Agent actions documented in commits
- Error tracking via GitHub issues
