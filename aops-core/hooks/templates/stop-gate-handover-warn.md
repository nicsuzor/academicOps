# Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

## MANDATORY WORKFLOW

1. **Complete all file changes** - Finish any pending edits, writes, or code modifications
2. **Run quality gates** - If code was changed, run tests and verify they pass
3. **Update task status** - Mark tasks complete or update progress as appropriate
4. **Invoke `/handover`** - Use the Skill tool with `skill="aops-core:handover"`
5. **Commit and PUSH** - The handover skill will guide you, but ensure `git push` succeeds
6. **Verify** - All changes committed AND pushed to remote
7. **Output Framework Reflection** - Provide context for the next session

## CRITICAL RULES

- Work is **NOT complete** until `git push` succeeds
- **NEVER stop** before pushing to remote
- If push fails, resolve and retry until it succeeds
- Using mutating tools (Edit, Write, Bash, git) after handover will reset this gate

## To Clear This Gate

Invoke `/handover` as your final action: `Skill(skill="aops-core:handover")`

**Not done yet?** If you weren't trying to finish, keep working or use AskUserQuestion to pause for user input.
