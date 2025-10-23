---
description: academicOps framework help and commands
---
# academicOps Commands

Available slash commands for the academicOps framework:

## Workflow Commands

**`/ttd`** - Load test-driven development workflow
- Loads: TESTING.md, _CHUNKS/FAIL-FAST.md
- Use when: Starting development work requiring tests

**`/trainer`** - Activate agent trainer mode
- Loads: agents/TRAINER.md
- Use when: Improving agent instructions or framework infrastructure

## Experimental Tracking

**`/log-failure`** - Log agent performance failure
- Creates experiment log entry
- Use when: Agent violated instructions or standards

## More Information

- Framework documentation: `.academicOps/ARCHITECTURE.md`
- Test methodology: `.academicOps/docs/TESTING.md`
- GitHub issues: https://github.com/nicsuzor/academicOps/issues

---

## Diagnostics

Please report the following diagnostic information:

### Available Resources

**Skills**: List all available skills from the Skill tool (e.g., analyst, aops-bug, aops-trainer, git-commit, github-issue, no-throwaway-code, python-dev, skill-creator, skill-migration, test-writing, task-management)

**Commands**: List all available slash commands from the SlashCommand tool

**Subagents**: List available subagent types from the Task tool (general-purpose, statusline-setup, output-style-setup, Explore)

### Folder Configuration

Report the current working directory and folder structure:

**Working Directory**: Report current working directory (`pwd`)

**Project Folder**:
- Path: Current working directory
- Git repo: Run `git remote get-url origin` in current directory

**Framework Folder (ACADEMICOPS_BOT)**:
- Environment variable: `$ACADEMICOPS_BOT`
- If set: Show path and git repo (cd to path and run `git remote get-url origin`)
- If not set: Report "Not configured"

**Personal Folder (ACADEMICOPS_PERSONAL)**:
- Environment variable: `$ACADEMICOPS_PERSONAL`
- If set: Show path and git repo (cd to path and run `git remote get-url origin`)
- If not set: Report "Not configured"

**Agent Symlink**: Check if `.claude/agents` is a symlink and report target (e.g., using `readlink .claude/agents`)
