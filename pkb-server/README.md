# PKB MCP HTTP Server — Docker Deployment

Containerized deployment of the PKB MCP server over HTTP transport (port 8026).

## Prerequisites

- Docker and Docker Compose
- PKB data directory at `/opt/nic/brain`
- BGE-M3 model files at `/opt/debian/cache/aops/models/bge-m3/`
- ~2.7GB RAM available for model weights

## Quick Start

```bash
# Build and start
docker compose -f pkb-server/docker-compose.yml up -d

# Check logs
docker logs pkb-mcp-server

# Verify health
curl http://localhost:8026/health
```

## Manual `docker run`

```bash
docker build -t pkb-mcp-server pkb-server/

docker run -d --name pkb-mcp-server \
  -v /opt/nic/brain:/data \
  -v /opt/debian/cache/aops/models/bge-m3:/models/bge-m3:ro \
  -p 8026:8026 \
  --restart unless-stopped \
  pkb-mcp-server
```

## Client Configuration

Set `PKB_MCP_URL` on any machine that should connect:

```bash
export PKB_MCP_URL=http://<host>:8026/mcp
```

Tailscale handles authentication and encryption — no TLS configuration needed.

## Resource Usage

- **Memory**: ~2.7GB (BGE-M3 model weights)
- **Startup**: ~4 seconds
- **Port**: 8026 (HTTP, MCP JSON-RPC)
