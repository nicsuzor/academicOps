#!/usr/bin/env -S uv run python
import json
import os
import statistics
import sys
import time
from datetime import UTC, datetime
from typing import Any

import mcp.types as mt
from fastmcp.client.transports import StdioTransport
from fastmcp.server import create_proxy
from fastmcp.server.middleware.middleware import Middleware, MiddlewareContext

# Configuration
PKB_MCP_URL = os.environ.get("PKB_MCP_URL")
SLOW_THRESHOLD_MS = float(os.environ.get("PKB_SLOW_THRESHOLD_MS", 500))

# Latency storage
HISTORY_LIMIT = 1000
tool_latencies: dict[str, list[float]] = {}

# Determine target
if PKB_MCP_URL:
    target: str | StdioTransport = PKB_MCP_URL
    print(f"Proxying remote PKB at {target}", file=sys.stderr)
else:
    # Fallback to local pkb binary if URL not set (common in Gemini CLI)
    target = StdioTransport("pkb", ["mcp"])
    print("Proxying local 'pkb mcp'", file=sys.stderr)

# Create proxy
# We use create_proxy to preserve all tools, resources, and prompts from the target server
try:
    mcp = create_proxy(target, name="pkb-perf-proxy")
except Exception as e:
    print(f"CRITICAL: Failed to create proxy for {target}: {e}", file=sys.stderr)
    sys.exit(1)


class PerfMiddleware(Middleware):
    """Measures tool call latency and logs structured performance data."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: Any,
    ) -> Any:
        tool_name = context.message.name
        arguments = context.message.arguments or {}

        start = time.perf_counter()
        success = False
        try:
            result = await call_next(context)
            success = True
            return result
        except Exception:
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000

            perf_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "tool": tool_name,
                "duration_ms": round(duration_ms, 2),
                "success": success,
                "args": arguments,
            }
            print(f"[PKB_PERF] {json.dumps(perf_entry)}", file=sys.stderr)

            if duration_ms > SLOW_THRESHOLD_MS:
                print(
                    f"[PKB_SLOW_CALL] tool={tool_name} duration={duration_ms:.2f}ms "
                    f"threshold={SLOW_THRESHOLD_MS}ms args={json.dumps(arguments)}",
                    file=sys.stderr,
                )

            if tool_name not in tool_latencies:
                tool_latencies[tool_name] = []

            history = tool_latencies[tool_name]
            history.append(duration_ms)
            if len(history) > HISTORY_LIMIT:
                history.pop(0)


mcp.add_middleware(PerfMiddleware())


@mcp.tool()
def pkb_perf_stats() -> str:
    """Get aggregated p50/p95/p99 latency stats per tool from this session."""
    if not tool_latencies:
        return "No tool calls recorded yet."

    results = {}
    for tool_name, latencies in tool_latencies.items():
        if not latencies:
            continue
        sorted_lats = sorted(latencies)
        count = len(sorted_lats)
        results[tool_name] = {
            "count": count,
            "p50": round(statistics.median(sorted_lats), 2),
            "p95": round(statistics.quantiles(sorted_lats, n=100)[94], 2)
            if count >= 2
            else round(sorted_lats[-1], 2),
            "p99": round(statistics.quantiles(sorted_lats, n=100)[98], 2)
            if count >= 2
            else round(sorted_lats[-1], 2),
            "max": round(sorted_lats[-1], 2),
            "avg": round(statistics.mean(latencies), 2),
        }
    return json.dumps(results, indent=2)


if __name__ == "__main__":
    # Ensure stdout/stderr are unbuffered for real-time logging
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, write_through=True)

    print(f"Starting PKB Performance Proxy for {PKB_MCP_URL}", file=sys.stderr)
    mcp.run()
