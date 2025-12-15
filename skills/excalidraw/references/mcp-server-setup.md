---
title: MCP Excalidraw Server Setup
type: reference
permalink: excalidraw-mcp-server
description: Real-time programmatic manipulation of Excalidraw canvas through AI agents using MCP server integration.
---

# MCP Excalidraw Server Setup

**Purpose**: Real-time programmatic manipulation of Excalidraw canvas through AI agents.

**When to use**: Automation workflows, live collaborative editing, programmatic generation.

**Not needed for**: Manual diagram creation (use Excalidraw directly).

---

## Architecture

Two independent components:

1. **Canvas Server** - Web interface (port 3000)
2. **MCP Server** - Connects AI assistants via stdio

**Repository**: https://github.com/yctimlin/mcp_excalidraw

---

## Installation

### Canvas Server (Local - Recommended)

```bash
git clone https://github.com/yctimlin/mcp_excalidraw.git
cd mcp_excalidraw
npm install
npm run build
npm run canvas
```

Access at: `http://localhost:3000`

### Canvas Server (Docker)

```bash
docker pull ghcr.io/yctimlin/mcp_excalidraw-canvas:latest
docker run -d -p 3000:3000 ghcr.io/yctimlin/mcp_excalidraw-canvas:latest
```

---

## MCP Server Configuration

Add to Claude Desktop/Code/Cursor config:

```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "node",
      "args": ["/path/to/mcp_excalidraw/dist/index.js"],
      "env": {
        "EXPRESS_SERVER_URL": "http://localhost:3000",
        "ENABLE_CANVAS_SYNC": "true"
      }
    }
  }
}
```

---

## Available MCP Tools

### Element Creation
- **Shapes**: rectangles, ellipses, diamonds
- **Connectors**: arrows, lines
- **Text**: labeled content with adjustable font sizes
- **Batch operations**: Create multiple elements simultaneously

### Element Management
- Update existing elements by ID
- Delete elements by ID
- Query elements with filters
- Element grouping and alignment
- Distribution controls
- Element locking

---

## Element Creation Examples

### Rectangle
```json
{
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 100,
  "backgroundColor": "#e3f2fd",
  "strokeColor": "#1976d2"
}
```

### Text
```json
{
  "type": "text",
  "x": 150,
  "y": 125,
  "text": "Process Step",
  "fontSize": 16
}
```

### Arrow
```json
{
  "type": "arrow",
  "x": 300,
  "y": 130,
  "width": 100,
  "height": 0,
  "strokeColor": "#666666"
}
```

---

## NPM Scripts Reference

| Script | Purpose |
|--------|---------|
| `npm start` | Build and start MCP server |
| `npm run canvas` | Build and start canvas server |
| `npm run build` | Build both frontend and backend |
| `npm run dev` | Start TypeScript watch mode + dev server |
| `npm run type-check` | TypeScript type validation |

---

## Troubleshooting

**Canvas server not responding**:
- Check `EXPRESS_SERVER_URL` environment variable
- Verify server is running (check port 3000)
- Check firewall settings

**Elements not appearing**:
- Verify WebSocket connection
- Check element coordinates are on visible canvas
- Inspect browser console for errors

**Connection issues**:
- Restart both canvas and MCP servers
- Check network connectivity
- Verify MCP config paths are correct

---

## Status

- **Canvas Server**: Production ready (local & Docker)
- **MCP Server**: Production ready (local & Docker)
- **NPM Publishing**: Development/testing phase

---

**Last Updated**: 2025-11-18
**Maintainer**: excalidraw skill
**Source**: https://github.com/yctimlin/mcp_excalidraw
