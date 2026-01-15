# Core Rules

## Hydrator Loop

For non-trivial tasks, hydrate before execution:

1. **Read** `$AOPS/aops-core/agents/prompt-hydrator.md`
2. **Gather context**: memory search, bd issues, relevant heuristics
3. **Select workflow** from `$AOPS/WORKFLOWS.md`
4. **Plan with TodoWrite** before coding

Skip hydration for: simple questions, single-file edits, quick lookups.

## Task Tracking (bd)

Track file-modifying work with bd:

```bash
bd add "task description"     # Create task
bd list --status=open         # See open tasks
bd ready                      # Tasks ready for work
bd update <id> --status=in_progress
bd close <id>                 # When complete
bd sync                       # Sync state
```

**Rules:**
- Create bd task before multi-file changes
- Close task only after verification passes
- Run `bd sync` before session end

## Session Completion

Work is NOT complete until `git push` succeeds:

1. Run quality gates (tests, linters)
2. Update/close bd issues
3. Format and commit: `./scripts/format.sh && git add -A && git commit -m "..."`
4. Push: `git pull --rebase && bd sync && git push`

## Constraints

- **No workarounds**: If tools fail, HALT and report
- **Verify first**: Check actual state, never assume
- **One thing**: Complete requested task, then STOP
