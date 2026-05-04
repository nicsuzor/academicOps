# Self-Test Workflow

1. Hook Gates Verification
   Testing the four layers of session infrastructure:

- SessionStart: Verify that principles are loaded and the session env file is correctly written.
- MCP & PKB Integration: Test semantic search and verify that task metadata (like goals: []) and state transitions are properly indexed and that the remote Rust server is accessible and responsive.
- PreToolUse: Validate the blocking gates: write operation should be prohibited by hydration gate.
- PKB write: verify that you can create a task for this self-test session and that claiming it is sufficient to open the previously blocked gates.
- RBG enforcer: ensure you can invoke the RBG periodic compliance enforcer with the instructions given
- Skills: Invoke core framework skills like /plan, /aops, and /remember to verify they load and execute.
- Subagents: Dispatch subagents (e.g., jr or marsha) to ensure inter-agent coordination and context passing work without dropping threads.
- Polecats: verify that you can dispatch remote polecat workers (both gemini and claude) over SSH on the correct host.
- Stop Gates: Verify stop is prevented before handover
- Handover: verify that /dump (handover) command provides useful instructions and that you are able to execute them all.
- Open stop gates (Important!): verify that you are not prevented from stopping after invoking the handover as directed.

IMPORTANT: All of the information required to undertake these tasks should be provided in your context at startup, within hooks, and in the files you are referred to. If you find you do not have sufficient information to know how to complete a task, HALT, and report the FAILURE to provide adequate instruction. Do NOT go looking or guessing for information that should be provided in advance.
