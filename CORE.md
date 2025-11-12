## User

- **Nic**: Law professor with ADHD researching tech fairness
- **Email**: n.suzor@qut.edu.au, nic@suzor.net
- **Needs**: Zero-friction capture, clean task separation, concise communication
- **Work Style**: Highest quality, academic rigor, professional standards

## When drafting content in my voice (academic writing, reviews, emails, etc.):

- Quick reference: [[STYLE-QUICK.md]]
- Comprehensive guide: [[STYLE.md]]

## Communicating with me:

- Read [[ACCOMMODATIONS.md]]

## Tools:

- Use the outlook mcp tool to access my email. There are two main accounts: n.suzor@qut.edu.au (QUT work) and nic@suzor.net (personal). I have another account, nsuzor@osbmember.com, for my Oversight Board (OSB) work, but it is only accessible on secure devices, not here.
- use 'uv run' for python commands.
- In my personal repository, you can add packages whenever you want with 'uv add' or 'npm i -g' (nvx managed)
- Making changes to live configs can be VERY dangerous. Make sure you RESEARCH the proper format for your changes (NO GUESSING) and VALIDATE them BEFORE you symlink edited config files into the user's live dotfiles.
- **Task operations**: For task management (viewing, archiving, creating), use the `task` skill.
- **Email → Task workflow**: When I ask "check my email for tasks", "process emails", "any new tasks from email", "what's in my inbox that needs action", "email triage", or "review emails for action items", OR when I use `/email` command, invoke the `tasks` skill's `email-task-capture` workflow ([[skills/tasks/workflows/email-capture.md]]). This extracts action items from emails, categorizes them using bmem context, and creates tasks automatically.

## Repository

- **This repo**: `/home/nic/src/writing/` (PRIVATE, nicsuzor/writing)
- Personal workspace for academic work and automation

## Framework Documentation, Paths, and state:

- **Framework state**: See "Framework State (Authoritative)" section in [[README.md]]
- **Paths**: `README.md` (file tree in root of repository)

## Agent Protocol: Before Creating Framework Components

**MANDATORY before proposing any new framework component (hook, skill, script, command, workflow):**

- Invoke `framework` skill for strategic context
- Use the `framework` skill for ALL questions or decisions about the documentation or tools in this project.
