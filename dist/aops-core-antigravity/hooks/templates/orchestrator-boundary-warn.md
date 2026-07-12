# Orchestrator Boundary Warning

You just wrote to project source outside the framework allowlist:

- Tool: `{tool_name}`
- File: `{file_path}`

This is worker scope. The orchestrator's job is to dispatch; the worker's job
is to execute. Stop, file a task, and dispatch:

```
create_task(title="…", project="…")
polecat run -t <task-id>
```
