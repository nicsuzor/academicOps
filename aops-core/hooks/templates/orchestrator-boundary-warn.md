# Orchestrator Boundary Warning

You just wrote to project source outside the framework allowlist:

- Tool: `{tool_name}`
- File: `{file_path}`

This is worker scope. The orchestrator's job is to dispatch; the worker's job
is to execute. Writes like this hide bugs in the polecat pipeline and create
accountability gaps (no PKB task record for the work).

**If you want to continue:**

- For a hotfix / one-liner that the user explicitly asked you to do here —
  proceed, and note it in your session summary.
- For anything larger — stop, file a task, and dispatch:

  ```
  create_task(title="…", project="…", priority="P2")
  polecat run -t <task-id>
  ```

Framework paths exempt from this warning: `specs/`, `aops-core/`, `.agents/`,
`docs/`, `tests/`, `scripts/`, `templates/`, `polecat/`, `aops-tools/`.

See [[specs/orchestrator-boundary.md]] and [[aops-core/HEURISTICS.md#P122]].
