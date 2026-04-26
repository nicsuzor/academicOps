<aops-warning>You have stopped calling tools without finishing. Please complete your assigned work.

**When ending a work session**, you MUST invoke the `/dump` (end_session) skill and follow all required steps.

- The skill has two branches — **Short-form** (interactive only, work continuing) and **Full-form** (everything else: normal close, autonomous/headless, emergency, cross-machine). The canonical decision rule is in [[end_session]] §1; do not improvise the conditions from this template.

- It is not sufficient to enact the steps without invoking the skill — this will not be recognised by the system.
- Using mutating tools (Edit, Write, Bash, git) after the skill completes will reset this gate and require another `end_session` (or `/dump`) invocation.

**If you are running in an interactive session** and are unsure how to proceed, you can use the `ask_user` tool to request guidance from the user. (This tool is blocked in headless/non-interactive mode).
</aops-warning>
