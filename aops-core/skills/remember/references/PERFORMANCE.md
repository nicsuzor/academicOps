# PKB MCP Performance Monitoring

The PKB MCP server is wrapped in a performance proxy that logs tool call latency and provides aggregated statistics.

## Log Format

Tool call performance data is emitted to the server's `stderr` in a structured JSON format:

```json
[PKB_PERF] {"timestamp": "2026-04-26T...", "tool": "get_task", "duration_ms": 123.45, "success": true, "args": {"id": "task-123"}}
```

## Slow Call Alerts

If a tool call exceeds a configurable threshold (default: 500ms), a flagged log line is emitted:

```
[PKB_SLOW_CALL] tool=search duration=2100.50ms threshold=500ms args={"query": "performance"}
```

You can configure this threshold via the `PKB_SLOW_THRESHOLD_MS` environment variable.

## Aggregated Statistics

Aggregated p50, p95, and p99 statistics are available via the `pkb_perf_stats` MCP tool.

Example output:

```json
{
  "get_task": {
    "count": 50,
    "p50": 45.2,
    "p95": 120.5,
    "p99": 450.1,
    "max": 512.0,
    "avg": 55.4
  }
}
```

## Interpreting Stats

- **p50 (Median)**: Typical latency for the tool.
- **p95/p99**: Tail latency. High values indicate occasional spikes, often due to cold starts or complex graph traversals.
- **count**: Total number of calls in the current session.

These stats help identify which tools are candidates for optimization (e.g., adding caching or optimizing queries).
