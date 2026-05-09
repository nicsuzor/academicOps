#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=3.2",
#     "mcp",
# ]
# ///
import asyncio
import json
import logging
import os
import statistics
import sys
import time
import traceback
from contextlib import suppress
from typing import Any

import mcp.types as mt
from fastmcp.client import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.server.lifespan import lifespan
from fastmcp.server.middleware.middleware import Middleware, MiddlewareContext
from fastmcp.server.providers.proxy import FastMCPProxy

# Logging configuration
LOG_FILE = "/tmp/pkb-proxy.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pkb-perf-proxy")

# Configuration
PKB_MCP_URL = os.environ.get("PKB_MCP_URL")

# Latency storage
HISTORY_LIMIT = 1000
tool_latencies: dict[str, list[float]] = {}

# Determine target
if PKB_MCP_URL:
    target = PKB_MCP_URL
    logger.info(f"Proxying remote PKB at {target}")
    print(f"Proxying remote PKB at {target}", file=sys.stderr)
else:
    # Fallback to local pkb binary if URL not set (common in Gemini CLI)
    target = StdioTransport("pkb", ["mcp"])
    logger.info("Proxying local 'pkb mcp'")
    print("Proxying local 'pkb mcp'", file=sys.stderr)

# Create shared client for persistent connection
shared_client = Client(target)


async def keep_alive_task():
    """Background task to keep the PKB connection alive and handle auto-reconnect."""
    backoff = 1
    while True:
        try:
            logger.info("Attempting to establish persistent connection to PKB backend...")
            async with shared_client:
                logger.info("Persistent connection to PKB backend established")
                backoff = 1  # Reset backoff on successful connection
                while shared_client.is_connected():
                    await asyncio.sleep(1)
            logger.warning("PKB backend connection closed")
        except Exception as e:
            logger.error(f"PKB backend connection failed: {e}")
            logger.debug(traceback.format_exc())
            # Use exponential backoff for reconnect attempts
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


@lifespan
async def persistent_connection_lifespan(server):
    """Lifespan manager to start/stop the keep-alive task."""
    logger.info("Entering persistent connection lifespan")
    task = asyncio.create_task(keep_alive_task())
    try:
        yield {}
    finally:
        logger.info("Exiting persistent connection lifespan, cancelling keep-alive task")
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        # Ensure the shared client is closed and its session task is stopped
        await shared_client.close()


async def client_factory():
    """Returns the shared client.

    FastMCPProxy will use 'async with client' on every request, which will
    increment the reference count on the shared_client's session.
    """
    return shared_client


# Create proxy server
try:
    mcp = FastMCPProxy(
        client_factory=client_factory,
        name="pkb-perf-proxy",
        lifespan=persistent_connection_lifespan,
    )
    logger.info("Successfully created FastMCPProxy with persistent lifespan")
except Exception as e:
    logger.critical(f"Failed to create proxy for {target}: {e}")
    logger.critical(traceback.format_exc())
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
        logger.debug(f"Calling tool: {tool_name}")

        start = time.perf_counter()
        try:
            result = await call_next(context)
            logger.debug(f"Tool {tool_name} returned successfully")
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"Tool {tool_name} took {duration_ms:.2f}ms")

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

    logger.info(f"Starting PKB Performance Proxy for {PKB_MCP_URL}")
    mcp.run()
