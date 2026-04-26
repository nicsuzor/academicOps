<aops-warning>You have stopped calling tools without finishing. Please complete your assigned work.

**When ending a work session**, you MUST invoke the `/dump` (end_session) skill and follow all required steps.

- **Short-form handover** (Interactive only): If you have a clear follow-up and the user is still steering, use the short-form `/dump` branch (update task delta + state next steps).
- **Full-form handover**: If you are finished or truly ending the session, follow the full workflow (commit + push + PR + release_task + handover block).

- It is not sufficient to enact the steps without invoking the skill — this will not be recognised by the system.
- Using mutating tools (Edit, Write, Bash, git) after the skill completes will reset this gate and require another `end_session` (or `/dump`) invocation.

**If you are running in an interactive session** and are unsure how to proceed, you can use the `ask_user` tool to request guidance from the user. (This tool is blocked in headless/non-interactive mode).
</aops-warning>
