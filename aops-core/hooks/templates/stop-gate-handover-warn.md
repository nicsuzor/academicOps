# Handover Required

You are stopping the session, but the `/handover` skill has not been invoked.

**To clear this gate, you must invoke `/handover`** (use the Skill tool with skill="aops-core:handover").

**Important**: Using any mutating tools (Edit, Write, Bash with file operations, git commands, etc.) will reset this gate. Complete all file changes first, then invoke `/handover` as your final action before stopping.

The `/handover` skill will guide you through:

1. Checking for uncommitted changes
2. Committing any remaining work
3. Outputting the required Framework Reflection
4. Clearing the stop gate

**Note:** If you weren't trying to finish the session, either keep going or use AskUserQuestion to pause and wait for a response.
