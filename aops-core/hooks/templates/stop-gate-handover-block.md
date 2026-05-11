<aops-warning>You have stopped calling tools without finishing. Please complete your assigned work.

**Before invoking any handover skill, check that you actually finished.** If the bound task is not done and you are not blocked on user input, keep working — do not invoke a handover skill just to stop. Decisions inside the four corners of the task and within your declared expertise are yours to make; do not poll the user for them. If you want to keep going past the current task, use the `ask_user` / `AskUserQuestion` tool with a **specific recommended next step**, not an open-ended "what now?".

If you are genuinely at end-of-session, pick the right skill:

- **`/end-session`** — canonical close. Task complete or terminally blocked, normal end-of-day, autonomous/headless close. Does the full quality bar: commit + push + PR + `release_task` + Framework Reflection / Output / Tasks worked blocks + handover. The decision rule is in [[end_session]] §1; do not improvise.
- **`/dump`** — emergency bail. Mid-flight work, context full, restart needed. Captures a resume task + short handover block and halts. Does NOT commit, push, or write reflection blocks. Uncommitted work stays on the branch.

It is not sufficient to enact the steps without invoking the skill — this will not be recognised by the system.

Using mutating tools (Edit, Write, Bash, git) after the skill completes will reset this gate and require another handover invocation.

**If you are running in an interactive session** and are unsure how to proceed, you can use the `ask_user` tool to request guidance from the user. (This tool is blocked in headless/non-interactive mode).
</aops-warning>
