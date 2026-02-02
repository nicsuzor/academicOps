[ SYTEM WARNING: We do not detect a valid handover invocation as the last action. ]

**When ending a work session**, you MUST invoke `/handover` as your final action: `Skill(skill="aops-core:handover")` and follow all required steps. 
- It is not sufficient to enact the steps without invoking the `/handover` skill -- this will not be recognised by the system.
- Using mutating tools (Edit, Write, Bash, git) after handover will reset this gate and require you to invoke `/handover` again.
- **Not done yet?** If you weren't trying to finish, keep working or use AskUserQuestion to pause for user input.
