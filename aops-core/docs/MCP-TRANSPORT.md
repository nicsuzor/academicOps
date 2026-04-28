# MCP Transport Strategy

## Overview

The academicOps framework supports two primary transports for MCP servers: **stdio** and **HTTP/SSE**.

### Canonical Transport Policy

- **HTTP/SSE**: The canonical transport for runtimes that cannot reliably use stdio due to restricted shell environments or missing environment variables. This includes:
  - **Cowork** (VM-based ephemeral workspaces)
  - **Desktop Code** (Claude Desktop, etc.)
  - **GitHub Actions** (when PKB context is needed)
- **Stdio**: Remains the default and recommended transport for local development environments where a full shell environment is available (e.g., Claude Code CLI on a developer machine). It offers lower latency and no network requirements.

## Network Requirements

### Tailscale (Preferred)

For clients that can reach the Tailscale network, the PKB MCP server is available at:
`http://services.stoat-musical.ts.net:8026/mcp`

### Public Endpoint (Fallback)

For clients outside the Tailscale network (like Cowork VMs without Tailscale installed), a public-auth'd endpoint is required.

## Auth Model (Draft)

For HTTP/SSE transport, authentication is handled via a Bearer token:

- **Client Configuration**: Set `PKB_MCP_TOKEN` in `~/.env.local`.
- **Header**: `Authorization: Bearer <token>`

## Configuration

The framework uses `scripts/run-mcp.sh` to launch MCP servers. This script resolves the transport based on the presence of `PKB_MCP_URL` in the environment or `~/.env.local`.

- If `PKB_MCP_URL` is set: use HTTP/SSE via `pkb_perf_proxy.py`.
- If `PKB_MCP_URL` is unset: fall back to local `pkb mcp` (stdio).
