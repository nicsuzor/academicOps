1. Hook Gates Verification
   Testing the four layers of session infrastructure:

- SessionStart: Verify that principles are loaded and the latest state is pulled successfully.
- PreToolUse: Validate the hydration gate, periodic compliance enforcer, and policy enforcer. (Diagnosing our current tool lock-out will serve as the
  first real-world test of this!)
- PostToolUse: Check the warn-tier detection and ensure autocommit fires correctly.
- Stop Gates: Verify QA and handover discipline before a session ends.
- Automated Validation: Run uv run pytest tests/hooks/ to ensure gate logic aligns with the expected block/warn/allow fixtures.

  2. MCP & PKB Integration
- Connectivity & Schema: Use MCP tools (like mcp_pkb_get_stats and mcp_pkb_get_task) to verify the Rust server is responsive.
- Graph Maintenance: Test semantic search and verify that task metadata (like goals: []) and state transitions are properly indexed.

  3. Core Skills & Subagent Dispatch
- Skills: Invoke core framework skills like /plan, /aops, and /remember to verify they load and execute.
- Subagents: Dispatch subagents (e.g., jr or marsha) to ensure inter-agent coordination and context passing work without dropping threads.

  4. Framework Health Audit
- Diagnostic Scripts: Run uv run python scripts/audit_framework_health.py and uv run python scripts/check_framework_integrity.py to check for orphan
  files, broken context map references, and constraint violations.

  5. Full Test Suite Execution
- Action: Run uv run pytest tests/ to catch any remaining regressions across the entire framework, including utilities and routing logic.
