# DEVELOPMENT MODE

DEVELOPMENT MODE allows you to make changes to architecture, prompts, workflow, documentation, or other components of the meta-project.

In DEVELOPMENT MODE, you need to be EXTRA CAREFUL in identifying root causes and proposing solutions that fit our goals and design choices.

The reliability of our system is paramount, and its integrity relies on ensuring that workflows are CAREFULLY DESIGNED and RIGOROUSLY TESTED. 


## DEVELOPMENT MODE PROCESS:

1. First **CHECK EXISTING ISSUES**: Search for issues and discussion on GitHub to understand decisions and progress to date
2. **MAKE A PLAN**: Create a new issue if required or update an open issue; create a details implementation plan with testing strategy and acceptance criteria.
3. **FIX THE ROOT CAUSE**: Address the underlying issue in the project's instructions, prompts, or workflows. Do not just complete the specific task that failed.
4. **BE CONCISE**: Keep all changes to prompts and documentation concise to manage token costs and improve clarity.
5. **IMPLEMENT SOLUTION**: Write code, create workflows, update architecture
6. **Log actions**: Create meaningful git commits describing what you did
7. **Update your progress** in the relevant GitHub issues.

### INTERACTIVE DEVELOPMENT
When working directly with the user in a back-and-forth exchange, you must follow their directions PRECISELY.
- **DO NOT** jump ahead or anticipate steps.
- Acknowledge and wait at each step if the user indicates a pause.
- Your role is to be a tool that the user is guiding, not an autonomous agent.

## REMEMBER
- Don't over-engineer, but adopt best practices.
- **ALL CHANGES** must be committed to GitHub. Local artifacts are temporary only.
- Adopt modular design for efficient reuse.


### Documentation Strategy - AVOID DUPLICATION

**GitHub Issues** are for:
- Problem identification and tracking
- Implementation planning and discussion
- Progress updates and resolution status
- Known bugs and feature requests


**DO NOT** create local files for bugs or progress tracking.
**DO NOT** copy issue content into workflow files
**DO NOT** create "Known Issues" sections in operational docs

INSTEAD:
- Reference GitHub issue numbers in commits
- Link to workflow files from issues when relevant
- Keep operational docs focused on HOW TO DO things
- Keep issues focused on WHAT needs fixing/building

### IMPORTANT: iterate and document!

We are BUILDING a system and LEARNING what works. Every time you complete a task:

1. **REFLECT** on what could be improved
2. **UPDATE** this documentation accordingly
3. **TRACK** progress using GitHub issues
## Instructions

**BEFORE** commencing a development task, you **MUST** read:


## Core Principles

**Don't over-engineer.** You're helping one person manage their projects more effectively. Keep solutions simple and focused on reducing cognitive load.

## When Building Workflows
- Start simple and iterate
- Use existing tools (like Zapier) instead of building from scratch
- Test with small batches first
- Focus on what actually saves time

## When Writing Documentation
- Be concise and practical
- Focus on what the workflow does, not implementation details
- Update docs when things change significantly
