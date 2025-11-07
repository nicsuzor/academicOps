# AGENTS AND TOOLS INDEX

## AI Agents

### gemini-cli

- **Primary rules**: `bot/GEMINI.md` (symlinked to `CLAUDE.md`)
- **Purpose**: Cost-effective model for structured workflows and routine tasks
- **Commands**: Located in `bot/.gemini/commands/`
  - `email.toml`: Email processing and response drafting
  - `strategy.toml`: Strategic planning advisor
- **Critical Files**:
  - `bot/.gemini/WORKFLOW-MODE-CRITICAL.md`: Strict error handling rules
- **Working Directory**: Can be invoked from any directory
- **Known Issues**: See GitHub issue #22 - workflow mode violations

### claude-code

- **Primary rules**: `bot/CLAUDE.md`
- **Purpose**: Premium model for development tasks and agent performance oversight
- **Sub-agents**: Defined in `bot/.claude/agents/`
  - `trainer.md`: Agent Trainer for optimizing agent performance
- **Working Directory**: Typically invoked from parent `/home/nic/src/writing/`
- **Use Cases**: Complex development, debugging, agent training

## Automation Scripts

### Task Management

- **Location**: `bot/scripts/`
- **Key Scripts**:
  - `task_add.py`: Add new tasks to inbox
  - `task_complete.sh`: Mark tasks as completed
  - `task_view.py`: Generate current task view
  - `task_process.py`: Process and organize tasks
  - `auto_sync.sh`: Git sync with automatic commit/push

### Email Processing

- **Location**: `bot/scripts/`
- **Key Scripts**:
  - `email-triage.py`: Triage and categorize emails
  - `outlook-read.ps1`: Read emails from Outlook (Windows)
  - `outlook-draft.ps1`: Create draft responses (Windows)
  - `outlook-message.ps1`: Send messages (Windows)
- **Documentation**: See `docs/EMAIL.md` and `docs/EMAIL-TRIAGE-DESIGN.md`

## Data Structure

### Personal Repository (`/home/nic/src/writing/`)

- `data/`: Task and project database (PRIVATE)
  - `goals/`: Strategic goals (*.md files)
  - `projects/`: Active projects (*.md files)
  - `tasks/`: Task files organized by status
  - `playbooks/`: Personal knowledge, tips, and techniques (*.md files)
  - `views/`: Aggregated views (current_view.json)
- `docs/`: System documentation
- `projects/`: Academic project submodules

### Bot Submodule (`bot/` - PUBLIC)

- `scripts/`: Automation tools
- `models/`: Data models (task.py)
- `.claude/`: Claude-specific configs
- `.gemini/`: Gemini-specific configs

## Critical Documentation

### Core Instructions

- `docs/INSTRUCTIONS.md`: Primary operational guide (READ FIRST)
- `bot/docs/AGENT-INSTRUCTIONS.md`: Detailed agent behaviors
- `docs/modes.md`: Workflow/Supervised/Development modes

### Workflows

- `docs/workflows/`: Documented workflows
  - `strategy.md`: Strategic planning workflow
  - `daily-planning.md`: Daily planning routine
  - `weekly-review.md`: Weekly review process
  - `idea-capture.md`: Idea capture workflow
  - `project-creation.md`: New project setup

### Development

- `docs/DEVELOPMENT.md`: Development guidelines
- `docs/architecture.md`: System architecture
- `docs/error-handling.md`: Error handling strategies
- `docs/error-quick-reference.md`: Quick error resolution guide
